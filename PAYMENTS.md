# SkilTrix SAP ABAP compiler payments

## Setup and deployment

Install the Python requirements and set these variables in the Django process environment (for local development, use `apis/.env`):

```text
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

Never put the secret or webhook secret in Vite variables. The public Key ID is returned by the authenticated order endpoint for Checkout.

Apply the database migrations and verify the app:

```powershell
cd apis
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test skiltrix.tests_payments
```

Build both React apps after changing their sources:

```powershell
cd skiltrix; npm run build
cd ..\admin; npm run build
```

Razorpay Test Mode API keys do not move real funds. Configure a webhook in the Razorpay Dashboard for `payment.captured` and `payment.failed`, with the HTTPS URL:

```text
https://<api-host>/apps/skiltrix/api/abap/payments/webhook/
```

Use the webhook signing secret generated for that webhook as `RAZORPAY_WEBHOOK_SECRET`; it is distinct from the API Key Secret. Test order creation, successful capture, failure, closing Checkout, webhook delivery, and status reconciliation using Razorpay test credentials before replacing the two API credentials with Live Mode values. No Nginx, Cloudflare, or other infrastructure configuration is changed by this feature.

## Endpoints

All user endpoints use the existing SkilTrix bearer-token authentication.

| Method and path | Purpose |
| --- | --- |
| `GET /apps/skiltrix/api/abap/pricing/` | Current SAP ABAP product price, active flag, pricing version, and caller access status |
| `GET /apps/skiltrix/api/abap/access/` | Caller entitlement status |
| `POST /apps/skiltrix/api/abap/coupons/validate/` | Validate `{ "code": "ABAP20" }`; returns amounts in paise |
| `POST /apps/skiltrix/api/abap/payments/create-order/` | Server recalculates and creates order. Send `Idempotency-Key`, `expected_amount_paise`, `pricing_version`, and optional `coupon_code` |
| `POST /apps/skiltrix/api/abap/payments/verify/` | Verify Checkout response fields `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature` |
| `POST /apps/skiltrix/api/abap/payments/cancel/` | Mark the caller's failed checkout order as cancelled |
| `GET /apps/skiltrix/api/abap/payments/status/<order_id>/` | Caller-owned status check and Razorpay reconciliation |
| `GET /apps/skiltrix/api/abap/payments/history/` | Caller-owned purchase history |
| `POST /apps/skiltrix/api/abap/payments/webhook/` | Razorpay HMAC verified event receiver; no bearer token |

Admin endpoints require an authenticated account whose server-side `user_type` is `admin`:

| Method and path | Purpose |
| --- | --- |
| `GET/PATCH /api/admin/compiler-pricing/` | View/update the SAP ABAP price and sale status; also shows aggregate revenue and coupons |
| `GET/POST /api/admin/compiler-coupons/` | List/create coupon rules |
| `GET/PATCH/DELETE /api/admin/compiler-coupons/<id>/` | Inspect/edit/archive a coupon; DELETE deactivates rather than removing redemption history |
| `GET /api/admin/compiler-payment-report/` | Recent platform-wide payment report |

The administrator UI is `/skiltrix/compiler-pricing` in the existing admin app. Prices and discounts use integer paise in the backend and display as INR in the UI. `allow_free` is an explicit coupon option; such a quote grants access through the zero-value purchase path without calling Razorpay.

The one-time product starts at ₹299 through migration `0007`; the migration uses `get_or_create`, preserving an existing SAP ABAP product price. Existing administrator changes are stored in `CompilerProduct` and picked up by the next pricing request.
