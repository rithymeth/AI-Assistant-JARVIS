import unittest

from tools.process_control import list_processes
from tools.system_control import clamp_delay, clamp_percent


class ProcessPowerTests(unittest.TestCase):
    def test_percent_and_delay_are_clamped(self):
        self.assertEqual(clamp_percent(150), 100)
        self.assertEqual(clamp_percent(-5), 0)
        self.assertEqual(clamp_delay(10**9), 24 * 60 * 60)
        with self.assertRaises(ValueError):
            clamp_percent("loud")

    def test_process_list_is_capped(self):
        rows = list_processes(limit=3)
        self.assertLessEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
