import unittest

from tools.web_fetch import fetch_page


class WebFetchTests(unittest.TestCase):
    def test_rejects_non_http_urls(self):
        with self.assertRaises(ValueError):
            fetch_page("file:///etc/passwd")
        with self.assertRaises(ValueError):
            fetch_page("not-a-url")


if __name__ == "__main__":
    unittest.main()
