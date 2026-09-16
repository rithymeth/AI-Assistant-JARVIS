import unittest

from tools._platform import IS_WINDOWS
from tools.camera import CAP_ANY, CAP_DSHOW, camera_backend


class CameraTests(unittest.TestCase):
    def test_backend_matches_platform(self):
        backend = camera_backend()
        if IS_WINDOWS:
            self.assertEqual(backend, CAP_DSHOW)
        else:
            self.assertEqual(backend, CAP_ANY)


if __name__ == "__main__":
    unittest.main()
