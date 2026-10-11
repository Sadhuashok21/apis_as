import json
import hmac
import hashlib
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from .services import get_whatsapp_config, send_whatsapp_text, mark_whatsapp_as_read
from .models import WhatsAppContact, WhatsAppMessage, ProcessedWebhookEvent
from .handlers import handle_incoming_message

logger = logging.getLogger("whatsapp.webhook")


def verify_webhook_signature(request, app_secret: str) -> bool:
    """
    Validates Meta's X-Hub-Signature-256 HMAC header.
    Rejects tampered or spoofed webhook payloads.
    """
    if not app_secret:
        # If secret is not yet set in .env (e.g. initial setup), allow with warning
        logger.warning("WHATSAPP_APP_SECRET is not configured; skipping HMAC verification.")
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header in WhatsApp webhook POST.")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Malformed X-Hub-Signature-256 header: %s", signature_header)
        return False

    received_sig = signature_header.split("sha256=", 1)[1].strip()
    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        request.body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """
    Handles Meta WhatsApp Cloud API Webhook:
    - GET: Webhook verification challenge (Meta developer setup)
    - POST: Incoming message events, button clicks, status notifications, and deduplication
    """

    def get(self, request, *args, **kwargs):
        """
        Meta WhatsApp Webhook Verification Handshake.
        Meta requests: ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
        """
        config = get_whatsapp_config()
        configured_verify_token = config["verify_token"]

        mode = request.GET.get("hub.mode")
        verify_token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        logger.info(
            "WhatsApp webhook verification handshake initiated (mode=%s, token_provided=%s)",
            mode, bool(verify_token)
        )

        if mode == "subscribe" and verify_token and configured_verify_token:
            if verify_token == configured_verify_token:
                logger.info("WhatsApp webhook verified successfully!")
                return HttpResponse(challenge, content_type="text/plain", status=200)
            else:
                logger.warning("WhatsApp webhook verification token mismatch.")
                return HttpResponse("Verification token mismatch", status=403)

        logger.warning("Invalid WhatsApp webhook verification request parameters.")
        return HttpResponse("Forbidden", status=403)

    def post(self, request, *args, **kwargs):
        """
        Processes WhatsApp events: messages, interactive selections, and delivery statuses.
        """
        config = get_whatsapp_config()
        app_secret = config["app_secret"]

        # 1. HMAC Signature Verification
        if not verify_webhook_signature(request, app_secret):
            return HttpResponse("Invalid signature", status=403)

        # 2. JSON Payload Decoding
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            logger.warning("Failed to decode WhatsApp webhook JSON payload: %s", err)
            return JsonResponse({"error": "Malformed JSON payload"}, status=400)

        # 3. Verify event object type
        obj_type = payload.get("object")
        if obj_type != "whatsapp_business_account":
            logger.debug("Ignoring non-WhatsApp webhook object type: %s", obj_type)
            return JsonResponse({"status": "ignored", "reason": "unsupported_object"}, status=200)

        entries = payload.get("entry", [])
        if not entries:
            return JsonResponse({"status": "ok", "processed": 0}, status=200)

        # 4. Iterate entries and changes
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                field = change.get("field")
                if field != "messages":
                    continue

                value = change.get("value", {})
                self._process_value_payload(value)

        # Return HTTP 200 quickly to prevent Meta retries
        return JsonResponse({"status": "ok"}, status=200)

    def _process_value_payload(self, value: dict):
        """Handles the value payload: either status updates or incoming messages."""
        # ── A. Handle Status Updates (sent, delivered, read, failed) ─────────────
        statuses = value.get("statuses", [])
        for status_item in statuses:
            msg_id = status_item.get("id")
            new_status = status_item.get("status")
            errors = status_item.get("errors", [])
            err_msg = errors[0].get("message") if errors else ""

            if msg_id and new_status:
                try:
                    # Update existing outbound message record if tracked
                    updated = WhatsAppMessage.objects.filter(message_id=msg_id).update(
                        status=new_status,
                        error_message=err_msg
                    )
                    if updated:
                        logger.debug("Updated message %s status to %s", msg_id, new_status)
                except Exception as exc:
                    logger.debug("Could not update message status in DB: %s", exc)

        # ── B. Handle Incoming Messages ──────────────────────────────────────────
        messages = value.get("messages", [])
        contacts_meta = {
            c.get("wa_id"): c.get("profile", {}).get("name", "")
            for c in value.get("contacts", [])
            if c.get("wa_id")
        }

        for msg in messages:
            msg_id = msg.get("id")
            sender = msg.get("from")
            msg_type = msg.get("type", "unknown")
            timestamp_raw = msg.get("timestamp")

            if not msg_id or not sender:
                continue

            # Idempotency check: Ignore duplicate deliveries
            if ProcessedWebhookEvent.objects.filter(event_id=msg_id).exists():
                logger.info("Ignoring duplicate WhatsApp message ID: %s", msg_id)
                continue

            # Record event ID immediately to guarantee at-most-once execution
            try:
                ProcessedWebhookEvent.objects.create(
                    event_id=msg_id,
                    event_type="message"
                )
            except Exception:
                # If race condition, another thread already recorded it
                continue

            # Resolve or create contact profile
            profile_name = contacts_meta.get(sender, "")
            contact, _ = WhatsAppContact.objects.get_or_create(
                wa_id=sender,
                defaults={"profile_name": profile_name}
            )
            if profile_name and contact.profile_name != profile_name:
                contact.profile_name = profile_name
                contact.save(update_fields=["profile_name", "updated_at"])

            # Extract message content based on message type
            body_text = ""
            if msg_type == "text":
                body_text = msg.get("text", {}).get("body", "")

            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                int_type = interactive.get("type")
                if int_type == "button_reply":
                    reply = interactive.get("button_reply", {})
                    body_text = reply.get("title") or reply.get("id", "")
                elif int_type == "list_reply":
                    reply = interactive.get("list_reply", {})
                    body_text = reply.get("title") or reply.get("id", "")
                else:
                    body_text = "interactive_action"

            elif msg_type == "button":
                body_text = msg.get("button", {}).get("text", "")

            elif msg_type in ("image", "document", "audio", "video", "sticker", "location", "contacts"):
                body_text = f"[{msg_type.upper()} message received]"
                logger.info("Received media message (%s) from %s", msg_type, contact.masked_phone)
                # Send polite notice that our bot is text-based
                send_whatsapp_text(
                    to=contact.wa_id,
                    message=(
                        f"Thanks for sending your {msg_type}! 📎\n\n"
                        "Our WhatsApp assistant currently supports text and interactive menus.\n"
                        "Type *menu* to explore our programming tutorials and learning tracks."
                    ),
                    contact=contact
                )

            # Persist incoming message audit log
            try:
                WhatsAppMessage.objects.create(
                    message_id=msg_id,
                    contact=contact,
                    direction="inbound",
                    message_type=msg_type,
                    body=body_text,
                    raw_payload=msg,
                    status="received",
                    timestamp=timezone.now()
                )
            except Exception as save_err:
                logger.error("Failed to save inbound WhatsAppMessage: %s", save_err)

            # Mark message as read on WhatsApp (best practice)
            try:
                mark_whatsapp_as_read(msg_id)
            except Exception:
                pass

            # Route text and interactive responses to conversational handler
            if body_text and not body_text.startswith("["):
                try:
                    handle_incoming_message(contact, body_text, raw_message_data=msg)
                except Exception as handler_err:
                    logger.exception("Error processing conversational handler: %s", handler_err)
                    send_whatsapp_text(
                        to=contact.wa_id,
                        message="Sorry, we encountered a temporary error. Please type *menu* to try again.",
                        contact=contact
                    )

