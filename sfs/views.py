from django.shortcuts import render
from .models import *
from django.http import JsonResponse
from django.utils import timezone
import hashlib
from shared_lib.sfs_core import utils
from django.db import connection
from shared_lib.sfs_core.models import *
from shared_lib.utils.random import get_client_ip
from django.db.models import Count, F

# Create your views here.

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
    blueprints = SfsBp.objects.filter(status = "approved", fviews__gte= 1000)[:10]
    data = {
        "status": True,
        "message": "success",
        "blueprints": list(blueprints.values("name", "image"))

    }
    return JsonResponse(data, safe=False)

def feature(request):
    blueprint = SfsBp.objects.filter(feature=1, status="approved").order_by('?')[:1]
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
    pla = SfsBp.objects.filter(status="approved", type="planet")

    data = {
        "status": True,
        "message": "success",
        "blueprints": list(pla.values()),
    }

    return JsonResponse(data, safe=False)


def blueprints(request):

    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    start = (off_value - 1) * 10
    end = off_value * 10
    data = {
        "status": True,
        "message": "success",
    }


    blueprints = SfsBp.objects.filter(status="approved", type="blueprint").order_by("-id")[start:end]

    data.update({
        "off": off_value,
        "blueprints":  list(blueprints.values("name", "image", "fviews", "flikes", "fdownloads", "fshare", "comments", "bp_id")), 
        
    })

    return JsonResponse(data, safe=False)

def plawor(request):
    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    start = (off_value - 1) * 10
    end = off_value * 10
    data = {
        "status": True,
        "message": "success",
    }

    blueprints = SfsBp.objects.filter(status="approved", type="planet").order_by("-id")[start:end]

    data.update({
        "off": off_value,
        "blueprints":  list(blueprints.values("name", "image", "fviews", "flikes", "fdownloads", "fshare", "comments", "bp_id")), 
        
    })

    return JsonResponse(data, safe=False)


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
    cat = SfsBpCat.objects.filter(status="approved")

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
            cursor.execute("SELECT COUNT(*) FROM sfs_BP WHERE status = 'approved' and type='blueprint'")
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
        
        blueprint = SfsBp.objects.filter(bp_id = blueprint_id, status = 'approved').first()

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
            insert_error = Allerrors.objects.create(
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
            insert_error = Allerrors.objects.create(
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


def favorites_2_1(request):
    user_id = request.GET.get('user_id', '')
    
    data = {
            "status": True,
            "message": "success"
        }
    if user_id:
        favorites = Favorites.objects.filter(user_id = user_id)

        if favorites:

            data.update({"favorites": list(favorites.values("bp_pla_id", "type"))})
        else:
            data.update({"action": "no favorites"})
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

    if bp_id and type and download_type:

        utils.insert_dlv(get_client_ip(request), bp_id, type, request.GET.get('user_id', 'anonymous'), download_type, "2.1")

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