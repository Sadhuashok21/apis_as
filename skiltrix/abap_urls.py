"""
SkilTrix SAP ABAP Lab - URL Routing Definitions
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import abap_views
from . import coupon_views

router = DefaultRouter()
router.register("projects", abap_views.ABAPProjectViewSet, basename="abap-project")
router.register("exercises", abap_views.ABAPExerciseViewSet, basename="abap-exercise")
router.register("connections", abap_views.SAPSystemConnectionViewSet, basename="abap-connection")
router.register("dictionary", abap_views.ABAPDictionaryViewSet, basename="abap-dictionary")

urlpatterns = [
    path('pricing/', coupon_views.compiler_pricing, name="compiler-pricing"),
    path('access/', coupon_views.compiler_access, name="compiler-access"),
    path('payments/create-order/', coupon_views.create_payment_order, name="compiler-payment-create-order"),
    path('payments/verify/', coupon_views.verify_payment, name="compiler-payment-verify"),
    path('payments/cancel/', coupon_views.cancel_payment_order, name="compiler-payment-cancel"),
    path('payments/history/', coupon_views.payment_history, name="compiler-payment-history"),
    path('payments/status/<str:order_id>/', coupon_views.payment_status, name="compiler-payment-status"),
    path('payments/webhook/', coupon_views.razorpay_webhook, name="compiler-payment-webhook"),
    path('coupons/validate/', coupon_views.validate_compiler_coupon, name="compiler-coupon-validate"),
    # ABAP Execution & Compilation
    path('execute/', abap_views.execute_abap_view, name="abap-execute"),
    path('syntax-check/', abap_views.syntax_check_view, name="abap-syntax-check"),
    path('dictionary/preview/', abap_views.dictionary_preview_view, name="abap-dictionary-preview"),

    path('health/', abap_views.abap_health_check, name="abap-health"),
    path('', include(router.urls)),

    # ABAP Source Files
    path(
        'projects/<str:project_id>/files/',
        abap_views.ABAPSourceFileViewSet.as_view({'get': 'list'}),
        name="abap-files-list"
    ),
    path(
        'projects/<str:project_id>/files/content/',
        abap_views.ABAPSourceFileViewSet.as_view({'get': 'content'}),
        name="abap-files-content"
    ),
    path(
        'projects/<str:project_id>/files/save/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'save'}),
        name="abap-files-save"
    ),
    path(
        'projects/<str:project_id>/files/create/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'create_file'}),
        name="abap-files-create"
    ),
    path(
        'projects/<str:project_id>/files/folder/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'create_folder'}),
        name="abap-files-create-folder"
    ),
    path(
        'projects/<str:project_id>/files/rename/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'rename'}),
        name="abap-files-rename"
    ),
    path(
        'projects/<str:project_id>/files/move/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'move'}),
        name="abap-files-move"
    ),
    path(
        'projects/<str:project_id>/files/duplicate/',
        abap_views.ABAPSourceFileViewSet.as_view({'post': 'duplicate'}),
        name="abap-files-duplicate"
    ),
    path(
        'projects/<str:project_id>/files/delete/',
        abap_views.ABAPSourceFileViewSet.as_view({'delete': 'delete_file'}),
        name="abap-files-delete"
    ),
]
