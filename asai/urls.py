from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ASAIModelsView,
    ASAIServicesStatusView,
    ASAIConversationViewSet,
    ASAIChatView,
    ASAIImageGenerateView,
    ASAIImageJobDetailView,
    ASAIImageHistoryView,
    ASAIImageDeleteView,
    ASAIVisionAnalyzeView,
    ASAICodingAskView,
    ASAIDocumentUploadView,
    ASAIDocumentListView,
    ASAIDocumentAskView,
    ASAIVoiceTranscribeView,
    ASAIVideoGenerateView,
    ASAIUserSettingsView,
    ASAISubscriptionPlansView,
    ASAISubscriptionDetailView,
    ASAISubscriptionCheckoutView,
    ASAISubscriptionVerifyView,
    ASAISubscriptionCancelView,
    ASAISubscriptionHistoryView,
    ASAIUsageView,
    ASAIBusinessCreateView,
)
from .views_flow import (
    ASAIProjectListView,
    ASAIProjectDetailView,
    ASAISceneListView,
    ASAISceneDetailView,
    ASAISceneReorderView,
    ASAIAssetUploadView,
    ASAIAssetListView,
    ASAICharacterListView,
    ASAIFlowGenerateTextView,
    ASAIFlowGenerateFramesView,
    ASAIFlowExtendView,
    ASAIFlowEditView,
    ASAIFlowJobDetailView,
    ASAIFlowJobCancelView,
    ASAISceneVersionListView,
    ASAISceneVersionRestoreView,
    ASAIExportCreateView,
    ASAIExportDetailView,
    ASAIModelCapabilitiesView,
    ASAIStoryAssistantBreakdownView,
)

router = DefaultRouter()
router.register("conversations", ASAIConversationViewSet, basename="asai-conversation")

urlpatterns = [
    # Router endpoints (e.g. /conversations/)
    path("", include(router.urls)),

    # Model and service status
    path("models/", ASAIModelsView.as_view(), name="asai-models"),
    path("models/status/", ASAIServicesStatusView.as_view(), name="asai-services-status"),

    # Subscription, Plans & Usage Enforcement
    path("plans/", ASAISubscriptionPlansView.as_view(), name="asai-plans"),
    path("subscription/", ASAISubscriptionDetailView.as_view(), name="asai-subscription-detail"),
    path("subscription/checkout/", ASAISubscriptionCheckoutView.as_view(), name="asai-subscription-checkout"),
    path("subscription/verify/", ASAISubscriptionVerifyView.as_view(), name="asai-subscription-verify"),
    path("subscription/cancel/", ASAISubscriptionCancelView.as_view(), name="asai-subscription-cancel"),
    path("subscription/history/", ASAISubscriptionHistoryView.as_view(), name="asai-subscription-history"),
    path("usage/", ASAIUsageView.as_view(), name="asai-usage"),
    path("business/create/", ASAIBusinessCreateView.as_view(), name="asai-business-create"),

    # Chat completions & SSE streaming
    path("chat/", ASAIChatView.as_view(), name="asai-chat"),

    # Image generation (ComfyUI)
    path("images/generate/", ASAIImageGenerateView.as_view(), name="asai-image-generate"),
    path("images/jobs/<str:job_id>/", ASAIImageJobDetailView.as_view(), name="asai-image-job-detail"),
    path("images/history/", ASAIImageHistoryView.as_view(), name="asai-image-history"),
    path("images/<str:media_id>/", ASAIImageDeleteView.as_view(), name="asai-image-delete"),

    # Multimodal Vision Analysis
    path("vision/analyze/", ASAIVisionAnalyzeView.as_view(), name="asai-vision-analyze"),

    # Coding Assistant
    path("coding/ask/", ASAICodingAskView.as_view(), name="asai-coding-ask"),

    # Document AI (PDF, DOCX, XLSX, CSV, TXT)
    path("files/upload/", ASAIDocumentUploadView.as_view(), name="asai-document-upload"),
    path("files/", ASAIDocumentListView.as_view(), name="asai-document-list"),
    path("files/ask/", ASAIDocumentAskView.as_view(), name="asai-document-ask"),

    # Voice STT
    path("voice/transcribe/", ASAIVoiceTranscribeView.as_view(), name="asai-voice-transcribe"),

    # Video generation queue
    path("videos/generate/", ASAIVideoGenerateView.as_view(), name="asai-video-generate"),

    # User preferences / settings
    path("settings/", ASAIUserSettingsView.as_view(), name="asai-user-settings"),

    # ==============================================================================
    # ASAI FLOW FILMMAKING STUDIO ENDPOINTS
    # ==============================================================================
    path("flow/projects/", ASAIProjectListView.as_view(), name="asai-flow-projects"),
    path("flow/projects/<str:project_id>/", ASAIProjectDetailView.as_view(), name="asai-flow-project-detail"),
    path("flow/projects/<str:project_id>/scenes/", ASAISceneListView.as_view(), name="asai-flow-scenes"),
    path("flow/projects/<str:project_id>/scenes/reorder/", ASAISceneReorderView.as_view(), name="asai-flow-scenes-reorder"),
    path("flow/scenes/<str:scene_id>/", ASAISceneDetailView.as_view(), name="asai-flow-scene-detail"),
    path("flow/scenes/<str:scene_id>/versions/", ASAISceneVersionListView.as_view(), name="asai-flow-scene-versions"),
    path("flow/versions/<str:version_id>/restore/", ASAISceneVersionRestoreView.as_view(), name="asai-flow-version-restore"),
    path("flow/assets/upload/", ASAIAssetUploadView.as_view(), name="asai-flow-asset-upload"),
    path("flow/projects/<str:project_id>/assets/", ASAIAssetListView.as_view(), name="asai-flow-assets"),
    path("flow/projects/<str:project_id>/characters/", ASAICharacterListView.as_view(), name="asai-flow-characters"),
    path("flow/generate/text/", ASAIFlowGenerateTextView.as_view(), name="asai-flow-gen-text"),
    path("flow/generate/frames/", ASAIFlowGenerateFramesView.as_view(), name="asai-flow-gen-frames"),
    path("flow/extend/", ASAIFlowExtendView.as_view(), name="asai-flow-extend"),
    path("flow/edit/", ASAIFlowEditView.as_view(), name="asai-flow-edit"),
    path("flow/jobs/<str:job_id>/", ASAIFlowJobDetailView.as_view(), name="asai-flow-job-detail"),
    path("flow/jobs/<str:job_id>/cancel/", ASAIFlowJobCancelView.as_view(), name="asai-flow-job-cancel"),
    path("flow/projects/<str:project_id>/export/", ASAIExportCreateView.as_view(), name="asai-flow-export-create"),
    path("flow/exports/<str:export_id>/", ASAIExportDetailView.as_view(), name="asai-flow-export-detail"),
    path("flow/models/capabilities/", ASAIModelCapabilitiesView.as_view(), name="asai-flow-capabilities"),
    path("flow/assistant/breakdown/", ASAIStoryAssistantBreakdownView.as_view(), name="asai-flow-assistant-breakdown"),
]
