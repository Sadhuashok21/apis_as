import os
import logging
from typing import Dict, Any
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.core.files import File

from .models import (
    ASAIProject,
    ASAICharacter,
    ASAIAsset,
    ASAIScene,
    ASAIFlowJob,
    ASAIVideoVersion,
    ASAIExport,
)
from .serializers import (
    ASAIProjectSerializer,
    ASAICharacterSerializer,
    ASAIAssetSerializer,
    ASAISceneSerializer,
    ASAIFlowJobSerializer,
    ASAIVideoVersionSerializer,
    ASAIExportSerializer,
)
from .views import get_current_user_or_none, get_session_key
from .services.flow import (
    flow_service,
    FlowAssistantService,
    CapabilityRegistry,
    HardwareProbe,
)

logger = logging.getLogger("asai.flow.views")


# ------------------------------------------------------------------------------
# 1. Projects
# ------------------------------------------------------------------------------
class ASAIProjectListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        if user and user.is_authenticated:
            projects = ASAIProject.objects.filter(user=user)
        else:
            projects = ASAIProject.objects.filter(session_key=session_key)

        serializer = ASAIProjectSerializer(projects, many=True)
        return Response({"status": True, "projects": serializer.data})

    def post(self, request):
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)
        name = request.data.get("name", "Untitled Film Project").strip()
        aspect_ratio = request.data.get("aspect_ratio", "16:9")
        style = request.data.get("style", "Cinematic")

        project = flow_service.get_or_create_project(
            user=user,
            session_key=session_key,
            name=name,
            aspect_ratio=aspect_ratio,
            style=style,
        )
        serializer = ASAIProjectSerializer(project)
        return Response({"status": True, "project": serializer.data}, status=status.HTTP_201_CREATED)


class ASAIProjectDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        serializer = ASAIProjectSerializer(project)
        return Response({"status": True, "project": serializer.data})

    def patch(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        for field in ["name", "description", "aspect_ratio", "target_resolution", "frame_rate", "default_style", "auto_save_data"]:
            if field in request.data:
                setattr(project, field, request.data[field])
        project.save()
        serializer = ASAIProjectSerializer(project)
        return Response({"status": True, "project": serializer.data})

    def delete(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        project.delete()
        return Response({"status": True, "message": "Project deleted successfully."})


# ------------------------------------------------------------------------------
# 2. Scenes & Timeline Reordering
# ------------------------------------------------------------------------------
class ASAISceneListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        scenes = project.scenes.order_by("order")
        serializer = ASAISceneSerializer(scenes, many=True)
        return Response({"status": True, "scenes": serializer.data})

    def post(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        title = request.data.get("title", f"Scene {project.scenes.count() + 1}")
        prompt = request.data.get("prompt", "Cinematic wide shot")
        camera_framing = request.data.get("camera_framing", "Medium shot")
        camera_movement = request.data.get("camera_movement", "Static")
        duration = float(request.data.get("duration", 4.0))

        order = project.scenes.count()
        # Calculate timeline position
        last_scene = project.scenes.order_by("-order").first()
        timeline_pos = (last_scene.timeline_position_ms + int(last_scene.duration_seconds * 1000)) if last_scene else 0

        scene = ASAIScene.objects.create(
            project=project,
            order=order,
            title=title,
            description=request.data.get("description", ""),
            prompt=prompt,
            negative_prompt=request.data.get("negative_prompt", ""),
            camera_framing=camera_framing,
            camera_movement=camera_movement,
            visual_style=request.data.get("visual_style", project.default_style),
            lighting=request.data.get("lighting", "Natural cinematic"),
            environment=request.data.get("environment", ""),
            duration_seconds=duration,
            timeline_position_ms=timeline_pos,
            subtitle_text=request.data.get("subtitle_text", ""),
        )
        serializer = ASAISceneSerializer(scene)
        return Response({"status": True, "scene": serializer.data}, status=status.HTTP_201_CREATED)


class ASAISceneDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, scene_id):
        scene = get_object_or_404(ASAIScene, scene_id=scene_id)
        for field in [
            "title", "description", "prompt", "negative_prompt",
            "camera_framing", "camera_movement", "visual_style",
            "lighting", "environment", "duration_seconds",
            "subtitle_text", "transition_type"
        ]:
            if field in request.data:
                setattr(scene, field, request.data[field])
        scene.save()
        serializer = ASAISceneSerializer(scene)
        return Response({"status": True, "scene": serializer.data})

    def delete(self, request, scene_id):
        scene = get_object_or_404(ASAIScene, scene_id=scene_id)
        project = scene.project
        scene.delete()
        # Recalibrate remaining scenes
        remaining = list(project.scenes.order_by("order"))
        flow_service.reorder_scenes(project, [s.scene_id for s in remaining])
        return Response({"status": True, "message": "Scene deleted and timeline recalibrated."})


class ASAISceneReorderView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        scene_ids = request.data.get("scene_ids", [])
        if not isinstance(scene_ids, list):
            return Response({"status": False, "error": "scene_ids must be an array of UUIDs"}, status=status.HTTP_400_BAD_REQUEST)

        updated = flow_service.reorder_scenes(project, scene_ids)
        serializer = ASAISceneSerializer(updated, many=True)
        return Response({"status": True, "scenes": serializer.data})


# ------------------------------------------------------------------------------
# 3. Assets & Characters
# ------------------------------------------------------------------------------
class ASAIAssetUploadView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"status": False, "error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        project_id = request.data.get("project_id")
        project = ASAIProject.objects.filter(project_id=project_id).first() if project_id else None
        asset_type = request.data.get("asset_type", "style_ref")
        name = request.data.get("name") or file_obj.name
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        asset = ASAIAsset.objects.create(
            project=project,
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            asset_type=asset_type,
            name=name,
            description=request.data.get("description", ""),
            file=file_obj,
            file_size_bytes=file_obj.size,
            mime_type=file_obj.content_type or "",
        )
        asset.file_url = asset.file.url
        asset.save(update_fields=["file_url"])

        serializer = ASAIAssetSerializer(asset)
        return Response({"status": True, "asset": serializer.data}, status=status.HTTP_201_CREATED)


class ASAIAssetListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        assets = project.assets.order_by("-created_at")
        serializer = ASAIAssetSerializer(assets, many=True)
        return Response({"status": True, "assets": serializer.data})


class ASAICharacterListView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        characters = project.characters.all()
        serializer = ASAICharacterSerializer(characters, many=True)
        return Response({"status": True, "characters": serializer.data})

    def post(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        name = request.data.get("name", "New Character").strip()
        appearance = request.data.get("appearance_prompt", "")
        clothing = request.data.get("clothing_prompt", "")
        ref_file = request.FILES.get("reference_image")

        character = ASAICharacter.objects.create(
            project=project,
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            name=name,
            appearance_prompt=appearance,
            clothing_prompt=clothing,
        )
        if ref_file:
            character.reference_image = ref_file
            character.save()
            character.reference_image_url = character.reference_image.url
            character.save(update_fields=["reference_image_url"])

        serializer = ASAICharacterSerializer(character)
        return Response({"status": True, "character": serializer.data}, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------------------
# 4. Generation, Editing & Clip Extension
# ------------------------------------------------------------------------------
class ASAIFlowGenerateTextView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        project_id = request.data.get("project_id")
        scene_id = request.data.get("scene_id")
        prompt = request.data.get("prompt", "").strip()

        if not prompt:
            return Response({"status": False, "error": "Prompt cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(ASAIProject, project_id=project_id)
        scene = ASAIScene.objects.filter(scene_id=scene_id, project=project).first() if scene_id else None
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        provider_name = request.data.get("provider", "comfyui_video")
        camera_framing = request.data.get("camera_framing", "")
        camera_movement = request.data.get("camera_movement", "")
        duration = float(request.data.get("duration", 4.0))

        try:
            job = flow_service.submit_generation_job(
                project=project,
                scene=scene,
                mode="text_to_video",
                prompt=prompt,
                negative_prompt=request.data.get("negative_prompt", ""),
                provider_name=provider_name,
                camera_framing=camera_framing,
                camera_movement=camera_movement,
                duration_seconds=duration,
                user=user,
                session_key=session_key,
            )
            serializer = ASAIFlowJobSerializer(job)
            return Response({"status": True, "job": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except PermissionError as e:
            return Response({"status": False, "error": str(e), "quota_exhausted": True}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class ASAIFlowGenerateFramesView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        project_id = request.data.get("project_id")
        scene_id = request.data.get("scene_id")
        prompt = request.data.get("prompt", "").strip()
        project = get_object_or_404(ASAIProject, project_id=project_id)
        scene = ASAIScene.objects.filter(scene_id=scene_id, project=project).first() if scene_id else None
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        # Handle starting frame upload or existing path
        starting_frame_file = request.FILES.get("starting_frame")
        source_image_path = ""
        if starting_frame_file and scene:
            scene.starting_frame = starting_frame_file
            scene.save()
            scene.starting_frame_url = scene.starting_frame.url
            scene.save(update_fields=["starting_frame_url"])
            source_image_path = scene.starting_frame.path
        elif scene and scene.starting_frame:
            source_image_path = scene.starting_frame.path

        try:
            job = flow_service.submit_generation_job(
                project=project,
                scene=scene,
                mode="frames_to_video",
                prompt=prompt or "Smooth cinematic motion from keyframe",
                provider_name=request.data.get("provider", "comfyui_video"),
                camera_movement=request.data.get("camera_movement", "Zoom in"),
                source_image_path=source_image_path,
                duration_seconds=float(request.data.get("duration", 4.0)),
                user=user,
                session_key=session_key,
            )
            serializer = ASAIFlowJobSerializer(job)
            return Response({"status": True, "job": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except PermissionError as e:
            return Response({"status": False, "error": str(e), "quota_exhausted": True}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class ASAIFlowExtendView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        scene_id = request.data.get("scene_id")
        scene = get_object_or_404(ASAIScene, scene_id=scene_id)
        if not scene.active_clip:
            return Response({"status": False, "error": "Scene has no rendered clip to extend."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        try:
            job = flow_service.submit_generation_job(
                project=scene.project,
                scene=scene,
                mode="video_extend",
                prompt=request.data.get("prompt", scene.prompt),
                provider_name="ffmpeg_composer",
                duration_seconds=float(request.data.get("duration", 4.0)),
                user=user,
                session_key=session_key,
            )
            serializer = ASAIFlowJobSerializer(job)
            return Response({"status": True, "job": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except PermissionError as e:
            return Response({"status": False, "error": str(e), "quota_exhausted": True}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class ASAIFlowEditView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        scene_id = request.data.get("scene_id")
        instruction = request.data.get("instruction", "").strip()
        if not instruction:
            return Response({"status": False, "error": "Editing instruction cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        scene = get_object_or_404(ASAIScene, scene_id=scene_id)
        if not scene.active_clip:
            return Response({"status": False, "error": "Scene has no clip to edit."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        try:
            job = flow_service.submit_generation_job(
                project=scene.project,
                scene=scene,
                mode="video_edit",
                prompt=instruction,
                provider_name="ffmpeg_composer",
                user=user,
                session_key=session_key,
            )
            serializer = ASAIFlowJobSerializer(job)
            return Response({"status": True, "job": serializer.data}, status=status.HTTP_202_ACCEPTED)
        except PermissionError as e:
            return Response({"status": False, "error": str(e), "quota_exhausted": True}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class ASAIFlowJobDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        job = get_object_or_404(ASAIFlowJob, job_id=job_id)
        serializer = ASAIFlowJobSerializer(job)
        return Response({"status": True, "job": serializer.data})


class ASAIFlowJobCancelView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, job_id):
        job = get_object_or_404(ASAIFlowJob, job_id=job_id)
        job.status = "CANCELLED"
        job.save(update_fields=["status"])
        return Response({"status": True, "message": "Job cancelled."})


# ------------------------------------------------------------------------------
# 5. Version History & Restoration
# ------------------------------------------------------------------------------
class ASAISceneVersionListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, scene_id):
        scene = get_object_or_404(ASAIScene, scene_id=scene_id)
        versions = scene.versions.order_by("-version_number")
        serializer = ASAIVideoVersionSerializer(versions, many=True)
        return Response({"status": True, "versions": serializer.data})


class ASAISceneVersionRestoreView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, version_id):
        version = get_object_or_404(ASAIVideoVersion, version_id=version_id)
        scene = version.scene

        # Mark this version active and copy file to scene active clip
        scene.versions.update(is_active=False)
        version.is_active = True
        version.save(update_fields=["is_active"])

        if version.output_file and os.path.exists(version.output_file.path):
            with open(version.output_file.path, "rb") as f:
                scene.active_clip.save(os.path.basename(version.output_file.path), File(f), save=False)
            scene.active_clip_url = scene.active_clip.url
            scene.duration_seconds = version.duration_seconds
            scene.save(update_fields=["active_clip", "active_clip_url", "duration_seconds"])

        return Response({"status": True, "message": f"Version v{version.version_number} restored successfully."})


# ------------------------------------------------------------------------------
# 6. Multi-Scene Export & Capabilities
# ------------------------------------------------------------------------------
class ASAIExportCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, project_id):
        project = get_object_or_404(ASAIProject, project_id=project_id)
        resolution = request.data.get("resolution", project.target_resolution)
        fps = int(request.data.get("fps", project.frame_rate))
        burned_subs = bool(request.data.get("include_subtitles", False))
        user = get_current_user_or_none(request)
        session_key = get_session_key(request)

        export_job = flow_service.submit_project_export(
            project=project,
            resolution=resolution,
            frame_rate=fps,
            include_subtitles=burned_subs,
            user=user,
            session_key=session_key,
        )
        serializer = ASAIExportSerializer(export_job)
        return Response({"status": True, "export": serializer.data}, status=status.HTTP_202_ACCEPTED)


class ASAIExportDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, export_id):
        export_job = get_object_or_404(ASAIExport, export_id=export_id)
        serializer = ASAIExportSerializer(export_job)
        return Response({"status": True, "export": serializer.data})


class ASAIModelCapabilitiesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        providers = CapabilityRegistry.list_providers()
        gpu = HardwareProbe.get_gpu_info()
        return Response({
            "status": True,
            "gpu": gpu,
            "providers": providers,
        })


class ASAIStoryAssistantBreakdownView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        prompt = request.data.get("prompt", "").strip()
        if not prompt:
            return Response({"status": False, "error": "Prompt cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        scenes_count = int(request.data.get("scenes_count", 4))
        breakdown = FlowAssistantService.generate_storyboard_breakdown(prompt, scenes_count)
        return Response(breakdown)
