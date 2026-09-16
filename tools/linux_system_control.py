"""Best-effort system control on Linux/macOS. High-impact actions stay approval-gated."""

from __future__ import annotations

import shutil
import subprocess

COMMAND_TIMEOUT_SECONDS = 10


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or " ".join(args))
    return result.stdout.strip()


def brightness_cli_candidates(level: int) -> list[list[str]]:
    return [
        ["brightnessctl", "set", f"{level}%"],
        ["xbacklight", "-set", str(level)],
    ]


def lock_cli_candidates() -> list[list[str]]:
    return [
        ["loginctl", "lock-session"],
        ["xdg-screensaver", "lock"],
        ["gnome-screensaver-command", "-l"],
        ["dm-tool", "lock"],
    ]


def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    if shutil.which("pactl"):
        _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
        return f"Volume set to {level}%"
    if shutil.which("wpctl"):
        _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{level}%"])
        return f"Volume set to {level}%"
    raise RuntimeError("No PulseAudio/PipeWire volume tool found (pactl/wpctl)")


def mute_volume(mute: bool) -> str:
    flag = "1" if mute else "0"
    if shutil.which("pactl"):
        _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", flag])
        return "Muted" if mute else "Unmuted"
    if shutil.which("wpctl"):
        _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", flag])
        return "Muted" if mute else "Unmuted"
    raise RuntimeError("No PulseAudio/PipeWire mute tool found (pactl/wpctl)")


def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    errors: list[str] = []
    for args in brightness_cli_candidates(level):
        if not shutil.which(args[0]):
            continue
        try:
            _run(args)
            return f"Brightness set to {level}%"
        except Exception as exc:
            errors.append(f"{args[0]}: {exc}")
    try:
        import screen_brightness_control as sbc

        sbc.set_brightness(level)
        return f"Brightness set to {level}%"
    except Exception as exc:
        errors.append(f"sbc: {exc}")
    raise RuntimeError(
        "No brightness tool worked. Install brightnessctl or xbacklight. "
        + "; ".join(errors[-3:])
    )


def lock_screen() -> str:
    errors: list[str] = []
    for args in lock_cli_candidates():
        if not shutil.which(args[0]):
            continue
        try:
            _run(args)
            return "Locked the screen"
        except Exception as exc:
            errors.append(f"{args[0]}: {exc}")
    raise RuntimeError(
        "lock_screen needs loginctl, xdg-screensaver, gnome-screensaver-command, or dm-tool"
        + (f" ({'; '.join(errors[-2:])})" if errors else "")
    )


def sleep_pc() -> str:
    if shutil.which("systemctl"):
        _run(["systemctl", "suspend"])
        return "Put the PC to sleep"
    raise RuntimeError("sleep_pc needs systemctl on this OS")


def shutdown_pc(delay_seconds: int = 30) -> str:
    delay_seconds = max(0, int(delay_seconds))
    minutes = max(1, (delay_seconds + 59) // 60) if delay_seconds else 0
    if shutil.which("shutdown"):
        if delay_seconds == 0:
            _run(["shutdown", "-h", "now"])
        else:
            _run(["shutdown", "-h", f"+{minutes}"])
        return f"Shutting down in {delay_seconds}s — say 'cancel shutdown' to stop it"
    raise RuntimeError("shutdown command not found")


def restart_pc(delay_seconds: int = 30) -> str:
    delay_seconds = max(0, int(delay_seconds))
    minutes = max(1, (delay_seconds + 59) // 60) if delay_seconds else 0
    if shutil.which("shutdown"):
        if delay_seconds == 0:
            _run(["shutdown", "-r", "now"])
        else:
            _run(["shutdown", "-r", f"+{minutes}"])
        return f"Restarting in {delay_seconds}s — say 'cancel shutdown' to stop it"
    raise RuntimeError("shutdown command not found")


def cancel_shutdown() -> str:
    if shutil.which("shutdown"):
        _run(["shutdown", "-c"])
        return "Cancelled the pending shutdown/restart"
    raise RuntimeError("shutdown command not found")


def toggle_wifi(enabled: bool) -> str:
    if shutil.which("nmcli"):
        _run(["nmcli", "radio", "wifi", "on" if enabled else "off"])
        return f"WiFi {'enabled' if enabled else 'disabled'}"
    raise RuntimeError("toggle_wifi needs nmcli on this OS")
