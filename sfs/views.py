from django.shortcuts import render
from .models import *
from django.http import JsonResponse
from django.utils import timezone
import hashlib, os
from . import utils
from django.db import connection
from .models import *
from .utils import get_client_ip, unique_id
from django.db.models import Count, F, Q
from django.views import View
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, status
from .pagination import StandardResultsSetPagination, BlueprintPagination, PlanetPagination, ModsPagination

from .serializers import *

load_dotenv()

class BPSerializers(generics.ListCreateAPIView):
    """
    DRF List and Create API view for blueprints with pagination.
    Supports ?page=, ?off=, ?page_size=, and optional ?type= or ?status= filtering.
    """
    serializer_class = BpSerializers
    pagination_class = BlueprintPagination

    def get_queryset(self):
        queryset = BP.objects.filter(status="approved").order_by("-id")
        bp_type = self.request.query_params.get("type")
        if bp_type:
            queryset = queryset.filter(type=bp_type)
        return queryset

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    


# Create your views here.

def get_user_object(user_id_input):
    if not user_id_input:
        return None
    user_obj = AllUsers.objects.filter(
        Q(user_id=user_id_input) | Q(email=user_id_input) | Q(username=user_id_input)
    ).first()
    if not user_obj and str(user_id_input).isdigit():
        user_obj = AllUsers.objects.filter(id=int(user_id_input)).first()
    return user_obj


def like(request):
    bp_id = request.GET.get('bp_id', '')
    user_id = request.GET.get('user_id', '')

    if bp_id and user_id:
        user_obj = get_user_object(user_id)
        effective_user_id = user_obj.user_id if user_obj else user_id

        blueprint = BP.objects.filter(bp_id=bp_id).first()

        if blueprint is None:
            return JsonResponse({"status": False, "message": "Blueprint not found."}, safe=False)

        favorite = BpDlv.objects.filter(
            Q(user_id=effective_user_id) | Q(user_id=user_id),
            bp_pla_id=bp_id,
            type="like"
        ).first()

        if favorite:
            favorite.delete()

            if blueprint.flikes > 0:
                blueprint.flikes -= 1
            if blueprint.likes > 0:
                blueprint.likes -= 1
            blueprint.save()

            Favorites.objects.filter(
                Q(user_id=effective_user_id) | Q(user_id=user_id),
                bp_id=bp_id
            ).delete()

            return JsonResponse({"status": True, "message": "Unliked successfully.", "liked": False}, safe=False)
        else:
            Favorites.objects.create(user_id=effective_user_id, bp_id=bp_id, status="approved", time=timezone.now())
            BpDlv.objects.create(
                ip = get_client_ip(request),
                platform_name = "app",
                platform = "sfs",
                version = "2.100",
                type="like",
                download_type = "null",
                bp_pla_id=bp_id,
                user_id=effective_user_id,
                dlv_id = unique_id(),
                time=timezone.now(),
            )
            blueprint.flikes += 1
            blueprint.likes += 1
            blueprint.save()

            return JsonResponse({"status": True, "message": "Liked successfully.", "liked": True}, safe=False)
    else:
        return JsonResponse({"status": False, "message": "Missing user id or blueprint id."}, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class Upload(View):
    

    def post(self, request):
        name = request.POST.get('name', '').strip()
        image = request.FILES.get('image', '')
        zipfile = request.FILES.get('zip_file', '')
        sfs_link = request.POST.get('sfs_link', '').strip()
        raw_type = request.POST.get('type', '').strip().lower()
        user_id = request.POST.get('user_id', '').strip()
        description = request.POST.get('description', '').strip()
      
        categories = request.POST.getlist('categories')

        # Normalize type: blueprint, planet, mod
        if raw_type in ('bp', 'blueprint'):
            item_type = 'blueprint'
        elif raw_type in ('planet', 'planets', 'world', 'worlds'):
            item_type = 'planet'
        elif raw_type in ('mod', 'mods'):
            item_type = 'mod'
        else:
            item_type = raw_type

        data = {
            "status": True,
            "message": "success"
        }

        if item_type in ("select", ""):
            return JsonResponse({"status": False, "message": "Please select a valid type (blueprint, planet, or mod)."}, safe=False)

        # Fallback to authenticated user if user_id was not explicitly in POST
        if not user_id and request.user.is_authenticated:
            user_id = getattr(request.user, 'user_id', '') or str(request.user.id)
        if not user_id:
            user_id = request.headers.get('X-User-Id', '')

        user_obj = get_user_object(user_id)
        effective_user_id = user_obj.user_id if user_obj and hasattr(user_obj, 'user_id') else user_id
        
        if name and image and zipfile and item_type and effective_user_id:
            import boto3
            new_image = unique_id() + "." + image.name.split('.')[-1]
            new_zip = unique_id() + "." + zipfile.name.split('.')[-1]

            s3 = boto3.client(
                service_name="s3",
                endpoint_url=os.getenv("endpoint_url"),
                aws_access_key_id=os.getenv("aws_access_key_id"),
                aws_secret_access_key=os.getenv("aws_secret_access_key"),
                region_name="auto",
            )

            bp_id = unique_id()
            effective_sfs_link = sfs_link if sfs_link else "none"

            bp = BP.objects.create(
                name=name,
                image=new_image,
                zipfiles=new_zip,
                sfs_link=effective_sfs_link,
                type=item_type,
                bp_id=bp_id,
                status="approved",
                description=description,
                ip=request.META.get('REMOTE_ADDR') or get_client_ip(request),
                user_id=effective_user_id,
                time=timezone.now(),
            )

            for cat_id in categories:
                BPCategories.objects.create(
                    bp_id=bp_id,
                    category_id=cat_id,
                    time=timezone.now(),
                    ip=request.META.get('REMOTE_ADDR') or get_client_ip(request),
                    status="approved",
                )

            s3.put_object(
                Bucket="sfs-blueprints",
                Key="sfs/images/" + new_image,
                Body=image,
                ContentType=image.content_type,
            )

            s3.put_object(
                Bucket="sfs-blueprints",
                Key="sfs/zipfiles/" + new_zip,
                Body=zipfile,
                ContentType=zipfile.content_type,
            )

            data.update({
                "image_url": f"https://cdn.ascentracoresolutions.com/sfs/images/{new_image}",
                "zip_url": f"https://cdn.ascentracoresolutions.com/sfs/zipfiles/{new_zip}",
                "bp_id": bp_id,
                "type": item_type,
            })

            return JsonResponse(data, safe=False)        
        
        else:
            missing = []
            if not name: missing.append("name")
            if not image: missing.append("image")
            if not zipfile: missing.append("file")
            if not item_type: missing.append("type")
            if not effective_user_id: missing.append("user_id")
            return JsonResponse({"status": False, "message": f"Missing required fields: {', '.join(missing)}"}, safe=False)



def device_fcm(request):
    fcm = request.GET.get('fcm', '')
    user_id = request.GET.get('user_id', '')

    platform = request.GET.get('platform', '')
    platform_name = request.GET.get('platform_name', '')

    data = {
        "status": True,
        "message": "success",
    }

    if fcm:
        check = DeviceFCM.objects.filter(device=fcm).first()
        if check:
            data.update({"message": "exists"})
            return JsonResponse(data, safe=False)
        


    if fcm and platform and platform_name:
        DeviceFCM.objects.create(
                user_id= user_id if user_id else None,
                platform=platform,
                platform_name=platform_name,
                device_id=unique_id(),
                device = fcm
            )

        return JsonResponse(data, safe=False)
    else:
        data.update({"message": "no"})
        return JsonResponse(data, safe=False)


def favorites_2_1(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
            "status": True,
            "message": "success"
        }
    if user_id:
        favorites = Favorites.objects.filter(user_id = user_id, status = 'approved').select_related('bp').values("bp__name", "bp__image", "bp__fviews", "bp__flikes", "bp__fdownloads", "bp__fshare", "bp__comments", "bp__bp_id", "bp__user__name")
        if favorites:

            data.update({"favorites": list(favorites)})
        else:
            data.update({"action": "no"})
            data.update({"favorites": "no"})
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe= False)



def check_like(request):
    bp_id = request.GET.get('bp_id', '')
    user_id = request.GET.get('user_id', '')

    if bp_id and user_id:
        user_obj = get_user_object(user_id)
        effective_user_id = user_obj.user_id if user_obj else user_id

        favorite = BpDlv.objects.filter(
            Q(user_id=effective_user_id) | Q(user_id=user_id),
            bp_pla_id=bp_id,
            type="like"
        ).first()

        if favorite:
            return JsonResponse({"status": True, "liked": True}, safe=False)
        else:
            return JsonResponse({"status": True, "liked": False}, safe=False)
    else:
        return JsonResponse({"status": False, "message": "Missing user id or blueprint id."}, safe=False)

# 2_100 start 

def home_blue_2_100(request):

    data = {
        "status": True,
        "message": "success"
    }

    blueprints = BP.objects.filter(fviews__gte = 1, status="approved", type="blueprint").select_related('user').prefetch_related('bp_category_bp__category').order_by('?')[:5]
    blueprint_list = []

    for bp in blueprints:
        blueprint_list.append({
            "name": bp.name,
            "image": bp.image,
            "views": bp.fviews,
            "likes": bp.flikes,
            "downloads": bp.fdownloads,
            "share": bp.fshare,
            "comments": bp.comments,
            "bp_id": bp.bp_id,
            "user": bp.user.name,

            "categories": [
                {
                    "name": cat.category.bp_name,
                    "cat_id": cat.category.category_id,
                }
                for cat in bp.bp_category_bp.all()
            ]
        })

    data['blueprints'] = blueprint_list

    return JsonResponse(data, safe=False)


def home_pla_2_100(request):

    data = {
        "status": True,
        "message": "success"
    }

    bp = BP.objects.filter(views__gte = 0, status="approved", type="planet").order_by('?').values("views", "name", "image", "fviews", "flikes", "fdownloads", "comments", "fshare", "bp_id", "user__name")[:5]
    
    data['planets'] = list(bp)

    return JsonResponse(data, safe=False)


def home_cat_2_100(request):
        
    data = {
        "status": True,
        "message": "success"
    }

    bp = BpCat.objects.filter(status="approved").annotate(
    blueprint_count=Count('bp_categories__bp', distinct=True)).order_by('?').values("bp_name", "bp_img", "bp_para", "category_id", "blueprint_count")[:5]
    
    data['categories'] = list(bp)

    return JsonResponse(data, safe=False)

# 2_100 end 


def home_blueprints(request):
    blueprints = BP.objects.filter(status = "approved", fviews__gte= 1000)[:10]
    data = {
        "status": True,
        "message": "success",
        "blueprints": list(blueprints.values("name", "image"))

    }
    return JsonResponse(data, safe=False)

def feature(request):
    blueprint = BP.objects.filter(feature=1, status="approved").order_by('?')[:1]
    data = {
        "status": True,
        "message": "success",
    }

    if blueprint:
        data.update({"blueprint": blueprint.values("name", "fviews", "fdownloads", "fshare", "comments", "bp_id")})
    else:
        data.update({"action": "no"})
    return JsonResponse(data, safe=False)


def home_pla(request):
    pla = BP.objects.filter(status="approved", type="planet")

    data = {
        "status": True,
        "message": "success",
        "blueprints": list(pla.values()),
    }

    return JsonResponse(data, safe=False)


class BlueprintsListView(generics.ListAPIView):
    """
    DRF List view for blueprints with PageNumberPagination.
    """
    queryset = BP.objects.filter(status="approved", type="blueprint").order_by("-id")
    serializer_class = BlueprintSummarySerializer
    pagination_class = BlueprintPagination


class PlaworListView(generics.ListAPIView):
    """
    DRF List view for planet worlds with PageNumberPagination.
    """
    queryset = BP.objects.filter(status="approved", type="planet").order_by("-id")
    serializer_class = BlueprintSummarySerializer
    pagination_class = PlanetPagination


class ModsListView(generics.ListAPIView):
    """
    DRF List view for mods with PageNumberPagination.
    """
    queryset = BP.objects.filter(status="approved", type="mod").order_by("-id")
    serializer_class = BlueprintSummarySerializer
    pagination_class = ModsPagination


blueprints = BlueprintsListView.as_view()
plawor = PlaworListView.as_view()
mods = ModsListView.as_view()


# account and signin

def create_account(request):
    fullname = request.GET.get('fullname', '')
    lastname = request.GET.get('lastname', '')
    email = request.GET.get('email', '')
  
    
    data = {
        "status": True,
        "message": "success",
    }

    if fullname and lastname and email:

        user = AllUsers.objects.filter(email=email).first()

        if user:
            data.update({"data": "Email already exists"})
            return JsonResponse(data)
        
        create_user = AllUsers.objects.create(email=email,)

        data.update({"data": "User Created"})

    else:
        data.update({"data": "All are mandatory fields"})
    return JsonResponse(data, safe=False)

def create_account_pass(request):
    password = request.GET.get('password', '')
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
    }

    if password and user_id:

        passw = AllUsers.objects.filter(user_id=user_id).first()

        if passw:
            passw.password = password
            passw.status="approved"
            passw.save()

            
            data.update({"signin": passw.user_id})
        else:
            data.update({"signin": "no"})
    else:
        data.update({"signin": "missing fields"})
    return JsonResponse(data, safe=False)


def change_password(request):
    password = request.GET.get('password', '')
    email = request.GET.get('email', '')
    
    data = {
        "status": True,
        "message": "success",
    }

    if password and email:
        ex = AllUsers.objects.filter(email=email).first()
        if ex:
            ex.password = password
            ex.save()
            data.update({"signin": "updated"})
        else:
            data.update({"signin": "exists"})
    else:
        data.update({"signin": "empty"})
    return JsonResponse(data, safe=False)


def signin(request):
    email = request.GET.get('email', '')
    password = request.GET.get('password', '')
    
    data = {
        "status": True,
        "message": "success",
    }

    if email and password:
        password = hashlib.md5(password.encode()).hexdigest()

        user = AllUsers.objects.filter(status="approved", email=email, password=password).first()
        if user:

            data.update({"data": user.user_id})
        else:
            data.update({"data": "Invalid details"})
        
    else:
        data.update({"data": "email and password mandatory fields"})
    return JsonResponse(data, safe=False)


def profile(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
            "status": True,
            "message": "success"
        }
    if user_id:
        profile = AllUsers.objects.filter(user_id = user_id, status = 'approved').first()

        if profile:

            data.update({"name": profile.name, "email": profile.email})
        else:
            data.update({"action": "no user"})
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe= False)

# account and signin end


def home_cat(request):
    cat = BpCat.objects.filter(status="approved")

    data = {
        "status": True,
        "message": "success",
        "blueprints": cat,
    }

    return JsonResponse(data, safe=False)


def page(request):
    off = request.GET.get('off')

    if off is not None and off.isnumeric():
        off = int(off)

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sfs_bp WHERE status = 'approved' and type='blueprint'")
            rows = cursor.fetchone()[0]

        total_pages = rows // 10 

        if off < 1:
            off = 1

        if off >= total_pages:
            next_page = off
            back_page = off - 1
        else:
            next_page = off + 1
            back_page = off - 1

        # Page dictionary
        if off <= 1:
            pages = {
                "first": 0,
                "empty": 0,
                "back": 0,
                "current": off,
                "next": next_page,
                "empty1": 0,
                "last": total_pages
            }
        else:
            pages = {
                "first": 1,
                "empty": 0,
                "back": back_page,
                "current": off,
                "next": next_page,
                "empty1": 0,
                "last": total_pages
            }

        return JsonResponse({
            "status": True,
            "message": "success",
            "pages": pages
        })

    else:
        return JsonResponse({
            "status": False,
            "message": "empty"
        })


def pla_page(request):
    off = request.GET.get('off')

    if off and off.isnumeric():
        off = int(off)

        rows = BP.objects.filter(status='approved', type='planet').count()

        total_pages = rows // 10

        if off < 1:
            off = 1

        if off >= total_pages:
            next_page = off
            back_page = off - 1
        else:
            next_page = off + 1
            back_page = off - 1

        if off <= 1:
            pages = {
                "first": 0,
                "empty": 0,
                "back": 0,
                "current": off,
                "next": next_page,
                "empty1": 0,
                "last": total_pages
            }
        else:
            pages = {
                "first": 1,
                "empty": 0,
                "back": back_page,
                "current": off,
                "next": next_page,
                "empty1": 0,
                "last": total_pages
            }

        # JSON Response (like echo json_encode)
        return JsonResponse({
            "status": True,
            "message": "success",
            "pages": pages
        })
    
    return JsonResponse({
        "status": True,
        "message": "empty"
    })





def inner_bp(request):
    blueprint_id = request.GET.get('bp_id', '')

    data = {
        "status": True,
        "message": "success",
        }

    if blueprint_id:
        
        blueprint = BP.objects.filter(bp_id = blueprint_id, status = 'approved').first()

        if blueprint:

            data.update({"blueprints": list(blueprint)})
        else:
            data.update({"action": "no blueprint"})

    else:
        data.update({"message": "empty"})
    return JsonResponse(data, safe=False)



# insertions 


def error_insert(request):
    error_id = request.GET.get('error_id', '')
    error_msg = request.GET.get('error_msg', '')
    platform = request.GET.get('platform', '')
    platform_name = request.GET.get('platform_name', '')
    user_id = request.GET.get('user_id', '')
    version = request.GET.get('version', '')

    data = {
        "status": True,
        "message": "success",
    }

    if error_id and error_msg and platform and platform_name and version:
        
        if user_id:
            insert_error = AllErrors.objects.create(
                error_id=error_id,
                error_msg=error_msg,
                user_id=user_id,
                ip=request.META.get('REMOTE_ADDR'),
                platform=platform,
                platform_name=platform_name,
                time=timezone.now(),
            )
            data.update({"data": "Inserted"})
        else:
            insert_error = AllErrors.objects.create(
                    error_id=error_id,
                    error_msg=error_msg,
                    user_id='null',
                    ip=request.META.get('REMOTE_ADDR'),
                    platform=platform,
                    platform_name=platform_name,
                    time=timezone.now(),
                )
            data.update({"data": "Inserted"})

    else:
        data.update({"data": "All are mandatory fields"})
    return JsonResponse(data, safe=False)


def all_insert(request):
    user_id = request.GET.get('user_id', '')
    activity_id = request.GET.get('activity_id', '')
    platform = request.GET.get('platform', '')
    platform_name = request.GET.get('platform_name', '')
    version = request.GET.get('version', '')
    
    data = {
        "status": True,
        "message": "success"
    }

    if activity_id and platform and platform_name and version:
        ip = request.META.get('REMOTE_ADDR')

        if user_id:

            insert = TotalActivity.objects.create(
                    ip = ip, 
                    user_id = user_id,
                    activity_id = activity_id,
                    platform = platform, 
                    platform_name = platform_name,
                    time=timezone.now(),
                )
        else:
            insert = TotalActivity.objects.create(
                    ip = ip, 
                    user_id = 'null',
                    activity_id = activity_id,
                    platform = platform, 
                    platform_name = platform_name,
                    time=timezone.now(),
                )

            
    else:
        data.update({"status": False})
    return JsonResponse(data, safe=False)


def insert_id(request):
    bp_pla_id = request.GET.get('bp_pla_id', '')
    user_id = request.GET.get('user_id', '')
    type = request.GET.get('type', '')
    download_type = request.GET.get('download_type', '')
    platform = request.GET.get('platform', '')
    platform_name = request.GET.get('platform_name', '')
    version = request.GET.get('version', '')

    data = {
        "status": True,
        "message": "success"
    }
    

    if not bp_pla_id or not user_id or not type or not download_type or not version:

        data.update({"user": "missing fields"})
        return JsonResponse(data, safe=False)

    else:
        ip = request.META.get('REMOTE_ADDR')
   
        if type == 'downloads':

            insert = BpDlv.objects.create(
                user_id = user_id, 
                platform=platform, 
                platform_name=platform_name, 
                type=type, 
                download_type=download_type, 
                ip=ip,
                bp_pla_id=bp_pla_id,
                time=timezone.now())
        else:

            insert = BpDlv.objects.create(
            user_id = user_id, 
            platform=platform, 
            platform_name=platform_name, 
            type=type, 
            download_type="null", 
            ip=ip, 
            bp_pla_id=bp_pla_id,
            time=timezone.now())

    return JsonResponse(data, safe=False)



# 2.1 version start


def blueprints_2_1(request):
    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    start = (off_value - 1) * 10
    end = off_value * 10
    data = {
        "status": True,
        "message": "success",
    }


    blueprints = BP.objects.filter(
    status="approved",
    type="blueprint"
    ).select_related('user').prefetch_related('bp_category_bp__category').order_by("-id")[start:end]

    blueprint_list = []

    for bp in blueprints:
        blueprint_list.append({
            "name": bp.name,
            "image": bp.image,
            "views": bp.fviews,
            "likes": bp.flikes,
            "downloads": bp.fdownloads,
            "share": bp.fshare,
            "comments": bp.comments,
            "bp_id": bp.bp_id,
            "user": bp.user.name,

            "categories": [
                {
                    "name": cat.category.bp_name,
                    "cat_id": cat.category.category_id,
                }
                for cat in bp.bp_category_bp.all()
            ]
        })

    data.update({
        "off": off_value,
        "blueprints": blueprint_list
    })
    return JsonResponse(data, safe=False)


def random_blueprints_2_1(request):
    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    start = (off_value - 1) * 10
    end = off_value * 10
    data = {
        "status": True,
        "message": "success",
    }


    blueprints = BP.objects.filter(
    status="approved",
    type="blueprint"
    ).select_related('user').prefetch_related('bp_category_bp__category').order_by("?")[start:end]

    blueprint_list = []

    for bp in blueprints:
        blueprint_list.append({
            "name": bp.name,
            "image": bp.image,
            "views": bp.fviews,
            "likes": bp.flikes,
            "downloads": bp.fdownloads,
            "share": bp.fshare,
            "comments": bp.comments,
            "bp_id": bp.bp_id,
            "user": bp.user.name,

            "categories": [
                {
                    "name": cat.category.bp_name,
                    "cat_id": cat.category.category_id,
                }
                for cat in bp.bp_category_bp.all()
            ]
        })

    data.update({
        "off": off_value,
        "blueprints": blueprint_list
    })
    return JsonResponse(data, safe=False)



def profile_2_1(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
            "status": True,
            "message": "success"
        }
    if user_id:
        profile = AllUsers.objects.filter(user_id = user_id, status = 'approved').first()

        if profile:

            data.update({"name": profile.name, "email": profile.email})
        else:
            data.update({"action": "no user"})
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe= False)


def planets_2_1(request):
    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    start = (off_value - 1) * 10
    end = off_value * 10
    data = {
        "status": True,
        "message": "success",
    }


    planets = BP.objects.filter(status="approved", type="planet").order_by("-id")[start:end]

    data.update({
        "off": off_value,
        "planets":  list(planets.values("name", "image", "fviews", "flikes", "fdownloads", "fshare", "comments", "bp_id", "user__name")), 
        
    })

    return JsonResponse(data, safe=False)



def inner_bp(request):
    blueprint_id = request.GET.get('bp_id', '')

    data = {
        "status": True,
        "message": "success",
        }

    if blueprint_id:
        
        blueprint = BP.objects.filter(bp_id = blueprint_id, status = 'approved')

        if blueprint.exists():

            data.update({"blueprints": blueprint.values("fviews", "flikes", "fdownloads", "fshare", "comments", "bp_id", "description", "sfs_link", "zipfiles", "user__name", "image", "name").first()})
        else:
            data.update({"action": "no blueprint"})

    else:
        data.update({"message": "empty"})
    return JsonResponse(data, safe=False)



def add_favorite(request):
    user_id = request.GET.get('user_id', '')
    bp_pla_id = request.GET.get('bp_pla_id', '')
    type = request.GET.get('type', '')

    data = {
        "status": True,
        "message": "success"
    }

    if user_id and bp_pla_id and type:
        created = Favorites.objects.get_or_create(user_id=user_id, bp_pla_id=bp_pla_id, type=type)
        if created:
            data.update({"data": "Added to favorites"})
        else:
            data.update({"data": "Already in favorites"})
    else:
        data.update({"data": "All fields are mandatory"})
    
    return JsonResponse(data, safe=False)



def remove_favorite(request):
    user_id = request.GET.get('user_id', '')
    bp_pla_id = request.GET.get('bp_pla_id', '')
    type = request.GET.get('type', '')

    data = {
        "status": True,
        "message": "success"
    }


    if user_id and bp_pla_id and type:
        favorite = Favorites.objects.filter(user_id=user_id, bp_pla_id=bp_pla_id, type=type).first()
        if favorite:
            favorite.delete()
            data.update({"data": "Removed from favorites"})
        else:
            data.update({"data": "Not found in favorites"})
    else:
        data.update({"data": "All fields are mandatory"})
    
    return JsonResponse(data, safe=False)



def search_2_1(request):
    query = request.GET.get('query', '').strip()

    data = {
        "status": True,
        "message": "success",
    }

    if query:
        blueprints = BP.objects.filter(name__icontains=query, status="approved")

        if blueprints.count() == 0:
            blueprints = BP.objects.filter(status="approved").order_by('?')[:20]


        blueprint_list = []

        for bp in blueprints:
            blueprint_list.append({
                "name": bp.name,
                "image": bp.image,
                "views": bp.fviews,
                "likes": bp.flikes,
                "downloads": bp.fdownloads,
                "share": bp.fshare,
                "comments": bp.comments,
                "bp_id": bp.bp_id,
                "user": bp.user.name,

                "categories": [
                    {
                        "name": cat.category.bp_name,
                        "cat_id": cat.category.category_id,
                    }
                    for cat in bp.bp_category_bp.all()
                ]
            })



            data.update({
                "blueprints": blueprint_list,
            })
    else:
        data.update({"message": "empty"})

    return JsonResponse(data, safe=False)


def categories_2_1(request):

    from django.db.models import Count
    
    categories = BpCat.objects.filter(status="approved").annotate(
    blueprint_count=Count('bp_categories__bp', distinct=True))


    data = {
        "status": True,
        "message": "success",
        "categories": list(categories.values(
            "category_id",
            "bp_name",
            "bp_img",
            "bp_para",
            "blueprint_count"
        ),
        )
    }


    return JsonResponse(data, safe=False)

data = {
    "status": True,
    "message": "success",
}


def insert_dlv(request):
    bp_id = request.GET.get('bp_id', '')
    type = request.GET.get('type', '')
    download_type = request.GET.get('download_type', '')
    utm_source = request.GET.get('utm_source', None)

    if bp_id and type and download_type:

        utils.insert_dlv(get_client_ip(request), bp_id, type, request.GET.get('user_id', 'anonymous'), download_type, "2.1", utm_source=utm_source)

        return JsonResponse(data, safe=False)
    else:
    
        data.update({"message": "empty"})
        return JsonResponse(data, safe=False)


def inner_cat_2_1(request):
    category_id = request.GET.get('category_id', '')
    data = {
        "status": True,
        "message": "success",
    }


    if category_id:
        categories = BPCategories.objects.filter(category_id = category_id, status="approved")


        if categories:

            data.update({"current": category_id, "c_name": categories.first().category.bp_name, "c_para": categories.first().category.bp_para})


            blueprint_list = []

            for bp in categories:
                blueprint_list.append({
                    "name": bp.bp.name,
                    "image": bp.bp.image,
                    "views": bp.bp.fviews,
                    "likes": bp.bp.flikes,
                    "downloads": bp.bp.fdownloads,
                    "share": bp.bp.fshare,
                    "comments": bp.bp.comments,
                    "bp_id": bp.bp.bp_id,
                    "user": bp.bp.user.name,

                    "categories": [
                        {
                            "name": cat.category.bp_name,
                            "cat_id": cat.category.category_id,
                        }
                        for cat in bp.bp.bp_category_bp.all()
                    ]
                })
            data.update({"categories": 
                        #list(categories.values("category_id", "bp__name", "bp__image", "bp__fviews", "bp__flikes", "bp__fdownloads", "bp__fshare", "bp__comments", "bp__bp_id", "bp__user__name"))

                        blueprint_list
                        })
        else:
            data.update({"message": "no"})

        return JsonResponse(data, safe=False)

    else:
    
        data.update({"message": "empty"})
        return JsonResponse(data, safe=False)


# 2.1 version end


# ==============================================================================
# DYNAMIC COMMENTS APIS
# ==============================================================================

def get_comments(request):
    bp_id = request.GET.get('bp_id', '')
    user_id = request.GET.get('user_id', '')

    if not bp_id:
        return JsonResponse({"status": False, "message": "bp_id required", "comments": []})

    comments_qs = Comments.objects.filter(bp_id=bp_id).select_related('user').order_by('time')

    comments_list = []
    for c in comments_qs:
        author_name = "Space Pilot"
        if c.user:
            author_name = c.user.name or c.user.username or "Space Pilot"

        time_str = "Recently"
        if c.time:
            time_str = c.time.strftime("%d %b %Y, %H:%M")

        is_owner = False
        if user_id and c.user and str(c.user.user_id) == str(user_id):
            is_owner = True

        raw_text = c.comment or ""
        parent_id = None
        if raw_text.startswith("[reply:") and "]" in raw_text:
            idx = raw_text.find("]")
            parent_id = raw_text[7:idx].strip()
            raw_text = raw_text[idx + 1:].strip()

        comments_list.append({
            "id": str(c.id),
            "user_id": str(c.user.user_id) if c.user else "",
            "author": author_name,
            "text": raw_text,
            "parent_id": parent_id,
            "time": time_str,
            "is_owner": is_owner
        })

    return JsonResponse({
        "status": True,
        "count": len(comments_list),
        "comments": comments_list
    }, safe=False)


@csrf_exempt
def add_comment(request):
    bp_id = request.GET.get('bp_id', '') or request.POST.get('bp_id', '')
    user_id = request.GET.get('user_id', '') or request.POST.get('user_id', '')
    text = request.GET.get('comment_text', '') or request.POST.get('comment_text', '')
    parent_id = request.GET.get('parent_id', '') or request.POST.get('parent_id', '')

    if not (bp_id and user_id and text):
        return JsonResponse({"status": False, "message": "bp_id, user_id, and comment_text required"})

    bp_obj = BP.objects.filter(bp_id=bp_id).first()
    if not bp_obj:
        return JsonResponse({"status": False, "message": "Blueprint not found"})

    user_obj = get_user_object(user_id)
    if not user_obj:
        clean_username = str(user_id).replace("@", "_").replace(".", "_")
        user_obj = AllUsers.objects.create(
            user_id=user_id,
            username=clean_username[:50],
            name="Space Pilot",
            email=user_id if "@" in user_id else f"{user_id}@sfs.app",
            platform="sfs",
            platform_name="sfs_blueprints",
            type="user",
            ip=get_client_ip(request)
        )

    final_comment_text = f"[reply:{parent_id}] {text.strip()}" if parent_id else text.strip()

    new_comment = Comments.objects.create(
        ip=get_client_ip(request),
        user=user_obj,
        bp=bp_obj,
        comment=final_comment_text,
        status="approved",
        time=timezone.now()
    )

    bp_obj.comments = Comments.objects.filter(bp_id=bp_id).count()
    bp_obj.save()

    return JsonResponse({
        "status": True,
        "message": "Comment posted successfully",
        "comment": {
            "id": str(new_comment.id),
            "user_id": str(user_id),
            "author": user_obj.name or "You",
            "text": text.strip(),
            "parent_id": str(parent_id) if parent_id else None,
            "time": "Just now",
            "is_owner": True
        },
        "count": bp_obj.comments
    }, safe=False)


@csrf_exempt
def edit_comment(request):
    comment_id = request.GET.get('comment_id', '') or request.POST.get('comment_id', '')
    user_id = request.GET.get('user_id', '') or request.POST.get('user_id', '')
    text = request.GET.get('comment_text', '') or request.POST.get('comment_text', '')

    if not (comment_id and user_id and text):
        return JsonResponse({"status": False, "message": "comment_id, user_id, and comment_text required"})

    comment_obj = Comments.objects.filter(id=comment_id, user__user_id=user_id).first()
    if not comment_obj:
        return JsonResponse({"status": False, "message": "Comment not found or unauthorized"})

    comment_obj.comment = text
    comment_obj.save()

    return JsonResponse({"status": True, "message": "Comment updated successfully"}, safe=False)


@csrf_exempt
def delete_comment(request):
    comment_id = request.GET.get('comment_id', '') or request.POST.get('comment_id', '')
    user_id = request.GET.get('user_id', '') or request.POST.get('user_id', '')

    if not (comment_id and user_id):
        return JsonResponse({"status": False, "message": "comment_id and user_id required"})

    comment_obj = Comments.objects.filter(id=comment_id, user__user_id=user_id).first()
    if not comment_obj:
        return JsonResponse({"status": False, "message": "Comment not found or unauthorized"})

    bp_id = comment_obj.bp_id
    comment_obj.delete()

    bp_obj = BP.objects.filter(bp_id=bp_id).first()
    count = 0
    if bp_obj:
        bp_obj.comments = Comments.objects.filter(bp_id=bp_id).count()
        bp_obj.save()
        count = bp_obj.comments

    return JsonResponse({
        "status": True,
        "message": "Comment deleted successfully",
        "count": count
    }, safe=False)