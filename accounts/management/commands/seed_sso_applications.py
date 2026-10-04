from django.core.management.base import BaseCommand
from accounts.models import ClientApplication


APPLICATIONS = [
    {
        "client_id": "skiltrix",
        "name": "SkilTrix Online IDE & Learning Platform",
        "description": "Full-stack cloud IDE, coding practice, compiler, and SAP ABAP studio.",
        "logo_url": "/assets/logo.png",
        "client_type": "public",
        "allowed_redirect_uris": "\n".join([
            "http://localhost:8443/auth/callback",
            "http://127.0.0.1:8443/auth/callback",
            "http://localhost:5173/auth/callback",
            "http://127.0.0.1:5173/auth/callback",
            "http://localhost:5175/auth/callback",
            "http://127.0.0.1:5175/auth/callback",
            "https://skiltrix.asentracoresolutions.com/auth/callback",
            "https://skiltrix.ascentracoresolutions.com/auth/callback",
        ]),
        "allowed_logout_redirect_uris": "\n".join([
            "http://localhost:8443/login",
            "http://127.0.0.1:8443/login",
            "http://localhost:5173/login",
            "http://127.0.0.1:5173/login",
            "http://localhost:5175/login",
            "http://127.0.0.1:5175/login",
            "https://skiltrix.asentracoresolutions.com/login",
            "https://skiltrix.ascentracoresolutions.com/login",
        ]),
        "allowed_origins": "http://localhost:8443,http://127.0.0.1:8443,http://localhost:5173,http://127.0.0.1:5173,https://skiltrix.ascentracoresolutions.com",
        "allowed_origins": "http://localhost:8443,http://127.0.0.1:8443,http://localhost:5173,http://127.0.0.1:5173,https://skiltrix.asentracoresolutions.com,https://skiltrix.ascentracoresolutions.com",
        "is_enabled": True,
    },
    {
        "client_id": "admin",
        "name": "Ascentracore Admin Portal",
        "description": "Administrative console for managing apps, users, metrics, and services.",
        "logo_url": "/as_logo.webp",
        "client_type": "public",
        "allowed_redirect_uris": "\n".join([
            "http://localhost:5173/auth/callback",
            "http://127.0.0.1:5173/auth/callback",
            "http://localhost:5175/auth/callback",
            "http://127.0.0.1:5175/auth/callback",
            "http://localhost:3000/auth/callback",
            "http://127.0.0.1:3000/auth/callback",
            "https://admin.asentracoresolutions.com/auth/callback",
            "https://admin.ascentracoresolutions.com/auth/callback",
        ]),
        "allowed_logout_redirect_uris": "\n".join([
            "http://localhost:5173/login",
            "http://127.0.0.1:5173/login",
            "http://localhost:5175/login",
            "http://127.0.0.1:5175/login",
            "http://localhost:3000/login",
            "http://127.0.0.1:3000/login",
            "https://admin.asentracoresolutions.com/login",
            "https://admin.ascentracoresolutions.com/login",
        ]),
        "allowed_origins": "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175,https://admin.ascentracoresolutions.com",
        "allowed_origins": "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175,https://admin.asentracoresolutions.com,https://admin.ascentracoresolutions.com",
        "is_enabled": True,
    },
    {
        "client_id": "accounts",
        "name": "Ascentracore Central Accounts",
        "description": "Central identity provider, authentication, and self-service account manager.",
        "logo_url": "/assets/logo.webp",
        "client_type": "public",
        "allowed_redirect_uris": "\n".join([
            "http://localhost:5174/auth/callback",
            "http://127.0.0.1:5174/auth/callback",
            "http://localhost:5173/auth/callback",
            "http://127.0.0.1:5173/auth/callback",
            "https://accounts.asentracoresolutions.com/auth/callback",
            "https://accounts.ascentracoresolutions.com/auth/callback",
        ]),
        "allowed_logout_redirect_uris": "\n".join([
            "http://localhost:5174/login",
            "http://127.0.0.1:5174/login",
            "http://localhost:5173/login",
            "http://127.0.0.1:5173/login",
            "https://accounts.asentracoresolutions.com/login",
            "https://accounts.ascentracoresolutions.com/login",
        ]),
        "allowed_origins": "http://localhost:5174,http://127.0.0.1:5174,https://accounts.ascentracoresolutions.com",
        "allowed_origins": "http://localhost:5174,http://127.0.0.1:5174,https://accounts.asentracoresolutions.com,https://accounts.ascentracoresolutions.com",
        "is_enabled": True,
    },
    {
        "client_id": "main",
        "name": "Spaceflight Simulator Community (SFS)",
        "description": "Spaceflight Simulator blueprint repository, rocket designs, and builder community.",
        "logo_url": "/assets/logo.webp",
        "client_type": "public",
        "allowed_redirect_uris": "\n".join([
            "http://localhost:5175/auth/callback",
            "http://127.0.0.1:5175/auth/callback",
            "http://localhost:5176/auth/callback",
            "http://127.0.0.1:5176/auth/callback",
            "http://localhost:5173/auth/callback",
            "http://127.0.0.1:5173/auth/callback",
            "https://sfs.asentracoresolutions.com/auth/callback",
            "https://sfs.ascentracoresolutions.com/auth/callback",
        ]),
        "allowed_logout_redirect_uris": "\n".join([
            "http://localhost:5175/",
            "http://127.0.0.1:5175/",
            "http://localhost:5176/",
            "http://127.0.0.1:5176/",
            "https://sfs.asentracoresolutions.com/",
            "https://sfs.ascentracoresolutions.com/",
        ]),
        "allowed_origins": "http://localhost:5175,http://127.0.0.1:5175,http://localhost:5176,http://127.0.0.1:5176,https://sfs.ascentracoresolutions.com",
        "allowed_origins": "http://localhost:5175,http://127.0.0.1:5175,http://localhost:5176,http://127.0.0.1:5176,https://sfs.asentracoresolutions.com,https://sfs.ascentracoresolutions.com",
        "is_enabled": True,
    },
    {
        "client_id": "policies",
        "name": "Ascentracore Legal & Policies Portal",
        "description": "Official company terms of service, privacy policies, and compliance documentation.",
        "logo_url": "/assets/logo.webp",
        "client_type": "public",
        "allowed_redirect_uris": "\n".join([
            "http://localhost:5176/auth/callback",
            "http://127.0.0.1:5176/auth/callback",
            "http://localhost:5177/auth/callback",
            "http://127.0.0.1:5177/auth/callback",
            "http://localhost:5173/auth/callback",
            "http://127.0.0.1:5173/auth/callback",
            "https://policies.asentracoresolutions.com/auth/callback",
            "https://policies.ascentracoresolutions.com/auth/callback",
        ]),
        "allowed_logout_redirect_uris": "\n".join([
            "http://localhost:5176/",
            "http://127.0.0.1:5176/",
            "http://localhost:5177/",
            "http://127.0.0.1:5177/",
            "https://policies.asentracoresolutions.com/",
            "https://policies.ascentracoresolutions.com/",
        ]),
        "allowed_origins": "http://localhost:5176,http://127.0.0.1:5176,http://localhost:5177,http://127.0.0.1:5177,https://policies.ascentracoresolutions.com",
        "allowed_origins": "http://localhost:5176,http://127.0.0.1:5176,http://localhost:5177,http://127.0.0.1:5177,https://policies.asentracoresolutions.com,https://policies.ascentracoresolutions.com",
        "is_enabled": True,
    },
]


class Command(BaseCommand):
    help = "Seeds or updates the five registered client applications for SSO."

    def handle(self, *args, **options):
        for app_data in APPLICATIONS:
            client_id = app_data["client_id"]
            app, created = ClientApplication.objects.update_or_create(
                client_id=client_id,
                defaults=app_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} client application: {app.name} ({client_id})"))
