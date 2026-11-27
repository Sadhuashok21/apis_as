from ..capability_registry import CapabilityRegistry
from .ffmpeg_provider import FFmpegComposerProvider
from .comfyui_provider import ComfyUIVideoProvider
from .mock_provider import MockTestProvider

# Register providers
CapabilityRegistry.register_provider("comfyui_video", ComfyUIVideoProvider())
CapabilityRegistry.register_provider("ffmpeg_composer", FFmpegComposerProvider())
CapabilityRegistry.register_provider("mock_test_provider", MockTestProvider())

__all__ = [
    "FFmpegComposerProvider",
    "ComfyUIVideoProvider",
    "MockTestProvider",
]
