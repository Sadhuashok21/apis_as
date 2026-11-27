import json
from typing import List, Tuple, Dict, Any
import torch
from torch.utils.data import Dataset

from asai.services.neural_network.tokenizer import ASAITokenizer


class PretrainDataset(Dataset):
    """
    Dataset for Autoregressive Next-Token Prediction language modeling pretraining.
    Chunks continuous 1D tokenized data into sequences of length `context_length` with configurable stride.
    """

    def __init__(self, token_ids: List[int], context_length: int = 256, stride: int = 64):
        self.context_length = context_length
        self.stride = stride
        self.data = torch.tensor(token_ids, dtype=torch.long)
        self.length = max(0, (len(self.data) - context_length - 1) // stride)

    def __len__(self) -> int:
        return self.length

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        start = idx * self.stride
        x = self.data[start : start + self.context_length]
        y = self.data[start + 1 : start + self.context_length + 1]
        return x, y


class InstructionDataset(Dataset):
    """
    Supervised Fine-Tuning (SFT) Dataset with Loss Masking.
    Computes Cross-Entropy loss ONLY on Assistant tokens (masking User tokens with -100).
    """

    def __init__(
        self,
        jsonl_path: str,
        tokenizer: ASAITokenizer,
        context_length: int = 256
    ):
        self.tokenizer = tokenizer
        self.context_length = context_length
        self.samples: List[Tuple[torch.Tensor, torch.Tensor]] = []

        self._load_and_tokenize(jsonl_path)

    def _load_and_tokenize(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                messages = data.get("messages", [])
                if len(messages) < 2:
                    continue

                # Construct sequence with loss mask
                input_ids: List[int] = [self.tokenizer.bos_token_id]
                target_ids: List[int] = [-100] # Mask BOS token

                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "").strip()

                    if role == "user":
                        u_tokens = self.tokenizer.encode(f"<user> {content}", add_special_tokens=False)
                        input_ids.extend(u_tokens)
                        # User tokens are masked from loss computation with -100!
                        target_ids.extend([-100] * len(u_tokens))
                    elif role == "assistant":
                        # Add assistant marker and response
                        prefix_tokens = self.tokenizer.encode("<assistant>", add_special_tokens=False)
                        input_ids.extend(prefix_tokens)
                        target_ids.extend([-100] * len(prefix_tokens))

                        resp_tokens = self.tokenizer.encode(f" {content}", add_special_tokens=False)
                        resp_tokens.append(self.tokenizer.eos_token_id)
                        input_ids.extend(resp_tokens)
                        # Assistant response tokens are LEARNED (target == input)!
                        target_ids.extend(resp_tokens)

                # Truncate if exceeds context_length + 1
                max_len = self.context_length + 1
                if len(input_ids) > max_len:
                    input_ids = input_ids[:max_len]
                    target_ids = target_ids[:max_len]

                # Create autoregressive pair: x predicts y (shifted by 1)
                x_seq = input_ids[:-1]
                y_seq = target_ids[1:]

                # Pad sequences to context_length
                pad_len = self.context_length - len(x_seq)
                if pad_len > 0:
                    x_seq.extend([self.tokenizer.pad_token_id] * pad_len)
                    y_seq.extend([-100] * pad_len)

                self.samples.append((
                    torch.tensor(x_seq, dtype=torch.long),
                    torch.tensor(y_seq, dtype=torch.long)
                ))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.samples[idx]
