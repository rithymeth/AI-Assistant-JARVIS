import os

from core.brain.llm import describe_image
from tools.pc_control import take_screenshot

SCREEN_PROMPT = (
    "This is a screenshot of the user's computer screen. Describe what app or "
    "window appears focused, what the user seems to be doing, and summarize any "
    "clearly readable text. Be concise — 2-4 sentences."
)


def describe_screen() -> str:
    path = take_screenshot()
    try:
        return describe_image(path, SCREEN_PROMPT)
    finally:
        os.remove(path)
