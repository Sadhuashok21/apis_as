from django.utils import timezone
from rest_framework.permissions import BasePermission


def user_has_abap_access(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "user_type", "") == "admin" or getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    from .models import CompilerProduct, CompilerEntitlement
    if CompilerProduct.objects.filter(slug="sap-abap", active=True, price_paise=0).exists():
        return True
    return CompilerEntitlement.objects.filter(
        user_id=user.user_id,
        product__slug="sap-abap",
        status="active",
    ).filter(
        models_expiry_filter()
    ).exists()


def models_expiry_filter():
    from django.db.models import Q
    return Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())


class HasABAPEntitlement(BasePermission):
    message = "SAP ABAP compiler access requires an active purchase."

    def has_permission(self, request, view):
        return user_has_abap_access(request.user)
