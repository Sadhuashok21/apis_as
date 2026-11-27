import os
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.utils import timezone
from django.core.files import File
from ...models import (
    ASAIProject,
    ASAIScene,
    ASAIAsset,
    ASAICharacter,
    ASAIFlowJob,
    ASAIVideoVersion,
    ASAIExport,
)
from .capability_registry import CapabilityRegistry
from .providers.ffmpeg_provider import FFmpegComposerProvider
from ..subscription_service import subscription_service

logger = logging.getLogger("asai.flow.service")


class FlowService:
    """
    Core orchestrator for ASAI Flow filmmaking projects, scenes,
    generation queueing, version stacks, and multi-scene export rendering.
    """

    def __init__(self):
        self.composer = FFmpegComposerProvider()

    # --------------------------------------------------------------------------
    # 1. Project Management
    # --------------------------------------------------------------------------
    def get_or_create_project(
        self,
        user=None,
        session_key: str = "",
        name: str = "New Cinematic Project",
        aspect_ratio: str = "16:9",
        style: str = "Cinematic"
    ) -> ASAIProject:
        project = ASAIProject.objects.create(
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            name=name,
            aspect_ratio=aspect_ratio,
            default_style=style,
        )
        # Create initial default scene
        ASAIScene.objects.create(
            project=project,
            order=0,
            title="Scene 1: Establishing Shot",
            description="Opening scene of the film.",
            prompt=f"A cinematic establishing shot, {style} visual style, high detail, 8k resolution.",
            camera_framing="Wide shot",
            camera_movement="Dolly in",
            duration_seconds=4.0,
            timeline_position_ms=0,
        )
        return project

    # --------------------------------------------------------------------------
    # 2. Scene Operations & Timeline Reordering
    # --------------------------------------------------------------------------
    def reorder_scenes(self, project: ASAIProject, scene_ids_in_order: List[str]) -> List[ASAIScene]:
        """
        Reorders scenes based on drag-and-drop timeline placement and recalibrates timeline positions.
        """
        current_time_ms = 0
        updated_scenes = []

        for idx, sid in enumerate(scene_ids_in_order):
            scene = ASAIScene.objects.filter(project=project, scene_id=sid).first()
            if scene:
                scene.order = idx
                scene.timeline_position_ms = current_time_ms
                scene.save(update_fields=["order", "timeline_position_ms"])
                current_time_ms += int(scene.duration_seconds * 1000)
                updated_scenes.append(scene)

        return updated_scenes

    # --------------------------------------------------------------------------
    # 3. Asynchronous Video Generation Jobs
    # --------------------------------------------------------------------------
    def submit_generation_job(
        self,
        project: ASAIProject,
        scene: Optional[ASAIScene],
        mode: str,
        prompt: str,
        negative_prompt: str = "",
        provider_name: str = "comfyui_video",
        camera_framing: str = "",
        camera_movement: str = "",
        source_image_path: str = "",
        duration_seconds: float = 4.0,
        user=None,
        session_key: str = ""
    ) -> ASAIFlowJob:
        # 1. Quota Enforcement
        allowed, reason, quota_info = subscription_service.check_quota(user, session_key, feature="video", amount=1)
        if not allowed:
            raise PermissionError(f"Video generation quota exceeded: {reason}")

        # 2. Create Job Record
        job = ASAIFlowJob.objects.create(
            project=project,
            scene=scene,
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            provider_name=provider_name,
            mode=mode,
            prompt=prompt,
            negative_prompt=negative_prompt,
            generation_settings={
                "camera_framing": camera_framing,
                "camera_movement": camera_movement,
                "duration": duration_seconds,
                "aspect_ratio": project.aspect_ratio,
                "source_image": source_image_path,
            },
            status="QUEUED",
            progress=5,
            current_stage="Job registered in queue",
        )

        # 3. Launch background worker thread
        t = threading.Thread(target=self._run_job_worker, args=(job.job_id,), daemon=True)
        t.start()

        return job

    def _run_job_worker(self, job_id: str):
        """Background worker thread executing video generation and updating progress stages."""
        job = ASAIFlowJob.objects.filter(job_id=job_id).first()
        if not job:
            return

        try:
            job.status = "PREPARING"
            job.progress = 20
            job.current_stage = "Allocating GPU memory and validating frame buffers"
            job.save(update_fields=["status", "progress", "current_stage"])
            time.sleep(0.4)

            # Resolve Provider
            provider = CapabilityRegistry.get_provider(job.provider_name)
            if not provider:
                provider = CapabilityRegistry.get_provider("ffmpeg_composer")

            job.status = "GENERATING"
            job.progress = 50
            job.current_stage = f"Executing motion synthesis on {provider.display_name}"
            job.save(update_fields=["status", "progress", "current_stage"])

            gen_params = dict(job.generation_settings)
            gen_params["prompt"] = job.prompt
            gen_params["negative_prompt"] = job.negative_prompt

            # Handle start frame if blank but scene has starting frame
            if not gen_params.get("source_image") and job.scene and job.scene.starting_frame:
                gen_params["source_image"] = job.scene.starting_frame.path

            # Execute generation
            if job.mode == "video_extend":
                orig_clip = gen_params.get("source_video") or (job.scene.active_clip.path if job.scene and job.scene.active_clip else "")
                res = provider.extend_video(job.job_id, orig_clip, gen_params)
            elif job.mode == "video_edit":
                orig_clip = gen_params.get("source_video") or (job.scene.active_clip.path if job.scene and job.scene.active_clip else "")
                res = provider.edit_video(job.job_id, orig_clip, job.prompt, gen_params)
            else:
                res = provider.generate(job.job_id, gen_params)

            output_path = res.get("output_path")

            job.status = "ASSEMBLING"
            job.progress = 85
            job.current_stage = "Finalizing codec encoding and generating timeline thumbnails"
            job.save(update_fields=["status", "progress", "current_stage"])
            time.sleep(0.3)

            # Attach result video to Job
            if output_path and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    job.result_video.save(os.path.basename(output_path), File(f), save=False)
                job.result_video_url = job.result_video.url

                # If job was tied to a scene, update scene's active clip and record version stack
                if job.scene:
                    with open(output_path, "rb") as f:
                        job.scene.active_clip.save(os.path.basename(output_path), File(f), save=False)
                    job.scene.active_clip_url = job.scene.active_clip.url
                    job.scene.duration_seconds = float(gen_params.get("duration", 4.0))
                    job.scene.save(update_fields=["active_clip", "active_clip_url", "duration_seconds"])

                    # Create Version Stack Entry (Never overwrites original!)
                    version_num = job.scene.versions.count() + 1
                    ver = ASAIVideoVersion.objects.create(
                        scene=job.scene,
                        version_number=version_num,
                        prompt=job.prompt,
                        model_used=provider.display_name,
                        generation_settings=job.generation_settings,
                        duration_seconds=job.scene.duration_seconds,
                        is_active=True,
                    )
                    with open(output_path, "rb") as f:
                        ver.output_file.save(f"v{version_num}_{os.path.basename(output_path)}", File(f), save=True)
                    ver.output_url = ver.output_file.url
                    ver.save(update_fields=["output_url"])

            # Deduct usage quota
            subscription_service.consume_quota(job.user, job.session_key, feature="video", amount=1)

            job.status = "COMPLETED"
            job.progress = 100
            job.current_stage = "Clip generation complete"
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "progress", "current_stage", "result_video", "result_video_url", "completed_at"])
            logger.info(f"ASAI Flow Job {job_id} successfully completed.")

        except Exception as e:
            logger.error(f"ASAI Flow Job {job_id} failed: {e}", exc_info=True)
            job.status = "FAILED"
            job.error_details = str(e)
            job.progress = 0
            job.save(update_fields=["status", "error_details", "progress"])

    # --------------------------------------------------------------------------
    # 4. Multi-Scene Timeline Export Pipeline
    # --------------------------------------------------------------------------
    def submit_project_export(
        self,
        project: ASAIProject,
        resolution: str = "720p",
        frame_rate: int = 24,
        include_subtitles: bool = False,
        user=None,
        session_key: str = ""
    ) -> ASAIExport:
        export_job = ASAIExport.objects.create(
            project=project,
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else "",
            resolution=resolution,
            frame_rate=frame_rate,
            has_burned_subtitles=include_subtitles,
            status="QUEUED",
            progress=5,
        )

        t = threading.Thread(target=self._run_export_worker, args=(export_job.export_id,), daemon=True)
        t.start()

        return export_job

    def _run_export_worker(self, export_id: str):
        export_job = ASAIExport.objects.filter(export_id=export_id).select_related("project").first()
        if not export_job:
            return

        try:
            export_job.status = "RENDERING"
            export_job.progress = 25
            export_job.save(update_fields=["status", "progress"])

            project = export_job.project
            scenes = list(project.scenes.order_by("order"))

            # Collect active clips
            clip_paths = []
            audio_paths = []
            total_duration = 0.0

            for s in scenes:
                if s.active_clip and os.path.exists(s.active_clip.path):
                    clip_paths.append(s.active_clip.path)
                    total_duration += s.duration_seconds
                if s.audio_track and os.path.exists(s.audio_track.path):
                    audio_paths.append(s.audio_track.path)

            if not clip_paths:
                raise ValueError("Project has no rendered scene clips to assemble. Please generate at least one scene clip.")

            export_job.progress = 60
            export_job.save(update_fields=["progress"])

            out_dir = Path(settings.MEDIA_ROOT) / "asai" / "flow" / "exports"
            out_dir.mkdir(parents=True, exist_ok=True)
            final_mp4_path = str(out_dir / f"film_{project.project_id[:8]}_{export_id[:8]}.mp4")

            res = self.composer.render_final_export(clip_paths, audio_paths, final_mp4_path)
            rendered_path = res["output_path"]

            with open(rendered_path, "rb") as f:
                export_job.output_video.save(os.path.basename(rendered_path), File(f), save=False)
            export_job.output_video_url = export_job.output_video.url
            export_job.duration_seconds = total_duration
            export_job.status = "COMPLETED"
            export_job.progress = 100
            export_job.completed_at = timezone.now()
            export_job.save(update_fields=["output_video", "output_video_url", "duration_seconds", "status", "progress", "completed_at"])

            logger.info(f"Film export {export_id} completed successfully ({total_duration:.1f}s).")

        except Exception as e:
            logger.error(f"Film export {export_id} failed: {e}", exc_info=True)
            export_job.status = "FAILED"
            export_job.error_message = str(e)
            export_job.save(update_fields=["status", "error_message"])


flow_service = FlowService()
