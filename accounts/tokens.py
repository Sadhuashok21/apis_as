import base64
import hashlib
import json
import logging
import secrets
from datetime import timedelta
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.utils import timezone


logger = logging.getLogger(__name__)
SKILTRIX_FIREBASE_PROJECT_ID = getattr(settings, "SKILTRIX_FIREBASE_PROJECT_ID", "skiltrix")
FIREBASE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
FIREBASE_CERTS_CACHE_KEY = "skiltrix_firebase_x509_certs"


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


def _decode_jwt_segment(segment: str) -> bytes:
    rem = len(segment) % 4
    if rem:
        segment += "=" * (4 - rem)
    return base64.urlsafe_b64decode(segment.encode("ascii"))


def _get_firebase_public_certs() -> dict | None:
    cached = cache.get(FIREBASE_CERTS_CACHE_KEY)
    if isinstance(cached, dict) and cached:
        return cached
    try:
        resp = requests.get(FIREBASE_CERTS_URL, timeout=3)
        if resp.status_code == 200:
            certs = resp.json()
            if isinstance(certs, dict) and certs:
                cache.set(FIREBASE_CERTS_CACHE_KEY, certs, timeout=3600)
                return certs
    except requests.RequestException as exc:
        logger.warning("Unable to fetch Firebase public certificates: %s", exc)
    return None


def verify_skiltrix_firebase_id_token(id_token: str) -> dict:
    """
    Verify that a Firebase ID token was issued for the SkilTrix Firebase project
    (and reject legacy SFS Firebase tokens or expired/tampered tokens).
    """
    parts = (id_token or "").split(".")
    if len(parts) != 3:
        raise ValueError("Invalid Firebase ID token format.")

    try:
        header = json.loads(_decode_jwt_segment(parts[0]).decode("utf-8"))
        payload = json.loads(_decode_jwt_segment(parts[1]).decode("utf-8"))
        signature = _decode_jwt_segment(parts[2])
    except Exception as exc:
        raise ValueError("Malformed Firebase ID token.") from exc

    expected_iss = f"https://securetoken.google.com/{SKILTRIX_FIREBASE_PROJECT_ID}"
    aud = str(payload.get("aud") or "").strip()
    iss = str(payload.get("iss") or "").strip()
    if aud != SKILTRIX_FIREBASE_PROJECT_ID or iss != expected_iss:
        raise ValueError(
            f"Only SkilTrix Firebase authentication ({SKILTRIX_FIREBASE_PROJECT_ID}) is supported."
        )

    now_ts = int(timezone.now().timestamp())
    exp = int(payload.get("exp") or 0)
    if exp + 300 < now_ts:
        raise ValueError("Firebase ID token has expired. Please sign in again.")

    if not payload.get("sub"):
        raise ValueError("Firebase ID token is missing subject identifier.")

    certs = _get_firebase_public_certs()
    if certs:
        kid = header.get("kid")
        pem = certs.get(kid) if kid else None
        if not pem:
            raise ValueError("Unrecognized Firebase token signing key.")
        try:
            cert = x509.load_pem_x509_certificate(pem.encode("utf-8"))
            signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
            cert.public_key().verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        except Exception as exc:
            raise ValueError("Firebase ID token signature verification failed.") from exc

    return payload
