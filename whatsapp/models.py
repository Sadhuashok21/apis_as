from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class WhatsAppContact(models.Model):
    """
    Represents an individual WhatsApp user interacting with the SkilTrix WhatsApp Chatbot.
    Tracks state machine context, account association, and the 24-hour customer service window.
    """
    wa_id = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Standardized WhatsApp phone number without leading '+' (e.g. 919876543210)"
    )
    profile_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Display name as received from the Meta WhatsApp webhook payload"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="whatsapp_contacts",
        help_text="Associated SkilTrix user profile when account linking is completed"
    )
    current_state = models.CharField(
        max_length=64,
        default="MAIN_MENU",
        db_index=True,
        help_text="Current conversational state machine step (e.g. MAIN_MENU, PYTHON_INFO, etc.)"
    )
    state_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contextual JSON data stored across conversational turns"
    )
    last_incoming_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp of the most recent user-initiated message (for 24h window calculation)"
    )
    last_outgoing_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent bot response sent to this contact"
    )
    is_opted_in = models.BooleanField(
        default=True,
        help_text="Whether this user is opted in to receive bot replies and notifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wa_contacts"
        ordering = ["-updated_at"]
        verbose_name = "WhatsApp Contact"
        verbose_name_plural = "WhatsApp Contacts"

    def __str__(self):
        name = self.profile_name or "Unknown"
        return f"{name} ({self.masked_phone})"

    @property
    def masked_phone(self) -> str:
        """Returns partially masked phone number to protect privacy in logs and UI."""
        if len(self.wa_id) > 6:
            return f"{self.wa_id[:3]}***{self.wa_id[-3:]}"
        return self.wa_id

    def is_within_24h_window(self) -> bool:
        """
        Meta WhatsApp Cloud API enforces a 24-hour service window for free-form customer replies.
        After 24 hours from the last user-initiated incoming message, business-initiated messages
        must use an approved Meta template.
        """
        if not self.last_incoming_at:
            return False
        return (timezone.now() - self.last_incoming_at) <= timedelta(hours=24)


class WhatsAppMessage(models.Model):
    """
    Audit log of all incoming and outgoing WhatsApp messages.
    Stores metadata, message body, status updates, and raw webhook payloads.
    """
    DIRECTION_CHOICES = [
        ("inbound", "Inbound (User -> Bot)"),
        ("outbound", "Outbound (Bot -> User)"),
    ]

    STATUS_CHOICES = [
        ("received", "Received"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
    ]

    message_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="WhatsApp Message ID (wamid.HBg...)"
    )
    contact = models.ForeignKey(
        WhatsAppContact,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    direction = models.CharField(
        max_length=16,
        choices=DIRECTION_CHOICES,
        db_index=True
    )
    message_type = models.CharField(
        max_length=32,
        default="text",
        help_text="Message type: text, interactive, button, image, document, audio, etc."
    )
    body = models.TextField(
        blank=True,
        default="",
        help_text="Message text content or summary of interactive action"
    )
    raw_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Original raw Meta Cloud API payload for troubleshooting and auditing"
    )
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="received",
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if message transmission or handling failed"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )

    class Meta:
        db_table = "wa_messages"
        ordering = ["-timestamp"]
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"

    def __str__(self):
        return f"[{self.direction.upper()}] {self.contact.masked_phone}: {self.body[:40]}"


class ProcessedWebhookEvent(models.Model):
    """
    Idempotency store to prevent duplicate processing of webhook deliveries.
    Meta delivers webhooks at least once and will retry on slow responses or transient timeouts.
    """
    event_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Meta message ID or event ID used for idempotency"
    )
    event_type = models.CharField(
        max_length=32,
        default="message",
        help_text="Type of event (message, status, etc.)"
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wa_processed_events"
        ordering = ["-processed_at"]
        verbose_name = "Processed Webhook Event"
        verbose_name_plural = "Processed Webhook Events"

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"

