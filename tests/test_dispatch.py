import unittest

from core.auth.users import LOOPBACK_USER
from core.brain.pending_actions import create_pending_action, load_pending_action
from tools.dispatch import execute_tool


class DispatchTests(unittest.TestCase):
    def test_unknown_tool_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            execute_tool("not_a_real_tool", {})
        self.assertIn("Unknown tool", str(ctx.exception))

    def test_empty_action_id_rejected(self):
        with self.assertRaises(ValueError):
            create_pending_action(
                action_id="  ",
                session_id="s",
                user_message="x",
                messages=[],
                tool_name="write_file",
                tool_args={},
                requester=LOOPBACK_USER,
                requires_admin=False,
            )
        self.assertIsNone(load_pending_action(""))


if __name__ == "__main__":
    unittest.main()
