import os
from django.conf import settings

CDN_DOMAIN = getattr(settings, "CDN_DOMAIN", "https://cdn.ascentracoresolutions.com").rstrip("/")

images = f"{CDN_DOMAIN}/"
sfs_images = f"{CDN_DOMAIN}/sfs/images/"
sfs_zipfiles = f"{CDN_DOMAIN}/sfs/zipfiles/"
st_images = f"{CDN_DOMAIN}/st/images/"
st_pdfs = f"{CDN_DOMAIN}/st/pdfs/"
st_videos = f"{CDN_DOMAIN}/st/videos/"

def site_data(request):
    return {
        "CDN_DOMAIN": CDN_DOMAIN,
        "images": images,
        "sfs_images": sfs_images,
        "sfs_zipfiles": sfs_zipfiles,
        "st_images": st_images,
        "st_pdfs": st_pdfs,
        "st_videos": st_videos,
    }

# Re-export utilities from cdn_utils for ease of use across the project
from apis.cdn_utils import (
    get_sfs_image_url,
    get_sfs_zip_url,
    get_st_image_url,
    get_st_pdf_url,
    get_st_video_url,
    upload_sfs_image,
    upload_sfs_zip,
    upload_st_image,
    upload_st_pdf,
    upload_st_video,
    upload_to_r2,
    get_s3_client,
)

# Re-export utilities from sfs.utils for backward and cross-app compatibility
from sfs.utils import (
    unique_id,
    get_client_ip,
    generate_otp,
    insert_activity,
    insert_error,
)
