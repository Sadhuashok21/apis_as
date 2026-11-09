"""
Ascentracore Admin Accounts & Privileges Management API Views
Handles listing, creating, updating, promoting, and revoking administrative accounts
with granular role-based module privileges.
"""

import json
import uuid
import secrets
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils import timezone
from sfs.models import AllUsers
from accounts.models import UserProfile

# Default full privileges
DEFAULT_PRIVILEGES = {
    "can_manage_cms": True,
    "can_manage_courses": True,
    "can_manage_sfs": True,
    "can_manage_sonicora": True,
    "can_manage_skiltrix": True,
    "can_manage_users": True,
    "can_manage_admins": True,
    "can_manage_database": True,
    "can_view_logs": True,
    "can_manage_payments": True,
    "can_manage_inquiries": True,
}

# Role presets
ROLE_PRESETS = {
    "Super Admin": {
        "can_manage_cms": True,
        "can_manage_courses": True,
        "can_manage_sfs": True,
        "can_manage_sonicora": True,
        "can_manage_skiltrix": True,
        "can_manage_users": True,
        "can_manage_admins": True,
        "can_manage_database": True,
        "can_view_logs": True,
        "can_manage_payments": True,
        "can_manage_inquiries": True,
    },
    "CMS Manager": {
        "can_manage_cms": True,
        "can_manage_courses": True,
        "can_manage_sfs": False,
        "can_manage_sonicora": False,
        "can_manage_skiltrix": False,
        "can_manage_users": False,
        "can_manage_admins": False,
        "can_manage_database": False,
        "can_view_logs": False,
        "can_manage_payments": False,
        "can_manage_inquiries": False,
    },
    "SFS Moderator": {
        "can_manage_cms": False,
        "can_manage_courses": False,
        "can_manage_sfs": True,
        "can_manage_sonicora": False,
        "can_manage_skiltrix": False,
        "can_manage_users": False,
        "can_manage_admins": False,
        "can_manage_database": False,
        "can_view_logs": False,
        "can_manage_payments": False,
        "can_manage_inquiries": False,
    },
    "Platform Manager": {
        "can_manage_cms": True,
        "can_manage_courses": True,
        "can_manage_sfs": True,
        "can_manage_sonicora": True,
        "can_manage_skiltrix": True,
        "can_manage_users": True,
        "can_manage_admins": False,
        "can_manage_database": False,
        "can_view_logs": True,
        "can_manage_payments": True,
        "can_manage_inquiries": True,
    },
    "Support & Inquiries": {
        "can_manage_cms": False,
        "can_manage_courses": False,
        "can_manage_sfs": False,
        "can_manage_sonicora": False,
        "can_manage_skiltrix": False,
        "can_manage_users": True,
        "can_manage_admins": False,
        "can_manage_database": False,
        "can_view_logs": True,
        "can_manage_payments": False,
        "can_manage_inquiries": True,
    },
    "Custom Admin": {}
}

AVAILABLE_PRIVILEGES_META = [
    {
        "key": "can_manage_cms",
        "label": "Course Page Builder (CMS)",
        "description": "Create, edit, publish & generate TSX/CSS course pages",
        "category": "Content & Courses"
    },
    {
        "key": "can_manage_courses",
        "label": "Course Catalog & Assessments",
        "description": "Manage courses, syllabus, mocks and coding assessments",
        "category": "Content & Courses"
    },
    {
        "key": "can_manage_sfs",
        "label": "Space Flight Simulator (SFS)",
        "description": "Manage blueprints, categories, mods and planets",
        "category": "Gaming & Blueprints"
    },
    {
        "key": "can_manage_sonicora",
        "label": "SonicOra Media Hub",
        "description": "Upload movies, songs, heroes and media assets",
        "category": "Media & Entertainment"
    },
    {
        "key": "can_manage_skiltrix",
        "label": "SkilTrix Platform",
        "description": "Manage internships, companies, compiler pricing & coupons",
        "category": "Platform & Education"
    },
    {
        "key": "can_manage_users",
        "label": "Platform Users",
        "description": "Manage general member accounts, status, and verification",
        "category": "User & Access Management"
    },
    {
        "key": "can_manage_admins",
        "label": "Admin Accounts & Privileges",
        "description": "Create new admins, assign roles, and grant permissions",
        "category": "User & Access Management"
    },
    {
        "key": "can_manage_database",
        "label": "Database Manager",
        "description": "Inspect database tables and execute safe queries",
        "category": "Infrastructure & System"
    },
    {
        "key": "can_view_logs",
        "label": "System & Error Logs",
        "description": "View system activity audit trail and application errors",
        "category": "Infrastructure & System"
    },
    {
        "key": "can_manage_payments",
        "label": "Payments & Transactions",
        "description": "View payment reports, transaction logs and refund status",
        "category": "Financials & Billing"
    },
    {
        "key": "can_manage_inquiries",
        "label": "Contact Inquiries",
        "description": "View and manage incoming contact and enterprise inquiries",
        "category": "Communications"
    }
]


def _get_admin_data(user):
    """Serialize an administrative user with their assigned role and privileges."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    preferences = profile.preferences or {}

    stored_role = preferences.get("admin_role")
    if not stored_role:
        stored_role = "Super Admin" if (user.user_type or "").lower() == "admin" else "Custom Admin"

    user_privileges = preferences.get("admin_privileges")
    if user_privileges is None:
        # Default all true for primary admins if not explicitly customized
        if (user.user_type or "").lower() == "admin":
            user_privileges = dict(DEFAULT_PRIVILEGES)
        else:
            user_privileges = dict(ROLE_PRESETS.get(stored_role, {}))
            # Fill missing keys with False
            for k in DEFAULT_PRIVILEGES:
                user_privileges.setdefault(k, False)
    else:
        # Guarantee all default keys exist
        merged = {}
        for k in DEFAULT_PRIVILEGES:
            merged[k] = bool(user_privileges.get(k, False))
        user_privileges = merged

    full_name = f"{user.name or ''} {user.lastname or ''}".strip()
    if not full_name:
        full_name = user.username or user.email.split("@")[0]

    avatar = user.profile
    if not avatar or avatar in ["profile.webp", "default.png"]:
        avatar = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"

    return {
        "id": user.id,
        "user_id": user.user_id,
        "username": user.username,
        "name": full_name,
        "first_name": user.name or "",
        "last_name": user.lastname or "",
        "email": user.email,
        "profile": avatar,
        "user_type": user.user_type or "admin",
        "status": user.status or "approved",
        "role": stored_role,
        "privileges": user_privileges,
        "assigned_by": preferences.get("assigned_by", "System"),
        "assigned_at": preferences.get("assigned_at", ""),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@csrf_exempt
def admin_accounts(request):
    """
    GET: List all administrative accounts with roles, privileges, and summary stats.
    POST: Create a brand new administrator account.
    """
    if request.method == "GET":
        try:
            search = request.GET.get("search", "").strip()
            role_filter = request.GET.get("role", "").strip()
            status_filter = request.GET.get("status", "").strip()

            # Query all users designated as admin, superadmin, staff, moderator
            queryset = AllUsers.objects.filter(
                Q(user_type__in=["admin", "superadmin", "staff", "moderator"]) |
                Q(type__in=["admin", "superadmin", "staff", "moderator"])
            ).order_by("-id")

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(lastname__icontains=search) |
                    Q(email__icontains=search) |
                    Q(username__icontains=search)
                )

            if status_filter and status_filter != "all":
                queryset = queryset.filter(status=status_filter)

            # Serialize all admin accounts
            admins_list = []
            for u in queryset:
                data = _get_admin_data(u)
                if role_filter and role_filter != "all" and data["role"] != role_filter:
                    continue
                admins_list.append(data)

            # Compute statistics
            total_admins = len(admins_list)
            active_admins = sum(1 for a in admins_list if a["status"] == "approved")
            suspended_admins = sum(1 for a in admins_list if a["status"] == "suspended")
            super_admins = sum(1 for a in admins_list if a["role"] == "Super Admin")
            cms_managers = sum(1 for a in admins_list if a["role"] == "CMS Manager")
            sfs_moderators = sum(1 for a in admins_list if a["role"] == "SFS Moderator")
            other_roles = total_admins - (super_admins + cms_managers + sfs_moderators)

            return JsonResponse({
                "status": True,
                "total_count": total_admins,
                "stats": {
                    "total_admins": total_admins,
                    "active_admins": active_admins,
                    "suspended_admins": suspended_admins,
                    "super_admins": super_admins,
                    "cms_managers": cms_managers,
                    "sfs_moderators": sfs_moderators,
                    "other_roles": max(0, other_roles),
                },
                "roles": list(ROLE_PRESETS.keys()),
                "available_privileges": AVAILABLE_PRIVILEGES_META,
                "admins": admins_list,
            })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
            name = body.get("name", "").strip()
            lastname = body.get("lastname", "").strip()
            email = body.get("email", "").strip().lower()
            password = body.get("password", "").strip()
            role = body.get("role", "Super Admin").strip()
            status_val = body.get("status", "approved").strip()
            privileges = body.get("privileges", {})

            if not email or not password or not name:
                return JsonResponse({
                    "status": False,
                    "error": "Name, email, and password are required."
                }, status=400)

            # Check if email already registered
            if AllUsers.objects.filter(email=email).exists():
                return JsonResponse({
                    "status": False,
                    "error": f"An account with email '{email}' already exists."
                }, status=400)

            # Generate unique user_id
            user_id = secrets.token_hex(10).upper()
            username = email.split("@")[0] + "_" + secrets.token_hex(3)

            # Calculate privileges based on role preset if privileges not provided
            if not privileges or not isinstance(privileges, dict):
                privileges = dict(ROLE_PRESETS.get(role, DEFAULT_PRIVILEGES))
            else:
                # Merge with default keys
                merged = {}
                for k in DEFAULT_PRIVILEGES:
                    merged[k] = bool(privileges.get(k, False))
                privileges = merged

            user = AllUsers(
                user_id=user_id,
                username=username,
                name=name,
                lastname=lastname,
                email=email,
                user_type="admin",
                type="admin",
                status=status_val,
                platform="Web",
                platform_name="Admin Management Portal",
            )
            user.set_password(password)
            user.save()

            # Store privileges in UserProfile preferences
            profile, _ = UserProfile.objects.get_or_create(user=user)
            prefs = profile.preferences or {}
            prefs["admin_role"] = role
            prefs["admin_privileges"] = privileges
            prefs["assigned_by"] = "Admin Portal"
            prefs["assigned_at"] = timezone.now().isoformat()
            profile.preferences = prefs
            profile.save()

            return JsonResponse({
                "status": True,
                "message": f"Administrator '{full_name_label(name, lastname)}' created successfully.",
                "admin": _get_admin_data(user),
            }, status=201)
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)


def full_name_label(first, last):
    return f"{first} {last}".strip()


@csrf_exempt
def admin_account_detail(request, user_id):
    """
    GET: Get details of a single admin account.
    PUT: Update an admin's role, granular privileges, status, or reset password.
    DELETE: Demote admin to regular Member or delete account.
    """
    user = AllUsers.objects.filter(user_id=user_id).first()
    if not user:
        return JsonResponse({"status": False, "error": f"Admin with ID '{user_id}' not found."}, status=404)

    if request.method == "GET":
        try:
            return JsonResponse({"status": True, "admin": _get_admin_data(user)})
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "PUT":
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}

            if "name" in body:
                user.name = body["name"].strip()
            if "lastname" in body:
                user.lastname = body["lastname"].strip()
            if "status" in body:
                user.status = body["status"].strip()

            # Optional password reset
            new_password = body.get("password", "").strip()
            if new_password:
                if len(new_password) < 6:
                    return JsonResponse({"status": False, "error": "Password must be at least 6 characters."}, status=400)
                user.set_password(new_password)

            user.save()

            # Update UserProfile preferences (role & privileges)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            prefs = profile.preferences or {}

            if "role" in body:
                prefs["admin_role"] = body["role"].strip()

            if "privileges" in body and isinstance(body["privileges"], dict):
                current_privs = prefs.get("admin_privileges", {})
                for k in DEFAULT_PRIVILEGES:
                    if k in body["privileges"]:
                        current_privs[k] = bool(body["privileges"][k])
                prefs["admin_privileges"] = current_privs

            prefs["updated_at"] = timezone.now().isoformat()
            profile.preferences = prefs
            profile.save()

            return JsonResponse({
                "status": True,
                "message": f"Admin account '{user.email}' updated successfully.",
                "admin": _get_admin_data(user),
            })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    elif request.method == "DELETE":
        try:
            action = request.GET.get("action", "demote").strip().lower()

            if action == "delete":
                email = user.email
                user.delete()
                return JsonResponse({
                    "status": True,
                    "message": f"Administrator account '{email}' permanently deleted."
                })
            else:
                # Default: Demote to regular user
                user.user_type = "user"
                user.type = "user"
                user.save()

                # Remove admin privileges from preferences
                profile, _ = UserProfile.objects.get_or_create(user=user)
                prefs = profile.preferences or {}
                prefs.pop("admin_role", None)
                prefs.pop("admin_privileges", None)
                prefs["demoted_at"] = timezone.now().isoformat()
                profile.preferences = prefs
                profile.save()

                return JsonResponse({
                    "status": True,
                    "message": f"Administrator '{user.email}' demoted to regular member successfully."
                })
        except Exception as e:
            return JsonResponse({"status": False, "error": str(e)}, status=500)

    return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)


@csrf_exempt
def admin_account_promote(request):
    """
    POST: Promote an existing registered platform user to Administrator with specific role & privileges.
    """
    if request.method != "POST":
        return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
        user_id = body.get("user_id", "").strip()
        email = body.get("email", "").strip().lower()
        role = body.get("role", "Super Admin").strip()
        privileges = body.get("privileges", {})

        user = None
        if user_id:
            user = AllUsers.objects.filter(user_id=user_id).first()
        elif email:
            user = AllUsers.objects.filter(email=email).first()

        if not user:
            return JsonResponse({"status": False, "error": "User not found."}, status=404)

        # Update user to admin
        user.user_type = "admin"
        user.type = "admin"
        user.status = "approved"
        user.save()

        # Update UserProfile preferences
        profile, _ = UserProfile.objects.get_or_create(user=user)
        prefs = profile.preferences or {}

        # Merge privileges
        if not privileges or not isinstance(privileges, dict):
            privileges = dict(ROLE_PRESETS.get(role, DEFAULT_PRIVILEGES))
        else:
            merged = {}
            for k in DEFAULT_PRIVILEGES:
                merged[k] = bool(privileges.get(k, False))
            privileges = merged

        prefs["admin_role"] = role
        prefs["admin_privileges"] = privileges
        prefs["promoted_at"] = timezone.now().isoformat()
        prefs["assigned_by"] = "Admin Portal"
        profile.preferences = prefs
        profile.save()

        return JsonResponse({
            "status": True,
            "message": f"User '{user.email}' successfully promoted to {role}.",
            "admin": _get_admin_data(user),
        })
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)


@csrf_exempt
def admin_search_users(request):
    """
    GET: Search platform users to find candidates for promotion to Admin.
    """
    if request.method != "GET":
        return JsonResponse({"status": False, "error": "Method not allowed"}, status=405)

    try:
        query = request.GET.get("q", "").strip()
        if not query:
            return JsonResponse({"status": True, "users": []})

        # Search non-admin users
        candidates = AllUsers.objects.filter(
            Q(name__icontains=query) |
            Q(lastname__icontains=query) |
            Q(email__icontains=query) |
            Q(username__icontains=query)
        ).exclude(user_type__in=["admin", "superadmin"])[:15]

        results = []
        for u in candidates:
            full_name = f"{u.name or ''} {u.lastname or ''}".strip() or u.username or u.email
            avatar = u.profile if u.profile and u.profile not in ["profile.webp", "default.png"] else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"
            results.append({
                "id": u.id,
                "user_id": u.user_id,
                "name": full_name,
                "email": u.email,
                "username": u.username,
                "profile": avatar,
                "status": u.status or "approved",
                "user_type": u.user_type or "Member",
            })

        return JsonResponse({"status": True, "users": results})
    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)}, status=500)
