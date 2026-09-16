import unittest

from vision.detection import detect_objects
from vision.tracking import track_frame
from core.memory.vector_store import add_memory, search_memories


class DetectionTests(unittest.TestCase):
    def test_empty_image_path_rejected(self):
        with self.assertRaises(ValueError):
            detect_objects("  ")

    def test_missing_frame_rejected(self):
        with self.assertRaises(ValueError):
            track_frame(None)


class VectorStoreTests(unittest.TestCase):
    def test_empty_memory_is_noop(self):
        add_memory("s", "   ")
        self.assertEqual(search_memories("s", ""), [])


if __name__ == "__main__":
    unittest.main()
