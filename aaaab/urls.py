from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    # signin system
    path('signin', views.signin, name="signin"),
    path('create_account', views.create_account, name="create_account"),
    path('create_account_pass', views.create_account_pass, name="create_account_pass"),
    path('create_account_address', views.create_account_address, name="create_account_address"),
    path('create_account_email', views.create_account_email, name="create_account_email"),
    path('change_password', views.change_password, name="change_password"),
    path('send_otp', views.send_otp, name="send_otp"),

    # crud product 
    path('products/edit_product', views.edit_product, name="edit_product"),
    path('products/upload_product', views.upload_product, name="upload_product"),
    path('products/delete_product', views.delete_product, name="delete_product"),
    path('products/feature', views.feature, name="feature"),

    path('products/insert_rating', views.insert_rating, name="insert_rating"),
    path('products/reviews', views.reviews, name="reviews"),
    path('products/delete_review', views.delete_review, name="delete_review"),

    path('address/', views.address, name="address"),
    path('address/delete_address', views.delete_address, name="delete_address"),
    path('address/edit_address', views.edit_address, name="edit_address"),
    path('address/address_particular', views.address_particular, name="address_particular"),
    path('address/insert_address', views.insert_address, name="insert_address"),
    path("address/default", views.default_address, name="default_address"),
    path('search', views.search, name="search"),

    # products
    path('products', views.products, name="products"),
    path('products/product', views.product, name="product"),

    # category 
    path('upload_category', views.CategoryUpload.as_view(), name="category_upload"),
    path('upload_sub_category', views.sub_category, name="sub_category"),
    path("category/edit_category", views.edit_category, name="edit_category"),
    path('category/category_particular', views.category_particular, name="category_particular"),
    path('category', views.Category.as_view(), name="category"),
    path('sub_category_view', views.sub_category_view, name="sub_category_view"),
    path('view_sub_category', views.view_sub_cat, name="view_sub_cat"),
    path('view_cat', views.cat_view, name="cat_view"),

    path('products/check_name', views.check_name, name="check_name"),
    # cart system 
    path('add_cart', views.add_cart, name="add_cart"),
    path('decrease_cart', views.decrease_cart, name="decrease_cart"),
    path('cart', views.cart, name="cart"),
    path('delete_cart', views.delete_order, name="delete_order"),
    path('cart/confirm', views.confirm, name="confirm"),
    path('cart/show_cart', views.show_cart, name="show_cart"),
    path('carts', views.carts, name="carts"),
    path("cart/completed_carts", views.completed_carts, name="completed_carts"),
    path("cart/transit_carts", views.transit_carts, name="transit_carts"),
    path("cart/processing_carts", views.processing_carts, name="processing_carts"),
    path('cart/in_cart_product', views.inProductCart, name="inProductCart"),
    path('cart/user_orders', views.user_orders, name="user_orders"),
    path('cart/order_completed', views.order_completed, name="order_completed"),

    path('profile', views.profile, name="profile"),

    path('tickets/', views.tickets, name="tickets"),
    path('tickets/insert_ticket', views.insert_ticket, name="insert_ticket"),
    path('tickets/delete_ticket', views.delete_ticket, name="delete_ticket"),
    

]