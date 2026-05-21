from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from qdrant_client.http import models

from .config import Settings
from .permissions import validate_role
from .vector_store import get_qdrant_client


@dataclass
class RetrievedChunk:
    """A permission-filtered chunk returned from vector search."""

    text: str
    score: float
    metadata: dict[str, Any]

    @property
    def citation(self) -> str:
        """Return the citation format used in grounded answers."""

        file_name = self.metadata.get("file_name", "unknown")
        chunk_index = self.metadata.get("chunk_index", "unknown")
        return f"[source: {file_name}, chunk {chunk_index}]"

    @property
    def snippet(self) -> str:
        """Return a compact source preview for the UI."""

        normalized = " ".join(self.text.split())
        return normalized[:360]


def retrieve_chunks(query: str, user_role: str, settings: Settings) -> list[RetrievedChunk]:
    """Embed a query and retrieve chunks filtered by the current user role."""

    validate_role(user_role)
    if not query.strip():
        return []

    client = get_qdrant_client(settings)
    if not client.collection_exists(settings.qdrant_collection):
        return []

    embed_model = _build_query_embedding_model(settings)
    query_vector = embed_model.get_query_embedding(query)
    query_filter = _role_filter(user_role)
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=query_filter,
        limit=settings.top_k,
        with_payload=True,
        with_vectors=False,
    )

    points = getattr(response, "points", response)
    chunks: list[RetrievedChunk] = []
    for point in points:
        score = float(point.score)
        if score < settings.min_score:
            continue
        payload = point.payload or {}
        chunks.append(
            RetrievedChunk(
                text=_payload_text(payload),
                score=score,
                metadata=payload,
            )
        )
    return chunks


def _build_query_embedding_model(settings: Settings) -> HuggingFaceEmbedding:
    """Create the same LlamaIndex embedding model used during indexing."""

    if settings.embedding_provider != "sentence_transformers":
        raise ValueError(
            "Retrieval currently uses EMBEDDING_PROVIDER=sentence_transformers. "
            "Use the same embedding provider for indexing and retrieval."
        )
    return _cached_huggingface_embedding(settings.embedding_model)


@lru_cache(maxsize=4)
def _cached_huggingface_embedding(model_name: str) -> HuggingFaceEmbedding:
    """Cache embedding models so Streamlit asks do not reload weights every time."""

    return HuggingFaceEmbedding(model_name=model_name)


def _role_filter(user_role: str) -> models.Filter | None:
    """Build a Qdrant payload filter that enforces role-based access."""

    if user_role == "admin":
        return None
    return models.Filter(
        must=[
            models.FieldCondition(
                key="allowed_roles",
                match=models.MatchValue(value=user_role),
            )
        ]
    )


def _payload_text(payload: dict[str, Any]) -> str:
    """Extract node text from the LlamaIndex payload stored in Qdrant."""

    if "text" in payload:
        return str(payload["text"])

    node_content = payload.get("_node_content")
    if not node_content:
        return ""
    try:
        parsed = json.loads(node_content)
    except (TypeError, json.JSONDecodeError):
        return ""
    return str(parsed.get("text", ""))
