from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


TOKEN_SALT = "skiltrix.api-access"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 14


def issue_access_token(user):
    """Create a tamper-proof, time-limited API token for an authenticated user."""
    return signing.TimestampSigner(salt=TOKEN_SALT).sign(str(user.pk))


class SignedAccessTokenAuthentication(BaseAuthentication):
    """Authenticate API requests using tokens returned by signin/signup."""

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if parts[0].lower() != b"bearer":
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid authorization header.")

        try:
            user_pk = signing.TimestampSigner(salt=TOKEN_SALT).unsign(
                parts[1].decode("utf-8"), max_age=TOKEN_MAX_AGE_SECONDS
            )
            user = get_user_model().objects.get(pk=user_pk)
        except (UnicodeDecodeError, signing.BadSignature, get_user_model().DoesNotExist):
            raise AuthenticationFailed("Access token is invalid or expired.")

        if hasattr(user, "is_active") and not user.is_active:
            raise AuthenticationFailed("This account is inactive.")
        return user, None
