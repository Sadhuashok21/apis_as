import logging
from typing import Dict, Any, List, Optional
import torch

logger = logging.getLogger("asai.flow.capabilities")


class HardwareProbe:
    """
    Introspects host GPU and VRAM availability to prevent OOM errors on RTX 3050 6GB.
    """

    @staticmethod
    def get_gpu_info() -> Dict[str, Any]:
        cuda_available = torch.cuda.is_available()
        if not cuda_available:
            return {
                "cuda_available": False,
                "device_name": "CPU Only",
                "total_vram_mb": 0,
                "free_vram_mb": 0,
                "hardware_tier": "cpu_fallback",
                "recommended_max_res": "512x512",
                "safe_duration_sec": 4,
            }

        device_name = torch.cuda.get_device_name(0)
        total_bytes = torch.cuda.get_device_properties(0).total_memory
        total_vram_mb = round(total_bytes / (1024 * 1024), 1)

        # Estimate currently allocated & free VRAM
        try:
            allocated = torch.cuda.memory_allocated(0)
            reserved = torch.cuda.memory_reserved(0)
            free_vram_mb = max(0.0, round((total_bytes - reserved) / (1024 * 1024), 1))
        except Exception:
            free_vram_mb = total_vram_mb * 0.75

        # Classify hardware tier
        if total_vram_mb <= 6500:
            hardware_tier = "entry_gpu_6gb"
            recommended_max_res = "512x512"
            safe_duration_sec = 4
        elif total_vram_mb <= 12500:
            hardware_tier = "mid_gpu_8_12gb"
            recommended_max_res = "768x768"
            safe_duration_sec = 8
        else:
            hardware_tier = "high_gpu_16gb_plus"
            recommended_max_res = "1280x720"
            safe_duration_sec = 16

        return {
            "cuda_available": True,
            "device_name": device_name,
            "total_vram_mb": total_vram_mb,
            "free_vram_mb": free_vram_mb,
            "hardware_tier": hardware_tier,
            "recommended_max_res": recommended_max_res,
            "safe_duration_sec": safe_duration_sec,
        }


class CapabilityRegistry:
    """
    Central registry for ASAI Flow model providers and hardware-adaptive capabilities.
    """

    _providers: Dict[str, Any] = {}

    @classmethod
    def register_provider(cls, provider_id: str, provider_instance: Any):
        cls._providers[provider_id] = provider_instance
        logger.info(f"Registered Flow video provider: {provider_id}")

    @classmethod
    def get_provider(cls, provider_id: str):
        return cls._providers.get(provider_id)

    @classmethod
    def list_providers(cls) -> List[Dict[str, Any]]:
        gpu = HardwareProbe.get_gpu_info()
        catalog = []

        for pid, provider in cls._providers.items():
            caps = provider.get_capabilities()
            avail = provider.check_availability()

            # Adapt caps to hardware realities
            is_compatible = True
            incompatibility_reason = ""
            if caps.get("min_vram_mb", 0) > gpu["total_vram_mb"] and gpu["cuda_available"]:
                is_compatible = False
                incompatibility_reason = (
                    f"Model requires {caps.get('min_vram_mb')}MB VRAM, "
                    f"exceeding your RTX GPU capacity ({gpu['total_vram_mb']}MB)."
                )

            catalog.append({
                "provider_id": pid,
                "name": provider.display_name,
                "capabilities": caps,
                "availability": avail,
                "is_hardware_compatible": is_compatible,
                "incompatibility_reason": incompatibility_reason,
                "hardware_profile": {
                    "vram_headroom_mb": gpu["free_vram_mb"],
                    "recommended_resolution": gpu["recommended_max_res"],
                }
            })

        return catalog

    @classmethod
    def translate_camera_prompt(cls, camera_framing: str, camera_movement: str) -> str:
        """
        Translates creative camera controls into prompt tokens for models that
        interpret camera directions textually rather than via 3D matrix.
        """
        tokens = []
        if camera_framing and camera_framing.lower() != "default":
            tokens.append(f"{camera_framing.lower()} cinematography")
        if camera_movement and camera_movement.lower() != "static":
            tokens.append(f"smooth {camera_movement.lower()} camera movement")
        return ", ".join(tokens)
