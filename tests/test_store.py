import os
import tempfile
import unittest

TEST_DIR = tempfile.TemporaryDirectory()
os.environ["DB_PATH"] = os.path.join(TEST_DIR.name, "test.db")

from core.memory.db import connect


class StoreTests(unittest.TestCase):
    def test_connect_enables_wal_and_foreign_keys(self):
        with connect() as conn:
            conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            conn.execute(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))"
            )
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            with self.assertRaises(Exception):
                conn.execute("INSERT INTO child (parent_id) VALUES (999)")
        self.assertEqual(str(mode).lower(), "wal")
        self.assertEqual(int(fk), 1)


if __name__ == "__main__":
    unittest.main()
