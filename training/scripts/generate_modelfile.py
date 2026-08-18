"""Generates training/Modelfile.javi-toolfix from the quantized GGUF plus
the app's LIVE SYSTEM_PROMPT (imported from core/brain/agent.py, not
copy-pasted) — so this can never silently drift out of sync if the system
prompt changes later.

    .venv\\Scripts\\python.exe training\\scripts\\generate_modelfile.py
    (plain Windows venv is fine — this only imports a string constant and
    writes a text file, no training deps needed)

Then, in an Ollama-reachable shell:

    ollama create javi-toolfix -f training/Modelfile.javi-toolfix

Both javi3.2:3b and javi-toolfix stay installed side by side — flip
MODEL_NAME in .env to A/B compare, per training/README.md.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.brain.agent import SYSTEM_PROMPT  # noqa: E402

QUANT_TYPE = "Q4_K_M"
GGUF_PATH = REPO_ROOT / "training" / "models" / "gguf" / f"javi-toolfix-{QUANT_TYPE}.gguf"
MODELFILE_PATH = REPO_ROOT / "training" / "Modelfile.javi-toolfix"


def main():
    if not GGUF_PATH.exists():
        print(f"Warning: {GGUF_PATH} doesn't exist yet — writing the Modelfile anyway, "
              "but `ollama create` will fail until convert_and_quantize.py has run.")

    escaped_prompt = SYSTEM_PROMPT.replace('"""', '\\"\\"\\"')
    content = (
        f"FROM {GGUF_PATH}\n\n"
        f'SYSTEM """{escaped_prompt}"""\n\n'
        "PARAMETER stop <|eot_id|>\n"
    )
    MODELFILE_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {MODELFILE_PATH}")
    print(f"Next: ollama create javi-toolfix -f {MODELFILE_PATH}")


if __name__ == "__main__":
    main()
