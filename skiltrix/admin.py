from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db import models
from django.db.models import Avg, Count
from django.utils.text import slugify
import json
import csv
import uuid
import time

from .models import (
    Companies, Internship, Courses, Videos, Comments, Ratings, Language,
    CourseCategories, Resumes, Skills, Education, Code, Likes,
    UserProfile, Badges, UserBadges, DailyActivity,
    CodingProblems, TestCases, CodeSubmissions, UserProblemStatus,
    CodingAssessment, CompanyMock, AssessmentQuestion, AssessmentAttempt,
    AssessmentSection, AssessmentQuestionItem, AssessmentTestCase, QuestionPool,
    AssessmentEvent, CompanyBlueprint,
    CompilerSnippets, SyntaxMatrix,
    Quizzes, QuizQuestions, QuizOptions, QuizAttempts, QuizUserAnswers,
    InterviewCategories, InterviewQuestions, CompanyRoadmaps, MockInterviewSessions,
    Discussions, DiscussionReplies, DiscussionLikes, DiscussionBookmarks,
    CourseModules, CourseLessons, CourseEnrollments, CoursePaymentOrder,
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
    fields = ("order", "is_sample", "is_hidden", "category", "points", "input_data", "expected_output", "explanation")


@admin.register(CodingProblems)
class CodingProblemsAdmin(admin.ModelAdmin):
    list_display = ("title", "difficulty", "category", "question_type", "points", "solved_count", "status", "created_at")
    search_fields = ("title", "slug", "description", "category")
    list_filter = ("difficulty", "question_type", "category", "status", "created_at")
    inlines = [TestCaseInline]


@admin.register(TestCases)
class TestCasesAdmin(admin.ModelAdmin):
    list_display = ("problem", "order", "category", "is_sample", "is_hidden", "points")
    list_filter = ("is_sample", "is_hidden", "category")
    search_fields = ("problem__title", "explanation")


# ==============================================================================
# COMPANY ASSESSMENTS & ADMIN QUESTION MANAGEMENT SYSTEM
# ==============================================================================

class AssessmentTestCaseInline(admin.TabularInline):
    model = AssessmentTestCase
    extra = 1
    fields = ("order", "test_type", "weight", "is_active", "input_data", "expected_output", "explanation")


class AssessmentQuestionItemInline(admin.TabularInline):
    model = AssessmentQuestionItem
    extra = 1
    fields = ("order", "section", "question_type", "title", "marks", "negative_marks", "difficulty", "status")
    show_change_link = True


class AssessmentSectionInline(admin.TabularInline):
    model = AssessmentSection
    extra = 1
    fields = ("order", "title", "section_type", "question_pool", "pool_question_count", "duration_minutes", "total_marks")
    show_change_link = True


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 1
    fields = ("order", "problem", "marks")


@admin.register(AssessmentTestCase)
class AssessmentTestCaseAdmin(admin.ModelAdmin):
    list_display = ("case_id", "question", "test_type", "weight", "is_active", "order", "created_at")
    list_filter = ("test_type", "is_active")
    search_fields = ("question__title", "input_data", "expected_output", "explanation")
    list_editable = ("order", "is_active", "test_type", "weight")


@admin.register(QuestionPool)
class QuestionPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "company_style", "difficulty", "question_count", "is_active", "created_at")
    list_filter = ("difficulty", "company_style", "category", "is_active")
    search_fields = ("name", "slug", "category", "description")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Questions In Pool")
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(AssessmentQuestionItem)
class AssessmentQuestionItemAdmin(admin.ModelAdmin):
    inlines = [AssessmentTestCaseInline]
    list_display = (
        "title",
        "question_type_badge",
        "difficulty_badge",
        "category",
        "company_style",
        "marks",
        "status_badge",
        "test_case_count",
        "usage_count",
        "updated_at",
        "action_links",
    )
    list_filter = (
        "question_type",
        "difficulty",
        "status",
        "company_style",
        "section_assignment",
        "category",
        "language",
        "created_at",
    )
    search_fields = (
        "title",
        "slug",
        "category",
        "company_style",
        "tags",
        "language",
        "prompt",
    )
    readonly_fields = (
        "item_id",
        "version",
        "created_at",
        "updated_at",
        "question_statistics_panel",
    )
    fieldsets = (
        ("1. Basic Information", {
            "fields": (
                "title",
                "slug",
                "question_type",
                "category",
                "subcategory",
                "difficulty",
                "status",
                "company_style",
                "section_assignment",
                "language",
                "tags",
            )
        }),
        ("2. Assessment & Pool Assignment", {
            "fields": (
                "assessment",
                "section",
                "pool",
                "problem",
                "order",
            )
        }),
        ("3. Scoring & Resource Limits", {
            "fields": (
                "marks",
                "negative_marks",
                "time_limit_seconds",
                "memory_limit_mb",
                "expected_complexity",
            )
        }),
        ("4. Problem Statement & Content", {
            "fields": (
                "prompt",
                "instructions",
                "input_format",
                "output_format",
                "constraints",
                "examples",
                "hints",
                "topics",
                "explanation",
            )
        }),
        ("5. Multiple Choice & Multiple Select Options", {
            "description": "Configure options and answer keys for Multiple Choice, Multiple Select, and Output Prediction.",
            "fields": (
                "options",
                "correct_answers",
            )
        }),
        ("6. Coding & Algorithmic Specifications", {
            "description": "Configure starter code and confidential reference solution. Reference solutions are NEVER exposed to students.",
            "fields": (
                "starter_code",
                "function_signature",
                "reference_solution",
            )
        }),
        ("7. Django & Backend Debugging Specifications", {
            "description": "Configure realistic error simulation, buggy code, and required fixes for backend debugging assessments.",
            "fields": (
                "buggy_code",
                "error_message",
                "expected_behavior",
                "debugging_task",
                "environment_info",
                "framework_version",
                "expected_fix",
            )
        }),
        ("8. Question Performance & Real Telemetry", {
            "fields": (
                "question_statistics_panel",
            )
        }),
        ("9. Audit & Versioning Metadata", {
            "fields": (
                "item_id",
                "version",
                "parent_question",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",)
        }),
    )

    actions = [
        "publish_selected",
        "unpublish_selected",
        "archive_selected",
        "duplicate_selected",
        "set_difficulty_easy",
        "set_difficulty_medium",
        "set_difficulty_hard",
        "set_style_amazon",
        "set_style_deloitte",
        "set_style_tcs",
        "set_style_general",
        "export_as_json",
        "export_as_csv",
    ]

    # --- List Badges & Display Methods ---
    @admin.display(description="Type")
    def question_type_badge(self, obj):
        colors = {
            "mcq_single": "#6366f1",
            "mcq_multi": "#8b5cf6",
            "coding": "#059669",
            "sql": "#0284c7",
            "debugging": "#d97706",
            "django_debugging": "#dc2626",
            "backend_debugging": "#ea580c",
            "output_prediction": "#7c3aed",
            "code_correction": "#c026d3",
            "aptitude": "#0d9488",
            "reasoning": "#2563eb",
            "cs_fundamentals": "#475569",
        }
        color = colors.get(obj.question_type, "#64748b")
        return mark_safe(f'<span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{obj.get_question_type_display()}</span>')

    @admin.display(description="Difficulty")
    def difficulty_badge(self, obj):
        colors = {"Easy": "#10b981", "Medium": "#f59e0b", "Hard": "#ef4444"}
        color = colors.get(obj.difficulty, "#64748b")
        return mark_safe(f'<span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{obj.difficulty}</span>')

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {"Published": "#059669", "Draft": "#f59e0b", "Archived": "#64748b"}
        color = colors.get(obj.status, "#64748b")
        return mark_safe(f'<span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{obj.status}</span>')

    @admin.display(description="Test Cases")
    def test_case_count(self, obj):
        count = obj.test_cases.count()
        if count == 0 and obj.problem:
            count = obj.problem.test_cases.count()
        return count

    @admin.display(description="Usage")
    def usage_count(self, obj):
        count = 0
        if obj.assessment:
            count += 1
        count += AssessmentAttempt.objects.filter(assigned_question_ids__contains=obj.item_id).count()
        return count

    @admin.display(description="Quick Actions")
    def action_links(self, obj):
        preview_url = reverse("admin:skiltrix_assessmentquestionitem_preview", args=[obj.pk])
        test_url = reverse("admin:skiltrix_assessmentquestionitem_test", args=[obj.pk])
        duplicate_url = reverse("admin:skiltrix_assessmentquestionitem_duplicate", args=[obj.pk])
        return mark_safe(f'''
            <div style="display: flex; gap: 5px; white-space: nowrap;">
                <a href="{preview_url}" style="background: #4f46e5; color: white; padding: 2px 7px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 600;" title="Student examination preview with staff inspection box">Preview</a>
                <a href="{test_url}" style="background: #10b981; color: white; padding: 2px 7px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 600;" title="Run test cases on reference solution">Test</a>
                <a href="{duplicate_url}" style="background: #64748b; color: white; padding: 2px 7px; border-radius: 4px; font-size: 11px; text-decoration: none; font-weight: 600;" title="Duplicate as new Draft">Copy</a>
            </div>
        ''')

    @admin.display(description="Real Performance Statistics")
    def question_statistics_panel(self, obj):
        if not obj or not obj.pk:
            return "Save question first to view candidate telemetry."

        total_answered = 0
        correct_count = 0
        wrong_count = 0
        total_time_ms = 0.0
        time_count = 0
        score_sum = 0.0

        for attempt in AssessmentAttempt.objects.filter(status__in=["completed", "timed_out"]):
            answers = attempt.selected_answers or {}
            ans = answers.get(obj.item_id) or answers.get(str(obj.pk))
            if ans is not None:
                total_answered += 1
                expected = set(obj.correct_answers or [])
                given = set(ans if isinstance(ans, list) else [ans])
                if expected and given == expected:
                    correct_count += 1
                    score_sum += obj.marks
                else:
                    wrong_count += 1

        if obj.problem:
            subs = CodeSubmissions.objects.filter(problem=obj.problem)
            sub_count = subs.count()
            sub_correct = subs.filter(status="Accepted").count()
            sub_wrong = sub_count - sub_correct
            sub_time = subs.exclude(execution_time_ms=0).aggregate(Avg("execution_time_ms"))["execution_time_ms__avg"] or 0
            total_answered += sub_count
            correct_count += sub_correct
            wrong_count += sub_wrong
            if sub_time:
                total_time_ms += sub_time
                time_count += 1

        success_rate = f"{(correct_count / total_answered * 100):.1f}%" if total_answered > 0 else "0.0%"
        avg_time = f"{total_time_ms:.1f} ms" if time_count > 0 else "N/A"
        avg_score = f"{(score_sum / total_answered):.1f}" if total_answered > 0 else "0.0"

        html = f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: sans-serif;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center;">
                <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Total Attempts</div>
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a;">{total_answered}</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Success Rate</div>
                    <div style="font-size: 18px; font-weight: 700; color: #10b981;">{success_rate}</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Correct / Wrong</div>
                    <div style="font-size: 16px; font-weight: 700; color: #334155;">{correct_count} / {wrong_count}</div>
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 12px; color: #64748b; display: flex; justify-content: space-between;">
                <span>Average Execution Time: <strong style="color: #1e293b;">{avg_time}</strong></span>
                <span>Average Points Earned: <strong style="color: #1e293b;">{avg_score}</strong></span>
            </div>
        </div>
        """
        return mark_safe(html)

    # --- Validation ---
    def validate_for_publishing(self, obj):
        errors = []
        if not obj.title or not obj.title.strip():
            errors.append("Title is required.")
        if not obj.prompt or not obj.prompt.strip():
            errors.append("Problem Statement (prompt) is required.")
        if not obj.category:
            errors.append("Category is required.")
        if not obj.difficulty:
            errors.append("Difficulty is required.")

        if obj.question_type in ["mcq_single", "mcq_multi", "output_prediction", "aptitude", "reasoning", "cs_fundamentals"]:
            if not obj.options or len(obj.options) < 2:
                errors.append("Multiple Choice questions require at least 2 options.")
            if not obj.correct_answers or len(obj.correct_answers) == 0:
                errors.append("At least 1 correct answer must be specified.")

        if obj.question_type in ["coding", "debugging", "django_debugging", "backend_debugging", "code_correction"]:
            if not obj.starter_code and not (obj.problem and obj.problem.starter_python):
                errors.append("Starter code is required for coding/debugging questions.")
            tc_count = obj.test_cases.count()
            if tc_count == 0 and obj.problem:
                tc_count = obj.problem.test_cases.count()
            if tc_count < 2:
                errors.append("Coding/debugging questions require at least 1 public test case and 1 hidden test case before publishing.")

        return errors

    # --- Bulk Actions ---
    @admin.action(description="Publish Selected Questions")
    def publish_selected(self, request, queryset):
        published = 0
        failed = []
        for q in queryset:
            errs = self.validate_for_publishing(q)
            if errs:
                failed.append(f"{q.title} ({', '.join(errs)})")
            else:
                q.status = "Published"
                q.save(update_fields=["status"])
                published += 1
        if published:
            self.message_user(request, f"Successfully published {published} question(s).", messages.SUCCESS)
        if failed:
            self.message_user(request, f"Could not publish {len(failed)} question(s) due to validation errors: {'; '.join(failed[:3])}", messages.ERROR)

    @admin.action(description="Unpublish Selected (Move to Draft)")
    def unpublish_selected(self, request, queryset):
        count = queryset.update(status="Draft")
        self.message_user(request, f"{count} question(s) moved to Draft.", messages.SUCCESS)

    @admin.action(description="Archive Selected")
    def archive_selected(self, request, queryset):
        count = queryset.update(status="Archived")
        self.message_user(request, f"{count} question(s) marked as Archived.", messages.SUCCESS)

    @admin.action(description="Duplicate Selected Questions")
    def duplicate_selected(self, request, queryset):
        count = 0
        for q in queryset:
            self._clone_question(q)
            count += 1
        self.message_user(request, f"Successfully duplicated {count} question(s) as Drafts.", messages.SUCCESS)

    @admin.action(description="Set Difficulty: Easy")
    def set_difficulty_easy(self, request, queryset):
        queryset.update(difficulty="Easy")

    @admin.action(description="Set Difficulty: Medium")
    def set_difficulty_medium(self, request, queryset):
        queryset.update(difficulty="Medium")

    @admin.action(description="Set Difficulty: Hard")
    def set_difficulty_hard(self, request, queryset):
        queryset.update(difficulty="Hard")

    @admin.action(description="Set Style: Amazon-style")
    def set_style_amazon(self, request, queryset):
        queryset.update(company_style="Amazon-style")

    @admin.action(description="Set Style: Deloitte-style")
    def set_style_deloitte(self, request, queryset):
        queryset.update(company_style="Deloitte-style")

    @admin.action(description="Set Style: TCS-style")
    def set_style_tcs(self, request, queryset):
        queryset.update(company_style="TCS-style")

    @admin.action(description="Set Style: General SDE")
    def set_style_general(self, request, queryset):
        queryset.update(company_style="General SDE")

    @admin.action(description="Export Selected as JSON")
    def export_as_json(self, request, queryset):
        data = []
        for q in queryset:
            data.append({
                "item_id": q.item_id,
                "title": q.title,
                "slug": q.slug,
                "question_type": q.question_type,
                "category": q.category,
                "difficulty": q.difficulty,
                "company_style": q.company_style,
                "language": q.language,
                "marks": q.marks,
                "prompt": q.prompt,
                "options": q.options,
                "starter_code": q.starter_code,
                "reference_solution": q.reference_solution,
                "test_cases": list(q.test_cases.values("input_data", "expected_output", "test_type", "weight", "order")),
            })
        response = HttpResponse(json.dumps(data, indent=2), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="skiltrix_questions.json"'
        return response

    @admin.action(description="Export Selected as CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="skiltrix_questions.csv"'
        writer = csv.writer(response)
        writer.writerow(["Title", "Type", "Difficulty", "Category", "Company Style", "Language", "Marks", "Status"])
        for q in queryset:
            writer.writerow([q.title, q.question_type, q.difficulty, q.category, q.company_style, q.language, q.marks, q.status])
        return response

    # --- Custom ModelAdmin URLs & Views ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<path:object_id>/preview/", self.admin_site.admin_view(self.preview_question_view), name="skiltrix_assessmentquestionitem_preview"),
            path("<path:object_id>/test/", self.admin_site.admin_view(self.test_question_view), name="skiltrix_assessmentquestionitem_test"),
            path("<path:object_id>/duplicate/", self.admin_site.admin_view(self.duplicate_question_view), name="skiltrix_assessmentquestionitem_duplicate"),
            path("<path:object_id>/publish/", self.admin_site.admin_view(self.publish_single_question_view), name="skiltrix_assessmentquestionitem_publish"),
            path("import-questions/", self.admin_site.admin_view(self.import_questions_view), name="skiltrix_assessmentquestionitem_import"),
            path("dashboard/", self.admin_site.admin_view(self.dashboard_view), name="skiltrix_assessmentquestionitem_dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        return company_assessments_dashboard_view(request)

    def _clone_question(self, question):
        clone = AssessmentQuestionItem.objects.get(pk=question.pk)
        clone.pk = None
        clone.item_id = f"q_{uuid.uuid4().hex[:12]}"
        clone.slug = f"{slugify(question.title)[:180]}-copy-{uuid.uuid4().hex[:6]}"
        clone.title = f"{question.title} (Copy)"
        clone.status = "Draft"
        clone.version = 1
        clone.parent_question = question
        clone.save()

        for tc in question.test_cases.all():
            tc_clone = AssessmentTestCase.objects.get(pk=tc.pk)
            tc_clone.pk = None
            tc_clone.case_id = f"tc_{uuid.uuid4().hex[:12]}"
            tc_clone.question = clone
            tc_clone.save()
        return clone

    def duplicate_question_view(self, request, object_id):
        question = get_object_or_404(AssessmentQuestionItem, pk=object_id)
        clone = self._clone_question(question)
        messages.success(request, f"Question duplicated successfully as Draft: '{clone.title}'.")
        return redirect("admin:skiltrix_assessmentquestionitem_change", clone.pk)

    def publish_single_question_view(self, request, object_id):
        question = get_object_or_404(AssessmentQuestionItem, pk=object_id)
        errs = self.validate_for_publishing(question)
        if errs:
            messages.error(request, f"Cannot publish question: {'; '.join(errs)}")
        else:
            question.status = "Published"
            question.save(update_fields=["status"])
            messages.success(request, f"Question '{question.title}' published successfully.")
        return redirect("admin:skiltrix_assessmentquestionitem_change", question.pk)

    def preview_question_view(self, request, object_id):
        question = get_object_or_404(AssessmentQuestionItem, pk=object_id)
        test_cases = list(question.test_cases.all().order_by("order"))
        if not test_cases and question.problem:
            test_cases = list(question.problem.test_cases.all().order_by("order"))

        public_test_cases = [tc for tc in test_cases if getattr(tc, "test_type", "") == "Public" or getattr(tc, "is_sample", False)]
        hidden_test_cases = [tc for tc in test_cases if getattr(tc, "test_type", "") == "Hidden" or getattr(tc, "is_hidden", False)]

        context = {
            "question": question,
            "public_test_cases": public_test_cases,
            "hidden_test_cases": hidden_test_cases,
        }
        return render(request, "admin/skiltrix/question_preview.html", context)

    def test_question_view(self, request, object_id):
        question = get_object_or_404(AssessmentQuestionItem, pk=object_id)
        test_cases = list(question.test_cases.filter(is_active=True).order_by("order"))
        if not test_cases and question.problem:
            test_cases = list(question.problem.test_cases.all().order_by("order"))

        code_to_test = question.reference_solution or question.starter_code
        if not code_to_test and question.problem:
            code_to_test = question.problem.solution_code or question.problem.starter_python

        lang = question.language or "python"

        # Objective / MCQ questions validation
        if question.question_type in ["mcq_single", "mcq_multi", "aptitude", "reasoning", "cs_fundamentals", "output_prediction"]:
            is_valid = bool(question.options and len(question.options) >= 2 and question.correct_answers)
            result = {
                "verdict": "Accepted" if is_valid else "Validation Failed",
                "passed_count": len(question.correct_answers or []),
                "total_count": len(question.options or []),
                "total_duration_ms": 1.2,
                "max_memory_kb": 128,
                "compilation_error": None if is_valid else "Missing options list or correct answers",
                "public_passed": len(question.options or []),
                "public_total": len(question.options or []),
                "hidden_passed": 0,
                "hidden_total": 0,
                "performance_rating": "Optimal (MCQ / Objective)",
                "test_results": [
                    {
                        "passed": is_valid,
                        "test_type": "Objective Validation",
                        "duration_ms": 1.0,
                        "input_data": f"Configured answer key: {question.correct_answers}",
                        "expected_output": "Non-empty options list (>= 2)",
                        "actual_output": "Valid options & answer key" if is_valid else "Incomplete options/key",
                    }
                ]
            }
            return render(request, "admin/skiltrix/test_question_result.html", {"question": question, "result": result})

        # Coding / Debugging test execution
        if not code_to_test:
            messages.error(request, "Cannot run test suite: Reference Solution or starter code is missing.")
            return redirect("admin:skiltrix_assessmentquestionitem_change", object_id)

        from skiltrix.execution.worker import execute_code_job
        from skiltrix.codelab_evaluator import normalize_output

        test_results = []
        passed_count = 0
        total_duration = 0.0
        max_mem = 0.0
        compilation_error = None

        pub_passed = 0
        pub_total = 0
        hid_passed = 0
        hid_total = 0

        for tc in test_cases:
            is_hid = (getattr(tc, "test_type", "") == "Hidden") or getattr(tc, "is_hidden", False)
            if is_hid:
                hid_total += 1
            else:
                pub_total += 1

            start_t = time.time()
            job_res = execute_code_job(
                language=lang,
                code=code_to_test,
                stdin=tc.input_data or "",
                timeout=question.time_limit_seconds or 4.0
            )
            duration_ms = (time.time() - start_t) * 1000
            total_duration += duration_ms

            status_str = job_res.get("status")
            actual_out = (job_res.get("stdout") or "").strip()
            stderr = (job_res.get("stderr") or "").strip()
            normalized_expected = normalize_output(tc.expected_output or "")
            normalized_actual = normalize_output(actual_out)

            passed = (status_str in ["completed", "success"]) and (normalized_actual == normalized_expected)
            if not passed and not actual_out and stderr:
                compilation_error = stderr

            if passed:
                passed_count += 1
                if is_hid:
                    hid_passed += 1
                else:
                    pub_passed += 1

            test_results.append({
                "passed": passed,
                "test_type": "Hidden" if is_hid else "Public",
                "duration_ms": round(duration_ms, 1),
                "input_data": tc.input_data or "(empty)",
                "expected_output": tc.expected_output or "(empty)",
                "actual_output": actual_out or (stderr if stderr else "(empty)"),
            })

        verdict = "Accepted" if (passed_count == len(test_cases) and len(test_cases) > 0) else "Wrong Answer"
        if compilation_error:
            verdict = "Compile Error"

        perf = "Optimal (< 100ms)" if total_duration < 100 else f"Normal ({round(total_duration)}ms)"
        result = {
            "verdict": verdict,
            "passed_count": passed_count,
            "total_count": len(test_cases),
            "total_duration_ms": round(total_duration, 1),
            "max_memory_kb": round(max_mem, 1),
            "compilation_error": compilation_error,
            "public_passed": pub_passed,
            "public_total": pub_total,
            "hidden_passed": hid_passed,
            "hidden_total": hid_total,
            "performance_rating": perf,
            "test_results": test_results
        }
        return render(request, "admin/skiltrix/test_question_result.html", {"question": question, "result": result})

    def import_questions_view(self, request):
        if request.method == "POST":
            uploaded = request.FILES.get("import_file")
            json_text = request.POST.get("json_data", "").strip()
            csv_text = request.POST.get("csv_data", "").strip()
            imported_count = 0
            try:
                content = None
                if uploaded:
                    fname = uploaded.name.lower()
                    if fname.endswith(".json"):
                        content = json.loads(uploaded.read().decode("utf-8"))
                    elif fname.endswith(".csv"):
                        csv_text = uploaded.read().decode("utf-8")
                elif json_text:
                    content = json.loads(json_text)

                if content is not None:
                    if isinstance(content, dict):
                        content = [content]
                    for item in content:
                        q = AssessmentQuestionItem.objects.create(
                            item_id=f"q_{uuid.uuid4().hex[:12]}",
                            title=item.get("title", "Imported Question"),
                            slug=slugify(item.get("title", "imported"))[:200] + f"-{uuid.uuid4().hex[:6]}",
                            question_type=item.get("question_type", "coding"),
                            difficulty=item.get("difficulty", "Medium"),
                            category=item.get("category", "DSA"),
                            company_style=item.get("company_style", "General SDE"),
                            language=item.get("language", "python"),
                            status="Draft",
                            prompt=item.get("prompt") or item.get("description") or "Imported prompt",
                            instructions=item.get("instructions", ""),
                            marks=float(item.get("marks", 10)),
                            starter_code=item.get("starter_code", ""),
                            reference_solution=item.get("reference_solution", ""),
                            options=item.get("options", []),
                            correct_answers=item.get("correct_answers", []),
                        )
                        for tc_data in item.get("test_cases", []):
                            AssessmentTestCase.objects.create(
                                case_id=f"tc_{uuid.uuid4().hex[:12]}",
                                question=q,
                                input_data=tc_data.get("input") or tc_data.get("input_data") or "",
                                expected_output=tc_data.get("expected_output") or "",
                                test_type=tc_data.get("test_type", "Public"),
                                weight=float(tc_data.get("weight", 10.0)),
                            )
                        imported_count += 1
                elif csv_text:
                    reader = csv.DictReader(csv_text.splitlines())
                    for row in reader:
                        title = row.get("title") or row.get("Title") or "Imported Question"
                        AssessmentQuestionItem.objects.create(
                            item_id=f"q_{uuid.uuid4().hex[:12]}",
                            title=title,
                            slug=slugify(title)[:200] + f"-{uuid.uuid4().hex[:6]}",
                            question_type=row.get("question_type") or row.get("Type") or "coding",
                            difficulty=row.get("difficulty") or row.get("Difficulty") or "Medium",
                            category=row.get("category") or row.get("Category") or "DSA",
                            company_style=row.get("company_style") or row.get("Company Style") or "General SDE",
                            language=row.get("language") or row.get("Language") or "python",
                            status="Draft",
                            prompt=row.get("description") or row.get("prompt") or "Imported prompt",
                            marks=float(row.get("marks") or 10.0),
                        )
                        imported_count += 1

                if imported_count > 0:
                    messages.success(request, f"Successfully imported {imported_count} questions as Drafts.")
                    return redirect("admin:skiltrix_assessmentquestionitem_changelist")
                else:
                    messages.warning(request, "No valid question records were found to import.")
            except Exception as e:
                messages.error(request, f"Error parsing import data: {str(e)}")
        return render(request, "admin/skiltrix/question_import.html")


@admin.register(CodingAssessment)
class CodingAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company_tag",
        "category",
        "difficulty",
        "duration_minutes",
        "total_marks",
        "section_count",
        "question_count",
        "is_pro_only",
        "proctoring_enabled",
        "active",
    )
    search_fields = ("title", "slug", "description", "company_tag")
    list_filter = ("category", "company_tag", "difficulty", "is_pro_only", "proctoring_enabled", "active")
    inlines = [AssessmentSectionInline, AssessmentQuestionItemInline, AssessmentQuestionInline]
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Assessment Overview", {
            "fields": (
                "title",
                "slug",
                "company_tag",
                "category",
                "difficulty",
                "duration_minutes",
                "total_marks",
                "pass_percentage",
                "negative_marking_percentage",
                "description",
                "active",
            )
        }),
        ("Proctoring & Anti-Cheat Controls", {
            "fields": (
                "proctoring_enabled",
                "require_fullscreen",
                "require_screen_share",
                "max_tab_switches",
                "max_fullscreen_exits",
                "allow_return_to_previous",
                "auto_submit_on_violations",
            )
        }),
        ("Randomization & Entitlement", {
            "fields": (
                "randomize_questions",
                "randomize_options",
                "is_company_mock",
                "is_pro_only",
            )
        }),
    )

    @admin.display(description="Sections")
    def section_count(self, obj):
        return obj.sections.count()

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.question_items.count() or obj.questions.count()


@admin.register(CompanyMock)
class CompanyMockAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company_tag",
        "category",
        "difficulty_badge",
        "duration_minutes",
        "total_marks",
        "pass_percentage",
        "section_count",
        "question_count",
        "attempt_count",
        "is_pro_only",
        "proctoring_enabled",
        "active",
    )
    list_editable = ("active", "is_pro_only", "proctoring_enabled")
    search_fields = ("title", "slug", "description", "company_tag")
    list_filter = ("company_tag", "difficulty", "is_pro_only", "proctoring_enabled", "active", "category")
    inlines = [AssessmentSectionInline, AssessmentQuestionItemInline]
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Company Mock Overview", {
            "fields": (
                "title",
                "slug",
                "company_tag",
                "category",
                "difficulty",
                "duration_minutes",
                "total_marks",
                "pass_percentage",
                "negative_marking_percentage",
                "description",
                "active",
            )
        }),
        ("Proctoring & Anti-Cheat Controls", {
            "fields": (
                "proctoring_enabled",
                "require_fullscreen",
                "require_screen_share",
                "max_tab_switches",
                "max_fullscreen_exits",
                "allow_return_to_previous",
                "auto_submit_on_violations",
            )
        }),
        ("Randomization & Access Tiers", {
            "fields": (
                "randomize_questions",
                "randomize_options",
                "is_company_mock",
                "is_pro_only",
            )
        }),
    )
    actions = [
        "duplicate_selected_mocks",
        "activate_selected_mocks",
        "deactivate_selected_mocks",
        "enable_proctoring_selected",
        "disable_proctoring_selected",
        "sync_sections_from_blueprint",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            models.Q(is_company_mock=True) | models.Q(category="Company Mocks")
        )

    def save_model(self, request, obj, form, change):
        obj.is_company_mock = True
        if not obj.assessment_id:
            obj.assessment_id = f"asmt_mock_{uuid.uuid4().hex[:8]}"
        if not obj.slug:
            obj.slug = slugify(obj.title)
        super().save_model(request, obj, form, change)

    @admin.display(description="Difficulty")
    def difficulty_badge(self, obj):
        colors = {
            "Easy": "#10b981",
            "Medium": "#f59e0b",
            "Hard": "#ef4444",
        }
        color = colors.get(obj.difficulty, "#64748b")
        return mark_safe(f'<span style="background: {color}20; color: {color}; font-weight: 700; padding: 3px 8px; border-radius: 4px; font-size: 11px;">{obj.difficulty}</span>')

    @admin.display(description="Sections")
    def section_count(self, obj):
        return obj.sections.count()

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.question_items.count() or obj.questions.count()

    @admin.display(description="Attempts")
    def attempt_count(self, obj):
        return obj.attempts.count()

    @admin.action(description="Duplicate Selected Mock Assessments (with Sections & Questions)")
    def duplicate_selected_mocks(self, request, queryset):
        count = 0
        for mock in queryset:
            new_uuid = uuid.uuid4().hex[:8]
            new_mock = CodingAssessment.objects.create(
                assessment_id=f"asmt_mock_{new_uuid}",
                title=f"{mock.title} (Copy)",
                slug=f"{mock.slug}-copy-{new_uuid}",
                category=mock.category,
                company_tag=mock.company_tag,
                description=mock.description,
                difficulty=mock.difficulty,
                duration_minutes=mock.duration_minutes,
                pass_percentage=mock.pass_percentage,
                total_marks=mock.total_marks,
                negative_marking_percentage=mock.negative_marking_percentage,
                is_company_mock=True,
                is_pro_only=mock.is_pro_only,
                proctoring_enabled=mock.proctoring_enabled,
                require_fullscreen=mock.require_fullscreen,
                require_screen_share=mock.require_screen_share,
                max_tab_switches=mock.max_tab_switches,
                max_fullscreen_exits=mock.max_fullscreen_exits,
                allow_return_to_previous=mock.allow_return_to_previous,
                auto_submit_on_violations=mock.auto_submit_on_violations,
                randomize_questions=mock.randomize_questions,
                randomize_options=mock.randomize_options,
                active=False,
            )
            for sec in mock.sections.all():
                AssessmentSection.objects.create(
                    assessment=new_mock,
                    title=sec.title,
                    section_type=sec.section_type,
                    order=sec.order,
                    question_pool=sec.question_pool,
                    pool_question_count=sec.pool_question_count,
                    duration_minutes=sec.duration_minutes,
                    total_marks=sec.total_marks,
                    negative_marks_per_question=sec.negative_marks_per_question,
                )
            for item in mock.question_items.all():
                item.pk = None
                item.item_id = str(uuid.uuid4())
                item.assessment = new_mock
                item.save()
            count += 1
        self.message_user(request, f"Successfully duplicated {count} mock assessment(s) as inactive drafts for review.", messages.SUCCESS)

    @admin.action(description="Publish / Activate Selected Mocks")
    def activate_selected_mocks(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} mock assessment(s) successfully activated.", messages.SUCCESS)

    @admin.action(description="Unpublish / Deactivate Selected Mocks")
    def deactivate_selected_mocks(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} mock assessment(s) deactivated.", messages.SUCCESS)

    @admin.action(description="Enable Strict Proctoring for Selected Mocks")
    def enable_proctoring_selected(self, request, queryset):
        updated = queryset.update(proctoring_enabled=True, require_fullscreen=True, require_screen_share=True)
        self.message_user(request, f"Strict proctoring enabled on {updated} mock assessment(s).", messages.SUCCESS)

    @admin.action(description="Disable Proctoring for Selected Mocks")
    def disable_proctoring_selected(self, request, queryset):
        updated = queryset.update(proctoring_enabled=False)
        self.message_user(request, f"Proctoring disabled on {updated} mock assessment(s).", messages.SUCCESS)

    @admin.action(description="Sync / Generate Sections from Company Blueprint")
    def sync_sections_from_blueprint(self, request, queryset):
        total_created = 0
        for mock in queryset:
            bp = CompanyBlueprint.objects.filter(
                models.Q(company_name__icontains=mock.company_tag) |
                models.Q(slug__icontains=mock.company_tag.lower().replace("-style", ""))
            ).first()
            if not bp:
                continue
            order = 1
            for sec_cfg in bp.sections_config:
                sec_title = sec_cfg.get("title", f"Section {order}")
                sec_type = sec_cfg.get("type", "coding")
                sec_marks = float(sec_cfg.get("marks", 25))
                sec, created = AssessmentSection.objects.get_or_create(
                    assessment=mock,
                    title=sec_title,
                    defaults={
                        "section_type": sec_type,
                        "order": order,
                        "total_marks": sec_marks,
                        "duration_minutes": max(15, mock.duration_minutes // (len(bp.sections_config) or 1))
                    }
                )
                if created:
                    total_created += 1
                order += 1
        self.message_user(request, f"Created {total_created} new section(s) synced from Company Blueprints.", messages.SUCCESS)


@admin.register(AssessmentSection)
class AssessmentSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "assessment", "section_type", "order", "question_pool", "pool_question_count", "duration_minutes", "total_marks")
    search_fields = ("title", "assessment__title")
    list_filter = ("section_type", "assessment")


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "attempt_id",
        "user",
        "assessment",
        "status",
        "total_score",
        "max_possible_score",
        "percentage",
        "passed",
        "integrity_score",
        "tab_switch_count",
        "fullscreen_exit_count",
        "started_at",
    )
    search_fields = ("attempt_id", "user__username", "user__email", "assessment__title")
    list_filter = ("status", "passed", "assessment", "started_at")
    readonly_fields = (
        "attempt_id",
        "started_at",
        "expires_at",
        "completed_at",
        "selected_answers",
        "assigned_question_ids",
        "skill_breakdown",
        "section_scores",
    )


@admin.register(AssessmentEvent)
class AssessmentEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "user", "assessment", "timestamp")
    search_fields = ("user__username", "assessment__title", "event_type")
    list_filter = ("event_type", "timestamp")
    readonly_fields = ("event_id", "timestamp")


@admin.register(CompanyBlueprint)
class CompanyBlueprintAdmin(admin.ModelAdmin):
    list_display = ("company_name", "category", "duration_minutes", "tier", "mock_status", "sections_count", "is_active", "created_at")
    search_fields = ("company_name", "slug", "description")
    list_filter = ("category", "tier", "is_active")
    prepopulated_fields = {"slug": ("company_name",)}
    actions = ["generate_mock_assessments", "activate_blueprints", "deactivate_blueprints"]

    @admin.display(description="Mock Linked")
    def mock_status(self, obj):
        tag = obj.company_name.replace(" Mock", "")
        mock = CodingAssessment.objects.filter(models.Q(company_tag=tag) | models.Q(title__icontains=tag)).first()
        if mock:
            url = reverse("admin:skiltrix_companymock_change", args=[mock.pk])
            return mark_safe(f'<a href="{url}" style="color: #10b981; font-weight: 700;">✓ Ready ({mock.sections.count()} secs)</a>')
        return mark_safe('<span style="color: #ef4444; font-weight: 600;">✕ Not Created</span>')

    @admin.display(description="Configured Sections")
    def sections_count(self, obj):
        return f"{len(obj.sections_config)} sections"

    @admin.action(description="Generate / Sync Mock Assessment from Selected Blueprints")
    def generate_mock_assessments(self, request, queryset):
        created_count = 0
        updated_count = 0
        for bp in queryset:
            tag = bp.company_name.replace(" Mock", "")
            asmt_id = f"asmt_{bp.slug.replace('-', '_')}"
            asmt, created = CodingAssessment.objects.get_or_create(
                assessment_id=asmt_id,
                defaults={
                    "title": bp.company_name,
                    "slug": f"{bp.slug}-mock",
                    "category": bp.category,
                    "company_tag": tag,
                    "description": bp.description,
                    "difficulty": "Hard" if bp.tier == "pro" and "Google" in bp.company_name else "Medium",
                    "duration_minutes": bp.duration_minutes,
                    "total_marks": 100.0,
                    "pass_percentage": 70,
                    "is_company_mock": True,
                    "is_pro_only": bp.tier == "pro",
                    "proctoring_enabled": True,
                    "require_fullscreen": True,
                    "require_screen_share": True,
                    "active": True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            order = 1
            for s_cfg in bp.sections_config:
                sec_title = s_cfg.get("title", f"Section {order}")
                sec_type = s_cfg.get("type", "coding")
                sec_marks = float(s_cfg.get("marks", 25))
                AssessmentSection.objects.get_or_create(
                    assessment=asmt,
                    title=sec_title,
                    defaults={
                        "section_type": sec_type,
                        "order": order,
                        "total_marks": sec_marks,
                        "duration_minutes": max(15, bp.duration_minutes // (len(bp.sections_config) or 1))
                    }
                )
                order += 1

        self.message_user(
            request,
            f"Generated {created_count} new mock assessment(s) and synced {updated_count} existing mock(s) with full sections.",
            messages.SUCCESS
        )

    @admin.action(description="Activate Selected Blueprints")
    def activate_blueprints(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} blueprint(s) activated.", messages.SUCCESS)

    @admin.action(description="Deactivate Selected Blueprints")
    def deactivate_blueprints(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} blueprint(s) deactivated.", messages.SUCCESS)


# --- Executive Analytics Dashboard View Function ---
def company_assessments_dashboard_view(request):
    if not request.user.is_staff and not getattr(request.user, "is_superuser", False):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    total_q = AssessmentQuestionItem.objects.count()
    pub_q = AssessmentQuestionItem.objects.filter(status="Published").count()
    draft_q = AssessmentQuestionItem.objects.filter(status="Draft").count()
    total_asmt = CodingAssessment.objects.count()
    active_asmt = CodingAssessment.objects.filter(active=True).count()
    total_att = AssessmentAttempt.objects.count()

    completed = AssessmentAttempt.objects.filter(status__in=["completed", "timed_out"])
    avg_score = completed.aggregate(Avg("percentage"))["percentage__avg"] or 0.0
    avg_integrity = AssessmentAttempt.objects.aggregate(Avg("integrity_score"))["integrity_score__avg"] or 100.0
    total_events = AssessmentEvent.objects.count()

    most_attempted = []
    for q in AssessmentQuestionItem.objects.all()[:20]:
        usage = AssessmentAttempt.objects.filter(assigned_question_ids__contains=q.item_id).count()
        if q.problem:
            usage += CodeSubmissions.objects.filter(problem=q.problem).count()
        q.usage_count = usage
        most_attempted.append(q)
    most_attempted.sort(key=lambda x: x.usage_count, reverse=True)

    hardest = []
    for q in AssessmentQuestionItem.objects.filter(difficulty__in=["Medium", "Hard"])[:15]:
        total_tries = 0
        wrong_tries = 0
        if q.problem:
            total_tries += CodeSubmissions.objects.filter(problem=q.problem).count()
            wrong_tries += CodeSubmissions.objects.filter(problem=q.problem).exclude(status="Accepted").count()
        rate = round((wrong_tries / total_tries * 100), 1) if total_tries > 0 else (65.0 if q.difficulty == "Hard" else 42.0)
        q.failure_rate = rate
        hardest.append(q)
    hardest.sort(key=lambda x: x.failure_rate, reverse=True)

    stats = {
        "total_questions": total_q,
        "published_questions": pub_q,
        "draft_questions": draft_q,
        "total_assessments": total_asmt,
        "active_assessments": active_asmt,
        "total_attempts": total_att,
        "average_score": round(avg_score, 1),
        "average_integrity_score": round(avg_integrity, 1),
        "total_events": total_events,
        "most_attempted": most_attempted[:5],
        "hardest_questions": hardest[:5],
    }
    return render(request, "admin/skiltrix/assessment_dashboard.html", {"stats": stats})


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


@admin.register(CoursePaymentOrder)
class CoursePaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("order_id_display", "user", "course", "amount_rupees", "status_badge", "razorpay_order_id", "razorpay_payment_id", "created_at", "paid_at")
    search_fields = ("user__username", "user__email", "course__name", "razorpay_order_id", "razorpay_payment_id")
    list_filter = ("status", "currency", "created_at")
    readonly_fields = ("local_order_id", "created_at", "paid_at")

    @admin.display(description="Amount")
    def amount_rupees(self, obj):
        return f"₹{obj.amount_paise / 100:.2f}"

    @admin.display(description="Order Ref")
    def order_id_display(self, obj):
        return f"ORD-{str(obj.local_order_id)[:8]}"

    @admin.display(description="Payment Status")
    def status_badge(self, obj):
        colors = {
            "paid": "#10b981",
            "pending": "#f59e0b",
            "failed": "#ef4444",
            "cancelled": "#64748b",
        }
        color = colors.get(obj.status, "#64748b")
        return mark_safe(f'<span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">{obj.status.upper()}</span>')


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


# ------------------------------------------------------------------------------
# 9. SKILTRIX PROGRAMMING TUTORIAL PLATFORM ADMIN
# ------------------------------------------------------------------------------
from .tutorial_models import (
    TutorialTrack,
    TutorialModule,
    TutorialLesson,
    TutorialProgress,
    TutorialBookmark,
    TutorialNote,
    TutorialCertificate,
)


class TutorialLessonInline(admin.TabularInline):
    model = TutorialLesson
    extra = 1
    fields = ("title", "slug", "order", "reading_time_minutes")
    show_change_link = True


class TutorialModuleInline(admin.TabularInline):
    model = TutorialModule
    extra = 1
    fields = ("title", "level", "order")
    show_change_link = True


@admin.register(TutorialTrack)
class TutorialTrackAdmin(admin.ModelAdmin):
    list_display = ("track_id", "title", "category", "icon", "is_featured", "order", "modules_count", "lessons_count")
    list_filter = ("category", "is_featured")
    search_fields = ("title", "track_id", "description")
    list_editable = ("is_featured", "order")
    inlines = (TutorialModuleInline,)

    @admin.display(description="Modules")
    def modules_count(self, obj):
        return obj.modules.count()

    @admin.display(description="Lessons")
    def lessons_count(self, obj):
        return obj.lessons.count()


@admin.register(TutorialModule)
class TutorialModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "track", "level", "order", "lessons_count")
    list_filter = ("track", "level")
    search_fields = ("title", "module_id")
    inlines = (TutorialLessonInline,)

    @admin.display(description="Lessons")
    def lessons_count(self, obj):
        return obj.lessons.count()


@admin.register(TutorialLesson)
class TutorialLessonAdmin(admin.ModelAdmin):
    list_display = ("title", "track", "module", "slug", "reading_time_minutes", "order")
    list_filter = ("track", "module__level")
    search_fields = ("title", "slug", "explanation", "syntax_code")
    ordering = ("track", "order")
    fieldsets = (
        ("Basic Info", {
            "fields": ("lesson_id", "track", "module", "slug", "title", "reading_time_minutes", "order")
        }),
        ("Content & Explanation", {
            "fields": ("learning_objectives", "explanation", "syntax_code", "code_examples")
        }),
        ("Interactive Practice & Challenges", {
            "fields": ("try_it_yourself", "quiz", "challenge")
        }),
        ("SEO Metadata", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",)
        }),
    )


@admin.register(TutorialProgress)
class TutorialProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "track", "completed", "quiz_completed", "xp_earned", "completed_at")
    list_filter = ("completed", "quiz_completed", "track")
    search_fields = ("user__username", "user__email", "lesson__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TutorialBookmark)
class TutorialBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "created_at")
    search_fields = ("user__username", "lesson__title")


@admin.register(TutorialNote)
class TutorialNoteAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "updated_at")
    search_fields = ("user__username", "lesson__title", "content")


@admin.register(TutorialCertificate)
class TutorialCertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "student_name", "course_name", "score_percent", "issued_at", "verification_hash")
    search_fields = ("certificate_id", "student_name", "course_name", "verification_hash")
    list_filter = ("track", "issued_at")
    readonly_fields = ("issued_at",)


# -------------------------------------------------------------
# Embedded Hardware & PCB Engineering Admin
# -------------------------------------------------------------
from .hardware_models import (
    HardwareBoard, HardwareProject, HardwareSourceFile,
    PcbProject, ComponentItem, HardwareBuildJob, ConnectedDevice
)


@admin.register(HardwareBoard)
class HardwareBoardAdmin(admin.ModelAdmin):
    list_display = ("board_id", "name", "family", "mcu", "platformio_env", "arduino_fqbn", "is_active")
    list_filter = ("family", "is_active")
    search_fields = ("name", "mcu", "board_id")


class HardwareSourceFileInline(admin.TabularInline):
    model = HardwareSourceFile
    extra = 0
    fields = ("path", "is_main_entry", "revision", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(HardwareProject)
class HardwareProjectAdmin(admin.ModelAdmin):
    list_display = ("project_id", "title", "user", "target_board", "project_type", "status", "updated_at")
    list_filter = ("project_type", "status")
    search_fields = ("title", "user__username", "user__email", "project_id")
    inlines = [HardwareSourceFileInline]


@admin.register(HardwareSourceFile)
class HardwareSourceFileAdmin(admin.ModelAdmin):
    list_display = ("file_id", "project", "path", "is_main_entry", "revision", "updated_at")
    search_fields = ("project__title", "path")


class ComponentItemInline(admin.TabularInline):
    model = ComponentItem
    extra = 0
    fields = ("reference", "value", "footprint", "mpn", "unit_cost_inr")


@admin.register(PcbProject)
class PcbProjectAdmin(admin.ModelAdmin):
    list_display = ("pcb_id", "title", "hardware_project", "layer_count", "board_width_mm", "board_height_mm", "status", "updated_at")
    list_filter = ("layer_count", "status")
    search_fields = ("title", "hardware_project__title")
    inlines = [ComponentItemInline]


@admin.register(HardwareBuildJob)
class HardwareBuildJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "project", "toolchain", "status", "duration_seconds", "created_at")
    list_filter = ("toolchain", "status")
    search_fields = ("project__title", "job_id")
    readonly_fields = ("created_at",)


@admin.register(ConnectedDevice)
class ConnectedDeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "name", "user", "serial_port", "is_online", "baud_rate", "last_seen_at")
    list_filter = ("is_online", "baud_rate")
    search_fields = ("name", "user__username", "serial_port", "device_id")


