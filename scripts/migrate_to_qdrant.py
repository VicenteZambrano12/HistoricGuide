# /// script
# requires-python = ">=3.10"
# dependencies = ["qdrant-client>=1.12,<2"]
# ///
"""Copy the existing SQLite embeddings into a dedicated Qdrant collection."""

import argparse
from contextlib import closing
from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import sqlite3
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models


ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    model: str
    dimensions: int
    points: list[models.PointStruct]


def load_snapshot(database: Path) -> Snapshot:
    """Validate the complete read-only source before making any remote changes."""
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Source database failed its integrity check.")
        info = connection.execute("SELECT * FROM build_info WHERE id = 1").fetchone()
        if info is None or info["schema_version"] != 1:
            raise ValueError("Source must have build_info with schema_version=1.")
        dimensions = info["embedding_dimensions"]
        model = info["embedding_model"]
        if not isinstance(dimensions, int) or dimensions < 1 or not isinstance(model, str) or not model.strip():
            raise ValueError("Invalid source embedding model or dimensions.")
        rows = connection.execute("SELECT * FROM chunks ORDER BY id").fetchall()
    if not rows or len(rows) != info["chunk_count"]:
        raise ValueError("Source is empty or chunk_count does not match build_info.")
    points: list[models.PointStruct] = []
    for row in rows:
        chunk_id = row["id"]
        if any(
            not isinstance(row[field], str) or not row[field].strip()
            for field in ("id", "text", "stop", "type", "source")
        ):
            raise ValueError(f"Missing text or metadata in chunk {chunk_id!r}.")
        if row["embedding_model"] != model or row["embedding_dimensions"] != dimensions:
            raise ValueError(f"Inconsistent embedding metadata in chunk {chunk_id!r}.")
        vector = json.loads(row["embedding"])
        if (
            not isinstance(vector, list)
            or len(vector) != dimensions
            or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in vector
            )
        ):
            raise ValueError(f"Invalid embedding in chunk {chunk_id!r}.")
        norm = math.hypot(*vector)
        if not norm or not math.isfinite(norm):
            raise ValueError(f"Embedding must have a finite nonzero norm: {chunk_id!r}.")
        for field, minimum in (("page", 1), ("chunk_index", 0), ("token_count", 1)):
            if not isinstance(row[field], int) or row[field] < minimum:
                raise ValueError(f"Invalid {field} in chunk {chunk_id!r}.")
        points.append(models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"historicguide:chunk:{chunk_id}")),
            vector=[float(value) for value in vector],
            payload={
                "chunk_id": chunk_id,
                "text": row["text"],
                "stop_id": row["stop"],
                "stop": row["stop"],
                "type": row["type"],
                "source": row["source"],
                "page": row["page"],
                "chunk_index": row["chunk_index"],
                "token_count": row["token_count"],
                "embedding_model": model,
                "embedding_dimensions": dimensions,
            },
        ))
    if len({point.id for point in points}) != len(points):
        raise ValueError("Duplicate point IDs in source.")
    return Snapshot(model=model, dimensions=dimensions, points=points)


def migrate(
    client: QdrantClient,
    snapshot: Snapshot,
    *,
    collection: str = "historic_guide",
    batch_size: int = 32,
) -> int:
    """Upsert deterministic IDs; never delete collections or unrelated points."""
    if not collection.strip() or batch_size < 1:
        raise ValueError("Collection must be nonempty and batch_size must be positive.")
    expected = {str(point.id): point for point in snapshot.points}
    if client.collection_exists(collection):
        info = client.get_collection(collection)
        vectors = info.config.params.vectors
        if (
            not isinstance(vectors, models.VectorParams)
            or vectors.size != snapshot.dimensions
            or vectors.distance != models.Distance.COSINE
        ):
            raise ValueError("Existing collection must use unnamed cosine vectors with matching dimensions.")
        offset = None
        while True:
            records, offset = client.scroll(
                collection, limit=batch_size, offset=offset,
                with_payload=True, with_vectors=False,
            )
            for record in records:
                point = expected.get(str(record.id))
                if point is None or record.payload != point.payload:
                    raise ValueError(
                        "Existing collection contains unrelated or changed data; "
                        "use a new dedicated collection. Nothing was written."
                    )
            if offset is None:
                break
    else:
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=snapshot.dimensions, distance=models.Distance.COSINE,
            ),
        )
    for field in ("stop_id", "type"):
        client.create_payload_index(
            collection_name=collection, field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD, wait=True,
        )
    for start in range(0, len(snapshot.points), batch_size):
        batch = snapshot.points[start:start + batch_size]
        result = client.upsert(collection_name=collection, points=batch, wait=True)
        if result.status != models.UpdateStatus.COMPLETED:
            raise RuntimeError(f"Qdrant did not complete batch starting at {start}.")
        records = client.retrieve(
            collection, ids=[point.id for point in batch], with_payload=True, with_vectors=True,
        )
        if {str(record.id) for record in records} != {str(point.id) for point in batch}:
            raise RuntimeError("Uploaded point IDs failed read-back verification.")
        for record in records:
            point = expected[str(record.id)]
            if record.payload != point.payload:
                raise RuntimeError(f"Payload verification failed for {record.id}.")
            source_vector = point.vector
            stored_vector = record.vector
            if not isinstance(source_vector, list) or not isinstance(stored_vector, list):
                raise RuntimeError(f"Vector verification failed for {record.id}.")
            norm = math.hypot(*source_vector)
            if len(stored_vector) != len(source_vector) or any(
                not math.isclose(actual, value / norm, rel_tol=1e-5, abs_tol=1e-6)
                for actual, value in zip(stored_vector, source_vector)
            ):
                raise RuntimeError(f"Vector verification failed for {record.id}.")
        LOGGER.info("Uploaded and verified %d/%d chunks", start + len(batch), len(snapshot.points))
    count = client.count(collection, exact=True).count
    if count != len(snapshot.points):
        raise RuntimeError(f"Expected {len(snapshot.points)} points, found {count}.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "database/provisional_db/chunks.sqlite3")
    parser.add_argument("--url", default=os.environ.get("QDRANT_URL"),
                        help="Qdrant HTTP URL, or set QDRANT_URL. Use a tunnel for a private VM.")
    parser.add_argument("--collection", default="historic_guide")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true", help="Validate SQLite only; no Qdrant connection.")
    args = parser.parse_args()
    if args.batch_size < 1 or not args.collection.strip():
        parser.error("--batch-size must be positive and --collection must be nonempty.")
    if not args.dry_run and not args.url:
        parser.error("Provide --url or QDRANT_URL.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    snapshot = load_snapshot(args.database)
    LOGGER.info(
        "Validated %d chunks; model=%s, dimensions=%d",
        len(snapshot.points), snapshot.model, snapshot.dimensions,
    )
    if args.dry_run:
        return
    client = QdrantClient(url=args.url, api_key=os.environ.get("QDRANT_API_KEY"), timeout=60)
    try:
        count = migrate(client, snapshot, collection=args.collection, batch_size=args.batch_size)
    finally:
        client.close()
    LOGGER.info("Migration complete: %d verified points in %s.", count, args.collection)


if __name__ == "__main__":
    main()