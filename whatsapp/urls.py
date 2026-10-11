from django.urls import path, re_path
from .views import WhatsAppWebhookView

app_name = "whatsapp"

urlpatterns = [
    # Support both with and without trailing slash for Meta Webhook configuration
    path("webhook/", WhatsAppWebhookView.as_view(), name="webhook"),
    re_path(r"^webhook/?$", WhatsAppWebhookView.as_view(), name="webhook_flexible"),
]

