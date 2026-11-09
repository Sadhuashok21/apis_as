import uuid
from django.db import models
from django.utils import timezone


class CmsCourse(models.Model):
    """
    Metadata representation of a dynamic curriculum or course in Skiltrix CMS.
    Page contents are generated as physical TSX/CSS/JS files, never stored in DB.
    """
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    )

    course_id = models.CharField(max_length=60, unique=True, default=uuid.uuid4, db_index=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=60, default="languages")
    icon = models.CharField(max_length=60, default="book-open")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="published", db_index=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_cms_courses"
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.title} ({self.slug})"


class CmsPage(models.Model):
    """
    Hierarchical page metadata for dynamic courses.
    Educational body content is strictly compiled and written to physical project files.
    """
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
    )

    TARGET_CHOICES = (
        ("_blank", "New Tab"),
        ("_self", "Current Tab"),
    )

    page_id = models.CharField(max_length=70, unique=True, default=uuid.uuid4, db_index=True)
    course = models.ForeignKey(CmsCourse, on_delete=models.CASCADE, related_name="pages", to_field="course_id")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, db_index=True)
    url_path = models.CharField(max_length=255, unique=True, db_index=True, help_text="e.g. /courses/c-programming/variables/")
    
    # Physical file locations
    file_path = models.CharField(max_length=500, help_text="Path to generated index.tsx")
    css_path = models.CharField(max_length=500, help_text="Path to generated index.css")
    js_path = models.CharField(max_length=500, blank=True, default="", help_text="Path to generated index.js (optional)")

    page_order = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True)

    # SEO metadata
    seo_title = models.CharField(max_length=255, blank=True, default="")
    seo_description = models.TextField(blank=True, default="")

    # YouTube video settings
    video_title = models.CharField(max_length=255, blank=True, default="")
    video_url = models.CharField(max_length=500, blank=True, default="")
    video_thumbnail = models.CharField(max_length=500, blank=True, default="")
    video_target = models.CharField(max_length=10, choices=TARGET_CHOICES, default="_blank")

    # Sequential Topic Navigation
    prev_page = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="next_links")
    next_page = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="prev_links")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "st_cms_pages"
        ordering = ["page_order", "id"]
        indexes = [
            models.Index(fields=["course", "parent", "page_order"]),
            models.Index(fields=["url_path", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.url_path}]"


class CmsMedia(models.Model):
    """
    Media library records for images, thumbnails, and diagrams.
    Stored on disk/CDN, never stored in DB as binary blobs.
    """
    media_id = models.CharField(max_length=70, unique=True, default=uuid.uuid4, db_index=True)
    title = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
    file_type = models.CharField(max_length=50, default="image/png")
    file_size_kb = models.IntegerField(default=0)
    alt_text = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "st_cms_media"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CmsBuildJob(models.Model):
    """
    Record of frontend build and atomic publishing jobs.
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    job_id = models.CharField(max_length=70, unique=True, default=uuid.uuid4)
    triggered_by = models.CharField(max_length=100, default="admin")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    output_log = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "st_cms_build_jobs"
        ordering = ["-started_at"]
