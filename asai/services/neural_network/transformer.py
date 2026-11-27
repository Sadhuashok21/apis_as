import math
from typing import Optional, Tuple, List, Union
import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ASAIModelConfig
from .attention import CausalSelfAttention


class FeedForward(nn.Module):
    """
    Position-wise Feed-Forward Network (FFN) with GELU activation.
    Expands d_model -> d_ff -> d_model with residual connection.
    """

    def __init__(self, config: ASAIModelConfig):
        super().__init__()
        self.c_fc = nn.Linear(config.d_model, config.d_ff, bias=config.bias)
        self.gelu = nn.GELU()
        self.c_proj = nn.Linear(config.d_ff, config.d_model, bias=config.bias)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.c_fc(x)
        x = self.gelu(x)
        x = self.c_proj(x)
        x = self.dropout(x)
        return x


class TransformerDecoderBlock(nn.Module):
    """
    Standard Pre-LayerNorm Transformer Decoder block.
    Flow: x -> LayerNorm -> CausalAttention -> (+) -> LayerNorm -> FeedForward -> (+)
    """

    def __init__(self, config: ASAIModelConfig):
        super().__init__()
        self.ln_1 = nn.LayerNorm(config.d_model, elementwise_affine=config.bias)
        self.attn = CausalSelfAttention(config)
        self.ln_2 = nn.LayerNorm(config.d_model, elementwise_affine=config.bias)
        self.mlp = FeedForward(config)

    def forward(
        self,
        x: torch.Tensor,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        # Attention sub-layer with Pre-LN and residual
        attn_out, new_cache = self.attn(self.ln_1(x), kv_cache=kv_cache, use_cache=use_cache)
        x = x + attn_out

        # Feed-forward sub-layer with Pre-LN and residual
        x = x + self.mlp(self.ln_2(x))
        return x, new_cache


class ASAITransformer(nn.Module):
    """
    Complete ASAI GPT-style Decoder-Only Autoregressive Transformer.
    Built entirely from scratch in raw PyTorch without external LLM libraries.
    """

    def __init__(self, config: ASAIModelConfig):
        super().__init__()
        self.config = config

        self.transformer = nn.ModuleDict(dict(
            # Token embedding table: maps token IDs -> d_model vector
            wte = nn.Embedding(config.vocab_size, config.d_model),
            # Learned position embeddings: maps sequence position 0..T-1 -> d_model vector
            wpe = nn.Embedding(config.context_length, config.d_model),
            drop = nn.Dropout(config.dropout),
            # Stack of L Decoder blocks
            h = nn.ModuleList([TransformerDecoderBlock(config) for _ in range(config.n_layer)]),
            # Final LayerNorm
            ln_f = nn.LayerNorm(config.d_model, elementwise_affine=config.bias),
        ))

        # Output projection head: maps hidden representation -> vocabulary logits
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        # Weight tying (optional, saves ~2M parameters if enabled)
        if config.tie_word_embeddings:
            self.lm_head.weight = self.transformer.wte.weight

        # Initialize all weights according to GPT standards
        self.apply(self._init_weights)

        # Apply special scaled init to the residual projections, per GPT-2 paper
        for pn, p in self.named_parameters():
            if pn.endswith("c_proj.weight"):
                torch.nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * config.n_layer))

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
            if module.weight is not None:
                torch.nn.init.ones_(module.weight)

    def get_num_params(self, non_embedding: bool = False) -> int:
        """Calculates total trainable parameter count."""
        n_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if non_embedding:
            n_params -= self.transformer.wpe.weight.numel()
        return n_params

    def forward(
        self,
        idx: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        kv_caches: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[List[Tuple[torch.Tensor, torch.Tensor]]]]:
        """
        Forward pass.
        Args:
            idx: Tensor of token indices with shape (Batch, Seq_Len)
            targets: Optional tensor of target token indices with shape (Batch, Seq_Len)
            kv_caches: Optional list of KV caches for each block
            use_cache: If True, returns updated KV caches for fast generation
        Returns:
            logits: (Batch, Seq_Len, vocab_size)
            loss: Cross-entropy scalar loss (if targets provided)
            new_caches: List of updated KV caches
        """
        device = idx.device
        b, t = idx.size()
        assert t <= self.config.context_length, (
            f"Cannot forward sequence of length {t}, block size is {self.config.context_length}"
        )

        pos = torch.arange(0, t, dtype=torch.long, device=device) # (t)

        # Forward the ASAI Transformer model
        tok_emb = self.transformer.wte(idx) # token embeddings of shape (b, t, d_model)
        pos_emb = self.transformer.wpe(pos) # position embeddings of shape (t, d_model)
        x = self.transformer.drop(tok_emb + pos_emb)

        new_caches = [] if use_cache else None
        for i, block in enumerate(self.transformer.h):
            block_cache = kv_caches[i] if kv_caches is not None else None
            x, cache = block(x, kv_cache=block_cache, use_cache=use_cache)
            if use_cache:
                new_caches.append(cache)

        x = self.transformer.ln_f(x)

        if targets is not None:
            # If targets given, compute full cross-entropy loss
            logits = self.lm_head(x)
            # Flatten across sequence dimension for CrossEntropyLoss
            # ignore_index=-100 ensures prompt tokens are not penalized during instruction tuning!
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
                ignore_index=-100
            )
        else:
            # Inference optimization: only forward the lm_head on the very last token
            logits = self.lm_head(x[:, [-1], :])
            loss = None

        return logits, loss, new_caches

    @torch.no_grad()
    def generate(
        self,
        idx: torch.Tensor,
        max_new_tokens: int = 150,
        temperature: float = 0.6,
        top_k: Optional[int] = 30,
        top_p: Optional[float] = 0.85,
        repetition_penalty: float = 1.25,
        no_repeat_ngram_size: int = 3,
        eos_token_id: Optional[int] = None
    ) -> torch.Tensor:
        """
        Generates tokens autoregressively from a starting prompt tensor `idx`.
        Guarantees degeneration-free text through strict N-gram repetition blocking,
        sliding-window frequency penalties, and adaptive tail pruning.
        """
        eos_id = eos_token_id if eos_token_id is not None else self.config.eos_token_id

        for _ in range(max_new_tokens):
            # Crop context if sequence exceeds context_length
            idx_cond = idx if idx.size(1) <= self.config.context_length else idx[:, -self.config.context_length:]

            # Forward the model to get the logits for the last token
            logits, _, _ = self(idx_cond)
            logits = logits[:, -1, :].clone() # shape (B, vocab_size)

            # 1. No-Repeat N-Gram Blocking (prevents repeating loops)
            if no_repeat_ngram_size > 0 and idx.size(1) >= no_repeat_ngram_size:
                cur_tokens = idx[0].tolist()
                ngram_len = no_repeat_ngram_size
                prev_ngrams = {}
                for i in range(len(cur_tokens) - ngram_len + 1):
                    prefix = tuple(cur_tokens[i : i + ngram_len - 1])
                    next_tok = cur_tokens[i + ngram_len - 1]
                    if prefix not in prev_ngrams:
                        prev_ngrams[prefix] = set()
                    prev_ngrams[prefix].add(next_tok)

                cur_prefix = tuple(cur_tokens[-(ngram_len - 1):])
                if cur_prefix in prev_ngrams:
                    banned_tokens = prev_ngrams[cur_prefix]
                    for b_tok in banned_tokens:
                        logits[0, b_tok] = -float("Inf")

            # 2. Sliding-Window Repetition Penalty (last 32 tokens only)
            if repetition_penalty != 1.0:
                recent_window = idx[0, max(0, idx.size(1) - 32):].tolist()
                for token_id in set(recent_window):
                    count = recent_window.count(token_id)
                    penalty = repetition_penalty ** count
                    if logits[0, token_id] < 0:
                        logits[0, token_id] *= penalty
                    else:
                        logits[0, token_id] /= penalty

            # 3. Temperature & Sampling
            if temperature > 0.0:
                logits = logits / temperature

                # Top-K filtering
                if top_k is not None and top_k > 0:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float("Inf")

                # Top-P (Nucleus) filtering
                if top_p is not None and 0.0 < top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0
                    indices_to_remove = sorted_indices[sorted_indices_to_remove]
                    logits[0, indices_to_remove] = -float("Inf")

                # Tail probability pruning
                probs = F.softmax(logits, dim=-1)
                max_prob = torch.max(probs)
                probs[probs < 0.03 * max_prob] = 0.0
                prob_sum = probs.sum()
                if prob_sum > 0:
                    probs = probs / prob_sum
                    idx_next = torch.multinomial(probs, num_samples=1)
                else:
                    idx_next = torch.argmax(logits, dim=-1, keepdim=True)
            else:
                idx_next = torch.argmax(logits, dim=-1, keepdim=True)

            idx = torch.cat((idx, idx_next), dim=1)

            if idx_next.item() == eos_id:
                break

        return idx
