from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('signin', views.signin, name="signin"),
    path('create_account', views.create_account, name="create_account"),
    path('create_account_pass', views.create_account_pass, name="create_account_pass"),
    path('create_account_address', views.create_account_address, name="create_account_address"),
    path('send_otp', views.send_otp, name="send_otp"),

    # crud product 
    path('products/edit_product', views.edit_product, name="edit_product"),
    path('products/upload_product', views.upload_product, name="upload_product"),
    path('products/delete_product', views.delete_product, name="delete_product"),
    path('products/change_image', views.change_image, name="change_image"),

    path('address/', views.address, name="address"),
    path('insert_address', views.insert_address, name="insert_address"),


    path('search', views.search, name="search"),
    # products
    path('products', views.products, name="products"),
    path('products/product', views.product, name="product"),

    # category 
    path('upload_category', views.CategoryUpload.as_view(), name="category_upload"),
    path('category', views.Category.as_view(), name="category"),
    path('view_cat', views.cat_view, name="cat_view"),

    path('products/check_name', views.check_name, name="check_name"),
    # cart system 
    path('cart/add_cart', views.add_cart, name="add_cart"),
    path('cart/decrease_cart', views.decrease_cart, name="decrease_cart"),
    path('cart', views.cart, name="cart"),
    path('cart/delete_cart', views.delete_order, name="delete_order"),


    path('cart/user_orders', views.user_orders, name="user_orders"),

    path('profile', views.profile, name="profile"),

]
