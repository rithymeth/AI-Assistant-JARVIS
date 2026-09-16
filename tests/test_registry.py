import unittest

from tools.arguments import parse_tool_arguments
from tools.registry import execute_tool


class RegistryTests(unittest.TestCase):
    def test_parse_dict_arguments(self):
        self.assertEqual(parse_tool_arguments({"query": "ai"}), {"query": "ai"})

    def test_parse_json_string_arguments(self):
        self.assertEqual(parse_tool_arguments('{"query": "ai"}'), {"query": "ai"})

    def test_parse_empty_values(self):
        self.assertEqual(parse_tool_arguments(None), {})
        self.assertEqual(parse_tool_arguments(""), {})
        self.assertEqual(parse_tool_arguments("   "), {})

    def test_parse_rejects_non_object_json(self):
        with self.assertRaises(ValueError):
            parse_tool_arguments("[1, 2]")

    def test_execute_unknown_tool_raises_valueerror(self):
        with self.assertRaisesRegex(ValueError, "Unknown tool"):
            execute_tool("not_a_real_tool", {})


if __name__ == "__main__":
    unittest.main()
