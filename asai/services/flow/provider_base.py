import abc
from typing import Dict, Any, Optional, List, Tuple


class BaseVideoProvider(abc.ABC):
    """
    Abstract Base Class for ASAI Flow Video Providers.
    Encapsulates capability introspection, hardware resource estimation,
    generation execution, job monitoring, clip extension, and video editing.
    """

    provider_id: str = "base_provider"
    display_name: str = "Base Video Provider"

    @abc.abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Returns full capability specification for this model provider:
        - supported generation modes (text_to_video, frames_to_video, video_edit, video_extend)
        - aspect ratios supported (e.g. ['16:9', '9:16', '1:1'])
        - resolutions supported (e.g. ['512x512', '768x768', '1280x720'])
        - max duration (seconds)
        - character consistency support (bool)
        - reference image support (bool)
        - native camera control support (bool or 'prompt_guided')
        - required VRAM (MB/GB)
        """
        pass

    @abc.abstractmethod
    def check_availability(self) -> Dict[str, Any]:
        """
        Checks if the provider's runtime / node is active and available.
        Returns:
            {"available": bool, "status": str, "reason": str, "vram_free_mb": float}
        """
        pass

    @abc.abstractmethod
    def validate_request(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates whether generation parameters match provider capabilities.
        Returns (is_valid: bool, error_message: str).
        """
        pass

    @abc.abstractmethod
    def estimate_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimates VRAM allocation, compute time, and device compatibility.
        """
        pass

    @abc.abstractmethod
    def generate(self, job_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits or executes a video generation task.
        """
        pass

    @abc.abstractmethod
    def extend_video(self, job_id: str, original_clip_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extends an existing video clip.
        Raises NotImplementedError or returns capability error if unsupported.
        """
        pass

    @abc.abstractmethod
    def edit_video(self, job_id: str, source_video_path: str, instruction: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies video-to-video editing.
        Raises NotImplementedError or returns capability error if unsupported.
        """
        pass

    @abc.abstractmethod
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Queries live progress and execution stage for a running job.
        """
        pass

    @abc.abstractmethod
    def cancel(self, job_id: str) -> bool:
        """
        Cancels an ongoing generation job and frees resources.
        """
        pass

    @abc.abstractmethod
    def retrieve_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the generated video path, metadata, and extracted frames.
        """
        pass
