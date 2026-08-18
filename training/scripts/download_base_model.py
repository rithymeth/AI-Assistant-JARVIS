"""Downloads the Llama 3.2 3B Instruct base checkpoint for QLoRA training.

Cannot be automated past this point: Meta's Llama 3.2 is a gated model on
HuggingFace. Before running this script you must, in your own HF account:

  1. Visit https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct and
     accept the license (usually near-instant approval).
  2. Create a token with 'read' access at
     https://huggingface.co/settings/tokens
  3. Put it in .env at the repo root as HF_TOKEN=hf_xxx... (or export it as
     an environment variable before running this script) — never paste it
     into chat.

Run inside WSL2, with training/requirements-train.txt installed:

    python3 training/scripts/download_base_model.py
"""

import os
import sys
from pathlib import Path

MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_DIR = REPO_ROOT / "training" / "models" / "base"


def _load_hf_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if token:
        return token
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip().startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main():
    token = _load_hf_token()
    if not token:
        sys.exit(
            "HF_TOKEN not found (checked the HF_TOKEN env var and .env at the repo root).\n"
            "Accept the Llama 3.2 license and generate a token first — see this script's "
            "docstring — then set HF_TOKEN before re-running."
        )

    from huggingface_hub import snapshot_download

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID} to {LOCAL_DIR} ...")
    try:
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=str(LOCAL_DIR),
            token=token,
            ignore_patterns=["*.pth", "original/*"],  # keep just the safetensors + configs
        )
    except Exception as e:
        sys.exit(
            f"Download failed: {e}\n"
            "If this is a 401/403, double-check you accepted the license on the model's "
            "HF page with the SAME account that generated HF_TOKEN."
        )
    print(f"Done. Base checkpoint is at {LOCAL_DIR}")


if __name__ == "__main__":
    main()
