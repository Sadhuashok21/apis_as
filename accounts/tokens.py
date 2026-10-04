import base64
import hashlib
import json
import secrets
from datetime import timedelta
from django.conf import settings
from django.core import signing
from django.utils import timezone


SSO_TOKEN_SALT = "accounts.sso.v1"
SSO_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days default access token


def generate_secure_token(length: int = 32) -> str:
    """Generate a URL-safe cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_otp_code(digits: int = 6) -> str:
    """Generate a 6-digit numeric OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(digits))


def verify_pkce_challenge(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """
    Verify PKCE code_verifier against code_challenge according to RFC 7636.
    """
    if not code_verifier or not code_challenge:
        return False

    if method == "plain":
        return secrets.compare_digest(code_verifier, code_challenge)

    if method == "S256":
        # Calculate SHA-256 of code_verifier
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        # Base64-url encode without trailing '=' padding
        calculated_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        clean_target = code_challenge.rstrip("=")
        return secrets.compare_digest(calculated_challenge, clean_target)

    return False


def issue_sso_access_token(user, client_id: str, session_id: str, scopes: list = None) -> str:
    """
    Issue a tamper-proof signed SSO access token containing user identity,
    client application ID, session identifier, and scopes.
    """
    payload = {
        "uid": str(user.pk),
        "cid": client_id,
        "sid": session_id,
        "scp": scopes or ["openid", "profile", "email"],
        "iat": int(timezone.now().timestamp()),
    }
    return signing.TimestampSigner(salt=SSO_TOKEN_SALT).sign_object(payload)


def verify_sso_access_token(token: str, max_age: int = SSO_TOKEN_MAX_AGE_SECONDS) -> dict:
    """
    Verify and unsign an SSO access token. Returns decoded dict if valid.
    Raises signing.BadSignature or signing.SignatureExpired if invalid.
    """
    return signing.TimestampSigner(salt=SSO_TOKEN_SALT).unsign_object(token, max_age=max_age)
