import unittest

from core.auth.face import NoFaceDetected, embed_face, is_match
from core.auth.face_sessions import create_session, verify_session


class FaceTests(unittest.TestCase):
    def test_empty_image_path_rejected(self):
        with self.assertRaises(NoFaceDetected):
            embed_face("  ")

    def test_no_enrolled_faces_is_not_a_match(self):
        self.assertFalse(is_match([1.0, 0.0], []))

    def test_session_roundtrip_and_wrong_user(self):
        token = create_session(7)
        self.assertTrue(verify_session(token, 7))
        self.assertFalse(verify_session(token, 8))
        self.assertFalse(verify_session("", 7))


if __name__ == "__main__":
    unittest.main()
