from django.shortcuts import render
from django.http import JsonResponse
from shared_lib.skiltrix_core.models import *

# Create your views here.


def internships(request):

    type = request.GET.get('type', '')


    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if type == 'paid':
        internships = Internship.objects.filter(status="active", is_paid=1).values()
    elif type== 'free':
        
        internships = Internship.objects.filter(status="active", is_paid=0).values()
    elif type == 'remote':
        
        internships = Internship.objects.filter(status="active", location='remote').values()
    else:
        
        internships = Internship.objects.filter(status="active",).values()

    data.update({"internships": list(internships)})
    return JsonResponse(data, safe=False)


def profile(request):
    user_id = request.GET.get('user_id', '')

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
   
        profile = AllUsers.objects.filter(status="approved", user_id = user_id).first()

        if profile:

            data.update({'action': profile.user_id})
        else:
            data.update({'action': "no"})
    else:
        data.update({"action": "empty"})

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

        if profile:
            skills = Skills.objects.filter(user_id = user_id)
            data.update({"skills": list(skills.values())})
        else:
            data.update({'action': "no"})
    else:
        data.update({"action": "empty"})

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

    type = request.GET.get("type", '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }

    if type == 'free':

        courses = Courses.objects.filter(status="active", is_paid=0).values()
    elif type == 'paid':
    
        courses = Courses.objects.filter(status="active", is_paid=1).values()
    else: 
        courses = Courses.objects.filter(status="active").values()
        
    data.update({"courses": list(courses)})
    return JsonResponse(data, safe=False)

def languages(request):

    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }

    languages = Language.objects.filter(status="active").values()
        
    data.update({"languages": list(languages)})
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