"""QLoRA fine-tune of Llama 3.2 3B Instruct on training/data/train.jsonl,
targeting the four documented tool-use reliability problems (not
personality/style) — see README.md's "Known limitations" section for what
those are, and training/README.md for the full pipeline this script is one
step of.

4-bit quantized base (bitsandbytes) is a hard requirement here, not a
choice — the plan this implements targets a 4GB VRAM budget, and full or
even 8-bit fine-tuning of a 3B model doesn't fit. Runs in WSL2 only (see
training/requirements-train.txt for why).

    python3 training/scripts/train_lora.py

Prerequisites: training/scripts/download_base_model.py already run
successfully (base checkpoint at training/models/base), and
training/scripts/mine_examples.py already run (training/data/train.jsonl
exists and has more than the bootstrap handful of examples — see that
script's note about needs_review.jsonl).
"""

import json
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_MODEL_DIR = REPO_ROOT / "training" / "models" / "base"
TRAIN_DATA_PATH = REPO_ROOT / "training" / "data" / "train.jsonl"
ADAPTER_OUT_DIR = REPO_ROOT / "training" / "models" / "adapter"

# Attention-only target modules — the standard, lowest-footprint LoRA choice
# for Llama-family models; skips MLP layers to keep the adapter small and
# training fast, appropriate for a narrowly-scoped behavioral fix rather
# than broad capability change.
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

MAX_SEQ_LENGTH = 2048
NUM_EPOCHS = 3
LEARNING_RATE = 2e-4
PER_DEVICE_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 8  # effective batch size 8, small VRAM footprint


def load_dataset() -> Dataset:
    if not TRAIN_DATA_PATH.exists():
        sys.exit(f"{TRAIN_DATA_PATH} not found — run training/scripts/mine_examples.py first.")
    records = []
    with open(TRAIN_DATA_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if len(records) < 20:
        print(
            f"WARNING: only {len(records)} training examples. The hand-authored seed set "
            "bootstraps the pipeline end-to-end but is not enough data for a real fine-tune — "
            "review training/data/needs_review.jsonl and add corrected real examples first. "
            "Continuing anyway since you ran this script directly."
        )
    return Dataset.from_list([{"messages": r["messages"]} for r in records])


def main():
    if not BASE_MODEL_DIR.exists():
        sys.exit(f"{BASE_MODEL_DIR} not found — run training/scripts/download_base_model.py first.")

    dataset = load_dataset()

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_DIR)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_DIR,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )

    sft_config = SFTConfig(
        output_dir=str(ADAPTER_OUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=PER_DEVICE_BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        gradient_checkpointing=True,
        learning_rate=LEARNING_RATE,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch",
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,  # keep conversations distinct — this is a small, curated set, not raw text
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    trainer.train()
    trainer.save_model(str(ADAPTER_OUT_DIR))
    tokenizer.save_pretrained(str(ADAPTER_OUT_DIR))
    print(f"LoRA adapter saved to {ADAPTER_OUT_DIR}")


if __name__ == "__main__":
    main()
