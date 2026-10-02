from rest_framework import serializers
from shared_lib.sfs_core.models import AllUsers
from .models import (
    Companies, Company,
    Internship, InternshipProgram, InternshipStep, InternshipProgress, InternshipStepProgress,
    Courses, Course, CourseTopic, CourseModule, CourseLesson, Lesson, CourseEnrollment, LessonProgress,
    Videos, Video, VideoLike, VideoComment, VideoCommentLike, VideoBookmark, VideoSubtitle, VideoNote,
    Comments, Comment,
    Ratings, Rating, CourseReview,
    Language, ProgrammingLanguage, Technology,
    CourseCategories, CourseCategory,
    Resumes, Resume,
    Skills, Skill,
    Education,
    Code, SavedCode,
    Likes,
    UserProfile,
    Badges, Badge,
    UserBadges, UserBadge,
    DailyActivity, DailyContribution, UserActivity,
    CodingProblems, CodingProblem, CompanyProblem,
    TestCases, TestCase, ProblemTestCase,
    CodeSubmissions, CodeSubmission, ProblemSubmission,
    UserProblemStatus, ProblemProgress,
    CompilerSnippets, CodeExecution,
    SyntaxMatrix,
    Quizzes, Quiz,
    QuizQuestions, QuizQuestion,
    QuizOptions, QuizOption,
    QuizAttempts, QuizAttempt,
    QuizUserAnswers, QuizAnswer,
    InterviewCategories, InterviewCategory,
    InterviewQuestions, InterviewQuestion, InterviewQuestionBookmark,
    CompanyRoadmaps,
    MockInterviewSessions,
    Discussions, Discussion, DiscussionPost,
    DiscussionReplies, DiscussionReply, DiscussionComment,
    DiscussionLikes, DiscussionLike, DiscussionPostLike, DiscussionCommentLike,
    DiscussionBookmarks, DiscussionBookmark,
    CourseModules,
    CourseLessons,
    CourseEnrollments,
    VideoSubtitles,
    VideoProgress,
    VideoNotes,
    InternshipApplications, InternshipApplication,
    SavedInternships, SavedInternship,
    Notifications, Notification,
    LearningPath,
    LessonCodeExample,
    CodingTopic,
    ProblemExample,
    DiscussionTag,
    UserFollow,
    UserGoal,
    CourseBookmark,
    ProblemBookmark,
    SearchHistory,
    InformationPage,
)


# ==============================================================================
# 1. USER & PROFILE
# ==============================================================================

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AllUsers
        fields = ["id", "user_id", "username", "name", "lastname", "email", "profile", "user_type"]


UserSerializer = UserSummarySerializer


class BadgesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badges
        fields = "__all__"


BadgeSerializer = BadgesSerializer


class UserBadgesSerializer(serializers.ModelSerializer):
    badge = BadgesSerializer(read_only=True)

    class Meta:
        model = UserBadges
        fields = ["user_badge_id", "badge", "earned_at"]


UserBadgeSerializer = UserBadgesSerializer


class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = ["activity_id", "date", "minutes_spent", "problems_solved", "quizzes_completed", "xp_earned"]


DailyContributionSerializer = DailyActivitySerializer
UserActivitySerializer = DailyActivitySerializer


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    earned_badges = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def get_earned_badges(self, obj):
        try:
            user_badges = UserBadges.objects.filter(user=obj.user).select_related("badge")
            return [ub.badge.name for ub in user_badges]
        except Exception:
            return []


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


class UserFollowSerializer(serializers.ModelSerializer):
    follower = UserSummarySerializer(read_only=True)
    following = UserSummarySerializer(read_only=True)

    class Meta:
        model = UserFollow
        fields = "__all__"


class UserGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoal
        fields = "__all__"


# ==============================================================================
# 2. CODING & COMPILER
# ==============================================================================

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCases
        fields = ["test_case_id", "input_data", "expected_output", "is_sample", "is_hidden", "points", "order"]


ProblemTestCaseSerializer = TestCaseSerializer


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
        if request and hasattr(request, "user") and request.user.is_authenticated:
            return UserProblemStatus.objects.filter(user=request.user, problem=obj, solved=True).exists()
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
        return TestCaseSerializer(samples, many=True).data

    def get_starter_codes(self, obj):
        return {
            "python": obj.starter_python,
            "java": obj.starter_java,
            "cpp": obj.starter_cpp,
            "c": obj.starter_c,
            "javascript": obj.starter_javascript,
        }


CodingProblemSerializer = CodingProblemDetailSerializer
CompanyProblemSerializer = CodingProblemListSerializer


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
        read_only_fields = [
            "status", "passed_test_cases", "total_test_cases",
            "execution_time_ms", "memory_kb", "error_message", "score"
        ]


ProblemSubmissionSerializer = CodeSubmissionSerializer


class UserProblemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProblemStatus
        fields = "__all__"


ProblemProgressSerializer = UserProblemStatusSerializer


class CompilerSnippetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompilerSnippets
        fields = "__all__"


CodeExecutionSerializer = CompilerSnippetSerializer


class SyntaxMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyntaxMatrix
        fields = "__all__"


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = "__all__"


TechnologySerializer = LanguageSerializer
ProgrammingLanguageSerializer = LanguageSerializer


class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        fields = "__all__"


SavedCodeSerializer = CodeSerializer


class CodingTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingTopic
        fields = "__all__"


class ProblemExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemExample
        fields = "__all__"


class ProblemBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemBookmark
        fields = "__all__"


# ==============================================================================
# 3. QUIZZES
# ==============================================================================

class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOptions
        fields = ["option_id", "option_text", "order"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestions
        fields = ["question_id", "question_text", "code_snippet", "language", "points", "order", "options"]


class QuizListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quizzes
        fields = [
            "quiz_id", "title", "slug", "topic", "difficulty",
            "duration_minutes", "passing_score", "total_questions", "points", "icon"
        ]


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quizzes
        fields = [
            "quiz_id", "title", "slug", "topic", "difficulty",
            "duration_minutes", "passing_score", "total_questions",
            "points", "icon", "questions"
        ]


QuizSerializer = QuizDetailSerializer


class QuizUserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizUserAnswers
        fields = "__all__"


QuizAnswerSerializer = QuizUserAnswerSerializer


class QuizAttemptSerializer(serializers.ModelSerializer):
    user_answers = QuizUserAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempts
        fields = [
            "attempt_id", "user", "quiz", "score", "total_questions",
            "correct_count", "incorrect_count", "percentage", "passed",
            "time_taken_seconds", "user_answers", "created_at"
        ]


# ==============================================================================
# 4. INTERVIEW
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
            "interview_id", "category", "category_name", "topic",
            "difficulty", "question", "short_answer", "explanation",
            "code", "language", "tags", "frequent_companies", "status"
        ]


class InterviewQuestionBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestionBookmark
        fields = "__all__"


class CompanyRoadmapSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyRoadmaps
        fields = "__all__"


InternshipStepSerializer = CompanyRoadmapSerializer


class MockInterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockInterviewSessions
        fields = "__all__"


# ==============================================================================
# 5. COMPANIES & INTERNSHIPS
# ==============================================================================

class CompanySerializer(serializers.ModelSerializer):
    roadmaps = CompanyRoadmapSerializer(many=True, read_only=True)

    class Meta:
        model = Companies
        fields = ["company_id", "name", "image", "description", "status", "roadmaps", "created_at"]


class InternshipSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source="company.name")
    company_image = serializers.ReadOnlyField(source="company.image")

    class Meta:
        model = Internship
        fields = [
            "internship_id", "name", "company", "company_name", "company_image",
            "is_paid", "type", "location", "deadline", "price", "apply_link",
            "status", "created_at"
        ]


InternshipProgramSerializer = InternshipSerializer


class InternshipApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.name")
    internship_name = serializers.ReadOnlyField(source="internship.name")

    class Meta:
        model = InternshipApplications
        fields = [
            "application_id", "internship", "internship_name", "user",
            "user_name", "resume", "cover_letter", "portfolio_url",
            "status", "applied_at"
        ]


InternshipProgressSerializer = InternshipApplicationSerializer
InternshipStepProgressSerializer = InternshipApplicationSerializer


class SavedInternshipSerializer(serializers.ModelSerializer):
    internship = InternshipSerializer(read_only=True)

    class Meta:
        model = SavedInternships
        fields = ["saved_id", "user", "internship", "created_at"]


# ==============================================================================
# 6. COURSES, MODULES & LESSONS
# ==============================================================================

class CourseLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLessons
        fields = "__all__"


LessonSerializer = CourseLessonSerializer


class LessonCodeExampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonCodeExample
        fields = "__all__"


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = CourseLessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModules
        fields = ["module_id", "course", "title", "description", "order", "lessons"]


class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategories
        fields = "__all__"


CourseTopicSerializer = CourseCategorySerializer


class LearningPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPath
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    modules = CourseModuleSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source="user.name")

    class Meta:
        model = Courses
        fields = [
            "course_id", "name", "image", "type", "is_paid", "price",
            "user", "instructor_name", "status", "modules", "created_at"
        ]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseEnrollments
        fields = ["enrollment_id", "user", "course", "progress_percent", "is_completed", "enrolled_at", "completed_at"]


LessonProgressSerializer = CourseEnrollmentSerializer


class CourseBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseBookmark
        fields = "__all__"


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ratings
        fields = "__all__"


CourseReviewSerializer = RatingSerializer


# ==============================================================================
# 7. VIDEOS, SUBTITLES & PROGRESS
# ==============================================================================

class VideoSubtitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoSubtitles
        fields = "__all__"


class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = "__all__"


class VideoNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoNotes
        fields = "__all__"


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.name")

    class Meta:
        model = Comments
        fields = ["id", "comment", "video", "user", "user_name"]


VideoCommentSerializer = CommentSerializer


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Likes
        fields = "__all__"


VideoLikeSerializer = LikeSerializer
VideoCommentLikeSerializer = LikeSerializer


class VideoBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoBookmark
        fields = "__all__"


class VideoSerializer(serializers.ModelSerializer):
    subtitles = VideoSubtitleSerializer(many=True, read_only=True)
    course_name = serializers.ReadOnlyField(source="course.name")

    class Meta:
        model = Videos
        fields = [
            "video_id", "title", "description", "video", "image",
            "like", "share", "views", "course", "course_name",
            "user", "status", "subtitles", "created_at"
        ]


# ==============================================================================
# 8. COMMUNITY & DISCUSSIONS
# ==============================================================================

class DiscussionTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionTag
        fields = "__all__"


class DiscussionReplySerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.name")
    user_profile = serializers.ReadOnlyField(source="user.profile")

    class Meta:
        model = DiscussionReplies
        fields = [
            "reply_id", "discussion", "user", "user_name", "user_profile",
            "content", "code", "likes_count", "is_accepted", "created_at"
        ]


DiscussionCommentSerializer = DiscussionReplySerializer


class DiscussionListSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source="user.name")
    author_profile = serializers.ReadOnlyField(source="user.profile")

    class Meta:
        model = Discussions
        fields = [
            "discussion_id", "title", "content", "code", "language", "tag",
            "user", "author_name", "author_profile", "likes_count", "comments_count",
            "is_solved", "is_pinned", "created_at"
        ]


class DiscussionDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source="user.name")
    author_profile = serializers.ReadOnlyField(source="user.profile")
    replies = DiscussionReplySerializer(many=True, read_only=True)

    class Meta:
        model = Discussions
        fields = [
            "discussion_id", "title", "content", "code", "language", "tag",
            "user", "author_name", "author_profile", "likes_count", "comments_count",
            "is_solved", "is_pinned", "replies", "created_at"
        ]


DiscussionPostSerializer = DiscussionDetailSerializer


class DiscussionLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionLikes
        fields = "__all__"


DiscussionPostLikeSerializer = DiscussionLikeSerializer
DiscussionCommentLikeSerializer = DiscussionLikeSerializer


class DiscussionBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionBookmarks
        fields = "__all__"


# ==============================================================================
# 9. NOTIFICATIONS & MISCELLANEOUS
# ==============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = ["notification_id", "user", "title", "body", "category", "icon", "read", "action_url", "created_at"]


class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = "__all__"


class InformationPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPage
        fields = "__all__"
        fields = "__all__"
