from django.contrib import admin
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
from .models import CompilerCoupon, CompilerCouponRedemption, CompilerProduct, CompilerPaymentOrder, CompilerEntitlement


class CouponRedemptionInline(admin.TabularInline):
    model = CompilerCouponRedemption
    extra = 0
    can_delete = False
    readonly_fields = ("user", "compiler", "discount_paise", "redeemed_at")


@admin.register(CompilerCoupon)
class CompilerCouponAdmin(admin.ModelAdmin):
    list_display = ("code", "compiler", "discount_type", "discount_value", "active", "expires_at", "redemption_count", "paid_revenue")
    search_fields = ("code",)
    list_filter = ("active", "compiler", "discount_type")
    list_editable = ("active",)
    inlines = (CouponRedemptionInline,)
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        obj.code = obj.code.strip().upper()
        super().save_model(request, obj, form, change)

    @admin.display(description="Redemptions")
    def redemption_count(self, obj):
        return obj.redemptions.count()

    @admin.display(description="Paid revenue (₹)")
    def paid_revenue(self, obj):
        total = sum(obj.payment_orders.filter(status="paid").values_list("amount_paise", flat=True))
        return f"₹{total / 100:.2f}"


@admin.register(CompilerProduct)
class CompilerProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price_paise", "currency", "active", "one_time_access", "updated_at")
    readonly_fields = ("updated_at",)
    search_fields = ("name", "slug")


@admin.register(CompilerPaymentOrder)
class CompilerPaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("razorpay_order_id", "user", "product", "amount_paise", "currency", "status", "created_at", "paid_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("razorpay_order_id", "razorpay_payment_id", "user__email", "user__username")
    readonly_fields = tuple(field.name for field in CompilerPaymentOrder._meta.fields)
    list_select_related = ("user", "product", "coupon")


@admin.register(CompilerEntitlement)
class CompilerEntitlementAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "status", "starts_at", "expires_at", "payment_order")
    list_filter = ("status", "product")
    search_fields = ("user__email", "user__username")

# ------------------------------------------------------------------------------
# 1. USERS & PROFILE
# ------------------------------------------------------------------------------

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "total_xp", "current_streak", "problems_solved", "quizzes_completed", "last_active_date")
    search_fields = ("user__username", "user__email", "headline")
    list_filter = ("role", "status", "last_active_date")


@admin.register(Badges)
class BadgesAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "points", "icon", "status", "created_at")
    search_fields = ("name", "slug", "description")
    list_filter = ("category", "status")


@admin.register(UserBadges)
class UserBadgesAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "earned_at")
    search_fields = ("user__username", "badge__name")
    list_filter = ("earned_at",)


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "minutes_spent", "problems_solved", "quizzes_completed", "xp_earned")
    search_fields = ("user__username",)
    list_filter = ("date",)


# ------------------------------------------------------------------------------
# 2. CODING & PRACTICE
# ------------------------------------------------------------------------------

class TestCaseInline(admin.TabularInline):
    model = TestCases
    extra = 1


@admin.register(CodingProblems)
class CodingProblemsAdmin(admin.ModelAdmin):
    list_display = ("title", "difficulty", "acceptance_rate", "points", "solved_count", "status", "created_at")
    search_fields = ("title", "slug", "description")
    list_filter = ("difficulty", "status", "created_at")
    inlines = [TestCaseInline]


@admin.register(TestCases)
class TestCasesAdmin(admin.ModelAdmin):
    list_display = ("problem", "is_sample", "is_hidden", "points", "order")
    list_filter = ("is_sample", "is_hidden")
    search_fields = ("problem__title",)


@admin.register(CodeSubmissions)
class CodeSubmissionsAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "language", "status", "passed_test_cases", "total_test_cases", "execution_time_ms", "score", "created_at")
    search_fields = ("user__username", "problem__title")
    list_filter = ("status", "language", "created_at")


@admin.register(UserProblemStatus)
class UserProblemStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "solved", "attempts", "last_attempt_at")
    search_fields = ("user__username", "problem__title")
    list_filter = ("solved",)


@admin.register(CompilerSnippets)
class CompilerSnippetsAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "language", "is_public", "status", "created_at")
    search_fields = ("title", "user__username")
    list_filter = ("language", "is_public", "status")


@admin.register(SyntaxMatrix)
class SyntaxMatrixAdmin(admin.ModelAdmin):
    list_display = ("topic", "category", "order")
    search_fields = ("topic", "category")
    list_filter = ("category",)


# ------------------------------------------------------------------------------
# 3. QUIZZES
# ------------------------------------------------------------------------------

class QuizOptionInline(admin.TabularInline):
    model = QuizOptions
    extra = 4


@admin.register(QuizQuestions)
class QuizQuestionsAdmin(admin.ModelAdmin):
    list_display = ("quiz", "question_text", "order", "points")
    search_fields = ("question_text", "quiz__title")
    list_filter = ("quiz__topic",)
    inlines = [QuizOptionInline]


@admin.register(Quizzes)
class QuizzesAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "difficulty", "duration_minutes", "passing_score", "total_questions", "points", "status")
    search_fields = ("title", "topic")
    list_filter = ("topic", "difficulty", "status")


@admin.register(QuizAttempts)
class QuizAttemptsAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score", "percentage", "passed", "time_taken_seconds", "created_at")
    search_fields = ("user__username", "quiz__title")
    list_filter = ("passed", "created_at")


# ------------------------------------------------------------------------------
# 4. INTERVIEW PREP
# ------------------------------------------------------------------------------

@admin.register(InterviewCategories)
class InterviewCategoriesAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "count", "status")
    search_fields = ("name",)


@admin.register(InterviewQuestions)
class InterviewQuestionsAdmin(admin.ModelAdmin):
    list_display = ("topic", "question", "difficulty", "status", "created_at")
    search_fields = ("question", "short_answer", "topic")
    list_filter = ("topic", "difficulty", "status")


@admin.register(CompanyRoadmaps)
class CompanyRoadmapsAdmin(admin.ModelAdmin):
    list_display = ("company", "step_number", "title", "category")
    search_fields = ("title", "company__name")
    list_filter = ("company", "category")


@admin.register(MockInterviewSessions)
class MockInterviewSessionsAdmin(admin.ModelAdmin):
    list_display = ("user", "role_track", "difficulty", "total_score", "completed_at")
    search_fields = ("user__username", "role_track")
    list_filter = ("difficulty", "completed_at")


# ------------------------------------------------------------------------------
# 5. COMMUNITY & DISCUSSIONS
# ------------------------------------------------------------------------------

class DiscussionReplyInline(admin.TabularInline):
    model = DiscussionReplies
    extra = 1


@admin.register(Discussions)
class DiscussionsAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "tag", "likes_count", "comments_count", "is_solved", "is_pinned", "status", "created_at")
    search_fields = ("title", "content", "user__username")
    list_filter = ("tag", "is_solved", "is_pinned", "status")
    inlines = [DiscussionReplyInline]


@admin.register(DiscussionReplies)
class DiscussionRepliesAdmin(admin.ModelAdmin):
    list_display = ("discussion", "user", "likes_count", "is_accepted", "created_at")
    search_fields = ("content", "user__username")
    list_filter = ("is_accepted", "created_at")


# ------------------------------------------------------------------------------
# 6. COURSES & MEDIA
# ------------------------------------------------------------------------------

class CourseLessonInline(admin.TabularInline):
    model = CourseLessons
    extra = 1


@admin.register(CourseModules)
class CourseModulesAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    search_fields = ("title", "course__name")
    inlines = [CourseLessonInline]


@admin.register(CourseEnrollments)
class CourseEnrollmentsAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "progress_percent", "is_completed", "enrolled_at", "completed_at")
    search_fields = ("user__username", "course__name")
    list_filter = ("is_completed", "enrolled_at")


@admin.register(VideoSubtitles)
class VideoSubtitlesAdmin(admin.ModelAdmin):
    list_display = ("video", "language_code", "label")
    search_fields = ("video__title", "label")


@admin.register(VideoProgress)
class VideoProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "video", "watched_seconds", "total_seconds", "is_completed", "last_watched_at")
    search_fields = ("user__username", "video__title")
    list_filter = ("is_completed",)


# ------------------------------------------------------------------------------
# 7. INTERNSHIPS
# ------------------------------------------------------------------------------

@admin.register(InternshipApplications)
class InternshipApplicationsAdmin(admin.ModelAdmin):
    list_display = ("internship", "user", "status", "applied_at")
    search_fields = ("internship__name", "user__username")
    list_filter = ("status", "applied_at")


@admin.register(SavedInternships)
class SavedInternshipsAdmin(admin.ModelAdmin):
    list_display = ("user", "internship", "created_at")
    search_fields = ("user__username", "internship__name")


# ------------------------------------------------------------------------------
# 8. NOTIFICATIONS
# ------------------------------------------------------------------------------

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "read", "created_at")
    search_fields = ("title", "body", "user__username")
    list_filter = ("category", "read", "created_at")
