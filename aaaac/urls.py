from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.orders, name="orders"),
    path('orders/completed', views.completed, name="completed"),
    path('orders/all_orders', views.all_orders, name="all_orders"),
    path('orders/order_complete', views.o_complete, name="order_complete"),
    path('profile/', views.profile, name="profile"),
    
]