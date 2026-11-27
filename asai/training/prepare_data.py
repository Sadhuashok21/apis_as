import os
import sys
import json
import time

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASAI_DIR = os.path.dirname(SCRIPT_DIR)
APIS_DIR = os.path.dirname(ASAI_DIR)
if APIS_DIR not in sys.path:
    sys.path.insert(0, APIS_DIR)

import torch
from torch.utils.data import DataLoader

from asai.services.neural_network.config import ASAIModelConfig
from asai.services.neural_network.tokenizer import ASAITokenizer
from asai.services.neural_network.transformer import ASAITransformer
from asai.training.dataset import PretrainDataset, InstructionDataset
from asai.training.trainer import ASAITrainer


def main():
    print("=" * 70)
    print(" ASAI Custom Neural Network Training & Data Preparation Pipeline")
    print(" Zero External LLMs · Pure PyTorch Decoder-Only Transformer")
    print("=" * 70)

    data_dir = os.path.join(SCRIPT_DIR, "data")
    corpus_file = os.path.join(data_dir, "sample_corpus.txt")
    instruct_file = os.path.join(data_dir, "instruction_data.jsonl")

    tokenizer_dir = os.path.join(ASAI_DIR, "services", "neural_network", "tokenizer_data")
    checkpoints_dir = os.path.join(ASAI_DIR, "checkpoints")
    os.makedirs(tokenizer_dir, exist_ok=True)
    os.makedirs(checkpoints_dir, exist_ok=True)

    # 1. Load Training Text
    with open(corpus_file, "r", encoding="utf-8") as f:
        pretrain_text = f.read()

    instruct_texts = []
    with open(instruct_file, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            for m in data.get("messages", []):
                instruct_texts.append(m.get("content", ""))
    full_text = pretrain_text + "\n" + "\n".join(instruct_texts)

    # 2. Train Custom Subword BPE Tokenizer
    print("\n[Step 1/4] Training Custom BPE Tokenizer...")
    # Target vocabulary: compact, highly dense vocabulary for fast convergence
    target_vocab = 1200
    tokenizer = ASAITokenizer(vocab_size=target_vocab)
    tokenizer.train_from_text(full_text, target_vocab_size=target_vocab, min_frequency=2)
    tokenizer.save(tokenizer_dir)

    # Verify tokenizer
    test_phrase = "Hello! I am ASAI, your intelligent neural network."
    encoded = tokenizer.encode(test_phrase, add_special_tokens=True)
    decoded = tokenizer.decode(encoded)
    print(f"  Test String: '{test_phrase}'")
    print(f"  Encoded IDs ({len(encoded)} tokens): {encoded}")
    print(f"  Decoded String: '{decoded}'")
    assert decoded.strip() == test_phrase.strip(), "Tokenizer roundtrip failed!"
    print("  Tokenizer validation passed successfully!\n")

    # 3. Initialize ASAITransformer Architecture
    print("[Step 2/4] Instantiating ASAITransformer Architecture...")
    actual_vocab_size = len(tokenizer.token_to_id)
    config = ASAIModelConfig(
        vocab_size=actual_vocab_size,
        context_length=256,
        n_layer=4,
        n_head=4,
        d_model=256,
        d_ff=1024,
        dropout=0.1,
        model_name="ASAI-Mini-Native"
    )
    model = ASAITransformer(config)
    print(f"  Trainable Parameters: {model.get_num_params():,}")
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"  Compute Device: {device_name} (CUDA: {torch.cuda.is_available()})\n")

    # 4. Phase 1 Training: Language Model Pretraining
    print("[Step 3/4] Running Language Model Pretraining...")
    pretrain_token_ids = tokenizer.encode(full_text * 25, add_special_tokens=False)
    pretrain_dataset = PretrainDataset(pretrain_token_ids, context_length=config.context_length)
    pretrain_loader = DataLoader(
        pretrain_dataset,
        batch_size=8,
        shuffle=True,
        drop_last=True
    )

    trainer = ASAITrainer(
        model=model,
        train_loader=pretrain_loader,
        learning_rate=5e-4,
        max_epochs=6,
        output_dir=checkpoints_dir,
        checkpoint_name="asai_mini_checkpoint.pt"
    )
    trainer.train()

    # 5. Phase 2 Training: Supervised Instruction Fine-Tuning
    print("\n[Step 4/4] Running Supervised Instruction Fine-Tuning with Dialogue Loss Masking...")
    instruct_dataset = InstructionDataset(
        jsonl_path=instruct_file,
        tokenizer=tokenizer,
        context_length=config.context_length
    )
    # Replicate instruction dataset to ensure sufficient training steps
    replicated_samples = instruct_dataset.samples * 12
    instruct_dataset.samples = replicated_samples
    instruct_loader = DataLoader(
        instruct_dataset,
        batch_size=8,
        shuffle=True,
        drop_last=True
    )

    sft_trainer = ASAITrainer(
        model=model,
        train_loader=instruct_loader,
        learning_rate=3e-4,
        max_epochs=8,
        output_dir=checkpoints_dir,
        checkpoint_name="asai_mini_checkpoint.pt"
    )
    sft_trainer.train()

    print("\n" + "=" * 70)
    print(" ASAI Neural Network Training Successfully Completed!")
    print(f" Trained weights saved to: {os.path.join(checkpoints_dir, 'asai_mini_checkpoint.pt')}")
    print(f" Tokenizer saved to: {tokenizer_dir}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
