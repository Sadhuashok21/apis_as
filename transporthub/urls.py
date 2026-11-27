from django.urls import path
from .views import Trains, create_train
from rest_framework.routers import DefaultRouter



router = DefaultRouter()


router.register("trains", Trains)

urlpatterns = [
    path('create_train', create_train, name="create_train"),
] + router.urls