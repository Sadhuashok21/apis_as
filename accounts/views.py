import json
import secrets
import uuid
import hashlib
import re
from hmac import compare_digest
from datetime import timedelta
from urllib.parse import urlparse, urlencode

from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, login as django_login, logout as django_logout
from django.contrib.auth.hashers import check_password, identify_hasher, is_password_usable, make_password
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    ClientApplication,
    UserProfile,
    UserSession,
    AuthorizationCode,
    EmailVerificationToken,
    PasswordResetToken,
    AuthenticationAuditLog,
)
from .serializers import (
    UserSerializer,
    SignupSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UpdateProfileSerializer,
    ClientApplicationSerializer,
    UserSessionSerializer,
    OAuthAuthorizeSerializer,
    OAuthTokenSerializer,
)
from .tokens import (
    generate_secure_token,
    generate_otp_code,
    verify_pkce_challenge,
    issue_sso_access_token,
)


User = get_user_model()


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")[:490]


def log_audit_event(request, event_type: str, user=None, client_app=None, status_str="SUCCESS", details=""):
    try:
        AuthenticationAuditLog.objects.create(
            user=user,
            event_type=event_type,
            client_app=client_app,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            status=status_str,
            details=details[:1000] if details else "",
        )
    except Exception:
        pass


def create_user_session(user, client_app=None, ip="", user_agent="", duration_days=14):
    session_id = f"sess_{uuid.uuid4().hex}"
    expires_at = timezone.now() + timedelta(days=duration_days)
    session = UserSession.objects.create(
        session_id=session_id,
        user=user,
        client_app=client_app,
        ip_address=ip[:49],
        user_agent=user_agent[:490],
        expires_at=expires_at,
    )
    return session


def verify_account_password(user, raw_password):
    """Verify current Django hashes and transparently upgrade legacy SFS passwords."""
    encoded = user.password or ""
    if not encoded or not is_password_usable(encoded):
        return False

    try:
        identify_hasher(encoded)
    except ValueError:
        # Older account-creation and password-change endpoints stored plain
        # text. The old SFS sign-in also used an MD5 digest in some deployments.
        # Accept either legacy format once, then replace it with Django's
        # configured password hash before issuing a session.
        legacy_candidates = [raw_password]
        if re.fullmatch(r"[0-9a-fA-F]{32}", encoded):
            legacy_candidates.insert(0, hashlib.md5(raw_password.encode("utf-8")).hexdigest())
        if not any(compare_digest(candidate, encoded) for candidate in legacy_candidates):
            return False
        user.set_password(raw_password)
        user.save(update_fields=["password"])
        return True

    return check_password(raw_password, encoded)


# ============================================================================
# Central Auth Endpoints
# ============================================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def accounts_signup(request):
    """
    Global registration endpoint. Creates the central AllUsers record and
    associated UserProfile.
    """
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        log_audit_event(
            request, "SIGNUP",
            status_str="FAILURE",
            details=json.dumps(serializer.errors)
        )
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    email = data["email"]
    name = data["name"]
    lastname = data.get("lastname", "")
    username = data.get("username") or email.split("@")[0] + "_" + uuid.uuid4().hex[:6]
    phone_number = data.get("phone_number", "")
    password = data["password"]

    user_id = f"USR_{uuid.uuid4().hex[:12].upper()}"

    user = User(
        user_id=user_id,
        username=username,
        email=email,
        name=name,
        lastname=lastname,
        platform=data.get("platform", "web"),
        platform_name=data.get("platform_name", "ascentracore"),
        type=data.get("type", "user"),
        status="approved",
        ip=get_client_ip(request),
    )
    user.set_password(password)
    user.save()

    # Create extended profile
    UserProfile.objects.create(
        user=user,
        phone_number=phone_number,
    )

    # Establish central session
    session = create_user_session(
        user=user,
        client_app=None,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    token = issue_sso_access_token(user, client_id="central", session_id=session.session_id)

    log_audit_event(request, "SIGNUP", user=user, details="New user account registered")

    user_data = UserSerializer(user).data
    return Response({
        "status": True,
        "message": "Account created successfully.",
        "user": user_data,
        "access_token": token,
        "token_type": "Bearer",
        "session_id": session.session_id,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def accounts_login(request):
    """
    Global login endpoint. Authenticates with email or username and password.
    Creates a central session and issues an SSO access token.
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "status": False,
            "message": "The login request is incomplete or invalid.",
            "errors": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    ident = serializer.validated_data["email"].strip()
    raw_password = serializer.validated_data["password"]
    client_id = serializer.validated_data.get("client_id", "").strip()

    client_app = None
    if client_id:
        client_app = ClientApplication.objects.filter(client_id=client_id, is_enabled=True).first()

    user = User.objects.filter(Q(email__iexact=ident) | Q(username__iexact=ident)).first()

    if not user or not verify_account_password(user, raw_password):
        log_audit_event(
            request, "LOGIN_FAILED",
            client_app=client_app,
            status_str="FAILURE",
            details=f"Invalid credentials for '{ident}'"
        )
        return Response({
            "status": False,
            "message": "Invalid email or password."
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Check account status
    status_val = getattr(user, "status", "approved")
    if status_val in ("suspended", "blocked", "disabled"):
        log_audit_event(request, "LOGIN_BLOCKED", user=user, client_app=client_app, status_str="WARNING")
        return Response({
            "status": False,
            "message": f"This account is {status_val}. Please contact support."
        }, status=status.HTTP_403_FORBIDDEN)

    # Create session
    session = create_user_session(
        user=user,
        client_app=client_app,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    token = issue_sso_access_token(
        user,
        client_id=client_app.client_id if client_app else "central",
        session_id=session.session_id
    )

    # Sync Django session if session middleware active
    if hasattr(request, "session"):
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    log_audit_event(request, "LOGIN", user=user, client_app=client_app, details="User login successful")

    return Response({
        "status": True,
        "message": "Login successful.",
        "user": UserSerializer(user).data,
        "access_token": token,
        "token_type": "Bearer",
        "session_id": session.session_id,
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def accounts_me(request):
    """
    Get or update the current authenticated user profile.
    """
    user = request.user
    if request.method == "GET":
        return Response({
            "status": True,
            "user": UserSerializer(user).data
        })

    # PATCH
    serializer = UpdateProfileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    vd = serializer.validated_data
    if "name" in vd:
        user.name = vd["name"]
    if "lastname" in vd:
        user.lastname = vd["lastname"]
    if "profile" in vd:
        user.profile = vd["profile"]
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    if "phone_number" in vd:
        profile.phone_number = vd["phone_number"]
    if "bio" in vd:
        profile.bio = vd["bio"]
    profile.save()

    log_audit_event(request, "PROFILE_UPDATED", user=user, details="User updated profile details")

    return Response({
        "status": True,
        "message": "Profile updated successfully.",
        "user": UserSerializer(user).data
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accounts_logout(request):
    """
    Logout from the current application / session.
    """
    session_id = getattr(request, "auth_session_id", None)
    if session_id:
        UserSession.objects.filter(session_id=session_id).update(
            is_revoked=True, revoked_at=timezone.now()
        )

    if hasattr(request, "session"):
        django_logout(request)

    log_audit_event(request, "LOGOUT", user=request.user, details="Logged out from current session")

    return Response({"status": True, "message": "Successfully logged out."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accounts_logout_all(request):
    """
    Global logout: Invalidate all sessions across central accounts and all connected applications.
    """
    user = request.user
    UserSession.objects.filter(user=user, is_revoked=False).update(
        is_revoked=True, revoked_at=timezone.now()
    )

    if hasattr(request, "session"):
        django_logout(request)

    log_audit_event(request, "GLOBAL_LOGOUT", user=user, details="All active sessions revoked")

    return Response({"status": True, "message": "All sessions revoked. Logged out globally."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accounts_change_password(request):
    """
    Change password for the current authenticated user.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    if not check_password(serializer.validated_data["old_password"], user.password):
        log_audit_event(request, "PASSWORD_CHANGE_FAILED", user=user, status_str="FAILURE")
        return Response({"status": False, "message": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(serializer.validated_data["new_password"])
    user.save()

    # Optionally revoke all other sessions on password change
    UserSession.objects.filter(user=user, is_revoked=False).exclude(
        session_id=getattr(request, "auth_session_id", None)
    ).update(is_revoked=True, revoked_at=timezone.now())

    log_audit_event(request, "PASSWORD_CHANGED", user=user, details="Password changed successfully")

    return Response({"status": True, "message": "Password changed successfully."})


@api_view(["POST"])
@permission_classes([AllowAny])
def accounts_password_reset_request(request):
    """
    Request a password reset link. Returns generic response to avoid email enumeration.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data["email"].strip().lower()
    user = User.objects.filter(email__iexact=email).first()

    if user:
        token_str = generate_secure_token(48)
        PasswordResetToken.objects.create(
            token=token_str,
            user=user,
            expires_at=timezone.now() + timedelta(hours=2),
        )
        # Attempt sending reset email
        try:
            reset_url = f"{getattr(settings, 'ACCOUNTS_PORTAL_URL', 'http://localhost:5174')}/forgot-password?token={token_str}"
            send_mail(
                subject="Reset Your Ascentracore Password",
                message=f"Hi {user.name},\n\nUse the link below to reset your password:\n{reset_url}\n\nThis link expires in 2 hours.",
                from_email=getattr(settings, "EMAIL_HOST_USER", "noreply") + "@ascentracoresolutions.com",
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        log_audit_event(request, "PASSWORD_RESET_REQUESTED", user=user)

    # Always return success to prevent email enumeration
    return Response({
        "status": True,
        "message": "If an account exists with that email, a password reset link has been sent."
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def accounts_password_reset_confirm(request):
    """
    Confirm password reset with valid single-use token.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    token_str = serializer.validated_data["token"].strip()
    new_password = serializer.validated_data["new_password"]

    reset_obj = PasswordResetToken.objects.filter(token=token_str).first()
    if not reset_obj or not reset_obj.is_valid():
        return Response({
            "status": False,
            "message": "Reset link is invalid or has expired."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = reset_obj.user
    user.set_password(new_password)
    user.save()

    reset_obj.is_used = True
    reset_obj.save()

    # Invalidate all existing sessions
    UserSession.objects.filter(user=user).update(is_revoked=True, revoked_at=timezone.now())

    log_audit_event(request, "PASSWORD_RESET_COMPLETED", user=user)

    return Response({"status": True, "message": "Password has been successfully reset. Please log in with your new password."})


# ============================================================================
# Applications & Sessions Management
# ============================================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accounts_list_applications(request):
    """
    List connected applications registered in the SSO ecosystem.
    """
    apps = ClientApplication.objects.filter(is_enabled=True)
    return Response({
        "status": True,
        "applications": ClientApplicationSerializer(apps, many=True).data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accounts_list_sessions(request):
    """
    List active user sessions across all connected applications.
    """
    sessions = UserSession.objects.filter(
        user=request.user,
        is_revoked=False,
        expires_at__gt=timezone.now()
    ).order_by("-last_active_at")

    serializer = UserSessionSerializer(sessions, many=True, context={"request": request})
    return Response({
        "status": True,
        "sessions": serializer.data
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def accounts_revoke_session(request, session_id):
    """
    Revoke a specific session remotely.
    """
    session = UserSession.objects.filter(session_id=session_id, user=request.user).first()
    if not session:
        return Response({"status": False, "message": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    session.revoke()
    log_audit_event(request, "SESSION_REVOKED", user=request.user, details=f"Revoked session {session_id}")
    return Response({"status": True, "message": "Session revoked."})


# ============================================================================
# Single Sign-On (SSO) OAuth2 / OIDC PKCE Endpoints
# ============================================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def accounts_sso_check(request):
    """
    Check if the user has an active central session on the backend.
    Used by client apps (skiltrix, admin, main, policies) to perform silent SSO detection.
    If authenticated via session cookie or Bearer token, issues an access token for the client app.
    """
    user = None
    if request.user and request.user.is_authenticated:
        user = request.user
    elif hasattr(request, "session") and request.user and request.user.is_authenticated:
        user = request.user

    if user and user.is_authenticated:
        client_id = request.query_params.get("client_id", "").strip() or "central"
        client_app = ClientApplication.objects.filter(client_id=client_id, is_enabled=True).first()

        session = create_user_session(
            user=user,
            client_app=client_app,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        token = issue_sso_access_token(
            user=user,
            client_id=client_app.client_id if client_app else "central",
            session_id=session.session_id,
            scopes=["openid", "profile", "email"],
        )

        return Response({
            "status": True,
            "authenticated": True,
            "user": UserSerializer(user).data,
            "access_token": token,
            "session_id": session.session_id,
        })

    return Response({
        "status": True,
        "authenticated": False,
        "user": None,
    })



@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_authorize(request):
    """
    OAuth2 / OIDC Authorization endpoint (called by central accounts login).
    Generates an Authorization Code with PKCE challenge binding and returns
    redirect URL to the client application.
    """
    serializer = OAuthAuthorizeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    client_id = serializer.validated_data["client_id"]
    redirect_uri = serializer.validated_data["redirect_uri"]
    code_challenge = serializer.validated_data["code_challenge"]
    code_challenge_method = serializer.validated_data.get("code_challenge_method", "S256")
    state = serializer.validated_data.get("state", "")
    nonce = serializer.validated_data.get("nonce", "")
    scope = serializer.validated_data.get("scope", "openid profile email")

    # 1. Validate client application
    client_app = ClientApplication.objects.filter(client_id=client_id, is_enabled=True).first()
    if not client_app:
        return Response({
            "status": False,
            "error": "invalid_client",
            "message": f"Client application '{client_id}' is not registered or is disabled."
        }, status=status.HTTP_400_BAD_REQUEST)

    # 2. Validate redirect_uri against client's allowlist
    if not client_app.is_redirect_uri_allowed(redirect_uri):
        log_audit_event(
            request, "OAUTH_INVALID_REDIRECT_URI",
            client_app=client_app,
            status_str="WARNING",
            details=f"Attempted unregistered redirect_uri: {redirect_uri}"
        )
        return Response({
            "status": False,
            "error": "invalid_redirect_uri",
            "message": "The provided redirect_uri is not authorized for this application."
        }, status=status.HTTP_400_BAD_REQUEST)

    # 3. User must be authenticated to authorize
    if not request.user or not request.user.is_authenticated:
        return Response({
            "status": False,
            "error": "login_required",
            "message": "Authentication required before authorizing client."
        }, status=status.HTTP_401_UNAUTHORIZED)

    user = request.user
    if getattr(user, "status", "approved") in ("suspended", "blocked", "disabled"):
        return Response({
            "status": False,
            "error": "access_denied",
            "message": "User account is suspended."
        }, status=status.HTTP_403_FORBIDDEN)

    # 4. Create short-lived Authorization Code (5 minutes expiry)
    code = f"authcode_{secrets.token_urlsafe(32)}"
    expires_at = timezone.now() + timedelta(minutes=5)

    auth_code = AuthorizationCode.objects.create(
        code=code,
        user=user,
        client_app=client_app,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
        scope=scope,
        expires_at=expires_at,
    )

    log_audit_event(
        request, "OAUTH_CODE_ISSUED",
        user=user,
        client_app=client_app,
        details=f"Issued authorization code for client '{client_id}'"
    )

    # Construct redirect URL
    params = {"code": code}
    if state:
        params["state"] = state
    query_str = urlencode(params)
    separator = "&" if "?" in redirect_uri else "?"
    redirect_url = f"{redirect_uri}{separator}{query_str}"

    return Response({
        "status": True,
        "code": code,
        "state": state,
        "redirect_url": redirect_url,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_token(request):
    """
    OAuth2 / OIDC Token Exchange endpoint.
    Exchanges Authorization Code + PKCE code_verifier for an application-scoped access token.
    """
    serializer = OAuthTokenSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    client_id = serializer.validated_data["client_id"]
    code_str = serializer.validated_data["code"]
    code_verifier = serializer.validated_data["code_verifier"]
    redirect_uri = serializer.validated_data["redirect_uri"]

    client_app = ClientApplication.objects.filter(client_id=client_id, is_enabled=True).first()
    if not client_app:
        return Response({
            "status": False,
            "error": "invalid_client",
            "message": "Invalid client application."
        }, status=status.HTTP_400_BAD_REQUEST)

    auth_code = AuthorizationCode.objects.filter(code=code_str, client_app=client_app).first()
    if not auth_code:
        log_audit_event(request, "OAUTH_TOKEN_FAILED", client_app=client_app, status_str="FAILURE", details="Authorization code not found")
        return Response({
            "status": False,
            "error": "invalid_grant",
            "message": "Authorization code is invalid or has expired."
        }, status=status.HTTP_400_BAD_REQUEST)

    if auth_code.is_used:
        # Potential replay attack! Revoke code and alert
        log_audit_event(
            request, "OAUTH_CODE_REPLAY_ATTACK",
            user=auth_code.user,
            client_app=client_app,
            status_str="WARNING",
            details="Attempted reuse of already-consumed authorization code"
        )
        return Response({
            "status": False,
            "error": "invalid_grant",
            "message": "Authorization code has already been used."
        }, status=status.HTTP_400_BAD_REQUEST)

    if timezone.now() > auth_code.expires_at:
        return Response({
            "status": False,
            "error": "invalid_grant",
            "message": "Authorization code has expired."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate redirect_uri matches the one provided during authorize
    if auth_code.redirect_uri.rstrip("/").lower() != redirect_uri.rstrip("/").lower():
        return Response({
            "status": False,
            "error": "invalid_grant",
            "message": "redirect_uri does not match original authorization request."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Validate PKCE verifier
    if not verify_pkce_challenge(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
        log_audit_event(
            request, "OAUTH_PKCE_FAILED",
            user=auth_code.user,
            client_app=client_app,
            status_str="FAILURE",
            details="PKCE code_verifier challenge mismatch"
        )
        return Response({
            "status": False,
            "error": "invalid_grant",
            "message": "PKCE verification failed: code_verifier does not match code_challenge."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Consume authorization code
    auth_code.is_used = True
    auth_code.save(update_fields=["is_used"])

    user = auth_code.user

    # Create active session bound to this client app
    session = create_user_session(
        user=user,
        client_app=client_app,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    access_token = issue_sso_access_token(
        user=user,
        client_id=client_app.client_id,
        session_id=session.session_id,
        scopes=auth_code.scope.split(),
    )

    log_audit_event(
        request, "OAUTH_TOKEN_ISSUED",
        user=user,
        client_app=client_app,
        details=f"Issued access token for application '{client_app.name}'"
    )

    return Response({
        "status": True,
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 60 * 60 * 24 * 7,
        "scope": auth_code.scope,
        "user": UserSerializer(user).data,
        "session_id": session.session_id,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def openid_configuration(request):
    """
    OpenID Connect Discovery 1.0 endpoint.
    Exposes metadata, issuer, authorization_endpoint, token_endpoint, userinfo_endpoint.
    """
    base_url = request.build_absolute_uri("/").rstrip("/")
    return Response({
        "issuer": f"{base_url}/api/accounts",
        "authorization_endpoint": f"{getattr(settings, 'ACCOUNTS_PORTAL_URL', 'http://localhost:5174')}/login",
        "token_endpoint": f"{base_url}/api/accounts/oauth/token/",
        "userinfo_endpoint": f"{base_url}/api/accounts/me/",
        "end_session_endpoint": f"{base_url}/api/accounts/logout-all/",
        "response_types_supported": ["code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def accounts_google_auth(request):
    """
    Authenticate or register a user via Google Firebase OAuth credential.
    Supports single sign-on across all applications and optional OAuth/PKCE authorization flow.
    """
    data = request.data
    email = data.get("email", "").strip().lower()
    if not email:
        return Response({"status": False, "message": "Email is required from Google authentication."}, status=status.HTTP_400_BAD_REQUEST)

    name = data.get("name", "").strip()
    lastname = data.get("lastname", "").strip()
    profile_pic = data.get("profile", "") or data.get("photoURL", "")
    client_id = data.get("client_id", "").strip()
    redirect_uri = data.get("redirect_uri", "").strip()
    code_challenge = data.get("code_challenge", "").strip()
    code_challenge_method = data.get("code_challenge_method", "S256").strip()
    state = data.get("state", "").strip()
    scope = data.get("scope", "openid profile email").strip()

    client_app = None
    if client_id:
        client_app = ClientApplication.objects.filter(client_id=client_id, is_enabled=True).first()

    # Look up user by email
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        base_username = (email.split("@")[0] or "user").lower()
        candidate = base_username
        idx = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base_username}{idx}"
            idx += 1

        user_id = f"USR_{uuid.uuid4().hex[:12].upper()}"
        user = User(
            user_id=user_id,
            username=candidate[:50],
            email=email[:50],
            name=(name or candidate)[:50],
            lastname=lastname[:50],
            profile=(profile_pic or "profile.webp")[:500],
            platform="web",
            platform_name="google_oauth",
            type="user",
            status="approved",
            ip=get_client_ip(request)[:50],
        )
        user.set_unusable_password()
        user.save()

        UserProfile.objects.create(
            user=user,
            email_verified=True,
        )
        log_audit_event(request, "GOOGLE_SIGNUP", user=user, client_app=client_app, details=f"New user registered via Google: {email}")
    else:
        # Check account status
        status_val = getattr(user, "status", "approved")
        if status_val in ("suspended", "blocked", "disabled"):
            log_audit_event(request, "GOOGLE_LOGIN_BLOCKED", user=user, client_app=client_app, status_str="WARNING")
            return Response({
                "status": False,
                "message": f"This account is {status_val}. Please contact support."
            }, status=status.HTTP_403_FORBIDDEN)

        # Update avatar or name if missing
        updated_fields = []
        if profile_pic and not user.profile:
            user.profile = profile_pic
            updated_fields.append("profile")
        if not user.name and name:
            user.name = name
            updated_fields.append("name")
        if not user.lastname and lastname:
            user.lastname = lastname
            updated_fields.append("lastname")
        if updated_fields:
            user.save(update_fields=updated_fields)

        # Ensure UserProfile exists & email verified
        profile_obj, _ = UserProfile.objects.get_or_create(user=user)
        if not profile_obj.email_verified:
            profile_obj.email_verified = True
            profile_obj.save(update_fields=["email_verified"])

        log_audit_event(request, "GOOGLE_LOGIN", user=user, client_app=client_app, details=f"User signed in via Google: {email}")

    # Create active session
    session = create_user_session(
        user=user,
        client_app=client_app,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    token = issue_sso_access_token(
        user,
        client_id=client_app.client_id if client_app else "central",
        session_id=session.session_id,
        scopes=["openid", "profile", "email"],
    )

    # Sync Django session if session middleware active
    if hasattr(request, "session"):
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # If OAuth PKCE authorization parameters are provided, issue authorization code and redirect_url
    redirect_url = None
    code = None
    if client_app and redirect_uri and code_challenge:
        if not client_app.is_redirect_uri_allowed(redirect_uri):
            return Response({
                "status": False,
                "error": "invalid_redirect_uri",
                "message": f"Redirect URI '{redirect_uri}' is not authorized for application '{client_app.client_id}'."
            }, status=status.HTTP_400_BAD_REQUEST)

        code = generate_secure_token(32)
        AuthorizationCode.objects.create(
            code=code,
            client_app=client_app,
            user=user,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method or "S256",
            scope=scope or "openid profile email",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        params = {"code": code}
        if state:
            params["state"] = state
        query_str = urlencode(params)
        separator = "&" if "?" in redirect_uri else "?"
        redirect_url = f"{redirect_uri}{separator}{query_str}"

    return Response({
        "status": True,
        "message": "Google authentication successful.",
        "user": UserSerializer(user).data,
        "access_token": token,
        "token_type": "Bearer",
        "session_id": session.session_id,
        "code": code,
        "state": state,
        "redirect_url": redirect_url,
    })

