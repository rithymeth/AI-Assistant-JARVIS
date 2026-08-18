import psutil

# Killing these can bluescreen or hard-crash the OS outright, not just
# misbehave — unlike anything else this tool set touches, that's
# unrecoverable, so it's blocked even under approval (same defense-in-depth
# reasoning as open_app's shell-metacharacter rejection: a single
# misheard/misinterpreted voice command shouldn't be able to take the whole
# machine down with zero chance to undo it).
PROTECTED_PROCESS_NAMES = {
    "system",
    "system idle process",
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
}


def list_processes() -> list[dict]:
    processes = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = p.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info["name"],
                    "memory_mb": round(info["memory_info"].rss / (1024 * 1024), 1) if info["memory_info"] else None,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue  # process exited or is unqueryable mid-scan — not an error, just skip it
    return sorted(processes, key=lambda p: p["memory_mb"] or 0, reverse=True)


def kill_process(name_or_pid: str) -> str:
    text = str(name_or_pid).strip()
    if text.isdigit():
        targets = [p for p in psutil.process_iter(["pid"]) if p.info["pid"] == int(text)]
    else:
        needle = text.lower()
        targets = [p for p in psutil.process_iter(["pid", "name"]) if needle in (p.info["name"] or "").lower()]

    if not targets:
        return f"No running process matches '{name_or_pid}'"

    blocked = [p for p in targets if (p.info.get("name") or "").lower() in PROTECTED_PROCESS_NAMES]
    if blocked:
        raise ValueError(
            f"Refusing to kill protected system process(es): {[p.info.get('name') for p in blocked]}"
        )

    killed = []
    for p in targets:
        try:
            p.kill()
            killed.append(p.info.get("name") or str(p.info["pid"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not killed:
        return f"Found process(es) matching '{name_or_pid}' but couldn't kill any (access denied?)"
    return f"Killed {len(killed)} process(es): {killed}"
