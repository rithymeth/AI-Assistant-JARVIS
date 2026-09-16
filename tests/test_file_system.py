import unittest

from tools.file_system import list_dir, read_file, write_file


class FileSystemTests(unittest.TestCase):
    def test_sandbox_blocks_parent_escape(self):
        with self.assertRaises(ValueError):
            read_file("../README.md")
        with self.assertRaises(ValueError):
            write_file("../escape.txt", "nope")
        with self.assertRaises(ValueError):
            list_dir("..")

    def test_write_and_read_roundtrip(self):
        write_file("upgrade_probe.txt", "ok")
        self.assertEqual(read_file("upgrade_probe.txt"), "ok")


if __name__ == "__main__":
    unittest.main()
