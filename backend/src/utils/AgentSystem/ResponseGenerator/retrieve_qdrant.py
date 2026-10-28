"""Retrieve the same stop/type context from the migrated Qdrant collection."""

from qdrant_client import QdrantClient, models

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category
from src.utils.general.GeminiApiCall import GeminiClient, _configuration_value
from src.utils.general.sources import PdfSource, report_sources

from .retrieve_chunks import _unit_vector


def qdrant_client() -> QdrantClient:
    url = _configuration_value("QDRANT_URL").strip()
    api_key = _configuration_value("QDRANT_API_KEY").strip() or None
    if url:
        return QdrantClient(url=url, api_key=api_key, timeout=60)
    host = _configuration_value("QDRANT_HOST").strip()
    if not host:
        raise ValueError("Set QDRANT_URL or QDRANT_HOST for ENV=GCP.")
    port = int(_configuration_value("QDRANT_PORT", "6333"))
    if not 1 <= port <= 65535:
        raise ValueError("QDRANT_PORT must be between 1 and 65535.")
    return QdrantClient(host=host, port=port, api_key=api_key, timeout=60)


def retrieve_qdrant(
    client: GeminiClient, stop: str, category: Category, *, user_query: str | None,
) -> list[str]:
    collection = _configuration_value("QDRANT_COLLECTION", "historic_guide").strip()
    if not collection:
        raise ValueError("QDRANT_COLLECTION must not be empty.")
    chunk_type = "restaurants" if category == "restaurant" else "historic"
    filters = models.Filter(must=[
        models.FieldCondition(key="stop_id", match=models.MatchValue(value=stop)),
        models.FieldCondition(key="type", match=models.MatchValue(value=chunk_type)),
    ])
    model = client.embedding_model.strip().removeprefix("models/")
    remote = qdrant_client()
    try:
        vectors = remote.get_collection(collection).config.params.vectors
        if not isinstance(vectors, models.VectorParams) or vectors.distance != models.Distance.COSINE:
            raise RuntimeError("Qdrant collection must use unnamed cosine vectors.")
        dimensions = vectors.size
        offset = None
        found = False
        while True:
            records, offset = remote.scroll(
                collection, scroll_filter=filters, limit=100, offset=offset,
                with_payload=True, with_vectors=False,
            )
            for record in records:
                found = True
                payload = record.payload or {}
                if payload.get("embedding_model") != model:
                    raise RuntimeError("RAG embedding model mismatch in Qdrant.")
                if payload.get("embedding_dimensions") != dimensions:
                    raise RuntimeError("Incompatible embedding dimensions in Qdrant.")
            if offset is None:
                break
        if not found:
            raise ValueError(f"No RAG chunks found for stop={stop!r}, type={chunk_type!r}.")
        query = user_query or (
            "Give a short historical introduction." if category == "historic"
            else "Introduce nearby dining options and local specialties."
        )
        embeddings = client.embed(
            [f"Stop: {stop}\nType: {chunk_type}\n\n{query}"],
            task_type="RETRIEVAL_QUERY",
        )
        if len(embeddings) != 1:
            raise RuntimeError("Expected exactly one query embedding.")
        query_vector = _unit_vector(embeddings[0], dimensions)
        points = remote.query_points(
            collection, query=query_vector, query_filter=filters,
            limit=2, with_payload=True, with_vectors=True,
        ).points
        if not points:
            raise RuntimeError("Qdrant returned no results after matching chunks were found.")
        texts: list[str] = []
        sources: list[PdfSource] = []
        for point in points:
            payload = point.payload or {}
            if (
                payload.get("stop_id") != stop or payload.get("type") != chunk_type
                or payload.get("embedding_model") != model
                or payload.get("embedding_dimensions") != dimensions
            ):
                raise RuntimeError("Qdrant returned incompatible chunk metadata.")
            _unit_vector(point.vector, dimensions)
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Qdrant returned empty chunk text.")
            sources.append(PdfSource.model_validate({
                "source": payload.get("source"), "page": payload.get("page"),
            }))
            texts.append(text)
        report_sources(sources)
        return texts
    finally:
        remote.close()
