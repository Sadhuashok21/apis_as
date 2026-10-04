from django.shortcuts import render, redirect
from sfs.models import *
from .utils import *
from django.http import JsonResponse, StreamingHttpResponse
from apps.utils import *
from django.urls import reverse
from urllib.parse import urlencode
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import Count
from sfs.utils import *
import requests


# Create your views here.
def download(request, bp_id):
    blueprint = BP.objects.filter(status="approved", bp_id=bp_id).first()


    if blueprint is None:
        if request.user.is_authenticated:
            insert_error(get_client_ip(request), version, "Blueprint not found during download", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insert_error(get_client_ip(request), version, "Blueprint not found during download", request.build_absolute_uri(), 400, "website", "sfs")

        messages.error(request, "Blueprint not found.")
        return redirect('blueprints')


    blueprint.fdownloads += 1
    blueprint.downloads += 1
    blueprint.save()


    file_url = "https://cdn.ascentracoresolutions.com/sfs/zipfiles/3emqqip1hf9sdj5v8cab.zip"
    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "blueprint-downloaded", "website", "sfs", request.user.user_id)
        
    else:    
        insert_activity(get_client_ip(request), version, "blueprint-downloaded", "website", "sfs")
        

    r = requests.get(file_url, stream=True)

    response = StreamingHttpResponse(
        streaming_content=r.iter_content(chunk_size=8192),
        content_type=r.headers.get('Content-Type')
    )

    response['Content-Disposition'] = 'attachment; filename=' + blueprint.name + ".zip"

    return response


def sfs_index(request):

    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "sfs_index", "website", "sfs", request.user.user_id)

    else:    
        insert_activity(get_client_ip(request), version, "sfs_index", "website", "sfs")

    bp = BP.objects.filter(status="approved").order_by('?')[:10]
    categories = BpCat.objects.filter(status="approved").annotate(
        blueprint_count = Count('bp_categories__bp', distinct = True))[:10]
    return render(request, "sfs_index.html", {"bp": bp, "cats": categories})


def blueprints(request):
    # Get off value
    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "blueprints", "website", "sfs", request.user.user_id)
        
    else:    
        insert_activity(get_client_ip(request), version, "blueprints", "website", "sfs")

    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    # Pagination slicing
    start = (off_value - 1) * 10
    end = off_value * 10

    blueprints = BP.objects.filter(status="approved", type="blueprint").order_by("-id")#[start:end]

    total = BP.objects.filter(status="approved", type="blueprint").count()
    categories = BpCat.objects.filter(status="approved").all()

    last_page = (total + 9) // 10

    pages = []
    dot_added = False

    # for page in range(1, last_page + 1):
    #     if (
    #         page <= 2 or                       
    #         page > last_page - 2 or          
    #         abs(page - off_value) <= 1         
    #     ):
    #         pages.append(page)
    #         dot_added = False
    #     else:
    #         if not dot_added:
    #             pages.append('.')
    #             dot_added = True

    # Formatting
    for bp in blueprints:
        bp.format_views = format_views(bp.fviews)
        bp.format_likes = format_views(bp.flikes)
        bp.format_downloads = format_views(bp.fdownloads)
        bp.is_favourite = Favorites.objects.filter(
            bp_id=bp.bp_id,
            user_id= request.session.get('user_id', 'none')
        ).exists()

    return render(
        request,
        "blueprints.html",
        {
            "blueprints": blueprints,
            "off": off_value,
            "back": off_value - 1,
            "next": off_value + 1,
            "last_page": last_page,
            "all_pages": pages,
            "categories": categories
        }
    )


def home(request):
    ip = get_client_ip(request)

    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "home", "website", "sfs", request.user.user_id)
        
    else:    
        insert_activity(get_client_ip(request), version, "home", "website", "sfs")


    blueprints = BP.objects.filter(status = "approved", type='blueprint').order_by('?')[:10]
    planetsandworlds = BP.objects.filter(status= "approved", type='planet').order_by('?')[:10]
    
    categories = BpCat.objects.filter(status="approved").annotate(
    blueprint_count=Count('bp_categories__bp', distinct=True)
)

    return render(request, "home.html", {
        "categories": categories, 
        "blueprints": blueprints, 
        "planetsandworlds": planetsandworlds,
        "count": category})

def planetsandworlds(request):
    off_str = request.GET.get('off', '').strip()
    off_value = int(off_str) if off_str.isdigit() and int(off_str) > 0 else 1

    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "planetandworlds", "website", "sfs", request.user.user_id)
        
    else:    
        insert_activity(get_client_ip(request), version, "planetandworlds", "website", "sfs")
 
    start = (off_value - 1) * 10
    end = off_value * 10

    planetsandworlds = BP.objects.filter(status = "approved", type='planet').order_by("-id")[start:end]

    total = BP.objects.filter(status="approved", type="planet").count()

    for bp in planetsandworlds:
        bp.format_views = format_views(bp.fviews)
        bp.format_likes = format_views(bp.flikes)
        bp.format_downloads = format_views(bp.fdownloads)
    
    last_page = (total + 9) // 10

    pages = []
    dot_added = False

    # for page in range(1, last_page + 1):
    #     if (
    #         page <= 2 or                       
    #         page > last_page - 2 or          
    #         abs(page - off_value) <= 1         
    #     ):
    #         pages.append(page)
    #         dot_added = False
    #     else:
    #         if not dot_added:
    #             pages.append('.')
    #             dot_added = True


    return render(
        request, "planetsandworlds.html", 
            {
                "planetsandworlds": planetsandworlds,
                "off": off_value,
                "back": off_value - 1,
                "next": off_value + 1,
                "last_page": last_page,
                "all_pages": pages,
            }
        )

def blueprint(request):
    blueprint_id = request.GET.get('bp_id', '')

    if blueprint_id:
        blueprint = BP.objects.filter(status = "approved", bp_id = blueprint_id).first()
        
        if blueprint is None:
            if request.user.is_authenticated:
                insert_error(get_client_ip(request), version, "Blueprint not found", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
            else:
                insert_error(get_client_ip(request), version, "Blueprint not found", request.build_absolute_uri(), 400, "website", "sfs")
                
            messages.error(request, "Blueprint not found.")
            return render(request, "blueprint.html")

        
        """ bp = BpDlv.objects.create(
            ip=get_client_ip(request),
            bp_pla_id=blueprint_id,
            platform=platform,
            platform_name="Sfs",
            type="views",
            download_type = "",
            user_id = None,
            version=version,
            time=timezone.now()
        ) """


        blueprint.fviews += 1
        blueprint.views += 1
        blueprint.save()

        blueprint.format_views = format_views(blueprint.fviews)
        blueprint.format_likes = format_views(blueprint.flikes)
        blueprint.format_downloads = format_views(blueprint.fdownloads)

        blueprints = BP.objects.filter(status="approved", type='blueprint').order_by('?')[:10]
        for bp in blueprints:
            bp.format_views = format_views(bp.fviews)
            bp.format_likes = format_views(bp.flikes)
            bp.format_downloads = format_views(bp.fdownloads)


        if request.user.is_authenticated:
        
            insert_activity(get_client_ip(request), version, "blueprint", "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "blueprint", "website", "sfs")
        
        return render(request, "blueprint.html", {
            "blueprint_name": "as",
            "blueprint": blueprint, 
            "blueprints": blueprints,
            "blueprint_id": blueprint_id, 
            "file": blueprint.zipfiles
            })
    else:
        print("error")
        if request.user.is_authenticated:
            insert_error(get_client_ip(request), version, "No blueprint id provided", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insert_error(get_client_ip(request), version, "No blueprint id provided", request.build_absolute_uri(), 400, "website", "sfs")
            
        return redirect('blueprints')





def category(request):
    category_id = request.GET.get('category_id', '')

    if category_id:
        if request.user.is_authenticated:
    
            insert_activity(get_client_ip(request), version, "category-"+category_id, "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "category-"+category_id, "website", "sfs")
        

        blueprints = BPCategories.objects.filter(category_id = category_id, status="approved")
        categories = BpCat.objects.filter(status="approved")

        return render(request, "category.html", {"category_id": category_id, "categories": categories, "blueprints": blueprints })

    else:
        if request.user.is_authenticated:
            insert_error(get_client_ip(request), version, "No cateogry id provided", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insert_error(get_client_ip(request), version, "No cateogry id provided", request.build_absolute_uri(), 400, "website", "sfs")
            
        return redirect("blueprints")


def search(request):
    search = request.GET.get('search', '')

    if search:
        bp = BP.objects.filter(name__icontains=search, status="approved").all()

    
        if bp.count() == 0:
            bp = BP.objects.filter(status="approved").order_by('?')[:20]


        if request.user.is_authenticated:
    
            insert_activity(get_client_ip(request), version, "search-" + search, "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "search-" + search, "website", "sfs")
        
        
        return render(request, "search.html", {"blueprints": bp, "query": search,})
    else: 

        if request.user.is_authenticated:
            insert_error(get_client_ip(request), version, "No search query provided", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insert_error(get_client_ip(request), version, "No search query provided", request.build_absolute_uri(), 400, "website", "sfs")
            
        return redirect('blueprints')

def search_(request, name):

    if name is not None:
        if request.user.is_authenticated:
            
            insert_activity(get_client_ip(request), version, "search_", "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "search_", "website", "sfs")
        

        bp = BP.objects.filter(name__icontains = name, status ="approved")
        

    else:
        if request.user.is_authenticated:
            insert_error(get_client_ip(request), version, "search is null", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)
        else:
            insert_error(get_client_ip(request), version, "search is null", request.build_absolute_uri(), 400, "website", "sfs")



    return render(request, "search.html", {"blueprints": bp})


@method_decorator(csrf_exempt, name='dispatch')
class Upload(View):
    def get(self, request):
  
        if request.user.is_authenticated:

            insert_activity(get_client_ip(request), version, "bp-upoad", "website", "sfs", request.user.user_id)
        
    
            categories = BpCat.objects.filter(status="approved").all()
            return render(request, "upload.html", {"categories": categories})
        else:
            url = urlencode({"redirect": main_url + "/sfs/uploads"})


            insert_error(get_client_ip(request), version, "Unauthorized access to upload page", request.build_absolute_uri(), 401, "website", "sfs")


            return redirect(f"{reverse('access_denied')}?{url}")

    def post(self, request):
        import boto3
        name = request.POST.get('name', '')
        image = request.FILES.get('image', '')
        zipfile = request.FILES.get('zip_file', '')
        sfs_link = request.POST.get('sfs_link', '')
        type = request.POST.get('type', '')
        description = request.POST.get('description', '')
      
        categories = request.POST.getlist('categories')

        if request.user.is_authenticated:
            user_id = request.user.is_authenticated
            if name and image and zipfile and type and user_id:

                if type == "Select":
                    messages.error(request, "Please select a valid type.")
                    
                    insert_error(get_client_ip(request), version, "Invalid type selected during upload", request.build_absolute_uri(), 400, "website", "sfs", request.user.user_id)

                    return redirect('uploads')

                new_image = unique_id() + "." + image.name.split('.')[-1]

                new_zip = unique_id() + "." + zipfile.name.split('.')[-1]

            
                s3 = boto3.client(
                    service_name="s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name="auto",
                )
        

                bp_id = unique_id()

                bp = BP.objects.create(
                    name=name,
                    image=new_image,
                    zipfiles=new_zip,
                    sfs_link=sfs_link if type == "blueprint" else "none",
                    type=type,
                    bp_id=bp_id,
                    status="approved",
                    description = description,
                    ip=request.META.get('REMOTE_ADDR'),
                    user_id=user_id,
                    time=timezone.now(),
                )

                for cat_id in categories:
                    BPCategories.objects.create(
                        bp_id=bp_id,
                        category_id=cat_id,
                        time = timezone.now(),
                        ip = request.META.get('REMOTE_ADDR'),
                        status = "approved",
                    )


                response1 = s3.put_object(
                    Bucket="sfs-blueprints",
                    Key="sfs/images/" + new_image,
                    Body=image,
                    ContentType=image.content_type,
                )
                response = s3.put_object(
                    Bucket="sfs-blueprints",
                    Key="sfs/zipfiles/" + new_zip,
                    Body=zipfile,
                    ContentType=zipfile.content_type,
                )

                messages.success(request, "Blueprint uploaded successfully.")

                if request.user.is_authenticated:
            
                    insert_activity(get_client_ip(request), version, "bp-uploaded", "website", "sfs", request.user.user_id)
                    
                else:    
                    insert_activity(get_client_ip(request), version, "bp-uploaded", "website", "sfs")
                

                return redirect('blueprints')

                    
            else:
                messages.error(request, "Please fill in all the required fields.")
                                    
                insert_error(get_client_ip(request), version, "Missing required fields during upload", request.build_absolute_uri(), 401, "website", "sfs")

                return redirect('uploads')


@method_decorator(csrf_exempt, name='dispatch')
class UploadCat(View):
    def get(self, request):
        if request.user.is_authenticated:
            
            insert_activity(get_client_ip(request), version, "category-upload", "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "category-upload", "website", "sfs")
        

        return render(request, "upload_cat.html")

    def post(self, request):
        import boto3 
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        image = request.FILES.get('image', '')

        if request.user.is_authenticated:
            user_id = request.user.user_id

            if name and description and image and user_id:

                if BpCat.objects.filter(bp_name=name).exists():
                    insert_error(get_client_ip(request), version, "Category with this name already exists during category upload", request.build_absolute_uri(), 409, "website", "sfs", request.user.user_id)

                    messages.error(request, "Category with this name already exists.")
                    return redirect('upload_category')

                ext = image.name.split('.')[-1]
                image.name = unique_id() + "." + ext

                s3 = boto3.client(
                    service_name="s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name="auto",
                )
                
                response = s3.put_object(
                    Bucket="sfs-blueprints",
                    Key="sfs/images/" + image.name,
                    Body=image,
                    ContentType=image.content_type,
                )


                cat = BpCat.objects.create(
                    bp_category = "sfs",
                    bp_name = name,
                    bp_para = description,
                    bp_img = image,
                    category_id = unique_id(),
                    user_id = user_id,
                    status = "approved",
                    ip = request.META.get('REMOTE_ADDR', 'error'),
                    time = timezone.now(),
                )


                insert_activity(get_client_ip(request), version, "blueprint-uploaded", "website", "sfs", request.user.user_id)
 
                messages.success(request, "Category uploaded successfully.")
                return redirect('home')
            else:
                insert_error(get_client_ip(request), version, "Missing required fields during category upload", request.build_absolute_uri(), 401, "website", "sfs")

                messages.error(request, "Please fill in all the required fields.")
                return render(request, "upload_cat.html")
        



def profile(request):
    if request.user.is_authenticated:

        insert_activity(get_client_ip(request), version, "profile", "website", "sfs", request.user.user_id)
        
    else:    
        insert_activity(get_client_ip(request), version, "profile", "website", "sfs")
    

    return render(request, "profile.html")

def favorites(request):

    if request.user.is_authenticated:

        user_id = request.user.user_id
        
        favorites = Favorites.objects.filter(user_id=user_id)
            
        insert_activity(get_client_ip(request), version, "favourites", "website", "sfs", request.user.user_id)
      
    
        return render(request, "favourites.html", {"blueprints": favorites})
    else:

        insert_error(get_client_ip(request), version, "Unauthorized access to favorites", request.build_absolute_uri(), 401, "website", "sfs")

        url = urlencode({"redirect": main_url + "/sfs/favorites"})
        
        return redirect(f"{reverse('access_denied')}?{url}")


def add_favourite(request):
    bp_id = request.GET.get('bp_id', '')

    data = {
        "status": True,
        "message": "success",

    }

    if request.user.is_authenticated:
        user_id = request.user.user_id
        if user_id and bp_id:
            
            favourite = Favorites.objects.filter(user_id=user_id, bp_id=bp_id).first()
            
            if favourite:

                favourite.delete()
                data.update({"action": "removed"})
                return JsonResponse(data, safe=False)
            
            else:
                Favorites.objects.create(
                    user_id = user_id,
                    bp_id = bp_id,
                    status = "approved",
                    time = timezone.now(),
                )
                data.update({"action": "added"})
                return JsonResponse(data, safe=False)
        else:

            insert_error(get_client_ip(request), version, "Missing user id or blueprint id during add favorite", request.build_absolute_uri(), 401, "website", "sfs")

            data.update({"action": "empty"})
            return JsonResponse(data, safe=False)
    else:
        return JsonResponse(
            {
                "status": False,
                "message": "Please sign in to like this blueprint.",
            },
            status=401,
        )

def logout(request):
    if request.user.is_authenticated:
        request.session.flush()
        return redirect(url)
    else:
        return redirect('home')



def access_denied(request):
    redirect_link = request.GET.get('redirect', '')

    if redirect_link:
        link = urlencode({"redirect":redirect_link})

        if request.user.is_authenticated:
    
            insert_activity(get_client_ip(request), version, "access_denied: " + redirect_link, "website", "sfs", request.user.user_id)
            
        else:    
            insert_activity(get_client_ip(request), version, "access_denied: " + redirect_link, "website", "sfs")
        
        return render(request, "login.html", {"login": url, "signup": f"{url}/signup", "redirect": redirect_link, "url_link": link})
    else:
        insert_error(get_client_ip(request), version, "Unauthorized access to a page without redirect link", request.build_absolute_uri(), 401, "website", "sfs")

        return render(request, "login.html", {"login": url, "signup": f"{url}/signup"})

