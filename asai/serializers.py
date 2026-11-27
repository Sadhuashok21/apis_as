from rest_framework import serializers
from .models import (
    ASAIModel,
    ASAIConversation,
    ASAIMessage,
    ASAIImageGenerationJob,
    ASAIGeneratedMedia,
    ASAIDocument,
    ASAIVideoGenerationJob,
    ASAIUserSettings,
    ASAIUsageLog,
    ASAISubscriptionPlan,
    ASAIUserSubscription,
    ASAIPaymentTransaction,
    ASAIUsageAllowance,
    ASAIBusinessOrganization,
    ASAIOrganizationMember,
    ASAICoupon,
    ASAIProject,
    ASAICharacter,
    ASAIAsset,
    ASAIScene,
    ASAIFlowJob,
    ASAIVideoVersion,
    ASAIExport,
)


class ASAIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIModel
        fields = [
            "model_id",
            "name",
            "ollama_model",
            "tag",
            "description",
            "capabilities",
            "context_window",
            "is_active",
            "is_default",
            "order",
        ]


class ASAIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIMessage
        fields = [
            "message_id",
            "role",
            "content",
            "model_used",
            "tokens",
            "rating",
            "metadata",
            "created_at",
        ]


class ASAIConversationSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="conversation_id", read_only=True)
    message_count = serializers.IntegerField(source="messages.count", read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ASAIConversation
        fields = [
            "id",
            "conversation_id",
            "title",
            "model",
            "is_pinned",
            "is_archived",
            "message_count",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if last:
            return {
                "role": last.role,
                "content": last.content[:80] + ("..." if len(last.content) > 80 else ""),
                "created_at": last.created_at.isoformat()
            }
        return None


class ASAIConversationDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="conversation_id", read_only=True)
    messages = ASAIMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ASAIConversation
        fields = [
            "id",
            "conversation_id",
            "title",
            "model",
            "system_prompt",
            "is_pinned",
            "is_archived",
            "messages",
            "created_at",
            "updated_at",
        ]


class ASAIGeneratedMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIGeneratedMedia
        fields = [
            "media_id",
            "job",
            "media_type",
            "file",
            "file_url",
            "prompt",
            "aspect_ratio",
            "width",
            "height",
            "metadata",
            "created_at",
        ]


class ASAIImageGenerationJobSerializer(serializers.ModelSerializer):
    media = ASAIGeneratedMediaSerializer(source="generated_media", many=True, read_only=True)

    class Meta:
        model = ASAIImageGenerationJob
        fields = [
            "job_id",
            "prompt",
            "negative_prompt",
            "model_name",
            "aspect_ratio",
            "width",
            "height",
            "num_images",
            "status",
            "progress",
            "current_step",
            "error_message",
            "media",
            "created_at",
            "completed_at",
        ]


class ASAIDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIDocument
        fields = [
            "doc_id",
            "name",
            "file",
            "file_url",
            "file_type",
            "file_size_bytes",
            "summary",
            "metadata",
            "created_at",
        ]


class ASAIVideoGenerationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIVideoGenerationJob
        fields = [
            "job_id",
            "prompt",
            "duration_seconds",
            "aspect_ratio",
            "motion_strength",
            "status",
            "progress",
            "result_video_url",
            "error_message",
            "created_at",
            "completed_at",
        ]


class ASAIUserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIUserSettings
        fields = [
            "theme",
            "default_model",
            "language",
            "chat_history_enabled",
            "suggested_prompts_enabled",
            "voice_enabled",
            "updated_at",
        ]


# ==============================================================================
# SUBSCRIPTION & USAGE SERIALIZERS
# ==============================================================================

class ASAISubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAISubscriptionPlan
        fields = [
            "plan_id",
            "name",
            "tier",
            "tagline",
            "badge",
            "price_monthly_inr",
            "price_yearly_inr",
            "yearly_discount_percent",
            "daily_message_limit",
            "monthly_image_credits",
            "max_doc_size_mb",
            "monthly_doc_limit",
            "monthly_video_limit",
            "context_window",
            "has_advanced_code",
            "has_priority_processing",
            "has_voice",
            "has_team_workspace",
            "features_highlight",
            "cta_text",
            "is_active",
            "order",
        ]


class ASAIUserSubscriptionSerializer(serializers.ModelSerializer):
    plan = ASAISubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = ASAIUserSubscription
        fields = [
            "subscription_id",
            "plan",
            "billing_cycle",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "created_at",
        ]


class ASAIPaymentTransactionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = ASAIPaymentTransaction
        fields = [
            "transaction_id",
            "plan_name",
            "billing_cycle",
            "amount_paise",
            "currency",
            "gateway",
            "razorpay_order_id",
            "razorpay_payment_id",
            "status",
            "failure_reason",
            "created_at",
            "completed_at",
        ]


class ASAIUsageAllowanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ASAIUsageAllowance
        fields = [
            "daily_messages_used",
            "last_message_date",
            "monthly_images_used",
            "monthly_docs_used",
            "monthly_videos_used",
            "updated_at",
        ]


class ASAIBusinessOrganizationSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = ASAIBusinessOrganization
        fields = [
            "org_id",
            "name",
            "seats_allocated",
            "billing_email",
            "members_count",
            "settings",
            "created_at",
        ]


# ==============================================================================
# ASAI FLOW SERIALIZERS
# ==============================================================================

class ASAICharacterSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="character_id", read_only=True)

    class Meta:
        model = ASAICharacter
        fields = [
            "id",
            "character_id",
            "name",
            "appearance_prompt",
            "clothing_prompt",
            "physical_attributes",
            "reference_image_url",
            "voice_ref",
            "metadata",
            "created_at",
        ]


class ASAIAssetSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="asset_id", read_only=True)

    class Meta:
        model = ASAIAsset
        fields = [
            "id",
            "asset_id",
            "asset_type",
            "name",
            "description",
            "file_url",
            "file_size_bytes",
            "mime_type",
            "metadata",
            "created_at",
        ]


class ASAIVideoVersionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="version_id", read_only=True)
    video_url = serializers.CharField(source="output_url", read_only=True)

    class Meta:
        model = ASAIVideoVersion
        fields = [
            "id",
            "version_id",
            "version_number",
            "prompt",
            "model_used",
            "output_url",
            "video_url",
            "duration_seconds",
            "is_active",
            "created_at",
        ]


class ASAISceneSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="scene_id", read_only=True)
    video_url = serializers.CharField(source="active_clip_url", read_only=True)
    first_frame_url = serializers.CharField(source="starting_frame_url", read_only=True)
    characters_detail = ASAICharacterSerializer(source="characters", many=True, read_only=True)
    versions_count = serializers.IntegerField(source="versions.count", read_only=True)

    class Meta:
        model = ASAIScene
        fields = [
            "id",
            "scene_id",
            "order",
            "title",
            "description",
            "prompt",
            "negative_prompt",
            "characters",
            "characters_detail",
            "camera_framing",
            "camera_movement",
            "visual_style",
            "lighting",
            "environment",
            "starting_frame_url",
            "first_frame_url",
            "ending_frame_url",
            "active_clip_url",
            "video_url",
            "duration_seconds",
            "timeline_position_ms",
            "audio_track_url",
            "subtitle_text",
            "transition_type",
            "versions_count",
            "created_at",
            "updated_at",
        ]


class ASAIProjectSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="project_id", read_only=True)
    scenes = ASAISceneSerializer(many=True, read_only=True)
    scenes_count = serializers.IntegerField(source="scenes.count", read_only=True)
    assets_count = serializers.IntegerField(source="assets.count", read_only=True)
    characters_count = serializers.IntegerField(source="characters.count", read_only=True)

    class Meta:
        model = ASAIProject
        fields = [
            "id",
            "project_id",
            "name",
            "description",
            "thumbnail",
            "aspect_ratio",
            "target_resolution",
            "frame_rate",
            "default_style",
            "auto_save_data",
            "scenes",
            "scenes_count",
            "assets_count",
            "characters_count",
            "created_at",
            "updated_at",
        ]


class ASAIFlowJobSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="job_id", read_only=True)

    class Meta:
        model = ASAIFlowJob
        fields = [
            "id",
            "job_id",
            "project_id",
            "scene_id",
            "provider_name",
            "mode",
            "prompt",
            "status",
            "progress",
            "current_stage",
            "error_details",
            "vram_allocated_mb",
            "result_video_url",
            "created_at",
            "completed_at",
        ]


class ASAIExportSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="export_id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = ASAIExport
        fields = [
            "id",
            "export_id",
            "project_id",
            "project_name",
            "format",
            "resolution",
            "frame_rate",
            "duration_seconds",
            "has_audio",
            "has_burned_subtitles",
            "output_video_url",
            "status",
            "progress",
            "error_message",
            "created_at",
            "completed_at",
        ]
