import json
import uuid
from collections.abc import Iterator

from core.auth.users import LOOPBACK_USER, User
from core.brain.pending_actions import (
    create_pending_action,
    list_pending_actions,
    load_pending_action,
    normalize_message,
    remove_pending_action,
)
from core.brain.policy import BASE_SYSTEM_PROMPT
from core.brain.llm import chat_once, stream_chat
from core.memory.knowledge import recall_facts, remember_fact
from core.memory.store import add_message, get_history, list_preferences
from core.memory.vector_store import add_memory, search_memories
from tools.registry import APPROVAL_REQUIRED, INFORMATIONAL_TOOLS, TOOL_SCHEMAS, describe_pending, execute_tool

SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

MAX_TOOL_ITERATIONS = 5
RECENT_HISTORY_LIMIT = 10  # messages; older context relies on vector recall instead
MAX_INJECTED_PREFERENCES = 30  # most recent — a sanity cap, not expected to bite in normal use


def handle_message(session_id: str, user_message: str, requester: User | None = None) -> Iterator[dict]:
    requester = requester or LOOPBACK_USER
    add_message(session_id, "user", user_message)
    recent_history = get_history(session_id)[-RECENT_HISTORY_LIMIT:]

    system_content = SYSTEM_PROMPT

    # Unlike memories/facts below, preferences are injected in FULL and
    # unconditionally, every turn — they're standing instructions (a
    # correction, "always"/"never" do X, what to call the user), not
    # something to use only if relevant to the current message.
    preferences = list_preferences()[-MAX_INJECTED_PREFERENCES:]
    if preferences:
        system_content += (
            "\n\nStanding preferences and corrections the user has taught you — "
            "ALWAYS follow these, in every reply, not just when they seem relevant:\n"
        )
        system_content += "\n".join(f"- {p['text']}" for p in preferences)

    memories = search_memories(session_id, user_message, k=3)
    if memories:
        system_content += (
            "\n\nBackground only — possibly-relevant snippets retrieved from earlier in this "
            "conversation (outside recent context). Use ONLY if directly relevant to the "
            "user's current message; otherwise ignore them completely and never mention or "
            "repeat them:\n"
        )
        system_content += "\n".join(f"- {m}" for m in memories)

    facts = recall_facts(user_message, k=3)
    if facts:
        system_content += (
            "\n\nThings you've looked up and learned in past conversations (web searches, "
            "page reads, screen looks, file reads) that might be relevant. Use ONLY if "
            "directly relevant to the user's current message; otherwise ignore completely:\n"
        )
        system_content += "\n".join(f"- {f}" for f in facts)

    messages = [{"role": "system", "content": system_content}, *recent_history]
    yield from _agent_loop(session_id, user_message, messages, requester)


def resume_after_approval(action_id: str, approved: bool, approver: User | None = None) -> Iterator[dict]:
    approver = approver or LOOPBACK_USER
    pending = load_pending_action(action_id)
    if pending is None:
        yield {"type": "error", "message": "Unknown or already-resolved action_id"}
        return
    if pending["requires_admin"] and not approver.is_admin:
        # The self-approval enforcement point: a standard user's own
        # approval-gated request was flagged requires_admin when it was
        # created (see _agent_loop below), and only an admin (or the person
        # at the keyboard, who is always the synthetic admin user) may
        # resolve it — not the original requester approving themselves.
        yield {"type": "error", "message": "This action requires admin approval."}
        return
    remove_pending_action(action_id)

    messages = pending["messages"]
    user_message = pending["user_message"]
    requester = pending["requester"]
    call = pending["tool_call"]
    name = call["function"]["name"]
    args = call["function"]["arguments"]

    if approved:
        try:
            outcome = execute_tool(name, args)
            result = f"The user approved this action and it already ran successfully. Result: {json.dumps(outcome, default=str)}"
            yield {"type": "tool_result", "tool": name, "result": outcome}
        except Exception as e:
            result = f"The user approved this action but it failed when it ran: {e}"
            yield {"type": "tool_result", "tool": name, "result": result}
    else:
        result = "The user denied this action. Do not attempt it again this turn."
        yield {"type": "tool_denied", "tool": name}

    messages.append({"role": "tool", "content": result})
    yield from _agent_loop(pending["session_id"], user_message, messages, requester)


def _agent_loop(session_id: str, user_message: str, messages: list, requester: User) -> Iterator[dict]:
    for _ in range(MAX_TOOL_ITERATIONS):
        response = chat_once(messages, tools=TOOL_SCHEMAS)
        tool_calls = response.tool_calls
        if not tool_calls:
            break

        messages.append(normalize_message(response))

        for call in tool_calls:
            name = call.function.name
            args = dict(call.function.arguments)
            call_dict = {"function": {"name": name, "arguments": args}}

            if name in APPROVAL_REQUIRED:
                action_id = str(uuid.uuid4())
                requires_admin = not requester.is_admin
                create_pending_action(
                    action_id=action_id,
                    session_id=session_id,
                    user_message=user_message,
                    messages=messages,
                    tool_name=name,
                    tool_args=args,
                    requester=requester,
                    requires_admin=requires_admin,
                )
                yield {
                    "type": "pending_action",
                    "action_id": action_id,
                    "tool": name,
                    "args": args,
                    "description": describe_pending(name, args),
                    "requires_admin": requires_admin,
                }
                return

            yield {"type": "tool_call", "tool": name, "args": args}
            try:
                result = execute_tool(name, args)
                if name in INFORMATIONAL_TOOLS:
                    lookup_key = f"{name}:{json.dumps(args, sort_keys=True)}"
                    remember_fact(lookup_key, f"Tool: {name}, args: {args}\nResult: {result}")
            except Exception as e:
                result = f"Error running {name}: {e}"
            yield {"type": "tool_result", "tool": name, "result": result}
            messages.append({"role": "tool", "content": json.dumps(result, default=str)})
    else:
        messages.append({"role": "system", "content": "Tool iteration limit reached — answer with what you have."})

    full_reply = []
    for token in stream_chat(messages):
        full_reply.append(token)
        yield {"type": "token", "content": token}

    reply_text = "".join(full_reply)
    add_message(session_id, "assistant", reply_text)
    add_memory(session_id, f"User asked: {user_message}\nJavi answered: {reply_text}")
    yield {"type": "done"}
