from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ASAIModelConfig:
    """
    Configuration specification for the ASAI custom Decoder-only Transformer.
    Default settings optimized for NVIDIA RTX 3050 (6GB VRAM) and CPU inference.
    """
    # Architecture dimensions
    vocab_size: int = 8192          # Vocabulary size for custom BPE tokenizer
    context_length: int = 256       # Maximum sequence / context window (T)
    n_layer: int = 4                # Number of Transformer Decoder blocks (L)
    n_head: int = 4                 # Number of attention heads (h)
    d_model: int = 256              # Embedding / model dimension (d_model)
    d_ff: int = 1024                # Feed-forward hidden dimension (4 * d_model)
    dropout: float = 0.1            # Dropout rate
    bias: bool = True               # Whether to include bias in Linear and LayerNorm

    # Special token IDs
    pad_token_id: int = 0           # <pad>
    unk_token_id: int = 1           # <unk>
    bos_token_id: int = 2           # <s> (Beginning of Sequence)
    eos_token_id: int = 3           # </s> (End of Sequence)
    user_token_id: int = 4          # <user>
    assistant_token_id: int = 5     # <assistant>

    # Training and generation hyperparameters
    tie_word_embeddings: bool = False # If True, tie LM head to token embedding
    model_name: str = "ASAI-Mini-7M"
    version: str = "1.0.0"

    def __post_init__(self):
        assert self.d_model % self.n_head == 0, (
            f"d_model ({self.d_model}) must be divisible by n_head ({self.n_head})"
        )
