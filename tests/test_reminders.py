import unittest
from unittest.mock import patch

from tools.reminders import set_reminder


class ReminderTests(unittest.TestCase):
    def test_set_reminder_uses_portable_clock_string(self):
        with patch("tools.reminders.create_reminder") as create:
            result = set_reminder("stretch", delay_minutes=0)
        self.assertTrue(result.startswith("Reminder set for "))
        self.assertIn("stretch", result)
        self.assertNotIn("%#I", result)
        create.assert_called_once()

    def test_set_reminder_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            set_reminder("  ", delay_minutes=5)


if __name__ == "__main__":
    unittest.main()
