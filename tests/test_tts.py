import unittest

from voice.tts import speak_to_file


class TtsTests(unittest.TestCase):
    def test_empty_text_rejected_before_engine(self):
        with self.assertRaises(ValueError):
            speak_to_file("   ", "/tmp/unused.wav")


if __name__ == "__main__":
    unittest.main()
