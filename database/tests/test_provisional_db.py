from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from database.scripts.chunk_gen import ChunkGen
from database.scripts.provisional_db_gen import build_database
from src.utils.general.GeminiApiCall import GeminiClient


class ChunkGenTests(unittest.TestCase):
    def test_token_limit_unicode_special_tokens_and_coverage(self) -> None:
        chunker = ChunkGen(max_tokens=40, overlap_tokens=8)
        text = "First paragraph about Rome.\n\n" + (
            "Caf\u00e9 history. The Pantheon has a dome! <|endoftext|> " * 25
        ) + "z" * 500
        chunks = chunker.split_text(text)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(0 < chunker.count_tokens(chunk) <= 40 for chunk in chunks))
        self.assertTrue(all("\ufffd" not in chunk for chunk in chunks))
        self.assertTrue(chunks[0].startswith("First paragraph"))
        self.assertTrue(chunks[-1].endswith("z" * 20))

    def test_overlap_and_no_overlap(self) -> None:
        text = " ".join(f"word{index}" for index in range(100))
        for overlap in (0, 8):
            with self.subTest(overlap=overlap):
                chunker = ChunkGen(40, overlap)
                chunks = chunker.split_text(text)
                recovered: list[str] = []
                for chunk in chunks:
                    words = chunk.split()
                    repeated = 0
                    for size in range(1, min(len(recovered), len(words)) + 1):
                        if recovered[-size:] == words[:size]:
                            repeated = size
                    if overlap and recovered:
                        self.assertGreater(repeated, 0)
                    if not overlap:
                        self.assertEqual(repeated, 0)
                    recovered.extend(words[repeated:])
                self.assertEqual(recovered, text.split())

    def test_bad_settings_and_empty_text(self) -> None:
        for settings in ((0, 0), (10, -1), (10, 10)):
            with self.assertRaises(ValueError):
                ChunkGen(*settings)
        with self.assertRaises(ValueError):
            ChunkGen().split_text(" \n ")

    @patch("database.scripts.chunk_gen.PdfReader")
    def test_metadata_headers_pages_and_empty_page_errors(self, reader: Mock) -> None:
        reader.return_value = SimpleNamespace(
            is_encrypted=False,
            pages=[
                SimpleNamespace(extract_text=lambda index=index, **kwargs: (
                    f"Repeated header\nSecond header\nUnique content {index}.\n"
                    f"Repeated footer\nPage {index} of 3"
                ))
                for index in range(1, 4)
            ],
        )
        chunker = ChunkGen()
        chunks = chunker.generate(
            ROOT / "database/docs/Pantheon/historic/example.pdf",
            docs_root=ROOT / "database/docs",
        )
        self.assertEqual([chunk.page for chunk in chunks], [1, 2, 3])
        self.assertEqual([chunk.chunk_index for chunk in chunks], [0, 1, 2])
        self.assertTrue(all(chunk.stop == "Pantheon" and chunk.type == "historic" for chunk in chunks))
        self.assertTrue(all(chunk.source == "Pantheon/historic/example.pdf" for chunk in chunks))
        self.assertTrue(all(chunk.text.startswith("Unique content") for chunk in chunks))
        reader.return_value.pages = [SimpleNamespace(extract_text=lambda **kwargs: "")]
        with self.assertRaisesRegex(ValueError, "OCR"):
            chunker.generate(
                ROOT / "database/docs/Pantheon/historic/example.pdf",
                docs_root=ROOT / "database/docs",
            )

    def test_real_corpus(self) -> None:
        chunker = ChunkGen()
        pdfs = sorted((ROOT / "database/docs").rglob("*.pdf"))
        self.assertTrue(pdfs)
        for pdf in pdfs:
            with self.subTest(pdf=pdf):
                chunks = chunker.generate(pdf, docs_root=ROOT / "database/docs")
                self.assertTrue(chunks)
                self.assertEqual({chunk.page for chunk in chunks}, set(range(1, 11)))
                self.assertTrue(all(0 < chunk.token_count <= 400 for chunk in chunks))
                self.assertTrue(all("Rome Archaeological & Culinary Corpus" not in chunk.text for chunk in chunks))


class EmbeddingTests(unittest.TestCase):
    @patch("src.utils.general.GeminiApiCall.urlopen")
    def test_model_config_payload_query_and_order(self, urlopen: Mock) -> None:
        with patch("src.utils.general.GeminiApiCall._configuration_value", return_value="models/test-embedding"):
            client = GeminiClient(api_key="test-key")
        urlopen.return_value = BytesIO(json.dumps({
            "embeddings": [{"values": [1, 2]}, {"values": [3, 4]}],
        }).encode())
        self.assertEqual(client.embed(["First", "Second"], titles=["A", "B"]), [[1.0, 2.0], [3.0, 4.0]])
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/test-embedding:batchEmbedContents"))
        payload = json.loads(request.data)
        self.assertEqual(payload["requests"][0], {
            "model": "models/test-embedding",
            "content": {"parts": [{"text": "First"}]},
            "taskType": "RETRIEVAL_DOCUMENT",
            "title": "A",
        })
        urlopen.return_value = BytesIO(b'{"embeddings":[{"values":[1,2]}]}')
        client.embed(["Question"], task_type="RETRIEVAL_QUERY")
        self.assertEqual(json.loads(urlopen.call_args.args[0].data)["requests"][0]["taskType"], "RETRIEVAL_QUERY")

    def test_bad_requests_and_responses(self) -> None:
        client = GeminiClient(api_key="test-key")
        for texts in ([], [""], ["text"] * 101):
            with self.assertRaises(ValueError):
                client.embed(texts)
        with self.assertRaises(ValueError):
            client.embed(["query"], task_type="RETRIEVAL_QUERY", titles=["Title"])
        for response in (
            {}, {"embeddings": []}, {"embeddings": [{"values": []}]},
            {"embeddings": [{"values": [True]}]},
            {"embeddings": [{"values": [float("nan")]}]},
            {"embeddings": [{"values": [0, 0]}]},
        ):
            with self.subTest(response=response), patch.object(client, "_request", return_value=response):
                with self.assertRaises(RuntimeError):
                    client.embed(["text"])


class DatabaseTests(unittest.TestCase):
    def test_real_pdf_snapshot_atomic_failure_and_rebuild(self) -> None:
        client = GeminiClient(api_key="test-key", embedding_model="test-embedding")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "chunks.sqlite3"
            docs = ROOT / "database/docs"
            with patch.object(client, "embed", side_effect=lambda texts, **kwargs: [[1.0, 2.0] for _ in texts]) as embed:
                count = build_database(docs, output, client=client, batch_size=100)
                self.assertGreater(count, 100)
                self.assertTrue(all(len(call.args[0]) <= 100 for call in embed.call_args_list))
                self.assertIn("Stop:", embed.call_args_list[0].args[0][0])
                first_snapshot = output.read_bytes()
                with sqlite3.connect(output) as connection:
                    self.assertEqual(connection.execute("SELECT count(*) FROM chunks").fetchone(), (count,))
                    self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                    self.assertEqual(connection.execute("SELECT count(DISTINCT stop) FROM chunks").fetchone(), (5,))
                    self.assertEqual(connection.execute("SELECT DISTINCT type FROM chunks ORDER BY type").fetchall(), [("historic",), ("restaurants",)])
                    self.assertEqual(connection.execute("SELECT document_count, chunk_count FROM build_info").fetchone(), (10, count))
                    self.assertEqual(json.loads(connection.execute("SELECT embedding FROM chunks LIMIT 1").fetchone()[0]), [1.0, 2.0])
                    ids = connection.execute("SELECT id FROM chunks ORDER BY id").fetchall()
                build_database(docs, output, client=client, batch_size=100)
                with sqlite3.connect(output) as connection:
                    self.assertEqual(connection.execute("SELECT id FROM chunks ORDER BY id").fetchall(), ids)
            with patch.object(client, "embed", side_effect=RuntimeError("API unavailable")):
                before_failure = output.read_bytes()
                with self.assertRaisesRegex(RuntimeError, "API unavailable"):
                    build_database(docs, output, client=client)
                self.assertEqual(output.read_bytes(), before_failure)
            self.assertTrue(first_snapshot)
            self.assertEqual(sorted(path.name for path in output.parent.iterdir()), ["chunks.sqlite3"])
            with self.assertRaises(ValueError):
                build_database(output.parent, output, client=client)


if __name__ == "__main__":
    unittest.main()
