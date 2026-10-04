from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/tasks/', views.tasks_api, name='tasks_api'),
]
