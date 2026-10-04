from datetime import timedelta
import hashlib
import hmac
import json
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from sfs.models import AllUsers
from .coupon_views import coupon_quote
from .models import CompilerCoupon, CompilerEntitlement, CompilerPaymentOrder, CompilerProduct


class CompilerCouponTests(TestCase):
    def setUp(self):
        self.user = AllUsers.objects.create(
            username="pay_test", name="Payment Test", email="payment-test@example.invalid",
            user_id="pay_test_user", platform="web", platform_name="SkilTrix", type="user", ip="127.0.0.1",
        )
        self.product, _ = CompilerProduct.objects.get_or_create(slug="sap-abap", defaults={"name": "SAP ABAP", "price_paise": 29900})
        self.product.price_paise = 29900
        self.product.active = True
        self.product.save()

    def make_coupon(self, **overrides):
        values = {"code": "ABAP20", "discount_type": "percent", "discount_value": 20, "compiler": "sap-abap"}
        values.update(overrides)
        return CompilerCoupon.objects.create(**values)

    def test_percentage_and_fixed_discount_use_paise(self):
        self.make_coupon()
        quote, error = coupon_quote(self.user, "abap20", self.product)
        self.assertIsNone(error)
        self.assertEqual(quote["discount_amount_paise"], 5980)
        self.assertEqual(quote["final_amount_paise"], 23920)

        self.make_coupon(code="FLAT100", discount_type="fixed", discount_value=100)
        quote, error = coupon_quote(self.user, "FLAT100", self.product)
        self.assertIsNone(error)
        self.assertEqual((quote["discount_amount_paise"], quote["final_amount_paise"]), (10000, 19900))

    def test_expired_wrong_compiler_and_zero_policy(self):
        self.make_coupon(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIn("expired", coupon_quote(self.user, "ABAP20", self.product)[1])
        self.make_coupon(code="OTHER", compiler="python")
        self.assertIn("does not apply", coupon_quote(self.user, "OTHER", self.product)[1])
        self.make_coupon(code="FREE", discount_type="fixed", discount_value=999)
        quote, error = coupon_quote(self.user, "FREE", self.product)
        self.assertIsNone(error)
        self.assertEqual(quote["final_amount_paise"], 100)
        self.make_coupon(code="FREEALL", discount_type="fixed", discount_value=999, allow_free=True)
        quote, error = coupon_quote(self.user, "FREEALL", self.product)
        self.assertIsNone(error)
        self.assertEqual(quote["final_amount_paise"], 0)

    def test_price_is_dynamic_and_coupon_limits_are_enforced(self):
        coupon = self.make_coupon(max_redemptions=1)
        self.product.price_paise = 35000
        self.product.save()
        quote, _ = coupon_quote(self.user, "ABAP20", self.product)
        self.assertEqual(quote["original_amount_paise"], 35000)
        from .models import CompilerCouponRedemption
        CompilerCouponRedemption.objects.create(coupon=coupon, user=self.user, compiler="sap-abap", discount_paise=7000)
        self.assertIn("redemption limit", coupon_quote(self.user, "ABAP20", self.product)[1])


class CompilerEntitlementPaymentTests(TestCase):
    def setUp(self):
        self.user = AllUsers.objects.create(
            username="abap_locked", name="Locked User", email="locked@example.invalid",
            user_id="abap_locked_user", platform="web", platform_name="SkilTrix", type="user", ip="127.0.0.1",
        )
        self.product, _ = CompilerProduct.objects.get_or_create(slug="sap-abap", defaults={"name": "SAP ABAP", "price_paise": 29900})
        self.product.price_paise = 29900
        self.product.active = True
        self.product.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_regular_user_cannot_change_admin_product_price(self):
        response = self.client.patch(reverse("compiler-product-config"), {"price_paise": 1}, format="json")
        self.assertEqual(response.status_code, 403)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price_paise, 29900)

    def test_explicit_free_coupon_creates_access_without_razorpay(self):
        coupon = CompilerCoupon.objects.create(
            code="FREEABAP", discount_type="fixed", discount_value=999,
            compiler="sap-abap", allow_free=True,
        )
        quote, error = coupon_quote(self.user, coupon.code, self.product)
        self.assertIsNone(error)
        response = self.client.post(
            reverse("compiler-payment-create-order"),
            {"coupon_code": coupon.code, "expected_amount_paise": 0, "pricing_version": quote["pricing_version"]},
            format="json", HTTP_IDEMPOTENCY_KEY="free-purchase-001",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["free_purchase"])
        self.assertTrue(CompilerEntitlement.objects.filter(user=self.user, product=self.product, status="active").exists())

    def test_unpaid_user_is_denied_execution(self):
        response = self.client.post(reverse("abap-execute"), {"code": "WRITE 'hello'.", "execution_mode": "simulator"})
        self.assertEqual(response.status_code, 403)

    @patch("skiltrix.coupon_views.get_razorpay_client")
    def test_verified_payment_grants_permanent_entitlement_idempotently(self, get_client):
        order = CompilerPaymentOrder.objects.create(
            user=self.user, product=self.product, razorpay_order_id="order_test_01",
            base_amount_paise=29900, discount_paise=0, amount_paise=29900,
        )
        razorpay = Mock()
        razorpay.payment.fetch.return_value = {
            "id": "pay_test_01", "order_id": order.razorpay_order_id,
            "amount": 29900, "currency": "INR", "status": "captured",
        }
        get_client.return_value = razorpay
        response = self.client.post(reverse("compiler-payment-verify"), {
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_id": "pay_test_01",
            "razorpay_signature": "valid-signature",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["access"])
        razorpay.utility.verify_payment_signature.assert_called_once()
        self.assertEqual(CompilerEntitlement.objects.filter(user=self.user, product=self.product, status="active").count(), 1)
        self.assertIsNone(CompilerEntitlement.objects.get(user=self.user, product=self.product).expires_at)

        repeated = self.client.post(reverse("compiler-payment-verify"), {
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_id": "pay_test_01",
            "razorpay_signature": "valid-signature",
        })
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(CompilerEntitlement.objects.filter(user=self.user, product=self.product).count(), 1)

    @patch("skiltrix.coupon_views.get_razorpay_client")
    def test_invalid_signature_does_not_unlock(self, get_client):
        order = CompilerPaymentOrder.objects.create(
            user=self.user, product=self.product, razorpay_order_id="order_test_02",
            base_amount_paise=29900, discount_paise=0, amount_paise=29900,
        )
        razorpay = Mock()
        razorpay.utility.verify_payment_signature.side_effect = ValueError("bad signature")
        get_client.return_value = razorpay
        response = self.client.post(reverse("compiler-payment-verify"), {
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_id": "pay_invalid",
            "razorpay_signature": "bad",
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CompilerEntitlement.objects.filter(user=self.user, product=self.product).exists())

    def test_wrong_user_cannot_see_another_users_order_status(self):
        order = CompilerPaymentOrder.objects.create(
            user=self.user, product=self.product, razorpay_order_id="order_private_01",
            base_amount_paise=29900, discount_paise=0, amount_paise=29900,
        )
        other = AllUsers.objects.create(
            username="another_user", name="Other User", email="other@example.invalid",
            user_id="other_user_id", platform="web", platform_name="SkilTrix", type="user", ip="127.0.0.1",
        )
        self.client.force_authenticate(other)
        response = self.client.get(reverse("compiler-payment-status", args=[order.razorpay_order_id]))
        self.assertEqual(response.status_code, 404)

    @patch("skiltrix.coupon_views.get_razorpay_client")
    @patch.dict("os.environ", {"RAZORPAY_WEBHOOK_SECRET": "webhook-test-secret"})
    def test_duplicate_signed_webhook_is_idempotent(self, get_client):
        order = CompilerPaymentOrder.objects.create(
            user=self.user, product=self.product, razorpay_order_id="order_webhook_01",
            base_amount_paise=29900, discount_paise=0, amount_paise=29900,
        )
        razorpay = Mock()
        razorpay.payment.fetch.return_value = {
            "id": "pay_webhook_01", "order_id": order.razorpay_order_id,
            "amount": 29900, "currency": "INR", "status": "captured",
        }
        get_client.return_value = razorpay
        body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {
            "id": "pay_webhook_01", "order_id": order.razorpay_order_id,
        }}}}).encode()
        signature = hmac.new(b"webhook-test-secret", body, hashlib.sha256).hexdigest()
        for _ in range(2):
            response = APIClient().generic("POST", reverse("compiler-payment-webhook"), body,
                                           content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(CompilerEntitlement.objects.filter(user=self.user, product=self.product).count(), 1)
        self.assertEqual(CompilerPaymentOrder.objects.get(pk=order.pk).status, "paid")
