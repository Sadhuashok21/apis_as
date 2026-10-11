import os
import logging
import requests
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.utils import timezone
from .models import WhatsAppContact, WhatsAppMessage

logger = logging.getLogger("whatsapp")


def get_whatsapp_config() -> Dict[str, str]:
    """
    Safely retrieves WhatsApp Cloud API configuration from settings and environment variables.
    Never hardcodes access tokens or phone number IDs.
    """
    access_token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", None) or os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", None) or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    business_account_id = getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", None) or os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", None) or os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None) or os.getenv("WHATSAPP_APP_SECRET", "")
    api_version = getattr(settings, "WHATSAPP_API_VERSION", None) or os.getenv("WHATSAPP_API_VERSION", "v21.0")

    # Clean up any surrounding quotes from .env
    return {
        "access_token": access_token.strip("\"'"),
        "phone_number_id": phone_number_id.strip("\"'"),
        "business_account_id": business_account_id.strip("\"'"),
        "verify_token": verify_token.strip("\"'"),
        "app_secret": app_secret.strip("\"'"),
        "api_version": api_version.strip("\"'") or "v21.0",
    }


def clean_phone_number(phone: str) -> str:
    """
    Standardizes international phone number by stripping +, spaces, hyphens, and parentheses.
    Example: '+91 99400-00000' -> '919940000000'
    """
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _post_to_graph_api(payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    """
    Internal helper to send a POST request to Meta WhatsApp Graph API.
    Handles network errors, HTTP error codes, and formats clear diagnostic output without exposing secrets.
    """
    config = get_whatsapp_config()
    access_token = config["access_token"]
    phone_number_id = config["phone_number_id"]
    api_version = config["api_version"]

    if not access_token or not phone_number_id:
        error_msg = "WhatsApp Cloud API credentials missing: WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID is not configured."
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "status_code": 0}

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        data = response.json() if response.content else {}

        if response.status_code in (200, 201):
            messages = data.get("messages", [])
            wamid = messages[0].get("id") if messages else ""
            return {
                "success": True,
                "data": data,
                "message_id": wamid,
                "status_code": response.status_code
            }

        # Analyze Meta error details safely
        error_info = data.get("error", {})
        error_code = error_info.get("code")
        error_subcode = error_info.get("error_subcode")
        error_message = error_info.get("message", "Unknown Graph API error")
        error_type = error_info.get("type", "OAuthException")

        friendly_error = f"Meta API Error ({response.status_code}) [Code {error_code}, Subcode {error_subcode}]: {error_message}"
        logger.warning(
            "WhatsApp Cloud API request failed: %s (type=%s, code=%s)",
            error_message, error_type, error_code
        )

        return {
            "success": False,
            "error": friendly_error,
            "error_code": error_code,
            "error_subcode": error_subcode,
            "raw_error": error_info,
            "status_code": response.status_code
        }

    except requests.exceptions.Timeout:
        logger.error("WhatsApp Cloud API request timed out after %d seconds.", timeout)
        return {"success": False, "error": "WhatsApp API connection timed out.", "status_code": 408}
    except requests.exceptions.ConnectionError:
        logger.error("Failed to establish network connection to Meta WhatsApp Graph API.")
        return {"success": False, "error": "Unable to connect to WhatsApp Graph API servers.", "status_code": 503}
    except Exception as exc:
        logger.exception("Unexpected exception when calling WhatsApp Cloud API: %s", exc)
        return {"success": False, "error": str(exc), "status_code": 500}


def send_whatsapp_text(
    to: str,
    message: str,
    contact: Optional[WhatsAppContact] = None,
    preview_url: bool = False
) -> Dict[str, Any]:
    """
    Primary interface for sending a plain-text WhatsApp message through Meta Cloud API.

    Args:
        to: Destination phone number (E.164 format without '+', e.g. '919876543210')
        message: Content string of the message
        contact: Optional WhatsAppContact model instance to link audit log
        preview_url: Whether to enable URL link previews if message contains links

    Returns:
        Dict containing success status, message_id if successful, or error details.
    """
    clean_to = clean_phone_number(to)
    if not clean_to or not message.strip():
        return {"success": False, "error": "Recipient phone and message body are required."}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_to,
        "type": "text",
        "text": {
            "preview_url": preview_url,
            "body": message.strip(),
        },
    }

    result = _post_to_graph_api(payload)

    # Persist message audit log if contact is resolved or can be resolved
    try:
        resolved_contact = contact
        if not resolved_contact:
            resolved_contact, _ = WhatsAppContact.objects.get_or_create(
                wa_id=clean_to,
                defaults={"profile_name": clean_to}
            )

        if result.get("success"):
            wamid = result.get("message_id") or f"out_{clean_to}_{int(timezone.now().timestamp())}"
            WhatsAppMessage.objects.create(
                message_id=wamid,
                contact=resolved_contact,
                direction="outbound",
                message_type="text",
                body=message.strip(),
                raw_payload=payload,
                status="sent",
                timestamp=timezone.now()
            )
            resolved_contact.last_outgoing_at = timezone.now()
            resolved_contact.save(update_fields=["last_outgoing_at", "updated_at"])
        else:
            wamid = f"failed_{clean_to}_{int(timezone.now().timestamp())}"
            WhatsAppMessage.objects.create(
                message_id=wamid,
                contact=resolved_contact,
                direction="outbound",
                message_type="text",
                body=message.strip(),
                raw_payload=payload,
                status="failed",
                error_message=result.get("error", "API failure"),
                timestamp=timezone.now()
            )
    except Exception as log_err:
        logger.warning("Failed to record outbound WhatsAppMessage audit log: %s", log_err)

    return result


def send_whatsapp_interactive_buttons(
    to: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = "SkilTrix Learning Platform",
    contact: Optional[WhatsAppContact] = None
) -> Dict[str, Any]:
    """
    Sends an interactive message with up to 3 quick-reply buttons.
    Each button item in buttons must have: {"id": "btn_id", "title": "Button Title"} (title <= 20 chars).
    Falls back gracefully to plain text if buttons list is empty.
    """
    clean_to = clean_phone_number(to)
    if not buttons:
        return send_whatsapp_text(to=clean_to, message=body_text, contact=contact)

    # Meta limits reply buttons to max 3 items
    formatted_buttons = []
    for btn in buttons[:3]:
        btn_id = btn.get("id", "btn")
        btn_title = (btn.get("title") or "Select")[:20]
        formatted_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn_id,
                "title": btn_title
            }
        })

    interactive_block: Dict[str, Any] = {
        "type": "button",
        "body": {"text": body_text},
        "action": {"buttons": formatted_buttons}
    }
    if header_text:
        interactive_block["header"] = {"type": "text", "text": header_text[:60]}
    if footer_text:
        interactive_block["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_to,
        "type": "interactive",
        "interactive": interactive_block
    }

    result = _post_to_graph_api(payload)

    # Fallback to plain text if interactive button delivery fails
    if not result.get("success"):
        logger.info("Interactive button send failed, falling back to numbered text menu.")
        menu_text = body_text + "\n\n" + "\n".join(
            f"{i+1}. {b.get('title')}" for i, b in enumerate(buttons)
        )
        return send_whatsapp_text(to=clean_to, message=menu_text, contact=contact)

    # Record message audit log
    try:
        resolved_contact = contact
        if not resolved_contact:
            resolved_contact, _ = WhatsAppContact.objects.get_or_create(
                wa_id=clean_to,
                defaults={"profile_name": clean_to}
            )
        wamid = result.get("message_id") or f"out_btn_{clean_to}_{int(timezone.now().timestamp())}"
        WhatsAppMessage.objects.create(
            message_id=wamid,
            contact=resolved_contact,
            direction="outbound",
            message_type="interactive_button",
            body=body_text,
            raw_payload=payload,
            status="sent",
            timestamp=timezone.now()
        )
        resolved_contact.last_outgoing_at = timezone.now()
        resolved_contact.save(update_fields=["last_outgoing_at", "updated_at"])
    except Exception as log_err:
        logger.warning("Failed to record interactive button audit log: %s", log_err)

    return result


def send_whatsapp_interactive_list(
    to: str,
    body_text: str,
    button_label: str,
    sections: List[Dict[str, Any]],
    header_text: Optional[str] = "SkilTrix Menu",
    footer_text: Optional[str] = "Type 'menu' anytime",
    contact: Optional[WhatsAppContact] = None
) -> Dict[str, Any]:
    """
    Sends an interactive message with a selectable list menu (up to 10 choices across sections).
    Each section: {"title": "Section Title", "rows": [{"id": "r1", "title": "Row Title", "description": "Optional"}]}
    """
    clean_to = clean_phone_number(to)
    interactive_block: Dict[str, Any] = {
        "type": "list",
        "header": {"type": "text", "text": header_text[:60]},
        "body": {"text": body_text},
        "footer": {"text": footer_text[:60]},
        "action": {
            "button": (button_label or "View Menu")[:20],
            "sections": sections
        }
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_to,
        "type": "interactive",
        "interactive": interactive_block
    }

    result = _post_to_graph_api(payload)
    if not result.get("success"):
        logger.info("Interactive list send failed, falling back to formatted text menu.")
        text_lines = [f"*{header_text}*", body_text, ""]
        for section in sections:
            if section.get("title"):
                text_lines.append(f"_{section['title']}:_")
            for row in section.get("rows", []):
                desc = f" - {row['description']}" if row.get("description") else ""
                text_lines.append(f"• *{row['title']}*{desc}")
        text_lines.append(f"\n{footer_text}")
        return send_whatsapp_text(to=clean_to, message="\n".join(text_lines), contact=contact)

    try:
        resolved_contact = contact
        if not resolved_contact:
            resolved_contact, _ = WhatsAppContact.objects.get_or_create(
                wa_id=clean_to,
                defaults={"profile_name": clean_to}
            )
        wamid = result.get("message_id") or f"out_list_{clean_to}_{int(timezone.now().timestamp())}"
        WhatsAppMessage.objects.create(
            message_id=wamid,
            contact=resolved_contact,
            direction="outbound",
            message_type="interactive_list",
            body=body_text,
            raw_payload=payload,
            status="sent",
            timestamp=timezone.now()
        )
        resolved_contact.last_outgoing_at = timezone.now()
        resolved_contact.save(update_fields=["last_outgoing_at", "updated_at"])
    except Exception as log_err:
        logger.warning("Failed to record interactive list audit log: %s", log_err)

    return result


def mark_whatsapp_as_read(message_id: str) -> bool:
    """
    Sends a read receipt to WhatsApp for an inbound message.
    """
    if not message_id:
        return False

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    result = _post_to_graph_api(payload)
    return bool(result.get("success"))

