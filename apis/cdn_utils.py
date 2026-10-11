"""
Ascentracore Solutions & Ecosystem CDN Utility
CDN Domain: https://cdn.ascentracoresolutions.com/

Path structure:
- SFS:
    - images:   https://cdn.ascentracoresolutions.com/sfs/images/<filename>
    - zipfiles: https://cdn.ascentracoresolutions.com/sfs/zipfiles/<filename>
- SkilTrix (st):
    - images:   https://cdn.ascentracoresolutions.com/st/images/<filename>
    - pdfs:     https://cdn.ascentracoresolutions.com/st/pdfs/<filename>
    - videos:   https://cdn.ascentracoresolutions.com/st/videos/<filename>
"""

import os
import boto3
from django.conf import settings
from sfs.utils import unique_id

CDN_DOMAIN = getattr(settings, "CDN_DOMAIN", "https://cdn.ascentracoresolutions.com").rstrip("/")

SFS_IMAGES_BASE = f"{CDN_DOMAIN}/sfs/images"
SFS_ZIPFILES_BASE = f"{CDN_DOMAIN}/sfs/zipfiles"

ST_IMAGES_BASE = f"{CDN_DOMAIN}/st/images"
ST_PDFS_BASE = f"{CDN_DOMAIN}/st/pdfs"
ST_VIDEOS_BASE = f"{CDN_DOMAIN}/st/videos"

R2_BUCKET = getattr(settings, "R2_BUCKET_NAME", "sfs-blueprints")


def get_sfs_image_url(filename: str) -> str:
    """Return full CDN URL for an SFS image."""
    if not filename:
        return ""
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    clean_name = filename.lstrip("/")
    if clean_name.startswith("sfs/images/"):
        return f"{CDN_DOMAIN}/{clean_name}"
    return f"{SFS_IMAGES_BASE}/{clean_name}"


def get_sfs_zip_url(filename: str) -> str:
    """Return full CDN URL for an SFS zip file."""
    if not filename:
        return ""
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    clean_name = filename.lstrip("/")
    if clean_name.startswith("sfs/zipfiles/"):
        return f"{CDN_DOMAIN}/{clean_name}"
    return f"{SFS_ZIPFILES_BASE}/{clean_name}"


def get_st_image_url(filename: str) -> str:
    """Return full CDN URL for a SkilTrix image."""
    if not filename:
        return ""
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    clean_name = filename.lstrip("/")
    if clean_name.startswith("st/images/"):
        return f"{CDN_DOMAIN}/{clean_name}"
    return f"{ST_IMAGES_BASE}/{clean_name}"


def get_st_pdf_url(filename: str) -> str:
    """Return full CDN URL for a SkilTrix PDF / document."""
    if not filename:
        return ""
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    clean_name = filename.lstrip("/")
    if clean_name.startswith("st/pdfs/"):
        return f"{CDN_DOMAIN}/{clean_name}"
    return f"{ST_PDFS_BASE}/{clean_name}"


def get_st_video_url(filename: str) -> str:
    """Return full CDN URL for a SkilTrix video."""
    if not filename:
        return ""
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    clean_name = filename.lstrip("/")
    if clean_name.startswith("st/videos/"):
        return f"{CDN_DOMAIN}/{clean_name}"
    return f"{ST_VIDEOS_BASE}/{clean_name}"


def get_s3_client():
    """Instantiate and return boto3 S3 client configured with Cloudflare R2 credentials."""
    endpoint_url = os.getenv("endpoint_url") or getattr(settings, "R2_ENDPOINT_URL", "")
    aws_access_key_id = os.getenv("aws_access_key_id") or getattr(settings, "R2_ACCESS_KEY_ID", "")
    aws_secret_access_key = os.getenv("aws_secret_access_key") or getattr(settings, "R2_SECRET_ACCESS_KEY", "")

    return boto3.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="auto",
    )


def upload_to_r2(file_obj, key: str, content_type: str = None, bucket: str = None) -> str:
    """
    Upload a file-like object to R2 under the specified key.
    Returns the full CDN URL.
    """
    s3 = get_s3_client()
    target_bucket = bucket or R2_BUCKET

    kwargs = {
        "Bucket": target_bucket,
        "Key": key,
        "Body": file_obj,
    }
    if content_type:
        kwargs["ContentType"] = content_type

    s3.put_object(**kwargs)
    return f"{CDN_DOMAIN}/{key.lstrip('/')}"


def upload_sfs_image(file_obj, filename: str = None, content_type: str = None) -> tuple[str, str]:
    """Upload an image to sfs/images/. Returns (filename, full_cdn_url)."""
    if not filename:
        ext = getattr(file_obj, "name", "image.png").split(".")[-1]
        filename = f"{unique_id()}.{ext}"
    key = f"sfs/images/{filename}"
    ctype = content_type or getattr(file_obj, "content_type", "image/png")
    url = upload_to_r2(file_obj, key, content_type=ctype)
    return filename, url


def upload_sfs_zip(file_obj, filename: str = None, content_type: str = None) -> tuple[str, str]:
    """Upload a zipfile to sfs/zipfiles/. Returns (filename, full_cdn_url)."""
    if not filename:
        ext = getattr(file_obj, "name", "archive.zip").split(".")[-1]
        filename = f"{unique_id()}.{ext}"
    key = f"sfs/zipfiles/{filename}"
    ctype = content_type or getattr(file_obj, "content_type", "application/zip")
    url = upload_to_r2(file_obj, key, content_type=ctype)
    return filename, url


def upload_st_image(file_obj, filename: str = None, content_type: str = None) -> tuple[str, str]:
    """Upload an image to st/images/. Returns (filename, full_cdn_url)."""
    if not filename:
        ext = getattr(file_obj, "name", "image.png").split(".")[-1]
        filename = f"{unique_id()}.{ext}"
    key = f"st/images/{filename}"
    ctype = content_type or getattr(file_obj, "content_type", "image/png")
    url = upload_to_r2(file_obj, key, content_type=ctype)
    return filename, url


def upload_st_pdf(file_obj, filename: str = None, content_type: str = None) -> tuple[str, str]:
    """Upload a pdf to st/pdfs/. Returns (filename, full_cdn_url)."""
    if not filename:
        ext = getattr(file_obj, "name", "document.pdf").split(".")[-1]
        filename = f"{unique_id()}.{ext}"
    key = f"st/pdfs/{filename}"
    ctype = content_type or getattr(file_obj, "content_type", "application/pdf")
    url = upload_to_r2(file_obj, key, content_type=ctype)
    return filename, url


def upload_st_video(file_obj, filename: str = None, content_type: str = None) -> tuple[str, str]:
    """Upload a video to st/videos/. Returns (filename, full_cdn_url)."""
    if not filename:
        ext = getattr(file_obj, "name", "video.mp4").split(".")[-1]
        filename = f"{unique_id()}.{ext}"
    key = f"st/videos/{filename}"
    ctype = content_type or getattr(file_obj, "content_type", "video/mp4")
    url = upload_to_r2(file_obj, key, content_type=ctype)
    return filename, url

