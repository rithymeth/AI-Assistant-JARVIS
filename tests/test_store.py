import os
import tempfile
import unittest

TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = os.path.join(TEST_DIR.name, "test.db")

from core.memory.db import connect
from core.memory import store

store.init_db()


class StoreTests(unittest.TestCase):
    def test_connect_enables_wal_and_foreign_keys(self):
        with connect() as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(str(mode).lower(), "wal")
        self.assertEqual(int(fk), 1)

    def test_empty_message_is_not_stored(self):
        store.add_message("s-empty", "user", "")
        store.add_message("s-empty", "user", "hello")
        history = store.get_history("s-empty")
        self.assertEqual([row["content"] for row in history], ["hello"])


if __name__ == "__main__":
    unittest.main()
