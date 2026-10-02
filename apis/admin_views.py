import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection, models
from django.db.models import Q, Sum
from django.utils import timezone
from shared_lib.sfs_core.models import AllUsers, BP, BpCat, BPCategories
from shared_lib.utils.models import TotalActivity, AllErrors
from shared_lib.utils.random import unique_id, get_client_ip


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

            uid = unique_id(20)
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
                        "image": f"https://images.unsplash.com/photo-1517976487502-5731f30bc482?w=400" if not bp.image or not bp.image.startswith("http") else bp.image,
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
                    "image": f"https://images.unsplash.com/photo-1517976487502-5731f30bc482?w=400" if not bp.image or not bp.image.startswith("http") else bp.image,
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


@csrf_exempt
def admin_categories(request, cat_id=None):
    """List, create, or update blueprint categories."""
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
                    "bp_img": f"https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400" if not c.bp_img or not c.bp_img.startswith("http") else c.bp_img,
                    "bp_para": c.bp_para,
                    "status": c.status or "approved",
                    "blueprint_count": count
                })
            return JsonResponse({"status": True, "categories": cat_list})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "POST":
        try:
            body = json.loads(request.body.decode('utf-8')) if request.body else {}
            name = body.get("bp_name") or body.get("name", "")
            para = body.get("bp_para") or body.get("description", "")
            img = body.get("bp_img", "default.png")

            if not name:
                return JsonResponse({"status": False, "error": "Category name required"}, status=400)

            user = AllUsers.objects.first()
            new_cat = BpCat.objects.create(
                bp_name=name,
                bp_category=name[:20],
                bp_img=img,
                bp_para=para,
                category_id=unique_id(20),
                user=user,
                status="approved",
                ip=get_client_ip(request),
                time=timezone.now()
            )
            return JsonResponse({"status": True, "message": "Category created", "category_id": new_cat.category_id})
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


