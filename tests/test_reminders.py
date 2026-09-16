import unittest
from unittest.mock import patch

from tools.reminders import cancel_reminder, set_reminder
from vision.camera_monitor import start_monitor
from core.memory import knowledge


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

    def test_cancel_reminder_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            cancel_reminder("  ")


class MonitorTests(unittest.TestCase):
    def test_interval_must_be_at_least_one_second(self):
        with self.assertRaises(ValueError):
            start_monitor(0)


class KnowledgeTests(unittest.TestCase):
    def test_empty_fact_is_noop(self):
        knowledge.remember_fact("  ", "   ")
        self.assertEqual(knowledge.recall_facts(""), [])


if __name__ == "__main__":
    unittest.main()
