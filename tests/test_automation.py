import unittest

from tools.automation import press_key


class AutomationTests(unittest.TestCase):
    def test_empty_key_rejected_before_gui(self):
        with self.assertRaises(ValueError):
            press_key("  ")


if __name__ == "__main__":
    unittest.main()
