from django.urls import path

from . import coding_assessment_views as cav

urlpatterns = [
    # Student Coding & Unified Assessment APIs
    path("", cav.coding_assessment_list, name="coding-assessment-list"),
    path("submissions/", cav.coding_submissions_list, name="coding-submission-list"),
    # Admin Coding Assessment Management APIs
    path("admin/problems/", cav.admin_coding_problems, name="admin-coding-problems"),
    path(
        "admin/problems/parse-django-archive/",
        cav.admin_parse_django_archive,
        name="admin-parse-django-archive",
    ),
    path(
        "admin/problems/<str:problem_id>/",
        cav.admin_coding_problem_detail,
        name="admin-coding-problem-detail",
    ),
    path(
        "admin/problems/<str:problem_id>/testcases/",
        cav.admin_problem_testcases,
        name="admin-problem-testcases",
    ),
    path(
        "admin/problems/<str:problem_id>/testcases/<str:test_case_id>/",
        cav.admin_problem_testcase_detail,
        name="admin-problem-testcase-detail",
    ),
    path(
        "admin/assessments/",
        cav.admin_coding_assessments,
        name="admin-coding-assessments",
    ),
    path(
        "admin/assessments/<str:assessment_id>/",
        cav.admin_coding_assessment_detail,
        name="admin-coding-assessment-detail",
    ),
    path(
        "admin/assessments/<str:assessment_id>/assignments/",
        cav.admin_assessment_assignments,
        name="admin-assessment-assignments",
    ),
    path(
        "admin/assessments/<str:assessment_id>/assignments/<str:assignment_id>/",
        cav.admin_assessment_assignment_detail,
        name="admin-assessment-assignment-detail",
    ),
    path(
        "admin/assessments/<str:assessment_id>/analytics/",
        cav.admin_assessment_analytics,
        name="admin-assessment-analytics",
    ),
    path(
        "admin/assessments/<str:assessment_id>/release-results/",
        cav.admin_assessment_release_results,
        name="admin-assessment-release-results",
    ),
    path(
        "admin/assessments/<str:assessment_id>/export/",
        cav.admin_assessment_export,
        name="admin-assessment-export",
    ),
    path("admin/batches/", cav.admin_batches, name="admin-batches"),
    path("admin/batches/<str:batch_id>/", cav.admin_batch_detail, name="admin-batch-detail"),
    path("admin/students/", cav.admin_students_search, name="admin-students-search"),
    path("admin/submissions/", cav.admin_all_submissions, name="admin-coding-submissions"),
    # Student Assessment Lifecycle Actions
    path(
        "<str:assessment_id>/",
        cav.coding_assessment_detail,
        name="coding-assessment-detail",
    ),
    path(
        "<str:assessment_id>/start/",
        cav.coding_assessment_start,
        name="coding-assessment-start",
    ),
    path(
        "<str:assessment_id>/run/",
        cav.coding_assessment_run,
        name="coding-assessment-run",
    ),
    path(
        "<str:assessment_id>/codelab-reset/",
        cav.coding_assessment_codelab_reset,
        name="coding-assessment-codelab-reset",
    ),
    path(
        "<str:assessment_id>/submit-problem/",
        cav.coding_assessment_submit_problem,
        name="coding-assessment-submit-problem",
    ),
    path(
        "<str:assessment_id>/autosave/",
        cav.coding_assessment_autosave,
        name="coding-assessment-autosave",
    ),
    path(
        "<str:assessment_id>/event/",
        cav.coding_assessment_event,
        name="coding-assessment-event",
    ),
    path(
        "<str:assessment_id>/submit/",
        cav.coding_assessment_submit,
        name="coding-assessment-submit",
    ),
    path(
        "<str:assessment_id>/result/",
        cav.coding_assessment_result,
        name="coding-assessment-result",
    ),
]
