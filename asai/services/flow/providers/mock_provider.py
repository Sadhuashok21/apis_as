from typing import Dict, Any, Optional, Tuple
from ..provider_base import BaseVideoProvider


class MockTestProvider(BaseVideoProvider):
    """
    Deterministic provider for automated testing and CI/CD validation.
    """

    provider_id = "mock_test_provider"
    display_name = "ASAI Mock Simulation Provider (CI / Tests)"

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "text_to_video": True,
            "image_to_video": True,
            "first_last_frame": True,
            "video_extension": True,
            "video_to_video_edit": True,
            "character_reference": True,
            "native_camera_control": True,
            "supported_aspect_ratios": ["16:9", "9:16", "1:1", "2.39:1"],
            "supported_resolutions": ["512x512", "720p", "1080p"],
            "max_duration_seconds": 30,
            "min_vram_mb": 0,
            "is_offline_capable": True,
        }

    def check_availability(self) -> Dict[str, Any]:
        return {"available": True, "status": "Ready", "details": "Simulated mock provider", "vram_free_mb": 6000}

    def validate_request(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, ""

    def estimate_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"vram_required_mb": 0, "hardware": "CPU Mock", "estimated_seconds": 0.1}

    def generate(self, job_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "COMPLETED", "output_path": "/mock/test/path.mp4", "duration": 4.0}

    def extend_video(self, job_id: str, original_clip_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "COMPLETED", "output_path": "/mock/test/extended.mp4"}

    def edit_video(self, job_id: str, source_video_path: str, instruction: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "COMPLETED", "output_path": "/mock/test/edited.mp4"}

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        return {"status": "COMPLETED", "progress": 100}

    def cancel(self, job_id: str) -> bool:
        return True

    def retrieve_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        return None
