import unittest

from tools.shell import run_command


class ShellTests(unittest.TestCase):
    def test_empty_command_rejected(self):
        with self.assertRaises(ValueError):
            run_command("   ")


if __name__ == "__main__":
    unittest.main()
