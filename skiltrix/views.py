from django.shortcuts import render
from django.http import JsonResponse
from shared_lib.skiltrix_core.models import *

# Create your views here.


def internships(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }

    data.update({"internships": list(Internship.objects.filter(status="active").values())})
    return JsonResponse(data, safe=False)


def profile(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
   
        profile = AllUsers.objects.filter(status="active", user_id = user_id).first()

    else:
        data.update({"action": "nouser"})

    data.update({'profile': profile.user_id})
    return JsonResponse(data, safe=False)


def profile_skills(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
    
        profile = AllUsers.objects.filter(status="active", user_id = user_id).first()

    else:
        data.update({"action": "nouser"})

    data.update({'profile': profile.user_id})
    return JsonResponse(data, safe=False)


def recommend(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    

    data.update({'profile': profile.user_id})
    return JsonResponse(data, safe=False)


def courses(request):

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }

    courses = Courses.objects.filter(status="active").values()
    
    data.update({"courses": list(courses)})
    return JsonResponse(data, safe=False)

def videos(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    courses = Videos.objects.values()
    
    data.update({"videos": list(courses)})
    return JsonResponse(data, safe=False)

def profile_resumes(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
    
        resumes = Resumes.objects.filter(status="active", user_id = user_id)
        data.update({"resumes": resumes})
    else:
        data.update({"action": "nouser"})

    return JsonResponse(data, safe=False)


def profile_education(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
    
        education = Education.objects.filter(status="active", user_id = user_id)

        data.update({'education': list(education)})
    else:
        data.update({"action": "nouser"})

    return JsonResponse(data, safe=False)