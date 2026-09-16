"""Canonical tool dispatch and small registry compatibility fixes."""

from __future__ import annotations


def execute_tool(name: str, args: dict | None = None):
    from tools import registry

    handler = registry.HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return handler(args or {})


def apply_registry_compat() -> None:
    from tools import registry

    registry.HANDLERS["get_time_in"] = lambda args: registry._call(
        "tools.worldclock", "get_time_in", args.get("location")
    )
    registry.INFORMATIONAL_TOOLS.add("describe_camera")
    registry.execute_tool = execute_tool

    for schema in registry.TOOL_SCHEMAS:
        fn = schema.get("function") or {}
        if fn.get("name") != "get_time_in":
            continue
        fn["description"] = (
            "Get the current real, DST-aware local time and date. "
            "Pass a city, or omit location for this machine."
        )
        params = fn.setdefault("parameters", {})
        props = params.setdefault("properties", {})
        props["location"] = {
            "type": "string",
            "description": "City name, e.g. 'Tokyo'. Omit for this machine.",
        }
        params["required"] = []


apply_registry_compat()
