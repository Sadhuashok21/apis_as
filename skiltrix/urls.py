from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("companies", views.CompaniesViewSet, basename="company")
router.register("internships", views.InternshipViewSet, basename="internship")
router.register("courses", views.CoursesViewSet, basename="course")
router.register("videos", views.VideosViewSet, basename="video")
router.register("problems", views.CodingProblemsViewSet, basename="problem")
router.register("submissions", views.CodeSubmissionsViewSet, basename="submission")
router.register("snippets", views.CompilerSnippetsViewSet, basename="snippet")
router.register("syntax", views.SyntaxMatrixViewSet, basename="syntax")
router.register("quizzes", views.QuizzesViewSet, basename="quiz")
router.register("quiz-attempts", views.QuizAttemptsViewSet, basename="quiz-attempt")
router.register("interview-categories", views.InterviewCategoriesViewSet, basename="interview-category")
router.register("interview-questions", views.InterviewQuestionsViewSet, basename="interview-question")
router.register("roadmaps", views.CompanyRoadmapsViewSet, basename="roadmap")
router.register("discussions", views.DiscussionsViewSet, basename="discussion")
router.register("badges", views.BadgesViewSet, basename="badge")
router.register("notifications", views.NotificationsViewSet, basename="notification")
router.register("profiles", views.UserProfileViewSet, basename="profile")
router.register("languages", views.LanguageViewSet, basename="language")
router.register("modules", views.CourseModulesViewSet, basename="module")
router.register("enrollments", views.CourseEnrollmentsViewSet, basename="enrollment")
router.register("activity", views.DailyActivityViewSet, basename="activity")

urlpatterns = [
    path('', views.internships, name="internships"),
    path('internships/', views.internships, name="internships"),
    path('courses/', views.courses, name="courses"),
    path('profile', views.profile, name="profile"),
    path('profile-skills', views.profile_skills, name="profile_skills"),
    path('profile-resumes', views.profile_resumes, name="profile_resumes"),
    path('profile-education', views.profile_education, name="profile-education"),
    path('videos/', views.videos, name="videos"),
    path('languages/', views.languages, name="languages"),
    path('api/', include(router.urls)),
    path('api/actions/submit-code/', views.submit_code, name="submit-code"),
    path('api/actions/execute-code/', views.execute_compiler_code, name="execute-code"),
    path('api/actions/quiz-attempt/', views.quiz_attempt, name="quiz-attempt"),
    path('api/actions/apply-internship/', views.apply_internship, name="apply-internship"),
    path('api/actions/progress/', views.user_progress, name="user-progress"),
    path('api/actions/notifications/read/', views.mark_notifications_read, name="mark-notifications-read"),
    path('api/actions/enroll-course/', views.enroll_course, name="enroll-course"),
]
