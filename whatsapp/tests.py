import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from .models import WhatsAppContact, WhatsAppMessage, ProcessedWebhookEvent
from .services import send_whatsapp_text


@override_settings(
    WHATSAPP_VERIFY_TOKEN="test_skiltrix_verify_token_123",
    WHATSAPP_APP_SECRET="test_skiltrix_app_secret_456",
    WHATSAPP_ACCESS_TOKEN="test_access_token_789",
    WHATSAPP_PHONE_NUMBER_ID="1234567890",
    WHATSAPP_API_VERSION="v21.0"
)
class WhatsAppChatbotTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = "/api/whatsapp/webhook/"
        self.verify_token = "test_skiltrix_verify_token_123"
        self.app_secret = "test_skiltrix_app_secret_456"

    def _generate_signature(self, payload_bytes: bytes) -> str:
        digest = hmac.new(
            self.app_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={digest}"

    def _create_message_payload(self, text="Hi", msg_id="wamid.test_001", sender="919940000000", msg_type="text"):
        msg_obj = {
            "from": sender,
            "id": msg_id,
            "timestamp": "1730000000",
            "type": msg_type,
        }
        if msg_type == "text":
            msg_obj["text"] = {"body": text}
        elif msg_type == "image":
            msg_obj["image"] = {"id": "media_001", "mime_type": "image/jpeg"}

        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_account_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "1234567890"
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Ashok Kumar"},
                                        "wa_id": sender
                                    }
                                ],
                                "messages": [msg_obj]
                            }
                        }
                    ]
                }
            ]
        }

    # 1. Successful Webhook Verification
    def test_01_successful_webhook_verification(self):
        response = self.client.get(self.webhook_url, {
            "hub.mode": "subscribe",
            "hub.verify_token": self.verify_token,
            "hub.challenge": "challenge_string_abc_123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "challenge_string_abc_123")

    # 2. Invalid Verification Token
    def test_02_invalid_verification_token(self):
        response = self.client.get(self.webhook_url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token_xyz",
            "hub.challenge": "challenge_string_abc_123"
        })
        self.assertEqual(response.status_code, 403)

    # 3. Incoming Text Message Processing
    @patch("requests.post")
    def test_03_incoming_text_message(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.out_reply_001"}]}
        )

        payload = self._create_message_payload(text="Hi", msg_id="wamid.msg_test_003")
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )

        self.assertEqual(response.status_code, 200)
        # Check contact created
        contact = WhatsAppContact.objects.filter(wa_id="919940000000").first()
        self.assertIsNotNone(contact)
        self.assertEqual(contact.profile_name, "Ashok Kumar")
        # Check inbound message saved
        inbound = WhatsAppMessage.objects.filter(message_id="wamid.msg_test_003").first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.body, "Hi")
        self.assertEqual(inbound.direction, "inbound")

    # 4. Invalid Signature Rejection
    def test_04_invalid_signature(self):
        payload = self._create_message_payload(text="Hello", msg_id="wamid.msg_test_004")
        payload_bytes = json.dumps(payload).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid_tampered_signature_999"
        )
        self.assertEqual(response.status_code, 403)

    # 5. Duplicate Message ID (Idempotency)
    @patch("requests.post")
    def test_05_duplicate_message_id_deduplication(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.out_reply_005"}]}
        )

        payload = self._create_message_payload(text="Hi", msg_id="wamid.duplicate_msg_005")
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        # First request
        res1 = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(res1.status_code, 200)

        initial_count = WhatsAppMessage.objects.filter(message_id="wamid.duplicate_msg_005").count()
        self.assertEqual(initial_count, 1)

        # Duplicate request with same message ID
        res2 = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(res2.status_code, 200)
        final_count = WhatsAppMessage.objects.filter(message_id="wamid.duplicate_msg_005").count()
        self.assertEqual(final_count, 1)  # Did not duplicate

    # 6. Delivery-Status Event Processing
    def test_06_delivery_status_event(self):
        contact = WhatsAppContact.objects.create(wa_id="919940000000", profile_name="Ashok")
        msg = WhatsAppMessage.objects.create(
            message_id="wamid.out_tracked_006",
            contact=contact,
            direction="outbound",
            status="sent",
            body="Welcome to SkilTrix"
        )

        status_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "biz_account_123",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "1234567890"
                                },
                                "statuses": [
                                    {
                                        "id": "wamid.out_tracked_006",
                                        "status": "delivered",
                                        "timestamp": "1730000050",
                                        "recipient_id": "919940000000"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        payload_bytes = json.dumps(status_payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(response.status_code, 200)

        msg.refresh_from_db()
        self.assertEqual(msg.status, "delivered")

    # 7. Malformed Webhook Payload
    def test_07_malformed_webhook_payload(self):
        bad_json = b"not-a-json-object"
        signature = self._generate_signature(bad_json)

        response = self.client.post(
            self.webhook_url,
            data=bad_json,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(response.status_code, 400)

    # 8. Unsupported Message Type Graceful Handling
    @patch("requests.post")
    def test_08_unsupported_media_message(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.out_reply_008"}]}
        )

        payload = self._create_message_payload(msg_id="wamid.media_008", msg_type="image")
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(response.status_code, 200)

        inbound = WhatsAppMessage.objects.filter(message_id="wamid.media_008").first()
        self.assertIsNotNone(inbound)
        self.assertEqual(inbound.message_type, "image")
        self.assertIn("IMAGE message received", inbound.body)

    # 9. WhatsApp Cloud API Failure Handling
    @patch("requests.post")
    def test_09_whatsapp_api_failure_handling(self, mock_post):
        # Simulate Meta rate limit / server error
        mock_post.return_value = MagicMock(
            status_code=429,
            json=lambda: {
                "error": {
                    "message": "(#130429) Rate limit hit",
                    "type": "OAuthException",
                    "code": 130429
                }
            }
        )

        res = send_whatsapp_text(to="919940000000", message="Test notification")
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], 130429)

        # Check failed message log
        failed_msg = WhatsAppMessage.objects.filter(status="failed").first()
        self.assertIsNotNone(failed_msg)
        self.assertIn("130429", failed_msg.error_message)

    # 10. Successful Automatic Reply (Menu Option 1)
    @patch("requests.post")
    def test_10_successful_automatic_reply_option_one(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.out_reply_010"}]}
        )

        payload = self._create_message_payload(text="1", msg_id="wamid.option1_010")
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(response.status_code, 200)

        # Check that outgoing reply for Python was sent
        outbound = WhatsAppMessage.objects.filter(direction="outbound", status="sent").first()
        self.assertIsNotNone(outbound)
        self.assertIn("Python", outbound.body)

    # 11. Unknown Menu Selection Handling
    @patch("requests.post")
    def test_11_unknown_menu_selection_fallback(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "wamid.out_reply_011"}]}
        )

        payload = self._create_message_payload(text="quantum computing xyz", msg_id="wamid.unknown_011")
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature
        )
        self.assertEqual(response.status_code, 200)

        outbound = WhatsAppMessage.objects.filter(direction="outbound", status="sent").first()
        self.assertIsNotNone(outbound)
        self.assertIn("didn't recognize that option", outbound.body)

    # 12. Database Persistence & 24h Window Check
    def test_12_database_persistence_and_window(self):
        contact = WhatsAppContact.objects.create(
            wa_id="919940001234",
            profile_name="Priya Sharma",
            last_incoming_at=timezone.now()
        )
        self.assertTrue(contact.is_within_24h_window())
        self.assertEqual(contact.masked_phone, "919***234")

        msg = WhatsAppMessage.objects.create(
            message_id="wamid.persist_012",
            contact=contact,
            direction="inbound",
            message_type="text",
            body="Hello SkilTrix",
            status="received"
        )
        self.assertEqual(WhatsAppContact.objects.count(), 1)
        self.assertEqual(WhatsAppMessage.objects.count(), 1)
        self.assertEqual(msg.contact.wa_id, "919940001234")
