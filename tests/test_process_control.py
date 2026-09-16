import unittest

from tools.process_control import kill_process


class ProcessControlTests(unittest.TestCase):
    def test_empty_target_rejected(self):
        with self.assertRaises(ValueError):
            kill_process("  ")


if __name__ == "__main__":
    unittest.main()
