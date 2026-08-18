# Javi tool-use LoRA fine-tuning

Narrowly scoped: fixes the five documented tool-use reliability problems
below (not personality/style), via a QLoRA adapter on `llama3.2:3b`'s base
checkpoint (`meta-llama/Llama-3.2-3B-Instruct`). Isolated from the running
app — nothing here is imported by `api/`, `core/`, `tools/`, etc., and
`requirements-train.txt` is never merged into the top-level
`requirements.txt`. The only eventual touch point with the running app is a
one-line `.env` change at the very end (`MODEL_NAME=javi-toolfix`), and even
that's optional — both models stay installed side by side.

## What this targets

Confirmed with a real baseline run of `llama3.2:3b` via
`scripts/evaluate.py` (see "Baseline results" below):

1. **skip_and_fabricate** — sometimes skips calling a tool and fabricates
   an answer instead.
2. **wrong_question_answered** — sometimes calls the right tool but then
   answers a different question than what was asked.
3. **redundant_refetch** — sometimes re-fetches something already in the
   injected knowledge-base context instead of trusting it.
4. **unnecessary_tool_call** — calls a tool for things it should just
   answer directly (arithmetic, general trivia) — not one of the
   originally-planned four, added after the baseline run surfaced it
   directly and repeatedly.
5. **lost_thread_long_conversation** — in longer conversations, can lose
   track of something stated several turns earlier.

## Baseline results (untrained `llama3.2:3b`, this session)

```
[PASS] skip_and_fabricate
[PASS] wrong_question_answered
[FAIL] redundant_refetch          — re-searched a fact already in context
[FAIL] unnecessary_tool_call      — called a tool for plain arithmetic
[FAIL] lost_thread_long_conversation — lost a fact from 3 turns earlier

2/5 passed.
```

Reproduce with (works right now, no training deps or WSL2 needed — plain
inference against your already-running Ollama, from the main app's venv):

```
.venv\Scripts\python.exe training\scripts\evaluate.py llama3.2:3b
```

## Prerequisites (you have to do these — can't be automated)

1. **Accept the Llama 3.2 license** on your own HuggingFace account:
   https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
2. **Generate an HF token** (read access is enough):
   https://huggingface.co/settings/tokens — put it in `.env` at the repo
   root as `HF_TOKEN=hf_...` (never paste it into chat).
3. **Install a real WSL2 Ubuntu distro** — `wsl --list` showing only
   Docker Desktop's internal distro isn't enough:
   ```
   wsl --install -d Ubuntu
   ```
   Then, inside that Ubuntu shell, enable the NVIDIA CUDA driver component
   for WSL if you haven't already (one-time, follow NVIDIA's official WSL2
   CUDA setup guide for your GPU).
4. **Set up the training venv inside WSL2** (this repo is reachable at
   `/mnt/d/Javis` from there):
   ```
   cd /mnt/d/Javis
   python3 -m venv .venv-train && source .venv-train/bin/activate
   pip install torch --index-url https://download.pytorch.org/whl/cu121  # match your driver's CUDA version
   pip install -r training/requirements-train.txt
   ```
5. **Clone and build llama.cpp** (only needed later, for the
   convert/quantize step — see `scripts/convert_and_quantize.py`'s
   docstring for the exact commands).

## Pipeline

Run in this order. Steps 1-2 need only the main app's Windows venv (no
GPU/WSL2 needed). Steps 3-5 need WSL2 + the training venv above. Step 6
needs only the main venv again.

```
# 1. Build the training set from the hand-authored seed examples, and flag
#    real-conversation candidates from javi.db for manual review.
.venv\Scripts\python.exe training\scripts\mine_examples.py

#    -> READ training/data/needs_review.jsonl and hand-correct genuine
#       failure-mode examples into training/data/synthetic_examples.jsonl,
#       then re-run mine_examples.py. The current seed set (~15 examples)
#       is enough to prove the pipeline runs end-to-end, NOT enough to
#       expect a real behavioral improvement from — add more before
#       trusting the "after" eval numbers.

# 2. (WSL2) Download the gated base checkpoint — needs HF_TOKEN, see above.
python3 training/scripts/download_base_model.py

# 3. (WSL2) QLoRA fine-tune. This is the actual GPU-time step.
python3 training/scripts/train_lora.py

# 4. (WSL2) Merge the adapter into full-precision weights, on CPU.
python3 training/scripts/merge_adapter.py

# 5. (WSL2) Convert to GGUF and quantize (needs llama.cpp built — see
#    convert_and_quantize.py's docstring).
LLAMA_CPP_DIR=~/llama.cpp python3 training/scripts/convert_and_quantize.py

# 6. (back in the main Windows venv) Generate the Ollama Modelfile — this
#    pulls SYSTEM_PROMPT live from core/brain/agent.py, so it can't drift.
.venv\Scripts\python.exe training\scripts\generate_modelfile.py
ollama create javi-toolfix -f training\Modelfile.javi-toolfix
```

## Verification before trusting it

```
.venv\Scripts\python.exe training\scripts\evaluate.py javi-toolfix
```

Compare the pass count against the baseline above (2/5), and READ the
plain-conversation regression section — a narrow fine-tune on ~15-way-more
examples can cause catastrophic forgetting of ordinary conversation even
while fixing the targeted failure modes; don't switch `.env`'s `MODEL_NAME`
to `javi-toolfix` until that regression check looks right to you too.
Both models stay installed (`ollama list`), so you can flip back to
`llama3.2:3b` at any time by changing `MODEL_NAME` back — nothing about
this pipeline is destructive to the existing setup.

## Directory contents

```
training/
  requirements-train.txt   # WSL2-only training deps, isolated from the app
  data/
    synthetic_examples.jsonl  # hand-authored seed set, edit this
    train.jsonl                # generated — synthetic_examples.jsonl + live SYSTEM_PROMPT
    needs_review.jsonl         # generated — heuristic candidates from javi.db, unreviewed
  scripts/
    mine_examples.py          # builds train.jsonl + needs_review.jsonl
    download_base_model.py    # HF snapshot_download, needs HF_TOKEN
    train_lora.py              # QLoRA fine-tune (WSL2, GPU)
    merge_adapter.py           # merge adapter into full-precision base (CPU)
    convert_and_quantize.py    # HF -> GGUF -> Q4_K_M via llama.cpp
    generate_modelfile.py      # writes Modelfile.javi-toolfix from live SYSTEM_PROMPT
    evaluate.py                 # the 5-case held-out eval + regression check
  models/                     # generated — base/adapter/merged/gguf (gitignored)
  Modelfile.javi-toolfix      # generated
```
