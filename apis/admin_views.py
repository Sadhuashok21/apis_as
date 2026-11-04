import json
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection, models
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from sfs.models import AllUsers, BP, BpCat, BPCategories, TotalActivity, AllErrors
from sfs.utils import unique_id, get_client_ip
from apis.cdn_utils import get_sfs_image_url


def get_admin_stats(request):
    """Aggregate statistics for admin dashboard."""
    try:
        total_bp = BP.objects.count()
        approved_bp = BP.objects.filter(status="approved").count()
        total_cat = BpCat.objects.count()
        total_users = AllUsers.objects.count()

        totals = BP.objects.aggregate(
            views=Sum('views'),
            downloads=Sum('downloads'),
            likes=Sum('likes'),
            shares=Sum('share')
        )

        total_activity = TotalActivity.objects.count()
        total_errors = AllErrors.objects.count()

        # Recent activities
        recent_activities = []
        for a in TotalActivity.objects.order_by('-id')[:5]:
            recent_activities.append({
                "id": a.id,
                "activity_id": a.activity_id,
                "platform": a.platform,
                "platform_name": a.platform_name,
                "time": a.time.strftime('%Y-%m-%d %H:%M') if a.time else "",
                "user": a.user.name if a.user else "System"
            })

        return JsonResponse({
            "status": True,
            "stats": {
                "total_blueprints": total_bp,
                "approved_blueprints": approved_bp,
                "total_categories": total_cat,
                "total_users": total_users,
                "total_views": totals['views'] or 0,
                "total_downloads": totals['downloads'] or 0,
                "total_likes": totals['likes'] or 0,
                "total_shares": totals['shares'] or 0,
                "total_activities": total_activity,
                "total_errors": total_errors,
            },
            "recent_activities": recent_activities
        })
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_admin_analytics(request):
    """Return daily activity and error counts for a bounded date range."""
    today = timezone.localdate()
    try:
        end_date = date.fromisoformat(request.GET.get("end_date", today.isoformat()))
        start_date = date.fromisoformat(
            request.GET.get("start_date", (today - timedelta(days=6)).isoformat())
        )
    except ValueError:
        return JsonResponse(
            {"status": False, "error": "Dates must use YYYY-MM-DD format."},
            status=400,
        )

    if end_date < start_date:
        return JsonResponse(
            {"status": False, "error": "end_date must be on or after start_date."},
            status=400,
        )
    if (end_date - start_date).days > 365:
        return JsonResponse(
            {"status": False, "error": "Date range cannot exceed 366 days."},
            status=400,
        )

    activity_counts = {
        row["day"]: row["total"]
        for row in TotalActivity.objects.filter(
            time__date__range=(start_date, end_date)
        ).annotate(day=TruncDate("time")).values("day").annotate(total=Count("id"))
    }
    error_counts = {
        row["day"]: row["total"]
        for row in AllErrors.objects.filter(
            time__date__range=(start_date, end_date)
        ).annotate(day=TruncDate("time")).values("day").annotate(total=Count("id"))
    }

    daily = []
    current_date = start_date
    while current_date <= end_date:
        daily.append({
            "date": current_date.isoformat(),
            "activities": activity_counts.get(current_date, 0),
            "errors": error_counts.get(current_date, 0),
        })
        current_date += timedelta(days=1)

    return JsonResponse({
        "status": True,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": daily,
    })


@csrf_exempt
def admin_users(request, user_id=None):
    """List, search, filter, update, or delete users."""
    if request.method == "GET":
        try:
            search = request.GET.get("search", "").strip()
            status = request.GET.get("status", "").strip()
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            offset = (page - 1) * limit

            queryset = AllUsers.objects.all().order_by('-id')

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(username__icontains=search) |
                    Q(platform_name__icontains=search)
                )

            if status and status != "all":
                if status == "approved":
                    queryset = queryset.filter(Q(status="approved") | Q(status="") | Q(status__isnull=True))
                else:
                    queryset = queryset.filter(status=status)

            total_count = queryset.count()
            users_page = queryset[offset:offset + limit]

            users_list = []
            for u in users_page:
                users_list.append({
                    "id": u.id,
                    "user_id": u.user_id,
                    "name": u.name or u.username,
                    "email": u.email,
                    "profile": f"https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150" if not u.profile or u.profile == "profile.webp" else u.profile,
                    "status": u.status or "approved",
                    "type": u.user_type or "Member",
                    "platform": u.platform or "Web",
                    "platform_name": u.platform_name or "Browser",
                    "created_at": u.created_at.strftime('%Y-%m-%d') if u.created_at else ""
                })

            return JsonResponse({
                "status": True,
                "total": total_count,
                "page": page,
                "limit": limit,
                "users": users_list
            })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "POST":
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
            name = body.get("name", "").strip()
            email = body.get("email", "").strip()
            status = body.get("status", "approved")
            user_type = body.get("type", "Member")
            platform = body.get("platform", "Web")
            platform_name = body.get("platform_name", "Browser")

            if not name or not email:
                return JsonResponse({"status": False, "error": "Name and email are required"}, status=400)

            # Check if email exists
            if AllUsers.objects.filter(email=email).exists():
                return JsonResponse({"status": False, "error": "User with this email already exists"}, status=400)

            uid = unique_id()
            user = AllUsers.objects.create(
                username=uid[:15],
                name=name,
                email=email,
                user_id=uid,
                status=status,
                user_type=user_type,
                platform=platform,
                platform_name=platform_name,
                ip=get_client_ip(request)
            )

            return JsonResponse({"status": True, "message": "User created", "user_id": user.user_id})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method in ["PATCH", "PUT"]:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
            target_user_id = user_id or body.get("user_id") or body.get("id")

            if not target_user_id:
                return JsonResponse({"status": False, "error": "User ID required"}, status=400)

            user = AllUsers.objects.filter(Q(id=target_user_id) | Q(user_id=target_user_id)).first()
            if not user:
                return JsonResponse({"status": False, "error": "User not found"}, status=404)

            if "status" in body:
                user.status = body["status"]
            if "name" in body:
                user.name = body["name"]
            if "type" in body:
                user.user_type = body["type"]
            user.save()

            return JsonResponse({"status": True, "message": "User updated successfully"})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "DELETE":
        try:
            target_user_id = user_id or request.GET.get("user_id") or request.GET.get("id")
            if not target_user_id:
                return JsonResponse({"status": False, "error": "User ID required"}, status=400)

            user = AllUsers.objects.filter(Q(id=target_user_id) | Q(user_id=target_user_id)).first()
            if not user:
                return JsonResponse({"status": False, "error": "User not found"}, status=404)

            user.delete()
            return JsonResponse({"status": True, "message": "User deleted successfully"})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)


@csrf_exempt
def admin_logs(request):
    """Retrieve system logs from AllErrors and TotalActivity with unified or filtered streams."""
    try:
        log_type = request.GET.get("type", "all")
        search = request.GET.get("search", "").strip()
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 50))
        offset = (page - 1) * limit

        logs_list = []

        if log_type == "errors":
            query = AllErrors.objects.all().order_by('-id')
            if search:
                query = query.filter(
                    Q(error_msg__icontains=search) |
                    Q(activity__icontains=search) |
                    Q(platform_name__icontains=search) |
                    Q(ip__icontains=search)
                )
            total = query.count()
            for err in query[offset:offset + limit]:
                code = err.error_code if (err.error_code and err.error_code != 200) else 500
                logs_list.append({
                    "id": f"ERR-{err.id}",
                    "raw_id": err.id,
                    "time": err.time.strftime('%Y-%m-%d %H:%M:%S') if err.time else "",
                    "user": err.user.name if err.user else "System",
                    "user_id": err.user.user_id if err.user else "System",
                    "error_code": code,
                    "error_msg": err.error_msg,
                    "change": f"System Alert [{code}]: {err.error_msg[:120]}...",
                    "activity_id": err.activity or "SYSTEM_ERROR",
                    "platform": err.platform or "website",
                    "platform_name": err.platform_name or "sfs",
                    "ip": err.ip or "127.0.0.1",
                    "version": err.version or "1.0",
                    "status": "Failed" if code >= 400 else "Logged"
                })

        elif log_type in ["total", "activity"]:
            query = TotalActivity.objects.all().order_by('-id')
            if search:
                query = query.filter(
                    Q(activity_id__icontains=search) |
                    Q(platform_name__icontains=search) |
                    Q(ip__icontains=search)
                )
            total = query.count()
            for act in query[offset:offset + limit]:
                act_name = act.activity_id or "Action"
                logs_list.append({
                    "id": f"ACT-{act.id}",
                    "raw_id": act.id,
                    "time": act.time.strftime('%Y-%m-%d %H:%M:%S') if act.time else "",
                    "user": act.user.name if act.user else "Anonymous",
                    "user_id": act.user.user_id if act.user else "System",
                    "error_code": 200,
                    "error_msg": f"Action: {act_name}",
                    "change": f"Action '{act_name}' logged on {act.platform_name} ({act.platform})",
                    "activity_id": act_name,
                    "utm_source": getattr(act, "utm_source", None) or "",
                    "platform": act.platform or "website",
                    "platform_name": act.platform_name or "sfs",
                    "ip": act.ip or "127.0.0.1",
                    "version": act.version or "1.0",
                    "status": "Success"
                })

        else:
            # "all": Combined stream of recent errors + activities
            err_query = AllErrors.objects.all().order_by('-id')[:limit]
            act_query = TotalActivity.objects.all().order_by('-id')[:limit]

            combined = []
            for err in err_query:
                code = err.error_code if (err.error_code and err.error_code != 200) else 500
                combined.append({
                    "id": f"ERR-{err.id}",
                    "raw_id": err.id,
                    "time_dt": err.time,
                    "time": err.time.strftime('%Y-%m-%d %H:%M:%S') if err.time else "",
                    "user": err.user.name if err.user else "System",
                    "user_id": err.user.user_id if err.user else "System",
                    "error_code": code,
                    "error_msg": err.error_msg,
                    "change": f"System Alert [{code}]: {err.error_msg[:120]}...",
                    "activity_id": err.activity or "SYSTEM_ERROR",
                    "platform": err.platform or "website",
                    "platform_name": err.platform_name or "sfs",
                    "ip": err.ip or "127.0.0.1",
                    "version": err.version or "1.0",
                    "status": "Failed" if code >= 400 else "Logged"
                })

            for act in act_query:
                act_name = act.activity_id or "Action"
                combined.append({
                    "id": f"ACT-{act.id}",
                    "raw_id": act.id,
                    "time_dt": act.time,
                    "time": act.time.strftime('%Y-%m-%d %H:%M:%S') if act.time else "",
                    "user": act.user.name if act.user else "Anonymous",
                    "user_id": act.user.user_id if act.user else "System",
                    "error_code": 200,
                    "error_msg": f"Action: {act_name}",
                    "change": f"Action '{act_name}' logged on {act.platform_name} ({act.platform})",
                    "activity_id": act_name,
                    "utm_source": getattr(act, "utm_source", None) or "",
                    "platform": act.platform or "website",
                    "platform_name": act.platform_name or "sfs",
                    "ip": act.ip or "127.0.0.1",
                    "version": act.version or "1.0",
                    "status": "Success"
                })

            combined.sort(key=lambda x: str(x.get("time_dt") or x.get("time")), reverse=True)
            for item in combined:
                item.pop("time_dt", None)

            if search:
                combined = [
                    item for item in combined
                    if search.lower() in item["error_msg"].lower()
                    or search.lower() in item["activity_id"].lower()
                    or search.lower() in item["user"].lower()
                    or search in item["ip"]
                ]

            total = AllErrors.objects.count() + TotalActivity.objects.count()
            logs_list = combined[offset:offset + limit]

        return JsonResponse({
            "status": True,
            "total": total,
            "page": page,
            "limit": limit,
            "logs": logs_list
        })
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)


@csrf_exempt
def admin_blueprints(request, bp_id=None):
    """Manage blueprints, approval status, and real vs fake metrics."""
    if request.method == "GET":
        try:
            if bp_id:
                bp = BP.objects.filter(bp_id=bp_id).first()
                if not bp:
                    return JsonResponse({"status": False, "error": "Blueprint not found"}, status=404)
                cats = [c.category.bp_name for c in BPCategories.objects.filter(bp=bp).select_related('category')]
                return JsonResponse({
                    "status": True,
                    "blueprint": {
                        "bp_id": bp.bp_id,
                        "name": bp.name,
                        "image": bp.image or "",
                        "image_url": get_sfs_image_url(bp.image),
                        "type": bp.type,
                        "categories": cats if cats else ["General"],
                        "downloads": bp.downloads,
                        "likes": bp.likes,
                        "views": bp.views,
                        "share": bp.share,
                        "fdownloads": bp.fdownloads,
                        "flikes": bp.flikes,
                        "fviews": bp.fviews,
                        "fshare": bp.fshare,
                        "sfs_link": bp.sfs_link,
                        "status": bp.status or "approved",
                        "user": {
                            "name": bp.user.name if bp.user else "Space Flight Simulator",
                            "email": bp.user.email if bp.user else ""
                        },
                        "created_at": bp.time.strftime('%Y-%m-%d') if bp.time else ""
                    }
                })

            search = request.GET.get("search", "").strip()
            bp_type = request.GET.get("type", "").strip()
            status = request.GET.get("status", "").strip()
            page = int(request.GET.get("page", 1))
            limit = int(request.GET.get("limit", 20))
            offset = (page - 1) * limit

            queryset = BP.objects.all().order_by('-id')

            if bp_type and bp_type != "all":
                queryset = queryset.filter(type=bp_type)

            if status and status != "all":
                queryset = queryset.filter(status=status)

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(bp_id__icontains=search) |
                    Q(user__name__icontains=search)
                )

            total = queryset.count()
            page_bps = queryset[offset:offset + limit]

            bp_list = []
            for bp in page_bps:
                cats = [c.category.bp_name for c in BPCategories.objects.filter(bp=bp).select_related('category')]
                bp_list.append({
                    "bp_id": bp.bp_id,
                    "name": bp.name,
                    "image": bp.image or "",
                        "image_url": get_sfs_image_url(bp.image),
                    "type": bp.type,
                    "categories": cats if cats else ["General"],
                    "downloads": bp.downloads,
                    "likes": bp.likes,
                    "views": bp.views,
                    "share": bp.share,
                    "fdownloads": bp.fdownloads,
                    "flikes": bp.flikes,
                    "fviews": bp.fviews,
                    "fshare": bp.fshare,
                    "sfs_link": bp.sfs_link,
                    "status": bp.status or "approved",
                    "user": {
                        "name": bp.user.name if bp.user else "Space Flight Simulator",
                        "email": bp.user.email if bp.user else ""
                    },
                    "created_at": bp.time.strftime('%Y-%m-%d') if bp.time else ""
                })

            return JsonResponse({
                "status": True,
                "total": total,
                "page": page,
                "limit": limit,
                "blueprints": bp_list
            })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method in ["PATCH", "PUT"]:
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
            target_id = bp_id or body.get("bp_id")

            bp = BP.objects.filter(bp_id=target_id).first()
            if not bp:
                return JsonResponse({"status": False, "error": "Blueprint not found"}, status=404)

            # Update status
            if "status" in body:
                bp.status = body["status"]

            # Update fake or real metrics (matching edit_bp.html)
            if "fdownloads" in body:
                bp.fdownloads = int(body["fdownloads"])
            if "flikes" in body:
                bp.flikes = int(body["flikes"])
            if "fviews" in body:
                bp.fviews = int(body["fviews"])
            if "fshare" in body:
                bp.fshare = int(body["fshare"])
            if "name" in body:
                bp.name = body["name"]
            if "type" in body:
                bp.type = body["type"]
            if "sfs_link" in body:
                bp.sfs_link = body["sfs_link"]

            bp.save()
            return JsonResponse({"status": True, "message": "Blueprint updated successfully"})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "DELETE":
        try:
            target_id = bp_id or request.GET.get("bp_id")
            bp = BP.objects.filter(bp_id=target_id).first()
            if not bp:
                return JsonResponse({"status": False, "error": "Blueprint not found"}, status=404)
            bp.delete()
            return JsonResponse({"status": True, "message": "Blueprint deleted successfully"})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)


def upload_category_image_to_s3(image_file):
    """
    Upload category banner image to sfs-blueprints S3 bucket under sfs/images/<new_image>
    using boto3, matching the blueprint upload architecture.
    """
    import os
    import boto3
    from django.conf import settings
    from sfs.utils import unique_id

    ext = image_file.name.split('.')[-1].lower() if '.' in image_file.name else 'png'
    new_image = f"{unique_id()}.{ext}"
    content_type = getattr(image_file, 'content_type', None) or 'image/png'

    endpoint_url = os.getenv("endpoint_url") or getattr(settings, "R2_ENDPOINT_URL", "")
    aws_access_key_id = os.getenv("aws_access_key_id") or getattr(settings, "R2_ACCESS_KEY_ID", "")
    aws_secret_access_key = os.getenv("aws_secret_access_key") or getattr(settings, "R2_SECRET_ACCESS_KEY", "")
    bucket = getattr(settings, "R2_BUCKET_NAME", "sfs-blueprints")

    # 1. Boto3 S3 upload to sfs-blueprints bucket
    try:
        s3 = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name="auto",
        )
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        s3.put_object(
            Bucket=bucket,
            Key=f"sfs/images/{new_image}",
            Body=image_file,
            ContentType=content_type,
        )
    except Exception as e:
        print(f"[boto3 S3 upload] Category banner upload failed: {e}")

    # 2. Local media backup for offline/dev resilience
    try:
        media_root = getattr(settings, "MEDIA_ROOT", "media")
        local_dir = os.path.join(media_root, "sfs", "images")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, new_image)
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        with open(local_path, "wb") as f:
            for chunk in image_file.chunks():
                f.write(chunk)
    except Exception as e:
        print(f"[Category Local Backup] Backup error: {e}")

    return new_image


@csrf_exempt
def admin_categories(request, cat_id=None):
    """Retrieve, create, edit, or delete blueprint categories with boto3 S3 banner image uploads."""
    if request.method == "GET":
        try:
            categories = BpCat.objects.all().order_by('-id')
            cat_list = []
            for c in categories:
                count = BPCategories.objects.filter(category=c).count()
                cat_list.append({
                    "id": c.id,
                    "category_id": c.category_id,
                    "bp_name": c.bp_name,
                    "bp_img": c.bp_img or "",
                    "image_url": get_sfs_image_url(c.bp_img),
                    "bp_para": c.bp_para,
                    "status": c.status or "approved",
                    "blueprint_count": count
                })
            return JsonResponse({"status": True, "categories": cat_list})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method in ("POST", "PUT"):
        try:
            name = ""
            para = ""
            status_val = "approved"
            target_id = cat_id or request.POST.get("id") or request.POST.get("category_id")
            body_dict = {}

            if request.POST:
                name = request.POST.get("name") or request.POST.get("bp_name") or ""
                para = request.POST.get("description") or request.POST.get("bp_para") or ""
                status_val = request.POST.get("status") or "approved"
                if not target_id:
                    target_id = request.POST.get("id") or request.POST.get("category_id")
            elif request.body:
                try:
                    body_dict = json.loads(request.body.decode('utf-8'))
                    name = body_dict.get("name") or body_dict.get("bp_name") or ""
                    para = body_dict.get("description") or body_dict.get("bp_para") or ""
                    status_val = body_dict.get("status") or "approved"
                    if not target_id:
                        target_id = body_dict.get("id") or body_dict.get("category_id")
                except Exception:
                    pass

            image_file = request.FILES.get("image") or request.FILES.get("cat_img") or request.FILES.get("bp_img")

            # Update existing category if target_id provided
            if target_id:
                if str(target_id).isdigit():
                    cat = BpCat.objects.filter(id=int(target_id)).first() or BpCat.objects.filter(category_id=str(target_id)).first()
                else:
                    cat = BpCat.objects.filter(category_id=str(target_id)).first()
                if cat:
                    if name:
                        cat.bp_name = name
                        cat.bp_category = name[:20]
                    if para:
                        cat.bp_para = para
                    if status_val:
                        cat.status = status_val
                    if image_file:
                        cat.bp_img = upload_category_image_to_s3(image_file)
                    cat.save()
                    return JsonResponse({
                        "status": True,
                        "message": "Category updated successfully",
                        "category": {
                            "id": cat.id,
                            "category_id": cat.category_id,
                            "bp_name": cat.bp_name,
                            "bp_img": cat.bp_img,
                            "image_url": get_sfs_image_url(cat.bp_img),
                            "bp_para": cat.bp_para,
                            "status": cat.status
                        }
                    })

            # Create new category
            if not name:
                return JsonResponse({"status": False, "error": "Category name required"}, status=400)

            if image_file:
                new_image = upload_category_image_to_s3(image_file)
            else:
                new_image = request.POST.get("bp_img") or body_dict.get("bp_img", "")
                if not new_image:
                    return JsonResponse({"status": False, "error": "Local banner image file is required"}, status=400)

            user = AllUsers.objects.first()
            new_cat = BpCat.objects.create(
                bp_name=name,
                bp_category=name[:20],
                bp_img=new_image,
                bp_para=para,
                category_id=unique_id(),
                user=user,
                status=status_val,
                ip=get_client_ip(request),
                time=timezone.now()
            )
            return JsonResponse({
                "status": True,
                "message": "Category created successfully",
                "category_id": new_cat.category_id,
                "bp_img": new_cat.bp_img,
                "image_url": get_sfs_image_url(new_cat.bp_img)
            })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "DELETE":
        try:
            target_id = cat_id or request.GET.get("id") or request.GET.get("category_id")
            if not target_id and request.body:
                try:
                    body_dict = json.loads(request.body.decode('utf-8'))
                    target_id = body_dict.get("id") or body_dict.get("category_id")
                except Exception:
                    pass
            if not target_id:
                return JsonResponse({"status": False, "error": "Category ID is required for deletion"}, status=400)
            if str(target_id).isdigit():
                deleted, _ = BpCat.objects.filter(id=int(target_id)).delete()
                if not deleted:
                    deleted, _ = BpCat.objects.filter(category_id=str(target_id)).delete()
            else:
                deleted, _ = BpCat.objects.filter(category_id=str(target_id)).delete()
            return JsonResponse({"status": True, "message": "Category deleted successfully", "deleted": deleted})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)


@csrf_exempt
def admin_transport_hub(request):
    """Retrieve train routes, schedules, and stations."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT train_number, train_name, source_station, destination_station, departure_time, arrival_time FROM trains LIMIT 25")
            trains_data = cursor.fetchall()
            trains_list = []
            for t in trains_data:
                trains_list.append({
                    "route_id": f"TR_{t[0]}",
                    "train_no": str(t[0]),
                    "train_name": t[1],
                    "origin": t[2],
                    "destination": t[3],
                    "departure": str(t[4]) if t[4] else "08:00 AM",
                    "arrival": str(t[5]) if t[5] else "04:30 PM",
                    "status": "On Time"
                })
        return JsonResponse({"status": True, "trains": trains_list})
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)


@csrf_exempt
def admin_database_tables(request):
    """Query live MySQL tables and row counts."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            table_list = []
            for t in tables:
                t_name = t[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{t_name}`")
                    row_count = cursor.fetchone()[0]
                except Exception:
                    row_count = 0
                table_list.append({"table_name": t_name, "rows_count": row_count})

        return JsonResponse({
            "status": True,
            "database_name": connection.settings_dict.get("NAME", "as_main"),
            "tables_count": len(table_list),
            "tables": table_list
        })
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)

