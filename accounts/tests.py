import base64
import hashlib
import json
import secrets
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import ClientApplication, UserSession, AuthorizationCode, PasswordResetToken
from .tokens import verify_pkce_challenge


User = get_user_model()


class GlobalAccountsAndSSOTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Seed test client app
        self.app = ClientApplication.objects.create(
            client_id="test_client",
            name="Test Client App",
            client_type="public",
            allowed_redirect_uris="http://localhost:3000/auth/callback\nhttps://example.com/callback",
            allowed_logout_redirect_uris="http://localhost:3000/login",
            is_enabled=True,
        )

        # Pre-seed a test user
        self.test_user = User(
            user_id="USR_TEST001",
            username="testuser1",
            email="testuser1@example.com",
            name="Test",
            lastname="User",
            status="approved",
        )
        self.test_user.set_password("SecureP@ssw0rd123")
        self.test_user.save()

    def test_01_user_registration(self):
        """1. A user can register once."""
        res = self.client.post("/api/accounts/signup/", {
            "name": "Jane",
            "lastname": "Doe",
            "email": "jane@example.com",
            "password": "ValidPassword999!",
            "phone_number": "+1234567890",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["status"])
        self.assertEqual(res.data["user"]["email"], "jane@example.com")
        self.assertIn("access_token", res.data)

        # Verify database record
        created_user = User.objects.filter(email="jane@example.com").first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.name, "Jane")
        self.assertEqual(created_user.accounts_profile.phone_number, "+1234567890")

    def test_02_duplicate_email_rejected(self):
        """2. The same email cannot register a duplicate account."""
        res = self.client.post("/api/accounts/signup/", {
            "name": "Test Duplicate",
            "email": "testuser1@example.com",
            "password": "Password123!",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res.data["status"])

    def test_03_login_and_profile_access(self):
        """3. User can log in and access me endpoint."""
        # Test login without client_id
        res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Test login with blank string client_id
        res_blank = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
            "client_id": "",
        }, format="json")
        self.assertEqual(res_blank.status_code, status.HTTP_200_OK)
        token = res_blank.data["access_token"]
        self.assertTrue(token)

        # Test GET /api/accounts/me/
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_res = self.client.get("/api/accounts/me/")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["user"]["email"], "testuser1@example.com")

        # Test PATCH /api/accounts/me/
        patch_res = self.client.patch("/api/accounts/me/", {
            "name": "UpdatedName",
            "bio": "Full-stack engineer",
            "phone_number": "+1999888777",
        }, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["user"]["name"], "UpdatedName")
        self.assertEqual(patch_res.data["user"]["bio"], "Full-stack engineer")

    def test_04_invalid_credentials_rejected(self):
        """4. Invalid password returns 401."""
        res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "WrongPassword999",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(res.data["status"])

    def test_05_oauth_pkce_authorization_code_flow(self):
        """5. Full OIDC/OAuth2 PKCE authorization code exchange flow."""
        # Authenticate central user
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        central_token = login_res.data["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {central_token}")

        # 1. Generate PKCE verifier and challenge
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

        # 2. Authorize
        auth_res = self.client.post("/api/accounts/oauth/authorize/", {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/auth/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "xyz123",
        }, format="json")

        self.assertEqual(auth_res.status_code, status.HTTP_200_OK)
        self.assertTrue(auth_res.data["status"])
        code = auth_res.data["code"]
        self.assertTrue(code.startswith("authcode_"))
        self.assertIn("code=", auth_res.data["redirect_url"])

        # Clear credentials (client app performs token exchange as public client)
        self.client.credentials()

        # 3. Token exchange with valid PKCE verifier
        token_res = self.client.post("/api/accounts/oauth/token/", {
            "client_id": "test_client",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": "http://localhost:3000/auth/callback",
        }, format="json")

        self.assertEqual(token_res.status_code, status.HTTP_200_OK)
        self.assertTrue(token_res.data["status"])
        app_token = token_res.data["access_token"]
        self.assertEqual(token_res.data["user"]["email"], "testuser1@example.com")

        # 4. Access protected endpoint with the application-scoped token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {app_token}")
        me_res = self.client.get("/api/accounts/me/")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)

    def test_06_oauth_invalid_redirect_uri_blocked(self):
        """6. Unregistered redirect URI is blocked to prevent open-redirect."""
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access_token']}")

        res = self.client.post("/api/accounts/oauth/authorize/", {
            "client_id": "test_client",
            "redirect_uri": "https://malicious-attacker.com/steal-code",
            "code_challenge": "some_challenge",
            "code_challenge_method": "S256",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["error"], "invalid_redirect_uri")

    def test_07_oauth_pkce_mismatch_fails(self):
        """7. Invalid PKCE verifier causes token exchange to fail."""
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res.data['access_token']}")

        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

        auth_res = self.client.post("/api/accounts/oauth/authorize/", {
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/auth/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }, format="json")
        code = auth_res.data["code"]

        self.client.credentials()

        # Attempt exchange with incorrect verifier
        bad_token_res = self.client.post("/api/accounts/oauth/token/", {
            "client_id": "test_client",
            "code": code,
            "code_verifier": "WRONG_VERIFIER_STRING_THAT_DOES_NOT_MATCH",
            "redirect_uri": "http://localhost:3000/auth/callback",
        }, format="json")

        self.assertEqual(bad_token_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_token_res.data["error"], "invalid_grant")

    def test_08_session_revocation_and_global_logout(self):
        """8. Session revocation and global logout invalidate tokens immediately."""
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        token = login_res.data["access_token"]
        session_id = login_res.data["session_id"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Check session is in session list
        sess_list = self.client.get("/api/accounts/sessions/")
        self.assertEqual(sess_list.status_code, status.HTTP_200_OK)
        self.assertTrue(len(sess_list.data["sessions"]) >= 1)

        # Global logout
        logout_res = self.client.post("/api/accounts/logout-all/")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Subsequent request with old token is rejected
        rejected_res = self.client.get("/api/accounts/me/")
        self.assertIn(rejected_res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_09_password_change(self):
        """9. User can change password with old password verification."""
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        token = login_res.data["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        res = self.client.post("/api/accounts/password/change/", {
            "old_password": "SecureP@ssw0rd123",
            "new_password": "NewSecretP@ssword2026",
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify old password no longer works
        fail_login = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "SecureP@ssw0rd123",
        }, format="json")
        self.assertEqual(fail_login.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify new password works
        ok_login = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "NewSecretP@ssword2026",
        }, format="json")
        self.assertEqual(ok_login.status_code, status.HTTP_200_OK)

    def test_10_password_reset_flow(self):
        """10. Request and confirm password reset."""
        # Request reset
        req_res = self.client.post("/api/accounts/password/reset/", {
            "email": "testuser1@example.com",
        }, format="json")
        self.assertEqual(req_res.status_code, status.HTTP_200_OK)

        # Get generated token from DB
        token_obj = PasswordResetToken.objects.filter(user=self.test_user, is_used=False).first()
        self.assertIsNotNone(token_obj)

        # Confirm reset
        conf_res = self.client.post("/api/accounts/password/reset/confirm/", {
            "token": token_obj.token,
            "new_password": "ResetP@ssword999!",
        }, format="json")
        self.assertEqual(conf_res.status_code, status.HTTP_200_OK)

        # Verify login with reset password
        login_res = self.client.post("/api/accounts/login/", {
            "email": "testuser1@example.com",
            "password": "ResetP@ssword999!",
        }, format="json")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

    def test_11_openid_configuration_discovery(self):
        """11. OIDC discovery metadata endpoint."""
        res = self.client.get("/api/accounts/.well-known/openid-configuration")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("authorization_endpoint", res.data)
        self.assertIn("token_endpoint", res.data)
        self.assertIn("userinfo_endpoint", res.data)

    def test_12_google_oauth_new_and_existing_user(self):
        """12. Google OAuth sign-in for new user and existing user with PKCE."""
        # 1. New user registration via Google with PKCE
        verifier = "test-pkce-verifier-google-auth-string-1234567890"
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

        res = self.client.post("/api/accounts/google/", {
            "email": "newgoogleuser@example.com",
            "name": "Google",
            "lastname": "Tester",
            "profile": "https://example.com/avatar.jpg",
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/auth/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "state_google_123",
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["status"])
        self.assertEqual(res.data["user"]["email"], "newgoogleuser@example.com")
        self.assertIn("access_token", res.data)
        self.assertIsNotNone(res.data["code"])
        self.assertIn("code=", res.data["redirect_url"])
        self.assertIn("state=state_google_123", res.data["redirect_url"])

        # Exchange authorization code for token
        code = res.data["code"]
        token_res = self.client.post("/api/accounts/oauth/token/", {
            "client_id": "test_client",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": "http://localhost:3000/auth/callback",
        }, format="json")
        self.assertEqual(token_res.status_code, status.HTTP_200_OK)
        self.assertTrue(token_res.data["status"])

        # 2. Existing user signs in via Google
        res2 = self.client.post("/api/accounts/google/", {
            "email": "testuser1@example.com",
            "name": "Test",
            "lastname": "User",
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["status"])
        self.assertEqual(res2.data["user"]["email"], "testuser1@example.com")
        self.assertIn("access_token", res2.data)

    def test_13_skiltrix_firebase_only_and_admin_user_filtering(self):
        """13. Reject SFS Firebase tokens, accept SkilTrix Firebase RS256 tokens, and scope SkilTrix admin users."""
        from datetime import datetime, timedelta, timezone as dt_timezone
        from unittest.mock import patch
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.x509.oid import NameOID
        from django.core.cache import cache

        # Generate ephemeral RSA key + self-signed cert to test full RS256 verification
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "skiltrix-test")])
        now = datetime.now(dt_timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(hours=1))
            .sign(private_key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        def make_jwt(project_id: str, email: str, kid: str = "test-kid-1") -> str:
            def b64(data: bytes) -> str:
                return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

            hdr = b64(json.dumps({"alg": "RS256", "typ": "JWT", "kid": kid}).encode("utf-8"))
            pld = b64(json.dumps({
                "aud": project_id,
                "iss": f"https://securetoken.google.com/{project_id}",
                "sub": "firebase-uid-123",
                "email": email,
                "exp": int(now.timestamp()) + 3600,
            }).encode("utf-8"))
            sig_input = f"{hdr}.{pld}".encode("ascii")
            sig = private_key.sign(sig_input, padding.PKCS1v15(), hashes.SHA256())
            return f"{hdr}.{pld}.{b64(sig)}"

        cache.delete("skiltrix_firebase_x509_certs")
        with patch("accounts.tokens._get_firebase_public_certs", return_value={"test-kid-1": cert_pem}):
            # 1. SFS Firebase token rejected on Google and GitHub endpoints
            sfs_token = make_jwt("sfs-blueprints-21", "sfsuser@example.com")
            bad_google = self.client.post("/api/accounts/google/", {
                "email": "sfsuser@example.com",
                "name": "SFS",
                "id_token": sfs_token,
            }, format="json")
            self.assertEqual(bad_google.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertFalse(bad_google.data["status"])

            bad_github = self.client.post("/api/accounts/github/", {
                "email": "sfsuser@example.com",
                "name": "SFS",
                "id_token": sfs_token,
            }, format="json")
            self.assertEqual(bad_github.status_code, status.HTTP_401_UNAUTHORIZED)

            # 2. SkilTrix Firebase token succeeds and tags new SkilTrix client user with platform_name="skiltrix"
            ClientApplication.objects.create(
                client_id="skiltrix",
                name="SkilTrix",
                client_type="public",
                allowed_redirect_uris="http://localhost:8443/auth/callback",
                is_enabled=True,
            )
            sk_token = make_jwt("skiltrix", "skstudent@example.com")
            ok_google = self.client.post("/api/accounts/firebase/", {
                "email": "skstudent@example.com",
                "name": "SkStudent",
                "client_id": "skiltrix",
                "id_token": sk_token,
            }, format="json")
            self.assertEqual(ok_google.status_code, status.HTTP_200_OK)
            created_sk = User.objects.get(email="skstudent@example.com")
            self.assertEqual(created_sk.platform_name, "skiltrix")

        # 3. Admin users filtering: app=skiltrix excludes pure sfs_blueprints users
        User.objects.create(
            user_id="USR_SFS_ONLY",
            username="sfsonly",
            email="sfsonly@example.com",
            name="SFS Only Player",
            platform="android",
            platform_name="sfs_blueprints",
            type="user",
            status="approved",
        )
        sk_list = self.client.get("/api/admin/users/?app=skiltrix&limit=50")
        self.assertEqual(sk_list.status_code, status.HTTP_200_OK)
        sk_emails = [u["email"] for u in sk_list.json()["users"]]
        self.assertIn("skstudent@example.com", sk_emails)
        self.assertNotIn("sfsonly@example.com", sk_emails)

        sfs_list = self.client.get("/api/admin/users/?app=sfs&limit=50")
        self.assertEqual(sfs_list.status_code, status.HTTP_200_OK)
        sfs_emails = [u["email"] for u in sfs_list.json()["users"]]
        self.assertIn("sfsonly@example.com", sfs_emails)
        self.assertNotIn("skstudent@example.com", sfs_emails)

