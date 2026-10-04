import uuid
import requests
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import logout as auth_logout
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
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
    VideoSubtitles,
    VideoProgress,
    VideoNotes,
    InternshipApplications,
    SavedInternships,
    Notifications,
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
    video_list = Videos.objects.filter(status="active").values()
    data.update({"videos": list(video_list)})
    return JsonResponse(data, safe=False)


def profile_resumes(request):
    user_id = request.GET.get('user_id', '')
    data = {
        "status": True,
        "message": "success",
        "action": "retrieved"
    }
    if user_id:
        resumes_qs = Resumes.objects.filter(status="active", user_id=user_id)
        data.update({"resumes": list(resumes_qs.values())})
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
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty)
        if topic:
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
        user = AllUsers.objects.filter(user_id=user_id).first() if user_id else None
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

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id") or self.kwargs.get("user__user_id")
        if user_id:
            return UserProfile.objects.filter(user__user_id=user_id).select_related("user")
        return UserProfile.objects.none()

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
    user_id = request.data.get("user_id")
    course_id = request.data.get("course_id")
    user = AllUsers.objects.filter(user_id=user_id).first() if user_id else None
    course = Courses.objects.filter(course_id=course_id, status="active").first() if course_id else None
    if not user or not course:
        return Response({"status": False, "message": "Valid user_id and course_id are required"}, status=status.HTTP_400_BAD_REQUEST)
    enrollment, created = CourseEnrollments.objects.get_or_create(
        user=user,
        course=course,
        defaults={"enrollment_id": f"enr_{uuid.uuid4().hex[:12]}", "progress_percent": 0, "is_completed": False},
    )
    return Response({"status": True, "created": created, "enrollment": CourseEnrollmentSerializer(enrollment).data}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
