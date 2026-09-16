"""Desktop input automation. pyautogui is imported lazily so headless tests
can load the package without a display."""


def _gui():
    import pyautogui

    pyautogui.FAILSAFE = True
    return pyautogui


def click_at(x: int, y: int) -> str:
    try:
        x = int(x)
        y = int(y)
    except (TypeError, ValueError) as exc:
        raise ValueError("Click coordinates must be integers") from exc
    if x < 0 or y < 0:
        raise ValueError("Click coordinates must be on-screen")
    _gui().click(x, y)
    return f"Clicked at ({x}, {y})"


def type_text(text: str) -> str:
    if text is None or not str(text):
        raise ValueError("Nothing to type")
    _gui().typewrite(str(text), interval=0.02)
    return f"Typed {len(str(text))} character(s)"


def press_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise ValueError("Key name is empty")
    _gui().press(key)
    return f"Pressed '{key}'"
