import hashlib
import hmac
import json
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    CompilerCoupon,
    CompilerCouponRedemption,
    CompilerEntitlement,
    CompilerPaymentOrder,
    CompilerProduct,
)
from .abap_access import user_has_abap_access


PRODUCT_SLUG = "sap-abap"


def get_abap_product():
    return CompilerProduct.objects.filter(slug=PRODUCT_SLUG).first()


def coupon_quote(user, code, product=None, lock=False):
    product = product or get_abap_product()
    if not product or not product.active:
        return None, "SAP ABAP compiler purchases are currently unavailable."
    now = timezone.now()
    qs = CompilerCoupon.objects
    if lock:
        qs = qs.select_for_update()
    coupon = qs.filter(code=(code or "").strip().upper()).first()
    if not coupon:
        return None, "Coupon code was not found."
    if not coupon.active:
        return None, "This coupon is inactive."
    if coupon.starts_at and now < coupon.starts_at:
        return None, "This coupon is not available yet."
    if coupon.expires_at and now >= coupon.expires_at:
        return None, "This coupon has expired."
    if coupon.compiler not in ("*", PRODUCT_SLUG, "abap"):
        return None, "This coupon does not apply to the SAP ABAP compiler."
    if coupon.minimum_amount_paise > product.price_paise:
        return None, "The purchase does not meet this coupon's minimum amount."

    redemptions = CompilerCouponRedemption.objects.filter(coupon=coupon)
    pending = CompilerPaymentOrder.objects.filter(coupon=coupon, status="pending", created_at__gte=now - timedelta(minutes=20))
    if coupon.max_redemptions is not None and redemptions.count() + pending.count() >= coupon.max_redemptions:
        return None, "This coupon has reached its redemption limit."
    if redemptions.filter(user=user).count() + pending.filter(user=user).count() >= coupon.per_user_limit:
        return None, "You have reached this coupon's redemption limit."

    if coupon.discount_type == CompilerCoupon.PERCENT:
        # INR paise, rounded to the nearest paisa (half up).
        discount = (product.price_paise * coupon.discount_value + 50) // 100
    else:
        discount = coupon.discount_value * 100
    if coupon.maximum_discount_paise is not None:
        discount = min(discount, coupon.maximum_discount_paise)
    discount = min(discount, product.price_paise)
    if discount == product.price_paise and not coupon.allow_free:
        discount = max(0, product.price_paise - 100)
    return {
        "valid": True,
        "compiler": PRODUCT_SLUG,
        "currency": product.currency,
        "original_amount_paise": product.price_paise,
        "discount_amount_paise": discount,
        "final_amount_paise": product.price_paise - discount,
        "coupon_code": coupon.code,
        "allow_free": coupon.allow_free,
        "pricing_version": product.updated_at.isoformat(),
    }, None


def get_razorpay_client():
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        return None
    import razorpay
    return razorpay.Client(auth=(key_id, key_secret))


def grant_order_entitlement(order):
    entitlement, created = CompilerEntitlement.objects.get_or_create(
        user=order.user,
        product=order.product,
        defaults={"payment_order": order, "status": "active", "expires_at": None},
    )
    if not created and entitlement.status != "active":
        entitlement.status = "active"
        entitlement.payment_order = order
        entitlement.expires_at = None
        entitlement.save(update_fields=["status", "payment_order", "expires_at"])
    if order.coupon_id:
        CompilerCouponRedemption.objects.get_or_create(
            payment_order=order,
            defaults={"coupon": order.coupon, "user": order.user, "compiler": PRODUCT_SLUG, "discount_paise": order.discount_paise},
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def compiler_pricing(request):
    product = get_abap_product()
    if not product:
        return Response({"detail": "Pricing is not initialized. Apply Django migrations."}, status=503)
    user = getattr(request, "user", None)
    access = user_has_abap_access(user) if user and user.is_authenticated else False
    is_free = bool(product.active and product.price_paise == 0)
    return Response({
        "compiler": PRODUCT_SLUG,
        "name": product.name,
        "currency": product.currency,
        "price_paise": product.price_paise,
        "price": f"{product.price_paise / 100:.2f}",
        "is_free": is_free,
        "active": product.active,
        "access": access,
        "pricing_version": product.updated_at.isoformat(),
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def compiler_access(request):
    user = getattr(request, "user", None)
    product = get_abap_product()
    is_free = bool(product and product.active and product.price_paise == 0)
    allowed = user_has_abap_access(user) if user and user.is_authenticated else False
    return Response({
        "compiler": PRODUCT_SLUG,
        "has_access": allowed,
        "is_free": is_free,
        "status": "active" if allowed else "locked"
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_compiler_coupon(request):
    product = get_abap_product()
    quote, error = coupon_quote(request.user, request.data.get("code", ""), product)
    if error:
        return Response({"valid": False, "detail": error}, status=status.HTTP_400_BAD_REQUEST)
    return Response(quote)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    if user_has_abap_access(request.user):
        return Response({"detail": "SAP ABAP access is already active."}, status=status.HTTP_409_CONFLICT)
    idem = (request.headers.get("Idempotency-Key") or request.data.get("idempotency_key") or "").strip()
    if not idem or len(idem) > 100:
        return Response({"detail": "A valid Idempotency-Key header is required."}, status=400)
    try:
        with transaction.atomic():
            existing = CompilerPaymentOrder.objects.filter(user=request.user, idempotency_key=idem).first()
            if existing:
                if existing.status == "pending":
                    return Response({"order_id": existing.razorpay_order_id, "amount_paise": existing.amount_paise,
                                     "currency": existing.currency, "key_id": settings.RAZORPAY_KEY_ID, "status": existing.status})
                if existing.status == "paid":
                    return Response({"status": "paid", "free_purchase": existing.amount_paise == 0,
                                     "access": user_has_abap_access(request.user), "order_id": existing.razorpay_order_id})
                return Response({"detail": "This idempotency key has already been used."}, status=409)

            product = CompilerProduct.objects.select_for_update().filter(slug=PRODUCT_SLUG).first()
            if not product or not product.active:
                return Response({"detail": "SAP ABAP compiler purchases are currently unavailable."}, status=409)
            code = request.data.get("coupon_code", "")
            coupon = None
            discount = 0
            if code:
                quote, error = coupon_quote(request.user, code, product=product, lock=True)
                if error:
                    return Response({"valid": False, "detail": error}, status=400)
                if request.data.get("expected_amount_paise") is None or int(request.data["expected_amount_paise"]) != quote["final_amount_paise"] or request.data.get("pricing_version") != quote["pricing_version"]:
                    return Response({"detail": "Price or coupon eligibility changed. Review the updated quote before continuing.", "quote": quote}, status=409)
                coupon = CompilerCoupon.objects.select_for_update().get(code=quote["coupon_code"])
                discount = quote["discount_amount_paise"]
                amount = quote["final_amount_paise"]
            else:
                amount = product.price_paise
                if request.data.get("expected_amount_paise") is None or int(request.data["expected_amount_paise"]) != amount or request.data.get("pricing_version") != product.updated_at.isoformat():
                    return Response({"detail": "Price changed. Review the updated quote before continuing.", "quote": {
                        "original_amount_paise": amount, "discount_amount_paise": 0, "final_amount_paise": amount,
                        "currency": product.currency, "pricing_version": product.updated_at.isoformat(),
                    }}, status=409)

            previous_pending = CompilerPaymentOrder.objects.filter(user=request.user, product=product, status="pending").order_by("-created_at").first()
            if previous_pending:
                if previous_pending.amount_paise == amount and previous_pending.coupon_id == (coupon.pk if coupon else None):
                    return Response({"order_id": previous_pending.razorpay_order_id, "amount_paise": previous_pending.amount_paise,
                                     "currency": previous_pending.currency, "key_id": settings.RAZORPAY_KEY_ID, "status": "pending"})
                return Response({"detail": "A payment for this compiler is already pending. Complete or close that checkout before starting another.",
                                 "order_id": previous_pending.razorpay_order_id}, status=409)

            if amount <= 0:
                local_id = uuid.uuid4()
                order = CompilerPaymentOrder.objects.create(
                    user=request.user, product=product, coupon=coupon, local_order_id=local_id,
                    razorpay_order_id=f"free_{local_id.hex}", idempotency_key=idem,
                    base_amount_paise=product.price_paise, discount_paise=discount, amount_paise=0,
                    currency=product.currency, status="paid", paid_at=timezone.now(),
                )
                grant_order_entitlement(order)
                return Response({"status": "paid", "free_purchase": True, "access": True}, status=201)

            client = get_razorpay_client()
            if client is None:
                return Response({"detail": "Razorpay is not configured on the server."}, status=503)
            try:
                remote = client.order.create({"amount": amount, "currency": product.currency, "receipt": f"st-{uuid.uuid4().hex[:24]}", "notes": {"user_id": request.user.user_id, "product": PRODUCT_SLUG}})
            except Exception:
                return Response({"detail": "Razorpay could not create the order. Please retry."}, status=502)
            order = CompilerPaymentOrder.objects.create(
                user=request.user, product=product, coupon=coupon, idempotency_key=idem,
                razorpay_order_id=remote["id"], base_amount_paise=product.price_paise,
                discount_paise=discount, amount_paise=amount, currency=product.currency,
            )
            return Response({"order_id": order.razorpay_order_id, "amount_paise": amount,
                             "currency": product.currency, "key_id": settings.RAZORPAY_KEY_ID, "status": order.status}, status=201)
    except IntegrityError:
        existing = CompilerPaymentOrder.objects.filter(user=request.user, idempotency_key=idem).first()
        if existing:
            if existing.status == "paid":
                return Response({"status": "paid", "free_purchase": existing.amount_paise == 0,
                                 "access": user_has_abap_access(request.user), "order_id": existing.razorpay_order_id})
            if existing.status == "pending":
                return Response({"order_id": existing.razorpay_order_id, "amount_paise": existing.amount_paise,
                                 "currency": existing.currency, "key_id": settings.RAZORPAY_KEY_ID, "status": existing.status})
        return Response({"detail": "This idempotency key has already been used."}, status=409)
    except (ValueError, TypeError):
        return Response({"detail": "The quote amount is invalid."}, status=400)


def verify_and_capture_order(*, order, payment_id, signature=None, webhook=False):
    client = get_razorpay_client()
    if client is None:
        return False, "Razorpay is not configured."
    if not webhook:
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
        except Exception:
            return False, "Payment signature is invalid."
    try:
        payment = client.payment.fetch(payment_id)
    except Exception:
        return False, "Unable to confirm the payment with Razorpay."
    if payment.get("order_id") != order.razorpay_order_id or payment.get("amount") != order.amount_paise or payment.get("currency") != order.currency:
        return False, "Payment details do not match this order."
    if payment.get("status") == "authorized":
        try:
            client.payment.capture(payment_id, order.amount_paise)
            payment = client.payment.fetch(payment_id)
        except Exception:
            return False, "Payment is authorized and capture is still pending."
    if payment.get("status") != "captured":
        return False, "Payment is not captured yet."
    with transaction.atomic():
        locked = CompilerPaymentOrder.objects.select_for_update().get(pk=order.pk)
        if locked.status == "paid":
            return locked.razorpay_payment_id == payment_id, "Payment was already verified." if locked.razorpay_payment_id == payment_id else "Order was paid using a different transaction."
        if locked.status not in ("pending", "failed", "cancelled"):
            return False, "Order is not in a verifiable state."
        if locked.coupon_id:
            coupon = CompilerCoupon.objects.select_for_update().get(pk=locked.coupon_id)
            now = timezone.now()
            recent_pending = CompilerPaymentOrder.objects.filter(
                coupon=coupon, status="pending", created_at__gte=now - timedelta(minutes=20),
            ).exclude(pk=locked.pk)
            global_full = coupon.max_redemptions is not None and (
                CompilerCouponRedemption.objects.filter(coupon=coupon).count() + recent_pending.count() >= coupon.max_redemptions
            )
            user_full = CompilerCouponRedemption.objects.filter(coupon=coupon, user=locked.user).count() + recent_pending.filter(user=locked.user).count() >= coupon.per_user_limit
            if global_full or user_full:
                try:
                    client.payment.refund(payment_id, {"amount": locked.amount_paise})
                    reason = "Coupon redemption limit reached; Razorpay refund initiated."
                except Exception:
                    reason = "Coupon redemption limit reached after capture; manual refund required."
                locked.status = "failed"
                locked.razorpay_payment_id = payment_id
                locked.failure_reason = reason
                locked.save(update_fields=["status", "razorpay_payment_id", "failure_reason"])
                return False, reason
        locked.razorpay_payment_id = payment_id
        locked.status = "paid"
        locked.paid_at = timezone.now()
        locked.save(update_fields=["razorpay_payment_id", "status", "paid_at"])
        grant_order_entitlement(locked)
    return True, "Payment verified."


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    order_id = request.data.get("razorpay_order_id", "")
    payment_id = request.data.get("razorpay_payment_id", "")
    order = CompilerPaymentOrder.objects.filter(razorpay_order_id=order_id, user=request.user).first()
    if not order:
        return Response({"detail": "Payment order not found."}, status=404)
    ok, message = verify_and_capture_order(order=order, payment_id=payment_id, signature=request.data.get("razorpay_signature"))
    if not ok:
        return Response({"detail": message, "status": order.status}, status=400)
    return Response({"status": "paid", "access": user_has_abap_access(request.user), "detail": message})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_payment_order(request):
    order = CompilerPaymentOrder.objects.filter(
        razorpay_order_id=request.data.get("order_id", ""), user=request.user,
    ).first()
    if not order:
        return Response({"detail": "Payment order not found."}, status=404)
    with transaction.atomic():
        order = CompilerPaymentOrder.objects.select_for_update().get(pk=order.pk)
        if order.status == "pending":
            order.status = "cancelled"
            order.failure_reason = str(request.data.get("reason", "Checkout closed"))[:255]
            order.save(update_fields=["status", "failure_reason"])
    return Response({"status": order.status})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_status(request, order_id):
    order = CompilerPaymentOrder.objects.filter(razorpay_order_id=order_id, user=request.user).first()
    if not order:
        return Response({"detail": "Payment order not found."}, status=404)
    if order.status == "pending":
        client = get_razorpay_client()
        if client is not None:
            try:
                payments = client.order.payments(order.razorpay_order_id)
                for payment in payments.get("items", []):
                    if payment.get("status") in ("authorized", "captured"):
                        verify_and_capture_order(order=order, payment_id=payment.get("id", ""), webhook=True)
                        order.refresh_from_db()
                        if order.status == "paid":
                            break
            except Exception:
                # The caller can retry. The stored order remains pending and access locked.
                pass
    return Response({"order_id": order.razorpay_order_id, "status": order.status, "amount_paise": order.amount_paise,
                     "currency": order.currency, "access": user_has_abap_access(request.user)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_history(request):
    rows = CompilerPaymentOrder.objects.filter(user=request.user).select_related("product", "coupon").order_by("-created_at")[:100]
    return Response([{
        "order_id": row.razorpay_order_id, "compiler": row.product.name, "coupon_code": row.coupon.code if row.coupon else None,
        "original_amount_paise": row.base_amount_paise, "discount_paise": row.discount_paise,
        "amount_paise": row.amount_paise, "currency": row.currency, "status": row.status,
        "created_at": row.created_at, "paid_at": row.paid_at,
        "access_expires_at": CompilerEntitlement.objects.filter(user=request.user, product=row.product, status="active").values_list("expires_at", flat=True).first(),
    } for row in rows])


@api_view(["POST"])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET") or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not secret or not signature:
        return Response({"detail": "Webhook verification is not configured."}, status=400)
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return Response({"detail": "Invalid webhook signature."}, status=400)
    try:
        event = json.loads(request.body)
    except (ValueError, TypeError):
        return Response({"detail": "Invalid webhook body."}, status=400)
    if event.get("event") == "payment.captured":
        payload = event.get("payload", {}).get("payment", {}).get("entity", {})
        order = CompilerPaymentOrder.objects.filter(razorpay_order_id=payload.get("order_id")).first()
        if order:
            verify_and_capture_order(order=order, payment_id=payload.get("id", ""), webhook=True)
    elif event.get("event") == "payment.failed":
        payload = event.get("payload", {}).get("payment", {}).get("entity", {})
        with transaction.atomic():
            order = CompilerPaymentOrder.objects.select_for_update().filter(razorpay_order_id=payload.get("order_id")).first()
            if order and order.status == "pending":
                order.status = "failed"
                order.failure_reason = (payload.get("error_description") or "Payment failed")[:255]
                order.save(update_fields=["status", "failure_reason"])
    return Response({"received": True})
