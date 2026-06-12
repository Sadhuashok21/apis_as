from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('products/', views.Products.as_view(), name="products"),
    path('add_cart', views.add_cart, name="add_cart"),
    path('decrease_cart', views.decrease_cart, name="decrease_cart"),
    path('delete_cart', views.delete_order, name="delete_cart"),
    path('cart', views.cart, name="cart"),
    #path('')
]