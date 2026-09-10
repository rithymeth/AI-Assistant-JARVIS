import os
import tempfile
import time
import unittest
from unittest.mock import patch

TEST_DIR = tempfile.TemporaryDirectory()
os.environ.setdefault("DB_PATH", os.path.join(TEST_DIR.name, "test.db"))

from core.memory import knowledge, vector_store


class FakeEmbedder:
    def encode(self, text):
        return [float(len(text))]


class FakeCollection:
    def __init__(self, query_result=None):
        self.query_result = query_result or {}
        self.add_calls = []
        self.upsert_calls = []

    def count(self):
        return 4

    def add(self, **kwargs):
        self.add_calls.append(kwargs)

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def query(self, **kwargs):
        self.last_query = kwargs
        return self.query_result


class MemoryTests(unittest.TestCase):
    def test_search_memories_reranks_recent_results_and_dedupes(self):
        now = time.time()
        collection = FakeCollection(
            {
                "documents": [["same note", "same note  ", "recent detail", "older detail"]],
                "metadatas": [[
                    {"created_at_ts": now - 120},
                    {"created_at_ts": now - 60},
                    {"created_at_ts": now - 60},
                    {"created_at_ts": now - 90 * 86400},
                ]],
                "distances": [[0.01, 0.02, 0.08, 0.07]],
            }
        )
        with patch.object(vector_store, "_collection", return_value=collection), patch.object(
            vector_store, "get_embedder", return_value=FakeEmbedder()
        ):
            results = vector_store.search_memories("session-1", "query", k=3)

        self.assertEqual(results[0], "same note")
        self.assertIn("recent detail", results)
        self.assertNotIn("same note  ", results)
        self.assertEqual(collection.last_query["where"]["memory_type"], vector_store.MEMORY_TYPE_CONVERSATION)

    def test_remember_fact_sets_fact_type_metadata(self):
        collection = FakeCollection({"ids": [[]], "distances": [[]]})
        with patch.object(knowledge, "_collection", return_value=collection), patch.object(
            knowledge, "get_embedder", return_value=FakeEmbedder()
        ):
            knowledge.remember_fact("lookup:key", "A fact", fact_type="screen_observation")

        self.assertEqual(collection.upsert_calls[0]["metadatas"][0]["fact_type"], "screen_observation")

    def test_recall_facts_dedupes_and_filters_by_fact_type(self):
        now = time.time()
        collection = FakeCollection(
            {
                "documents": [["same fact", "same fact", "fresh fact", "stale fact"]],
                "metadatas": [[
                    {"learned_at_ts": now - 600, "fact_type": "tool_lookup"},
                    {"learned_at_ts": now - 60, "fact_type": "tool_lookup"},
                    {"learned_at_ts": now - 60, "fact_type": "tool_lookup"},
                    {"learned_at_ts": now - 60 * 86400, "fact_type": "tool_lookup"},
                ]],
                "distances": [[0.01, 0.03, 0.07, 0.02]],
            }
        )
        with patch.object(knowledge, "_collection", return_value=collection), patch.object(
            knowledge, "get_embedder", return_value=FakeEmbedder()
        ):
            results = knowledge.recall_facts("query", k=3)

        self.assertEqual(results[0], "same fact")
        self.assertIn("fresh fact", results)
        self.assertEqual(collection.last_query["where"]["fact_type"], knowledge.FACT_TYPE_TOOL_LOOKUP)


if __name__ == "__main__":
    unittest.main()
