from django.contrib.admin.models import CHANGE, ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from .models import CompilerCoupon, CompilerCouponRedemption, CompilerPaymentOrder, CompilerProduct


class IsSkiltrixAdministrator(BasePermission):
    message = "Administrator access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "admin")


def audit(request, obj, action_flag, message):
    try:
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj)[:200],
            action_flag=action_flag,
            change_message=message,
        )
    except Exception:
        pass


def coupon_json(coupon):
    return {
        "id": coupon.pk, "code": coupon.code, "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value, "compiler": coupon.compiler,
        "active": coupon.active, "starts_at": coupon.starts_at, "expires_at": coupon.expires_at,
        "allow_free": coupon.allow_free,
        "minimum_amount_paise": coupon.minimum_amount_paise,
        "maximum_discount_paise": coupon.maximum_discount_paise,
        "max_redemptions": coupon.max_redemptions, "per_user_limit": coupon.per_user_limit,
        "redemptions": coupon.redemptions.count(),
        "revenue_paise": sum(coupon.payment_orders.filter(status="paid").values_list("amount_paise", flat=True)),
        "discount_total_paise": sum(coupon.payment_orders.filter(status="paid").values_list("discount_paise", flat=True)),
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsSkiltrixAdministrator])
def product_config(request):
    product = CompilerProduct.objects.filter(slug="sap-abap").first()
    if not product:
        return Response({"detail": "Pricing is not initialized."}, status=503)
    if request.method == "PATCH":
        if "is_free" in request.data:
            if request.data["is_free"] is True:
                product.price_paise = 0
            elif request.data["is_free"] is False and product.price_paise == 0:
                product.price_paise = 19900
        if "price_paise" in request.data:
            try:
                amount = int(request.data["price_paise"])
            except (TypeError, ValueError):
                return Response({"detail": "price_paise must be a valid integer."}, status=400)
            if amount < 0 or amount > 100_000_000:
                return Response({"detail": "Price must be between 0 and 100,000,000 paise."}, status=400)
            product.price_paise = amount
        if "active" in request.data:
            if not isinstance(request.data["active"], bool):
                return Response({"detail": "active must be a boolean."}, status=400)
            product.active = request.data["active"]
        product.save()
        audit(request, product, CHANGE, "Updated SAP ABAP compiler product configuration.")
    orders = CompilerPaymentOrder.objects.filter(product=product, status="paid")
    return Response({
        "id": product.pk, "name": product.name, "slug": product.slug, "price_paise": product.price_paise,
        "is_free": product.price_paise == 0,
        "currency": product.currency, "active": product.active, "one_time_access": product.one_time_access,
        "successful_payments": orders.count(), "revenue_paise": sum(orders.values_list("amount_paise", flat=True)),
        "discounts_paise": sum(CompilerPaymentOrder.objects.filter(product=product, status="paid").values_list("discount_paise", flat=True)),
        "coupons": [coupon_json(c) for c in CompilerCoupon.objects.order_by("code")],
    })


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsSkiltrixAdministrator])
def coupon_management(request, coupon_id=None):
    coupon = CompilerCoupon.objects.filter(pk=coupon_id).first() if coupon_id else None
    if coupon_id and coupon is None:
        return Response({"detail": "Coupon not found."}, status=404)
    if request.method == "GET":
        if coupon:
            return Response(coupon_json(coupon))
        return Response([coupon_json(item) for item in CompilerCoupon.objects.order_by("code")])
    if request.method == "DELETE":
        coupon.active = False
        coupon.save(update_fields=["active"])
        audit(request, coupon, CHANGE, "Archived coupon by deactivating it.")
        return Response({"status": "archived"})

    data = request.data
    allowed = {"code", "discount_type", "discount_value", "compiler", "active", "allow_free", "starts_at", "expires_at", "minimum_amount_paise", "maximum_discount_paise", "max_redemptions", "per_user_limit"}
    values = {key: data[key] for key in allowed if key in data}
    if "code" in values:
        values["code"] = str(values["code"]).strip().upper()
    if "discount_type" in values and values["discount_type"] not in ("percent", "fixed"):
        return Response({"detail": "discount_type must be percent or fixed."}, status=400)
    if "compiler" in values and values["compiler"] not in ("sap-abap", "abap", "*"):
        return Response({"detail": "Only SAP ABAP or all compilers are currently supported."}, status=400)
    for key in ("active", "allow_free"):
        if key in values and not isinstance(values[key], bool):
            return Response({"detail": f"{key} must be a boolean."}, status=400)
    try:
        for key in ("discount_value", "minimum_amount_paise", "per_user_limit"):
            if key in values:
                values[key] = int(values[key])
                if values[key] < (1 if key in ("discount_value", "per_user_limit") else 0):
                    raise ValueError
        for key in ("maximum_discount_paise", "max_redemptions"):
            if key in values and values[key] not in (None, ""):
                values[key] = int(values[key])
                if values[key] < 1:
                    raise ValueError
            elif key in values:
                values[key] = None
        if values.get("discount_type", coupon.discount_type if coupon else None) == "percent" and values.get("discount_value", coupon.discount_value if coupon else 0) > 100:
            raise ValueError
    except (TypeError, ValueError):
        return Response({"detail": "Coupon discount and limits contain an invalid value."}, status=400)
    for key in ("starts_at", "expires_at"):
        if key in values and values[key] not in (None, ""):
            if isinstance(values[key], str):
                values[key] = parse_datetime(values[key])
            if values[key] is None:
                return Response({"detail": f"{key} must be a valid ISO date and time."}, status=400)
            if timezone.is_naive(values[key]):
                values[key] = timezone.make_aware(values[key], timezone.get_current_timezone())
        elif key in values:
            values[key] = None
    start = values.get("starts_at", coupon.starts_at if coupon else None)
    expiry = values.get("expires_at", coupon.expires_at if coupon else None)
    if start and expiry and expiry <= start:
        return Response({"detail": "Expiry must be later than the start date."}, status=400)
    if coupon is None:
        required = {"code", "discount_type", "discount_value"}
        if not required.issubset(values):
            return Response({"detail": "code, discount_type, and discount_value are required."}, status=400)
        try:
            coupon = CompilerCoupon.objects.create(**values)
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                return Response({"detail": "That coupon code already exists."}, status=409)
            raise
        audit(request, coupon, ADDITION, "Created compiler coupon.")
        return Response(coupon_json(coupon), status=201)
    for key, value in values.items():
        setattr(coupon, key, value)
    coupon.save()
    audit(request, coupon, CHANGE, "Updated compiler coupon.")
    return Response(coupon_json(coupon))


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSkiltrixAdministrator])
def payment_report(request):
    rows = CompilerPaymentOrder.objects.filter(product__slug="sap-abap").select_related("user", "coupon").order_by("-created_at")[:200]
    return Response([{
        "order_id": row.razorpay_order_id,
        "user_id": row.user.user_id,
        "email": row.user.email,
        "coupon_code": row.coupon.code if row.coupon else None,
        "base_amount_paise": row.base_amount_paise,
        "discount_paise": row.discount_paise,
        "amount_paise": row.amount_paise,
        "currency": row.currency,
        "status": row.status,
        "payment_id": row.razorpay_payment_id,
        "created_at": row.created_at,
        "paid_at": row.paid_at,
    } for row in rows])

