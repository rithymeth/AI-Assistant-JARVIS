import pyautogui

# Moving the mouse to a screen corner aborts an in-flight automation call —
# a physical kill-switch, kept on unconditionally.
pyautogui.FAILSAFE = True


def click_at(x: int, y: int) -> str:
    pyautogui.click(x, y)
    return f"Clicked at ({x}, {y})"


def type_text(text: str) -> str:
    pyautogui.typewrite(text, interval=0.02)
    return f"Typed {len(text)} character(s)"


def press_key(key: str) -> str:
    pyautogui.press(key)
    return f"Pressed '{key}'"
