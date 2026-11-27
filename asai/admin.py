from django.contrib import admin
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
)


@admin.register(ASAIModel)
class ASAIModelAdmin(admin.ModelAdmin):
    list_display = ("name", "model_id", "ollama_model", "tag", "is_active", "is_default", "order")
    list_filter = ("is_active", "is_default")
    search_fields = ("name", "model_id", "ollama_model")


class ASAIMessageInline(admin.TabularInline):
    model = ASAIMessage
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(ASAIConversation)
class ASAIConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "conversation_id", "user", "model", "is_pinned", "created_at", "updated_at")
    list_filter = ("model", "is_pinned", "is_archived", "created_at")
    search_fields = ("title", "conversation_id", "user__email", "user__name")
    inlines = [ASAIMessageInline]


@admin.register(ASAIMessage)
class ASAIMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "model_used", "tokens", "rating", "created_at")
    list_filter = ("role", "rating", "created_at")
    search_fields = ("content", "conversation__title", "conversation__conversation_id")


@admin.register(ASAIImageGenerationJob)
class ASAIImageGenerationJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "user", "prompt_preview", "model_name", "aspect_ratio", "status", "progress", "created_at")
    list_filter = ("status", "aspect_ratio", "created_at")
    search_fields = ("job_id", "prompt", "comfy_prompt_id", "user__email")

    def prompt_preview(self, obj):
        return obj.prompt[:50] + "..." if len(obj.prompt) > 50 else obj.prompt
    prompt_preview.short_description = "Prompt"


@admin.register(ASAIGeneratedMedia)
class ASAIGeneratedMediaAdmin(admin.ModelAdmin):
    list_display = ("media_id", "user", "media_type", "aspect_ratio", "created_at")
    list_filter = ("media_type", "created_at")
    search_fields = ("media_id", "prompt", "user__email")


@admin.register(ASAIDocument)
class ASAIDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "doc_id", "user", "file_type", "file_size_bytes", "created_at")
    list_filter = ("file_type", "created_at")
    search_fields = ("name", "doc_id", "user__email")


@admin.register(ASAIVideoGenerationJob)
class ASAIVideoGenerationJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "user", "duration_seconds", "aspect_ratio", "status", "progress", "created_at")
    list_filter = ("status", "aspect_ratio", "created_at")
    search_fields = ("job_id", "prompt")


@admin.register(ASAIUserSettings)
class ASAIUserSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "default_model", "language", "chat_history_enabled")
    search_fields = ("user__email", "user__name")


@admin.register(ASAIUsageLog)
class ASAIUsageLogAdmin(admin.ModelAdmin):
    list_display = ("feature", "user", "model_used", "duration_ms", "status", "created_at")
    list_filter = ("feature", "status", "created_at")
    search_fields = ("feature", "model_used", "user__email")

from .models import (
    ASAIProject,
    ASAICharacter,
    ASAIAsset,
    ASAIScene,
    ASAIFlowJob,
    ASAIVideoVersion,
    ASAIExport,
)

@admin.register(ASAIProject)
class ASAIProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "project_id", "user", "aspect_ratio", "target_resolution", "default_style", "created_at")
    search_fields = ("name", "project_id", "user__email")

@admin.register(ASAIScene)
class ASAISceneAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "order", "camera_framing", "camera_movement", "duration_seconds")
    list_filter = ("camera_framing", "camera_movement")
    search_fields = ("title", "prompt", "project__name")

@admin.register(ASAIFlowJob)
class ASAIFlowJobAdmin(admin.ModelAdmin):
    list_display = ("job_id", "project", "mode", "provider_name", "status", "progress", "created_at")
    list_filter = ("status", "mode", "provider_name")
    search_fields = ("job_id", "prompt", "project__name")

@admin.register(ASAIAsset)
class ASAIAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "asset_id", "project", "asset_type", "created_at")
    list_filter = ("asset_type",)
    search_fields = ("name", "asset_id")

@admin.register(ASAICharacter)
class ASAICharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "character_id", "project", "created_at")
    search_fields = ("name", "character_id")

@admin.register(ASAIExport)
class ASAIExportAdmin(admin.ModelAdmin):
    list_display = ("export_id", "project", "resolution", "duration_seconds", "status", "progress", "created_at")
    list_filter = ("status", "resolution")
