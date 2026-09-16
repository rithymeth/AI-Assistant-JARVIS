import unittest

from tools._geo import format_place_name, geocode


class GeoTests(unittest.TestCase):
    def test_empty_location_rejected(self):
        with self.assertRaises(ValueError):
            geocode("  ")

    def test_place_name_falls_back(self):
        self.assertEqual(format_place_name(None), "unknown place")
        self.assertEqual(format_place_name({}), "unknown place")
        self.assertEqual(format_place_name({"name": "Phnom Penh", "country": "Cambodia"}), "Phnom Penh, Cambodia")


if __name__ == "__main__":
    unittest.main()
