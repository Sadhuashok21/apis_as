import json
import logging
import random
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import httpx
from django.conf import settings

logger = logging.getLogger("asai.comfyui")


class ComfyUIClient:
    """
    Client for interacting with local or private ComfyUI generation node.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or getattr(settings, "COMFYUI_BASE_URL", "http://127.0.0.1:8188")).rstrip("/")
        self.timeout = 300.0

    def is_alive(self) -> bool:
        """Check if ComfyUI instance is actively running."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/system_stats")
                return res.status_code == 200
        except Exception:
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Fetch VRAM and device stats from ComfyUI."""
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"{self.base_url}/system_stats")
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return {}

    def get_checkpoints(self) -> List[str]:
        """Fetch list of available checkpoints installed in ComfyUI."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
                if res.status_code == 200:
                    data = res.json()
                    input_info = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
                    ckpt_list = input_info.get("ckpt_name", [[]])[0]
                    if isinstance(ckpt_list, list):
                        return ckpt_list
        except Exception as e:
            logger.warning(f"Failed to query ComfyUI checkpoints: {e}")
        return []

    def build_sd15_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 768,
        checkpoint: Optional[str] = None,
        steps: int = 20,
        cfg: float = 7.0,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Builds standard ComfyUI API graph workflow for Text-to-Image.
        """
        ckpt_name = checkpoint
        if not ckpt_name:
            available = self.get_checkpoints()
            if available:
                ckpt_name = available[0]
            else:
                ckpt_name = "v1-5-pruned-emaonly.safetensors"

        actual_seed = seed if seed is not None else random.randint(100000000, 999999999)

        return {
            "3": {
                "inputs": {
                    "seed": actual_seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": ckpt_name
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt or "blurry, low quality, deformed, watermark, text, signature",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ASAI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

    def queue_prompt(self, workflow: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Submits prompt workflow to ComfyUI.
        Returns (success: bool, prompt_id: str, raw_response: dict)
        """
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(f"{self.base_url}/prompt", json={"prompt": workflow})
                if res.status_code == 200:
                    data = res.json()
                    prompt_id = data.get("prompt_id", "")
                    return True, prompt_id, data
                else:
                    return False, "", {"error": f"ComfyUI HTTP {res.status_code}: {res.text}"}
        except httpx.ConnectError:
            return False, "", {"error": f"ComfyUI node offline at {self.base_url}"}
        except Exception as e:
            return False, "", {"error": str(e)}

    def check_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        Check execution history of a prompt_id in ComfyUI.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{self.base_url}/history/{prompt_id}")
                if res.status_code == 200:
                    return res.json().get(prompt_id, {})
        except Exception:
            pass
        return {}

    def fetch_image_bytes(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """
        Download rendered image directly from ComfyUI /view.
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.get(f"{self.base_url}/view", params=params)
                if res.status_code == 200:
                    return res.content
        except Exception as e:
            logger.error(f"Failed to fetch image {filename} from ComfyUI: {e}")
        return None

    def save_rendered_image(self, filename: str, subfolder: str = "") -> Tuple[Optional[str], Optional[str]]:
        """
        Fetches the image from ComfyUI, saves it to Django's MEDIA_ROOT / asai / generated,
        and returns (saved_relative_path, media_url).
        """
        raw_bytes = self.fetch_image_bytes(filename, subfolder)
        if not raw_bytes:
            return None, None

        asai_media_dir = Path(settings.MEDIA_ROOT) / "asai" / "generated"
        asai_media_dir.mkdir(parents=True, exist_ok=True)

        target_file = asai_media_dir / filename
        with open(target_file, "wb") as f:
            f.write(raw_bytes)

        relative_path = f"asai/generated/{filename}"
        media_url = f"{settings.MEDIA_URL}asai/generated/{filename}"
        return relative_path, media_url


comfyui_client = ComfyUIClient()
