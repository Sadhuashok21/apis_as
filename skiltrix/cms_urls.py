from django.urls import path
from . import cms_views

urlpatterns = [
    # Courses
    path("courses/", cms_views.cms_courses_api, name="cms-courses"),
    path("courses/<str:course_id>/", cms_views.cms_course_detail_api, name="cms-course-detail"),

    # Pages
    path("pages/", cms_views.cms_pages_api, name="cms-pages"),
    path("pages/<str:page_id>/", cms_views.cms_page_detail_api, name="cms-page-detail"),
    path("pages/<str:page_id>/publish/", cms_views.cms_publish_page_api, name="cms-page-publish"),

    # Navigation & Hierarchy
    path("navigation/<str:course_id>/", cms_views.cms_navigation_tree_api, name="cms-navigation-tree"),

    # Media Library
    path("media/", cms_views.cms_media_api, name="cms-media"),
    path("media/<str:media_id>/", cms_views.cms_media_delete_api, name="cms-media-delete"),
]
