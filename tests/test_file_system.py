import unittest

from tools.file_system import cap_dir_entries, list_dir, read_file, write_file


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

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            read_file("   ")
        with self.assertRaises(ValueError):
            write_file("", "x")

    def test_dir_listing_is_capped(self):
        rows = [{"name": str(i), "type": "file", "size": 1} for i in range(120)]
        capped = cap_dir_entries(rows, limit=80)
        self.assertEqual(len(capped), 81)
        self.assertEqual(capped[-1]["type"], "truncated")


if __name__ == "__main__":
    unittest.main()
