import os
import json
import uuid
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.text import slugify

from .cms_models import CmsCourse, CmsPage, CmsMedia, CmsBuildJob
from .cms_generator import (
    generate_course_page_files,
    delete_course_page_files,
    update_cms_manifest,
    get_skiltrix_generated_root
)


def _json_body(request):
    if request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except Exception:
            return {}
    return {}


# ==============================================================================
# COURSE METADATA APIS
# ==============================================================================

@csrf_exempt
def cms_courses_api(request):
    """
    GET: List all courses with page counts and status.
    POST: Create a new course metadata record.
    """
    if request.method == "GET":
        courses = CmsCourse.objects.all().order_by("order", "title")
        data = []
        for c in courses:
            data.append({
                "id": c.id,
                "course_id": c.course_id,
                "title": c.title,
                "slug": c.slug,
                "description": c.description,
                "category": c.category,
                "icon": c.icon,
                "status": c.status,
                "order": c.order,
                "pages_count": c.pages.count(),
                "published_count": c.pages.filter(status="published").count(),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            })
        return JsonResponse({"status": True, "courses": data})

    elif request.method == "POST":
        body = _json_body(request)
        title = body.get("title", "").strip()
        if not title:
            return JsonResponse({"status": False, "message": "Course title is required"}, status=400)

        slug = slugify(body.get("slug") or title)
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while CmsCourse.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        course = CmsCourse.objects.create(
            course_id=body.get("course_id") or str(uuid.uuid4())[:12],
            title=title,
            slug=slug,
            description=body.get("description", "").strip(),
            category=body.get("category", "languages"),
            icon=body.get("icon", "book-open"),
            status=body.get("status", "published"),
            order=int(body.get("order", 0)),
        )

        return JsonResponse({
            "status": True,
            "message": "Course created successfully",
            "course": {
                "course_id": course.course_id,
                "title": course.title,
                "slug": course.slug,
                "status": course.status,
            }
        })

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def cms_course_detail_api(request, course_id):
    """
    GET, PUT, DELETE for a specific course.
    """
    course = CmsCourse.objects.filter(course_id=course_id).first() or CmsCourse.objects.filter(slug=course_id).first()
    if not course:
        return JsonResponse({"status": False, "message": "Course not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "status": True,
            "course": {
                "id": course.id,
                "course_id": course.course_id,
                "title": course.title,
                "slug": course.slug,
                "description": course.description,
                "category": course.category,
                "icon": course.icon,
                "status": course.status,
                "order": course.order,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
            }
        })

    elif request.method in ["PUT", "PATCH"]:
        body = _json_body(request)
        if "title" in body:
            course.title = body["title"].strip()
        if "description" in body:
            course.description = body["description"].strip()
        if "category" in body:
            course.category = body["category"]
        if "icon" in body:
            course.icon = body["icon"]
        if "status" in body:
            course.status = body["status"]
        if "order" in body:
            course.order = int(body["order"])
        course.save()
        return JsonResponse({"status": True, "message": "Course updated successfully"})

    elif request.method == "DELETE":
        course.delete()
        update_cms_manifest()
        return JsonResponse({"status": True, "message": "Course deleted successfully"})

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


# ==============================================================================
# PAGE METADATA & CONTENT APIS
# ==============================================================================

@csrf_exempt
def cms_pages_api(request):
    """
    GET: List all pages (filterable by course_id, status, search).
    POST: Create a draft page metadata record.
    """
    if request.method == "GET":
        course_id = request.GET.get("course_id", "").strip()
        status = request.GET.get("status", "").strip()
        search = request.GET.get("search", "").strip()

        qs = CmsPage.objects.all().select_related("course", "parent").order_by("course__order", "page_order", "id")

        if course_id:
            qs = qs.filter(course__course_id=course_id)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(title__icontains=search)

        data = []
        for p in qs:
            data.append({
                "id": p.id,
                "page_id": p.page_id,
                "course_id": p.course.course_id,
                "course_title": p.course.title,
                "course_slug": p.course.slug,
                "parent_id": p.parent.page_id if p.parent else None,
                "parent_title": p.parent.title if p.parent else None,
                "title": p.title,
                "slug": p.slug,
                "url_path": p.url_path,
                "file_path": p.file_path,
                "status": p.status,
                "page_order": p.page_order,
                "video_url": p.video_url,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            })

        return JsonResponse({"status": True, "pages": data, "count": len(data)})

    elif request.method == "POST":
        body = _json_body(request)
        course_id = body.get("course_id", "").strip()
        title = body.get("title", "").strip()
        parent_id = body.get("parent_id")

        if not course_id or not title:
            return JsonResponse({"status": False, "message": "course_id and title are required"}, status=400)

        course = CmsCourse.objects.filter(course_id=course_id).first()
        if not course:
            return JsonResponse({"status": False, "message": "Course not found"}, status=404)

        parent_page = CmsPage.objects.filter(page_id=parent_id).first() if parent_id else None

        slug = slugify(body.get("slug") or title)
        base_slug = slug
        counter = 1
        while CmsPage.objects.filter(course=course, slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Calculate URL path
        if parent_page:
            url_path = f"{parent_page.url_path.rstrip('/')}/{slug}/"
        else:
            url_path = f"/courses/{course.slug}/{slug}/"

        page = CmsPage.objects.create(
            page_id=body.get("page_id") or str(uuid.uuid4())[:14],
            course=course,
            parent=parent_page,
            title=title,
            slug=slug,
            url_path=url_path,
            file_path="",
            css_path="",
            js_path="",
            page_order=int(body.get("page_order", course.pages.count() + 1)),
            status="draft",
            seo_title=body.get("seo_title", ""),
            seo_description=body.get("seo_description", ""),
            video_title=body.get("video_title", ""),
            video_url=body.get("video_url", ""),
            video_thumbnail=body.get("video_thumbnail", ""),
            video_target=body.get("video_target", "_blank"),
        )

        return JsonResponse({
            "status": True,
            "message": "Page draft created successfully",
            "page": {
                "page_id": page.page_id,
                "title": page.title,
                "slug": page.slug,
                "url_path": page.url_path,
                "status": page.status,
            }
        })

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def cms_page_detail_api(request, page_id):
    """
    GET: Get page metadata + read existing published content from disk (if exists).
    PUT/PATCH: Update page metadata.
    DELETE: Delete page metadata, remove generated files, and update manifest.
    """
    page = CmsPage.objects.filter(page_id=page_id).select_related("course", "parent", "prev_page", "next_page").first()
    if not page:
        return JsonResponse({"status": False, "message": "Page not found"}, status=404)

    if request.method == "GET":
        # Read content from generated file if available
        existing_html = ""
        existing_css = ""
        existing_js = ""

        if page.file_path:
            base_dir = Path(settings.BASE_DIR).parent
            tsx_path = base_dir / page.file_path
            if tsx_path.exists():
                try:
                    content = tsx_path.read_text(encoding="utf-8")
                    # Extract the inner HTML content from dangerouslySetInnerHTML={{ __html: `...` }}
                    m = re.search(r'dangerouslySetInnerHTML=\{\{\s*__html:\s*`(.*?)`\s*\}\}', content, re.DOTALL)
                    if m:
                        existing_html = m.group(1).replace('\\`', '`').replace('\\$', '$')
                except Exception as e:
                    print(f"Error reading TSX content: {e}")

        if page.css_path:
            base_dir = Path(settings.BASE_DIR).parent
            css_path = base_dir / page.css_path
            if css_path.exists():
                try:
                    existing_css = css_path.read_text(encoding="utf-8")
                except Exception:
                    pass

        return JsonResponse({
            "status": True,
            "page": {
                "page_id": page.page_id,
                "course_id": page.course.course_id,
                "course_title": page.course.title,
                "course_slug": page.course.slug,
                "parent_id": page.parent.page_id if page.parent else None,
                "parent_title": page.parent.title if page.parent else None,
                "title": page.title,
                "slug": page.slug,
                "url_path": page.url_path,
                "file_path": page.file_path,
                "css_path": page.css_path,
                "js_path": page.js_path,
                "status": page.status,
                "page_order": page.page_order,
                "seo_title": page.seo_title,
                "seo_description": page.seo_description,
                "video_title": page.video_title,
                "video_url": page.video_url,
                "video_thumbnail": page.video_thumbnail,
                "video_target": page.video_target,
                "prev_page_id": page.prev_page.page_id if page.prev_page else None,
                "next_page_id": page.next_page.page_id if page.next_page else None,
                "created_at": page.created_at.isoformat(),
                "updated_at": page.updated_at.isoformat(),
                "content_html": existing_html,
                "content_css": existing_css,
                "content_js": existing_js,
            }
        })

    elif request.method in ["PUT", "PATCH"]:
        body = _json_body(request)
        if "title" in body:
            page.title = body["title"].strip()
        if "seo_title" in body:
            page.seo_title = body["seo_title"].strip()
        if "seo_description" in body:
            page.seo_description = body["seo_description"].strip()
        if "video_title" in body:
            page.video_title = body["video_title"].strip()
        if "video_url" in body:
            page.video_url = body["video_url"].strip()
        if "video_thumbnail" in body:
            page.video_thumbnail = body["video_thumbnail"].strip()
        if "video_target" in body:
            page.video_target = body["video_target"]
        if "page_order" in body:
            page.page_order = int(body["page_order"])
        if "prev_page_id" in body:
            page.prev_page = CmsPage.objects.filter(page_id=body["prev_page_id"]).first()
        if "next_page_id" in body:
            page.next_page = CmsPage.objects.filter(page_id=body["next_page_id"]).first()
        page.save()
        return JsonResponse({"status": True, "message": "Page updated successfully"})

    elif request.method == "DELETE":
        if page.file_path:
            delete_course_page_files(page.file_path)
        page.delete()
        update_cms_manifest()
        return JsonResponse({"status": True, "message": "Page deleted successfully"})

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def cms_publish_page_api(request, page_id):
    """
    POST: Converts editor HTML/content into physical TSX/CSS/JS files,
    updates metadata, sets status to 'published', and refreshes manifest.json.
    """
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "POST required"}, status=405)

    page = CmsPage.objects.filter(page_id=page_id).select_related("course", "parent").first()
    if not page:
        return JsonResponse({"status": False, "message": "Page not found"}, status=404)

    body = _json_body(request)
    html_content = body.get("html_content", "").strip()
    custom_css = body.get("custom_css", "").strip()
    custom_js = body.get("custom_js", "").strip()

    # Optional metadata updates passed with publish
    if body.get("title"):
        page.title = body["title"].strip()
    if body.get("seo_title"):
        page.seo_title = body["seo_title"].strip()
    if body.get("seo_description"):
        page.seo_description = body["seo_description"].strip()
    if "video_url" in body:
        page.video_url = body.get("video_url", "").strip()
        page.video_title = body.get("video_title", "").strip()
        page.video_thumbnail = body.get("video_thumbnail", "").strip()
        page.video_target = body.get("video_target", "_blank")

    if body.get("prev_page_id"):
        page.prev_page = CmsPage.objects.filter(page_id=body["prev_page_id"]).first()
    if body.get("next_page_id"):
        page.next_page = CmsPage.objects.filter(page_id=body["next_page_id"]).first()

    # Determine slug hierarchy for nesting
    hierarchy_slugs = []
    curr = page.parent
    while curr:
        hierarchy_slugs.insert(0, curr.slug)
        curr = curr.parent
    hierarchy_slugs.append(page.slug)

    # Breadcrumbs
    breadcrumbs = [{"label": "Courses", "to": "/courses"}]
    breadcrumbs.append({
        "label": page.course.title,
        "to": f"/courses/{page.course.slug}"
    })

    curr_path = f"/courses/{page.course.slug}"
    curr_crumb = page.parent
    parent_crumbs = []
    while curr_crumb:
        parent_crumbs.insert(0, curr_crumb)
        curr_crumb = curr_crumb.parent

    for pc in parent_crumbs:
        curr_path = f"{curr_path}/{pc.slug}"
        breadcrumbs.append({"label": pc.title, "to": curr_path})

    breadcrumbs.append({"label": page.title})

    # Prepare navigation links
    prev_link = {
        "title": page.prev_page.title,
        "path": page.prev_page.url_path
    } if page.prev_page else None

    next_link = {
        "title": page.next_page.title,
        "path": page.next_page.url_path
    } if page.next_page else None

    video_data = {
        "url": page.video_url,
        "thumbnail": page.video_thumbnail,
        "title": page.video_title or "Lecture Video",
        "target": page.video_target,
    } if page.video_url else None

    # Generate physical files!
    try:
        gen_res = generate_course_page_files(
            course_slug=page.course.slug,
            page_slug_hierarchy=hierarchy_slugs,
            page_title=page.title,
            course_title=page.course.title,
            html_content=html_content,
            custom_css=custom_css,
            custom_js=custom_js,
            breadcrumbs=breadcrumbs,
            prev_page=prev_link,
            next_page=next_link,
            video_data=video_data,
        )

        page.file_path = gen_res["file_path"]
        page.css_path = gen_res["css_path"]
        page.js_path = gen_res["js_path"]
        page.status = "published"
        page.save()

        # Update manifest.json
        manifest = update_cms_manifest()

        return JsonResponse({
            "status": True,
            "message": "Page published and compiled successfully!",
            "url_path": page.url_path,
            "file_path": page.file_path,
            "css_path": page.css_path,
            "manifest_count": len(manifest),
        })

    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": f"Compilation failed: {str(e)}"
        }, status=500)


# ==============================================================================
# HIERARCHY & NAVIGATION REORDER APIS
# ==============================================================================

@csrf_exempt
def cms_navigation_tree_api(request, course_id):
    """
    GET: Returns nested hierarchical tree of all pages for a given course.
    POST: Batch updates page orders and parent relationships.
    """
    course = CmsCourse.objects.filter(course_id=course_id).first() or CmsCourse.objects.filter(slug=course_id).first()
    if not course:
        return JsonResponse({"status": False, "message": "Course not found"}, status=404)

    if request.method == "GET":
        pages = CmsPage.objects.filter(course=course).order_by("page_order", "id")

        # Build recursive hierarchy
        by_parent = {}
        for p in pages:
            pid = p.parent_id
            if pid not in by_parent:
                by_parent[pid] = []
            by_parent[pid].append({
                "page_id": p.page_id,
                "title": p.title,
                "slug": p.slug,
                "url_path": p.url_path,
                "status": p.status,
                "order": p.page_order,
                "parent_id": p.parent.page_id if p.parent else None,
            })

        def build_tree(parent_db_id):
            items = by_parent.get(parent_db_id, [])
            tree = []
            for it in items:
                # Find matching DB id for child lookup
                db_item = next((p for p in pages if p.page_id == it["page_id"]), None)
                children = build_tree(db_item.id) if db_item else []
                it["children"] = children
                tree.append(it)
            return tree

        tree = build_tree(None)
        return JsonResponse({"status": True, "tree": tree, "course": {"title": course.title, "slug": course.slug}})

    elif request.method == "POST":
        body = _json_body(request)
        reorder_list = body.get("pages", [])  # list of { page_id, order, parent_id }

        for item in reorder_list:
            p_id = item.get("page_id")
            order = item.get("order", 1)
            parent_id = item.get("parent_id")

            parent_obj = CmsPage.objects.filter(page_id=parent_id).first() if parent_id else None

            p = CmsPage.objects.filter(page_id=p_id, course=course).first()
            if p:
                p.page_order = int(order)
                p.parent = parent_obj
                p.save()

        update_cms_manifest()
        return JsonResponse({"status": True, "message": "Navigation hierarchy updated successfully"})

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


# ==============================================================================
# MEDIA LIBRARY APIS
# ==============================================================================

@csrf_exempt
def cms_media_api(request):
    """
    GET: List media items with pagination.
    POST: Upload media item (image/thumbnail) and store on disk/S3.
    """
    if request.method == "GET":
        search = request.GET.get("search", "").strip()
        qs = CmsMedia.objects.all().order_by("-created_at")
        if search:
            qs = qs.filter(title__icontains=search)

        data = []
        for m in qs:
            data.append({
                "media_id": m.media_id,
                "title": m.title,
                "file_name": m.file_name,
                "file_url": m.file_url,
                "file_type": m.file_type,
                "file_size_kb": m.file_size_kb,
                "alt_text": m.alt_text,
                "created_at": m.created_at.isoformat(),
            })
        return JsonResponse({"status": True, "media": data, "count": len(data)})

    elif request.method == "POST":
        if "file" not in request.FILES:
            return JsonResponse({"status": False, "message": "No file uploaded"}, status=400)

        uploaded_file = request.FILES["file"]
        title = request.POST.get("title", uploaded_file.name).strip()
        alt_text = request.POST.get("alt_text", "").strip()

        # Save locally under media/cms/
        media_root = Path(settings.MEDIA_ROOT) / "cms"
        media_root.mkdir(parents=True, exist_ok=True)

        ext = os.path.splitext(uploaded_file.name)[1]
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
        destination_path = media_root / unique_name

        with open(destination_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        file_url = f"{settings.MEDIA_URL}cms/{unique_name}"
        file_size_kb = int(uploaded_file.size / 1024)

        media_item = CmsMedia.objects.create(
            media_id=str(uuid.uuid4())[:12],
            title=title,
            file_name=unique_name,
            file_url=file_url,
            file_type=uploaded_file.content_type or "image/png",
            file_size_kb=file_size_kb,
            alt_text=alt_text,
        )

        return JsonResponse({
            "status": True,
            "message": "Media uploaded successfully",
            "media": {
                "media_id": media_item.media_id,
                "title": media_item.title,
                "file_url": media_item.file_url,
                "alt_text": media_item.alt_text,
            }
        })

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)


@csrf_exempt
def cms_media_delete_api(request, media_id):
    """
    DELETE: Delete media item.
    """
    if request.method != "DELETE":
        return JsonResponse({"status": False, "message": "DELETE required"}, status=405)

    media = CmsMedia.objects.filter(media_id=media_id).first()
    if not media:
        return JsonResponse({"status": False, "message": "Media not found"}, status=404)

    # Remove physical file if on disk
    try:
        file_path = Path(settings.MEDIA_ROOT) / "cms" / media.file_name
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    media.delete()
    return JsonResponse({"status": True, "message": "Media deleted successfully"})
