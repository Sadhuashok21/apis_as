import math
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ASAIModelConfig


class CausalSelfAttention(nn.Module):
    """
    Multi-Head Causal Self-Attention (MHA) with Lower-Triangular Causal Masking
    and optional Key-Value (KV) caching for fast autoregressive generation.
    """

    def __init__(self, config: ASAIModelConfig):
        super().__init__()
        assert config.d_model % config.n_head == 0, "d_model must be divisible by n_head"

        self.n_head = config.n_head
        self.d_model = config.d_model
        self.head_dim = config.d_model // config.n_head

        # Combined Q, K, V projection in a single matrix multiplication
        self.c_attn = nn.Linear(config.d_model, 3 * config.d_model, bias=config.bias)
        # Output projection
        self.c_proj = nn.Linear(config.d_model, config.d_model, bias=config.bias)

        # Regularization
        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)

        # Causal mask: upper triangle is -inf so tokens cannot attend to future positions
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(config.context_length, config.context_length))
            .view(1, 1, config.context_length, config.context_length)
        )

    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        B, T, C = x.size() # Batch size, sequence length, embedding dimension

        # Compute query, key, values for all heads in batch
        qkv = self.c_attn(x)
        q, k, v = qkv.split(self.d_model, dim=2)

        # Reshape to (B, n_head, T, head_dim)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        # KV caching for fast sequential generation
        if kv_cache is not None:
            prev_k, prev_v = kv_cache
            k = torch.cat([prev_k, k], dim=2)
            v = torch.cat([prev_v, v], dim=2)

        new_kv_cache = (k, v) if use_cache else None
        current_seq_len = k.size(2)

        # Scaled dot-product attention: (Q @ K^T) / sqrt(head_dim)
        # Use PyTorch 2.0+ scaled_dot_product_attention (Flash/Memory-Efficient Attention) when available without KV cache
        if hasattr(F, "scaled_dot_product_attention") and kv_cache is None:
            # Native causal flash attention
            y = F.scaled_dot_product_attention(
                q, k, v,
                attn_mask=None,
                dropout_p=self.attn_dropout.p if self.training else 0.0,
                is_causal=True
            )
        else:
            # Manual causal attention for KV caching or compatibility
            att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            # Apply causal mask up to current sequence length
            causal_mask = self.bias[:, :, current_seq_len - T:current_seq_len, :current_seq_len]
            att = att.masked_fill(causal_mask == 0, float("-inf"))
            att = F.softmax(att, dim=-1)
            att = self.attn_dropout(att)
            y = att @ v

        # Re-assemble all head outputs side by side
        y = y.transpose(1, 2).contiguous().view(B, T, C)

        # Output projection
        y = self.resid_dropout(self.c_proj(y))
        return y, new_kv_cache
