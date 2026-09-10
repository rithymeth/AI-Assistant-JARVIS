import os
import tempfile
import unittest
from unittest.mock import patch

TEST_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DB_PATH", os.path.join(TEST_DIR.name, "test.db"))

from core.memory import store
from core.brain import agent

store.init_db()


class AgentTests(unittest.TestCase):
    def test_handle_message_builds_structured_context(self):
        captured = {}

        def fake_loop(session_id, user_message, messages, requester):
            captured["session_id"] = session_id
            captured["user_message"] = user_message
            captured["messages"] = messages
            captured["requester"] = requester
            return iter(())

        with (
            patch.object(agent, "add_message"),
            patch.object(agent, "get_history", return_value=[]),
            patch.object(agent, "list_preferences", return_value=[{"text": "Always be brief."}]),
            patch.object(agent, "search_memories", return_value=["User asked about backups before."]),
            patch.object(agent, "recall_facts", return_value=["Tool: web_search\nResult: Canberra is the capital."]),
            patch.object(agent, "_agent_loop", side_effect=fake_loop),
        ):
            list(agent.handle_message("session-1", "What do you remember?"))

        system_message = captured["messages"][0]
        self.assertEqual(system_message["role"], "system")
        self.assertIn("Standing preferences and corrections", system_message["content"])
        self.assertIn("Always be brief.", system_message["content"])
        self.assertIn("Background only — possibly-relevant snippets", system_message["content"])
        self.assertIn("User asked about backups before.", system_message["content"])
        self.assertIn("Things you've looked up and learned", system_message["content"])
        self.assertIn("Canberra is the capital", system_message["content"])

    def test_resume_after_approval_uses_persisted_action_and_removes_it(self):
        requester = agent.User(id=7, username="sam", role="admin")
        with (
            patch.object(agent, "execute_tool", return_value={"status": "ok"}),
            patch.object(agent, "_agent_loop", return_value=iter(([{"type": "done"}]))),
        ):
            action_id = "pending-1"
            agent.create_pending_action(
                action_id=action_id,
                session_id="session-2",
                user_message="write the file",
                messages=[{"role": "system", "content": "hi"}],
                tool_name="write_file",
                tool_args={"path": "note.txt", "content": "hello"},
                requester=requester,
                requires_admin=False,
            )

            events = list(agent.resume_after_approval(action_id, approved=True, approver=requester))

        self.assertEqual(events[0]["type"], "tool_result")
        self.assertIsNone(agent.load_pending_action(action_id))


if __name__ == "__main__":
    unittest.main()
