from core.auth.users import User
from core.memory.store import (
    delete_pending_action,
    get_pending_action,
    list_pending_actions as list_pending_action_rows,
    upsert_pending_action,
)
from tools.registry import describe_pending


def normalize_tool_call(call) -> dict:
    return {
        "function": {
            "name": call.function.name,
            "arguments": dict(call.function.arguments),
        }
    }


def normalize_message(message) -> dict:
    if isinstance(message, dict):
        normalized = {
            "role": message.get("role", "assistant"),
            "content": message.get("content", "") or "",
        }
        if message.get("tool_calls"):
            normalized["tool_calls"] = message["tool_calls"]
        return normalized

    normalized = {
        "role": getattr(message, "role", "assistant"),
        "content": getattr(message, "content", "") or "",
    }
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        normalized["tool_calls"] = [normalize_tool_call(call) for call in tool_calls]
    return normalized


def normalize_messages(messages: list) -> list[dict]:
    return [normalize_message(message) for message in messages]


def create_pending_action(
    action_id: str,
    session_id: str,
    user_message: str,
    messages: list,
    tool_name: str,
    tool_args: dict,
    requester: User,
    requires_admin: bool,
) -> None:
    upsert_pending_action(
        action_id=action_id,
        session_id=session_id,
        user_message=user_message,
        messages=normalize_messages(messages),
        tool_name=tool_name,
        tool_args=tool_args,
        requester=requester,
        requires_admin=requires_admin,
    )


def load_pending_action(action_id: str) -> dict | None:
    pending = get_pending_action(action_id)
    if pending is None:
        return None
    requester = pending["requester"]
    pending["requester"] = User(
        id=requester["id"],
        username=requester["username"],
        role=requester["role"],
    )
    return pending


def remove_pending_action(action_id: str) -> bool:
    return delete_pending_action(action_id)


def list_pending_actions() -> list[dict]:
    rows = list_pending_action_rows()
    for row in rows:
        row["description"] = describe_pending(row["tool"], row["args"])
    return rows
