import unittest

from tools.linux_pc_control import screenshot_cli_candidates
from tools.preferences import forget_preference, remember_preference


class LinuxPcTests(unittest.TestCase):
    def test_screenshot_cli_includes_common_tools(self):
        cmds = screenshot_cli_candidates("/tmp/screen.png")
        names = [row[0] for row in cmds]
        self.assertIn("grim", names)
        self.assertIn("screencapture", names)


class PreferenceTests(unittest.TestCase):
    def test_empty_preference_rejected(self):
        with self.assertRaises(ValueError):
            remember_preference("   ")
        with self.assertRaises(ValueError):
            forget_preference("  ")


if __name__ == "__main__":
    unittest.main()
