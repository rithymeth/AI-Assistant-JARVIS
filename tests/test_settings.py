import unittest

from config.settings import env_int


class SettingsTests(unittest.TestCase):
    def test_env_int_falls_back_on_junk(self):
        self.assertEqual(env_int("__definitely_not_set__", 8000), 8000)

    def test_system_status_returns_core_fields(self):
        from tools.system_status import get_system_status

        status = get_system_status()
        self.assertIn("cpu_percent", status)
        self.assertIn("memory_percent", status)
        self.assertIn("disks", status)


if __name__ == "__main__":
    unittest.main()
