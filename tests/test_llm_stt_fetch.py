import unittest

from core.brain.llm import describe_image
from tools.web_fetch import fetch_page
from voice.stt import transcribe


class LlmSttFetchTests(unittest.TestCase):
    def test_empty_image_path_rejected(self):
        with self.assertRaises(ValueError):
            describe_image("  ", "what is this")

    def test_missing_audio_rejected(self):
        with self.assertRaises(ValueError):
            transcribe("  ")
        with self.assertRaises(ValueError):
            transcribe("/tmp/javi-missing-audio.wav")

    def test_non_http_url_rejected(self):
        with self.assertRaises(ValueError):
            fetch_page("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
