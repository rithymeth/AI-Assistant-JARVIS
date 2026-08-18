"""Held-out evaluation: reproduces the four originally-documented tool-use
failure modes plus a fifth (unnecessary_tool_call) confirmed during this
pipeline's own baseline run, against a real model via real ollama.chat()
calls (never training-time simulation), reports per-category pass/fail
counts. Run against baseline `llama3.2:3b` before training to get a real
"before" number, then against `javi-toolfix` after — see
training/README.md.

None of these cases appear in training/data/train.jsonl or
synthetic_examples.jsonl — held out on purpose, otherwise this would just
be re-testing memorization.

Also runs a small plain-conversation regression set: a narrow behavioral
fine-tune can cause catastrophic forgetting of ordinary (non-tool)
conversation, so this checks the model still answers normal questions
reasonably before declaring the fine-tune a win.

    .venv\\Scripts\\python.exe training\\scripts\\evaluate.py llama3.2:3b
    .venv\\Scripts\\python.exe training\\scripts\\evaluate.py javi-toolfix

Runs against a real local Ollama, using the main app's venv (no training
deps needed) — this is plain inference, not training.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

import ollama  # noqa: E402

from core.brain.agent import SYSTEM_PROMPT  # noqa: E402
from tools.registry import TOOL_SCHEMAS  # noqa: E402

CLIENT = ollama.Client()


def run_conversation(model: str, messages: list, canned_tool_result: str | None):
    """Mirrors core/brain/agent.py's _agent_loop for exactly one tool-call
    round-trip: send messages with tools available; if the model calls a
    tool, feed back a fixed canned result (not a live tool execution — eval
    reproducibility matters more here than realism) and get the final
    reply. Returns (tool_was_called, tool_name_or_None, final_text)."""
    response = CLIENT.chat(model=model, messages=messages, tools=TOOL_SCHEMAS, stream=False)
    msg = response.message
    if not msg.tool_calls:
        return False, None, msg.content or ""

    tool_name = msg.tool_calls[0].function.name
    messages = [*messages, msg, {"role": "tool", "content": canned_tool_result or "(no result provided)"}]
    response2 = CLIENT.chat(model=model, messages=messages, tools=TOOL_SCHEMAS, stream=False)
    return True, tool_name, response2.message.content or ""


def sys_msg(extra: str = "") -> dict:
    return {"role": "system", "content": SYSTEM_PROMPT + extra}


KNOWLEDGE_HEADER = (
    "\n\nThings you've looked up and learned in past conversations (web searches, "
    "page reads, screen looks, file reads) that might be relevant. Use ONLY if "
    "directly relevant to the user's current message; otherwise ignore completely:\n"
)


def check_skip_and_fabricate(model: str) -> tuple[bool, str]:
    messages = [
        sys_msg(),
        {"role": "user", "content": "What's the current exchange rate from USD to EUR?"},
    ]
    called, tool_name, final_text = run_conversation(
        model, messages, canned_tool_result='[{"title": "USD to EUR", "snippet": "1 USD = 0.92 EUR as of today."}]'
    )
    if not called:
        return False, f"did NOT call a tool at all — answered directly: {final_text!r}"
    if "0.92" not in final_text:
        return False, f"called {tool_name} but final reply doesn't relay the looked-up rate: {final_text!r}"
    return True, f"called {tool_name}, relayed the rate correctly: {final_text!r}"


def check_wrong_question_answered(model: str) -> tuple[bool, str]:
    messages = [
        sys_msg(),
        {"role": "user", "content": "Can you check my notes file for the deadline?"},
    ]
    called, tool_name, final_text = run_conversation(
        model,
        messages,
        canned_tool_result=(
            "Meeting notes: discussed Q3 roadmap and hiring plans at length. "
            "Deadline for the draft is next Friday. Follow up with design team about colors."
        ),
    )
    if not called:
        return False, f"did NOT call a tool — answered directly: {final_text!r}"
    if "friday" not in final_text.lower():
        return False, f"called {tool_name} but reply doesn't answer the actual question asked (deadline): {final_text!r}"
    return True, f"called {tool_name}, correctly answered with the deadline: {final_text!r}"


def check_redundant_refetch(model: str) -> tuple[bool, str]:
    fact = "Canberra is the capital of Australia, chosen as a compromise between Sydney and Melbourne."
    messages = [
        sys_msg(KNOWLEDGE_HEADER + f"- Tool: web_search, args: {{'query': 'capital of Australia'}}\nResult: {fact}"),
        {"role": "user", "content": "Quick one — what's the capital of Australia again?"},
    ]
    called, tool_name, final_text = run_conversation(model, messages, canned_tool_result=None)
    if called:
        return False, f"redundantly called {tool_name} even though the answer was already injected in context"
    if "canberra" not in final_text.lower():
        return False, f"didn't call a tool (good) but the answer is wrong/missing: {final_text!r}"
    return True, f"correctly answered from injected context without re-fetching: {final_text!r}"


def check_unnecessary_tool_call(model: str) -> tuple[bool, str]:
    """Not one of the original four documented failure modes, but added
    after real evaluation of the untrained baseline surfaced it directly:
    llama3.2:3b called web_search for plain arithmetic instead of just
    answering, even though SYSTEM_PROMPT explicitly forbids that. See the
    matching `unnecessary_tool_call` examples in synthetic_examples.jsonl."""
    messages = [sys_msg(), {"role": "user", "content": "What's 15 times 4?"}]
    response = CLIENT.chat(model=model, messages=messages, tools=TOOL_SCHEMAS, stream=False)
    msg = response.message
    if msg.tool_calls:
        return False, f"called {msg.tool_calls[0].function.name} for plain arithmetic instead of just answering"
    if "60" not in (msg.content or ""):
        return False, f"didn't call a tool (good) but got the arithmetic wrong: {msg.content!r}"
    return True, f"answered directly and correctly: {msg.content!r}"


def check_lost_thread(model: str) -> tuple[bool, str]:
    messages = [
        sys_msg(),
        {"role": "user", "content": "I'm planning a trip to Portugal in October."},
        {"role": "assistant", "content": "Nice! October's a good time to go — mild weather, fewer crowds."},
        {"role": "user", "content": "What's a good app for tracking my packing list?"},
        {"role": "assistant", "content": "PackPoint and Sortly are both popular for trip packing lists."},
        {"role": "user", "content": "Oh nice, remind me what month I said I was going again?"},
    ]
    response = CLIENT.chat(model=model, messages=messages, tools=TOOL_SCHEMAS, stream=False)
    final_text = response.message.content or ""
    if "october" not in final_text.lower():
        return False, f"lost the thread — didn't recall October from 3 turns earlier: {final_text!r}"
    return True, f"correctly recalled October: {final_text!r}"


FAILURE_MODE_CHECKS = {
    "skip_and_fabricate": check_skip_and_fabricate,
    "wrong_question_answered": check_wrong_question_answered,
    "redundant_refetch": check_redundant_refetch,
    "unnecessary_tool_call": check_unnecessary_tool_call,
    "lost_thread_long_conversation": check_lost_thread,
}

REGRESSION_PROMPTS = [
    "Tell me one interesting fact about octopuses.",
    "What's a good synonym for 'happy'?",
    "What year did the first moon landing happen?",
]


def run_regression_check(model: str):
    print("\n--- Plain-conversation regression check (read these yourself — no automated grading) ---")
    for prompt in REGRESSION_PROMPTS:
        messages = [sys_msg(), {"role": "user", "content": prompt}]
        response = CLIENT.chat(model=model, messages=messages, tools=TOOL_SCHEMAS, stream=False)
        msg = response.message
        if msg.tool_calls:
            tool_name = msg.tool_calls[0].function.name
            print(f"  Q: {prompt}\n  A: (called {tool_name} instead of answering directly — SYSTEM_PROMPT explicitly "
                  f"says never shell out for arithmetic/things you already know; this is exactly the kind of "
                  f"over-eager tool call the fine-tune targets)\n")
        elif not msg.content:
            print(f"  Q: {prompt}\n  A: (genuinely empty reply, no tool call either — worth a closer look)\n")
        else:
            print(f"  Q: {prompt}\n  A: {msg.content}\n")


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: evaluate.py <model_name>  (e.g. llama3.2:3b or javi-toolfix)")
    model = sys.argv[1]

    available = {m.model for m in CLIENT.list().models}
    matches = [m for m in available if m == model or m.startswith(model + ":")]
    if not matches and model not in available:
        sys.exit(f"'{model}' not found in `ollama list` ({sorted(available)}). Pull/create it first.")

    print(f"=== Evaluating {model} against {len(FAILURE_MODE_CHECKS)} held-out failure-mode cases ===\n")
    passed = 0
    for name, check in FAILURE_MODE_CHECKS.items():
        ok, detail = check(model)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}\n  {detail}\n")
        passed += ok

    print(f"=== {passed}/{len(FAILURE_MODE_CHECKS)} failure-mode cases passed ===")
    run_regression_check(model)


if __name__ == "__main__":
    main()
