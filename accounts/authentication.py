from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from skiltrix.authentication import TOKEN_SALT, TOKEN_MAX_AGE_SECONDS
from .tokens import verify_sso_access_token
from .models import UserSession


class GlobalAccountsAuthentication(BaseAuthentication):
    """
    Centralized DRF Authentication backend for all 5 frontend applications.
    Supports:
    1. Modern SSO tokens (issued via OIDC/OAuth2 PKCE flow or central signin)
       with real-time active session validation and revocation checks.
    2. Legacy TimestampSigner tokens from skiltrix.authentication for full backward compatibility.
    """

    def authenticate(self, request):
        auth_header = get_authorization_header(request).split()
        if not auth_header:
            return None

        if auth_header[0].lower() != b"bearer":
            return None

        if len(auth_header) != 2:
            raise AuthenticationFailed("Invalid authorization header format. Expected 'Bearer <token>'.")

        raw_token = auth_header[1].decode("utf-8")
        User = get_user_model()

        # 1. Attempt Modern SSO token decode
        try:
            payload = verify_sso_access_token(raw_token)
            user_pk = payload.get("uid")
            session_id = payload.get("sid")
            client_id = payload.get("cid")

            user = User.objects.get(pk=user_pk)

            # Check if associated session was revoked
            if session_id:
                session = UserSession.objects.filter(session_id=session_id).first()
                if session and not session.is_valid():
                    raise AuthenticationFailed("Your session has been revoked or expired. Please sign in again.")
                elif session:
                    # Update activity timestamp
                    session.save(update_fields=["last_active_at"])

            # Check user account status
            self._validate_user_status(user)

            # Attach auth metadata to request
            request.auth_client_id = client_id
            request.auth_session_id = session_id
            return (user, raw_token)

        except (signing.BadSignature, signing.SignatureExpired):
            # Not an SSO token or expired, try legacy token format
            pass
        except User.DoesNotExist:
            raise AuthenticationFailed("User account associated with this token no longer exists.")

        # 2. Backward compatibility: Attempt legacy skiltrix token decode
        try:
            legacy_pk = signing.TimestampSigner(salt=TOKEN_SALT).unsign(
                raw_token, max_age=TOKEN_MAX_AGE_SECONDS
            )
            legacy_user = User.objects.get(pk=legacy_pk)
            self._validate_user_status(legacy_user)
            return (legacy_user, raw_token)
        except (UnicodeDecodeError, signing.BadSignature, signing.SignatureExpired, User.DoesNotExist):
            raise AuthenticationFailed("Access token is invalid or expired.")

    def _validate_user_status(self, user):
        if hasattr(user, "is_active") and not user.is_active:
            raise AuthenticationFailed("This account is inactive.")

        status = getattr(user, "status", "approved")
        if status in ("suspended", "blocked", "disabled"):
            raise AuthenticationFailed(f"Account is {status}. Please contact administrator.")
