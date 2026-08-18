import ctypes
import subprocess

import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities

SHUTDOWN_COMMAND_TIMEOUT_SECONDS = 10


def _volume_interface():
    return AudioUtilities.GetSpeakers().EndpointVolume


def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    _volume_interface().SetMasterVolumeLevelScalar(level / 100.0, None)
    return f"Volume set to {level}%"


def mute_volume(mute: bool) -> str:
    _volume_interface().SetMute(1 if mute else 0, None)
    return "Muted" if mute else "Unmuted"


def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    sbc.set_brightness(level)
    return f"Brightness set to {level}%"


def lock_screen() -> str:
    ctypes.windll.user32.LockWorkStation()
    return "Locked the screen"


def sleep_pc() -> str:
    # Hibernate=False (sleep/standby, not hibernate), ForceCritical=True
    # (don't block on apps that refuse to sleep), DisableWakeEvent=False.
    ctypes.windll.powrprof.SetSuspendState(False, True, False)
    return "Put the PC to sleep"


def _run_power_command(args: list[str]) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=SHUTDOWN_COMMAND_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed with exit code {result.returncode}")
    return result.stdout.strip()


def shutdown_pc(delay_seconds: int = 30) -> str:
    # No /f (force-close apps) — Windows' own unsaved-changes prompts in
    # other apps still apply, a real safety net on top of the approval gate.
    _run_power_command(["shutdown", "/s", "/t", str(max(0, int(delay_seconds)))])
    return f"Shutting down in {delay_seconds}s — say 'cancel shutdown' to stop it"


def restart_pc(delay_seconds: int = 30) -> str:
    _run_power_command(["shutdown", "/r", "/t", str(max(0, int(delay_seconds)))])
    return f"Restarting in {delay_seconds}s — say 'cancel shutdown' to stop it"


def cancel_shutdown() -> str:
    _run_power_command(["shutdown", "/a"])
    return "Cancelled the pending shutdown/restart"


def toggle_wifi(enabled: bool) -> str:
    # Requires an elevated (admin) process on most Windows configurations —
    # if Javi isn't running as admin this will surface that failure via the
    # command's stderr rather than silently doing nothing.
    state = "enabled" if enabled else "disabled"
    result = subprocess.run(
        ["netsh", "interface", "set", "interface", "Wi-Fi", f"admin={state}"],
        capture_output=True,
        text=True,
        timeout=SHUTDOWN_COMMAND_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "netsh failed")
    return f"WiFi {state}"
