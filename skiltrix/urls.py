from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from . import codelab_views

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
router.register("codelab/projects", codelab_views.CodeProjectViewSet, basename="codelab-project")

urlpatterns = [
    path('api/csrf/', views.csrf_bootstrap, name="csrf-bootstrap"),
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
    path('api/actions/run-sample-code/', views.run_sample_code, name="run-sample-code"),
    path('api/actions/execute-code/', views.execute_compiler_code, name="execute-code"),
    path('api/actions/quiz-attempt/', views.quiz_attempt, name="quiz-attempt"),
    path('api/actions/apply-internship/', views.apply_internship, name="apply-internship"),
    path('api/actions/progress/', views.user_progress, name="user-progress"),
    path('api/actions/notifications/read/', views.mark_notifications_read, name="mark-notifications-read"),
    path('api/actions/enroll-course/', views.enroll_course, name="enroll-course"),
    path('api/actions/logout/', views.signout, name="logout"),

    # CodeLab Specific Endpoints
    path('api/codelab/projects/<str:project_id>/files/', codelab_views.ProjectFileViewSet.as_view({'get': 'list'}), name="codelab-files-list"),
    path('api/codelab/projects/<str:project_id>/files/content/', codelab_views.ProjectFileViewSet.as_view({'get': 'content'}), name="codelab-files-content"),
    path('api/codelab/projects/<str:project_id>/files/save/', codelab_views.ProjectFileViewSet.as_view({'post': 'save'}), name="codelab-files-save"),
    path('api/codelab/projects/<str:project_id>/files/create/', codelab_views.ProjectFileViewSet.as_view({'post': 'create_file'}), name="codelab-files-create"),
    path('api/codelab/projects/<str:project_id>/files/delete/', codelab_views.ProjectFileViewSet.as_view({'delete': 'delete_file'}), name="codelab-files-delete"),
    path('api/codelab/projects/<str:project_id>/files/rename/', codelab_views.ProjectFileViewSet.as_view({'post': 'rename_path'}), name="codelab-files-rename"),
    path('api/codelab/projects/<str:project_id>/files/move/', codelab_views.ProjectFileViewSet.as_view({'post': 'move_path'}), name="codelab-files-move"),
    path('api/codelab/projects/<str:project_id>/files/duplicate/', codelab_views.ProjectFileViewSet.as_view({'post': 'duplicate_file'}), name="codelab-files-duplicate"),
    path('api/codelab/execute/', codelab_views.execute_project_or_code, name="codelab-execute"),

    # CodeLab SQL Playground Endpoints
    path('api/codelab/projects/<str:project_id>/sql/schema/', codelab_views.get_sql_schema, name="codelab-sql-schema"),
    path('api/codelab/projects/<str:project_id>/sql/execute/', codelab_views.execute_sql, name="codelab-sql-execute"),
    path('api/codelab/projects/<str:project_id>/sql/reset/', codelab_views.reset_sql_database, name="codelab-sql-reset"),
    path('api/codelab/projects/<str:project_id>/sql/export-csv/', codelab_views.export_sql_csv, name="codelab-sql-export-csv"),
    path('api/codelab/sql/templates/', codelab_views.list_sql_templates, name="codelab-sql-templates"),

    # CodeLab Django Environment Endpoints
    path('api/codelab/projects/<str:project_id>/django/start/', codelab_views.start_django_server, name="codelab-django-start"),
    path('api/codelab/projects/<str:project_id>/django/stop/', codelab_views.stop_django_server, name="codelab-django-stop"),
    path('api/codelab/projects/<str:project_id>/django/restart/', codelab_views.restart_django_server, name="codelab-django-restart"),
    path('api/codelab/projects/<str:project_id>/django/status/', codelab_views.get_django_server_status, name="codelab-django-status"),
    path('api/codelab/projects/<str:project_id>/django/migrations/', codelab_views.run_django_migrations_endpoint, name="codelab-django-migrations"),
    path('api/codelab/projects/<str:project_id>/django/makemigrations/', codelab_views.run_django_makemigrations_endpoint, name="codelab-django-makemigrations"),
    path('api/codelab/projects/<str:project_id>/django/migrate/', codelab_views.run_django_migrate_endpoint, name="codelab-django-migrate"),
    path('api/codelab/projects/<str:project_id>/django/database/', codelab_views.project_django_database_endpoint, name="codelab-django-database"),
    path('api/codelab/projects/<str:project_id>/django/showmigrations/', codelab_views.run_django_showmigrations_endpoint, name="codelab-django-showmigrations"),
    path('api/codelab/projects/<str:project_id>/django/sqlmigrate/', codelab_views.run_django_sqlmigrate_endpoint, name="codelab-django-sqlmigrate"),
    path('api/codelab/projects/<str:project_id>/django/test/', codelab_views.run_django_tests_endpoint, name="codelab-django-test"),
    path('api/codelab/projects/<str:project_id>/django/check/', codelab_views.run_django_check_endpoint, name="codelab-django-check"),
    path('api/codelab/projects/<str:project_id>/django/create-app/', codelab_views.create_django_app_endpoint, name="codelab-django-create-app"),
    path('api/codelab/projects/<str:project_id>/django/navigation/', codelab_views.get_django_navigation_endpoint, name="codelab-django-navigation"),
    path('api/codelab/projects/<str:project_id>/django/api-request/', codelab_views.test_django_api_endpoint_view, name="codelab-django-api-request"),

    # CodeLab PHP Environment Endpoints
    path('api/codelab/projects/<str:project_id>/php/start/', codelab_views.start_php_server, name="codelab-php-start"),
    path('api/codelab/projects/<str:project_id>/php/stop/', codelab_views.stop_php_server, name="codelab-php-stop"),
    path('api/codelab/projects/<str:project_id>/php/restart/', codelab_views.restart_php_server, name="codelab-php-restart"),
    path('api/codelab/projects/<str:project_id>/php/status/', codelab_views.get_php_server_status, name="codelab-php-status"),
    path('api/codelab/projects/<str:project_id>/php/api-request/', codelab_views.test_php_api_endpoint_view, name="codelab-php-api-request"),

    # CodeLab Interactive Terminal Command Bridge
    path('api/codelab/projects/<str:project_id>/terminal/execute/', codelab_views.execute_terminal_command, name="codelab-terminal-execute"),

    # Live Preview Proxy Endpoints
    path('api/preview/<str:project_id>/', codelab_views.preview_proxy, name="codelab-preview-root"),
    path('api/preview/<str:project_id>/<path:subpath>', codelab_views.preview_proxy, name="codelab-preview-subpath"),

    # CodeLab Observability & System Health
    path('api/codelab/health/', codelab_views.codelab_health_check, name="codelab-health-check"),

    # SAP ABAP Lab Endpoints
    path('api/abap/', include('skiltrix.abap_urls')),
]




