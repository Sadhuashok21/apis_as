from django.urls import path
from .views import *

urlpatterns = [
    path('', internships, name="internships"),
    path('internships/', internships, name="internships"),
    path('courses/', courses, name="courses"),
    path('profile', profile, name="profile"),
    path('profile-skills', profile_skills, name="profile_skills"),
    path('profile-resumes', profile_resumes, name="profile_resumes"),
    path('profile-education', profile_education, name="profile-education"),
    path('videos/', videos, name="videos"),
]