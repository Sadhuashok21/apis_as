import traceback, re

from shared_lib.utils import insertions

import os
import traceback

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

            print("🔥 ERROR INSERTED SUCCESSFULLY")

        except Exception as e:

            print(
                "🔥 ERROR INSERTION FAILED:",
                e
            )

        return None