from django.shortcuts import render
from django.http import JsonResponse
from .models import Task

def home(request):
    tasks = Task.objects.all()
    context = {
        'title': 'SkilTrix Django Development Suite',
        'tasks': tasks,
    }
    return render(request, 'myapp/index.html', context)

def tasks_api(request):
    return JsonResponse({
        'status': 'success',
        'message': 'Welcome to your Django API!',
        'version': '1.0.0'
    })
