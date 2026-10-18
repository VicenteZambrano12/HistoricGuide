"""Retrieve stop/type-filtered context from the provisional SQLite snapshot."""

from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.general.GeminiApiCall import GeminiClient
from src.utils.general.sources import PdfSource, report_sources


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[5] / "database/provisional_db/chunks.sqlite3"
)


def _unit_vector(values: object, dimensions: int) -> list[float]:
    if not isinstance(values, list) or len(values) != dimensions or not values:
        raise RuntimeError("Invalid retrieval vector dimensions.")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        raise RuntimeError("Retrieval vectors must contain finite numbers.")
    norm = math.hypot(*values)
    if not norm or not math.isfinite(norm):
        raise RuntimeError("Retrieval vectors must have a finite, nonzero norm.")
    return [value / norm for value in values]


def retrieve_chunks(
    client: GeminiClient,
    stop: str,
    category: Category,
    *,
    user_query: str | None,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> list[str]:
    """Return the two closest chunks (or one if only one matches); errors propagate."""
    chunk_type = "restaurants" if category == "restaurant" else "historic"
    with closing(sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        info = connection.execute(
            "SELECT embedding_model, embedding_dimensions FROM build_info WHERE id = 1"
        ).fetchone()
        if info is None:
            raise RuntimeError("The RAG database has no build metadata; rebuild it.")
        model = client.embedding_model.strip().removeprefix("models/")
        if info["embedding_model"] != model:
            raise RuntimeError(
                f"RAG embedding model mismatch: database uses {info['embedding_model']!r}, "
                f"but the client uses {model!r}. Rebuild the database or use its model."
            )
        rows = connection.execute(
            """SELECT id, text, source, page, embedding, embedding_model, embedding_dimensions
               FROM chunks WHERE stop = ? AND type = ? ORDER BY id""",
            (stop, chunk_type),
        ).fetchall()
    if not rows:
        raise ValueError(f"No RAG chunks found for stop={stop!r}, type={chunk_type!r}.")

    query = user_query or (
        "Give a short historical introduction."
        if category == "historic"
        else "Introduce nearby dining options and local specialties."
    )
    vectors = client.embed(
        [f"Stop: {stop}\nType: {chunk_type}\n\n{query}"],
        task_type="RETRIEVAL_QUERY",
    )
    if len(vectors) != 1:
        raise RuntimeError("Expected exactly one query embedding.")
    dimensions = info["embedding_dimensions"]
    query_vector = _unit_vector(vectors[0], dimensions)
    scored: list[tuple[float, sqlite3.Row]] = []
    for row in rows:
        if row["embedding_model"] != model or row["embedding_dimensions"] != dimensions:
            raise RuntimeError(f"Incompatible embedding metadata for chunk {row['id']!r}.")
        vector = _unit_vector(json.loads(row["embedding"]), dimensions)
        if not row["text"].strip():
            raise RuntimeError(f"Empty text for chunk {row['id']!r}.")
        score = math.fsum(left * right for left, right in zip(query_vector, vector))
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [row for _, row in scored[:2]]
    report_sources([PdfSource(source=row["source"], page=row["page"]) for row in selected])
    return [row["text"] for row in selected]
