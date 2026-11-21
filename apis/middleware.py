import traceback, re
import os
from django.http import JsonResponse
from sfs import utils as insertions

PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )


def get_error_app(exception):
    tb = traceback.extract_tb(exception.__traceback__)

    for frame in reversed(tb):

        file_path = os.path.abspath(frame.filename)

        # Ignore virtual environment
        if "\\env\\" in file_path:
            continue

        # Ignore Python/site-packages
        if "site-packages" in file_path:
            continue

        # Only consider files inside your project
        if file_path.startswith(PROJECT_ROOT):

            relative_path = os.path.relpath(
                file_path,
                PROJECT_ROOT
            )

            parts = relative_path.replace("\\", "/").split("/")

            if parts:
                return parts[0]

    return "unknown"



class ExceptionLoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)    


    def process_exception(self, request, exception):

        error_type = type(exception).__name__
        error_message = str(exception)
        traceback_text = traceback.format_exc()


        app_name = get_error_app(exception)

        ip_address = request.META.get(
            "REMOTE_ADDR",
            "unknown"
        )

        try:
            user_id = request.session.get(
                "user_id",
                None
            )
        except Exception:
            user_id = None

        print("================================")
        print("Error:", error_type)
        print("Message:", error_message)
        print("App:", app_name)
        print("Path:", request.path)
        print("================================")

        # -----------------------------------------
        # Insert dynamically
        # -----------------------------------------

        try:

            if request.user.is_authenticated:
                insertions.insert_error(
                    ip_address,
                    "1.0",
                    traceback_text + "\n" + error_message,
                    request.path,
                    500,
                    "website",
                    app_name,
                    request.user.user_id
                )

            else:
                insertions.insert_error(
                    ip_address,
                    "1.0",
                    traceback_text + "\n" + error_message,
                    request.path,
                    500,
                    "website",
                    app_name
                )

            print("[ERROR LOG] ERROR INSERTED SUCCESSFULLY")

        except Exception as e:

            print(
                "[ERROR LOG] ERROR INSERTION FAILED:",
                e
            )

        return None


class AdminUploadLimitMiddleware:
    """
    Enforces upload size limits:
    - Up to 1 GB (1,073,741,824 bytes) ONLY for admin panels:
        * Request path begins with /admin/ or /api/admin/
        * Request origin or referer is from admin portal
        * Header X-Admin-Portal is true
        * User is staff, superuser, or has an admin role
    - Standard 50 MB limit for all non-admin user uploads.
    """
    ADMIN_MAX_UPLOAD_BYTES = 1024 * 1024 * 1024      # 1 GB
    STANDARD_MAX_UPLOAD_BYTES = 50 * 1024 * 1024     # 50 MB

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        content_length_raw = request.META.get('CONTENT_LENGTH')
        if content_length_raw and request.method in ('POST', 'PUT', 'PATCH'):
            try:
                content_length = int(content_length_raw)
            except (ValueError, TypeError):
                content_length = 0

            if content_length > 0:
                is_admin_path = (
                    request.path.startswith('/admin/') or
                    request.path.startswith('/api/admin/') or
                    '/admin/' in request.path
                )

                origin = (request.META.get('HTTP_ORIGIN') or '').lower()
                referer = (request.META.get('HTTP_REFERER') or '').lower()
                is_admin_origin = (
                    'admin.ascentracoresolutions.com' in origin or
                    'admin.ascentracoresolutions.com' in referer or
                    ':5174' in origin or
                    ':5174' in referer or
                    request.headers.get('X-Admin-Portal', '').lower() in ('true', '1')
                )

                is_admin_user = False
                user = getattr(request, 'user', None)
                if user and getattr(user, 'is_authenticated', False):
                    is_admin_user = (
                        getattr(user, 'is_staff', False) or
                        getattr(user, 'is_superuser', False) or
                        str(getattr(user, 'role', '')).lower() in ('admin', 'superadmin', 'staff')
                    )

                is_admin = is_admin_path or is_admin_origin or is_admin_user
                max_bytes = self.ADMIN_MAX_UPLOAD_BYTES if is_admin else self.STANDARD_MAX_UPLOAD_BYTES

                if content_length > max_bytes:
                    if is_admin:
                        return JsonResponse({
                            "status": False,
                            "error": "Payload Too Large",
                            "message": f"Upload size exceeds the maximum admin limit of 1 GB (Attempted: {round(content_length / (1024 * 1024 * 1024), 2)} GB)."
                        }, status=413)
                    else:
                        return JsonResponse({
                            "status": False,
                            "error": "Payload Too Large",
                            "message": f"Upload size exceeds the standard maximum limit of 50 MB (Attempted: {round(content_length / (1024 * 1024), 2)} MB). 1 GB uploads are reserved only for Admin Panels."
                        }, status=413)

        return self.get_response(request)
