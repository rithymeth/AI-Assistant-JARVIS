"""Helpers for model-produced tool calls."""

from __future__ import annotations

import json


def parse_tool_arguments(raw) -> dict:
    """Ollama sometimes returns tool arguments as a dict, sometimes as a JSON string."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments JSON must be an object")
        return parsed
    return dict(raw)
