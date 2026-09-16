from tools._platform import IS_WINDOWS

MAX_DELAY_SECONDS = 24 * 60 * 60


def _backend():
    if IS_WINDOWS:
        from tools import windows_system_control as backend
    else:
        from tools import linux_system_control as backend
    return backend


def clamp_percent(level) -> int:
    try:
        value = int(level)
    except (TypeError, ValueError) as exc:
        raise ValueError("Level must be a number from 0 to 100") from exc
    return max(0, min(100, value))


def clamp_delay(delay_seconds) -> int:
    try:
        value = int(delay_seconds)
    except (TypeError, ValueError):
        value = 30
    return max(0, min(value, MAX_DELAY_SECONDS))


def set_volume(level: int) -> str:
    return _backend().set_volume(clamp_percent(level))


def mute_volume(mute: bool) -> str:
    return _backend().mute_volume(bool(mute))


def set_brightness(level: int) -> str:
    return _backend().set_brightness(clamp_percent(level))


def lock_screen() -> str:
    return _backend().lock_screen()


def sleep_pc() -> str:
    return _backend().sleep_pc()


def shutdown_pc(delay_seconds: int = 30) -> str:
    return _backend().shutdown_pc(clamp_delay(delay_seconds))


def restart_pc(delay_seconds: int = 30) -> str:
    return _backend().restart_pc(clamp_delay(delay_seconds))


def cancel_shutdown() -> str:
    return _backend().cancel_shutdown()


def toggle_wifi(enabled: bool) -> str:
    return _backend().toggle_wifi(bool(enabled))
