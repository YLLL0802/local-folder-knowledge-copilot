from __future__ import annotations

import atexit
from pathlib import Path

from qdrant_client import QdrantClient

from .config import Settings


_CLIENT_CACHE: dict[tuple[str, str], QdrantClient] = {}


def get_qdrant_client(settings: Settings) -> QdrantClient:
    """Create a Qdrant client for either remote URL or local embedded storage."""

    key = (settings.qdrant_url, str(settings.qdrant_path))
    if key not in _CLIENT_CACHE:
        _CLIENT_CACHE[key] = _create_qdrant_client(*key)
    return _CLIENT_CACHE[key]


def close_qdrant_clients() -> None:
    """Close cached Qdrant clients cleanly on process shutdown."""

    for client in _CLIENT_CACHE.values():
        client.close()
    _CLIENT_CACHE.clear()


def _create_qdrant_client(qdrant_url: str, qdrant_path: str) -> QdrantClient:
    """Create one Qdrant client for the cache."""

    if qdrant_url:
        return QdrantClient(url=qdrant_url)

    path = Path(qdrant_path)
    path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path))


atexit.register(close_qdrant_clients)


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
