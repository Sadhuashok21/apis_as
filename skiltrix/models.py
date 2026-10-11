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

    QUESTION_TYPES = (
        ("algorithmic", "Algorithmic Problem"),
        ("debugging", "Backend & Code Debugging"),
        ("sql", "SQL Query Assessment"),
    )

    problem_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="Easy")
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default="algorithmic")
    category = models.CharField(max_length=80, default="DSA", help_text="e.g. DSA, Backend Debugging, SQL, DRF")
    topics = models.JSONField(default=list, blank=True)
    acceptance_rate = models.CharField(max_length=10, default="65%")
    points = models.IntegerField(default=100)
    description = models.TextField(help_text="Detailed problem description with examples in Markdown")
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    expected_complexity = models.CharField(max_length=120, blank=True, default="", help_text="e.g. Time: O(n), Space: O(n)")

    # Error simulation and realistic debugging fields
    error_snippet = models.TextField(blank=True, default="", help_text="Simulated error traceback or terminal error message")
    expected_behavior = models.TextField(blank=True, default="", help_text="Description of expected correct behavior")

    # Limits
    time_limit_seconds = models.FloatField(default=3.0)
    memory_limit_mb = models.IntegerField(default=128)

    # Starter code templates per programming language
    starter_python = models.TextField(blank=True)
    starter_java = models.TextField(blank=True)
    starter_cpp = models.TextField(blank=True)
    starter_c = models.TextField(blank=True)
    starter_javascript = models.TextField(blank=True)
    starter_sql = models.TextField(blank=True)
    solution_code = models.TextField(blank=True)
    explanation = models.TextField(blank=True, default="", help_text="Post-submission educational explanation & optimal complexity breakdown")
    hints = models.JSONField(default=list, blank=True)

    solved_count = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.difficulty}) - {self.category}"

    class Meta:
        managed = True
        db_table = "st_coding_problems"


class TestCases(models.Model):
    TEST_CATEGORIES = (
        ("Sample", "Sample Test Case"),
        ("Basic", "Basic Correctness"),
        ("Edge Case", "Edge Case"),
        ("Boundary", "Boundary Condition"),
        ("Performance", "Performance / Scale"),
        ("Invalid Assumption", "Invalid Assumption"),
    )

    test_case_id = models.CharField(max_length=50, unique=True)
    problem = models.ForeignKey(
        CodingProblems,
        db_column="problem_id",
        to_field="problem_id",
        on_delete=models.CASCADE,
        related_name="test_cases"
    )
    input_data = models.TextField(blank=True, default="")
    expected_output = models.TextField(blank=True, default="")
    is_sample = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    category = models.CharField(max_length=40, choices=TEST_CATEGORIES, default="Basic")
    explanation = models.CharField(max_length=255, blank=True, default="", help_text="Diagnostic reason shown only when failed in hidden tests")
    points = models.IntegerField(default=10)
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_test_cases"
        ordering = ["order"]


# ==============================================================================
# 2.1 COMPANY MOCK & CODING ASSESSMENTS PLATFORM
# ==============================================================================

class CodingAssessment(models.Model):
    CATEGORY_CHOICES = (
        ("Company Mocks", "Company Mocks"),
        ("Coding Assessments", "Coding Assessments"),
        ("Aptitude Assessments", "Aptitude Assessments"),
        ("Technical Assessments", "Technical Assessments"),
        ("Debugging Assessments", "Debugging Assessments"),
        ("SQL Assessments", "SQL Assessments"),
        ("Backend Assessments", "Backend Assessments"),
        ("Frontend Assessments", "Frontend Assessments"),
        ("DSA Assessments", "DSA Assessments"),
        ("Mixed Placement Assessments", "Mixed Placement Assessments"),
    )

    assessment_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Company Mocks")
    company_tag = models.CharField(max_length=60, default="General SDE", help_text="e.g. Amazon-style, Deloitte-style, TCS-style")
    description = models.TextField()
    difficulty = models.CharField(max_length=20, default="Medium", choices=[("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")])
    duration_minutes = models.IntegerField(default=90, help_text="Total assessment countdown time in minutes")
    pass_percentage = models.IntegerField(default=70)
    total_marks = models.FloatField(default=100.0)
    negative_marking_percentage = models.FloatField(default=0.0, help_text="Penalty ratio for incorrect MCQ/Aptitude answers e.g. 0.25")

    # Company Mock & Proctoring Configuration
    is_company_mock = models.BooleanField(default=True)
    is_pro_only = models.BooleanField(default=False, help_text="Gated to SkilTrix Pro subscription")
    proctoring_enabled = models.BooleanField(default=True)
    require_fullscreen = models.BooleanField(default=True)
    require_screen_share = models.BooleanField(default=True)
    max_tab_switches = models.IntegerField(default=3)
    max_fullscreen_exits = models.IntegerField(default=3)
    allow_return_to_previous = models.BooleanField(default=True)
    auto_submit_on_violations = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False, help_text="Randomize option order for multiple-choice questions")

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.company_tag} - {self.duration_minutes}m)"

    class Meta:
        managed = True
        db_table = "st_coding_assessments"
        verbose_name = "Assessment"
        verbose_name_plural = "Assessments"


class CompanyMock(CodingAssessment):
    class Meta:
        proxy = True
        verbose_name = "Company Mock"
        verbose_name_plural = "Company Mocks"


class QuestionPool(models.Model):
    DIFFICULTY_CHOICES = (
        ("Easy", "Easy"),
        ("Medium", "Medium"),
        ("Hard", "Hard"),
    )

    pool_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=80, default="DSA", help_text="e.g. DSA, Django, SQL, Aptitude")
    company_style = models.CharField(max_length=60, default="General SDE")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="Medium")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_question_pools"
        verbose_name = "Question Pool"
        verbose_name_plural = "Question Pools"

    def __str__(self):
        return f"{self.name} ({self.category} - {self.difficulty})"


class AssessmentSection(models.Model):
    SECTION_TYPES = (
        ("aptitude", "Quantitative Aptitude"),
        ("reasoning", "Logical Reasoning"),
        ("coding", "Coding & DSA"),
        ("debugging", "Backend & Code Debugging"),
        ("sql", "SQL Query Assessment"),
        ("technical", "CS Fundamentals & Tech MCQ"),
    )

    section_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    assessment = models.ForeignKey(
        CodingAssessment,
        db_column="assessment_id",
        to_field="assessment_id",
        on_delete=models.CASCADE,
        related_name="sections"
    )
    title = models.CharField(max_length=150)
    section_type = models.CharField(max_length=40, choices=SECTION_TYPES, default="coding")
    order = models.IntegerField(default=1)
    duration_minutes = models.IntegerField(default=0, help_text="Sectional timer in minutes; 0 uses overall exam timer")
    instructions = models.TextField(blank=True, default="")
    total_marks = models.FloatField(default=0.0)

    # Dynamic Question Pool linkage
    question_pool = models.ForeignKey(
        QuestionPool,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_sections",
        help_text="Optional pool from which questions are drawn dynamically"
    )
    pool_question_count = models.IntegerField(
        default=0,
        help_text="Number of questions to randomly pick from this pool for each student attempt"
    )

    class Meta:
        managed = True
        db_table = "st_assessment_sections"
        ordering = ["order"]
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def __str__(self):
        return f"{self.assessment.assessment_id} - Sec {self.order}: {self.title}"


class AssessmentQuestionItem(models.Model):
    QUESTION_TYPES = (
        ("mcq_single", "Multiple Choice"),
        ("mcq_multi", "Multiple Select"),
        ("coding", "Coding"),
        ("sql", "SQL"),
        ("debugging", "Debugging"),
        ("output_prediction", "Output Prediction"),
        ("code_correction", "Code Correction"),
        ("aptitude", "Aptitude"),
        ("reasoning", "Logical Reasoning"),
        ("cs_fundamentals", "CS Fundamentals"),
        ("django_debugging", "Django Debugging"),
        ("backend_debugging", "Backend Debugging"),
        ("numerical", "Numerical Answer"),
    )

    DIFFICULTY_CHOICES = (
        ("Easy", "Easy"),
        ("Medium", "Medium"),
        ("Hard", "Hard"),
    )

    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Published", "Published"),
        ("Archived", "Archived"),
    )

    ASSESSMENT_STYLES = (
        ("General SDE", "General SDE"),
        ("Amazon-style", "Amazon-style"),
        ("Deloitte-style", "Deloitte-style"),
        ("Accenture-style", "Accenture-style"),
        ("Cognizant-style", "Cognizant-style"),
        ("Infosys-style", "Infosys-style"),
        ("TCS-style", "TCS-style"),
        ("Wipro-style", "Wipro-style"),
        ("Capgemini-style", "Capgemini-style"),
        ("Microsoft-style", "Microsoft-style"),
        ("Google-style", "Google-style"),
        ("Custom", "Custom"),
    )

    SECTION_ASSIGNMENTS = (
        ("Aptitude", "Aptitude"),
        ("Logical Reasoning", "Logical Reasoning"),
        ("Technical", "Technical"),
        ("Coding", "Coding"),
        ("Debugging", "Debugging"),
        ("SQL", "SQL"),
        ("CS Fundamentals", "CS Fundamentals"),
        ("Backend", "Backend"),
        ("Frontend", "Frontend"),
        ("DSA", "DSA"),
    )

    item_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    assessment = models.ForeignKey(
        CodingAssessment,
        db_column="assessment_id",
        to_field="assessment_id",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="question_items"
    )
    section = models.ForeignKey(
        AssessmentSection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="items"
    )
    pool = models.ForeignKey(
        QuestionPool,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="questions"
    )
    problem = models.ForeignKey(
        CodingProblems,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessment_item_links"
    )

    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default="mcq_single")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=80, default="DSA")
    subcategory = models.CharField(max_length=80, blank=True, default="")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="Medium")
    company_style = models.CharField(max_length=60, choices=ASSESSMENT_STYLES, default="General SDE")
    section_assignment = models.CharField(max_length=60, choices=SECTION_ASSIGNMENTS, blank=True, default="Coding")
    tags = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=50, blank=True, default="python")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Draft")

    prompt = models.TextField(help_text="Problem statement or question markdown")
    instructions = models.TextField(blank=True, default="")
    marks = models.FloatField(default=10.0)
    negative_marks = models.FloatField(default=0.0)
    time_limit_seconds = models.FloatField(default=3.0)
    memory_limit_mb = models.IntegerField(default=128)
    expected_complexity = models.CharField(max_length=120, blank=True, default="")

    # Question Content Details
    input_format = models.TextField(blank=True, default="")
    output_format = models.TextField(blank=True, default="")
    constraints = models.TextField(blank=True, default="")
    examples = models.JSONField(default=list, blank=True)
    hints = models.JSONField(default=list, blank=True)
    topics = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True, default="")

    # MCQ & Multiple Select
    options = models.JSONField(default=list, blank=True, help_text="List of choices: [{'id': 'A', 'text': '...'}]")
    correct_answers = models.JSONField(default=list, blank=True, help_text="Correct option IDs e.g. ['B'] or ['A', 'C'] - kept backend-only")

    # Coding & Correction
    starter_code = models.TextField(blank=True, default="")
    function_signature = models.CharField(max_length=255, blank=True, default="")
    reference_solution = models.TextField(blank=True, default="", help_text="Confidential Reference Solution - NEVER exposed through student APIs")

    # Django Debugging & Backend Debugging
    buggy_code = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    expected_behavior = models.TextField(blank=True, default="")
    debugging_task = models.TextField(blank=True, default="")
    environment_info = models.CharField(max_length=255, blank=True, default="Django 5.0, Python 3.11, PostgreSQL")
    framework_version = models.CharField(max_length=80, blank=True, default="Django 5.0")
    expected_fix = models.TextField(blank=True, default="")

    # Versioning & Ordering
    order = models.IntegerField(default=1)
    version = models.IntegerField(default=1)
    parent_question = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="versions")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = True
        db_table = "st_assessment_question_items"
        ordering = ["order"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def save(self, *args, **kwargs):
        if not self.item_id:
            import uuid
            self.item_id = f"q_{uuid.uuid4().hex[:12]}"
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.title)[:200] or "question"
            self.slug = f"{base}-{str(self.item_id)[-6:]}"
        super().save(*args, **kwargs)

    def __str__(self):
        asmt_tag = self.assessment.assessment_id if self.assessment else "Pool/Bank"
        return f"{asmt_tag} - Q{self.order}: {self.title} ({self.question_type})"


class AssessmentTestCase(models.Model):
    TEST_TYPES = (
        ("Public", "Public Test Case"),
        ("Hidden", "Hidden Test Case"),
    )

    case_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    question = models.ForeignKey(
        AssessmentQuestionItem,
        on_delete=models.CASCADE,
        related_name="test_cases"
    )
    input_data = models.TextField(blank=True, default="")
    expected_output = models.TextField(blank=True, default="")
    test_type = models.CharField(max_length=20, choices=TEST_TYPES, default="Public")
    weight = models.FloatField(default=10.0)
    is_active = models.BooleanField(default=True)
    explanation = models.CharField(max_length=255, blank=True, default="")
    order = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_assessment_test_cases"
        ordering = ["order"]
        verbose_name = "Test Case"
        verbose_name_plural = "Test Cases"

    def __str__(self):
        return f"TC #{self.order} ({self.test_type}) for {self.question.title}"


class AssessmentQuestion(models.Model):
    item_id = models.CharField(max_length=50, unique=True)
    assessment = models.ForeignKey(
        CodingAssessment,
        db_column="assessment_id",
        to_field="assessment_id",
        on_delete=models.CASCADE,
        related_name="questions"
    )
    problem = models.ForeignKey(
        CodingProblems,
        db_column="problem_id",
        to_field="problem_id",
        on_delete=models.CASCADE,
        related_name="assessment_assignments"
    )
    order = models.IntegerField(default=1)
    marks = models.IntegerField(default=100)

    class Meta:
        managed = True
        db_table = "st_assessment_questions"
        ordering = ["order"]
        unique_together = ("assessment", "problem")


class AssessmentAttempt(models.Model):
    STATUS_CHOICES = (
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("timed_out", "Timed Out"),
        ("disqualified", "Disqualified (Integrity Violations)"),
    )

    attempt_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="assessment_attempts"
    )
    assessment = models.ForeignKey(
        CodingAssessment,
        db_column="assessment_id",
        to_field="assessment_id",
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    total_score = models.FloatField(default=0.0)
    max_possible_score = models.FloatField(default=0.0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)

    # Category skill breakdown (Problem Solving, Data Structures, Algorithms, Debugging, Backend, Aptitude)
    skill_breakdown = models.JSONField(default=dict, blank=True)
    # Section score breakdown { "Coding": { "earned": 40, "total": 50 } }
    section_scores = models.JSONField(default=dict, blank=True)

    # Saved responses
    # { "item_id": ["A"], "prob_id": { "language": "python", "code": "..." } }
    selected_answers = models.JSONField(default=dict, blank=True)
    # Saved code drafts per problem for backward compatibility
    saved_drafts = models.JSONField(default=dict, blank=True)
    # Specific randomized question assignment for this candidate session
    assigned_question_ids = models.JSONField(default=list, blank=True)

    current_section = models.CharField(max_length=100, blank=True, default="")
    current_question_index = models.IntegerField(default=0)

    # Integrity & Proctoring Telemetry
    integrity_score = models.FloatField(default=100.0)
    tab_switch_count = models.IntegerField(default=0)
    fullscreen_exit_count = models.IntegerField(default=0)
    screen_share_stop_count = models.IntegerField(default=0)
    network_disconnect_count = models.IntegerField(default=0)

    class Meta:
        managed = True
        db_table = "st_assessment_attempts"
        ordering = ["-started_at"]
        verbose_name = "Attempt"
        verbose_name_plural = "Attempts"


class AssessmentEvent(models.Model):
    EVENT_TYPES = (
        ("TAB_SWITCH", "Tab Switch / Window Blur"),
        ("FULLSCREEN_EXIT", "Fullscreen Exited"),
        ("SCREEN_SHARE_STARTED", "Screen Sharing Started"),
        ("SCREEN_SHARE_STOPPED", "Screen Sharing Stopped"),
        ("NETWORK_DISCONNECT", "Network Disconnected"),
        ("NETWORK_RECONNECT", "Network Reconnected"),
        ("PAGE_RELOAD", "Page Reload Attempt"),
        ("MULTIPLE_SESSION", "Multiple Sessions Detected"),
        ("SUSPICIOUS_ACTIVITY", "Suspicious Rapid Changes"),
    )

    event_id = models.CharField(max_length=64, primary_key=True)
    attempt = models.ForeignKey(
        AssessmentAttempt,
        db_column="attempt_id",
        to_field="attempt_id",
        on_delete=models.CASCADE,
        related_name="integrity_events"
    )
    user = models.ForeignKey(
        AllUsers,
        db_column="user_id",
        to_field="user_id",
        on_delete=models.CASCADE,
        related_name="assessment_events"
    )
    assessment = models.ForeignKey(
        CodingAssessment,
        db_column="assessment_id",
        to_field="assessment_id",
        on_delete=models.CASCADE,
        related_name="events"
    )
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        managed = True
        db_table = "st_assessment_events"
        ordering = ["-timestamp"]
        verbose_name = "Integrity Event"
        verbose_name_plural = "Integrity Events"

    def __str__(self):
        return f"[{self.event_type}] {self.user.username} at {self.timestamp}"


class CompanyBlueprint(models.Model):
    blueprint_id = models.CharField(max_length=50, unique=True)
    company_name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=50, default="Company Mocks")
    sections_config = models.JSONField(default=list)
    recommended_topics = models.JSONField(default=list)
    duration_minutes = models.IntegerField(default=90)
    tier = models.CharField(max_length=20, default="free", choices=[("free", "Free"), ("pro", "Pro")])
    icon_name = models.CharField(max_length=50, default="briefcase")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "st_company_blueprints"
        verbose_name = "Companies / Blueprint"
        verbose_name_plural = "Companies / Blueprints"

    def __str__(self):
        return f"{self.company_name} ({self.tier})"


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
        verbose_name = "Submission"
        verbose_name_plural = "Submissions"


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
        verbose_name = "Mock Interview Session"
        verbose_name_plural = "Mock Interview Sessions"


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
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.name}"


class CoursePaymentOrder(models.Model):
    STATUSES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(
        AllUsers,
        on_delete=models.CASCADE,
        to_field="user_id",
        db_column="user_id",
        related_name="course_payment_orders",
    )
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        to_field="course_id",
        db_column="course_id",
        related_name="payment_orders",
    )
    enrollment = models.ForeignKey(
        CourseEnrollments,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_orders",
    )
    local_order_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    razorpay_order_id = models.CharField(max_length=80, unique=True)
    razorpay_payment_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=128, null=True, blank=True)
    amount_paise = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "st_course_payment_orders"
        ordering = ["-created_at"]
        verbose_name = "Course Payment Order"
        verbose_name_plural = "Course Payment Orders"

    def __str__(self):
        return f"{self.course.name} - {self.user.username} ({self.status}) [₹{self.amount_paise / 100:.2f}]"


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

# ==============================================================================
# TUTORIAL PLATFORM MODELS
# ==============================================================================
from .tutorial_models import (
    TutorialTrack,
    TutorialModule,
    TutorialLesson,
    TutorialProgress,
    TutorialBookmark,
    TutorialNote,
    TutorialCertificate,
)

# ==============================================================================
# CAREER LEARNING ROADMAPS (MATCHING ANDROID SKILTRIX)
# ==============================================================================
from .roadmap_models import (
    LearningRoadmapProgress,
)

# ==============================================================================
# EMBEDDED SYSTEMS, ARDUINO, ESP32 & PCB ENGINEERING
# ==============================================================================
from .hardware_models import (
    HardwareBoard,
    HardwareProject,
    HardwareSourceFile,
    PcbProject,
    ComponentItem,
    HardwareBuildJob,
    ConnectedDevice,
)
