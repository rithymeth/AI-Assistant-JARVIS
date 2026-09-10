from tools._platform import require_windows_capability


def _backend():
    require_windows_capability("Desktop control")
    from tools import windows_pc_control

    return windows_pc_control


def open_app(name: str) -> str:
    return _backend().open_app(name)


def close_app(title_substring: str) -> str:
    return _backend().close_app(title_substring)


def focus_window(title_substring: str) -> str:
    return _backend().focus_window(title_substring)


def list_windows() -> list[str]:
    return _backend().list_windows()


def take_screenshot() -> str:
    return _backend().take_screenshot()
