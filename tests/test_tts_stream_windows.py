import unittest

from tools.linux_pc_control import close_app, focus_window
from vision.camera_stream import clamp_fps
from voice.tts import speak_to_file


class TtsStreamWindowsTests(unittest.TestCase):
    def test_speak_rejects_empty_path(self):
        with self.assertRaises(ValueError):
            speak_to_file("hello", "  ")

    def test_fps_is_clamped(self):
        self.assertEqual(clamp_fps(0), 1.0)
        self.assertEqual(clamp_fps(99), 15.0)

    def test_window_actions_need_a_title(self):
        with self.assertRaises(ValueError):
            close_app("  ")
        with self.assertRaises(ValueError):
            focus_window("")


if __name__ == "__main__":
    unittest.main()
