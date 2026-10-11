from django.contrib import admin
from .models import WhatsAppContact, WhatsAppMessage, ProcessedWebhookEvent


@admin.register(WhatsAppContact)
class WhatsAppContactAdmin(admin.ModelAdmin):
    list_display = ("masked_phone", "profile_name", "user", "current_state", "is_opted_in", "last_incoming_at", "updated_at")
    list_filter = ("current_state", "is_opted_in", "created_at")
    search_fields = ("wa_id", "profile_name", "user__email", "user__name")
    readonly_fields = ("created_at", "updated_at", "last_incoming_at", "last_outgoing_at")
    ordering = ("-updated_at",)


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ("message_id", "contact_phone", "direction", "message_type", "status", "timestamp")
    list_filter = ("direction", "status", "message_type", "timestamp")
    search_fields = ("message_id", "contact__wa_id", "body")
    readonly_fields = ("message_id", "contact", "direction", "message_type", "body", "raw_payload", "status", "error_message", "timestamp")
    ordering = ("-timestamp",)

    def contact_phone(self, obj):
        return obj.contact.masked_phone
    contact_phone.short_description = "Contact"


@admin.register(ProcessedWebhookEvent)
class ProcessedWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "processed_at")
    search_fields = ("event_id",)
    readonly_fields = ("event_id", "event_type", "processed_at")
    ordering = ("-processed_at",)

