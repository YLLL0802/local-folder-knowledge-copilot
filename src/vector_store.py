from __future__ import annotations

from pathlib import Path

from qdrant_client import QdrantClient

from .config import Settings


def get_qdrant_client(settings: Settings) -> QdrantClient:
    """Create a Qdrant client for either remote URL or local embedded storage."""

    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)

    path = Path(settings.qdrant_path)
    path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path))


def clear_collection(client: QdrantClient, collection_name: str) -> bool:
    """Delete a Qdrant collection and report whether it existed."""

    if not client.collection_exists(collection_name):
        return False
    client.delete_collection(collection_name)
    return True


def count_points(client: QdrantClient, collection_name: str) -> int:
    """Return the number of indexed points in a collection."""

    if not client.collection_exists(collection_name):
        return 0
    result = client.count(collection_name=collection_name, exact=True)
    return int(result.count)
