import json
import uuid
from collections.abc import Iterator

from core.auth.users import LOOPBACK_USER, User
from core.brain.llm import chat_once, stream_chat
from core.memory.knowledge import recall_facts, remember_fact
from core.memory.store import add_message, get_history, list_preferences
from core.memory.vector_store import add_memory, search_memories
from tools.registry import APPROVAL_REQUIRED, INFORMATIONAL_TOOLS, TOOL_SCHEMAS, describe_pending, execute_tool

SYSTEM_PROMPT = (
    "You are Javi, a voice-first AI assistant running locally on the user's machine, with real "
    "control over their PC. Be concise — your replies are spoken aloud, so avoid long lists, "
    "code blocks, or markdown; speak in plain, short sentences. "
    "You have tools available: read_file, write_file, list_dir, run_command, web_search, "
    "fetch_page, open_app, close_app, focus_window, list_windows, describe_screen, "
    "describe_camera, click_at, type_text, press_key, set_volume, mute_volume, set_brightness, "
    "lock_screen, sleep_pc, shutdown_pc, restart_pc, cancel_shutdown, toggle_wifi, "
    "list_processes, kill_process, read_any_file, write_any_file, list_any_dir, "
    "remember_preference, recall_preferences, forget_preference, set_reminder, "
    "list_reminders, cancel_reminder, add_note, list_notes, remove_note, clear_list, "
    "get_weather, get_time_in, and get_system_status. "
    "describe_camera captures a frame from the user's physical webcam right now — use it when "
    "asked what you see/who's there in person, as distinct from describe_screen which looks at "
    "the computer screen. open_app can open ANYTHING by name or path — apps, files, folders, or "
    "URLs — not just named applications. fetch_page reads a specific page's full text, "
    "web_search finds pages/URLs by query; use web_search first, then fetch_page on a promising "
    "result if you need more than the snippet. read_file/write_file/list_dir only touch the "
    "sandboxed workspace directory; read_any_file/write_any_file/list_any_dir touch ANY path on "
    "the whole machine — prefer the sandboxed versions unless the user is clearly asking about a "
    "location outside the workspace. shutdown_pc/restart_pc take an optional delay_seconds "
    "(default 30) and can be undone with cancel_shutdown if called in time. kill_process force-"
    "kills by PID or a name substring — confirm which process if the user's request is ambiguous "
    "and more than one process could match. "
    "get_weather returns real current conditions and today's forecast for a named city — use it "
    "for any weather question instead of answering from your own knowledge, since you don't "
    "actually know today's weather. Omit location only if the user clearly means 'here'/'today' "
    "with no city named and a default is configured; otherwise ask which city if none was given. "
    "get_time_in returns the real current time and date for a named city (DST-aware) — call it "
    "for ANY 'what time is it in X' / 'what time is it there' question. You do not have a live "
    "clock and do not actually know the current time anywhere, including this machine's own "
    "timezone, so never state a specific time without calling this tool first. "
    "get_system_status returns this PC's real current CPU/memory/disk/battery/uptime — call it "
    "for any question about how the machine itself is doing right now (battery level, free disk "
    "space, whether it's running hot/slow); never guess these numbers. "
    "You also have a persistent knowledge base of things you've looked up in past "
    "conversations (injected below when relevant) — treat it as memory, not as something to "
    "re-explain to the user unless they ask what you know. Separately, you have STANDING "
    "PREFERENCES (injected below, in full, every turn) — these are corrections and instructions "
    "the user has taught you, and unlike the knowledge base you must follow them unconditionally, "
    "not just when relevant. Call remember_preference whenever the user corrects a mistake you "
    "made, gives a standing instruction ('always'/'never' do X, what to call them), or explicitly "
    "says to remember something — do this proactively, without being asked to use the tool by "
    "name. Call forget_preference if they say to stop doing something you were told to remember, "
    "or that a preference is no longer right. Call recall_preferences if they ask what you "
    "remember or know about them. "
    "set_reminder takes EITHER delay_minutes (a plain integer, for 'remind me in X minutes/hours' "
    "— convert hours to minutes yourself, e.g. 'in 2 hours' means delay_minutes=120) OR at_time "
    "(a clock time string like '15:00' or '3:00 PM', for 'remind me at TIME', resolving to the "
    "next occurrence of that time) — never both, never neither. Never try to compute an absolute "
    "date/time string yourself; pass the simple delay or clock time and let the tool do the math. "
    "Reminders are spoken aloud automatically when due, without the user needing to ask. "
    "add_note/list_notes/remove_note/clear_list manage named lists (shopping list, to-do list, "
    "whatever the user calls it) — plain content to track, NOT a standing instruction like a "
    "preference and NOT time-triggered like a reminder. Default to the 'general' list only if "
    "the user doesn't name one; use the name they say (e.g. 'add milk to my shopping list' -> "
    "list_name='shopping'). Call list_notes with no list_name if they just ask what's on their "
    "list(s) without specifying which. "
    "open_app/close_app/focus_window/list_windows/describe_screen/describe_camera/web_search/"
    "fetch_page/list_processes/cancel_shutdown/remember_preference/recall_preferences/"
    "forget_preference/set_reminder/list_reminders/cancel_reminder/add_note/list_notes/"
    "remove_note/clear_list run immediately, no approval "
    "needed. write_file, "
    "run_command, click_at, type_text, press_key, set_volume, mute_volume, set_brightness, "
    "lock_screen, sleep_pc, shutdown_pc, restart_pc, toggle_wifi, kill_process, read_any_file, "
    "write_any_file, and list_any_dir ALWAYS require human approval and will pause until "
    "approved — this is a hard rule with no exceptions, even for actions that seem harmless, "
    "because simulated clicks/keystrokes, shell commands, system changes, and anything outside "
    "the workspace sandbox are hard to undo. When you call one of those, do not generate any "
    "reply text in that same turn, since you won't know the outcome yet. "
    "If a 'tool' message says an approved action 'already ran successfully', that means it "
    "is DONE — report it as completed, in the past tense. Never say you are 'still waiting for "
    "approval' about an action a tool message already told you ran successfully. "
    "Answer directly from your own knowledge for general questions, trivia, math, definitions, "
    "and anything else you can just answer. Only use a tool when the task genuinely requires "
    "touching this specific machine or needs live information you don't know. EXCEPTION: weather "
    "is NOT something you can just answer — you have no live data feed and do not know today's "
    "actual conditions anywhere, so any weather question (even one that sounds like idle small "
    "talk, e.g. 'nice out today?' or 'is it raining?') MUST call get_weather rather than guessing "
    "or making up a plausible-sounding answer. SAME EXCEPTION for the current time/date anywhere "
    "(including 'here') — you do not have a live clock, so any 'what time is it' question MUST "
    "call get_time_in rather than stating a time from memory. "
    "Approval-gated tools interrupt the user, so never use them for things you can compute "
    "or already know yourself (e.g. never shell out for arithmetic). "
    "After a tool like describe_screen, list_windows, read_file, or web_search returns "
    "information, your final reply MUST actually relay that information to the user in plain "
    "spoken language — never reply with just 'Completed' or 'Done' when the tool result contains "
    "the actual answer to what they asked. The user cannot see the tool result, only hear you. "
    "Stick strictly to what the tool result actually says — never invent additional objects, "
    "text, windows, or details that were not in the tool result, even if you're inclined to "
    "elaborate. If the tool result is vague, relay it as-is rather than filling in guesses."
)

MAX_TOOL_ITERATIONS = 5
RECENT_HISTORY_LIMIT = 10  # messages; older context relies on vector recall instead
MAX_INJECTED_PREFERENCES = 30  # most recent — a sanity cap, not expected to bite in normal use

# In-memory pending tool-call approvals, keyed by action_id. Ephemeral by design —
# lost on server restart, which is acceptable for a short-lived approval prompt.
PENDING_ACTIONS: dict[str, dict] = {}


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
    pending = PENDING_ACTIONS.get(action_id)
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
    PENDING_ACTIONS.pop(action_id, None)

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


def list_pending_actions() -> list[dict]:
    """All in-flight approval-gated requests across every session — used by
    the admin-only /tools/pending endpoint so an admin can see and resolve a
    standard user's requires_admin request from a different session/device."""
    result = []
    for action_id, pending in PENDING_ACTIONS.items():
        name = pending["tool_call"]["function"]["name"]
        args = pending["tool_call"]["function"]["arguments"]
        result.append(
            {
                "action_id": action_id,
                "session_id": pending["session_id"],
                "tool": name,
                "args": args,
                "description": describe_pending(name, args),
                "requires_admin": pending["requires_admin"],
                "requested_by": pending["requester"].username,
            }
        )
    return result


def _agent_loop(session_id: str, user_message: str, messages: list, requester: User) -> Iterator[dict]:
    for _ in range(MAX_TOOL_ITERATIONS):
        response = chat_once(messages, tools=TOOL_SCHEMAS)
        tool_calls = response.tool_calls
        if not tool_calls:
            break

        messages.append(response)

        for call in tool_calls:
            name = call.function.name
            args = dict(call.function.arguments)
            call_dict = {"function": {"name": name, "arguments": args}}

            if name in APPROVAL_REQUIRED:
                action_id = str(uuid.uuid4())
                requires_admin = not requester.is_admin
                PENDING_ACTIONS[action_id] = {
                    "session_id": session_id,
                    "user_message": user_message,
                    "messages": messages,
                    "tool_call": call_dict,
                    "requester": requester,
                    "requires_admin": requires_admin,
                }
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
