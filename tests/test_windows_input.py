import unittest

from tools.automation import click_at, type_text
from tools.windows_pc_control import close_app, focus_window, open_app


class WindowsInputTests(unittest.TestCase):
    def test_empty_app_and_window_names_rejected(self):
        with self.assertRaises(ValueError):
            open_app("  ")
        with self.assertRaises(ValueError):
            close_app("")
        with self.assertRaises(ValueError):
            focus_window("  ")

    def test_click_and_type_guards(self):
        with self.assertRaises(ValueError):
            click_at(-1, 10)
        with self.assertRaises(ValueError):
            type_text("")


if __name__ == "__main__":
    unittest.main()
