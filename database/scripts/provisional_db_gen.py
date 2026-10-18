# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pypdf>=6,<7",
#     "python-dotenv>=1,<2",
#     "tiktoken>=0.8,<1",
# ]
# ///
"""Build an atomic SQLite snapshot of PDF chunks and Gemini embeddings."""

import argparse
from dataclasses import asdict
import hashlib
import json
import logging
import math
from pathlib import Path
import sqlite3
import sys
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from src.utils.general.GeminiApiCall import GeminiClient

if __package__:
    from .chunk_gen import ChunkGen
else:
    from chunk_gen import ChunkGen


LOGGER = logging.getLogger(__name__)


def _embed_batch(client: GeminiClient, texts: list[str], titles: list[str]) -> list[list[float]]:
    for attempt in range(4):
        try:
            return client.embed(texts, titles=titles)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            delay = float(60 * 2 ** attempt)
            retry_after = error.headers.get("Retry-After") if error.headers is not None else None
            if retry_after is not None and re.fullmatch(r"\d+(?:\.\d+)?", retry_after):
                delay = max(delay, float(retry_after))
            if not math.isfinite(delay) or delay > 600:
                raise
            LOGGER.warning(
                "Gemini HTTP %d; retrying embedding batch in %.0fs (%d/3)",
                error.code, delay, attempt + 1,
            )
            error.close()
            time.sleep(delay)
    raise RuntimeError("Embedding retries exhausted.")


def build_database(
    docs_root: Path,
    output: Path,
    *,
    client: GeminiClient,
    chunker: ChunkGen | None = None,
    batch_size: int = 32,
) -> int:
    """Rebuild the complete snapshot; leave the previous database intact on failure."""
    if not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be between 1 and 100.")
    docs_root = docs_root.resolve()
    output = output.resolve()
    if not docs_root.is_dir():
        raise FileNotFoundError(f"Document directory does not exist: {docs_root}")
    if output.is_relative_to(docs_root):
        raise ValueError("The output database must be outside the source document directory.")
    pdfs = sorted(path for path in docs_root.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdfs:
        raise ValueError(f"No PDFs found under {docs_root}.")
    chunker = chunker if chunker is not None else ChunkGen()
    chunks = [chunk for pdf in pdfs for chunk in chunker.generate(pdf, docs_root=docs_root)]
    if not chunks:
        raise ValueError("The corpus produced no chunks.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as file:
        temporary = Path(file.name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            with connection:
                connection.executescript("""
                    CREATE TABLE chunks (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        stop TEXT NOT NULL,
                        type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL CHECK (page > 0),
                        chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
                        token_count INTEGER NOT NULL CHECK (token_count > 0),
                        embedding TEXT NOT NULL,
                        embedding_model TEXT NOT NULL,
                        embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions > 0),
                        UNIQUE (source, chunk_index)
                    );
                    CREATE INDEX chunks_stop_type ON chunks (stop, type);
                    CREATE TABLE build_info (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        schema_version INTEGER NOT NULL,
                        embedding_model TEXT NOT NULL,
                        embedding_dimensions INTEGER NOT NULL,
                        tokenizer TEXT NOT NULL,
                        max_tokens INTEGER NOT NULL,
                        overlap_tokens INTEGER NOT NULL,
                        document_count INTEGER NOT NULL,
                        chunk_count INTEGER NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                dimensions: int | None = None
                for start in range(0, len(chunks), batch_size):
                    batch = chunks[start:start + batch_size]
                    vectors = _embed_batch(
                        client,
                        [f"Stop: {chunk.stop}\nType: {chunk.type}\n\n{chunk.text}" for chunk in batch],
                        [f"{chunk.stop} / {chunk.type} / page {chunk.page}" for chunk in batch],
                    )
                    if len(vectors) != len(batch):
                        raise RuntimeError("Embedding count does not match chunk count.")
                    for chunk, vector in zip(batch, vectors):
                        if dimensions is None:
                            dimensions = len(vector)
                        if not vector or len(vector) != dimensions:
                            raise RuntimeError("Embedding dimensions changed during the build.")
                        values = asdict(chunk)
                        values.update(
                            id=hashlib.sha256(
                                f"{chunk.source}\0{chunk.chunk_index}\0{chunk.text}".encode("utf-8")
                            ).hexdigest(),
                            embedding=json.dumps(vector, allow_nan=False),
                            embedding_model=client.embedding_model.strip().removeprefix("models/"),
                            embedding_dimensions=dimensions,
                        )
                        connection.execute("""
                            INSERT INTO chunks VALUES (
                                :id, :text, :stop, :type, :source, :page, :chunk_index,
                                :token_count, :embedding, :embedding_model, :embedding_dimensions
                            )
                        """, values)
                    LOGGER.info("Embedded %d/%d chunks", min(start + batch_size, len(chunks)), len(chunks))
                connection.execute("""
                    INSERT INTO build_info (
                        id, schema_version, embedding_model, embedding_dimensions, tokenizer,
                        max_tokens, overlap_tokens, document_count, chunk_count
                    ) VALUES (1, 1, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client.embedding_model.strip().removeprefix("models/"), dimensions, chunker.encoding.name,
                    chunker.max_tokens, chunker.overlap_tokens, len(pdfs), len(chunks),
                ))
                if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("SQLite integrity check failed.")
        finally:
            connection.close()
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=ROOT / "database/docs")
    parser.add_argument("--output", type=Path, default=ROOT / "database/provisional_db/chunks.sqlite3")
    parser.add_argument("--max-tokens", type=int, default=400)
    parser.add_argument("--overlap-tokens", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = build_database(
        args.docs_dir, args.output, client=GeminiClient(),
        chunker=ChunkGen(args.max_tokens, args.overlap_tokens), batch_size=args.batch_size,
    )
    LOGGER.info("Created %s with %d chunks", args.output.resolve(), count)


if __name__ == "__main__":
    main()