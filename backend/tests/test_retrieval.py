from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from src.systems.AgentSystem.AgentPipeline.AgentPipeline import AgentPipeline
from src.systems.AgentSystem.Orchestrator.Orchestrator import Orchestrator
from src.systems.AgentSystem.ResponseGenerator.ResponseGenerator import ResponseGenerator
from src.utils.AgentSystem.ResponseGenerator.retrieve_chunks import retrieve_chunks
from src.utils.general.GeminiApiCall import GeminiClient
from src.utils.general.sources import collecting_sources


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "chunks.sqlite3"
        self.client = GeminiClient(api_key="test-key", embedding_model="models/test-embedding")
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executescript("""
                CREATE TABLE build_info (
                    id INTEGER PRIMARY KEY, embedding_model TEXT, embedding_dimensions INTEGER
                );
                INSERT INTO build_info VALUES (1, 'test-embedding', 2);
                CREATE TABLE chunks (
                    id TEXT PRIMARY KEY, text TEXT, stop TEXT, type TEXT,
                    embedding TEXT, embedding_model TEXT, embedding_dimensions INTEGER,
                    source TEXT, page INTEGER
                );
            """)
        embedding_patch = patch.object(self.client, "embed", return_value=[[1.0, 0.0]])
        self.embed = embedding_patch.start()
        self.addCleanup(embedding_patch.stop)

    def add_chunk(
        self, identifier: str, vector: object, *,
        stop: str = "Pantheon", chunk_type: str = "historic",
        model: str = "test-embedding", dimensions: int = 2,
        source: str = "Pantheon/historic/guide.pdf", page: int = 1,
    ) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (identifier, f"Text for {identifier}", stop, chunk_type,
                 json.dumps(vector), model, dimensions, source, page),
            )

    def retrieve(self, stop="Pantheon", category="historic", query="Explain the dome."):
        return retrieve_chunks(
            self.client, stop, category, user_query=query, database_path=self.path,
        )

    def test_top_two_use_cosine_similarity_after_both_metadata_filters(self) -> None:
        self.add_chunk("third", [0.5, 0.5])
        self.add_chunk("second", [10.0, 1.0])
        self.add_chunk("first", [1.0, 0.0])
        self.add_chunk("large-but-orthogonal", [0.0, 9999.0])
        self.add_chunk("wrong-stop", [1.0, 0.0], stop="Roman_Forum")
        self.add_chunk("wrong-type", [1.0, 0.0], chunk_type="restaurants")
        self.assertEqual(self.retrieve(), ["Text for first", "Text for second"])
        self.embed.assert_called_once_with(
            ["Stop: Pantheon\nType: historic\n\nExplain the dome."],
            task_type="RETRIEVAL_QUERY",
        )

    def test_restaurant_category_maps_to_plural_database_type(self) -> None:
        self.add_chunk("history", [1.0, 0.0])
        self.add_chunk("food", [0.5, 0.5], chunk_type="restaurants")
        self.assertEqual(self.retrieve(category="restaurant"), ["Text for food"])
        self.assertIn("Type: restaurants", self.embed.call_args.args[0][0])

    def test_references_use_only_selected_chunks_and_their_actual_pages(self) -> None:
        self.add_chunk("third", [0.0, 1.0], source="unused.pdf", page=99)
        self.add_chunk("first", [1.0, 0.0], page=7)
        self.add_chunk("second", [1.0, 0.5], source="other.pdf", page=3)
        with collecting_sources() as sources:
            self.assertEqual(self.retrieve(), ["Text for first", "Text for second"])
        self.assertEqual([source.model_dump() for source in sources], [
            {"source": "Pantheon/historic/guide.pdf", "page": 7},
            {"source": "other.pdf", "page": 3},
        ])

    def test_references_deduplicate_pages_and_do_not_leak_between_requests(self) -> None:
        self.add_chunk("first", [1.0, 0.0], page=4)
        self.add_chunk("second", [1.0, 0.5], page=4)
        with collecting_sources() as sources:
            self.retrieve()
            self.retrieve()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].page, 4)
        with collecting_sources() as next_sources:
            self.assertEqual(next_sources, [])
        self.retrieve()
        self.assertEqual(len(sources), 1)

    def test_no_query_embeds_a_category_specific_introduction(self) -> None:
        self.add_chunk("history", [1.0, 0.0])
        self.add_chunk("food", [1.0, 0.0], chunk_type="restaurants")
        for category, expected in (
            ("historic", "historical introduction"),
            ("restaurant", "dining options"),
        ):
            with self.subTest(category=category):
                self.retrieve(category=category, query=None)
                self.assertIn(expected, self.embed.call_args.args[0][0])

    def test_ties_are_deterministic_and_negative_scores_are_ranked(self) -> None:
        self.add_chunk("z", [-1.0, 0.0])
        self.add_chunk("b", [0.0, 1.0])
        self.add_chunk("a", [0.0, -1.0])
        self.assertEqual(self.retrieve(), ["Text for a", "Text for b"])

    def test_missing_stop_does_not_embed_or_fall_back_to_other_metadata(self) -> None:
        self.add_chunk("other", [1.0, 0.0], stop="Roman_Forum")
        with self.assertRaisesRegex(ValueError, "No RAG chunks"):
            self.retrieve()
        self.embed.assert_not_called()

    def test_stop_filter_does_not_interpret_sql(self) -> None:
        self.add_chunk("history", [1.0, 0.0])
        with self.assertRaisesRegex(ValueError, "No RAG chunks"):
            self.retrieve(stop="Pantheon' OR 1=1 --")
        self.embed.assert_not_called()

    def test_missing_database_is_not_created(self) -> None:
        missing = self.path.parent / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            retrieve_chunks(
                self.client, "Pantheon", "historic", user_query=None, database_path=missing,
            )
        self.assertFalse(missing.exists())
        self.embed.assert_not_called()

    def test_embedding_model_mismatch_fails_before_api_call(self) -> None:
        self.client.embedding_model = "different-model"
        with self.assertRaisesRegex(RuntimeError, "model mismatch"):
            self.retrieve()
        self.embed.assert_not_called()

    def test_missing_build_metadata_is_explicit(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("DELETE FROM build_info")
        with self.assertRaisesRegex(RuntimeError, "no build metadata"):
            self.retrieve()
        self.embed.assert_not_called()

    def test_invalid_query_embeddings_fail(self) -> None:
        self.add_chunk("history", [1.0, 0.0])
        for vectors in ([], [[1.0]], [[0.0, 0.0]], [[float("nan"), 1.0]]):
            with self.subTest(vectors=vectors):
                self.embed.return_value = vectors
                with self.assertRaises(RuntimeError):
                    self.retrieve()

    def test_corrupt_document_vectors_fail_instead_of_being_skipped(self) -> None:
        self.add_chunk("corrupt", [1.0, 0.0])
        for vector in ([1.0], [0.0, 0.0], [True, 1.0], ["1", 1.0], [float("inf"), 0.0], {}):
            with self.subTest(vector=vector):
                with closing(sqlite3.connect(self.path)) as connection, connection:
                    connection.execute("UPDATE chunks SET embedding = ?", (json.dumps(vector),))
                with self.assertRaises(RuntimeError):
                    self.retrieve()

    def test_invalid_json_fails_explicitly(self) -> None:
        self.add_chunk("corrupt", [1.0, 0.0])
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE chunks SET embedding = 'invalid-json'")
        with self.assertRaises(json.JSONDecodeError):
            self.retrieve()

    def test_incompatible_chunk_metadata_fails(self) -> None:
        self.add_chunk("corrupt", [1.0, 0.0], model="other-model")
        with self.assertRaisesRegex(RuntimeError, "Incompatible embedding metadata"):
            self.retrieve()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "UPDATE chunks SET embedding_model = 'test-embedding', embedding_dimensions = 3"
            )
        with self.assertRaisesRegex(RuntimeError, "Incompatible embedding metadata"):
            self.retrieve()

    def test_empty_chunk_text_fails(self) -> None:
        self.add_chunk("empty", [1.0, 0.0])
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE chunks SET text = ' '")
        with self.assertRaisesRegex(RuntimeError, "Empty text"):
            self.retrieve()

    def test_embedding_api_errors_propagate(self) -> None:
        self.add_chunk("history", [1.0, 0.0])
        self.embed.side_effect = HTTPError("https://example.com", 429, "Quota", {}, None)
        with self.assertRaises(HTTPError):
            self.retrieve()

    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_pipeline_embeds_query_then_generates_using_exactly_two_matches(self, urlopen) -> None:
        self.add_chunk("first", [1.0, 0.0])
        self.add_chunk("second", [1.0, 0.1])
        self.add_chunk("third", [0.0, 1.0])
        self.add_chunk("food", [1.0, 0.0], chunk_type="restaurants")
        self.add_chunk("food-second", [1.0, 0.1], chunk_type="restaurants")
        client = GeminiClient(api_key="test-key", embedding_model="test-embedding")
        pipeline = AgentPipeline(
            orchestrator=Orchestrator(client=client),
            response_generator=ResponseGenerator(client=client, database_path=self.path),
        )
        for category, matches in (
            ("historic", ["Text for first", "Text for second"]),
            ("restaurant", ["Text for food", "Text for food-second"]),
        ):
            for routed in (False, True):
                with self.subTest(category=category, routed=routed):
                    urlopen.reset_mock()
                    texts = ([category] if routed else []) + ["Una respuesta fundamentada."]
                    responses = [
                        BytesIO(json.dumps({
                            "candidates": [{
                                "finishReason": "STOP",
                                "content": {"parts": [{"text": text}]},
                            }],
                        }).encode())
                        for text in texts
                    ]
                    responses.insert(
                        -1, BytesIO(json.dumps({"embeddings": [{"values": [1.0, 0.0]}]}).encode())
                    )
                    urlopen.side_effect = responses
                    kwargs = {"user_query": "Tell me more."} if routed else {"param": category}
                    self.assertEqual(
                        pipeline.run("Pantheon", language="es", **kwargs),
                        "Una respuesta fundamentada.",
                    )
                    self.assertEqual(urlopen.call_count, 3 if routed else 2)
                    embedding_request = urlopen.call_args_list[-2].args[0]
                    generation_request = urlopen.call_args_list[-1].args[0]
                    self.assertIn("test-embedding:batchEmbedContents", embedding_request.full_url)
                    embedding = json.loads(embedding_request.data)["requests"][0]
                    self.assertEqual(embedding["taskType"], "RETRIEVAL_QUERY")
                    if routed:
                        self.assertIn("Tell me more.", embedding["content"]["parts"][0]["text"])
                    payload = json.loads(generation_request.data)
                    data = json.loads(payload["contents"][0]["parts"][0]["text"])
                    self.assertEqual(data["context"], matches)
                    self.assertEqual(data["language"], "es")
                    self.assertIn(
                        f"You are the {category} guide",
                        payload["systemInstruction"]["parts"][0]["text"],
                    )


if __name__ == "__main__":
    unittest.main()
