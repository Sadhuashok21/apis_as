import os
from django.conf import settings
from django.http import JsonResponse

from django.utils import timezone
from shared_lib.utils import insertions, random



def insert_map(request):
    lat = request.GET.get('lat', '')
    lon = request.GET.get('lon', '')
    intensity = request.GET.get('intensity', '')

    data = {
        "status" : True,
        "message": "success",
        "lat": []
    }

    if lat and lon and intensity:
        Map.objects.create(
            lat=lat,
            lon = lon,
            intensity = intensity,
            time = timezone.now(),
            status = approved,
        )

        data['lat'] = 'inserted'
    else:
        data['lat'] = "empty"

    return JsonResponse(data, safe=False)



def map(request):
    
   
    maps = Map.objects.values()

    data = {
        "status" : True,
        "message": "success",
        "lat": list(maps)
    }

    return JsonResponse(data, safe=False)





def insert_challan(request):
    no = request.GET.get('no', '')
    date = request.GET.get('date', '')
    status = request.GET.get('status', '')
    payment = request.GET.get('payment', '')
    sent_court = request.GET.get('sent_court', '')
    remark = request.GET.get('remark', '')
    place = request.GET.get('place', '')
    violator_name = request.GET.get('violator_name', '')
    department = request.GET.get('department', '')
    state_code = request.GET.get('state_code', '')
    owner_name = request.GET.get('owner_name', '')


    data = {
        "status" : True,
        "message": "success",
    }


    if no and date and status and payment and sent_court and remark and place and violator_name and department and state_code and owner_name:
        RealChallan.objects.create(
            no = no,
            date = date,
            status = status,
            payment = payment,
            sent_court = sent_court,
            remark = remark,
            place = no,
            violator_name = violator_name,
            department = department,
            state_code = state_code,
            owner_name = owner_name,
            user_id = unique_id(),
            time = timezone.now()
        )

        data['data'] = 'inserted'
    else:
        data['data'] = 'empty'


    return JsonResponse(data, safe=False)


def ch(request):
    
    data = {
        "status" : True,
        "message": "success",
    }

    data['data'] = list(RealChallan.objects.values())
    return JsonResponse(data, safe=False)




def profile(request):
    user_id = request.GET.get('user_id', '')


    data = {
        "status" : True,
        "message": "success",
    }
    if user_id:
        user = Users.objects.filter(user_id=user_id).first()

        if user:
            data['profile'] = user.name
            data['email'] = user.email

        else:
            data['profile'] = 'no user'
    else:
            data['profile'] = 'empty'

    return JsonResponse(data, safe=False)
