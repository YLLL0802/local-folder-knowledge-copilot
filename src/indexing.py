from __future__ import annotations

import argparse
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llama_index.core import Document
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from .config import Settings, get_settings
from .loaders import load_documents
from .vector_store import (
    clear_collection,
    count_points,
    get_qdrant_client,
)


@dataclass
class IndexingResult:
    """Summary returned after indexing documents into Qdrant."""

    document_count: int
    chunk_count: int
    vector_size: int
    collection_name: str
    indexed_point_count: int


def index_folder(
    root_path: str | Path,
    settings: Settings,
    clear_existing: bool = False,
    max_file_size_mb: int = 10,
) -> IndexingResult:
    """Load, split, embed, and index documents into Qdrant."""

    documents = load_documents(root_path, max_file_size_mb=max_file_size_mb)
    llama_documents = _to_llama_documents(documents)
    client = get_qdrant_client(settings)
    if clear_existing:
        clear_collection(client, settings.qdrant_collection)

    nodes = _split_documents_with_llama_index(
        llama_documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    embed_model = _build_llama_index_embedding(settings)
    vector_size = _embedding_dimension(embed_model, settings)
    vector_store = _build_qdrant_vector_store(client, settings.qdrant_collection)
    pipeline = _build_ingestion_pipeline(embed_model, vector_store)
    pipeline.run(nodes=nodes, show_progress=False)

    return IndexingResult(
        document_count=len(documents),
        chunk_count=len(nodes),
        vector_size=vector_size,
        collection_name=settings.qdrant_collection,
        indexed_point_count=count_points(client, settings.qdrant_collection),
    )


def clear_index(settings: Settings) -> bool:
    """Clear the configured Qdrant collection from the UI or CLI layer."""

    client = get_qdrant_client(settings)
    return clear_collection(client, settings.qdrant_collection)


def _to_llama_documents(documents: list[Any]) -> list[Any]:
    """Convert project LoadedDocument objects into LlamaIndex Document objects."""

    llama_documents = []
    for document in documents:
        metadata = document.metadata.model_dump(mode="json")
        llama_documents.append(
            Document(
                text=document.text,
                metadata=metadata,
                id_=document.metadata.doc_id,
            )
        )
    return llama_documents


def _split_documents_with_llama_index(
    llama_documents: list[Any],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Any]:
    """Use LlamaIndex SentenceSplitter and attach stable enterprise chunk metadata."""

    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = splitter.get_nodes_from_documents(llama_documents, show_progress=False)

    chunk_indexes: dict[str, int] = {}
    for node in nodes:
        doc_id = node.ref_doc_id or node.metadata.get("doc_id") or node.node_id
        chunk_index = chunk_indexes.get(doc_id, 0)
        chunk_indexes[doc_id] = chunk_index + 1

        chunk_id = f"{doc_id}:{chunk_index}"
        node.id_ = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
        node.metadata["chunk_id"] = chunk_id
        node.metadata["chunk_index"] = chunk_index
        node.metadata["checksum"] = hashlib.sha256(
            _node_text(node).encode("utf-8")
        ).hexdigest()

    return nodes


def _build_llama_index_embedding(settings: Settings) -> Any:
    """Create the configured LlamaIndex embedding model."""

    if settings.embedding_provider != "sentence_transformers":
        raise ValueError(
            "LlamaIndex indexing currently uses EMBEDDING_PROVIDER=sentence_transformers. "
            "Set EMBEDDING_PROVIDER=sentence_transformers or provide a local HuggingFace model path."
        )
    try:
        return HuggingFaceEmbedding(model_name=settings.embedding_model)
    except OSError as exc:
        raise RuntimeError(
            f"Embedding model '{settings.embedding_model}' is not available locally. "
            "Connect to the internet for the first download or set EMBEDDING_MODEL to a local model path."
        ) from exc


def _embedding_dimension(embed_model: Any, settings: Settings) -> int:
    """Determine embedding dimension without duplicating ingestion work."""

    sample_vector = embed_model.get_text_embedding("dimension check")
    if not sample_vector:
        raise RuntimeError(f"Embedding model '{settings.embedding_model}' returned an empty vector.")
    return len(sample_vector)


def _build_qdrant_vector_store(client: Any, collection_name: str) -> Any:
    """Create the official LlamaIndex Qdrant vector store wrapper."""

    return QdrantVectorStore(client=client, collection_name=collection_name)


def _build_ingestion_pipeline(embed_model: Any, vector_store: Any) -> Any:
    """Create a LlamaIndex ingestion pipeline that embeds nodes and writes Qdrant."""

    return IngestionPipeline(transformations=[embed_model], vector_store=vector_store)


def _node_text(node: Any) -> str:
    """Read node text without including metadata in the checksum."""

    if hasattr(node, "text"):
        return node.text
    return node.get_content(metadata_mode="none")


def _main() -> None:
    """Run the indexing pipeline from the command line."""

    parser = argparse.ArgumentParser(description="Index local documents into Qdrant.")
    parser.add_argument("--root", default="data/sample_docs", help="Folder to index.")
    parser.add_argument("--clear", action="store_true", help="Clear collection before indexing.")
    parser.add_argument("--max-file-size-mb", type=int, default=10)
    args = parser.parse_args()

    settings = get_settings()
    result = index_folder(
        args.root,
        settings=settings,
        clear_existing=args.clear,
        max_file_size_mb=args.max_file_size_mb,
    )
    print(
        f"Indexed {result.document_count} documents into {result.chunk_count} chunks "
        f"({result.indexed_point_count} points in '{result.collection_name}', "
        f"vector_size={result.vector_size})."
    )


if __name__ == "__main__":
    _main()
