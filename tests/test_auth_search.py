import unittest

from core.auth.users import generate_code, hash_new_code, verify_code
from tools.web_search import clamp_max_results, web_search


class AuthSearchTests(unittest.TestCase):
    def test_empty_code_rejected(self):
        with self.assertRaises(ValueError):
            hash_new_code("  ")
        self.assertFalse(verify_code("", "salt", "hash"))

    def test_generated_code_roundtrips(self):
        code = generate_code()
        digest, salt = hash_new_code(code)
        self.assertTrue(verify_code(code, salt, digest))
        self.assertTrue(verify_code(code.lower(), salt, digest))
        self.assertFalse(verify_code(code + "x", salt, digest))

    def test_search_result_count_is_clamped(self):
        self.assertEqual(clamp_max_results(0), 1)
        self.assertEqual(clamp_max_results(99), 10)
        self.assertEqual(clamp_max_results("nope"), 5)

    def test_empty_search_query_rejected(self):
        with self.assertRaises(ValueError):
            web_search("  ")


if __name__ == "__main__":
    unittest.main()
