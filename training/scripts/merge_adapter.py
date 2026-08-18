"""Merges the trained LoRA adapter into the full-precision base weights, on
CPU.

Why CPU and why full precision, not the 4-bit base used for training:
merging LoRA deltas into a quantized base isn't the standard/supported
path (the quantization error compounds unpredictably with the merge), and
the resulting fp16 weights for a 3B model comfortably exceed the 4GB
training VRAM budget anyway — but this step happens exactly once per
trained adapter and doesn't need a GPU, so paying the CPU-merge time cost
here (a few minutes) instead of fighting the quantized-merge problem is
the better trade.

    python3 training/scripts/merge_adapter.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_MODEL_DIR = REPO_ROOT / "training" / "models" / "base"
ADAPTER_DIR = REPO_ROOT / "training" / "models" / "adapter"
MERGED_OUT_DIR = REPO_ROOT / "training" / "models" / "merged"


def main():
    if not BASE_MODEL_DIR.exists():
        sys.exit(f"{BASE_MODEL_DIR} not found — run download_base_model.py first.")
    if not ADAPTER_DIR.exists():
        sys.exit(f"{ADAPTER_DIR} not found — run train_lora.py first.")

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading full-precision base from {BASE_MODEL_DIR} (CPU, this takes a bit)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_DIR,
        torch_dtype=torch.float16,
        device_map="cpu",
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_DIR)

    print(f"Loading and merging adapter from {ADAPTER_DIR}...")
    merged_model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    merged_model = merged_model.merge_and_unload()

    MERGED_OUT_DIR.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(str(MERGED_OUT_DIR), safe_serialization=True)
    tokenizer.save_pretrained(str(MERGED_OUT_DIR))
    print(f"Merged model saved to {MERGED_OUT_DIR}")


if __name__ == "__main__":
    main()
