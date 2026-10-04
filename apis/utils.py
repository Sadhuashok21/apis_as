images = "https://cdn.ascentracoresolutions.com/"

def site_data(request):
    data = {
        "images": images,
    }
    return data

# Re-export utilities from sfs.utils for backward and cross-app compatibility
from sfs.utils import (
    unique_id,
    get_client_ip,
    generate_otp,
    insert_activity,
    insert_error,
)
