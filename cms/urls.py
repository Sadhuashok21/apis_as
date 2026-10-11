from django.urls import path
from . import views

urlpatterns = [
    path("overview/", views.get_site_overview, name="cms-overview"),
    path("posts/", views.list_blog_posts, name="cms-posts-list"),
    path("posts/<slug:slug>/", views.get_blog_post_detail, name="cms-post-detail"),
    path("tutorials/", views.list_tutorials, name="cms-tutorials-list"),
    path("tutorials/<str:category>/<slug:slug>/", views.get_tutorial_detail, name="cms-tutorial-detail"),
    path("resources/", views.list_resources, name="cms-resources-list"),
    path("case-studies/", views.list_case_studies, name="cms-case-studies-list"),
    path("case-studies/<slug:slug>/", views.get_case_study_detail, name="cms-case-study-detail"),
    path("products/", views.list_products, name="cms-products-list"),
    path("products/<slug:slug>/", views.get_product_detail, name="cms-product-detail"),
    path("services/", views.list_services, name="cms-services-list"),
    path("services/<slug:slug>/", views.get_service_detail, name="cms-service-detail"),
    path("faqs/", views.list_faqs, name="cms-faqs-list"),
    path("search/", views.global_search, name="cms-global-search"),
]
