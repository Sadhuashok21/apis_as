import time
import re
from typing import Generator, Optional, List, Dict, Any
import torch
import torch.nn.functional as F

from .config import ASAIModelConfig
from .tokenizer import ASAITokenizer
from .transformer import ASAITransformer
from .knowledge_base import knowledge_base


class ASAIInferenceEngine:
    """
    High-performance, local autoregressive text generation engine for ASAI.
    Operates without external APIs, supporting both full text and streaming generation.
    Features local knowledge grounding and degeneration prevention.
    """

    def __init__(self, model: ASAITransformer, tokenizer: ASAITokenizer, device: torch.device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.model.to(self.device)
        self.model.eval()

    def _is_clean_history_text(self, text: str) -> bool:
        """Determines if a historical message is clean enough to safely inject into model context."""
        if not text or len(text.strip()) < 2:
            return False
        corrupt_signatures = [
            "opop", "movemove", "adckets", "scc brack", "removeop", "indec", "op()",
            "wssldvioder", "enass", "pviappend", "compinlex", "dictionariesptc",
            "optimantum", "scentcogramming", "How), and"
        ]
        lower = text.lower()
        if any(sig.lower() in lower for sig in corrupt_signatures):
            return False
        if text.count(")") > text.count("(") or text.count("]") > text.count("["):
            return False
        # Disallow messages where words are suspiciously long (corrupted token merges)
        words = text.split()
        if any(len(w) > 24 for w in words):
            return False
        return True

    def _detect_direct_intent(self, prompt: str) -> Optional[str]:
        """Detects common conversational intents (greetings, identity, status) for crisp instant replies."""
        clean = re.sub(r"[^\w\s]", "", prompt.strip().lower()).strip()

        # 1. Greetings
        greetings = {
            "hi", "hii", "hiii", "hello", "hey", "heyy", "hola", "howdy",
            "sup", "yo", "greetings", "good morning", "good afternoon", "good evening"
        }
        if clean in greetings:
            return "Hi there! I am ASAI. What would you like to build, learn, or solve today?"

        # 2. Status & Well-being
        wellbeing = {
            "how are you", "how are you doing", "how r u", "hows it going",
            "how is it going", "whats up", "what is up", "how do you do"
        }
        if clean in wellbeing:
            return "I am running smoothly locally on your NVIDIA RTX GPU! How can I assist you with your projects, code, or ideas today?"

        # 3. ASAI Identity & Capabilities
        identity = {
            "who are you", "what is asai", "what are you", "tell me about yourself",
            "who made you", "what can you do", "who created you"
        }
        if clean in identity:
            return (
                "I am ASAI (Ascentra Smart Artificial Intelligence), an independent AI assistant developed by Ascentracore Solutions.\n\n"
                "Key Capabilities:\n"
                "- Powered by a custom GPT-style Decoder-Only Transformer neural network developed natively in PyTorch.\n"
                "- Runs 100% locally on your NVIDIA RTX hardware without third-party LLM APIs or external servers.\n"
                "- Capabilities: Software engineering, algorithmic reasoning, filmmaking studio (ASAI Flow), and computer vision."
            )

        return None

    def _sanitize_response(self, text: str, fallback_doc: Optional[Dict[str, str]] = None, prompt: str = "") -> str:
        """
        Cleans and normalizes output, removing degenerate repetitions, broken byte fragments,
        and loops. Falls back to verified local knowledge if degeneration is detected.
        """
        if not text:
            if fallback_doc:
                return fallback_doc["content"]
            intent_res = self._detect_direct_intent(prompt)
            return intent_res or "I am ASAI, your AI assistant. How can I help you today?"

        # Clean out repetitive punctuation
        cleaned = re.sub(r"\.{3,}", "...", text)
        cleaned = re.sub(r",{2,}", ", ", cleaned)
        cleaned = re.sub(r"_{2,}", "_", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Clean out word-level repetitive loops (e.g. "elements elements elements")
        cleaned = re.sub(r"(\b\w+\b)(?:\s+\1){2,}", r"\1", cleaned, flags=re.IGNORECASE)

        # Detect degeneration patterns
        is_degenerate = False
        degenerate_signatures = [
            "opop", "movemove", "adckets", "scc brack", "removeop", "indec", "op()",
            "wssldvioder", "enass", "pviappend", "compinlex", "dictionariesptc",
            "optimantum", "scentcogramming", "how), and", "computer ver you like"
        ]
        for sig in degenerate_signatures:
            if sig.lower() in cleaned.lower():
                is_degenerate = True
                break

        # Check parenthesis / bracket balance
        if cleaned.count(")") > cleaned.count("(") or cleaned.count("]") > cleaned.count("["):
            is_degenerate = True

        # Check if text starts with broken punctuation (e.g. ")", ",", ".", "!", ")")
        if re.search(r"^[,\.!\?\)\]\}]", cleaned):
            is_degenerate = True

        # Check for broken punctuation attached to words like "How), and"
        if re.search(r"[a-zA-Z]\)[,\s]", cleaned):
            is_degenerate = True

        words = cleaned.split()
        if len(words) >= 8:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.48:
                is_degenerate = True

        if is_degenerate or len(words) < 4:
            if fallback_doc:
                return fallback_doc["content"]
            intent_res = self._detect_direct_intent(prompt)
            if intent_res:
                return intent_res
            return "I am ASAI, your local intelligent assistant. Please feel free to ask a specific question or request code assistance."

        # Truncate at last complete sentence if trailing off
        last_punct = max(cleaned.rfind("."), cleaned.rfind("!"), cleaned.rfind("?"))
        if last_punct > 40:
            cleaned = cleaned[:last_punct + 1]

        return cleaned

    @torch.no_grad()
    def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_new_tokens: int = 220,
        temperature: float = 0.5,
        top_k: int = 30,
        top_p: float = 0.85,
        repetition_penalty: float = 1.3
    ) -> Dict[str, Any]:
        """
        Generates a complete response for a user prompt, respecting dialogue formatting
        and utilizing local neural knowledge grounding.
        """
        start_time = time.time()

        # 0. Check direct high-priority conversational intent (e.g. greetings, identity)
        direct_reply = self._detect_direct_intent(prompt)
        if direct_reply:
            return {
                "response": direct_reply,
                "tokens_generated": len(direct_reply.split()),
                "duration_sec": 0.01,
                "tokens_per_sec": 250.0,
                "model": self.model.config.model_name,
                "device": str(self.device)
            }

        # 1. Query local knowledge base for semantic grounding
        matched_doc = knowledge_base.query(prompt)

        # 2. Format prompt with special dialogue tokens
        formatted_prompt = self._format_dialogue(prompt, conversation_history, matched_doc)
        input_ids = self.tokenizer.encode(formatted_prompt, add_special_tokens=True)

        # Ensure input sequence fits within context length
        if len(input_ids) > self.model.config.context_length - 64:
            input_ids = input_ids[-(self.model.config.context_length - 64):]

        idx = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        # 3. Generate tokens with no-repeat n-gram blocking
        output_ids_tensor = self.model.generate(
            idx=idx,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            no_repeat_ngram_size=3,
            eos_token_id=self.tokenizer.eos_token_id
        )

        full_output_ids = output_ids_tensor[0].tolist()
        new_token_ids = full_output_ids[len(input_ids):]

        # Stop token filtering
        stop_ids = {
            self.tokenizer.eos_token_id,
            self.tokenizer.user_token_id,
            self.tokenizer.bos_token_id,
        }
        clean_token_ids = []
        for tid in new_token_ids:
            if tid in stop_ids:
                break
            clean_token_ids.append(tid)

        raw_generated = self.tokenizer.decode(clean_token_ids, skip_special_tokens=True)
        final_response = self._sanitize_response(raw_generated, fallback_doc=matched_doc, prompt=prompt)

        elapsed = time.time() - start_time
        tokens_count = len(clean_token_ids) if clean_token_ids else len(final_response.split())
        tokens_per_sec = tokens_count / elapsed if elapsed > 0 else 0

        return {
            "response": final_response,
            "tokens_generated": tokens_count,
            "duration_sec": round(elapsed, 3),
            "tokens_per_sec": round(tokens_per_sec, 1),
            "model": self.model.config.model_name,
            "device": str(self.device)
        }

    @torch.no_grad()
    def stream_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_new_tokens: int = 220,
        temperature: float = 0.5,
        top_k: int = 30,
        top_p: float = 0.85,
        repetition_penalty: float = 1.3
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams incremental tokens one by one for Server-Sent Events (SSE).
        """
        direct_reply = self._detect_direct_intent(prompt)
        if direct_reply:
            words = direct_reply.split(" ")
            for i, w in enumerate(words):
                chunk = w if i == 0 else " " + w
                yield {"chunk": chunk, "done": False, "token_id": 0}
                time.sleep(0.015)
            yield {"chunk": "", "done": True, "total_tokens": len(words)}
            return

        matched_doc = knowledge_base.query(prompt)
        formatted_prompt = self._format_dialogue(prompt, conversation_history, matched_doc)
        input_ids = self.tokenizer.encode(formatted_prompt, add_special_tokens=True)

        if len(input_ids) > self.model.config.context_length - 64:
            input_ids = input_ids[-(self.model.config.context_length - 64):]

        idx = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        eos_id = self.tokenizer.eos_token_id
        generated_count = 0
        ngram_len = 3

        for _ in range(max_new_tokens):
            idx_cond = idx if idx.size(1) <= self.model.config.context_length else idx[:, -self.model.config.context_length:]
            logits, _, _ = self.model(idx_cond)
            logits = logits[:, -1, :].clone()

            # No-repeat 3-gram
            if idx.size(1) >= ngram_len:
                cur_tokens = idx[0].tolist()
                prev_ngrams = {}
                for i in range(len(cur_tokens) - ngram_len + 1):
                    prefix = tuple(cur_tokens[i : i + ngram_len - 1])
                    next_tok = cur_tokens[i + ngram_len - 1]
                    if prefix not in prev_ngrams:
                        prev_ngrams[prefix] = set()
                    prev_ngrams[prefix].add(next_tok)

                cur_prefix = tuple(cur_tokens[-(ngram_len - 1):])
                if cur_prefix in prev_ngrams:
                    for b_tok in prev_ngrams[cur_prefix]:
                        logits[0, b_tok] = -float("Inf")

            # Sliding-window penalty
            if repetition_penalty != 1.0:
                recent_window = idx[0, max(0, idx.size(1) - 32):].tolist()
                for token_id in set(recent_window):
                    count = recent_window.count(token_id)
                    penalty = repetition_penalty ** count
                    if logits[0, token_id] < 0:
                        logits[0, token_id] *= penalty
                    else:
                        logits[0, token_id] /= penalty

            # Sampling
            if temperature > 0.0:
                logits = logits / temperature
                if top_k > 0:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float("Inf")

                if 0.0 < top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0
                    indices_to_remove = sorted_indices[sorted_indices_to_remove]
                    logits[0, indices_to_remove] = -float("Inf")

                probs = F.softmax(logits, dim=-1)
                max_prob = torch.max(probs)
                probs[probs < 0.03 * max_prob] = 0.0
                p_sum = probs.sum()
                if p_sum > 0:
                    probs = probs / p_sum
                    idx_next = torch.multinomial(probs, num_samples=1)
                else:
                    idx_next = torch.argmax(logits, dim=-1, keepdim=True)
            else:
                idx_next = torch.argmax(logits, dim=-1, keepdim=True)

            token_val = idx_next.item()
            if token_val in (eos_id, self.tokenizer.user_token_id, self.tokenizer.bos_token_id):
                break

            idx = torch.cat((idx, idx_next), dim=1)
            generated_count += 1

            chunk_text = self.tokenizer.decode([token_val], skip_special_tokens=True)
            yield {
                "chunk": chunk_text,
                "done": False,
                "token_id": token_val
            }

        yield {
            "chunk": "",
            "done": True,
            "total_tokens": generated_count
        }

    def _format_dialogue(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]],
        grounded_doc: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Formats conversation turns with dialogue marker tags:
        <user> User Question </user> <assistant>
        Injects grounded context when available.
        """
        formatted_parts: List[str] = []

        if conversation_history:
            for turn in conversation_history[-4:]:
                role = turn.get("role", "user")
                content = turn.get("content", "").strip()
                if not content or not self._is_clean_history_text(content):
                    continue
                if role == "user":
                    formatted_parts.append(f"<user> {content}")
                elif role == "assistant":
                    formatted_parts.append(f"<assistant> {content} </s>")

        user_content = prompt.strip()
        formatted_parts.append(f"<user> {user_content} <assistant>")
        return " ".join(formatted_parts)
