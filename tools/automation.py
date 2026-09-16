"""Desktop input automation. pyautogui is imported lazily so headless tests
can load the package without a display."""


def _gui():
    import pyautogui

    pyautogui.FAILSAFE = True
    return pyautogui


def click_at(x: int, y: int) -> str:
    _gui().click(int(x), int(y))
    return f"Clicked at ({int(x)}, {int(y)})"


def type_text(text: str) -> str:
    if text is None:
        raise ValueError("Nothing to type")
    _gui().typewrite(str(text), interval=0.02)
    return f"Typed {len(str(text))} character(s)"


def press_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise ValueError("Key name is empty")
    _gui().press(key)
    return f"Pressed '{key}'"
