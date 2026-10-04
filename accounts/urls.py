from django.urls import path
from . import views

urlpatterns = [
    # Core Authentication
    path("signup/", views.accounts_signup, name="accounts_signup"),
    path("login/", views.accounts_login, name="accounts_login"),
    path("google/", views.accounts_google_auth, name="accounts_google_auth"),
    path("logout/", views.accounts_logout, name="accounts_logout"),
    path("logout-all/", views.accounts_logout_all, name="accounts_logout_all"),
    path("me/", views.accounts_me, name="accounts_me"),

    # Password Management
    path("password/change/", views.accounts_change_password, name="accounts_change_password"),
    path("password/reset/", views.accounts_password_reset_request, name="accounts_password_reset_request"),
    path("password/reset/confirm/", views.accounts_password_reset_confirm, name="accounts_password_reset_confirm"),

    # Application & Session Management
    path("applications/", views.accounts_list_applications, name="accounts_list_applications"),
    path("sessions/", views.accounts_list_sessions, name="accounts_list_sessions"),
    path("sessions/<str:session_id>/", views.accounts_revoke_session, name="accounts_revoke_session"),

    # Single Sign-On (SSO) OAuth2 / OIDC Flow
    path("sso/check/", views.accounts_sso_check, name="accounts_sso_check"),
    path("oauth/authorize/", views.oauth_authorize, name="oauth_authorize"),
    path("oauth/token/", views.oauth_token, name="oauth_token"),

    # OIDC Discovery
    path(".well-known/openid-configuration", views.openid_configuration, name="openid_configuration"),
]
