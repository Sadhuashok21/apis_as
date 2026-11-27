import os
import math
import time
from typing import Optional, Dict, Any
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from asai.services.neural_network.transformer import ASAITransformer
from asai.services.neural_network.config import ASAIModelConfig


class ASAITrainer:
    """
    Complete PyTorch training engine for pretraining and instruction fine-tuning
    the ASAI Transformer on the NVIDIA RTX 3050 GPU (with CPU fallback).
    """

    def __init__(
        self,
        model: ASAITransformer,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        learning_rate: float = 5e-4,
        weight_decay: float = 0.1,
        max_epochs: int = 5,
        grad_accum_steps: int = 2,
        clip_grad_norm: float = 1.0,
        output_dir: str = "checkpoints",
        checkpoint_name: str = "asai_mini_checkpoint.pt"
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.learning_rate = learning_rate
        self.max_epochs = max_epochs
        self.grad_accum_steps = grad_accum_steps
        self.clip_grad_norm = clip_grad_norm
        self.output_dir = output_dir
        self.checkpoint_name = checkpoint_name

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.use_amp = (self.device.type == "cuda")

        # Configure AdamW with weight decay separation
        self.optimizer = self._configure_optimizers(weight_decay, learning_rate)

        # Learning rate scheduler (Cosine Annealing)
        total_steps = len(train_loader) * max_epochs // grad_accum_steps
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=max(1, total_steps),
            eta_min=learning_rate * 0.1
        )

        # Automatic Mixed Precision (AMP) Scaler for RTX 3050 Tensor Cores
        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)

        os.makedirs(self.output_dir, exist_ok=True)

    def _configure_optimizers(self, weight_decay: float, lr: float) -> torch.optim.AdamW:
        """
        Separates parameters into decay and no-decay groups (no decay on LayerNorm & biases).
        """
        decay_params = []
        nodecay_params = []

        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue
            if param.dim() >= 2:
                decay_params.append(param)
            else:
                nodecay_params.append(param)

        optim_groups = [
            {"params": decay_params, "weight_decay": weight_decay},
            {"params": nodecay_params, "weight_decay": 0.0},
        ]

        # Use fused AdamW if supported by CUDA driver
        fused = self.use_amp and hasattr(torch.optim.AdamW, "fused")
        optimizer = torch.optim.AdamW(optim_groups, lr=lr, betas=(0.9, 0.95), eps=1e-8)
        return optimizer

    def train(self) -> Dict[str, Any]:
        """Executes full training loop across epochs with validation logging."""
        print(f"\n{'='*70}")
        print(f"Starting ASAI Neural Network Training on device: {self.device}")
        print(f"Total Model Parameters: {self.model.get_num_params():,}")
        print(f"Epochs: {self.max_epochs} | Grad Accumulation: {self.grad_accum_steps} | AMP: {self.use_amp}")
        print(f"{'='*70}\n")

        best_val_loss = float("inf")
        step = 0
        training_start = time.time()

        for epoch in range(1, self.max_epochs + 1):
            self.model.train()
            epoch_loss = 0.0
            epoch_start = time.time()
            self.optimizer.zero_grad(set_to_none=True)

            for batch_idx, (x, y) in enumerate(self.train_loader):
                x = x.to(self.device, non_blocking=True)
                y = y.to(self.device, non_blocking=True)

                # Forward pass with Automatic Mixed Precision
                with torch.amp.autocast("cuda", enabled=self.use_amp):
                    logits, loss, _ = self.model(x, targets=y)
                    loss = loss / self.grad_accum_steps

                # Backward pass with scaled gradients
                self.scaler.scale(loss).backward()
                epoch_loss += loss.item() * self.grad_accum_steps

                if (batch_idx + 1) % self.grad_accum_steps == 0:
                    # Unscale gradients for clipping
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clip_grad_norm)

                    # Optimizer step & scaler update
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.optimizer.zero_grad(set_to_none=True)
                    self.scheduler.step()

                    step += 1

                    if step % 10 == 0:
                        current_loss = loss.item() * self.grad_accum_steps
                        current_ppl = math.exp(min(current_loss, 20.0))
                        lr = self.optimizer.param_groups[0]["lr"]
                        print(
                            f"Epoch [{epoch}/{self.max_epochs}] Step {step} | "
                            f"Loss: {current_loss:.4f} | Perplexity: {current_ppl:.2f} | "
                            f"LR: {lr:.6f}"
                        )

            avg_train_loss = epoch_loss / len(self.train_loader)
            train_ppl = math.exp(min(avg_train_loss, 20.0))
            epoch_time = time.time() - epoch_start

            print(f"\n--- Epoch {epoch} Complete ({epoch_time:.1f}s) ---")
            print(f"Train Loss: {avg_train_loss:.4f} | Train Perplexity: {train_ppl:.2f}")

            # Validation
            val_loss = self.evaluate()
            if val_loss is not None:
                val_ppl = math.exp(min(val_loss, 20.0))
                print(f"Val Loss: {val_loss:.4f} | Val Perplexity: {val_ppl:.2f}")

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self.save_checkpoint(is_best=True)
                    print(f"Saved new best model checkpoint to {self.output_dir}!")
            else:
                self.save_checkpoint(is_best=True)

            print("-" * 50 + "\n")

        total_time = time.time() - training_start
        print(f"Training completed in {total_time:.1f} seconds.")
        return {
            "total_time_sec": total_time,
            "final_train_loss": avg_train_loss,
            "best_val_loss": best_val_loss
        }

    @torch.no_grad()
    def evaluate(self) -> Optional[float]:
        """Calculates validation cross-entropy loss."""
        if not self.val_loader:
            return None

        self.model.eval()
        total_loss = 0.0

        for x, y in self.val_loader:
            x = x.to(self.device, non_blocking=True)
            y = y.to(self.device, non_blocking=True)
            with torch.amp.autocast("cuda", enabled=self.use_amp):
                _, loss, _ = self.model(x, targets=y)
                total_loss += loss.item()

        self.model.train()
        return total_loss / len(self.val_loader)

    def save_checkpoint(self, is_best: bool = False):
        """Persists trained weights and model configuration to disk."""
        ckpt_path = os.path.join(self.output_dir, self.checkpoint_name)
        checkpoint = {
            "model": self.model.state_dict(),
            "config": self.model.config.__dict__,
            "optimizer": self.optimizer.state_dict(),
            "saved_at": time.time()
        }
        torch.save(checkpoint, ckpt_path)
