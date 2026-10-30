import random
import string
from django.utils import timezone
from .models import BP, BpDlv, TotalActivity, AllErrors


def unique_id():
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choices(characters, k=20))
    return random_string


def get_client_ip(request):
    """Extracts client IP, even behind proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or "127.0.0.1"


def generate_otp(length=6):
    """Generates a random numeric OTP of specified length."""
    digits = string.digits
    otp = ''.join(random.choices(digits, k=length))
    return otp


def insert_activity(ip, version, activity_id, platform, platform_name, user_id=None, utm_source=None, utm_medium=None, utm_campaign=None):
    TotalActivity.objects.create(
        ip=ip,
        user_id=user_id,
        activity_id=activity_id,
        total_id=unique_id(),
        version=version,
        platform_name=platform_name,
        platform=platform,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign
    )
    print("Executed: ", activity_id, "utm_source:", utm_source)


def insert_error(ip, version, error_msg, activity, error_code, platform, platform_name, user_id=None, utm_source=None, utm_medium=None, utm_campaign=None):
    AllErrors.objects.create(
        ip=ip,
        error_id=unique_id(),
        error_msg=error_msg,
        user_id=user_id,
        activity=activity,
        version=version,
        error_code=error_code,
        platform=platform,
        platform_name=platform_name,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign
    )
    print("Error inserted: ", error_msg)


def insert_dlv(ip, bp_id, type, user_id, download_type, version, utm_source=None):
    bp = BP.objects.filter(bp_id=bp_id, status="approved").first()
    if bp:
        if type == "view":
            bp.fviews += 1
            bp.views += 1
        elif type == "like":
            bp.flikes += 1
            bp.likes += 1
        else:
            bp.fdownloads += 1
            bp.downloads += 1
        bp.save()

        BpDlv.objects.create(
            ip=ip,
            bp_pla_id=bp_id,
            type=type,
            user_id=user_id,
            download_type=download_type,
            dlv_id=unique_id(),
            platform="sfs",
            platform_name="app",
            utm_source=utm_source,
            version=version,
            time=timezone.now()
        )
    else:
        print("error: blueprint not found for insert_dlv")
