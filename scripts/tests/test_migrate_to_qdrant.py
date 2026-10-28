from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import UUID

from qdrant_client import QdrantClient, models

from scripts.migrate_to_qdrant import load_snapshot, migrate


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "chunks.sqlite3"
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript("""
                CREATE TABLE build_info (
                    id INTEGER, schema_version INTEGER, embedding_model TEXT,
                    embedding_dimensions INTEGER, chunk_count INTEGER
                );
                INSERT INTO build_info VALUES (1, 1, 'gemini-embedding-001', 3, 2);
                CREATE TABLE chunks (
                    id TEXT, text TEXT, stop TEXT, type TEXT, source TEXT,
                    page INTEGER, chunk_index INTEGER, token_count INTEGER,
                    embedding TEXT, embedding_model TEXT, embedding_dimensions INTEGER
                );
            """)
            for index, category in enumerate(("historic", "restaurants")):
                connection.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(index), "Roman history", "Torre_Argentina", category,
                        f"Torre_Argentina/{category}/doc.pdf", 1, 0, 3,
                        json.dumps([1.0, 2.0, 3.0]), "gemini-embedding-001", 3,
                    ),
                )
        self.client = QdrantClient(":memory:")
        self.addCleanup(self.client.close)

    def update_source(self, sql: str) -> None:
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(sql)

    def test_migration_metadata_vectors_filters_and_repeat(self) -> None:
        original = self.database.read_bytes()
        snapshot = load_snapshot(self.database)
        self.assertEqual(migrate(self.client, snapshot, batch_size=1), 2)
        first_ids = [str(point.id) for point in snapshot.points]
        for point_id in first_ids:
            self.assertEqual(UUID(point_id).version, 5)
        self.assertEqual(migrate(self.client, load_snapshot(self.database)), 2)
        records, _ = self.client.scroll("historic_guide", with_vectors=True)
        self.assertEqual({str(record.id) for record in records}, set(first_ids))
        for record in records:
            self.assertEqual(record.payload["stop_id"], "Torre_Argentina")
            self.assertEqual(record.payload["stop"], "Torre_Argentina")
            self.assertIn(record.payload["type"], ("historic", "restaurants"))
            self.assertEqual(record.payload["embedding_model"], snapshot.model)
            self.assertEqual(record.payload["text"], "Roman history")
            self.assertEqual(record.payload["page"], 1)
        result = self.client.query_points(
            "historic_guide", query=[1.0, 2.0, 3.0],
            query_filter=models.Filter(must=[
                models.FieldCondition(key="stop_id", match=models.MatchValue(value="Torre_Argentina")),
                models.FieldCondition(key="type", match=models.MatchValue(value="restaurants")),
            ]),
        )
        self.assertEqual(len(result.points), 1)
        self.assertAlmostEqual(result.points[0].score, 1.0, places=5)
        self.assertEqual(self.database.read_bytes(), original)

    def test_bad_source_is_rejected(self) -> None:
        mutations = (
            "UPDATE chunks SET embedding = '[0, 0, 0]'",
            "UPDATE chunks SET embedding = '[1, 2]'",
            "UPDATE chunks SET embedding = '[true, 2, 3]'",
            "UPDATE chunks SET embedding = '[NaN, 2, 3]'",
            "UPDATE chunks SET embedding_model = 'other'",
            "UPDATE chunks SET embedding_dimensions = 4",
            "UPDATE chunks SET stop = ''",
            "UPDATE chunks SET type = ''",
            "UPDATE chunks SET text = ''",
            "UPDATE chunks SET page = 0",
            "UPDATE chunks SET id = 'duplicate'",
            "UPDATE build_info SET chunk_count = 3",
            "DELETE FROM chunks",
        )
        original = self.database.read_bytes()
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.database.write_bytes(original)
                self.update_source(mutation)
                with self.assertRaises(ValueError):
                    load_snapshot(self.database)
        self.assertFalse(self.client.collection_exists("historic_guide"))

    def test_missing_database_does_not_create_file(self) -> None:
        missing = self.database.parent / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            load_snapshot(missing)
        self.assertFalse(missing.exists())

    def test_incompatible_collection_is_untouched(self) -> None:
        self.client.create_collection(
            "historic_guide", vectors_config=models.VectorParams(size=2, distance=models.Distance.DOT),
        )
        with self.assertRaisesRegex(ValueError, "matching dimensions"):
            migrate(self.client, load_snapshot(self.database))
        self.assertEqual(self.client.count("historic_guide").count, 0)

    def test_unrelated_points_are_untouched(self) -> None:
        self.client.create_collection(
            "historic_guide", vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
        )
        self.client.upsert(
            "historic_guide",
            [models.PointStruct(id=42, vector=[1.0, 0.0, 0.0], payload={"app": "basic-rag"})],
        )
        with self.assertRaisesRegex(ValueError, "Nothing was written"):
            migrate(self.client, load_snapshot(self.database))
        self.assertEqual(self.client.count("historic_guide").count, 1)
        self.assertEqual(self.client.retrieve("historic_guide", [42])[0].payload, {"app": "basic-rag"})

    def test_partial_upload_can_be_resumed(self) -> None:
        snapshot = load_snapshot(self.database)
        self.client.create_collection(
            "historic_guide", vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
        )
        self.client.upsert("historic_guide", snapshot.points[:1])
        self.assertEqual(migrate(self.client, snapshot), 2)

    def test_readback_failure_is_reported(self) -> None:
        with patch.object(self.client, "retrieve", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "read-back"):
                migrate(self.client, load_snapshot(self.database))

    def test_invalid_batch_size_does_not_create_collection(self) -> None:
        with self.assertRaises(ValueError):
            migrate(self.client, load_snapshot(self.database), batch_size=0)
        self.assertFalse(self.client.collection_exists("historic_guide"))


if __name__ == "__main__":
    unittest.main()
