import unittest

from tools.linux_system_control import brightness_cli_candidates, lock_cli_candidates
from api.validate import require_text
from fastapi import HTTPException


class LinuxSystemTests(unittest.TestCase):
    def test_brightness_cli_includes_common_tools(self):
        names = [row[0] for row in brightness_cli_candidates(40)]
        self.assertIn("brightnessctl", names)
        self.assertIn("xbacklight", names)

    def test_lock_cli_includes_common_tools(self):
        names = [row[0] for row in lock_cli_candidates()]
        self.assertIn("loginctl", names)
        self.assertIn("xdg-screensaver", names)


class ValidateTests(unittest.TestCase):
    def test_empty_chat_text_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_text("   ", "message")
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
