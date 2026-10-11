from rest_framework import serializers
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


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "meta_title", "meta_description"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "slug", "bio", "profile_image", "role", "email", "twitter_url", "linkedin_url", "github_url"]


class BlogPostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "featured_image",
            "author", "category", "tags", "published_at",
            "reading_time", "meta_title", "meta_description", "views_count"
        ]


class BlogPostDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    related_posts = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "excerpt", "content", "featured_image",
            "author", "category", "tags", "published_at", "updated_at",
            "reading_time", "meta_title", "meta_description", "canonical_url",
            "views_count", "related_posts"
        ]

    def get_related_posts(self, obj):
        related = BlogPost.objects.filter(
            status="published",
            category=obj.category
        ).exclude(id=obj.id)[:3]
        return BlogPostListSerializer(related, many=True).data


class TutorialListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Tutorial
        fields = [
            "id", "title", "slug", "category", "category_display", "difficulty",
            "introduction", "estimated_reading_time", "author", "published_date", "order"
        ]


class TutorialDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    related_tutorials = TutorialListSerializer(many=True, read_only=True)
    category_siblings = serializers.SerializerMethodField()

    class Meta:
        model = Tutorial
        fields = [
            "id", "title", "slug", "category", "category_display", "difficulty",
            "introduction", "content", "code_examples", "estimated_reading_time",
            "author", "published_date", "updated_date", "related_tutorials",
            "category_siblings", "meta_title", "meta_description", "canonical_url"
        ]

    def get_category_siblings(self, obj):
        siblings = Tutorial.objects.filter(
            status="published",
            category=obj.category
        ).order_by("order", "id")
        return [
            {"id": s.id, "title": s.title, "slug": s.slug, "difficulty": s.difficulty, "order": s.order}
            for s in siblings
        ]


class ResourceSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    resource_type_display = serializers.CharField(source="get_resource_type_display", read_only=True)

    class Meta:
        model = Resource
        fields = [
            "id", "title", "slug", "resource_type", "resource_type_display",
            "description", "content", "badge_text", "download_url",
            "external_url", "tags", "featured", "order", "created_at"
        ]


class CaseStudyListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStudy
        fields = [
            "id", "project_name", "title", "slug", "client_or_type",
            "summary", "technology_used", "cover_image", "live_url",
            "featured", "order", "created_at"
        ]


class CaseStudyDetailSerializer(serializers.ModelSerializer):
    related_studies = serializers.SerializerMethodField()

    class Meta:
        model = CaseStudy
        fields = [
            "id", "project_name", "title", "slug", "client_or_type",
            "summary", "background", "problem", "solution",
            "technology_used", "architecture", "development_process",
            "challenges", "results", "lessons_learned", "cover_image",
            "live_url", "featured", "created_at", "related_studies"
        ]

    def get_related_studies(self, obj):
        qs = CaseStudy.objects.filter(status="published").exclude(id=obj.id)[:3]
        return CaseStudyListSerializer(qs, many=True).data


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "tagline", "description",
            "features", "screenshots", "technologies", "status",
            "website_url", "app_url", "documentation_url", "github_url",
            "featured", "order"
        ]


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id", "name", "slug", "short_description", "full_description",
            "icon_name", "benefits", "deliverables", "technologies", "order"
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "order"]


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = "__all__"
