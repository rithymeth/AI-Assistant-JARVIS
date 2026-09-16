import unittest

from vision.ocr import extract_text


class OcrTests(unittest.TestCase):
    def test_empty_path_rejected_before_reader(self):
        with self.assertRaises(ValueError):
            extract_text("  ")


if __name__ == "__main__":
    unittest.main()
