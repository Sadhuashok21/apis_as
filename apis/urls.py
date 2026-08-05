"""
URL configuration for apis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name="index"),

    # spaceflight Simulator
    path('apps/sfs/', include('sfs.urls'), name="sfs"),

    #aaaaa - protein app
    path('apps/aaaaa/', include('aaaaa.urls'), name="aaaaa"),


    # aaaab
    path('apps/aaaab/', include('aaaab.urls'), name="aaaab"),


    # aaaac
    path('apps/aaaac/', include('aaaac.urls'), name="aaaac"),



    # krishi
    path('apps/krishi/', include('krishi.urls'), name="krishi"),

    path('apps/aaaad/', include('aaaad.urls'), name="aaaad"),

    path('insertions/sfs_insert', views.insert_sfs_app, name="sfs_insert"),
    path('insertions/sfs_error', views.error_sfs_app, name="error_sfs"),

    path('signin/', views.signin, name="signin"),
    path('signup/forgot_password', views.forgot_password_i, name="forgot_password_i"),
    path('signup/', views.signup, name="signup"),
    path('signup/check_username', views.check_username, name="check_username"),
    path('signup/otp', views.otp_i, name="otp_i"),
    path('signup/check_mail', views.check_mail, name="check_mail"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)