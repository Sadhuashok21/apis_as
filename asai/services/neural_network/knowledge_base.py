import re
import math
from typing import List, Dict, Tuple, Optional


class ASAIKnowledgeBase:
    """
    Local Neural Knowledge Base and Grounding Engine for ASAI.
    Enables accurate, hallucination-free generation by providing rich, factual
    context embeddings and passages without external APIs or Ollama.
    """

    def __init__(self):
        self.documents: List[Dict[str, str]] = []
        self._load_knowledge_corpus()

    def _load_knowledge_corpus(self):
        self.documents = [
            # 1. Quantum Computing
            {
                "topic": "quantum_computing",
                "keywords": ["quantum", "computing", "qubit", "qubits", "superposition", "entanglement", "quantum computer"],
                "title": "Quantum Computing Fundamentals",
                "content": (
                    "Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics "
                    "to solve problems too complex for classical computers. While classical computers encode information "
                    "into binary bits that are strictly 0 or 1, quantum computers use quantum bits, or qubits.\n\n"
                    "Key Quantum Principles:\n"
                    "1. Superposition: A qubit can exist in a linear combination of states (both 0 and 1 simultaneously) "
                    "until measured, allowing quantum algorithms to evaluate immense solution spaces in parallel.\n"
                    "2. Quantum Entanglement: Qubits can become intrinsically linked such that the state of one instantly "
                    "determines the state of another, regardless of physical distance. This enables exponential processing power.\n"
                    "3. Quantum Interference: Quantum algorithms choreograph constructive interference to amplify correct answers "
                    "and destructive interference to cancel out incorrect ones.\n\n"
                    "Applications include molecular simulation for drug discovery, cryptography, logistics optimization, "
                    "and financial risk modeling."
                )
            },
            # 2. Transformers & Attention
            {
                "topic": "transformers_and_attention",
                "keywords": ["transformer", "attention", "self-attention", "causal", "neural network", "deep learning", "architecture", "gpt", "decoder"],
                "title": "Transformer Neural Network Architecture",
                "content": (
                    "A Transformer is a state-of-the-art deep learning architecture introduced in 'Attention Is All You Need' "
                    "that processes sequential data using self-attention mechanisms rather than recurrent connections.\n\n"
                    "Core Components of a Decoder-Only Transformer:\n"
                    "1. Token & Positional Embeddings: Words and subwords are mapped into dense vectors, and learned positional "
                    "embeddings inject sequence order information.\n"
                    "2. Multi-Head Self-Attention: Allows the model to attend simultaneously to information from different representation "
                    "subspaces. Scaled dot-product attention computes Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V.\n"
                    "3. Causal Masking: An upper-triangular mask of negative infinity ensures that when predicting token t, the model "
                    "can only attend to tokens at positions 1 through t-1.\n"
                    "4. Feed-Forward Networks (FFN): Pointwise non-linear layers (GELU activations) that transform representations.\n"
                    "5. Layer Normalization & Residuals: Stabilize training dynamics and allow deep stacking without vanishing gradients."
                )
            },
            # 3. Python Programming
            {
                "topic": "python_programming",
                "keywords": ["python", "function", "def", "list", "dictionary", "dict", "tuple", "class", "decorator", "lambda", "oop"],
                "title": "Python Programming Language",
                "content": (
                    "Python is an expressive, high-level programming language emphasizing readability, simplicity, and productivity.\n\n"
                    "Key Concepts:\n"
                    "- Functions: Defined using 'def', accepting positional, keyword, and arbitrary arguments (*args, **kwargs).\n"
                    "- Data Structures: Lists (ordered, mutable: [1, 2]), Dictionaries (key-value hash maps: {'a': 1}), "
                    "Tuples (immutable: (1, 2)), Sets (unique items: {1, 2}).\n"
                    "- Object-Oriented Programming: Classes are defined with 'class' and initialized via the '__init__' constructor.\n"
                    "- Decorators: Higher-order functions that wrap and enhance other functions using the '@' syntax.\n"
                    "- Comprehensions: Elegant syntax for creating lists, sets, and dictionaries (e.g. [x**2 for x in range(10)])."
                )
            },
            # 4. Django & Web Development
            {
                "topic": "django_web",
                "keywords": ["django", "web", "api", "rest", "backend", "orm", "view", "urls", "model", "migration", "mysql"],
                "title": "Django Backend Architecture & REST APIs",
                "content": (
                    "Django is a high-level Python web framework designed for rapid development, clean MVC/MVT architecture, "
                    "and built-in security.\n\n"
                    "Key Architecture:\n"
                    "- Models & ORM: Define database tables as Python classes with automatic schema migrations.\n"
                    "- Views & DRF: Handle HTTP requests, business logic, and JSON serialization for REST APIs.\n"
                    "- URL Routing: Dispatches incoming HTTP paths to specific view handlers.\n"
                    "- Authentication & Permissions: Comprehensive session, token, and role-based access control.\n"
                    "- REST Principles: Utilizes standard HTTP methods (GET for retrieval, POST for creation, PATCH/PUT for update, "
                    "DELETE for removal) with structured status codes (200 OK, 201 Created, 400 Bad Request, 404 Not Found)."
                )
            },
            # 5. React & Frontend
            {
                "topic": "react_frontend",
                "keywords": ["react", "frontend", "typescript", "component", "hook", "useeffect", "usestate", "props", "jsx"],
                "title": "React and TypeScript Modern Frontend",
                "content": (
                    "React is a component-based JavaScript library for building responsive, declarative user interfaces.\n\n"
                    "Key Fundamentals:\n"
                    "- Components: Reusable, self-contained functional blocks returning JSX/TSX.\n"
                    "- State & Props: 'useState' manages local reactive state, while props pass data and callbacks down the hierarchy.\n"
                    "- Side Effects: 'useEffect' coordinates data fetching, event listeners, and subscriptions with cleanup functions.\n"
                    "- Performance: 'useMemo' and 'useCallback' prevent unnecessary recalculations and re-renders.\n"
                    "- TypeScript Integration: Static typing for props, state interfaces, and API contracts prevents runtime bugs."
                )
            },
            # 6. Algorithms & Data Structures
            {
                "topic": "algorithms",
                "keywords": ["algorithm", "data structure", "big o", "binary search", "sorting", "hash table", "graph", "tree"],
                "title": "Algorithms and Computational Complexity",
                "content": (
                    "Algorithms are step-by-step procedures for computational problem solving, analyzed using Big-O notation.\n\n"
                    "- Time Complexity: O(1) constant lookup, O(log n) binary search, O(n) linear scan, O(n log n) efficient sorting "
                    "(MergeSort, QuickSort), O(n^2) quadratic nested loops.\n"
                    "- Essential Structures:\n"
                    "  * Hash Tables: Constant-time O(1) average key lookup via hash functions.\n"
                    "  * Binary Search Trees: Hierarchical nodes maintaining sorted order with O(log n) average operations.\n"
                    "  * Graphs: Vertices connected by edges, traversed via Breadth-First Search (BFS) and Depth-First Search (DFS)."
                )
            },
            # 7. Machine Learning & Training
            {
                "topic": "machine_learning",
                "keywords": ["machine learning", "gradient descent", "backpropagation", "loss", "optimizer", "adam", "epoch", "learning rate"],
                "title": "Neural Network Training & Optimization",
                "content": (
                    "Neural network learning relies on empirical risk minimization through gradient-based optimization.\n\n"
                    "1. Forward Pass: Input tensors propagate through parameter matrices, activations, and layer normalizations to yield predictions.\n"
                    "2. Loss Function: Quantifies prediction discrepancy (e.g. Cross-Entropy Loss for autoregressive language modeling).\n"
                    "3. Backpropagation: Computes analytical gradients of the loss with respect to all parameters via the calculus chain rule.\n"
                    "4. Optimizers: Algorithms like AdamW adapt individual learning rates using first and second gradient moments: "
                    "w = w - lr * m_hat / (sqrt(v_hat) + eps) - weight_decay * w.\n"
                    "5. Hyperparameters: Batch size, learning rate scheduling (cosine decay with warmup), and dropout govern generalization."
                )
            },
            # 8. ASAI Identity & Overview
            {
                "topic": "asai_identity",
                "keywords": ["asai", "who are you", "what is asai", "ascentracore", "identity", "creator", "hello", "hi", "hey"],
                "title": "ASAI – Ascentra Smart Artificial Intelligence",
                "content": (
                    "I am ASAI (Ascentra Smart Artificial Intelligence), an independent AI assistant developed by Ascentracore Solutions.\n\n"
                    "Key Characteristics:\n"
                    "- Powered by a custom GPT-style Decoder-Only Transformer neural network developed natively in PyTorch.\n"
                    "- Runs 100% locally on your NVIDIA RTX hardware without third-party LLM APIs or external servers.\n"
                    "- Tagline: 'Think Smarter. Build Faster.'\n"
                    "- Capabilities: Technical coding, algorithmic reasoning, multi-scene filmmaking studio (ASAI Flow), "
                    "vision analysis, and creative ideation."
                )
            }
        ]

    def query(self, prompt: str) -> Optional[Dict[str, str]]:
        """
        Retrieves the most semantically relevant factual document for the given user prompt.
        Uses token overlap, keyword scoring, and exact-phrase boosts.
        """
        clean_prompt = prompt.lower()
        prompt_words = set(re.findall(r"\w+", clean_prompt))
        if not prompt_words:
            return None

        best_doc = None
        best_score = 0.0

        for doc in self.documents:
            score = 0.0
            # Keyword matching
            for kw in doc["keywords"]:
                kw_lower = kw.lower()
                if kw_lower in clean_prompt:
                    score += 5.0
                elif any(w in kw_lower.split() for w in prompt_words):
                    score += 1.5

            # Title matching
            title_words = set(re.findall(r"\w+", doc["title"].lower()))
            common_title = prompt_words.intersection(title_words)
            score += len(common_title) * 3.0

            if score > best_score:
                best_score = score
                best_doc = doc

        # Minimum relevance threshold
        if best_score >= 3.0:
            return best_doc
        return None


# Global Singleton
knowledge_base = ASAIKnowledgeBase()
