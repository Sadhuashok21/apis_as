import uuid
from django.db import models
from django.conf import settings


def generate_uuid():
    return uuid.uuid4().hex


class ASAIModel(models.Model):
    """
    Registry of configured AI models available to ASAI (LLM, Vision, Coder, Image, etc.)
    """
    model_id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)                     # e.g. "ASAI Pro", "ASAI Swift", "ASAI Vision XL", "ASAI Code"
    ollama_model = models.CharField(max_length=100, blank=True) # Underlying Ollama model name, e.g. "qwen2.5:3b"
    tag = models.CharField(max_length=50, blank=True)           # e.g. "Most capable", "Fastest", "Creative", "Specialist"
    description = models.TextField(blank=True)
    capabilities = models.JSONField(default=list, blank=True)   # e.g. ["chat", "vision", "code", "image"]
    context_window = models.IntegerField(default=128000)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "asai_models"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.model_id})"


class ASAIConversation(models.Model):
    """
    User conversation container for chat and multi-turn threads
    """
    conversation_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asai_conversations",
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True, help_text="Guest/session identifier")
    title = models.CharField(max_length=255, default="New conversation")
    model = models.CharField(max_length=100, default="qwen2.5:3b")
    system_prompt = models.TextField(blank=True, default="")
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_conversations"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.conversation_id[:8]})"


class ASAIMessage(models.Model):
    """
    Individual user or assistant message in an ASAIConversation
    """
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    )

    message_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    conversation = models.ForeignKey(
        ASAIConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    model_used = models.CharField(max_length=100, blank=True, default="")
    tokens = models.IntegerField(default=0)
    rating = models.SmallIntegerField(default=0, help_text="+1 thumb up, -1 thumb down, 0 neutral")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:40]}"


class ASAIImageGenerationJob(models.Model):
    """
    Background job tracking image generation dispatched to ComfyUI / local GPU
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("QUEUED", "Queued"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    )

    job_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_image_jobs"
    )
    session_key = models.CharField(max_length=64, blank=True)
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, default="")
    model_name = models.CharField(max_length=100, default="sd15")
    aspect_ratio = models.CharField(max_length=20, default="4:3")
    width = models.IntegerField(default=1024)
    height = models.IntegerField(default=768)
    num_images = models.IntegerField(default=1)
    init_image = models.FileField(upload_to="asai/uploads/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    progress = models.IntegerField(default=0)
    current_step = models.CharField(max_length=100, blank=True, default="")
    comfy_prompt_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "asai_image_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.job_id[:8]} - {self.status} ({self.progress}%)"


class ASAIGeneratedMedia(models.Model):
    """
    Persisted images, videos, or audio generated by ASAI
    """
    MEDIA_CHOICES = (
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
    )

    media_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    job = models.ForeignKey(
        ASAIImageGenerationJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_media"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_media"
    )
    media_type = models.CharField(max_length=20, choices=MEDIA_CHOICES, default="image")
    file = models.FileField(upload_to="asai/generated/")
    file_url = models.CharField(max_length=500, blank=True)
    prompt = models.TextField(blank=True)
    aspect_ratio = models.CharField(max_length=20, blank=True, default="")
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_generated_media"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.media_type.capitalize()} {self.media_id[:8]}"


class ASAIDocument(models.Model):
    """
    User uploaded documents (PDF, DOCX, CSV, XLSX, TXT) for Document AI
    """
    doc_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_documents"
    )
    session_key = models.CharField(max_length=64, blank=True)
    file = models.FileField(upload_to="asai/documents/")
    file_url = models.CharField(max_length=500, blank=True)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)
    file_size_bytes = models.BigIntegerField(default=0)
    extracted_text = models.TextField(blank=True, default="")
    summary = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.file_type})"


class ASAIVideoGenerationJob(models.Model):
    """
    Provider-based video generation job tracking
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("QUEUED", "Queued"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("UNAVAILABLE", "Unavailable"),
    )

    job_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_video_jobs"
    )
    prompt = models.TextField()
    source_image = models.FileField(upload_to="asai/video_sources/", null=True, blank=True)
    duration_seconds = models.IntegerField(default=8)
    aspect_ratio = models.CharField(max_length=20, default="16:9")
    motion_strength = models.CharField(max_length=50, default="Natural")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    progress = models.IntegerField(default=0)
    result_video = models.FileField(upload_to="asai/videos/", null=True, blank=True)
    result_video_url = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "asai_video_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Video Job {self.job_id[:8]} - {self.status}"


class ASAIUserSettings(models.Model):
    """
    User-specific preferences for the ASAI interface and model behavior
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asai_settings"
    )
    theme = models.CharField(max_length=10, default="dark", choices=[("light", "Light"), ("dark", "Dark")])
    default_model = models.CharField(max_length=100, default="ASAI Pro")
    language = models.CharField(max_length=50, default="English (US)")
    chat_history_enabled = models.BooleanField(default=True)
    suggested_prompts_enabled = models.BooleanField(default=True)
    voice_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "asai_user_settings"

    def __str__(self):
        return f"Settings for user {self.user_id}"


class ASAIUsageLog(models.Model):
    """
    Audit and performance metrics logging for inference requests
    """
    log_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_usage_logs"
    )
    feature = models.CharField(max_length=50) # "chat", "image", "vision", "code", "document", "voice", "video"
    model_used = models.CharField(max_length=100, blank=True, default="")
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="SUCCESS")
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_usage_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feature} by {self.user_id or 'anon'} - {self.duration_ms}ms"


# ==============================================================================
# SUBSCRIPTION & BILLING MODELS
# ==============================================================================

class ASAISubscriptionPlan(models.Model):
    """
    Configurable subscription tiers for ASAI (Free, Plus, Pro, Business).
    Stores pricing, quotas, limits, and feature access.
    """
    TIER_CHOICES = (
        ("free", "ASAI Free"),
        ("plus", "ASAI Plus"),
        ("pro", "ASAI Pro"),
        ("business", "ASAI Business"),
    )

    plan_id = models.CharField(max_length=50, primary_key=True) # "free", "plus", "pro", "business"
    name = models.CharField(max_length=100)                     # "ASAI Free", "ASAI Plus", "ASAI Pro", "ASAI Business"
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    tagline = models.CharField(max_length=255, blank=True)
    badge = models.CharField(max_length=50, blank=True)         # "Recommended", "For Teams", etc.
    price_monthly_inr = models.IntegerField(default=0)          # ₹0, ₹299, ₹799, 0 (custom)
    price_yearly_inr = models.IntegerField(default=0)           # ₹0, ₹2990, ₹7990, 0 (custom)
    yearly_discount_percent = models.IntegerField(default=17)   # e.g. 17% savings
    daily_message_limit = models.IntegerField(default=20)       # daily messages allowed
    monthly_image_credits = models.IntegerField(default=5)      # monthly image credits
    max_doc_size_mb = models.IntegerField(default=5)            # max document upload size in MB
    monthly_doc_limit = models.IntegerField(default=5)          # monthly document uploads allowed
    monthly_video_limit = models.IntegerField(default=0)        # monthly video generations allowed
    context_window = models.IntegerField(default=256)           # context length in tokens
    has_advanced_code = models.BooleanField(default=False)
    has_priority_processing = models.BooleanField(default=False)
    has_voice = models.BooleanField(default=False)
    has_team_workspace = models.BooleanField(default=False)
    features_highlight = models.JSONField(default=list, blank=True)
    cta_text = models.CharField(max_length=50, default="Get Started")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "asai_subscription_plans"
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} (₹{self.price_monthly_inr}/mo)"


class ASAIUserSubscription(models.Model):
    """
    Active subscription contract for a user or session identifier.
    """
    STATUS_CHOICES = (
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("past_due", "Past Due"),
        ("trialing", "Trialing"),
        ("expired", "Expired"),
    )
    CYCLE_CHOICES = (
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    subscription_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_subscriptions"
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    plan = models.ForeignKey(
        ASAISubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )
    billing_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default="monthly")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    current_period_start = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "asai_user_subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        user_label = self.user.username if self.user else self.session_key
        return f"{user_label} - {self.plan.name} ({self.status})"


class ASAIPaymentTransaction(models.Model):
    """
    Audit log of financial transactions and Razorpay orders for subscriptions.
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    )
    GATEWAY_CHOICES = (
        ("RAZORPAY", "Razorpay"),
        ("INTERNAL_TEST", "Internal Test Mode"),
    )

    transaction_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_transactions"
    )
    session_key = models.CharField(max_length=64, blank=True)
    subscription = models.ForeignKey(
        ASAIUserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    plan = models.ForeignKey(
        ASAISubscriptionPlan,
        on_delete=models.PROTECT
    )
    billing_cycle = models.CharField(max_length=20, default="monthly")
    amount_paise = models.PositiveIntegerField(help_text="Amount in paise (e.g. 79900 = ₹799.00)")
    currency = models.CharField(max_length=10, default="INR")
    gateway = models.CharField(max_length=30, choices=GATEWAY_CHOICES, default="RAZORPAY")
    razorpay_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=100, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    failure_reason = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "asai_payment_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Txn {self.transaction_id[:8]} - ₹{self.amount_paise / 100:.2f} ({self.status})"


class ASAIUsageAllowance(models.Model):
    """
    Per-user / per-session real-time usage tracking counters.
    Auto-resets daily message count and monthly credits.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_usage_allowance"
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    daily_messages_used = models.IntegerField(default=0)
    last_message_date = models.DateField(auto_now=True)
    monthly_images_used = models.IntegerField(default=0)
    monthly_docs_used = models.IntegerField(default=0)
    monthly_videos_used = models.IntegerField(default=0)
    last_month_reset = models.DateField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "asai_usage_allowance"

    def __str__(self):
        ident = self.user.username if self.user else self.session_key
        return f"Usage for {ident}: {self.daily_messages_used} msgs today"


class ASAIBusinessOrganization(models.Model):
    """
    Organization container for ASAI Business plan customers.
    """
    org_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    name = models.CharField(max_length=150)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asai_owned_orgs"
    )
    subscription = models.ForeignKey(
        ASAIUserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    seats_allocated = models.IntegerField(default=5)
    billing_email = models.EmailField(blank=True)
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "asai_business_organizations"

    def __str__(self):
        return f"Org {self.name} ({self.org_id[:8]})"


class ASAIOrganizationMember(models.Model):
    """
    Members and roles inside an ASAIBusinessOrganization.
    """
    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    )
    org = models.ForeignKey(
        ASAIBusinessOrganization,
        on_delete=models.CASCADE,
        related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asai_org_memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "asai_org_members"
        unique_together = ("org", "user")

    def __str__(self):
        return f"{self.user.username} in {self.org.name} ({self.role})"


class ASAICoupon(models.Model):
    """
    Promotional discounts applied to subscriptions.
    """
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(default=0) # e.g. 20 for 20%
    discount_amount_paise = models.PositiveIntegerField(default=0) # fixed discount
    valid_from = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(default=100)
    times_redeemed = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = "asai_coupons"

    def __str__(self):
        return f"Coupon {self.code} ({self.discount_percent}% off)"


# ==============================================================================
# ASAI FLOW – ADVANCED AI VIDEO CREATION & FILMMAKING STUDIO MODELS
# ==============================================================================

class ASAIProject(models.Model):
    """
    Project-based filmmaking workspace container.
    """
    project_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_flow_projects"
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    name = models.CharField(max_length=255, default="Untitled Film Project")
    description = models.TextField(blank=True, default="")
    thumbnail = models.FileField(upload_to="asai/flow/thumbnails/", null=True, blank=True)
    aspect_ratio = models.CharField(max_length=20, default="16:9") # 16:9, 9:16, 1:1, 2.39:1
    target_resolution = models.CharField(max_length=20, default="720p") # 512p, 720p, 1080p
    frame_rate = models.IntegerField(default=24) # 24, 30 fps
    default_style = models.CharField(max_length=100, default="Cinematic")
    auto_save_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_flow_projects"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.project_id[:8]})"


class ASAICharacter(models.Model):
    """
    Reusable character profile with reference images for character consistency.
    """
    character_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    project = models.ForeignKey(
        ASAIProject,
        on_delete=models.CASCADE,
        related_name="characters",
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_flow_characters"
    )
    session_key = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=150)
    appearance_prompt = models.TextField(blank=True, help_text="Physical features, hair, eyes, facial traits")
    clothing_prompt = models.TextField(blank=True, help_text="Default attire and wardrobe")
    physical_attributes = models.JSONField(default=dict, blank=True)
    reference_image = models.FileField(upload_to="asai/flow/characters/", null=True, blank=True)
    reference_image_url = models.CharField(max_length=500, blank=True)
    voice_ref = models.CharField(max_length=100, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "asai_flow_characters"
        ordering = ["name"]

    def __str__(self):
        return f"Character: {self.name}"


class ASAIAsset(models.Model):
    """
    Reusable media asset reference (Character, Location, Style, Frame, Audio, Video).
    """
    ASSET_TYPE_CHOICES = (
        ("character_ref", "Character Reference"),
        ("location_ref", "Location Reference"),
        ("style_ref", "Style Reference"),
        ("lighting_ref", "Lighting Reference"),
        ("first_frame", "First Frame"),
        ("last_frame", "Last Frame"),
        ("video_clip", "Video Clip"),
        ("audio", "Audio Track"),
    )

    asset_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    project = models.ForeignKey(
        ASAIProject,
        on_delete=models.CASCADE,
        related_name="assets",
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="asai_flow_assets"
    )
    session_key = models.CharField(max_length=64, blank=True)
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPE_CHOICES, default="style_ref")
    name = models.CharField(max_length=255, default="Untitled Asset")
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to="asai/flow/assets/")
    file_url = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_flow_assets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.asset_type})"


class ASAIScene(models.Model):
    """
    Storyboard and timeline scene representation.
    """
    scene_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    project = models.ForeignKey(
        ASAIProject,
        on_delete=models.CASCADE,
        related_name="scenes"
    )
    order = models.IntegerField(default=0, db_index=True)
    title = models.CharField(max_length=200, default="Scene")
    description = models.TextField(blank=True, default="")
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, default="")
    characters = models.ManyToManyField(ASAICharacter, blank=True, related_name="scenes")
    camera_framing = models.CharField(max_length=50, default="Medium shot")
    camera_movement = models.CharField(max_length=50, default="Static")
    visual_style = models.CharField(max_length=100, blank=True, default="Cinematic")
    lighting = models.CharField(max_length=100, blank=True, default="Natural cinematic")
    environment = models.CharField(max_length=150, blank=True, default="")
    starting_frame = models.FileField(upload_to="asai/flow/frames/", null=True, blank=True)
    starting_frame_url = models.CharField(max_length=500, blank=True)
    ending_frame = models.FileField(upload_to="asai/flow/frames/", null=True, blank=True)
    ending_frame_url = models.CharField(max_length=500, blank=True)
    active_clip = models.FileField(upload_to="asai/flow/clips/", null=True, blank=True)
    active_clip_url = models.CharField(max_length=500, blank=True)
    duration_seconds = models.FloatField(default=4.0)
    timeline_position_ms = models.IntegerField(default=0)
    audio_track = models.FileField(upload_to="asai/flow/audio/", null=True, blank=True)
    audio_track_url = models.CharField(max_length=500, blank=True)
    subtitle_text = models.TextField(blank=True, default="")
    transition_type = models.CharField(max_length=50, default="cut") # cut, crossfade, dissolve
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "asai_flow_scenes"
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.project.name} - Scene {self.order + 1}: {self.title}"


class ASAIFlowJob(models.Model):
    """
    Background video generation, extension, and editing job tracking.
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("QUEUED", "Queued"),
        ("VALIDATING", "Validating"),
        ("PREPARING", "Preparing"),
        ("GENERATING", "Generating"),
        ("PROCESSING", "Processing"),
        ("ASSEMBLING", "Assembling"),
        ("RENDERING", "Rendering"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    )

    MODE_CHOICES = (
        ("text_to_video", "Text to Video"),
        ("image_to_video", "Image to Video"),
        ("frames_to_video", "First & Last Frames to Video"),
        ("video_edit", "Video to Video Edit"),
        ("video_extend", "Clip Extension"),
        ("scene_compose", "Scene Composition"),
    )

    job_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    project = models.ForeignKey(
        ASAIProject,
        on_delete=models.CASCADE,
        related_name="flow_jobs",
        null=True,
        blank=True
    )
    scene = models.ForeignKey(
        ASAIScene,
        on_delete=models.SET_NULL,
        related_name="flow_jobs",
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_flow_jobs"
    )
    session_key = models.CharField(max_length=64, blank=True)
    provider_name = models.CharField(max_length=100, default="comfyui_animatediff")
    mode = models.CharField(max_length=30, choices=MODE_CHOICES, default="text_to_video")
    prompt = models.TextField()
    negative_prompt = models.TextField(blank=True, default="")
    generation_settings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    progress = models.IntegerField(default=0)
    current_stage = models.CharField(max_length=100, blank=True, default="")
    error_details = models.TextField(blank=True, default="")
    vram_allocated_mb = models.FloatField(default=0.0)
    result_video = models.FileField(upload_to="asai/flow/outputs/", null=True, blank=True)
    result_video_url = models.CharField(max_length=500, blank=True)
    extracted_frames = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "asai_flow_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Flow Job {self.job_id[:8]} ({self.mode}) - {self.status}"


class ASAIVideoVersion(models.Model):
    """
    Version history stack preserving previous generations and edits.
    """
    version_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    scene = models.ForeignKey(
        ASAIScene,
        on_delete=models.CASCADE,
        related_name="versions"
    )
    asset = models.ForeignKey(
        ASAIAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions"
    )
    version_number = models.PositiveIntegerField(default=1)
    prompt = models.TextField()
    model_used = models.CharField(max_length=100, default="")
    generation_settings = models.JSONField(default=dict, blank=True)
    output_file = models.FileField(upload_to="asai/flow/versions/")
    output_url = models.CharField(max_length=500, blank=True)
    duration_seconds = models.FloatField(default=4.0)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        managed = True
        db_table = "asai_flow_versions"
        ordering = ["-version_number"]

    def __str__(self):
        return f"Version v{self.version_number} for Scene {self.scene_id[:8]}"


class ASAIExport(models.Model):
    """
    Final rendered multi-scene video exports.
    """
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("RENDERING", "Rendering"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    )

    export_id = models.CharField(max_length=64, unique=True, default=generate_uuid, db_index=True)
    project = models.ForeignKey(
        ASAIProject,
        on_delete=models.CASCADE,
        related_name="exports"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asai_flow_exports"
    )
    session_key = models.CharField(max_length=64, blank=True)
    format = models.CharField(max_length=20, default="mp4")
    resolution = models.CharField(max_length=20, default="720p")
    frame_rate = models.IntegerField(default=24)
    duration_seconds = models.FloatField(default=0.0)
    has_audio = models.BooleanField(default=True)
    has_burned_subtitles = models.BooleanField(default=False)
    output_video = models.FileField(upload_to="asai/flow/exports/", null=True, blank=True)
    output_video_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    progress = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    render_log = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = "asai_flow_exports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export {self.export_id[:8]} ({self.project.name}) - {self.status}"
