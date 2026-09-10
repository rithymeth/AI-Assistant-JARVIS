from tools._platform import require_windows_capability


def _backend():
    require_windows_capability("System control")
    from tools import windows_system_control

    return windows_system_control


def set_volume(level: int) -> str:
    return _backend().set_volume(level)


def mute_volume(mute: bool) -> str:
    return _backend().mute_volume(mute)


def set_brightness(level: int) -> str:
    return _backend().set_brightness(level)


def lock_screen() -> str:
    return _backend().lock_screen()


def sleep_pc() -> str:
    return _backend().sleep_pc()


def shutdown_pc(delay_seconds: int = 30) -> str:
    return _backend().shutdown_pc(delay_seconds)


def restart_pc(delay_seconds: int = 30) -> str:
    return _backend().restart_pc(delay_seconds)


def cancel_shutdown() -> str:
    return _backend().cancel_shutdown()


def toggle_wifi(enabled: bool) -> str:
    return _backend().toggle_wifi(enabled)
