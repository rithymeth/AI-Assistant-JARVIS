from tools.automation import click_at, press_key, type_text
from tools.file_system import list_any_dir, list_dir, read_any_file, read_file, write_any_file, write_file
from tools.notes import add_note, clear_list, list_notes, remove_note
from tools.pc_control import close_app, focus_window, list_windows, open_app, take_screenshot
from tools.preferences import forget_preference, recall_preferences, remember_preference
from tools.process_control import kill_process, list_processes
from tools.reminders import cancel_reminder, list_reminders, set_reminder
from tools.shell import run_command
from tools.system_control import (
    cancel_shutdown,
    lock_screen,
    mute_volume,
    restart_pc,
    set_brightness,
    set_volume,
    shutdown_pc,
    sleep_pc,
    toggle_wifi,
)
from tools.system_status import get_system_status
from tools.weather import get_weather
from tools.web_fetch import fetch_page
from tools.web_search import web_search
from tools.worldclock import get_time_in
from vision.camera import describe_camera
from vision.screen import describe_screen

# Full-machine control, added on explicit request: "I want Javi to have
# full control if I told him to" — every single one of these still goes
# through the same mandatory voice/card approval as write_file/run_command
# always have, no exceptions. cancel_shutdown is the one deliberate
# exception in the OTHER direction — it undoes a pending dangerous action,
# so gating IT behind another approval prompt would work against the
# safety purpose of having it at all.
APPROVAL_REQUIRED = {
    "write_file",
    "run_command",
    "click_at",
    "type_text",
    "press_key",
    "set_volume",
    "mute_volume",
    "set_brightness",
    "lock_screen",
    "sleep_pc",
    "shutdown_pc",
    "restart_pc",
    "toggle_wifi",
    "kill_process",
    "read_any_file",
    "write_any_file",
    "list_any_dir",
}

# Tools whose results are worth remembering long-term (facts/knowledge worth
# recalling later), as opposed to tools that just take an action.
INFORMATIONAL_TOOLS = {
    "web_search",
    "fetch_page",
    "describe_screen",
    "list_windows",
    "read_file",
    "list_processes",
    "recall_preferences",
    "list_reminders",
    "list_notes",
    "get_weather",
    "get_time_in",
    "get_system_status",
}

HANDLERS = {
    "read_file": lambda args: read_file(args["path"]),
    "write_file": lambda args: write_file(args["path"], args["content"]),
    "list_dir": lambda args: list_dir(args.get("path", ".")),
    "run_command": lambda args: run_command(args["command"]),
    "web_search": lambda args: web_search(args["query"]),
    "get_weather": lambda args: get_weather(args.get("location")),
    "get_time_in": lambda args: get_time_in(args["location"]),
    "get_system_status": lambda args: get_system_status(),
    "fetch_page": lambda args: fetch_page(args["url"]),
    "open_app": lambda args: open_app(args["name"]),
    "close_app": lambda args: close_app(args["title"]),
    "focus_window": lambda args: focus_window(args["title"]),
    "list_windows": lambda args: list_windows(),
    "describe_screen": lambda args: describe_screen(),
    "describe_camera": lambda args: describe_camera(),
    "click_at": lambda args: click_at(int(args["x"]), int(args["y"])),
    "type_text": lambda args: type_text(args["text"]),
    "press_key": lambda args: press_key(args["key"]),
    "set_volume": lambda args: set_volume(int(args["level"])),
    "mute_volume": lambda args: mute_volume(bool(args["mute"])),
    "set_brightness": lambda args: set_brightness(int(args["level"])),
    "lock_screen": lambda args: lock_screen(),
    "sleep_pc": lambda args: sleep_pc(),
    "shutdown_pc": lambda args: shutdown_pc(int(args.get("delay_seconds", 30))),
    "restart_pc": lambda args: restart_pc(int(args.get("delay_seconds", 30))),
    "cancel_shutdown": lambda args: cancel_shutdown(),
    "toggle_wifi": lambda args: toggle_wifi(bool(args["enabled"])),
    "list_processes": lambda args: list_processes(),
    "kill_process": lambda args: kill_process(args["name_or_pid"]),
    "read_any_file": lambda args: read_any_file(args["path"]),
    "write_any_file": lambda args: write_any_file(args["path"], args["content"]),
    "list_any_dir": lambda args: list_any_dir(args["path"]),
    "remember_preference": lambda args: remember_preference(args["text"]),
    "recall_preferences": lambda args: recall_preferences(),
    "forget_preference": lambda args: forget_preference(args["text_or_id"]),
    "set_reminder": lambda args: set_reminder(args["text"], args.get("delay_minutes"), args.get("at_time")),
    "list_reminders": lambda args: list_reminders(),
    "cancel_reminder": lambda args: cancel_reminder(args["text_or_id"]),
    "add_note": lambda args: add_note(args["text"], args.get("list_name", "general")),
    "list_notes": lambda args: list_notes(args.get("list_name")),
    "remove_note": lambda args: remove_note(args["text_or_id"], args.get("list_name")),
    "clear_list": lambda args: clear_list(args["list_name"]),
}

# Human-readable one-liners for pending (approval-required) tool calls, spoken
# aloud by the voice-only frontend before it asks the user to confirm.
DESCRIBE_PENDING = {
    "write_file": lambda a: f"write to file {a.get('path')}",
    "run_command": lambda a: f"run the command: {a.get('command')}",
    "click_at": lambda a: f"click at position {a.get('x')}, {a.get('y')}",
    "type_text": lambda a: f"type the text: {a.get('text')}",
    "press_key": lambda a: f"press the {a.get('key')} key",
    "set_volume": lambda a: f"set the volume to {a.get('level')}%",
    "mute_volume": lambda a: "mute the volume" if a.get("mute") else "unmute the volume",
    "set_brightness": lambda a: f"set screen brightness to {a.get('level')}%",
    "lock_screen": lambda a: "lock the screen",
    "sleep_pc": lambda a: "put the PC to sleep",
    "shutdown_pc": lambda a: f"shut down the PC in {a.get('delay_seconds', 30)} seconds",
    "restart_pc": lambda a: f"restart the PC in {a.get('delay_seconds', 30)} seconds",
    "toggle_wifi": lambda a: "turn WiFi on" if a.get("enabled") else "turn WiFi off",
    "kill_process": lambda a: f"kill the process: {a.get('name_or_pid')}",
    "read_any_file": lambda a: f"read the file at {a.get('path')} (outside the sandbox)",
    "write_any_file": lambda a: f"write to the file at {a.get('path')} (outside the sandbox)",
    "list_any_dir": lambda a: f"list the directory at {a.get('path')} (outside the sandbox)",
}


def describe_pending(name: str, args: dict) -> str:
    template = DESCRIBE_PENDING.get(name)
    return template(args) if template else f"run {name} with {args}"


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the sandboxed workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path relative to the workspace root"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write (create or overwrite) a text file in the sandboxed workspace directory. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace root"},
                    "content": {"type": "string", "description": "Full text content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories inside the sandboxed workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path relative to workspace root, default '.'"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command inside the sandboxed workspace directory. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to run"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web and return top results (title, url, snippet).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather and today's forecast for a city. Omit location to use the configured default, if any.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name, e.g. 'Seattle' — omit to use the default location"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_in",
            "description": "Get the current real, DST-aware local time and date for a named city.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name, e.g. 'Tokyo'"}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get this PC's current CPU usage, memory usage, disk space free on every drive, battery level (if any), and uptime.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": (
                "Open ANYTHING by name or path, like the Windows Run dialog: an application "
                "('notepad', 'chrome', 'spotify'), a file ('C:\\Users\\me\\Documents\\notes.txt' — "
                "opens in its default program), a folder ('C:\\Users\\me\\Downloads' — opens in "
                "File Explorer), or a URL ('https://example.com' — opens in the default browser)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Application name, file/folder path, or URL to open"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a specific web page by URL and return its readable text content (not just a search snippet).",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Full URL to fetch, e.g. https://example.com/page"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close open window(s) whose title contains the given text.",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Substring to match against open window titles"}},
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring the window whose title contains the given text to the foreground.",
            "parameters": {
                "type": "object",
                "properties": {"title": {"type": "string", "description": "Substring to match against open window titles"}},
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_windows",
            "description": "List the titles of all currently open windows.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_screen",
            "description": "Take a screenshot of the user's screen right now and describe what's on it (focused app, what they're doing, visible text).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_camera",
            "description": "Capture a frame from the user's webcam right now and describe what/who is visible.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_at",
            "description": "Simulate a mouse click at specific screen coordinates. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate in pixels"},
                    "y": {"type": "integer", "description": "Y coordinate in pixels"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into whatever field/app currently has keyboard focus. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Text to type"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a single keyboard key (e.g. 'enter', 'tab', 'esc'). Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string", "description": "Key name, e.g. 'enter', 'tab', 'esc', 'a'"}},
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set the system speaker volume. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer", "description": "Volume level, 0-100"}},
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mute_volume",
            "description": "Mute or unmute the system speaker volume. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"mute": {"type": "boolean", "description": "true to mute, false to unmute"}},
                "required": ["mute"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set the screen brightness. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer", "description": "Brightness level, 0-100"}},
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "Lock the PC's screen immediately, requiring a password to unlock. Requires human approval.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_pc",
            "description": "Put the PC to sleep (standby) immediately. Requires human approval.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_pc",
            "description": "Shut down the PC after a delay. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "description": "Seconds before shutdown, default 30"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_pc",
            "description": "Restart the PC after a delay. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "description": "Seconds before restart, default 30"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_shutdown",
            "description": "Cancel a pending shutdown or restart scheduled by shutdown_pc/restart_pc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_wifi",
            "description": "Turn the WiFi adapter on or off. May require Javi to be running as administrator. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"enabled": {"type": "boolean", "description": "true to turn on, false to turn off"}},
                "required": ["enabled"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "List all currently running processes with their PID, name, and memory usage, sorted by memory (highest first).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Force-kill running process(es) by exact PID or by a case-insensitive substring match against the process name. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_pid": {"type": "string", "description": "A process ID, or a substring of the process name"}
                },
                "required": ["name_or_pid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_any_file",
            "description": "Read a text file from ANYWHERE on the machine (not sandboxed to the workspace directory). Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute path to the file"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_any_file",
            "description": "Write (create or overwrite) a text file ANYWHERE on the machine (not sandboxed to the workspace directory). Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file"},
                    "content": {"type": "string", "description": "Full text content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_any_dir",
            "description": "List files and directories at ANY absolute path on the machine (not sandboxed to the workspace directory). Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute path to the directory"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_preference",
            "description": (
                "Permanently remember a standing instruction, correction, or preference about how "
                "to behave — e.g. the user corrects a mistake, says 'always'/'never' do something, "
                "tells you to call them something, or explicitly says to remember something. "
                "Stored preferences are included in EVERY future conversation, not just when related "
                "to the current topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "A concise statement of the preference/correction, written as a standing instruction",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_preferences",
            "description": "List every standing preference/correction currently remembered, e.g. if the user asks what you remember about them.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_preference",
            "description": "Forget a previously-remembered preference, by its id or by a substring of its text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_or_id": {"type": "string", "description": "A preference id, or a substring of its text"}
                },
                "required": ["text_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": (
                "Set a reminder that will be spoken aloud when it comes due. Provide EXACTLY ONE of "
                "delay_minutes (for 'remind me in X minutes/hours') or at_time (for 'remind me at TIME') "
                "— never both, never neither. Do the minutes/hours-to-number conversion yourself (e.g. "
                "'in 2 hours' -> delay_minutes=120); do not attempt to compute an absolute date/time yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to remind the user about"},
                    "delay_minutes": {"type": "integer", "description": "Minutes from now, e.g. 20"},
                    "at_time": {"type": "string", "description": "A clock time, e.g. '15:00' or '3:00 PM' — next occurrence"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List every reminder that hasn't fired yet, soonest first.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "Cancel a pending reminder, by its id or by a substring of its text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_or_id": {"type": "string", "description": "A reminder id, or a substring of its text"}
                },
                "required": ["text_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add an item to a named list (e.g. a shopping list, a to-do list, or any other list the user names). Defaults to a general list if no list is named.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The item/note text to add"},
                    "list_name": {"type": "string", "description": "Which list, e.g. 'shopping' or 'todo' — defaults to 'general'"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List items on a named list. Omit list_name to see every list.",
            "parameters": {
                "type": "object",
                "properties": {"list_name": {"type": "string", "description": "Which list to show, e.g. 'shopping' — omit for all lists"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_note",
            "description": "Remove an item from a list, by its id or by a substring of its text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text_or_id": {"type": "string", "description": "A note id, or a substring of its text"},
                    "list_name": {"type": "string", "description": "Restrict the match to this list — omit to match across all lists"},
                },
                "required": ["text_or_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_list",
            "description": "Remove every item from a named list at once.",
            "parameters": {
                "type": "object",
                "properties": {"list_name": {"type": "string", "description": "Which list to clear entirely, e.g. 'shopping'"}},
                "required": ["list_name"],
            },
        },
    },
]


def execute_tool(name: str, args: dict):
    return HANDLERS[name](args)
