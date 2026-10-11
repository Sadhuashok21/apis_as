from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from . import codelab_views
from . import tutorial_views
from . import roadmap_views
from . import hardware_views


router = DefaultRouter()
router.register("hardware/boards", hardware_views.HardwareBoardViewSet, basename="hw-board")
router.register("hardware/projects", hardware_views.HardwareProjectViewSet, basename="hw-project")
router.register("hardware/files", hardware_views.HardwareSourceFileViewSet, basename="hw-file")
router.register("hardware/pcb", hardware_views.PcbProjectViewSet, basename="hw-pcb")
router.register("hardware/devices", hardware_views.ConnectedDeviceViewSet, basename="hw-device")

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
router.register("assessments", views.CodingAssessmentViewSet, basename="assessment")
router.register("questions", views.AssessmentQuestionItemViewSet, basename="assessment-question")
router.register("sections", views.AssessmentSectionViewSet, basename="assessment-section")
router.register("blueprints", views.CompanyBlueprintViewSet, basename="blueprint")
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
    # Accounts & SSO fallback routes if client requests under apps/skiltrix/api
    path('api/api/accounts/', include('accounts.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include(router.urls)),
    path('api/actions/submit-code/', views.submit_code, name="submit-code"),
    path('api/actions/run-sample-code/', views.run_sample_code, name="run-sample-code"),
    path('api/actions/execute-code/', views.execute_compiler_code, name="execute-code"),
    path('api/actions/quiz-attempt/', views.quiz_attempt, name="quiz-attempt"),
    path('api/actions/apply-internship/', views.apply_internship, name="apply-internship"),
    path('api/actions/progress/', views.user_progress, name="user-progress"),
    path('api/actions/notifications/read/', views.mark_notifications_read, name="mark-notifications-read"),
    path('api/actions/enroll-course/', views.enroll_course, name="enroll-course"),
    path('api/actions/verify-enrollment-payment/', views.verify_enrollment_payment, name="verify-enrollment-payment"),
    path('api/actions/cancel-enrollment-payment/', views.cancel_enrollment_payment, name="cancel-enrollment-payment"),
    path('api/actions/razorpay-config/', views.get_razorpay_config, name="razorpay-config"),
    path('api/actions/upload-cdn-asset/', views.upload_cdn_asset, name="upload-cdn-asset"),
    path('api/actions/logout/', views.signout, name="logout"),

    # ==============================================================================
    # SkilTrix Programming Tutorial Platform Endpoints
    # ==============================================================================
    path('api/tutorials/tracks/', tutorial_views.list_tutorial_tracks, name="tutorial-tracks-list"),
    path('api/tutorials/tracks/<str:track_id>/', tutorial_views.get_tutorial_track_curriculum, name="tutorial-track-detail"),
    path('api/tutorials/lessons/<str:track_id>/<slug:slug>/', tutorial_views.get_tutorial_lesson_detail, name="tutorial-lesson-detail"),
    path('api/tutorials/progress/', tutorial_views.save_tutorial_progress, name="tutorial-progress-save"),
    path('api/tutorials/bookmarks/toggle/', tutorial_views.toggle_tutorial_bookmark, name="tutorial-bookmark-toggle"),
    path('api/tutorials/notes/', tutorial_views.save_tutorial_note, name="tutorial-note-save"),
    path('api/tutorials/certificate/issue/', tutorial_views.issue_tutorial_certificate, name="tutorial-cert-issue"),
    path('api/tutorials/certificate/<str:cert_id>/', tutorial_views.get_tutorial_certificate, name="tutorial-cert-detail"),
    path('api/tutorials/search/', tutorial_views.search_tutorials, name="tutorial-search"),

    # ==============================================================================
    # SkilTrix Career Learning Roadmaps (Matching Android App Implementation)
    # ==============================================================================
    path('api/learning-roadmaps/', roadmap_views.list_career_roadmaps, name="career-roadmaps-list"),
    path('api/learning-roadmaps/<str:roadmap_key>/', roadmap_views.get_career_roadmap_detail, name="career-roadmap-detail"),
    path('api/learning-roadmaps/<str:roadmap_key>/stage/<int:stage_number>/toggle/', roadmap_views.toggle_career_stage_progress, name="career-roadmap-stage-toggle"),
    path('api/learning-roadmaps/<str:roadmap_key>/reset/', roadmap_views.reset_career_roadmap_progress, name="career-roadmap-reset"),
    path('api/learning-roadmaps/sync/', roadmap_views.sync_career_roadmaps_progress, name="career-roadmaps-sync"),
    path('learning-roadmaps/', roadmap_views.list_career_roadmaps),
    path('learning-roadmaps/<str:roadmap_key>/', roadmap_views.get_career_roadmap_detail),
    path('learning-roadmaps/<str:roadmap_key>/stage/<int:stage_number>/toggle/', roadmap_views.toggle_career_stage_progress),
    path('learning-roadmaps/<str:roadmap_key>/reset/', roadmap_views.reset_career_roadmap_progress),
    path('learning-roadmaps/sync/', roadmap_views.sync_career_roadmaps_progress),



    # Company Mock & Assessment Evaluation Endpoints
    path('api/actions/start-assessment/', views.start_assessment, name="start-assessment"),
    path('api/actions/autosave-assessment-draft/', views.autosave_assessment_draft, name="autosave-assessment-draft"),
    path('api/actions/record-assessment-event/', views.record_assessment_event, name="record-assessment-event"),
    path('api/actions/submit-assessment/', views.submit_assessment, name="submit-assessment"),
    path('api/actions/admin-assessment-monitoring/', views.admin_assessment_monitoring, name="admin-assessment-monitoring"),
    path('api/actions/company-preparation-stats/', views.company_preparation_stats, name="company-preparation-stats"),
    path('api/problems/<str:problem_id>/explanation/', views.get_problem_explanation, name="problem-explanation"),

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




