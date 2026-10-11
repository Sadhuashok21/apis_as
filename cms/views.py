from django.db.models import Q, F
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

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
from .serializers import (
    CategorySerializer,
    TagSerializer,
    AuthorSerializer,
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    TutorialListSerializer,
    TutorialDetailSerializer,
    ResourceSerializer,
    CaseStudyListSerializer,
    CaseStudyDetailSerializer,
    ProductSerializer,
    ServiceSerializer,
    FAQSerializer,
    SiteSettingSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_site_overview(request):
    """
    Returns high-level metadata, featured products, services, recent tutorials and posts for the homepage.
    """
    settings = SiteSetting.objects.first()
    settings_data = SiteSettingSerializer(settings).data if settings else {}

    featured_products = Product.objects.filter(featured=True).order_by("order")[:4]
    services = Service.objects.filter(is_active=True).order_by("order")[:6]
    recent_posts = BlogPost.objects.filter(status="published").order_by("-published_at")[:3]
    recent_tutorials = Tutorial.objects.filter(status="published").order_by("-published_date")[:6]
    case_studies = CaseStudy.objects.filter(status="published", featured=True).order_by("order")[:3]

    return Response({
        "status": True,
        "site": settings_data,
        "featured_products": ProductSerializer(featured_products, many=True).data,
        "services": ServiceSerializer(services, many=True).data,
        "recent_posts": BlogPostListSerializer(recent_posts, many=True).data,
        "recent_tutorials": TutorialListSerializer(recent_tutorials, many=True).data,
        "featured_case_studies": CaseStudyListSerializer(case_studies, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def list_blog_posts(request):
    category_slug = request.GET.get("category")
    tag_slug = request.GET.get("tag")
    search_query = request.GET.get("q")

    qs = BlogPost.objects.filter(status="published")

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    categories = Category.objects.all()
    tags = Tag.objects.all()

    return Response({
        "status": True,
        "count": qs.count(),
        "posts": BlogPostListSerializer(qs, many=True).data,
        "categories": CategorySerializer(categories, many=True).data,
        "tags": TagSerializer(tags, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_blog_post_detail(request, slug):
    try:
        post = BlogPost.objects.get(slug=slug, status="published")
        # Increment views safely
        BlogPost.objects.filter(id=post.id).update(views_count=F("views_count") + 1)
        post.refresh_from_db()
        return Response({
            "status": True,
            "post": BlogPostDetailSerializer(post).data
        })
    except BlogPost.DoesNotExist:
        return Response(
            {"status": False, "message": "Article not found or not published"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_tutorials(request):
    category = request.GET.get("category")
    difficulty = request.GET.get("difficulty")
    search_query = request.GET.get("q")

    qs = Tutorial.objects.filter(status="published")

    if category:
        qs = qs.filter(category=category.lower())
    if difficulty:
        qs = qs.filter(difficulty=difficulty.lower())
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(introduction__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # Group count by categories
    categories_list = [
        {"id": c[0], "name": c[1], "count": Tutorial.objects.filter(status="published", category=c[0]).count()}
        for c in Tutorial.CATEGORY_CHOICES
    ]

    return Response({
        "status": True,
        "count": qs.count(),
        "tutorials": TutorialListSerializer(qs, many=True).data,
        "categories": categories_list,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_tutorial_detail(request, category, slug):
    try:
        tutorial = Tutorial.objects.get(category=category.lower(), slug=slug, status="published")
        return Response({
            "status": True,
            "tutorial": TutorialDetailSerializer(tutorial).data
        })
    except Tutorial.DoesNotExist:
        return Response(
            {"status": False, "message": "Tutorial not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_resources(request):
    resource_type = request.GET.get("type")
    search_query = request.GET.get("q")

    qs = Resource.objects.filter(status="published")
    if resource_type:
        qs = qs.filter(resource_type=resource_type)
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    types_list = [
        {"id": t[0], "name": t[1], "count": Resource.objects.filter(status="published", resource_type=t[0]).count()}
        for t in Resource.RESOURCE_TYPE_CHOICES
    ]

    return Response({
        "status": True,
        "count": qs.count(),
        "resources": ResourceSerializer(qs, many=True).data,
        "types": types_list,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def list_case_studies(request):
    qs = CaseStudy.objects.filter(status="published").order_by("order", "-created_at")
    return Response({
        "status": True,
        "count": qs.count(),
        "case_studies": CaseStudyListSerializer(qs, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_case_study_detail(request, slug):
    try:
        cs = CaseStudy.objects.get(slug=slug, status="published")
        return Response({
            "status": True,
            "case_study": CaseStudyDetailSerializer(cs).data
        })
    except CaseStudy.DoesNotExist:
        return Response(
            {"status": False, "message": "Case study not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_products(request):
    qs = Product.objects.all().order_by("order")
    return Response({
        "status": True,
        "count": qs.count(),
        "products": ProductSerializer(qs, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_product_detail(request, slug):
    try:
        p = Product.objects.get(slug=slug)
        return Response({
            "status": True,
            "product": ProductSerializer(p).data
        })
    except Product.DoesNotExist:
        return Response(
            {"status": False, "message": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_services(request):
    qs = Service.objects.filter(is_active=True).order_by("order")
    return Response({
        "status": True,
        "count": qs.count(),
        "services": ServiceSerializer(qs, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_service_detail(request, slug):
    try:
        s = Service.objects.get(slug=slug, is_active=True)
        return Response({
            "status": True,
            "service": ServiceSerializer(s).data
        })
    except Service.DoesNotExist:
        return Response(
            {"status": False, "message": "Service not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_faqs(request):
    qs = FAQ.objects.filter(is_published=True).order_by("order")
    return Response({
        "status": True,
        "faqs": FAQSerializer(qs, many=True).data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def global_search(request):
    query = request.GET.get("q", "").strip()
    if not query or len(query) < 2:
        return Response({
            "status": True,
            "query": query,
            "total_results": 0,
            "posts": [],
            "tutorials": [],
            "resources": [],
            "case_studies": [],
        })

    posts = BlogPost.objects.filter(
        status="published"
    ).filter(
        Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query)
    )[:6]

    tutorials = Tutorial.objects.filter(
        status="published"
    ).filter(
        Q(title__icontains=query) | Q(introduction__icontains=query) | Q(content__icontains=query)
    )[:6]

    resources = Resource.objects.filter(
        status="published"
    ).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )[:6]

    case_studies = CaseStudy.objects.filter(
        status="published"
    ).filter(
        Q(title__icontains=query) | Q(project_name__icontains=query) | Q(summary__icontains=query)
    )[:4]

    total = posts.count() + tutorials.count() + resources.count() + case_studies.count()

    return Response({
        "status": True,
        "query": query,
        "total_results": total,
        "posts": BlogPostListSerializer(posts, many=True).data,
        "tutorials": TutorialListSerializer(tutorials, many=True).data,
        "resources": ResourceSerializer(resources, many=True).data,
        "case_studies": CaseStudyListSerializer(case_studies, many=True).data,
    })


def generate_sitemap_xml(request):
    """
    Dynamically generates public XML sitemap for search engine crawlers.
    Strictly excludes login, register, dashboard, compiler, profile, and admin.
    """
    from django.http import HttpResponse

    domain = "https://ascentracoresolutions.com"
    static_pages = [
        "",
        "/about",
        "/services",
        "/products",
        "/case-studies",
        "/tutorials",
        "/blog",
        "/resources",
        "/contact",
        "/privacy-policy",
        "/terms",
    ]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    # Static pages
    for path in static_pages:
        priority = "1.0" if path == "" else "0.8"
        xml_lines.append(f'  <url><loc>{domain}{path}</loc><changefreq>weekly</changefreq><priority>{priority}</priority></url>')

    # Blog posts
    for post in BlogPost.objects.filter(status="published"):
        lastmod = post.updated_at.strftime("%Y-%m-%d") if post.updated_at else ""
        lastmod_tag = f'<lastmod>{lastmod}</lastmod>' if lastmod else ""
        xml_lines.append(f'  <url><loc>{domain}/blog/{post.slug}</loc>{lastmod_tag}<changefreq>weekly</changefreq><priority>0.7</priority></url>')

    # Tutorials
    for tut in Tutorial.objects.filter(status="published"):
        lastmod = tut.updated_date.strftime("%Y-%m-%d") if tut.updated_date else ""
        lastmod_tag = f'<lastmod>{lastmod}</lastmod>' if lastmod else ""
        xml_lines.append(f'  <url><loc>{domain}/tutorials/{tut.category}/{tut.slug}</loc>{lastmod_tag}<changefreq>weekly</changefreq><priority>0.7</priority></url>')

    # Case studies
    for cs in CaseStudy.objects.filter(status="published"):
        xml_lines.append(f'  <url><loc>{domain}/case-studies/{cs.slug}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')

    # Products
    for prod in Product.objects.all():
        xml_lines.append(f'  <url><loc>{domain}/products/{prod.slug}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')

    # Services
    for svc in Service.objects.filter(is_active=True):
        xml_lines.append(f'  <url><loc>{domain}/services/{svc.slug}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')

    xml_lines.append('</urlset>')

    return HttpResponse("\n".join(xml_lines), content_type="application/xml")


def generate_robots_txt(request):
    """
    Returns public robots.txt directing crawlers to sitemap and disallowing private app paths.
    """
    from django.http import HttpResponse

    content = """User-agent: *
Allow: /
Allow: /about
Allow: /services
Allow: /products
Allow: /case-studies
Allow: /tutorials
Allow: /blog
Allow: /resources
Allow: /contact
Allow: /privacy-policy
Allow: /terms

Disallow: /admin/
Disallow: /api/
Disallow: /login
Disallow: /register
Disallow: /dashboard
Disallow: /profile
Disallow: /compiler
Disallow: /auth/
Disallow: /upload

Sitemap: https://ascentracoresolutions.com/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")

