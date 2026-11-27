import os
import logging
from typing import Optional, Tuple, Dict, Any
import torch

from .config import ASAIModelConfig
from .tokenizer import ASAITokenizer
from .transformer import ASAITransformer
from .inference import ASAIInferenceEngine

logger = logging.getLogger("asai.neural_network")


class ASAIModelManager:
    """
    Singleton manager for loading, caching, and serving the custom ASAI neural network.
    Automatically detects CUDA GPU acceleration or falls back to CPU.
    """
    _instance: Optional["ASAIModelManager"] = None

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.config = ASAIModelConfig()
        self.tokenizer = ASAITokenizer(vocab_size=self.config.vocab_size)
        self.model: Optional[ASAITransformer] = None
        self.engine: Optional[ASAIInferenceEngine] = None
        self.checkpoint_loaded: bool = False
        self.checkpoint_path: Optional[str] = None

        self._initialize()

    @classmethod
    def get_instance(cls, force_reload: bool = False) -> "ASAIModelManager":
        if cls._instance is None or force_reload:
            cls._instance = ASAIModelManager()
        return cls._instance

    def reload(self):
        """Reloads the tokenizer and model weights from disk."""
        self._initialize()

    def _initialize(self):
        """Loads tokenizer and neural network checkpoint from disk."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tokenizer_dir = os.path.join(base_dir, "tokenizer_data")
        checkpoints_dir = os.path.join(os.path.dirname(base_dir), "..", "checkpoints")

        # 1. Load custom Tokenizer if vocabulary exists
        if os.path.exists(os.path.join(tokenizer_dir, "vocab.json")):
            try:
                self.tokenizer.load(tokenizer_dir)
            except Exception as e:
                logger.warning(f"Could not load custom tokenizer from {tokenizer_dir}: {e}")

        # 2. Check for trained weights checkpoint and config
        default_ckpt = os.path.join(checkpoints_dir, "asai_mini_checkpoint.pt")
        if os.path.exists(default_ckpt):
            try:
                ckpt = torch.load(default_ckpt, map_location=self.device)
                if isinstance(ckpt, dict) and "config" in ckpt:
                    self.config = ASAIModelConfig(**ckpt["config"])
                elif len(self.tokenizer.token_to_id) > 0:
                    self.config.vocab_size = len(self.tokenizer.token_to_id)

                self.model = ASAITransformer(self.config)
                state_dict = ckpt["model"] if (isinstance(ckpt, dict) and "model" in ckpt) else ckpt
                self.model.load_state_dict(state_dict)
                self.checkpoint_loaded = True
                self.checkpoint_path = default_ckpt
                logger.info(f"Loaded trained ASAI checkpoint from {default_ckpt}")
            except Exception as e:
                logger.error(f"Error loading checkpoint {default_ckpt}: {e}")
                self.model = ASAITransformer(self.config)
        else:
            if len(self.tokenizer.token_to_id) > 0:
                self.config.vocab_size = len(self.tokenizer.token_to_id)
            self.model = ASAITransformer(self.config)
            logger.info("No pre-existing checkpoint found. Initialized with fresh weights.")

        # 3. Instantiate local Inference Engine
        self.engine = ASAIInferenceEngine(self.model, self.tokenizer, self.device)

    def get_status(self) -> Dict[str, Any]:
        """Returns neural network hardware and architecture status."""
        vram_mb = 0
        device_name = "CPU"
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))

        return {
            "model_name": self.config.model_name,
            "architecture": "Decoder-Only Autoregressive Transformer",
            "parameters": self.model.get_num_params() if self.model else 0,
            "vocabulary_size": len(self.tokenizer.token_to_id),
            "context_length": self.config.context_length,
            "n_layers": self.config.n_layer,
            "n_heads": self.config.n_head,
            "d_model": self.config.d_model,
            "device": str(self.device),
            "device_name": device_name,
            "vram_total_mb": vram_mb,
            "cuda_available": torch.cuda.is_available(),
            "checkpoint_loaded": self.checkpoint_loaded,
            "checkpoint_path": self.checkpoint_path or "Initialized (Ready for training)"
        }


def get_ai_engine() -> ASAIInferenceEngine:
    return ASAIModelManager.get_instance().engine
