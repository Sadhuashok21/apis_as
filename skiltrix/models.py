from django.db import models
from sfs.models import AllUsers
import uuid


class CompilerCoupon(models.Model):
    """Admin-managed discounts for compiler purchases."""
    PERCENT = "percent"
    FIXED = "fixed"
    DISCOUNT_TYPES = [(PERCENT, "Percentage"), (FIXED, "Fixed amount (INR)")]

    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.PositiveIntegerField(help_text="Percent points or INR whole rupees")
    compiler = models.CharField(max_length=40, default="abap", help_text="Compiler slug, or * for all")
    active = models.BooleanField(default=True)
    allow_free = models.BooleanField(default=False, help_text="Allow this coupon to cover the full purchase without Razorpay")
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    minimum_amount_paise = models.PositiveIntegerField(default=0)
    maximum_discount_paise = models.PositiveIntegerField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skiltrix_compiler_coupon"
        indexes = [models.Index(fields=["code", "active"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.discount_value < 1:
            raise ValidationError({"discount_value": "Discount must be greater than zero."})
        if self.discount_type == self.PERCENT and self.discount_value > 100:
            raise ValidationError({"discount_value": "Percentage discounts cannot exceed 100%."})
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValidationError({"expires_at": "Expiry must be after the start date."})
        if self.per_user_limit < 1:
            raise ValidationError({"per_user_limit": "Per-user redemption limit must be at least one."})

    def __str__(self):
        return self.code


class CompilerCouponRedemption(models.Model):
    coupon = models.ForeignKey(CompilerCoupon, on_delete=models.PROTECT, related_name="redemptions")
    user = models.ForeignKey(AllUsers, on_delete=models.PROTECT, to_field="user_id", db_column="user_id")
    compiler = models.CharField(max_length=40)
    discount_paise = models.PositiveIntegerField()
    redeemed_at = models.DateTimeField(auto_now_add=True)
    payment_order = models.OneToOneField("CompilerPaymentOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="coupon_redemption")

    class Meta:
        db_table = "skiltrix_coupon_redemption"
        indexes = [models.Index(fields=["coupon", "user"])]


class CompilerProduct(models.Model):
    """Admin-controlled compiler access product and price (amounts in paise)."""
    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    price_paise = models.PositiveIntegerField(default=29900)
    currency = models.CharField(max_length=3, default="INR")
    active = models.BooleanField(default=True)
    one_time_access = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skiltrix_compiler_product"

    def __str__(self):
        return self.name


class CompilerEntitlement(models.Model):
    user = models.ForeignKey(AllUsers, on_delete=models.CASCADE, to_field="user_id", db_column="user_id", related_name="compiler_entitlements")
    product = models.ForeignKey(CompilerProduct, on_delete=models.PROTECT, related_name="entitlements")
    payment_order = models.ForeignKey("CompilerPaymentOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="entitlements")
    status = models.CharField(max_length=12, default="active", choices=[("active", "Active"), ("revoked", "Revoked")])
    starts_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "skiltrix_compiler_entitlement"
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_compiler_entitlement_user_product")]
        indexes = [models.Index(fields=["user", "product", "status"])]


class CompilerPaymentOrder(models.Model):
    STATUSES = [("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("cancelled", "Cancelled")]
    user = models.ForeignKey(AllUsers, on_delete=models.PROTECT, to_field="user_id", db_column="user_id", related_name="compiler_payment_orders")
    product = models.ForeignKey(CompilerProduct, on_delete=models.PROTECT, related_name="payment_orders")
    coupon = models.ForeignKey(CompilerCoupon, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_orders")
    local_order_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    razorpay_order_id = models.CharField(max_length=80, unique=True)
    razorpay_payment_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    base_amount_paise = models.PositiveIntegerField()
    discount_paise = models.PositiveIntegerField(default=0)
    amount_paise = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "skiltrix_compiler_payment_order"
        constraints = [models.UniqueConstraint(fields=["user", "idempotency_key"], name="uniq_payment_idem_per_user")]
        indexes = [models.Index(fields=["user", "status", "created_at"])]

class Companies(models.Model):
    name = models.CharField(max_length=255)
    image = models.TextField()
    description = models.TextField()
    company_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_companies"


class Internship(models.Model):

    name = models.CharField(max_length=255)
    internship_id = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(
        Companies,
        db_column = "company_id",
        on_delete = models.CASCADE,
        to_field='company_id',
        related_name="internship_company",
        null=True,
        blank=True
    )
    is_paid = models.BooleanField(default=0)
    type = models.CharField(max_length=12, default='remote')
    location = models.CharField(blank=True, max_length=100)
    deadline = models.CharField(blank=True, max_length=50)
    price = models.FloatField()
    apply_link = models.TextField(null=True)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_internship"



class Courses(models.Model):
    name = models.CharField(max_length=255)
    image = models.TextField()
    type = models.CharField(max_length=30, default="beginner")
    is_paid = models.BooleanField(default=0)
    price = models.FloatField(default=0)
    course_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="courses_user_id"
    )
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_courses"


class Videos(models.Model):
    title = models.CharField(max_length=105)
    description = models.TextField()
    video = models.CharField(max_length=55)
    image = models.CharField(max_length=50, default="image.webp")
    like = models.IntegerField(default=0)
    share = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    course = models.ForeignKey(
        Courses,
        db_column="course_id",
        to_field="course_id",
        on_delete=models.CASCADE,
        related_name="courses_video_id"
    )
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="courses_videos_user_id"
    )
    video_id =  models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_course_videos"


class Comments(models.Model):

    comment = models.TextField()
    video = models.ForeignKey(
        Videos,
        db_column="video_id",
        to_field="video_id",
        on_delete=models.CASCADE,
        related_name="comment_video_id"

    )

    user = models.ForeignKey(
            AllUsers,
            db_column="user_id",
            to_field="user_id",
            on_delete=models.CASCADE,
            related_name="comment_user_id"
    
        )

    class Meta: 
        managed = True
        db_table = "st_comments"

class Ratings(models.Model):
    rating = models.IntegerField(default=0)
    rating_id = models.CharField(max_length=50)
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        db_column = "course_id",
        to_field="course_id",
        related_name="course_ratings",
    )
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        to_field="user_id",
        db_column="user_id",
        related_name="ratings_user"
    )
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_ratings"
    
class Language(models.Model):
    name = models.CharField(max_length=50)
    language_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="language_user",
    )   
    status = models.CharField(max_length=12, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        db_table = "languages"
        managed = True
    


class CourseCategories(models.Model):
    name = models.CharField(max_length=255)
    category_id = models.CharField(max_length=50, unique=True)
    course = models.ForeignKey(
        Courses,
        db_column = "course_id",
        on_delete = models.CASCADE,
        to_field='course_id',
        related_name="course_categories_course",

    )
    user = models.ForeignKey(
        AllUsers,
        on_delete = models.CASCADE,
        to_field='user_id',
        db_column="user_id",
        related_name="course_categories_user",
    )
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = "course_categories"
        managed = True


class Resumes(models.Model):

    name = models.CharField(max_length=255)
    resume_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="resumes_user",

    )
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: 
        managed = True
        db_table = "st_resumes"


class Skills(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="skills_user",

    )
    skill_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_skills"

class Education(models.Model):
    name = models.CharField(max_length=255)
    year_start = models.IntegerField()
    year_end = models.IntegerField()
    percentage = models.FloatField()
    course_name = models.TextField()
    college_name = models.TextField()
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        on_delete = models.CASCADE,
        to_field='user_id',
        related_name="education_user",

    )
    education_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_education"



class Code(models.Model):
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        to_field = "user_id",
        on_delete = models.CASCADE,
        related_name = "code_user"
    )
    code = models.TextField()
    code_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = True
        db_table = "st_code"




class Likes(models.Model):
    user = models.ForeignKey(
        AllUsers,
        db_column = "user_id",
        to_field = "user_id",
        on_delete = models.CASCADE,
        related_name = "likes_user"
    )
    video = models.ForeignKey(
        Videos,
        db_column = "video_id",
        to_field = "video_id",
        on_delete = models.CASCADE,
        related_name = "likes_video"
    )
    like_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_likes"


# ==============================================================================
# 1. USER PROFILE, GAMIFICATION & ACTIVITY TRACKING
# ==============================================================================

class UserProfile(models.Model):
    user = models.OneToOneField(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="skiltrix_profile"
    )
    headline = models.CharField(max_length=255, blank=True, default="Aspiring Software Engineer")
    bio = models.TextField(blank=True, default="Passionate about software development and solving DSA problems.")
    avatar_url = models.CharField(max_length=500, blank=True, default="")
    github_url = models.URLField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(max_length=255, blank=True, null=True)
    portfolio_url = models.URLField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=50, default="Student")
    total_xp = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    problems_solved = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    courses_enrolled = models.IntegerField(default=0)
    total_learning_minutes = models.IntegerField(default=0)
    last_active_date = models.DateField(auto_now=True)
    status = models.CharField(max_length=20, default="active")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    class Meta:
        managed = True
        db_table = "st_user_profiles"


class Badges(models.Model):
    badge_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default="trophy")
    description = models.TextField()
    category = models.CharField(max_length=50, default="General")
    points = models.IntegerField(default=50)
    criteria_type = models.CharField(max_length=50, default="manual")
    criteria_value = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = "st_badges"


class UserBadges(models.Model):
    user_badge_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="user_badges"
    )
    badge = models.ForeignKey(
        Badges,
        db_column="badge_id",
        to_field="badge_id",
        on_delete=models.CASCADE,
        related_name="awarded_users"
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_user_badges"
        unique_together = ("user", "badge")


class DailyActivity(models.Model):
    activity_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="daily_activities"
    )
    date = models.DateField()
    minutes_spent = models.IntegerField(default=0)
    problems_solved = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    xp_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_daily_activity"
        unique_together = ("user", "date")


# ==============================================================================
# 2. CODING, PRACTICE PROBLEMS & COMPILER
# ==============================================================================

class CodingProblems(models.Model):
    DIFFICULTY_CHOICES = (
        ("Easy", "Easy"),
        ("Medium", "Medium"),
        ("Hard", "Hard"),
    )

    problem_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="Easy")
    topics = models.JSONField(default=list, blank=True)
    acceptance_rate = models.CharField(max_length=10, default="65%")
    points = models.IntegerField(default=100)
    description = models.TextField(help_text="Detailed problem description with examples in Markdown")
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    
    # Starter code templates per programming language
    starter_python = models.TextField(blank=True)
    starter_java = models.TextField(blank=True)
    starter_cpp = models.TextField(blank=True)
    starter_c = models.TextField(blank=True)
    starter_javascript = models.TextField(blank=True)
    solution_code = models.TextField(blank=True)
    hints = models.JSONField(default=list, blank=True)
    
    solved_count = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.difficulty})"

    class Meta:
        managed = True
        db_table = "st_coding_problems"


class TestCases(models.Model):
    test_case_id = models.CharField(max_length=50, unique=True)
    problem = models.ForeignKey(
        CodingProblems,
        db_column="problem_id",
        to_field="problem_id",
        on_delete=models.CASCADE,
        related_name="test_cases"
    )
    input_data = models.TextField()
    expected_output = models.TextField()
    is_sample = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    points = models.IntegerField(default=10)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_test_cases"
        ordering = ["order"]


class CodeSubmissions(models.Model):
    STATUS_CHOICES = (
        ("Accepted", "Accepted"),
        ("Wrong Answer", "Wrong Answer"),
        ("Time Limit Exceeded", "Time Limit Exceeded"),
        ("Memory Limit Exceeded", "Memory Limit Exceeded"),
        ("Runtime Error", "Runtime Error"),
        ("Compile Error", "Compile Error"),
        ("Pending", "Pending"),
    )

    submission_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="coding_submissions"
    )
    problem = models.ForeignKey(
        CodingProblems,
        db_column="problem_id",
        to_field="problem_id",
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    language = models.CharField(max_length=20)
    code = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Pending")
    passed_test_cases = models.IntegerField(default=0)
    total_test_cases = models.IntegerField(default=0)
    execution_time_ms = models.FloatField(default=0.0)
    memory_kb = models.FloatField(default=0.0)
    error_message = models.TextField(null=True, blank=True)
    score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.status})"

    class Meta:
        managed = True
        db_table = "st_code_submissions"
        ordering = ["-created_at"]


class UserProblemStatus(models.Model):
    status_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="problem_statuses"
    )
    problem = models.ForeignKey(
        CodingProblems,
        db_column="problem_id",
        to_field="problem_id",
        on_delete=models.CASCADE,
        related_name="user_statuses"
    )
    solved = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    best_submission = models.ForeignKey(
        CodeSubmissions,
        db_column="submission_id",
        to_field="submission_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="best_for_status"
    )
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_user_problem_status"
        unique_together = ("user", "problem")


class CompilerSnippets(models.Model):
    snippet_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="compiler_snippets"
    )
    title = models.CharField(max_length=255, default="Untitled Snippet")
    language = models.CharField(max_length=30, default="python")
    code = models.TextField()
    stdin = models.TextField(blank=True)
    stdout = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_compiler_snippets"


class SyntaxMatrix(models.Model):
    entry_id = models.CharField(max_length=50, unique=True)
    topic = models.CharField(max_length=100)
    category = models.CharField(max_length=50, default="Syntax Basics")
    python_code = models.TextField()
    java_code = models.TextField()
    cpp_code = models.TextField()
    c_code = models.TextField()
    javascript_code = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    order = models.IntegerField(default=1)

    class Meta:
        managed = True
        db_table = "st_syntax_matrix"
        ordering = ["order"]


# ==============================================================================
# 3. QUIZZES & ASSESSMENT QUESTIONS
# ==============================================================================

class Quizzes(models.Model):
    quiz_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    topic = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=20, default="Beginner")
    duration_minutes = models.IntegerField(default=15)
    passing_score = models.IntegerField(default=70)
    total_questions = models.IntegerField(default=10)
    points = models.IntegerField(default=100)
    icon = models.CharField(max_length=50, default="target")
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.topic})"

    class Meta:
        managed = True
        db_table = "st_quizzes"


class QuizQuestions(models.Model):
    question_id = models.CharField(max_length=50, unique=True)
    quiz = models.ForeignKey(
        Quizzes,
        db_column="quiz_id",
        to_field="quiz_id",
        on_delete=models.CASCADE,
        related_name="questions"
    )
    question_text = models.TextField()
    code_snippet = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=20, default="python", blank=True)
    explanation = models.TextField(blank=True)
    points = models.IntegerField(default=10)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}"

    class Meta:
        managed = True
        db_table = "st_quiz_questions"
        ordering = ["order"]


class QuizOptions(models.Model):
    option_id = models.CharField(max_length=50, unique=True)
    question = models.ForeignKey(
        QuizQuestions,
        db_column="question_id",
        to_field="question_id",
        on_delete=models.CASCADE,
        related_name="options"
    )
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.option_text[:40]} ({'Correct' if self.is_correct else 'Wrong'})"

    class Meta:
        managed = True
        db_table = "st_quiz_options"
        ordering = ["order"]


class QuizAttempts(models.Model):
    attempt_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        Quizzes,
        db_column="quiz_id",
        to_field="quiz_id",
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    time_taken_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_quiz_attempts"
        ordering = ["-created_at"]


class QuizUserAnswers(models.Model):
    user_answer_id = models.CharField(max_length=50, unique=True)
    attempt = models.ForeignKey(
        QuizAttempts,
        db_column="attempt_id",
        to_field="attempt_id",
        on_delete=models.CASCADE,
        related_name="user_answers"
    )
    question = models.ForeignKey(
        QuizQuestions,
        db_column="question_id",
        to_field="question_id",
        on_delete=models.CASCADE,
        related_name="user_answers"
    )
    selected_option = models.ForeignKey(
        QuizOptions,
        db_column="option_id",
        to_field="option_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = "st_quiz_user_answers"


# ==============================================================================
# 4. INTERVIEW PREPARATION
# ==============================================================================

class InterviewCategories(models.Model):
    category_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default="target")
    count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        managed = True
        db_table = "st_interview_categories"


class InterviewQuestions(models.Model):
    interview_id = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        InterviewCategories,
        db_column="category_id",
        to_field="category_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions"
    )
    topic = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=20, default="Common")
    question = models.TextField()
    short_answer = models.TextField()
    explanation = models.TextField()
    code = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=20, default="python", blank=True)
    tags = models.JSONField(default=list, blank=True)
    frequent_companies = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic}: {self.question[:50]}"

    class Meta:
        managed = True
        db_table = "st_interview_questions"


class CompanyRoadmaps(models.Model):
    roadmap_id = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(
        Companies,
        db_column="company_id",
        to_field="company_id",
        on_delete=models.CASCADE,
        related_name="roadmaps"
    )
    step_number = models.IntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, default="Fundamentals")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_company_roadmaps"
        ordering = ["step_number"]


class MockInterviewSessions(models.Model):
    session_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="mock_interviews"
    )
    role_track = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=20, default="Intermediate")
    total_score = models.IntegerField(default=0)
    feedback = models.TextField(blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_mock_interviews"


# ==============================================================================
# 5. COMMUNITY & DISCUSSIONS
# ==============================================================================

class Discussions(models.Model):
    discussion_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="discussions"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    code = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=20, default="python", blank=True)
    tag = models.CharField(max_length=50, default="Python")
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    is_solved = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        managed = True
        db_table = "st_discussions"
        ordering = ["-created_at"]


class DiscussionReplies(models.Model):
    reply_id = models.CharField(max_length=50, unique=True)
    discussion = models.ForeignKey(
        Discussions,
        db_column="discussion_id",
        to_field="discussion_id",
        on_delete=models.CASCADE,
        related_name="replies"
    )
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="discussion_replies"
    )
    content = models.TextField()
    code = models.TextField(null=True, blank=True)
    likes_count = models.IntegerField(default=0)
    is_accepted = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_discussion_replies"
        ordering = ["created_at"]


class DiscussionLikes(models.Model):
    like_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="discussion_likes"
    )
    discussion = models.ForeignKey(
        Discussions,
        db_column="discussion_id",
        to_field="discussion_id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="likes"
    )
    reply = models.ForeignKey(
        DiscussionReplies,
        db_column="reply_id",
        to_field="reply_id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_discussion_likes"


class DiscussionBookmarks(models.Model):
    bookmark_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="discussion_bookmarks"
    )
    discussion = models.ForeignKey(
        Discussions,
        db_column="discussion_id",
        to_field="discussion_id",
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_discussion_bookmarks"
        unique_together = ("user", "discussion")


# ==============================================================================
# 6. COURSES & MEDIA CURRICULUM EXTENSIONS
# ==============================================================================

class CourseModules(models.Model):
    module_id = models.CharField(max_length=50, unique=True)
    course = models.ForeignKey(
        Courses,
        db_column="course_id",
        to_field="course_id",
        on_delete=models.CASCADE,
        related_name="modules"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_course_modules"
        ordering = ["order"]


class CourseLessons(models.Model):
    LESSON_TYPES = (
        ("video", "Video"),
        ("article", "Reading"),
        ("exercise", "Coding Exercise"),
        ("quiz", "Quiz"),
    )

    lesson_id = models.CharField(max_length=50, unique=True)
    module = models.ForeignKey(
        CourseModules,
        db_column="module_id",
        to_field="module_id",
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default="video")
    duration_minutes = models.IntegerField(default=10)
    is_free_preview = models.BooleanField(default=False)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_course_lessons"
        ordering = ["order"]


class CourseEnrollments(models.Model):
    enrollment_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="course_enrollments"
    )
    course = models.ForeignKey(
        Courses,
        db_column="course_id",
        to_field="course_id",
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    progress_percent = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "st_course_enrollments"
        unique_together = ("user", "course")


class VideoSubtitles(models.Model):
    subtitle_id = models.CharField(max_length=50, unique=True)
    video = models.ForeignKey(
        Videos,
        db_column="video_id",
        to_field="video_id",
        on_delete=models.CASCADE,
        related_name="subtitles"
    )
    language_code = models.CharField(max_length=10, default="en")
    label = models.CharField(max_length=50, default="English")
    vtt_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_video_subtitles"


class VideoProgress(models.Model):
    progress_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="video_progress"
    )
    video = models.ForeignKey(
        Videos,
        db_column="video_id",
        to_field="video_id",
        on_delete=models.CASCADE,
        related_name="user_progress"
    )
    watched_seconds = models.IntegerField(default=0)
    total_seconds = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    last_watched_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "st_video_progress"
        unique_together = ("user", "video")


class VideoNotes(models.Model):
    note_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="video_notes"
    )
    video = models.ForeignKey(
        Videos,
        db_column="video_id",
        to_field="video_id",
        on_delete=models.CASCADE,
        related_name="notes"
    )
    timestamp_seconds = models.IntegerField(default=0)
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_video_notes"


# ==============================================================================
# 7. INTERNSHIP APPLICATIONS & CAREER HUB
# ==============================================================================

class InternshipApplications(models.Model):
    STATUS_CHOICES = (
        ("applied", "Applied"),
        ("under_review", "Under Review"),
        ("shortlisted", "Shortlisted"),
        ("interview", "Interview Scheduled"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    application_id = models.CharField(max_length=50, unique=True)
    internship = models.ForeignKey(
        Internship,
        db_column="internship_id",
        to_field="internship_id",
        on_delete=models.CASCADE,
        related_name="applications"
    )
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="internship_applications"
    )
    resume = models.ForeignKey(
        Resumes,
        db_column="resume_id",
        to_field="resume_id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    cover_letter = models.TextField(blank=True)
    portfolio_url = models.URLField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="applied")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_internship_applications"
        unique_together = ("internship", "user")


class SavedInternships(models.Model):
    saved_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="saved_internships"
    )
    internship = models.ForeignKey(
        Internship,
        db_column="internship_id",
        to_field="internship_id",
        on_delete=models.CASCADE,
        related_name="saved_by_users"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_saved_internships"
        unique_together = ("user", "internship")


# ==============================================================================
# 8. NOTIFICATIONS & ALERTS
# ==============================================================================

class Notifications(models.Model):
    CATEGORY_CHOICES = (
        ("Achievements", "Achievements"),
        ("Community", "Community"),
        ("Learning", "Learning"),
        ("System", "System"),
        ("Internships", "Internships"),
    )

    notification_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="user_notifications"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="System")
    icon = models.CharField(max_length=50, default="bell")
    read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} -> {self.user.username}"

    class Meta:
        managed = True
        db_table = "st_notifications"
        ordering = ["-created_at"]

# ==============================================================================
# MODEL ALIASES
# ==============================================================================
Company = Companies
Course = Courses
Video = Videos
Comment = Comments
Rating = Ratings
CourseCategory = CourseCategories
Resume = Resumes
Skill = Skills
Badge = Badges
UserBadge = UserBadges
CodingProblem = CodingProblems
TestCase = TestCases
CodeSubmission = CodeSubmissions
Quiz = Quizzes
QuizQuestion = QuizQuestions
QuizOption = QuizOptions
QuizAttempt = QuizAttempts
QuizAnswer = QuizUserAnswers
InterviewCategory = InterviewCategories
InterviewQuestion = InterviewQuestions
Discussion = Discussions
DiscussionReply = DiscussionReplies
DiscussionLike = DiscussionLikes
DiscussionBookmark = DiscussionBookmarks
CourseModule = CourseModules
CourseLesson = CourseLessons
Lesson = CourseLessons
CourseEnrollment = CourseEnrollments
VideoSubtitle = VideoSubtitles
VideoNote = VideoNotes
InternshipApplication = InternshipApplications
SavedInternship = SavedInternships
Notification = Notifications


# ==============================================================================
# CODELAB MODELS
# ==============================================================================
from .codelab_models import (
    CodeProject,
    ProjectFile,
    ExecutionJob,
    SubmissionResult,
    WorkspaceSession,
    DatabaseWorkspace,
    ProjectDependency,
    ProjectActivity,
)

# ==============================================================================
# SAP ABAP LAB MODELS
# ==============================================================================
from .abap_models import (
    ABAPProject,
    ABAPSourceFile,
    ABAPExercise,
    ABAPTestCase,
    ABAPSubmission,
    SAPSystemConnection,
    ABAPDictionaryTable,
    ABAPLearningProgress,
)

