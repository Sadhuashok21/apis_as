import uuid
import hmac
import hashlib
import requests
from django.conf import settings
from django.http import JsonResponse, Http404
from django.middleware.csrf import get_token

from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.contrib.auth import logout as auth_logout
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from sfs.models import AllUsers


@ensure_csrf_cookie
def csrf_bootstrap(request):
    """Expose the CSRF token to credentialed browser clients on another origin."""
    return JsonResponse({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def signout(request):
    auth_logout(request)
    return Response({"status": True})
from .models import (
    Companies,
    Internship,
    Courses,
    Videos,
    Comments,
    Ratings,
    Language,
    CourseCategories,
    Resumes,
    Skills,
    Education,
    Code,
    Likes,
    UserProfile,
    Badges,
    UserBadges,
    DailyActivity,
    CodingProblems,
    TestCases,
    CodeSubmissions,
    UserProblemStatus,
    CompilerSnippets,
    SyntaxMatrix,
    Quizzes,
    QuizQuestions,
    QuizOptions,
    QuizAttempts,
    QuizUserAnswers,
    InterviewCategories,
    InterviewQuestions,
    CompanyRoadmaps,
    MockInterviewSessions,
    Discussions,
    DiscussionReplies,
    DiscussionLikes,
    DiscussionBookmarks,
    CourseModules,
    CourseLessons,
    CourseEnrollments,
    CoursePaymentOrder,
    VideoSubtitles,
    VideoProgress,
    VideoNotes,
    InternshipApplications,
    SavedInternships,
    Notifications,
    CodingAssessment,
    AssessmentQuestion,
    AssessmentAttempt,
    AssessmentSection,
    AssessmentQuestionItem,
    AssessmentEvent,
    CompanyBlueprint,
)

from .serializers import (
    UserSummarySerializer,
    UserProfileSerializer,
    BadgesSerializer,
    UserBadgesSerializer,
    DailyActivitySerializer,
    ResumeSerializer,
    SkillSerializer,
    EducationSerializer,
    TestCaseSerializer,
    CodingProblemListSerializer,
    CodingProblemDetailSerializer,
    CodingAssessmentListSerializer,
    CodingAssessmentDetailSerializer,
    AssessmentAttemptSerializer,
    AssessmentSectionSerializer,
    AssessmentQuestionItemCandidateSerializer,
    AssessmentQuestionItemFullSerializer,
    AssessmentEventSerializer,
    CompanyBlueprintSerializer,
    CodeSubmissionSerializer,
    UserProblemStatusSerializer,
    CompilerSnippetSerializer,
    SyntaxMatrixSerializer,
    LanguageSerializer,
    CodeSerializer,
    QuizListSerializer,
    QuizDetailSerializer,
    QuizAttemptSerializer,
    InterviewCategorySerializer,
    InterviewQuestionSerializer,
    CompanyRoadmapSerializer,
    CompanySerializer,
    InternshipSerializer,
    InternshipApplicationSerializer,
    SavedInternshipSerializer,
    CourseSerializer,
    CourseModuleSerializer,
    CourseLessonSerializer,
    CourseEnrollmentSerializer,
    VideoSerializer,
    VideoSubtitleSerializer,
    VideoProgressSerializer,
    VideoNoteSerializer,
    CommentSerializer,
    RatingSerializer,
    LikeSerializer,
    DiscussionListSerializer,
    DiscussionDetailSerializer,
    DiscussionReplySerializer,
    DiscussionLikeSerializer,
    DiscussionBookmarkSerializer,
    NotificationSerializer,
)


# ==============================================================================
# EXISTING FUNCTION-BASED VIEWS (PRESERVED FOR BACKWARD COMPATIBILITY)
# ==============================================================================

def internships(request):
    type_filter = request.GET.get('type', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if type_filter == 'paid':
        items = Internship.objects.filter(status="active", is_paid=1).values()
    elif type_filter == 'free':
        items = Internship.objects.filter(status="active", is_paid=0).values()
    elif type_filter == 'remote':
        items = Internship.objects.filter(status="active", location='remote').values()
    else:
        items = Internship.objects.filter(status="active").values()

    data.update({"internships": list(items)})
    return JsonResponse(data, safe=False)


def profile(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
        user_obj = AllUsers.objects.filter(status="approved", user_id=user_id).first()
        if user_obj:
            data.update({'action': user_obj.user_id, 'name': user_obj.name, 'email': user_obj.email})
        else:
            data.update({'action': "no"})
    else:
        data.update({"action": "empty"})

    return JsonResponse(data, safe=False)


def profile_skills(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
        user_obj = AllUsers.objects.filter(status="active", user_id=user_id).first()
        if user_obj:
            skills_qs = Skills.objects.filter(user_id=user_id)
            data.update({"skills": list(skills_qs.values()), 'profile': user_obj.user_id})
        else:
            data.update({'action': "no"})
    else:
        data.update({"action": "empty"})

    return JsonResponse(data, safe=False)


def recommend(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    user_id = request.GET.get('user_id', '')
    if user_id:
        data.update({'profile': user_id})
    return JsonResponse(data, safe=False)


def courses(request):
    type_filter = request.GET.get("type", '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if type_filter == 'free':
        items = Courses.objects.filter(status="active", is_paid=0).values()
    elif type_filter == 'paid':
        items = Courses.objects.filter(status="active", is_paid=1).values()
    else:
        items = Courses.objects.filter(status="active").values()

    data.update({"courses": list(items)})
    return JsonResponse(data, safe=False)


def languages(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    langs = Language.objects.filter(status="active").values()
    data.update({"languages": list(langs)})
    return JsonResponse(data, safe=False)


def videos(request):
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    from apis.cdn_utils import get_st_video_url, get_st_image_url
    video_list = []
    for v in Videos.objects.filter(status="active").values():
        v["video_url"] = get_st_video_url(v.get("video", ""))
        v["image_url"] = get_st_image_url(v.get("image", ""))
        video_list.append(v)
    data.update({"videos": video_list})
    return JsonResponse(data, safe=False)


def profile_resumes(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
        from apis.cdn_utils import get_st_pdf_url
        resumes_qs = Resumes.objects.filter(status="active", user_id=user_id)
        resumes_list = []
        for r in resumes_qs.values():
            r["pdf_url"] = get_st_pdf_url(r.get("name", ""))
            resumes_list.append(r)
        data.update({"resumes": resumes_list})
    else:
        data.update({"action": "nouser"})

    return JsonResponse(data, safe=False)


def profile_education(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
        edu_qs = Education.objects.filter(status="active", user_id=user_id)
        data.update({'education': list(edu_qs.values())})
    else:
        data.update({"action": "nouser"})

    return JsonResponse(data, safe=False)


# ==============================================================================
# REST FRAMEWORK VIEWSETS FOR ALL SKILTRIX MODELS
# ==============================================================================

class CompaniesViewSet(viewsets.ModelViewSet):
    queryset = Companies.objects.filter(status="active").prefetch_related("roadmaps")
    serializer_class = CompanySerializer
    lookup_field = "company_id"

    def perform_create(self, serializer):
        cid = serializer.validated_data.get("company_id") or f"comp_{uuid.uuid4().hex[:10]}"
        img = serializer.validated_data.get("image") or "default_company.png"
        serializer.save(company_id=cid, image=img)


class InternshipViewSet(viewsets.ModelViewSet):
    serializer_class = InternshipSerializer
    lookup_field = "internship_id"

    def get_queryset(self):
        qs = Internship.objects.filter(status="active").select_related("company")
        type_param = self.request.query_params.get("type")
        paid_param = self.request.query_params.get("paid")
        if type_param:
            qs = qs.filter(type=type_param)
        if paid_param is not None:
            qs = qs.filter(is_paid=(paid_param.lower() in ["true", "1"]))
        return qs

    def perform_create(self, serializer):
        iid = serializer.validated_data.get("internship_id") or f"intern_{uuid.uuid4().hex[:10]}"
        company_id = self.request.data.get("company_id")
        comp = None
        if company_id:
            comp = Companies.objects.filter(company_id=company_id).first()
        serializer.save(internship_id=iid, company=comp)


class CoursesViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    lookup_field = "course_id"

    def get_queryset(self):
        qs = Courses.objects.filter(status="active").prefetch_related("modules__lessons")
        type_param = self.request.query_params.get("type")
        paid_param = self.request.query_params.get("paid")
        if type_param:
            qs = qs.filter(type=type_param)
        if paid_param is not None:
            qs = qs.filter(is_paid=(paid_param.lower() in ["true", "1"]))
        return qs

    def perform_create(self, serializer):
        user = AllUsers.objects.first()
        cid = serializer.validated_data.get("course_id") or f"crs_{uuid.uuid4().hex[:10]}"
        img = serializer.validated_data.get("image") or "default_course.png"
        serializer.save(user=user, course_id=cid, image=img)


class VideosViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    lookup_field = "video_id"

    def get_queryset(self):
        qs = Videos.objects.filter(status="active").prefetch_related("subtitles")
        course_id = self.request.query_params.get("course_id")
        if course_id:
            qs = qs.filter(course__course_id=course_id)
        return qs

    def perform_create(self, serializer):
        user = AllUsers.objects.first()
        vid = serializer.validated_data.get("video_id") or f"vid_{uuid.uuid4().hex[:10]}"
        img = serializer.validated_data.get("image") or "default_video.webp"
        course_id = self.request.data.get("course_id")
        course = Courses.objects.filter(course_id=course_id).first() if course_id else None
        if not course:
            course = Courses.objects.first()
        serializer.save(user=user, video_id=vid, image=img[:50], course=course)


class CodingProblemsViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "problem_id"

    def get_queryset(self):
        qs = CodingProblems.objects.filter(status="active").prefetch_related("test_cases")
        difficulty = self.request.query_params.get("difficulty")
        topic = self.request.query_params.get("topic")
        category = self.request.query_params.get("category")
        qtype = self.request.query_params.get("type") or self.request.query_params.get("question_type")

        if difficulty and difficulty != "All":
            qs = qs.filter(difficulty__iexact=difficulty)
        if category and category != "All":
            qs = qs.filter(category__iexact=category)
        if qtype and qtype != "All":
            qs = qs.filter(question_type__iexact=qtype)
        if topic and topic != "All":
            qs = qs.filter(topics__contains=topic)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CodingProblemDetailSerializer
        return CodingProblemListSerializer


class CodeSubmissionsViewSet(viewsets.ModelViewSet):
    serializer_class = CodeSubmissionSerializer
    lookup_field = "submission_id"

    def get_queryset(self):
        qs = CodeSubmissions.objects.select_related("user", "problem")
        user_id = self.request.query_params.get("user_id")
        problem_id = self.request.query_params.get("problem_id")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if problem_id:
            qs = qs.filter(problem__problem_id=problem_id)
        return qs


class CompilerSnippetsViewSet(viewsets.ModelViewSet):
    serializer_class = CompilerSnippetSerializer
    lookup_field = "snippet_id"

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return CompilerSnippets.objects.filter(user_id=user_id, status="active")
        return CompilerSnippets.objects.filter(is_public=True, status="active")


class SyntaxMatrixViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SyntaxMatrix.objects.all().order_by("order")
    serializer_class = SyntaxMatrixSerializer
    lookup_field = "entry_id"


class QuizzesViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "quiz_id"

    def get_queryset(self):
        qs = Quizzes.objects.filter(status="active").prefetch_related("questions__options")
        topic = self.request.query_params.get("topic")
        difficulty = self.request.query_params.get("difficulty")
        if topic:
            qs = qs.filter(topic__iexact=topic)
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuizDetailSerializer
        return QuizListSerializer


class QuizAttemptsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuizAttemptSerializer
    lookup_field = "attempt_id"

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return QuizAttempts.objects.filter(user_id=user_id).select_related("quiz").order_by("-created_at")
        return QuizAttempts.objects.none()


class InterviewCategoriesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InterviewCategories.objects.filter(status="active")
    serializer_class = InterviewCategorySerializer
    lookup_field = "category_id"


class InterviewQuestionsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InterviewQuestionSerializer
    lookup_field = "interview_id"

    def get_queryset(self):
        qs = InterviewQuestions.objects.filter(status="active").select_related("category")
        topic = self.request.query_params.get("topic")
        difficulty = self.request.query_params.get("difficulty")
        category_id = self.request.query_params.get("category_id")
        if topic:
            qs = qs.filter(topic__iexact=topic)
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        if category_id:
            qs = qs.filter(category__category_id=category_id)
        return qs


class CompanyRoadmapsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyRoadmapSerializer
    lookup_field = "roadmap_id"

    def get_queryset(self):
        qs = CompanyRoadmaps.objects.all().order_by("step_number")
        company_id = self.request.query_params.get("company_id")
        if company_id:
            qs = qs.filter(company__company_id=company_id)
        return qs


class DiscussionsViewSet(viewsets.ModelViewSet):
    lookup_field = "discussion_id"

    def get_queryset(self):
        qs = Discussions.objects.filter(status="active").select_related("user").prefetch_related("replies__user")
        tag = self.request.query_params.get("tag")
        if tag and tag.lower() != "all":
            qs = qs.filter(tag__iexact=tag)
        return qs.order_by("-is_pinned", "-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DiscussionDetailSerializer
        return DiscussionListSerializer

    def perform_create(self, serializer):
        user_id = self.request.data.get("user_id")
        user = None
        if user_id:
            user = AllUsers.objects.filter(user_id=user_id).first()
            if not user:
                user = AllUsers.objects.filter(username=user_id).first()
            if not user:
                user = AllUsers.objects.filter(email=user_id).first()
        if not user and self.request.user and self.request.user.is_authenticated:
            user = AllUsers.objects.filter(username=self.request.user.username).first() or \
                   AllUsers.objects.filter(email=self.request.user.email).first()
        if not user and user_id:
            user, _ = AllUsers.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "username": f"user_{str(user_id)[:15]}",
                    "name": "SkilTrix Learner",
                    "email": f"{user_id}@skiltrix.internal" if "@" not in str(user_id) else str(user_id),
                    "user_type": "user",
                    "status": "approved",
                }
            )
        if not user:
            user = AllUsers.objects.exclude(user_id="").first()

        disc_id = f"disc_{uuid.uuid4().hex[:10]}"
        serializer.save(discussion_id=disc_id, user=user)


class BadgesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Badges.objects.filter(status="active")
    serializer_class = BadgesSerializer
    lookup_field = "badge_id"


class NotificationsViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    lookup_field = "notification_id"

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return Notifications.objects.filter(user_id=user_id).order_by("-created_at")
        return Notifications.objects.none()


class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    lookup_field = "user__user_id"

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        user_id = (
            self.kwargs.get(lookup_url_kwarg)
            or self.kwargs.get("user__user_id")
            or self.kwargs.get("pk")
            or self.request.query_params.get("user_id")
        )
        if not user_id and getattr(self.request, "user", None) and self.request.user.is_authenticated:
            user_id = getattr(self.request.user, "user_id", None)

        if not user_id:
            raise Http404("User ID not provided.")

        user = AllUsers.objects.filter(user_id=user_id).first()
        if not user:
            raise Http404(f"User '{user_id}' does not exist.")

        profile, _ = UserProfile.objects.select_related("user").get_or_create(user=user)
        self.check_object_permissions(self.request, profile)
        return profile

    def get_queryset(self):
        user_id = (
            self.request.query_params.get("user_id")
            or self.kwargs.get("user__user_id")
            or self.kwargs.get("pk")
        )
        if not user_id and getattr(self.request, "user", None) and self.request.user.is_authenticated:
            user_id = getattr(self.request.user, "user_id", None)

        if user_id:
            user = AllUsers.objects.filter(user_id=user_id).first()
            if user:
                UserProfile.objects.get_or_create(user=user)
            return UserProfile.objects.filter(user__user_id=user_id).select_related("user")

        return UserProfile.objects.all().select_related("user")

    def perform_update(self, serializer):
        profile = serializer.save()
        full_name = self.request.data.get("name")
        if full_name is not None:
            parts = str(full_name).strip().split(maxsplit=1)
            profile.user.name = parts[0] if parts else ""
            if len(parts) > 1:
                profile.user.lastname = parts[1]
            profile.user.save(update_fields=["name", "lastname"])



class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.all().order_by("name")
    serializer_class = LanguageSerializer
    lookup_field = "language_id"

    def perform_create(self, serializer):
        admin_user = AllUsers.objects.first()
        lang_id = self.request.data.get("language_id") or f"lang_{uuid.uuid4().hex[:8]}"
        serializer.save(language_id=lang_id, user=admin_user)


class CourseModulesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseModuleSerializer
    lookup_field = "module_id"

    def get_queryset(self):
        qs = CourseModules.objects.all().prefetch_related("lessons")
        course_id = self.request.query_params.get("course_id")
        if course_id:
            qs = qs.filter(course__course_id=course_id)
        return qs


class CourseEnrollmentsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseEnrollmentSerializer
    lookup_field = "enrollment_id"

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return CourseEnrollments.objects.filter(user_id=user_id).select_related("course").prefetch_related("course__modules__lessons")
        return CourseEnrollments.objects.none()


class DailyActivityViewSet(viewsets.ModelViewSet):
    serializer_class = DailyActivitySerializer
    lookup_field = "activity_id"

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return DailyActivity.objects.filter(user_id=user_id).order_by("-date")
        return DailyActivity.objects.none()


# ==============================================================================
# CUSTOM ACTION ENDPOINTS
# ==============================================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def submit_code(request):
    """
    Submit code for a coding problem. Evaluates against test cases,
    creates CodeSubmissions record, and updates UserProblemStatus.
    """
    user_id = request.data.get("user_id")
    problem_id = request.data.get("problem_id")
    language = request.data.get("language", "python")
    code = request.data.get("code", "")

    if not all([user_id, problem_id, code]):
        return Response(
            {"status": False, "message": "user_id, problem_id, and code are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = AllUsers.objects.filter(user_id=user_id).first()
    problem = CodingProblems.objects.filter(problem_id=problem_id).first()

    if not user:
        return Response({"status": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    if not problem:
        return Response({"status": False, "message": "Problem not found"}, status=status.HTTP_404_NOT_FOUND)

    # Evaluate test cases with real execution engine
    from .codelab_evaluator import evaluate_test_cases
    from .codelab_models import SubmissionResult

    eval_result = evaluate_test_cases(
        problem=problem,
        language=language,
        code=code,
        is_sample_only=False,
    )
    sub_status = eval_result["verdict"]
    passed_tc = eval_result["passed_count"]
    total_tc = eval_result["total_count"]
    exec_time = eval_result["total_duration_ms"]
    memory_used = eval_result["max_memory_kb"]

    submission_id = f"sub_{uuid.uuid4().hex[:12]}"
    submission = CodeSubmissions.objects.create(
        submission_id=submission_id,
        user=user,
        problem=problem,
        language=language,
        code=code,
        status=sub_status,
        passed_test_cases=passed_tc,
        total_test_cases=total_tc,
        execution_time_ms=exec_time,
        memory_kb=memory_used,
        score=problem.points if sub_status == "Accepted" else 0
    )

    # Save detailed per-test-case results
    for tr in eval_result["test_results"]:
        SubmissionResult.objects.create(
            result_id=f"res_{uuid.uuid4().hex[:12]}",
            submission_id=submission_id,
            test_case_id=tr["test_case_id"],
            verdict=tr["verdict"],
            execution_time_ms=tr.get("execution_time_ms", 0.0),
            memory_kb=tr.get("memory_kb", 0.0),
            actual_output=tr.get("actual_output", ""),
            error_message=tr.get("error_message", ""),
        )

    # Update or create user problem status
    user_status, _ = UserProblemStatus.objects.get_or_create(
        user=user,
        problem=problem,
        defaults={"status_id": f"ups_{uuid.uuid4().hex[:10]}"}
    )
    user_status.attempts += 1
    if sub_status == "Accepted":
        user_status.solved = True
        user_status.best_submission = submission
        problem.solved_count += 1
        problem.save(update_fields=["solved_count"])
    user_status.save()

    # Update profile XP
    profile_obj = UserProfile.objects.filter(user=user).first()
    if profile_obj and sub_status == "Accepted":
        profile_obj.total_xp += problem.points
        profile_obj.problems_solved += 1
        profile_obj.save(update_fields=["total_xp", "problems_solved"])

    return Response({
        "status": True,
        "message": "Submission evaluated successfully",
        "submission": CodeSubmissionSerializer(submission).data,
        "result": {
            "verdict": sub_status,
            "passed": passed_tc,
            "total": total_tc,
            "duration_ms": exec_time,
            "points_earned": problem.points if sub_status == "Accepted" else 0,
            "performance_status": eval_result.get("performance_status", "Optimal"),
            "expected_complexity": getattr(problem, "expected_complexity", ""),
            "explanation": getattr(problem, "explanation", "") or getattr(problem, "description", ""),
            "solution_code": getattr(problem, "solution_code", ""),
            "test_results": eval_result["test_results"],
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def run_sample_code(request):
    """
    Run code against sample test cases only, returning detailed output for user inspection.
    """
    problem_id = request.data.get("problem_id")
    language = request.data.get("language", "python")
    code = request.data.get("code", "")

    problem = CodingProblems.objects.filter(problem_id=problem_id).first()
    if not problem:
        return Response({"status": False, "message": "Problem not found"}, status=status.HTTP_404_NOT_FOUND)

    from .codelab_evaluator import evaluate_test_cases
    eval_result = evaluate_test_cases(
        problem=problem,
        language=language,
        code=code,
        is_sample_only=True,
    )

    return Response({
        "status": True,
        "verdict": eval_result["verdict"],
        "passed": eval_result["passed_count"],
        "total": eval_result["total_count"],
        "duration_ms": eval_result["total_duration_ms"],
        "test_results": eval_result["test_results"],
    })



@api_view(["POST"])
@permission_classes([AllowAny])
def execute_compiler_code(request):
    """Run a short single-file program in Wandbox's isolated compiler sandbox."""
    import re

    language = str(request.data.get("language", "")).lower().strip()
    # Accept API/database IDs too, so stale frontend bundles still resolve to the real language name.
    language_record = Language.objects.filter(language_id__iexact=language).first()
    if language_record:
        language = language_record.name.lower().strip()
    language_key = re.sub(r"[^a-z0-9+#]", "", language)
    code = request.data.get("code", "")
    stdin = request.data.get("stdin", "")
    aliases = {
        "py": {"python", "python3"},
        "python": {"python", "python3"},
        "python3": {"python", "python3"},
        "python37": {"python", "python3"},
        "python38": {"python", "python3"},
        "python39": {"python", "python3"},
        "python310": {"python", "python3"},
        "python311": {"python", "python3"},
        "python312": {"python", "python3"},
        "python313": {"python", "python3"},
        "java": {"java"},
        "java17": {"java"},
        "c": {"c"},
        "cpp": {"c++", "cpp", "cxx"},
        "cpp20": {"c++", "cpp", "cxx"},
        "c++": {"c++", "cpp", "cxx"},
        "c++20": {"c++", "cpp", "cxx"},
        "javascript": {"javascript", "node", "nodejs"},
        "js": {"javascript", "node", "nodejs"},
        "nodejs": {"javascript", "node", "nodejs"},
        "csharp": {"c#", "csharp"},
        "c#": {"c#", "csharp"},
        "sql": {"sql"},
    }
    if not language_key or len(language_key) > 40:
        return Response({"detail": "A valid compiler language is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(code, str) or not code.strip():
        return Response({"detail": "Enter code before running it."}, status=status.HTTP_400_BAD_REQUEST)
    if len(code) > 32000 or not isinstance(stdin, str) or len(stdin) > 8000:
        return Response({"detail": "Code or standard input exceeds the size limit."}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    # Reject common destructive file/process APIs before forwarding code to the runner.
    # The runner remains the isolation boundary; this is an additional policy layer.
    scan_code = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`', " ", code)
    scan_code = re.sub(r"/\*[\s\S]*?\*/|//[^\r\n]*", " ", scan_code)
    if language_key in {"python", "py", "python3"}:
        scan_code = re.sub(r"#[^\r\n]*", " ", scan_code)
    safety_patterns = [
        r"\bos\s*\.\s*(?:remove|removeall|unlink|rmdir|system|create|writefile)\s*\(",
        r"\bshutil\s*\.\s*(?:rmtree|move)\s*\(",
        r"\bsubprocess\s*\.",
        r"\b(?:ProcessBuilder|Runtime\s*\.\s*getRuntime\s*\(\)\s*\.\s*exec)\b",
        r"\b(?:exec\s*\.\s*Command|Command\s*::\s*new|Process\s*\.\s*Start)\b",
        r"\b(?:Files\s*\.\s*(?:delete|deleteIfExists|write|move|copy|create)|File\s*\.\s*delete)\s*\(",
        r"\bnew\s+(?:FileOutputStream|FileWriter|RandomAccessFile)\s*\(",
        r"\.\s*delete\s*\(",
        r"\b(?:child_process|process\.binding)\b",
        r"\b(?:fs|filesystem|Deno)\s*\.\s*(?:unlink|rm|rmdir|writeFile|appendFile|remove)\s*(?:Sync)?\s*\(",
        r"\b(?:std\s*::\s*fs|std\.fs)\s*::\s*(?:remove|remove_file|remove_dir|remove_dir_all|write)",
        r"\b(?:FileUtils\s*\.\s*rm|rm\s+-[^\r\n]*(?:r|f)|del\s+/[fq])",
        r"\b(?:fopen|freopen)\s*\([^,]+,\s*['\"]\s*[wax+]+",
        r"\b(?:ofstream|fstream)\s+[A-Za-z_]",
        r"\b(?:Remove-Item|remove-item|shutil\.rmtree)\b",
        r"\b(?:system|popen)\s*\(",
        r"\b(?:unlink|rmdir)\s*\(",
    ]
    unsafe_operation = any(re.search(pattern, scan_code, re.IGNORECASE) for pattern in safety_patterns)
    if language_key in {"c", "cpp", "c++", "go", "rust"} and re.search(r"\b(?:execve?|execlp?|execvp?)\s*\(", scan_code, re.IGNORECASE):
        unsafe_operation = True
    if language_key in {"python", "py", "python3"}:
        import ast

        try:
            tree = ast.parse(code)
        except SyntaxError:
            tree = None  # Let the compiler return the usual syntax error.
        if tree:
            module_aliases = {"os": {"os"}, "shutil": {"shutil"}, "subprocess": {"subprocess"}}
            symbol_aliases = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in module_aliases:
                            module_aliases[alias.name].add(alias.asname or alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module in module_aliases:
                    symbol_aliases.update(alias.asname or alias.name for alias in node.names)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
                root, _, member = function.partition(".")
                if (
                    (root in module_aliases["os"] and member in {"remove", "unlink", "rmdir", "system"})
                    or (root in module_aliases["shutil"] and member in {"rmtree", "move"})
                    or root in module_aliases["subprocess"]
                    or function in symbol_aliases
                    or (member in {"unlink", "rmdir", "write_text", "write_bytes", "touch"})
                    or (function == "open" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and any(flag in str(node.args[1].value) for flag in "wax+"))
                ):
                    unsafe_operation = True
                    break
    if unsafe_operation:
        return Response({"detail": "This compiler blocks file deletion/writes and process-launching code. Remove that operation to run the program."}, status=status.HTTP_403_FORBIDDEN)

    source_code = code
    if language_key in {"java", "java17"}:
        public_class = re.search(r"\bpublic\s+(?:final\s+)?(?:class|record|enum)\s+([A-Za-z_$][\w$]*)", code)
        if public_class:
            declared_name = public_class.group(1)
            # Wandbox compiles Java from prog.java. Rename the public class and code references,
            # while leaving comments and string/character literals exactly as the user wrote them.
            java_tokens = re.compile(r'"""[\s\S]*?"""|//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*')
            source_code = java_tokens.sub(
                lambda match: "prog" if match.group(0) == declared_name else match.group(0),
                code,
            )

    try:
        runtimes_response = requests.get("https://wandbox.org/api/list.json", timeout=(4, 8))
        runtimes_response.raise_for_status()
        runtimes = runtimes_response.json()
        accepted_names = aliases.get(language_key, {language_key})
        candidates = [
            runtime for runtime in runtimes
            if re.sub(r"[^a-z0-9+#]", "", str(runtime.get("language", "")).lower()) in accepted_names
        ]
        if not candidates:
            return Response({"detail": f"No {language} runtime is currently available."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Prefer the newest stable runtime; experimental `head` entries can lack installed executables.
        stable = [item for item in candidates if not str(item.get("name", "")).endswith("head")]
        candidates = stable or candidates
        def runtime_version(item):
            version_text = f"{item.get('version', '')} {item.get('name', '')}"
            return tuple(int(part) for part in re.findall(r"\d+", version_text))
        candidates.sort(key=runtime_version, reverse=True)
        if language_key in {"cpp", "cpp20", "c++", "c++20"}:
            gcc = [item for item in candidates if str(item.get("name", "")).lower().startswith("gcc")]
            if gcc:
                candidates = gcc + [item for item in candidates if item not in gcc]

        result = {}
        compiler = candidates[0]
        for compiler in candidates[:5]:
            result_response = requests.post(
                "https://wandbox.org/api/compile.json",
                json={"compiler": compiler["name"], "code": source_code, "stdin": stdin},
                timeout=(4, 35),
            )
            result_response.raise_for_status()
            result = result_response.json()
            runtime_error = " ".join(str(result.get(key) or "") for key in ("program_output", "program_error", "compiler_error", "program_message"))
            runtime_error_lower = runtime_error.lower()
            missing_cpp_runtime = language_key in {"cpp", "cpp20", "c++", "c++20"} and any(
                marker in runtime_error_lower
                for marker in ("'iostream' file not found", "'vector' file not found", "standard library headers not found")
            )
            if not (
                "catatonit" in runtime_error_lower
                or "failed to exec pid1" in runtime_error_lower
                or missing_cpp_runtime
            ):
                break
    except requests.RequestException:
        return Response({"detail": "The code execution service is unavailable. Please try again shortly."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except (ValueError, KeyError, TypeError):
        return Response({"detail": "The code execution service returned an invalid response."}, status=status.HTTP_502_BAD_GATEWAY)

    output = "".join([
        str(result.get("program_output") or ""),
        str(result.get("program_error") or ""),
        str(result.get("compiler_error") or ""),
    ]).strip()
    success = str(result.get("status", "1")) == "0"
    return Response({"success": success, "output": output or ("Program completed with no output." if success else "Execution failed."), "runtime": compiler.get("display-name", compiler.get("name"))})


@api_view(["POST"])
@permission_classes([AllowAny])
def quiz_attempt(request):
    """
    Submit answers for a quiz attempt. Calculates score and creates QuizAttempts record.
    """
    user_id = request.data.get("user_id")
    quiz_id = request.data.get("quiz_id")
    answers = request.data.get("answers", [])  # list of {question_id, selected_option_id}
    time_taken = request.data.get("time_taken_seconds", 0)

    if not all([user_id, quiz_id]):
        return Response(
            {"status": False, "message": "user_id and quiz_id are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = AllUsers.objects.filter(user_id=user_id).first()
    quiz = Quizzes.objects.filter(quiz_id=quiz_id).first()

    if not user or not quiz:
        return Response({"status": False, "message": "User or Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

    questions = QuizQuestions.objects.filter(quiz=quiz).prefetch_related("options")
    total_q = questions.count()
    correct_count = 0

    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    attempt = QuizAttempts.objects.create(
        attempt_id=attempt_id,
        user=user,
        quiz=quiz,
        total_questions=total_q,
        time_taken_seconds=time_taken
    )

    for ans in answers:
        q_id = ans.get("question_id")
        opt_id = ans.get("selected_option_id")
        question = questions.filter(question_id=q_id).first()
        selected_opt = QuizOptions.objects.filter(option_id=opt_id).first() if opt_id else None

        is_correct = bool(selected_opt and selected_opt.is_correct)
        if is_correct:
            correct_count += 1

        if question:
            QuizUserAnswers.objects.create(
                user_answer_id=f"qua_{uuid.uuid4().hex[:12]}",
                attempt=attempt,
                question=question,
                selected_option=selected_opt,
                is_correct=is_correct
            )

    percentage = round((correct_count / total_q * 100), 1) if total_q > 0 else 0
    passed = percentage >= quiz.passing_score
    score = int((percentage / 100) * quiz.points)

    attempt.score = score
    attempt.correct_count = correct_count
    attempt.incorrect_count = total_q - correct_count
    attempt.percentage = percentage
    attempt.passed = passed
    attempt.save()

    # Update profile quizzes completed
    profile_obj = UserProfile.objects.filter(user=user).first()
    if profile_obj:
        profile_obj.quizzes_completed += 1
        profile_obj.total_xp += score
        profile_obj.save(update_fields=["quizzes_completed", "total_xp"])

    return Response({
        "status": True,
        "message": "Quiz attempt recorded",
        "attempt": QuizAttemptSerializer(attempt).data,
        "result": {
            "score": score,
            "percentage": percentage,
            "passed": passed,
            "correct": correct_count,
            "total": total_q
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def apply_internship(request):
    """
    Apply for an internship position.
    """
    user_id = request.data.get("user_id")
    internship_id = request.data.get("internship_id")
    cover_letter = request.data.get("cover_letter", "")
    portfolio_url = request.data.get("portfolio_url", "")
    resume_id = request.data.get("resume_id")

    if not all([user_id, internship_id]):
        return Response(
            {"status": False, "message": "user_id and internship_id are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = AllUsers.objects.filter(user_id=user_id).first()
    internship_obj = Internship.objects.filter(internship_id=internship_id).first()

    if not user or not internship_obj:
        return Response({"status": False, "message": "User or Internship not found"}, status=status.HTTP_404_NOT_FOUND)

    resume = Resumes.objects.filter(resume_id=resume_id).first() if resume_id else None

    app_id = f"app_{uuid.uuid4().hex[:12]}"
    application, created = InternshipApplications.objects.get_or_create(
        internship=internship_obj,
        user=user,
        defaults={
            "application_id": app_id,
            "cover_letter": cover_letter,
            "portfolio_url": portfolio_url,
            "resume": resume,
            "status": "applied"
        }
    )

    return Response({
        "status": True,
        "message": "Application submitted successfully" if created else "Application updated",
        "application": InternshipApplicationSerializer(application).data
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def user_progress(request):
    """
    Get aggregated user stats and learning progression.
    """
    user_id = request.query_params.get("user_id")
    if not user_id:
        return Response({"status": False, "message": "user_id query param is required"}, status=status.HTTP_400_BAD_REQUEST)

    user = AllUsers.objects.filter(user_id=user_id).first()
    if not user:
        return Response({"status": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    profile_obj = UserProfile.objects.filter(user=user).first()
    badges_qs = UserBadges.objects.filter(user=user).select_related("badge")
    solved_count = UserProblemStatus.objects.filter(user=user, solved=True).count()
    quizzes_count = QuizAttempts.objects.filter(user=user, passed=True).count()
    enrollments_count = CourseEnrollments.objects.filter(user=user).count()

    return Response({
        "status": True,
        "user_id": user.user_id,
        "name": user.name,
        "xp": profile_obj.total_xp if profile_obj else 0,
        "streak": profile_obj.current_streak if profile_obj else 0,
        "problems_solved": solved_count,
        "quizzes_passed": quizzes_count,
        "courses_enrolled": enrollments_count,
        "badges": [b.badge.name for b in badges_qs],
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def mark_notifications_read(request):
    """
    Mark all unread notifications for a user as read.
    """
    user_id = request.data.get("user_id")
    if not user_id:
        return Response({"status": False, "message": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    updated_count = Notifications.objects.filter(user_id=user_id, read=False).update(read=True)
    return Response({
        "status": True,
        "message": f"{updated_count} notification(s) marked as read",
        "updated_count": updated_count
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def enroll_course(request):
    """
    Enrolls candidate in course.
    - Free course (price <= 0 or not is_paid): creates CourseEnrollments immediately.
    - Paid course (is_paid and price > 0): creates Razorpay Order with configured Razorpay account,
      returning order_id, key_id, amount_paise for checkout modal popup.
    """
    user_id = request.data.get("user_id")
    course_id = request.data.get("course_id")
    user = request.user if request.user and request.user.is_authenticated else None
    if not user and user_id:
        user = AllUsers.objects.filter(user_id=user_id).first()

    course = Courses.objects.filter(course_id=course_id, status="active").first() if course_id else None
    if not user:
        return Response({"status": False, "message": "Sign in before enrolling in a course."}, status=status.HTTP_401_UNAUTHORIZED)
    if not course:
        return Response({"status": False, "message": "Course not found or inactive"}, status=status.HTTP_404_NOT_FOUND)

    # Check existing enrollment
    existing = CourseEnrollments.objects.filter(user=user, course=course).first()
    if existing:
        return Response({
            "status": True,
            "requires_payment": False,
            "already_enrolled": True,
            "message": "You are already enrolled in this course.",
            "enrollment": CourseEnrollmentSerializer(existing).data
        }, status=status.HTTP_200_OK)

    is_paid = bool(course.is_paid and course.price > 0)
    if not is_paid:
        # Free course enrollment
        enrollment, created = CourseEnrollments.objects.get_or_create(
            user=user,
            course=course,
            defaults={"enrollment_id": f"enr_{uuid.uuid4().hex[:12]}", "progress_percent": 0, "is_completed": False},
        )
        return Response({
            "status": True,
            "requires_payment": False,
            "created": created,
            "message": "Enrolled in course successfully!",
            "enrollment": CourseEnrollmentSerializer(enrollment).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # Paid course enrollment -> Create Razorpay Order
    amount_paise = int(round(course.price * 100))
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret:
        return Response({
            "status": False,
            "message": "Razorpay payment gateway is not configured on the server."
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    import razorpay
    client = razorpay.Client(auth=(key_id, key_secret))
    receipt = f"crs_{uuid.uuid4().hex[:20]}"
    notes = {
        "user_id": str(user.user_id),
        "course_id": str(course.course_id),
        "course_name": str(course.name)[:40],
        "platform": "SkilTrix",
    }

    try:
        remote_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes,
        })
    except Exception as e:
        return Response({
            "status": False,
            "message": f"Could not create Razorpay order: {str(e)}"
        }, status=status.HTTP_502_BAD_GATEWAY)

    order = CoursePaymentOrder.objects.create(
        user=user,
        course=course,
        razorpay_order_id=remote_order["id"],
        amount_paise=amount_paise,
        currency="INR",
        status="pending",
    )

    return Response({
        "status": True,
        "requires_payment": True,
        "order_id": remote_order["id"],
        "amount_paise": amount_paise,
        "amount_rupees": course.price,
        "currency": "INR",
        "key_id": key_id,
        "course_name": course.name,
        "user_name": user.name or user.username,
        "user_email": user.email,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_enrollment_payment(request):
    """
    Verifies Razorpay payment signature for course enrollment.
    Upon successful HMAC-SHA256 signature verification, grants course enrollment access.
    """
    razorpay_order_id = request.data.get("razorpay_order_id")
    razorpay_payment_id = request.data.get("razorpay_payment_id")
    razorpay_signature = request.data.get("razorpay_signature")
    user_id = request.data.get("user_id")
    course_id = request.data.get("course_id")

    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return Response({
            "status": False,
            "message": "Missing Razorpay verification parameters (order_id, payment_id, signature required)."
        }, status=status.HTTP_400_BAD_REQUEST)

    user = request.user if request.user and request.user.is_authenticated else None
    if not user and user_id:
        user = AllUsers.objects.filter(user_id=user_id).first()

    course = Courses.objects.filter(course_id=course_id).first() if course_id else None

    order = CoursePaymentOrder.objects.filter(razorpay_order_id=razorpay_order_id).select_related("course", "user").first()
    if not order:
        return Response({
            "status": False,
            "message": "Payment order record not found for this Razorpay order."
        }, status=status.HTTP_404_NOT_FOUND)

    if not user:
        user = order.user
    if not course:
        course = order.course

    if order.status == "paid":
        enrollment = CourseEnrollments.objects.filter(user=user, course=course).first()
        return Response({
            "status": True,
            "message": "Payment already verified. Course enrollment is active.",
            "enrollment": CourseEnrollmentSerializer(enrollment).data if enrollment else None
        }, status=status.HTTP_200_OK)

    # Cryptographic HMAC-SHA256 verification
    key_secret = settings.RAZORPAY_KEY_SECRET
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    computed_sig = hmac.new(key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_sig, razorpay_signature):
        order.status = "failed"
        order.failure_reason = "Signature verification mismatch"
        order.save(update_fields=["status", "failure_reason"])
        return Response({
            "status": False,
            "message": "Invalid Razorpay payment signature. Payment verification failed."
        }, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    order.status = "paid"
    order.paid_at = now
    order.razorpay_payment_id = razorpay_payment_id
    order.razorpay_signature = razorpay_signature

    enrollment, _ = CourseEnrollments.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            "enrollment_id": f"enr_{uuid.uuid4().hex[:12]}",
            "progress_percent": 0,
            "is_completed": False,
            "enrolled_at": now
        }
    )
    order.enrollment = enrollment
    order.save(update_fields=["status", "paid_at", "razorpay_payment_id", "razorpay_signature", "enrollment"])

    return Response({
        "status": True,
        "message": f"Payment of ₹{order.amount_paise / 100:.2f} verified successfully! Enrolled in {course.name}.",
        "enrollment": CourseEnrollmentSerializer(enrollment).data,
        "order_id": order.razorpay_order_id,
        "payment_id": order.razorpay_payment_id,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def cancel_enrollment_payment(request):
    order_id = request.data.get("order_id") or request.data.get("razorpay_order_id")
    if not order_id:
        return Response({"status": False, "message": "order_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    order = CoursePaymentOrder.objects.filter(razorpay_order_id=order_id).first()
    if order and order.status == "pending":
        order.status = "cancelled"
        order.failure_reason = request.data.get("reason", "Checkout dismissed by candidate")
        order.save(update_fields=["status", "failure_reason"])
    return Response({"status": True, "message": "Order marked as cancelled"})


@api_view(["GET"])
@permission_classes([AllowAny])
def get_razorpay_config(request):
    return Response({
        "key_id": settings.RAZORPAY_KEY_ID,
        "currency": "INR",
        "name": "SkilTrix",
        "theme_color": "#4f46e5"
    })


# ==============================================================================
# 2.1 CODING ASSESSMENTS & REALISTIC SDE EVALUATION VIEWS
# ==============================================================================

class CodingAssessmentViewSet(viewsets.ModelViewSet):
    lookup_field = "assessment_id"

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {self.lookup_field: lookup_value}
        try:
            return queryset.get(**filter_kwargs)
        except (CodingAssessment.DoesNotExist, ValueError):
            if str(lookup_value).isdigit():
                try:
                    return queryset.get(pk=int(lookup_value))
                except CodingAssessment.DoesNotExist:
                    pass
            try:
                return queryset.get(slug=lookup_value)
            except CodingAssessment.DoesNotExist:
                pass
            raise Http404("Coding Assessment not found.")

    def get_queryset(self):
        if self.request.user.is_authenticated and (getattr(self.request.user, "is_staff", False) or getattr(self.request.user, "type", "") == "admin"):
            qs = CodingAssessment.objects.all().prefetch_related(
                "sections", "question_items__problem", "questions__problem"
            )
        else:
            qs = CodingAssessment.objects.all().prefetch_related(
                "sections", "question_items__problem", "questions__problem"
            )
        cat = self.request.query_params.get("category")
        if cat and cat != "All":
            qs = qs.filter(category=cat)
        tag = self.request.query_params.get("company_tag")
        if tag and tag != "All":
            qs = qs.filter(company_tag__icontains=tag)
        diff = self.request.query_params.get("difficulty")
        if diff and diff != "All":
            qs = qs.filter(difficulty=diff)
        pro = self.request.query_params.get("is_pro_only")
        if pro is not None:
            qs = qs.filter(is_pro_only=(pro.lower() == "true"))
        return qs

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update"]:
            return CodingAssessmentDetailSerializer
        return CodingAssessmentListSerializer

    @action(detail=True, methods=["get"])
    def questions(self, request, assessment_id=None):
        assessment = self.get_object()
        items = AssessmentQuestionItem.objects.filter(assessment=assessment).select_related("section", "problem")
        serializer = AssessmentQuestionItemFullSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_question(self, request, assessment_id=None):
        assessment = self.get_object()
        data = request.data
        section_id = data.get("section_id")
        section = None
        if section_id:
            section = AssessmentSection.objects.filter(models.Q(section_id=section_id) | models.Q(id=section_id), assessment=assessment).first()
        if not section:
            section = assessment.sections.first()

        item = AssessmentQuestionItem.objects.create(
            item_id=str(uuid.uuid4()),
            assessment=assessment,
            section=section,
            title=data.get("title", "Untitled Question"),
            slug=slugify(data.get("title", f"q-{uuid.uuid4().hex[:6]}"))[:250],
            question_type=data.get("question_type", "mcq_single"),
            category=data.get("category", assessment.category),
            difficulty=data.get("difficulty", assessment.difficulty),
            company_style=assessment.company_tag,
            marks=float(data.get("marks", 10.0)),
            negative_marks=float(data.get("negative_marks", 0.0)),
            prompt=data.get("prompt", ""),
            options=data.get("options", []),
            correct_answers=data.get("correct_answers", []),
            starter_code=data.get("starter_code", ""),
            reference_solution=data.get("reference_solution", ""),
            buggy_code=data.get("buggy_code", ""),
            error_message=data.get("error_message", ""),
            expected_behavior=data.get("expected_behavior", ""),
            expected_fix=data.get("expected_fix", ""),
            status="Published"
        )
        serializer = AssessmentQuestionItemFullSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AssessmentQuestionItemViewSet(viewsets.ModelViewSet):
    lookup_field = "item_id"
    queryset = AssessmentQuestionItem.objects.all().select_related("section", "problem")
    serializer_class = AssessmentQuestionItemFullSerializer

    def get_object(self):
        val = self.kwargs.get(self.lookup_field)
        try:
            return self.queryset.get(item_id=val)
        except AssessmentQuestionItem.DoesNotExist:
            if str(val).isdigit():
                try:
                    return self.queryset.get(pk=int(val))
                except AssessmentQuestionItem.DoesNotExist:
                    pass
            raise Http404("Question not found.")

    def get_queryset(self):
        qs = AssessmentQuestionItem.objects.all().select_related("section", "problem")
        asmt_id = self.request.query_params.get("assessment_id")
        if asmt_id:
            qs = qs.filter(models.Q(assessment__assessment_id=asmt_id) | models.Q(assessment__slug=asmt_id))
        return qs


class AssessmentSectionViewSet(viewsets.ModelViewSet):
    lookup_field = "section_id"
    queryset = AssessmentSection.objects.all()
    serializer_class = AssessmentSectionSerializer

    def get_queryset(self):
        qs = AssessmentSection.objects.all()
        asmt_id = self.request.query_params.get("assessment_id")
        if asmt_id:
            qs = qs.filter(models.Q(assessment__assessment_id=asmt_id) | models.Q(assessment__slug=asmt_id))
        return qs


class CompanyBlueprintViewSet(viewsets.ModelViewSet):
    lookup_field = "blueprint_id"
    queryset = CompanyBlueprint.objects.all()
    serializer_class = CompanyBlueprintSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def start_assessment(request):
    """
    Start or resume an assessment attempt. Enforces server-side timer & autosave state.
    """
    user_id = request.data.get("user_id")
    assessment_id = request.data.get("assessment_id")

    user = AllUsers.objects.filter(user_id=user_id).first()
    if not user and user_id:
        user, _ = AllUsers.objects.get_or_create(
            user_id=user_id,
            defaults={
                "username": f"user_{str(user_id)[:15]}",
                "email": f"{str(user_id)[:15]}@skiltrix.org",
                "name": "Assessment Candidate",
                "platform": "web",
                "platform_name": "skiltrix",
                "type": "student",
            }
        )

    assessment = CodingAssessment.objects.filter(assessment_id=assessment_id, active=True).prefetch_related(
        "sections", "question_items__problem", "questions__problem"
    ).first()

    if not user:
        return Response({"status": False, "message": "Valid user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not assessment:
        return Response({"status": False, "message": "Assessment not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    from datetime import timedelta
    import random

    now = timezone.now()
    # Check for active attempt
    attempt = AssessmentAttempt.objects.filter(
        user=user,
        assessment=assessment,
        status="in_progress"
    ).order_by("-started_at").first()

    if attempt:
        # Check if already expired
        if now >= attempt.expires_at:
            attempt.status = "timed_out"
            attempt.completed_at = attempt.expires_at
            attempt.save(update_fields=["status", "completed_at"])
            return Response({
                "status": False,
                "message": "Assessment has timed out.",
                "attempt": AssessmentAttemptSerializer(attempt).data,
                "is_expired": True
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Create new attempt
        expires_at = now + timedelta(minutes=assessment.duration_minutes)
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"

        assigned_q_ids = []
        # 1. First sample from configured question pools in sections
        for section in assessment.sections.all().order_by("order"):
            if section.question_pool and section.pool_question_count > 0:
                pool_questions = list(
                    section.question_pool.questions.filter(status="Published").values_list("item_id", flat=True)
                )
                sample_count = min(len(pool_questions), section.pool_question_count)
                if sample_count > 0:
                    sampled = random.sample(pool_questions, sample_count)
                    assigned_q_ids.extend(sampled)
            else:
                # Questions explicitly attached to this section
                sec_items = list(
                    assessment.question_items.filter(section=section, status="Published").values_list("item_id", flat=True)
                )
                if not sec_items:
                    sec_items = list(
                        assessment.question_items.filter(section_assignment=section.section_type, status="Published").values_list("item_id", flat=True)
                    )
                assigned_q_ids.extend(sec_items)

        # 2. Add published questions directly attached to assessment
        direct_items = list(
            assessment.question_items.filter(status="Published").values_list("item_id", flat=True)
        )
        for item_id in direct_items:
            if item_id not in assigned_q_ids:
                assigned_q_ids.append(item_id)

        # 3. Fallback to legacy assessment.questions if no question_items
        if not assigned_q_ids and assessment.questions.exists():
            assigned_q_ids = list(assessment.questions.values_list("problem__problem_id", flat=True))

        if assessment.randomize_questions:
            random.shuffle(assigned_q_ids)

        first_section_title = assessment.sections.first().title if assessment.sections.exists() else "Main Section"

        attempt = AssessmentAttempt.objects.create(
            attempt_id=attempt_id,
            user=user,
            assessment=assessment,
            status="in_progress",
            expires_at=expires_at,
            saved_drafts={},
            selected_answers={},
            assigned_question_ids=assigned_q_ids,
            current_section=first_section_title,
            current_question_index=0,
            integrity_score=100.0,
        )

    # Return assessment with questions and attempt metadata
    serializer_context = {
        "request": request,
        "attempt_id": attempt.attempt_id,
        "assigned_question_ids": attempt.assigned_question_ids
    }
    return Response({
        "status": True,
        "message": "Assessment session active",
        "attempt_id": attempt.attempt_id,
        "attempt": AssessmentAttemptSerializer(attempt).data,
        "assessment": CodingAssessmentDetailSerializer(assessment, context=serializer_context).data,
        "time_remaining_seconds": max(0, int((attempt.expires_at - now).total_seconds())),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def record_assessment_event(request):
    """
    Records browser integrity signals (TAB_SWITCH, FULLSCREEN_EXIT, SCREEN_SHARE_STOPPED, etc.)
    Updates neutral integrity metrics and enforces auto-submit policies without privacy violations.
    """
    attempt_id = request.data.get("attempt_id")
    event_type = request.data.get("event_type")
    metadata = request.data.get("metadata", {})

    attempt = AssessmentAttempt.objects.filter(attempt_id=attempt_id).select_related("assessment", "user").first()
    if not attempt:
        return Response({"status": False, "message": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)

    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    AssessmentEvent.objects.create(
        event_id=event_id,
        attempt=attempt,
        user=attempt.user,
        assessment=attempt.assessment,
        event_type=event_type,
        metadata=metadata if isinstance(metadata, dict) else {},
    )

    # Increment telemetry counters
    if event_type == "TAB_SWITCH":
        attempt.tab_switch_count += 1
    elif event_type == "FULLSCREEN_EXIT":
        attempt.fullscreen_exit_count += 1
    elif event_type == "SCREEN_SHARE_STOPPED":
        attempt.screen_share_stop_count += 1
    elif event_type == "NETWORK_DISCONNECT":
        attempt.network_disconnect_count += 1

    # Neutral integrity deduction: tab switch: -5, fullscreen exit: -8, screen share stop: -15
    deductions = (attempt.tab_switch_count * 5.0) + (attempt.fullscreen_exit_count * 8.0) + (attempt.screen_share_stop_count * 15.0)
    attempt.integrity_score = max(0.0, round(100.0 - deductions, 1))

    # Auto submit on violation limit if policy is configured
    assessment = attempt.assessment
    disqualified = False
    if assessment.auto_submit_on_violations and attempt.status == "in_progress":
        if (attempt.tab_switch_count > assessment.max_tab_switches or
            attempt.fullscreen_exit_count > assessment.max_fullscreen_exits):
            attempt.status = "disqualified"
            attempt.completed_at = timezone.now()
            disqualified = True

    attempt.save()

    return Response({
        "status": True,
        "event_id": event_id,
        "integrity_score": attempt.integrity_score,
        "tab_switch_count": attempt.tab_switch_count,
        "fullscreen_exit_count": attempt.fullscreen_exit_count,
        "screen_share_stop_count": attempt.screen_share_stop_count,
        "disqualified": disqualified,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def autosave_assessment_draft(request):
    """
    Periodically autosaves candidate responses (selected MCQ answers, code drafts, section).
    Throttled and safe against offline reconnects.
    """
    attempt_id = request.data.get("attempt_id")
    problem_id = request.data.get("problem_id")
    language = request.data.get("language", "python")
    code = request.data.get("code")
    selected_answers = request.data.get("selected_answers")
    current_section = request.data.get("current_section")
    current_question_index = request.data.get("current_question_index")

    attempt = AssessmentAttempt.objects.filter(attempt_id=attempt_id).first()
    if not attempt or attempt.status != "in_progress":
        return Response({"status": False, "message": "Active assessment attempt not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    if timezone.now() >= attempt.expires_at:
        attempt.status = "timed_out"
        attempt.save(update_fields=["status"])
        return Response({"status": False, "message": "Assessment duration has expired"}, status=status.HTTP_400_BAD_REQUEST)

    # Update code draft if problem_id passed
    if problem_id and code is not None:
        drafts = attempt.saved_drafts or {}
        drafts[problem_id] = {
            "language": language,
            "code": code,
            "saved_at": timezone.now().isoformat()
        }
        attempt.saved_drafts = drafts

    # Update selected answers for MCQ/Numerical items
    if isinstance(selected_answers, dict):
        answers = attempt.selected_answers or {}
        answers.update(selected_answers)
        attempt.selected_answers = answers

    if current_section is not None:
        attempt.current_section = current_section
    if current_question_index is not None:
        attempt.current_question_index = current_question_index

    attempt.save(update_fields=["saved_drafts", "selected_answers", "current_section", "current_question_index"])
    return Response({"status": True, "message": "Draft autosaved successfully"})


@api_view(["POST"])
@permission_classes([AllowAny])
def submit_assessment(request):
    """
    Final submission of an assessment. Evaluates both:
    1. Multi-section questions (MCQ, Multi-select, Numerical) with negative marking
    2. Coding, Debugging, SQL problems against full test suites
    Computes section breakdown, Amazon-style skill radar, and neutral integrity evaluation.
    """
    attempt_id = request.data.get("attempt_id")
    submissions_map = request.data.get("submissions", {})
    selected_answers_payload = request.data.get("selected_answers", {})

    attempt = AssessmentAttempt.objects.filter(attempt_id=attempt_id).select_related("assessment", "user").first()
    if not attempt:
        return Response({"status": False, "message": "Attempt not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    now = timezone.now()
    if attempt.status != "in_progress" and attempt.completed_at:
        return Response({
            "status": True,
            "message": "Assessment already submitted",
            "attempt": AssessmentAttemptSerializer(attempt).data
        })

    assessment = attempt.assessment

    # Merge answers
    combined_solutions = dict(attempt.saved_drafts or {})
    if isinstance(submissions_map, dict):
        for pid, data in submissions_map.items():
            combined_solutions[pid] = data

    all_selected_answers = dict(attempt.selected_answers or {})
    if isinstance(selected_answers_payload, dict):
        all_selected_answers.update(selected_answers_payload)

    total_marks_possible = 0.0
    total_marks_earned = 0.0

    section_scores = {}
    skill_totals = {
        "Problem Solving": {"earned": 0.0, "total": 0.0},
        "Data Structures": {"earned": 0.0, "total": 0.0},
        "Algorithms": {"earned": 0.0, "total": 0.0},
        "Debugging": {"earned": 0.0, "total": 0.0},
        "Backend": {"earned": 0.0, "total": 0.0},
        "Aptitude / Reasoning": {"earned": 0.0, "total": 0.0},
        "SQL & Databases": {"earned": 0.0, "total": 0.0},
    }

    per_problem_results = []
    from .codelab_evaluator import evaluate_test_cases, evaluate_assessment_question_item

    # 1. EVALUATE MULTI-SECTION QUESTION ITEMS (IF CONFIGURED)
    assigned_ids = attempt.assigned_question_ids or []
    if assigned_ids:
        raw_items = list(AssessmentQuestionItem.objects.filter(item_id__in=assigned_ids).select_related("section", "problem").prefetch_related("test_cases"))
        item_map = {it.item_id: it for it in raw_items}
        question_items = [item_map[qid] for qid in assigned_ids if qid in item_map]
    else:
        question_items = list(AssessmentQuestionItem.objects.filter(assessment=assessment).select_related("section", "problem").prefetch_related("test_cases"))

    if question_items:
        for item in question_items:
            sec_title = item.section.title if item.section else (item.section_assignment or "General Section")
            if sec_title not in section_scores:
                section_scores[sec_title] = {"earned": 0.0, "total": 0.0}

            total_marks_possible += item.marks
            section_scores[sec_title]["total"] += item.marks

            earned = 0.0
            verdict = "Incorrect"

            if item.question_type in ["mcq_single", "mcq_multi", "numerical", "output_prediction", "aptitude", "reasoning", "cs_fundamentals"]:
                ans = all_selected_answers.get(item.item_id) or all_selected_answers.get(str(item.pk))
                correct = item.correct_answers or []

                is_correct = False
                if item.question_type in ["mcq_single", "output_prediction", "aptitude", "reasoning", "cs_fundamentals"]:
                    chosen = ans[0] if isinstance(ans, list) and ans else ans
                    expected = correct[0] if correct else ""
                    is_correct = (str(chosen).strip().lower() == str(expected).strip().lower())
                elif item.question_type == "mcq_multi":
                    chosen_set = set(str(x).strip().lower() for x in (ans if isinstance(ans, list) else [ans]))
                    correct_set = set(str(x).strip().lower() for x in correct)
                    is_correct = (chosen_set == correct_set and len(chosen_set) > 0)
                elif item.question_type == "numerical":
                    chosen_val = str(ans[0] if isinstance(ans, list) and ans else ans or "").strip()
                    expected_val = str(correct[0] if correct else "").strip()
                    is_correct = (chosen_val == expected_val and chosen_val != "")

                if is_correct:
                    earned = item.marks
                    verdict = "Correct"
                else:
                    if ans is not None and ans != "" and ans != []:
                        penalty = item.negative_marks or (item.marks * assessment.negative_marking_percentage)
                        earned = - round(penalty, 2)
                        verdict = "Incorrect (Penalty Applied)"
                    else:
                        earned = 0.0
                        verdict = "Unattempted"

                skill_totals["Aptitude / Reasoning"]["earned"] += max(0.0, earned)
                skill_totals["Aptitude / Reasoning"]["total"] += item.marks

            elif item.question_type in ["coding", "debugging", "sql", "code_correction", "django_debugging", "backend_debugging"] or item.test_cases.exists() or item.problem:
                sol = combined_solutions.get(item.item_id) or combined_solutions.get(item.slug) or (combined_solutions.get(item.problem.problem_id) if item.problem else None) or {}
                lang = sol.get("language") or item.language or "python"
                code = sol.get("code") or ""

                if code.strip():
                    eval_res = evaluate_assessment_question_item(question_item=item, language=lang, code=code, is_sample_only=False)
                    pass_ratio = (eval_res["passed_count"] / eval_res["total_count"]) if eval_res["total_count"] > 0 else 0
                    earned = round(item.marks * pass_ratio, 2)
                    verdict = eval_res["verdict"]
                else:
                    earned = 0.0
                    verdict = "Not Attempted"
                    t_count = item.test_cases.count() or (item.problem.test_cases.count() if item.problem else 0)
                    eval_res = {"passed_count": 0, "total_count": t_count, "total_duration_ms": 0}

                # Skills
                if item.question_type in ["debugging", "django_debugging", "backend_debugging", "code_correction"] or "Debugging" in (item.category or ""):
                    skill_totals["Debugging"]["earned"] += earned
                    skill_totals["Debugging"]["total"] += item.marks
                    skill_totals["Backend"]["earned"] += earned
                    skill_totals["Backend"]["total"] += item.marks
                elif item.question_type == "sql" or "SQL" in (item.category or ""):
                    skill_totals["SQL & Databases"]["earned"] += earned
                    skill_totals["SQL & Databases"]["total"] += item.marks
                else:
                    skill_totals["Problem Solving"]["earned"] += earned
                    skill_totals["Problem Solving"]["total"] += item.marks
                    skill_totals["Data Structures"]["earned"] += earned
                    skill_totals["Data Structures"]["total"] += item.marks
                    skill_totals["Algorithms"]["earned"] += earned
                    skill_totals["Algorithms"]["total"] += item.marks

                prob_id = item.problem.problem_id if item.problem else item.item_id
                per_problem_results.append({
                    "problem_id": prob_id,
                    "title": item.title,
                    "difficulty": item.difficulty,
                    "category": item.category,
                    "question_type": item.question_type,
                    "marks_possible": item.marks,
                    "marks_earned": earned,
                    "verdict": verdict,
                    "passed_tests": eval_res.get("passed_count", 0),
                    "total_tests": eval_res.get("total_count", 0),
                    "duration_ms": eval_res.get("total_duration_ms", 0),
                    "expected_complexity": getattr(item, "expected_complexity", ""),
                    "explanation": item.explanation or (getattr(item.problem, "explanation", "") if item.problem else ""),
                    "solution_code": getattr(item.problem, "solution_code", "") if item.problem else "",
                })

            total_marks_earned += earned
            section_scores[sec_title]["earned"] += earned

    # 2. EVALUATE DIRECT ASSESSMENT QUESTIONS (FOR BACKWARD COMPATIBILITY & CODING ONLY)
    direct_questions = AssessmentQuestion.objects.filter(assessment=assessment).select_related("problem").order_by("order")
    if direct_questions.exists() and not question_items.exists():
        sec_title = "Coding Round"
        section_scores[sec_title] = {"earned": 0.0, "total": 0.0}

        for aq in direct_questions:
            prob = aq.problem
            marks = aq.marks
            total_marks_possible += marks
            section_scores[sec_title]["total"] += marks

            sol = combined_solutions.get(prob.problem_id, {})
            lang = sol.get("language") or "python"
            code = sol.get("code") or ""

            if code.strip():
                eval_res = evaluate_test_cases(problem=prob, language=lang, code=code, is_sample_only=False)
                pass_ratio = (eval_res["passed_count"] / eval_res["total_count"]) if eval_res["total_count"] > 0 else 0
                earned = round(marks * pass_ratio, 2)
                verdict = eval_res["verdict"]
            else:
                earned = 0.0
                verdict = "Not Attempted"
                eval_res = {"passed_count": 0, "total_count": prob.test_cases.count(), "total_duration_ms": 0}

            total_marks_earned += earned
            section_scores[sec_title]["earned"] += earned

            is_debug = (prob.question_type == "debugging" or "Debugging" in prob.category or "Backend" in prob.category)
            if is_debug:
                skill_totals["Debugging"]["earned"] += earned
                skill_totals["Debugging"]["total"] += marks
                skill_totals["Backend"]["earned"] += earned
                skill_totals["Backend"]["total"] += marks
            else:
                skill_totals["Problem Solving"]["earned"] += earned
                skill_totals["Problem Solving"]["total"] += marks
                skill_totals["Data Structures"]["earned"] += earned
                skill_totals["Data Structures"]["total"] += marks
                skill_totals["Algorithms"]["earned"] += earned
                skill_totals["Algorithms"]["total"] += marks

            per_problem_results.append({
                "problem_id": prob.problem_id,
                "title": prob.title,
                "difficulty": prob.difficulty,
                "category": prob.category,
                "question_type": prob.question_type,
                "marks_possible": marks,
                "marks_earned": earned,
                "verdict": verdict,
                "passed_tests": eval_res.get("passed_count", 0),
                "total_tests": eval_res.get("total_count", 0),
                "duration_ms": eval_res.get("total_duration_ms", 0),
                "expected_complexity": getattr(prob, "expected_complexity", ""),
                "explanation": getattr(prob, "explanation", "") or prob.description,
                "solution_code": getattr(prob, "solution_code", ""),
            })

    total_marks_earned = max(0.0, round(total_marks_earned, 2))
    percentage = round((total_marks_earned / total_marks_possible * 100), 1) if total_marks_possible > 0 else 0.0
    passed = percentage >= assessment.pass_percentage

    # Skill percentages
    final_skills = {}
    for sk, vals in skill_totals.items():
        if vals["total"] > 0:
            final_skills[sk] = round((vals["earned"] / vals["total"]) * 100, 1)

    # Format section scores
    clean_section_scores = {}
    for sec_name, vals in section_scores.items():
        pct = round((vals["earned"] / vals["total"] * 100), 1) if vals["total"] > 0 else 0.0
        clean_section_scores[sec_name] = {
            "earned": max(0.0, round(vals["earned"], 2)),
            "total": vals["total"],
            "percentage": pct
        }

    # Integrity neutral label
    integrity_status = "Good"
    if attempt.integrity_score < 75.0:
        integrity_status = "Needs Review"
    elif attempt.integrity_score < 90.0:
        integrity_status = "Acceptable"

    attempt.status = "completed"
    attempt.completed_at = now
    attempt.total_score = total_marks_earned
    attempt.max_possible_score = total_marks_possible
    attempt.percentage = percentage
    attempt.passed = passed
    attempt.skill_breakdown = final_skills
    attempt.section_scores = clean_section_scores
    attempt.selected_answers = all_selected_answers
    attempt.save()

    return Response({
        "status": True,
        "message": "Assessment submitted and scored successfully",
        "attempt": AssessmentAttemptSerializer(attempt).data,
        "score_summary": {
            "total_score": total_marks_earned,
            "max_possible": total_marks_possible,
            "percentage": percentage,
            "passed": passed,
            "pass_percentage": assessment.pass_percentage,
            "skill_breakdown": final_skills,
            "section_scores": clean_section_scores,
            "integrity_score": attempt.integrity_score,
            "integrity_status": integrity_status,
            "tab_switches": attempt.tab_switch_count,
            "fullscreen_exits": attempt.fullscreen_exit_count,
            "screenshare_stops": attempt.screen_share_stop_count,
        },
        "problem_evaluations": per_problem_results,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def admin_assessment_monitoring(request):
    """
    Live admin monitoring of candidate attempts, integrity telemetry, and proctoring events.
    Does NOT show or record private user screens.
    """
    attempts = AssessmentAttempt.objects.select_related("user", "assessment").order_by("-started_at")[:50]
    data = []
    from django.utils import timezone
    now = timezone.now()
    for att in attempts:
        time_elapsed_secs = int((now - att.started_at).total_seconds()) if att.started_at else 0
        data.append({
            "attempt_id": att.attempt_id,
            "candidate_name": att.user.name or att.user.username,
            "candidate_username": att.user.username,
            "assessment_title": att.assessment.title,
            "company_tag": att.assessment.company_tag,
            "status": att.status,
            "integrity_score": att.integrity_score,
            "tab_switches": att.tab_switch_count,
            "fullscreen_exits": att.fullscreen_exit_count,
            "screenshare_stops": att.screen_share_stop_count,
            "current_section": att.current_section,
            "percentage": att.percentage,
            "passed": att.passed,
            "started_at": att.started_at,
            "expires_at": att.expires_at,
            "completed_at": att.completed_at,
            "time_elapsed_secs": time_elapsed_secs,
        })
    recent_events = AssessmentEvent.objects.select_related("user", "assessment").order_by("-timestamp")[:30]
    events_data = AssessmentEventSerializer(recent_events, many=True).data

    return Response({
        "status": True,
        "attempts": data,
        "recent_events": events_data,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def company_preparation_stats(request):
    """
    Placement Preparation dashboard cards for top company mock patterns:
    Amazon-style, Deloitte-style, Accenture-style, TCS-style, Infosys-style, Cognizant-style, etc.
    """
    user_id = request.query_params.get("user_id")

    company_patterns = [
        {"tag": "Amazon-style", "name": "Amazon-style SDE Mock", "slug": "amazon-style-sde", "tier": "free", "topics": ["Graphs", "Dynamic Programming", "Min-Heap", "System Debugging"]},
        {"tag": "Deloitte-style", "name": "Deloitte-style Placement Mock", "slug": "deloitte-style-placement", "tier": "free", "topics": ["Quantitative Aptitude", "Logical Reasoning", "SQL Queries", "Coding"]},
        {"tag": "Accenture-style", "name": "Accenture-style Coding Mock", "slug": "accenture-style-coding", "tier": "free", "topics": ["Critical Reasoning", "Abstract Thinking", "Core Coding", "Debugging"]},
        {"tag": "Cognizant-style", "name": "Cognizant-style Placement Mock", "slug": "cognizant-style-placement", "tier": "pro", "topics": ["Verbal Ability", "Data Interpretation", "CS Basics", "Coding"]},
        {"tag": "Infosys-style", "name": "Infosys-style Placement Mock", "slug": "infosys-style-placement", "tier": "pro", "topics": ["Mathematical Abilities", "Pseudocode", "DSA", "Problem Solving"]},
        {"tag": "TCS-style", "name": "TCS-style Placement Mock", "slug": "tcs-style-placement", "tier": "free", "topics": ["Numerical Ability", "Reasoning Ability", "Hands-on Coding", "SQL"]},
        {"tag": "Wipro-style", "name": "Wipro-style Placement Mock", "slug": "wipro-style-placement", "tier": "pro", "topics": ["Quantitative", "Logical", "Basic Programming", "Essay/Comprehension"]},
        {"tag": "Capgemini-style", "name": "Capgemini-style Placement Mock", "slug": "capgemini-style-placement", "tier": "pro", "topics": ["Pseudocode", "English Communication", "Game-Based Aptitude", "Coding"]},
        {"tag": "Microsoft-style", "name": "Microsoft-style Placement Mock", "slug": "microsoft-style-placement", "tier": "pro", "topics": ["Trees & Graphs", "Intervals", "Concurrency", "High-Scale SQL"]},
        {"tag": "Google-style", "name": "Google-style Placement Mock", "slug": "google-style-placement", "tier": "pro", "topics": ["Advanced Dynamic Programming", "Combinatorics", "Graph Theory", "Optimization"]},
        {"tag": "General SDE", "name": "General SDE Assessment", "slug": "general-sde-assessment", "tier": "free", "topics": ["Arrays & Strings", "Hash Maps", "Two Pointers", "Backend Debugging"]},
    ]

    cards = []
    for pattern in company_patterns:
        qs = AssessmentAttempt.objects.filter(assessment__company_tag__icontains=pattern["tag"])
        if user_id:
            user_qs = qs.filter(user__user_id=user_id)
        else:
            user_qs = qs.none()

        attempts_count = user_qs.count()
        completed = user_qs.filter(status="completed")
        best_score = completed.order_by("-percentage").values_list("percentage", flat=True).first() if completed.exists() else None
        avg_score = round(sum(completed.values_list("percentage", flat=True)) / completed.count(), 1) if completed.exists() else None
        last_attempt = user_qs.order_by("-started_at").values_list("started_at", flat=True).first() if user_qs.exists() else None

        asmt = CodingAssessment.objects.filter(company_tag__icontains=pattern["tag"], active=True).first()

        cards.append({
            "tag": pattern["tag"],
            "name": pattern["name"],
            "slug": pattern["slug"],
            "tier": pattern["tier"],
            "assessment_id": asmt.assessment_id if asmt else f"asmt_{pattern['slug'].replace('-', '_')}",
            "recommended_topics": pattern["topics"],
            "attempts": attempts_count,
            "best_score": best_score,
            "average_score": avg_score,
            "last_attempt": last_attempt,
        })

    return Response({
        "status": True,
        "company_mocks": cards,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def get_problem_explanation(request, problem_id):
    """
    Returns official educational solution & explanation only AFTER student submission
    or for solved questions, preventing test cheating.
    """
    user_id = request.query_params.get("user_id")
    problem = CodingProblems.objects.filter(problem_id=problem_id).first()
    if not problem:
        return Response({"status": False, "message": "Problem not found"}, status=status.HTTP_404_NOT_FOUND)

    # Security check: Must have at least 1 evaluated submission
    has_attempted = False
    if user_id:
        has_attempted = CodeSubmissions.objects.filter(user_id=user_id, problem=problem).exists()

    if not has_attempted:
        return Response({
            "status": False,
            "message": "Official explanations and reference solutions unlock after your first submission attempt."
        }, status=status.HTTP_403_FORBIDDEN)

    return Response({
        "status": True,
        "problem_id": problem.problem_id,
        "title": problem.title,
        "expected_complexity": getattr(problem, "expected_complexity", ""),
        "explanation": getattr(problem, "explanation", "") or problem.description,
        "solution_code": getattr(problem, "solution_code", ""),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def upload_cdn_asset(request):
    """
    Direct upload endpoint for media files to Cloudflare R2 / CDN.
    Supported types:
    - 'st_image' -> st/images/
    - 'st_pdf'   -> st/pdfs/
    - 'st_video' -> st/videos/
    - 'sfs_image' -> sfs/images/
    - 'sfs_zip'  -> sfs/zipfiles/
    """
    file_obj = request.FILES.get("file")
    asset_type = request.data.get("type", "st_image")

    if not file_obj:
        return Response({"status": False, "message": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    from apis.cdn_utils import (
        upload_st_image, upload_st_pdf, upload_st_video,
        upload_sfs_image, upload_sfs_zip
    )

    try:
        if asset_type in ("st_image", "image"):
            filename, url = upload_st_image(file_obj)
        elif asset_type in ("st_pdf", "pdf", "resume"):
            filename, url = upload_st_pdf(file_obj)
        elif asset_type in ("st_video", "video"):
            filename, url = upload_st_video(file_obj)
        elif asset_type in ("sfs_image",):
            filename, url = upload_sfs_image(file_obj)
        elif asset_type in ("sfs_zip", "zip"):
            filename, url = upload_sfs_zip(file_obj)
        else:
            filename, url = upload_st_image(file_obj)

        return Response({
            "status": True,
            "message": "File uploaded successfully to CDN",
            "filename": filename,
            "url": url,
            "type": asset_type
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            "status": False,
            "message": f"CDN upload failed: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

