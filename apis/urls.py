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
from django.http import HttpResponse
from . import views
from . import admin_views
from skiltrix import payments_admin
from django.conf import settings
from django.conf.urls.static import static

ADS_TXT_CONTENT = "google.com, pub-8687126461256058, DIRECT, f08c47fec0942fa0\n"

urlpatterns = [
    path('', views.index, name="index"),
    path('ads.txt', lambda r: HttpResponse(ADS_TXT_CONTENT, content_type="text/plain"), name="ads_txt"),
    path('app-ads.txt', lambda r: HttpResponse(ADS_TXT_CONTENT, content_type="text/plain"), name="app_ads_txt"),

    # Authenticated SkilTrix administration for compiler pricing and coupons
    path('api/admin/compiler-pricing/', payments_admin.product_config, name="compiler-product-config"),
    path('api/admin/compiler-coupons/', payments_admin.coupon_management, name="compiler-coupons"),
    path('api/admin/compiler-coupons/<int:coupon_id>/', payments_admin.coupon_management, name="compiler-coupon-detail"),
    path('api/admin/compiler-payment-report/', payments_admin.payment_report, name="compiler-payment-report"),

    # Admin Management REST API Endpoints
    path('api/admin/stats/', admin_views.get_admin_stats, name="admin_stats"),
    path('api/admin/analytics/', admin_views.get_admin_analytics, name="admin_analytics"),
    path('api/admin/users/', admin_views.admin_users, name="admin_users"),
    path('api/admin/users/<int:user_id>/', admin_views.admin_users, name="admin_user_detail"),
    path('api/admin/logs/', admin_views.admin_logs, name="admin_logs"),
    path('api/admin/blueprints/', admin_views.admin_blueprints, name="admin_blueprints"),
    path('api/admin/blueprints/<str:bp_id>/', admin_views.admin_blueprints, name="admin_blueprint_detail"),
    path('api/admin/database/tables/', admin_views.admin_database_tables, name="admin_database_tables"),
    path('api/admin/categories/', admin_views.admin_categories, name="admin_categories"),
    path('api/admin/transport_hub/', admin_views.admin_transport_hub, name="admin_transport_hub"),

    # Central Accounts & SSO Identity System
    path('api/accounts/', include('accounts.urls')),

    # spaceflight Simulator
    path('apps/sfs/', include('sfs.urls'), name="sfs"),

    path('apps/skiltrix/', include('skiltrix.urls'), name="skiltrix"),

    path('insertions/sfs_insert', views.insert_sfs_app, name="sfs_insert"),
    path('insertions/sfs_error', views.error_sfs_app, name="error_sfs"),

    path('signin/', views.signin, name="signin"),
    path('signup/forgot_password', views.forgot_password_i, name="forgot_password_i"),
    path('signup/', views.signup, name="signup"),
    path('signup/check_username', views.check_username, name="check_username"),
    path('signup/otp', views.otp_i, name="otp_i"),
    path('signup/check_mail', views.check_mail, name="check_mail"),
    path('signup/check_signin', views.check_signin, name="check_signin"),
    path('fcm', views.device_fcm, name="fcm"),

    path('attach_user_id/', views.attach_user_id, name="attach_user_id")

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



handler404 = 'apis.views.er_404'
handler400 = 'apis.views.er_400'
handler401 = 'apis.views.er_401'
handler403 = 'apis.views.er_403'
handler408 = 'apis.views.er_408'
handler500 = 'apis.views.er_500'
handler502 = 'apis.views.er_502'
handler503 = 'apis.views.er_503'
handler504 = 'apis.views.er_504'
handler505 = 'apis.views.er_505'
