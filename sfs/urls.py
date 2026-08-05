from django.urls import path, include
from . import views

urlpatterns = [

    # 2.0932
    path('2_093/blueprints', views.blueprints, name="blueprints"),
    path('2_093/blueprint', views.inner_bp, name="blueprint"),
    path('2_093/plawor', views.plawor, name="plawor"),

    path('2_093/feature', views.feature, name="feature"),

    # pages
    path('2_093/blueprint_page', views.page, name="blue_page"),
    path('2_093/pla_page', views.pla_page, name="pla_page"),
    # pages end

    # account and signin 
    path('2_093/profile', views.profile, name="profile"),
    path('2_093/create_account_pass', views.create_account_pass, name="create_account_pass"),
    path('2_093/change_password', views.change_password, name="change_password"),
    path('2_093/signin', views.signin, name="signin"),
    path('2_093/create_account', views.create_account, name="create_account"),
    # account and signin end

    # 2.093 end


    # 2.1 start

    path('2_1/blueprints', views.blueprints_2_1, name="blueprints_2_1"),
    path('2_1/blueprints/random', views.random_blueprints_2_1, name="random"),
    path('2_1/planets', views.planets_2_1, name="planets_2_1"),
    path('2_1/categories', views.categories_2_1, name="categories_2_1"),
    path('2_1/blueprints/bp', views.inner_bp, name="inner_bp"),

    path('2_1/search', views.search_2_1, name="search_2_1"),
    path('2_1/blueprint_page', views.page, name="blue_page_2_1"),
    path('2_1/inner_cat', views.inner_cat_2_1, name="inner_cat_2_1"),

    path('2_1/insert_dlv', views.insert_dlv, name="insert_dlv"),


    # 2.100 start 
    path('2_100/home_blue', views.home_blue_2_100, name="home_blue_2_100"),
    path('2_100/home_pla', views.home_pla_2_100, name="home_pla_2_100"),
    path('2_100/home_cat', views.home_cat_2_100, name="home_cat_2_100"),

]
