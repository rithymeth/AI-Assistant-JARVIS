import sys

IS_WINDOWS = sys.platform.startswith("win")


def require_windows_capability(capability: str) -> None:
    if not IS_WINDOWS:
        raise RuntimeError(f"{capability} is only available on Windows")

