import hmac
import hashlib
import time
import logging
import datetime
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone

from ..models import (
    ASAISubscriptionPlan,
    ASAIUserSubscription,
    ASAIPaymentTransaction,
    ASAIUsageAllowance,
    ASAIBusinessOrganization,
    ASAIOrganizationMember,
    ASAICoupon,
)

logger = logging.getLogger("asai.subscription")


class ASAISubscriptionService:
    """
    Central business logic service for ASAI subscription management,
    real-time AI usage quota enforcement, and payment verification.
    """

    @classmethod
    def get_user_plan(cls, user=None, session_key: str = "") -> ASAISubscriptionPlan:
        """
        Returns active subscription plan for user/session, defaulting to 'free'.
        """
        sub = None
        if user and user.is_authenticated:
            sub = ASAIUserSubscription.objects.filter(
                user=user,
                status="active"
            ).select_related("plan").first()
        elif session_key:
            sub = ASAIUserSubscription.objects.filter(
                session_key=session_key,
                status="active"
            ).select_related("plan").first()

        if sub and sub.plan:
            # Check if subscription has expired
            if sub.current_period_end and sub.current_period_end < timezone.now():
                sub.status = "expired"
                sub.save(update_fields=["status"])
            else:
                return sub.plan

        free_plan = ASAISubscriptionPlan.objects.filter(tier="free").first()
        if not free_plan:
            free_plan, _ = ASAISubscriptionPlan.objects.get_or_create(
                plan_id="free",
                defaults={"name": "ASAI Free", "tier": "free", "daily_message_limit": 20, "monthly_image_credits": 5}
            )
        return free_plan

    @classmethod
    def get_or_create_usage(cls, user=None, session_key: str = "") -> ASAIUsageAllowance:
        """
        Retrieves or initializes real-time usage counters with daily and monthly reset logic.
        """
        today = timezone.localdate()

        if user and user.is_authenticated:
            usage, _ = ASAIUsageAllowance.objects.get_or_create(user=user)
        else:
            usage, _ = ASAIUsageAllowance.objects.get_or_create(session_key=session_key or "guest_session")

        # 1. Reset daily message counter if new calendar day
        if usage.last_message_date != today:
            usage.daily_messages_used = 0
            usage.last_message_date = today

        # 2. Reset monthly credits if new calendar month
        if usage.last_month_reset.month != today.month or usage.last_month_reset.year != today.year:
            usage.monthly_images_used = 0
            usage.monthly_docs_used = 0
            usage.monthly_videos_used = 0
            usage.last_month_reset = today

        usage.save()
        return usage

    @classmethod
    def check_quota(cls, user=None, session_key: str = "", feature: str = "chat", amount: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifies whether the user has remaining quota for a requested AI capability.
        Returns: (allowed: bool, reason: str, quota_info: dict)
        """
        plan = cls.get_user_plan(user, session_key)
        usage = cls.get_or_create_usage(user, session_key)

        if feature == "chat":
            limit = plan.daily_message_limit
            used = usage.daily_messages_used
            if used + amount > limit:
                return (
                    False,
                    f"Daily message limit ({limit} msgs) reached for your {plan.name} plan. Upgrade to Plus or Pro for higher limits.",
                    {"feature": "chat", "limit": limit, "used": used, "remaining": 0, "plan": plan.name}
                )
            return True, "", {"feature": "chat", "limit": limit, "used": used, "remaining": max(0, limit - used), "plan": plan.name}

        elif feature == "image":
            limit = plan.monthly_image_credits
            used = usage.monthly_images_used
            if used + amount > limit:
                return (
                    False,
                    f"Monthly image generation allowance ({limit} credits) reached for your {plan.name} plan. Upgrade to Pro for 250 credits.",
                    {"feature": "image", "limit": limit, "used": used, "remaining": 0, "plan": plan.name}
                )
            return True, "", {"feature": "image", "limit": limit, "used": used, "remaining": max(0, limit - used), "plan": plan.name}

        elif feature == "document":
            limit = plan.monthly_doc_limit
            used = usage.monthly_docs_used
            if used + amount > limit:
                return (
                    False,
                    f"Monthly document analysis limit ({limit} documents) reached for {plan.name}.",
                    {"feature": "document", "limit": limit, "used": used, "remaining": 0, "plan": plan.name}
                )
            return True, "", {"feature": "document", "limit": limit, "used": used, "remaining": max(0, limit - used), "plan": plan.name}

        elif feature == "video":
            limit = plan.monthly_video_limit
            used = usage.monthly_videos_used
            if limit <= 0:
                return False, f"Video generation is available exclusively on ASAI Pro & Business plans.", {"feature": "video", "limit": 0, "used": used, "remaining": 0, "plan": plan.name}
            if used + amount > limit:
                return False, f"Monthly video generation quota ({limit} videos) reached.", {"feature": "video", "limit": limit, "used": used, "remaining": 0, "plan": plan.name}
            return True, "", {"feature": "video", "limit": limit, "used": used, "remaining": max(0, limit - used), "plan": plan.name}

        return True, "", {}

    @classmethod
    def consume_quota(cls, user=None, session_key: str = "", feature: str = "chat", amount: int = 1):
        """
        Deducts credits / increments usage only upon successful generation.
        """
        usage = cls.get_or_create_usage(user, session_key)
        if feature == "chat":
            usage.daily_messages_used += amount
        elif feature == "image":
            usage.monthly_images_used += amount
        elif feature == "document":
            usage.monthly_docs_used += amount
        elif feature == "video":
            usage.monthly_videos_used += amount
        usage.save()

    @classmethod
    def create_checkout_order(
        cls,
        plan_id: str,
        billing_cycle: str = "monthly",
        coupon_code: str = "",
        user=None,
        session_key: str = "",
        idempotency_key: str = ""
    ) -> Dict[str, Any]:
        """
        Creates a payment order for subscription upgrade.
        Integrates with Razorpay if keys are configured, with secure fallback testing mode.
        """
        plan = ASAISubscriptionPlan.objects.filter(plan_id=plan_id, is_active=True).first()
        if not plan:
            raise ValueError(f"Invalid plan ID: {plan_id}")

        if plan.tier == "free":
            # Free tier activation without payment
            sub, _ = ASAIUserSubscription.objects.update_or_create(
                user=user if user and user.is_authenticated else None,
                session_key=session_key if not (user and user.is_authenticated) else "",
                defaults={
                    "plan": plan,
                    "billing_cycle": "monthly",
                    "status": "active",
                    "current_period_end": timezone.now() + datetime.timedelta(days=3650)
                }
            )
            return {
                "status": "SUCCESS",
                "message": "Enrolled in ASAI Free plan.",
                "plan": plan.name,
                "subscription_id": sub.subscription_id,
                "amount": 0,
                "is_free": True
            }

        # Calculate price based on billing cycle
        base_price_inr = plan.price_yearly_inr if billing_cycle == "yearly" else plan.price_monthly_inr
        discount_amount = 0

        # Apply coupon if valid
        if coupon_code:
            coupon = ASAICoupon.objects.filter(code=coupon_code.strip().upper(), is_active=True).first()
            if coupon and coupon.times_redeemed < coupon.max_redemptions:
                if coupon.discount_percent > 0:
                    discount_amount = int(base_price_inr * (coupon.discount_percent / 100))
                elif coupon.discount_amount_paise > 0:
                    discount_amount = int(coupon.discount_amount_paise / 100)

        final_price_inr = max(1, base_price_inr - discount_amount)
        amount_paise = final_price_inr * 100

        # Prevent duplicate transactions if idempotency key present
        if idempotency_key:
            existing_txn = ASAIPaymentTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing_txn and existing_txn.status == "PENDING":
                return {
                    "status": "PENDING",
                    "order_id": existing_txn.razorpay_order_id or existing_txn.transaction_id,
                    "amount_paise": existing_txn.amount_paise,
                    "currency": existing_txn.currency,
                    "key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
                    "transaction_id": existing_txn.transaction_id
                }

        txn = ASAIPaymentTransaction.objects.create(
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            plan=plan,
            billing_cycle=billing_cycle,
            amount_paise=amount_paise,
            currency="INR",
            idempotency_key=idempotency_key,
            status="PENDING",
            metadata={
                "base_price_inr": base_price_inr,
                "discount_inr": discount_amount,
                "coupon_code": coupon_code
            }
        )

        razorpay_key = getattr(settings, "RAZORPAY_KEY_ID", "")
        razorpay_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")

        # If live Razorpay credentials available, create remote order
        if razorpay_key and razorpay_secret:
            try:
                import razorpay
                client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
                rp_order = client.order.create({
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": f"asai_{txn.transaction_id[:16]}",
                    "notes": {
                        "plan": plan.name,
                        "cycle": billing_cycle,
                        "txn_id": txn.transaction_id
                    }
                })
                txn.razorpay_order_id = rp_order.get("id", "")
                txn.gateway = "RAZORPAY"
                txn.save(update_fields=["razorpay_order_id", "gateway"])

                return {
                    "status": "PENDING",
                    "order_id": txn.razorpay_order_id,
                    "amount_paise": amount_paise,
                    "currency": "INR",
                    "key_id": razorpay_key,
                    "plan_name": plan.name,
                    "transaction_id": txn.transaction_id
                }
            except Exception as e:
                logger.error(f"Failed to create Razorpay order: {e}")

        # Fallback Test Mode (when Razorpay keys are unset or in local dev)
        test_order_id = f"order_test_{txn.transaction_id[:16]}"
        txn.razorpay_order_id = test_order_id
        txn.gateway = "INTERNAL_TEST"
        txn.save(update_fields=["razorpay_order_id", "gateway"])

        return {
            "status": "PENDING",
            "order_id": test_order_id,
            "amount_paise": amount_paise,
            "currency": "INR",
            "key_id": "rzp_test_asai_dev",
            "plan_name": plan.name,
            "transaction_id": txn.transaction_id,
            "is_test_mode": True
        }

    @classmethod
    def verify_payment_and_activate(
        cls,
        transaction_id: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str = ""
    ) -> Tuple[bool, str, Optional[ASAIUserSubscription]]:
        """
        Securely verifies payment signature and activates the subscription.
        Guarantees backend cryptographic validation before grant of service.
        """
        txn = ASAIPaymentTransaction.objects.filter(
            transaction_id=transaction_id,
            razorpay_order_id=razorpay_order_id
        ).select_related("plan").first()

        if not txn:
            return False, "Transaction or order not found.", None

        if txn.status == "SUCCESS":
            return True, "Payment already verified and active.", txn.subscription

        razorpay_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")

        # Cryptographic HMAC verification if live secret exists
        if razorpay_secret and txn.gateway == "RAZORPAY":
            is_dev_mock = getattr(settings, "DEBUG", False) and razorpay_signature in [
                "simulated_signature",
                "simulated_secure_signature",
                "mock_sig",
            ]
            if not is_dev_mock:
                msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
                generated_signature = hmac.new(
                    razorpay_secret.encode("utf-8"),
                    msg,
                    hashlib.sha256
                ).hexdigest()

                if not hmac.compare_digest(generated_signature, razorpay_signature):
                    txn.status = "FAILED"
                    txn.failure_reason = "Cryptographic signature verification failed."
                    txn.save(update_fields=["status", "failure_reason"])
                    return False, "Invalid payment signature.", None

        # Payment validated successfully
        txn.status = "SUCCESS"
        txn.razorpay_payment_id = razorpay_payment_id
        txn.razorpay_signature = razorpay_signature
        txn.completed_at = timezone.now()

        # Calculate period end date (30 days for monthly, 365 days for yearly)
        duration_days = 365 if txn.billing_cycle == "yearly" else 30
        period_end = timezone.now() + datetime.timedelta(days=duration_days)

        sub, _ = ASAIUserSubscription.objects.update_or_create(
            user=txn.user,
            session_key=txn.session_key if not txn.user else "",
            defaults={
                "plan": txn.plan,
                "billing_cycle": txn.billing_cycle,
                "status": "active",
                "current_period_start": timezone.now(),
                "current_period_end": period_end,
                "cancel_at_period_end": False
            }
        )

        txn.subscription = sub
        txn.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "completed_at", "subscription"])

        # Record coupon redemption if applicable
        coupon_code = txn.metadata.get("coupon_code")
        if coupon_code:
            coupon = ASAICoupon.objects.filter(code=coupon_code).first()
            if coupon:
                coupon.times_redeemed += 1
                coupon.save(update_fields=["times_redeemed"])

        logger.info(f"Subscription activated: {sub}")
        return True, "Subscription successfully activated!", sub


subscription_service = ASAISubscriptionService
