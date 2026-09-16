import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from tools.worldclock import format_local_clock, get_time_in


class WorldClockTests(unittest.TestCase):
    def test_format_local_clock_is_portable(self):
        now = datetime(2026, 9, 16, 9, 5, tzinfo=ZoneInfo("Asia/Phnom_Penh"))
        payload = format_local_clock(now)
        self.assertEqual(payload["time"], "9:05 AM")
        self.assertEqual(payload["date"], "Wednesday, September 16")
        self.assertTrue(payload["utc_offset"])

    def test_get_time_in_without_location_uses_this_machine(self):
        payload = get_time_in(None)
        self.assertEqual(payload["location"], "this machine")
        self.assertIn("time", payload)
        self.assertIn("date", payload)


if __name__ == "__main__":
    unittest.main()
