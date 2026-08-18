import os

from core.brain.llm import describe_image
from tools.camera import capture_camera_frame

CAMERA_PROMPT = (
    "This is a live photo from the user's webcam. Describe what/who is "
    "visible, the setting, and anything notable. Be concise — 2-4 sentences."
)


def describe_camera() -> str:
    path = capture_camera_frame()
    try:
        return describe_image(path, CAMERA_PROMPT)
    finally:
        os.remove(path)
