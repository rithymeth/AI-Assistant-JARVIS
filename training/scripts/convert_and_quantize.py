"""Converts the merged HF model to GGUF and quantizes it, via llama.cpp.

This wraps external llama.cpp tooling rather than reimplementing GGUF
conversion — it is NOT installed by requirements-train.txt (it's a C++
project you build once, not a pip package). One-time setup in WSL2:

    git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
    cd ~/llama.cpp
    pip install -r requirements.txt   # for convert_hf_to_gguf.py's own deps
    cmake -B build -DGGML_CUDA=OFF    # CPU build is fine — quantizing a
    cmake --build build --config Release --target llama-quantize
                                       # 3B model doesn't need GPU

Then run this script with LLAMA_CPP_DIR pointing at that clone:

    LLAMA_CPP_DIR=~/llama.cpp python3 training/scripts/convert_and_quantize.py

QUANT_TYPE defaults to Q4_K_M — chosen to land in roughly the same disk/RAM
footprint as the already-pulled `llama3.2:3b` Ollama model, so the A/B
comparison in evaluate.py is apples-to-apples on resource usage too.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MERGED_DIR = REPO_ROOT / "training" / "models" / "merged"
GGUF_DIR = REPO_ROOT / "training" / "models" / "gguf"
QUANT_TYPE = os.environ.get("QUANT_TYPE", "Q4_K_M")


def main():
    llama_cpp_dir = os.environ.get("LLAMA_CPP_DIR")
    if not llama_cpp_dir:
        sys.exit("Set LLAMA_CPP_DIR to your llama.cpp clone — see this script's docstring.")
    llama_cpp_dir = Path(llama_cpp_dir)

    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    quantize_bin = llama_cpp_dir / "build" / "bin" / "llama-quantize"
    if not convert_script.exists():
        sys.exit(f"{convert_script} not found — is LLAMA_CPP_DIR correct?")
    if not quantize_bin.exists():
        sys.exit(f"{quantize_bin} not found — did you build the llama-quantize target?")
    if not MERGED_DIR.exists():
        sys.exit(f"{MERGED_DIR} not found — run merge_adapter.py first.")

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    fp16_gguf = GGUF_DIR / "javi-toolfix-f16.gguf"
    quantized_gguf = GGUF_DIR / f"javi-toolfix-{QUANT_TYPE}.gguf"

    print(f"Converting {MERGED_DIR} -> {fp16_gguf} ...")
    subprocess.run(
        [sys.executable, str(convert_script), str(MERGED_DIR), "--outfile", str(fp16_gguf), "--outtype", "f16"],
        check=True,
    )

    print(f"Quantizing to {QUANT_TYPE} -> {quantized_gguf} ...")
    subprocess.run([str(quantize_bin), str(fp16_gguf), str(quantized_gguf), QUANT_TYPE], check=True)

    print(f"Done. Quantized model at {quantized_gguf}")
    print("Next: python3 training/scripts/generate_modelfile.py")


if __name__ == "__main__":
    main()
