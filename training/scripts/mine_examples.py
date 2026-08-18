"""Builds training/data/train.jsonl from the hand-authored synthetic seed
set, and separately flags real-conversation candidates from javi.db for
manual review.

Why javi.db mining is best-effort, not automatic: core/memory/store.py's
`messages` table only ever persists the final "assistant" reply text (see
core/brain/agent.py's _agent_loop — add_message() is called once, at the
very end of a turn) — intermediate tool_calls/tool results live only in the
in-memory message list for that request and are never written to SQLite.
That means there is no ground truth in the DB for "did a tool actually get
called this turn" — so this script can only flag heuristic CANDIDATES
(a user message that looks like it needed a tool, paired with an assistant
reply that doesn't look like it used one) for a human to read, correct into
an ideal trajectory, and move into synthetic_examples.jsonl by hand. It
never auto-labels anything as a trusted training example.

Run from the repo root with the MAIN app's venv (this only reads javi.db
and the plain-Python SYSTEM_PROMPT string — no training deps needed):

    .venv\\Scripts\\python.exe training\\scripts\\mine_examples.py
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.brain.agent import SYSTEM_PROMPT  # noqa: E402  (import after sys.path fix)
from config.settings import DB_PATH  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = DATA_DIR / "synthetic_examples.jsonl"
TRAIN_OUT_PATH = DATA_DIR / "train.jsonl"
REVIEW_OUT_PATH = DATA_DIR / "needs_review.jsonl"

# Exact formatting agent.py uses for injected knowledge — kept in sync here
# on purpose (imported constants only cover the plain SYSTEM_PROMPT string;
# these header lines are copied verbatim from handle_message()) so a
# redundant_refetch training example's system prompt looks identical in
# shape to what the model actually sees at inference.
KNOWLEDGE_HEADER = (
    "\n\nThings you've looked up and learned in past conversations (web searches, "
    "page reads, screen looks, file reads) that might be relevant. Use ONLY if "
    "directly relevant to the user's current message; otherwise ignore completely:\n"
)

INJECT_MARKER = "__INJECT_KNOWLEDGE__:"


def _expand_system_message(raw_content: str) -> str:
    """Turns a synthetic_examples.jsonl `__INJECT_KNOWLEDGE__:lookup|fact`
    placeholder into the exact system-prompt shape used at inference, so
    the model isn't trained on a prompt structure it'll never actually see."""
    if not raw_content.startswith(INJECT_MARKER):
        return SYSTEM_PROMPT
    _lookup_key, _sep, fact = raw_content[len(INJECT_MARKER):].partition("|")
    return SYSTEM_PROMPT + KNOWLEDGE_HEADER + f"- {fact}"


def load_seed_examples() -> list[dict]:
    examples = []
    with open(SEED_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            messages = record["messages"]
            if messages and messages[0]["role"] == "system":
                messages[0] = {"role": "system", "content": _expand_system_message(messages[0]["content"])}
            else:
                messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            examples.append({"failure_mode": record.get("failure_mode", "unspecified"), "messages": messages})
    return examples


# Loose signal words for "this user turn probably needed a tool" — not a
# precise classifier, just enough to narrow down what a human should look
# at. Mirrors the tool set in tools/registry.py's TOOL_SCHEMAS.
TOOL_SIGNAL_PATTERNS = re.compile(
    r"\b(weather|search|look ?up|latest|current|open|close|focus|window|"
    r"screen|see|camera|file|read|write|run|command|fetch|url|website|"
    r"click|type|press key)\b",
    re.IGNORECASE,
)

# If the assistant's reply itself reads like it's reporting a tool result
# (numbers, quoted titles, "found", "according to") it's less likely to be
# a bare fabrication and more likely a real (if unverifiable from this
# table alone) tool-backed answer — skip flagging those to keep the review
# queue focused on the more obviously-suspicious cases.
LIKELY_GROUNDED_PATTERNS = re.compile(r"\b(according to|found|result|says|shows|titled)\b", re.IGNORECASE)


def mine_candidates_from_db(limit: int = 200) -> list[dict]:
    import sqlite3

    if not Path(DB_PATH).exists():
        print(f"No DB found at {DB_PATH} — skipping real-conversation mining.")
        return []

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT session_id, role, content, id FROM messages ORDER BY session_id, id ASC"
    ).fetchall()
    conn.close()

    candidates = []
    prev = None
    for session_id, role, content, msg_id in rows:
        if (
            prev
            and prev[0] == session_id
            and prev[1] == "user"
            and role == "assistant"
            and TOOL_SIGNAL_PATTERNS.search(prev[2])
            and not LIKELY_GROUNDED_PATTERNS.search(content)
        ):
            candidates.append(
                {
                    "session_id": session_id,
                    "user_message": prev[2],
                    "assistant_reply": content,
                    "note": (
                        "Heuristic candidate only — the messages table has no record of "
                        "whether a tool was actually called this turn (see this script's "
                        "docstring). Read this pair, decide what SHOULD have happened, and "
                        "hand-author the corrected trajectory into synthetic_examples.jsonl "
                        "if it's a genuine example of one of the four failure modes."
                    ),
                }
            )
        prev = (session_id, role, content, msg_id)
        if len(candidates) >= limit:
            break
    return candidates


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    seed_examples = load_seed_examples()
    with open(TRAIN_OUT_PATH, "w", encoding="utf-8") as f:
        for ex in seed_examples:
            f.write(json.dumps(ex) + "\n")
    print(f"Wrote {len(seed_examples)} hand-authored examples to {TRAIN_OUT_PATH}")

    candidates = mine_candidates_from_db()
    with open(REVIEW_OUT_PATH, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")
    print(f"Wrote {len(candidates)} unreviewed candidates to {REVIEW_OUT_PATH} (NOT included in train.jsonl)")
    if candidates:
        print(
            "Review those by hand before training a real model — this seed set alone "
            "(a handful of examples per failure mode) is meant to bootstrap the "
            "pipeline end-to-end, not to be a sufficient dataset on its own."
        )


if __name__ == "__main__":
    main()
