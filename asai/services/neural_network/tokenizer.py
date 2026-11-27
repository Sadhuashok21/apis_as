import os
import json
import re
from typing import List, Dict, Tuple, Optional


class ASAITokenizer:
    """
    Custom Byte-Pair Encoding (BPE) subword tokenizer built from scratch for ASAI.
    Operates on UTF-8 bytes to guarantee 0 Out-Of-Vocabulary (OOV) errors.
    """

    SPECIAL_TOKENS = [
        "<pad>",        # ID 0: Padding
        "<unk>",        # ID 1: Unknown
        "<s>",          # ID 2: Start of sequence
        "</s>",         # ID 3: End of sequence
        "<user>",       # ID 4: User dialogue marker
        "<assistant>",  # ID 5: Assistant dialogue marker
    ]

    def __init__(self, vocab_size: int = 8192):
        self.vocab_size = vocab_size

        # ID -> Token representation (bytes)
        self.id_to_token: Dict[int, bytes] = {}
        # Token representation (bytes) -> ID
        self.token_to_id: Dict[bytes, int] = {}

        # Merges: Tuple of (bytes, bytes) -> merged bytes
        self.merges: Dict[Tuple[bytes, bytes], bytes] = {}

        # Regex pre-tokenizer pattern (splits on whitespace, punctuation, contractions)
        self.split_pattern = re.compile(
            r"""'s|'t|'re|'ve|'m|'ll|'d| ?\w+| ?[^\s\w]+|\s+"""
        )

        self._init_base_vocab()

    def _init_base_vocab(self):
        """Initializes the special tokens and 256 individual byte tokens."""
        self.id_to_token.clear()
        self.token_to_id.clear()

        # 1. Register special tokens
        for idx, token_str in enumerate(self.SPECIAL_TOKENS):
            token_bytes = token_str.encode("utf-8")
            self.id_to_token[idx] = token_bytes
            self.token_to_id[token_bytes] = idx

        # 2. Register all 256 raw bytes (offset by len(SPECIAL_TOKENS))
        offset = len(self.SPECIAL_TOKENS)
        for b in range(256):
            token_bytes = bytes([b])
            token_id = offset + b
            self.id_to_token[token_id] = token_bytes
            self.token_to_id[token_bytes] = token_id

    @property
    def pad_token_id(self) -> int:
        return 0

    @property
    def unk_token_id(self) -> int:
        return 1

    @property
    def bos_token_id(self) -> int:
        return 2

    @property
    def eos_token_id(self) -> int:
        return 3

    @property
    def user_token_id(self) -> int:
        return 4

    @property
    def assistant_token_id(self) -> int:
        return 5

    def train_from_text(self, text: str, target_vocab_size: Optional[int] = None, min_frequency: int = 2):
        """
        Trains BPE merges iteratively on the provided text corpus up to target_vocab_size.
        """
        if target_vocab_size is None:
            target_vocab_size = self.vocab_size

        self._init_base_vocab()
        self.merges.clear()

        # Tokenize text into initial byte sequence chunks
        # Split text using split_pattern preserving whitespace
        words = self.split_pattern.findall(text)
        word_splits: List[List[bytes]] = [[bytes([b]) for b in w.encode("utf-8")] for w in words]

        num_merges = target_vocab_size - len(self.token_to_id)
        print(f"[ASAI Tokenizer] Base vocab: {len(self.token_to_id)} tokens. Training {num_merges} BPE merges...")

        for merge_i in range(num_merges):
            # Count pair frequencies
            pair_counts: Dict[Tuple[bytes, bytes], int] = {}
            for split in word_splits:
                for j in range(len(split) - 1):
                    pair = (split[j], split[j + 1])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

            if not pair_counts:
                break

            # Find most frequent pair
            best_pair, best_count = max(pair_counts.items(), key=lambda item: item[1])
            if best_count < min_frequency:
                break

            merged_token = best_pair[0] + best_pair[1]
            new_id = len(self.token_to_id)

            self.merges[best_pair] = merged_token
            self.id_to_token[new_id] = merged_token
            self.token_to_id[merged_token] = new_id

            # Apply merge to all word splits
            new_word_splits: List[List[bytes]] = []
            for split in word_splits:
                new_split: List[bytes] = []
                k = 0
                while k < len(split):
                    if k < len(split) - 1 and (split[k], split[k + 1]) == best_pair:
                        new_split.append(merged_token)
                        k += 2
                    else:
                        new_split.append(split[k])
                        k += 1
                new_word_splits.append(new_split)
            word_splits = new_word_splits

            if (merge_i + 1) % 500 == 0 or (merge_i + 1) == num_merges:
                print(f"  Merge {merge_i + 1}/{num_merges}: created token {merged_token!r} (frequency: {best_count})")

        print(f"[ASAI Tokenizer] Training complete. Final vocabulary size: {len(self.token_to_id)}")

    def _bpe(self, byte_list: List[bytes]) -> List[bytes]:
        """Applies learned BPE merges recursively to a sequence of byte tokens."""
        if len(byte_list) <= 1:
            return byte_list

        while True:
            # Find earliest mergeable pair
            min_merge_idx = None
            merge_candidate = None

            for i in range(len(byte_list) - 1):
                pair = (byte_list[i], byte_list[i + 1])
                if pair in self.merges:
                    merged = self.merges[pair]
                    if merged in self.token_to_id:
                        token_id = self.token_to_id[merged]
                        if min_merge_idx is None or token_id < min_merge_idx:
                            min_merge_idx = token_id
                            merge_candidate = (i, pair, merged)

            if merge_candidate is None:
                break

            i, pair, merged = merge_candidate
            byte_list = byte_list[:i] + [merged] + byte_list[i + 2:]

        return byte_list

    def encode(self, text: str, add_special_tokens: bool = False, add_eos: bool = False) -> List[int]:
        """Encodes an input string into token IDs, properly handling special dialogue tags."""
        if not text:
            return []

        token_ids: List[int] = []
        if add_special_tokens:
            token_ids.append(self.bos_token_id)

        # Split on special tokens first to preserve dialogue markers (<user>, <assistant>, </s>, etc.)
        special_pattern = r"(<pad>|<unk>|<s>|</s>|<user>|<assistant>)"
        chunks = re.split(special_pattern, text)

        for chunk in chunks:
            if not chunk:
                continue
            chunk_bytes = chunk.encode("utf-8")
            if chunk_bytes in self.token_to_id:
                token_ids.append(self.token_to_id[chunk_bytes])
                continue

            # Tokenize regular text chunk with BPE
            words = self.split_pattern.findall(chunk)
            for w in words:
                w_bytes = w.encode("utf-8")
                if w_bytes in self.token_to_id:
                    token_ids.append(self.token_to_id[w_bytes])
                    continue

                initial_bytes = [bytes([b]) for b in w_bytes]
                merged = self._bpe(initial_bytes)
                for m in merged:
                    token_ids.append(self.token_to_id.get(m, self.unk_token_id))

        if add_eos:
            token_ids.append(self.eos_token_id)

        return token_ids

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decodes token IDs back into a human-readable Unicode string."""
        byte_chunks: List[bytes] = []

        special_ids = {
            self.pad_token_id,
            self.unk_token_id,
            self.bos_token_id,
            self.eos_token_id,
            self.user_token_id,
            self.assistant_token_id,
        }

        for tid in token_ids:
            if skip_special_tokens and tid in special_ids:
                continue
            token_bytes = self.id_to_token.get(tid, b"")
            byte_chunks.append(token_bytes)

        full_bytes = b"".join(byte_chunks)
        return full_bytes.decode("utf-8", errors="replace")

    def save(self, directory: str):
        """Saves tokenizer vocabulary and merges to disk with hex encoding for robustness."""
        os.makedirs(directory, exist_ok=True)

        vocab_path = os.path.join(directory, "vocab.json")
        vocab_export = {token_bytes.hex(): tid for token_bytes, tid in self.token_to_id.items()}
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump(vocab_export, f, indent=2)

        merges_path = os.path.join(directory, "merges.json")
        merges_export = [[p1.hex(), p2.hex()] for (p1, p2) in self.merges.keys()]
        with open(merges_path, "w", encoding="utf-8") as f:
            json.dump(merges_export, f, indent=2)

        print(f"[ASAI Tokenizer] Saved vocabulary ({len(vocab_export)} entries) to {directory}")

    def load(self, directory: str):
        """Loads tokenizer vocabulary and merges from disk."""
        vocab_path = os.path.join(directory, "vocab.json")
        merges_path = os.path.join(directory, "merges.json")
        merges_txt = os.path.join(directory, "merges.txt")

        if not os.path.exists(vocab_path):
            raise FileNotFoundError(f"Vocab file not found at {vocab_path}")

        with open(vocab_path, "r", encoding="utf-8") as f:
            vocab_export: Dict[str, int] = json.load(f)

        self.token_to_id.clear()
        self.id_to_token.clear()
        for token_hex_or_str, tid in vocab_export.items():
            try:
                token_bytes = bytes.fromhex(token_hex_or_str)
            except ValueError:
                token_bytes = token_hex_or_str.encode("latin1")
            self.token_to_id[token_bytes] = tid
            self.id_to_token[tid] = token_bytes

        self.merges.clear()
        if os.path.exists(merges_path):
            with open(merges_path, "r", encoding="utf-8") as f:
                merges_export = json.load(f)
                for pair in merges_export:
                    p1 = bytes.fromhex(pair[0])
                    p2 = bytes.fromhex(pair[1])
                    self.merges[(p1, p2)] = p1 + p2
        elif os.path.exists(merges_txt):
            with open(merges_txt, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" ")
                    if len(parts) == 2:
                        p1 = parts[0].encode("latin1")
                        p2 = parts[1].encode("latin1")
                        self.merges[(p1, p2)] = p1 + p2

        print(f"[ASAI Tokenizer] Loaded vocabulary ({len(self.token_to_id)} tokens) from {directory}")
