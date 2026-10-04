import json
from datetime import timedelta
from urllib.parse import urlparse
from django.conf import settings
from django.db import models
from django.utils import timezone


class ClientApplication(models.Model):
    """
    Registered client applications that participate in Single Sign-On (SSO).
    Supports OpenID Connect / OAuth2 Authorization Code Flow with PKCE.
    """
    CLIENT_TYPE_CHOICES = (
        ("public", "Public Client (SPA / Mobile with PKCE)"),
        ("confidential", "Confidential Client (Backend Server)"),
    )

    client_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    logo_url = models.CharField(max_length=500, blank=True, default="")
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, default="public")
    client_secret = models.CharField(max_length=255, blank=True, default="")
    allowed_redirect_uris = models.TextField(
        help_text="Newline or comma-separated list of allowed callback redirect URIs."
    )
    allowed_logout_redirect_uris = models.TextField(
        blank=True,
        default="",
        help_text="Newline or comma-separated list of allowed post-logout redirect URIs."
    )
    allowed_origins = models.TextField(
        blank=True,
        default="",
        help_text="Allowed CORS origin(s) for token exchange."
    )
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_client_application"
        verbose_name = "Client Application"
        verbose_name_plural = "Client Applications"

    def __str__(self):
        return f"{self.name} ({self.client_id})"

    def get_redirect_uri_list(self):
        raw = self.allowed_redirect_uris.replace("\r\n", "\n").replace(",", "\n")
        return [line.strip() for line in raw.split("\n") if line.strip()]

    def get_logout_redirect_uri_list(self):
        raw = self.allowed_logout_redirect_uris.replace("\r\n", "\n").replace(",", "\n")
        return [line.strip() for line in raw.split("\n") if line.strip()]

    def is_redirect_uri_allowed(self, uri: str) -> bool:
        if not uri:
            return False
        allowed = self.get_redirect_uri_list()
        norm_target = uri.rstrip("/").lower()
        for item in allowed:
            if item.rstrip("/").lower() == norm_target:
                return True
        # In DEBUG / local development, allow any loopback port if path matches an allowed callback path
        if getattr(settings, "DEBUG", False):
            try:
                target_parsed = urlparse(uri)
                if target_parsed.hostname in ("localhost", "127.0.0.1"):
                    for item in allowed:
                        item_parsed = urlparse(item)
                        if (
                            item_parsed.hostname in ("localhost", "127.0.0.1")
                            and item_parsed.path.rstrip("/").lower() == target_parsed.path.rstrip("/").lower()
                        ):
                            return True
            except Exception:
                pass
        return False

    def is_logout_redirect_uri_allowed(self, uri: str) -> bool:
        if not uri:
            return True
        allowed = self.get_logout_redirect_uri_list()
        norm_target = uri.rstrip("/").lower()
        for item in allowed:
            if item.rstrip("/").lower() == norm_target:
                return True
        # In DEBUG / local development, allow any loopback port if path matches an allowed logout path
        if getattr(settings, "DEBUG", False):
            try:
                target_parsed = urlparse(uri)
                if target_parsed.hostname in ("localhost", "127.0.0.1"):
                    for item in allowed:
                        item_parsed = urlparse(item)
                        if (
                            item_parsed.hostname in ("localhost", "127.0.0.1")
                            and item_parsed.path.rstrip("/").lower() == target_parsed.path.rstrip("/").lower()
                        ):
                            return True
            except Exception:
                pass
        return False


class UserProfile(models.Model):
    """
    Extended user profile that complements the central AllUsers model.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_profile"
    )
    phone_number = models.CharField(max_length=25, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    email_verified = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile for {getattr(self.user, 'email', self.user_id)}"


class UserSession(models.Model):
    """
    Tracks active sessions across the central portal and connected SSO client apps.
    Allows users and admins to view active sessions and perform remote or global revocation.
    """
    session_id = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_sessions"
    )
    client_app = models.ForeignKey(
        ClientApplication,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sessions"
    )
    ip_address = models.CharField(max_length=50, blank=True, default="")
    user_agent = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_user_session"
        indexes = [
            models.Index(fields=["user", "is_revoked"]),
            models.Index(fields=["expires_at"]),
        ]
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def is_valid(self) -> bool:
        return not self.is_revoked and timezone.now() < self.expires_at

    def revoke(self):
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_revoked", "revoked_at"])


class AuthorizationCode(models.Model):
    """
    Short-lived authorization code issued during OIDC/OAuth2 PKCE flow.
    Expires in 5 minutes and is strictly single-use.
    """
    code = models.CharField(max_length=128, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_auth_codes"
    )
    client_app = models.ForeignKey(
        ClientApplication,
        on_delete=models.CASCADE,
        related_name="auth_codes"
    )
    redirect_uri = models.CharField(max_length=500)
    code_challenge = models.CharField(max_length=255)
    code_challenge_method = models.CharField(max_length=10, default="S256")
    nonce = models.CharField(max_length=255, blank=True, default="")
    scope = models.CharField(max_length=255, default="openid profile email")
    session = models.ForeignKey(
        UserSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="auth_codes"
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_authorization_code"
        indexes = [
            models.Index(fields=["code", "is_used"]),
        ]
        verbose_name = "Authorization Code"
        verbose_name_plural = "Authorization Codes"

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at


class EmailVerificationToken(models.Model):
    """
    Email verification tokens and 6-digit OTP codes for account verification.
    """
    token = models.CharField(max_length=128, unique=True)
    otp_code = models.CharField(max_length=10, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_email_tokens"
    )
    email = models.EmailField(max_length=255)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_email_verification"
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at


class PasswordResetToken(models.Model):
    """
    Secure, single-use password reset tokens.
    """
    token = models.CharField(max_length=128, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_password_tokens"
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_password_reset"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at


class AuthenticationAuditLog(models.Model):
    """
    Auditing records for security events, login attempts, logouts, session revocations, and SSO grants.
    Never stores plaintext passwords or secrets.
    """
    STATUS_CHOICES = (
        ("SUCCESS", "Success"),
        ("FAILURE", "Failure"),
        ("WARNING", "Warning"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounts_audit_logs"
    )
    event_type = models.CharField(max_length=50)
    client_app = models.ForeignKey(
        ClientApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )
    ip_address = models.CharField(max_length=50, blank=True, default="")
    user_agent = models.CharField(max_length=500, blank=True, default="")
    details = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUCCESS")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_audit_log"
        ordering = ["-created_at"]
        verbose_name = "Auth Audit Log"
        verbose_name_plural = "Auth Audit Logs"

    def __str__(self):
        user_display = getattr(self.user, "email", "Anonymous")
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.event_type} - {user_display} ({self.status})"
