import unittest

from tools.notes import remove_note
from tools.weather import _require_forecast_fields


class NotesWeatherTests(unittest.TestCase):
    def test_blank_remove_note_is_rejected(self):
        with self.assertRaises(ValueError):
            remove_note("  ")

    def test_incomplete_forecast_is_rejected(self):
        with self.assertRaises(RuntimeError):
            _require_forecast_fields({"current": {}, "daily": {}})


if __name__ == "__main__":
    unittest.main()
