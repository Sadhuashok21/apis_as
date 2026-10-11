from django.contrib import admin
from django.utils import timezone
from .models import (
    Category,
    Tag,
    Author,
    BlogPost,
    Tutorial,
    Resource,
    CaseStudy,
    Product,
    Service,
    FAQ,
    SiteSetting,
)


@admin.action(description="Publish selected items")
def make_published(modeladmin, request, queryset):
    if hasattr(queryset.model, "status"):
        queryset.update(status="published")
    elif hasattr(queryset.model, "is_published"):
        queryset.update(is_published=True)
    elif hasattr(queryset.model, "is_active"):
        queryset.update(is_active=True)


@admin.action(description="Unpublish / Set to Draft")
def make_draft(modeladmin, request, queryset):
    if hasattr(queryset.model, "status"):
        queryset.update(status="draft")
    elif hasattr(queryset.model, "is_published"):
        queryset.update(is_published=False)
    elif hasattr(queryset.model, "is_active"):
        queryset.update(is_active=False)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "meta_title", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "email", "slug")
    search_fields = ("name", "role", "email", "bio")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "status", "published_at", "reading_time", "views_count")
    list_filter = ("status", "category", "author", "created_at", "published_at")
    search_fields = ("title", "slug", "excerpt", "content", "meta_title", "meta_description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    actions = [make_published, make_draft]
    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "slug", "author", "category", "tags", "featured_image")
        }),
        ("Content & Excerpt", {
            "fields": ("excerpt", "content", "reading_time")
        }),
        ("Publishing Status", {
            "fields": ("status", "published_at")
        }),
        ("Search Engine Optimization (SEO)", {
            "classes": ("collapse",),
            "fields": ("meta_title", "meta_description", "canonical_url")
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.status == "published" and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "status", "order", "estimated_reading_time", "published_date")
    list_filter = ("category", "difficulty", "status", "published_date")
    search_fields = ("title", "slug", "introduction", "content", "code_examples")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("related_tutorials",)
    actions = [make_published, make_draft]
    fieldsets = (
        ("Tutorial Overview", {
            "fields": ("title", "slug", "category", "difficulty", "order", "author", "status", "published_date")
        }),
        ("Educational Content", {
            "fields": ("introduction", "content", "code_examples", "estimated_reading_time")
        }),
        ("Internal Linking", {
            "fields": ("related_tutorials",)
        }),
        ("SEO Settings", {
            "classes": ("collapse",),
            "fields": ("meta_title", "meta_description", "canonical_url")
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.status == "published" and not obj.published_date:
            obj.published_date = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "badge_text", "status", "featured", "order", "created_at")
    list_filter = ("resource_type", "status", "featured")
    search_fields = ("title", "slug", "description", "content")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    actions = [make_published, make_draft]


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ("project_name", "title", "client_or_type", "status", "featured", "order", "created_at")
    list_filter = ("status", "featured", "created_at")
    search_fields = ("project_name", "title", "summary", "problem", "solution", "architecture")
    prepopulated_fields = {"slug": ("title",)}
    actions = [make_published, make_draft]
    fieldsets = (
        ("Project Identification", {
            "fields": ("project_name", "title", "slug", "client_or_type", "cover_image", "live_url", "order", "featured", "status")
        }),
        ("Case Summary & Background", {
            "fields": ("summary", "background", "problem")
        }),
        ("Solution & Technical Architecture", {
            "fields": ("solution", "technology_used", "architecture", "development_process")
        }),
        ("Outcomes & Retrospective", {
            "fields": ("challenges", "results", "lessons_learned")
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "featured", "order", "website_url")
    list_filter = ("status", "featured")
    search_fields = ("name", "slug", "tagline", "description")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Identity", {
            "fields": ("name", "slug", "tagline", "status", "featured", "order")
        }),
        ("Product Details", {
            "fields": ("description", "features", "technologies", "screenshots")
        }),
        ("Links & Resources", {
            "fields": ("website_url", "app_url", "documentation_url", "github_url")
        }),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "short_description", "full_description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_published")
    list_filter = ("category", "is_published")
    search_fields = ("question", "answer")
    actions = [make_published, make_draft]


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("site_name", "contact_email", "contact_phone")
