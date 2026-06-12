from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from shared_lib.utils import insertions, random



sfs_app_version = "2.1"

data = {
    "status" : True,
    "message": "success"
}

def index(request):
    
    #return redirect("https://www.ascentracoresolutions.com")
    return HttpResponse("You don't have access to this page. Please contact support for more information.")


def insert_sfs_app(request):

    activity_id = request.GET.get("activity_id", "")


    if activity_id:

        insertions.insert_activity(random.get_client_ip(request), sfs_app_version, activity_id, request.GET.get('user_id', 'anonymous'))
        return JsonResponse(data, safe=False)
    else:

        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)





def error_sfs_app(request):
    activity_id = request.GET.get("activity_id", "")
    msg = request.GET.get('msg', '')

    if activity_id and msg:

        insertions.insert_error(random.get_client_ip(request), request.GET.get('user_id', 'anonymous'), sfs_app_version, msg, activity_id)
        return JsonResponse(data, safe=False)
    
    else:
        
        data.update({"message": "failed"})
        return JsonResponse(data, safe=False)

