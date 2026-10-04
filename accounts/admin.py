from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ClientApplication,
    UserProfile,
    UserSession,
    AuthorizationCode,
    EmailVerificationToken,
    PasswordResetToken,
    AuthenticationAuditLog,
)


@admin.register(ClientApplication)
class ClientApplicationAdmin(admin.ModelAdmin):
    list_display = ("client_id", "name", "client_type", "is_enabled", "created_at")
    list_filter = ("is_enabled", "client_type", "created_at")
    search_fields = ("client_id", "name", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Application Details", {
            "fields": ("client_id", "name", "description", "logo_url", "is_enabled")
        }),
        ("Security & Type", {
            "fields": ("client_type", "client_secret")
        }),
        ("Redirect URIs Allowlist", {
            "fields": ("allowed_redirect_uris", "allowed_logout_redirect_uris", "allowed_origins"),
            "description": "Strict allowlists to prevent open-redirect vulnerabilities."
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "email_verified", "created_at")
    list_filter = ("email_verified", "created_at")
    search_fields = ("user__email", "user__name", "phone_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "user", "client_app", "ip_address", "is_revoked_badge", "created_at", "expires_at")
    list_filter = ("is_revoked", "client_app", "created_at")
    search_fields = ("session_id", "user__email", "user__name", "ip_address")
    readonly_fields = ("session_id", "created_at", "last_active_at", "revoked_at")
    actions = ["revoke_selected_sessions"]

    def is_revoked_badge(self, obj):
        if obj.is_revoked:
            return format_html('<span style="color:red; font-weight:bold;">Revoked</span>')
        return format_html('<span style="color:green; font-weight:bold;">Active</span>')
    is_revoked_badge.short_description = "Status"

    def revoke_selected_sessions(self, request, queryset):
        count = queryset.update(is_revoked=True)
        self.message_user(request, f"Revoked {count} selected session(s).")
    revoke_selected_sessions.short_description = "Revoke selected sessions"


@admin.register(AuthorizationCode)
class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ("code_masked", "user", "client_app", "is_used", "expires_at", "created_at")
    list_filter = ("is_used", "client_app", "created_at")
    search_fields = ("user__email", "client_app__name")
    readonly_fields = ("code", "user", "client_app", "redirect_uri", "code_challenge", "code_challenge_method", "scope", "is_used", "expires_at", "created_at")

    def code_masked(self, obj):
        return f"{obj.code[:12]}..." if obj.code else ""
    code_masked.short_description = "Authorization Code"


@admin.register(AuthenticationAuditLog)
class AuthenticationAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "user_display", "client_app", "status_badge", "ip_address")
    list_filter = ("event_type", "status", "client_app", "created_at")
    search_fields = ("user__email", "user__name", "event_type", "ip_address", "details")
    readonly_fields = ("user", "event_type", "client_app", "ip_address", "user_agent", "status", "details", "created_at")

    def user_display(self, obj):
        return getattr(obj.user, "email", "Anonymous")
    user_display.short_description = "User"

    def status_badge(self, obj):
        color = "green" if obj.status == "SUCCESS" else "red" if obj.status == "FAILURE" else "orange"
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, obj.status)
    status_badge.short_description = "Status"
