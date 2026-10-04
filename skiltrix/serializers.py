from rest_framework import serializers
from .models import (
    Companies, Internship, Courses, Videos, Comments, Ratings, Language,
    CourseCategories, Resumes, Skills, Education, Code, Likes,
    UserProfile, Badges, UserBadges, DailyActivity,
    CodingProblems, TestCases, CodeSubmissions, UserProblemStatus,
    CompilerSnippets, SyntaxMatrix,
    Quizzes, QuizQuestions, QuizOptions, QuizAttempts, QuizUserAnswers,
    InterviewCategories, InterviewQuestions, CompanyRoadmaps, MockInterviewSessions,
    Discussions, DiscussionReplies, DiscussionLikes, DiscussionBookmarks,
    CourseModules, CourseLessons, CourseEnrollments,
    VideoSubtitles, VideoProgress, VideoNotes,
    InternshipApplications, SavedInternships, Notifications
)
from sfs.models import AllUsers


# ==============================================================================
# 1. USER & PROFILE SERIALIZERS
# ==============================================================================

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AllUsers
        fields = ["user_id", "username", "name", "lastname", "email", "profile"]


class BadgesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badges
        fields = "__all__"


class UserBadgesSerializer(serializers.ModelSerializer):
    badge = BadgesSerializer(read_only=True)

    class Meta:
        model = UserBadges
        fields = ["user_badge_id", "badge", "earned_at"]


class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = ["activity_id", "date", "minutes_spent", "problems_solved", "quizzes_completed", "xp_earned"]


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    earned_badges = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def get_earned_badges(self, obj):
        user_badges = UserBadges.objects.filter(user=obj.user).select_related("badge")
        return [ub.badge.name for ub in user_badges]


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resumes
        fields = "__all__"


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skills
        fields = "__all__"


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = "__all__"


# ==============================================================================
# 2. CODING & PRACTICE SERIALIZERS
# ==============================================================================

class TestCasePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCases
        fields = ["test_case_id", "input_data", "expected_output", "is_sample", "points", "order"]


class CodingProblemListSerializer(serializers.ModelSerializer):
    is_solved = serializers.SerializerMethodField()

    class Meta:
        model = CodingProblems
        fields = [
            "problem_id", "title", "slug", "difficulty", "topics",
            "acceptance_rate", "points", "solved_count", "total_attempts",
            "is_solved"
        ]

    def get_is_solved(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            return UserProblemStatus.objects.filter(user=request.user, problem=obj, solved=True).exists()
        user_id = request.query_params.get("user_id") if request else None
        if user_id:
            return UserProblemStatus.objects.filter(user_id=user_id, problem=obj, solved=True).exists()
        return False


class CodingProblemDetailSerializer(serializers.ModelSerializer):
    sample_test_cases = serializers.SerializerMethodField()
    starter_codes = serializers.SerializerMethodField()

    class Meta:
        model = CodingProblems
        fields = [
            "problem_id", "title", "slug", "difficulty", "topics",
            "acceptance_rate", "points", "description", "input_format",
            "output_format", "constraints", "starter_codes",
            "hints", "sample_test_cases", "created_at"
        ]

    def get_sample_test_cases(self, obj):
        samples = obj.test_cases.filter(is_sample=True).order_by("order")
        return TestCasePublicSerializer(samples, many=True).data

    def get_starter_codes(self, obj):
        return {
            "python": obj.starter_python,
            "java": obj.starter_java,
            "cpp": obj.starter_cpp,
            "c": obj.starter_c,
            "javascript": obj.starter_javascript,
        }


class CodeSubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.name")
    problem_title = serializers.ReadOnlyField(source="problem.title")

    class Meta:
        model = CodeSubmissions
        fields = [
            "submission_id", "user", "user_name", "problem", "problem_title",
            "language", "code", "status", "passed_test_cases", "total_test_cases",
            "execution_time_ms", "memory_kb", "error_message", "score", "created_at"
        ]
        read_only_fields = ["passed_test_cases", "total_test_cases", "execution_time_ms", "memory_kb", "error_message"]
        extra_kwargs = {
            "status": {"required": False},
            "score": {"required": False},
            "code": {"required": False},
            "language": {"required": False},
            "problem": {"required": False},
            "user": {"required": False},
        }


class CompilerSnippetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompilerSnippets
        fields = "__all__"


class SyntaxMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyntaxMatrix
        fields = "__all__"


# ==============================================================================
# 3. QUIZZES SERIALIZERS
# ==============================================================================

class QuizOptionPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOptions
        fields = ["option_id", "option_text", "order"]


class QuizQuestionPublicSerializer(serializers.ModelSerializer):
    options = QuizOptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestions
        fields = ["question_id", "question_text", "code_snippet", "language", "points", "order", "options"]


class QuizListSerializer(serializers.ModelSerializer):
    best_score = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()

    class Meta:
        model = Quizzes
        fields = [
            "quiz_id", "title", "slug", "topic", "difficulty",
            "duration_minutes", "passing_score", "total_questions", "points", "icon", "best_score", "attempts"
        ]

    def _attempts(self, obj):
        request = self.context.get("request")
        user_id = request.query_params.get("user_id") if request else None
        if not user_id:
            return QuizAttempts.objects.none()
        return QuizAttempts.objects.filter(user_id=user_id, quiz=obj)

    def get_best_score(self, obj):
        return self._attempts(obj).order_by("-percentage").values_list("percentage", flat=True).first() or 0

    def get_attempts(self, obj):
        return self._attempts(obj).count()


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuizQuestionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Quizzes
        fields = [
            "quiz_id", "title", "slug", "topic", "difficulty",
            "duration_minutes", "passing_score", "total_questions", "points", "icon", "questions"
        ]


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.ReadOnlyField(source="quiz.title")

    class Meta:
        model = QuizAttempts
        fields = [
            "attempt_id", "user", "quiz", "quiz_title", "score", "total_questions",
            "correct_count", "incorrect_count", "percentage", "passed", "time_taken_seconds", "created_at"
        ]


# ==============================================================================
# 4. INTERVIEW PREPARATION SERIALIZERS
# ==============================================================================

class InterviewCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewCategories
        fields = "__all__"


class InterviewQuestionSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source="category.name")

    class Meta:
        model = InterviewQuestions
        fields = [
            "interview_id", "category", "category_name", "topic", "difficulty",
            "question", "short_answer", "explanation", "code", "language",
            "tags", "frequent_companies", "created_at"
        ]


class CompanyRoadmapSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source="company.name")

    class Meta:
        model = CompanyRoadmaps
        fields = ["roadmap_id", "company", "company_name", "step_number", "title", "description", "category"]


# ==============================================================================
# 5. COMMUNITY & DISCUSSION SERIALIZERS
# ==============================================================================

class DiscussionReplySerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = DiscussionReplies
        fields = ["reply_id", "discussion", "user", "content", "code", "likes_count", "is_accepted", "created_at"]


class DiscussionListSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    author_name = serializers.ReadOnlyField(source="user.name")
    author_profile = serializers.ReadOnlyField(source="user.profile")

    class Meta:
        model = Discussions
        fields = [
            "discussion_id", "user", "author_name", "author_profile", "title", "content", "code", "language", "tag", "likes_count",
            "comments_count", "is_solved", "is_pinned", "created_at"
        ]


class DiscussionDetailSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    author_name = serializers.ReadOnlyField(source="user.name")
    author_profile = serializers.ReadOnlyField(source="user.profile")
    replies = DiscussionReplySerializer(many=True, read_only=True)

    class Meta:
        model = Discussions
        fields = [
            "discussion_id", "user", "author_name", "author_profile", "title", "content", "code", "language",
            "tag", "likes_count", "comments_count", "is_solved", "is_pinned",
            "created_at", "replies"
        ]


# ==============================================================================
# 6. COURSES & MEDIA SERIALIZERS
# ==============================================================================

class CourseLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLessons
        fields = ["lesson_id", "title", "lesson_type", "duration_minutes", "is_free_preview", "order"]


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModules
        fields = ["module_id", "title", "description", "order", "lessons"]


class VideoSubtitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoSubtitles
        fields = ["subtitle_id", "language_code", "label", "vtt_url"]


class VideoDetailSerializer(serializers.ModelSerializer):
    subtitles = VideoSubtitleSerializer(many=True, read_only=True)
    course_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    course_name = serializers.ReadOnlyField(source="course.name")

    class Meta:
        model = Videos
        fields = [
            "video_id", "title", "description", "video", "image",
            "like", "share", "views", "course", "course_id", "course_name", "subtitles", "created_at"
        ]
        extra_kwargs = {
            "video_id": {"required": False},
            "video": {"required": False, "allow_blank": True},
            "image": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True},
            "course": {"required": False, "allow_null": True}
        }


class CourseDetailSerializer(serializers.ModelSerializer):
    modules = CourseModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Courses
        fields = [
            "course_id", "name", "image", "type", "is_paid", "price",
            "status", "created_at", "modules"
        ]
        extra_kwargs = {
            "course_id": {"required": False},
            "image": {"required": False, "allow_blank": True},
            "price": {"required": False}
        }


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseDetailSerializer(read_only=True)
    course_name = serializers.ReadOnlyField(source="course.name")

    class Meta:
        model = CourseEnrollments
        fields = ["enrollment_id", "user", "course", "course_name", "progress_percent", "is_completed", "enrolled_at", "completed_at"]


# ==============================================================================
# 7. INTERNSHIPS & COMPANIES SERIALIZERS
# ==============================================================================

class CompanySerializer(serializers.ModelSerializer):
    roadmaps = CompanyRoadmapSerializer(many=True, read_only=True)

    class Meta:
        model = Companies
        fields = ["company_id", "name", "image", "description", "status", "roadmaps", "created_at"]
        extra_kwargs = {
            "company_id": {"required": False},
            "image": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True}
        }


class InternshipSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    company_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Internship
        fields = [
            "internship_id", "name", "company", "company_id", "is_paid", "type",
            "location", "deadline", "price", "apply_link", "status", "created_at"
        ]
        extra_kwargs = {
            "internship_id": {"required": False},
            "location": {"required": False, "allow_blank": True},
            "deadline": {"required": False, "allow_blank": True},
            "apply_link": {"required": False, "allow_null": True, "allow_blank": True}
        }


class InternshipApplicationSerializer(serializers.ModelSerializer):
    internship_title = serializers.ReadOnlyField(source="internship.name")
    company_name = serializers.ReadOnlyField(source="internship.company.name")

    class Meta:
        model = InternshipApplications
        fields = [
            "application_id", "internship", "internship_title", "company_name",
            "user", "resume", "cover_letter", "portfolio_url", "status", "applied_at"
        ]


# ==============================================================================
# 8. NOTIFICATIONS SERIALIZER
# ==============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = ["notification_id", "user", "title", "body", "category", "icon", "read", "action_url", "created_at"]


# Serializers used by the SkilTrix API viewsets.
TestCaseSerializer = TestCasePublicSerializer
CourseSerializer = CourseDetailSerializer
VideoSerializer = VideoDetailSerializer


class UserProblemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProblemStatus
        fields = "__all__"


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = "__all__"


class VideoNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoNotes
        fields = "__all__"


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["language_id", "name", "status"]
        extra_kwargs = {
            "language_id": {"required": False}
        }


class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        fields = "__all__"


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.name")

    class Meta:
        model = Comments
        fields = ["id", "comment", "video", "user", "user_name"]


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ratings
        fields = "__all__"


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Likes
        fields = "__all__"


class DiscussionLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionLikes
        fields = "__all__"


class DiscussionBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionBookmarks
        fields = "__all__"


class SavedInternshipSerializer(serializers.ModelSerializer):
    internship = InternshipSerializer(read_only=True)

    class Meta:
        model = SavedInternships
        fields = ["saved_id", "user", "internship", "created_at"]
