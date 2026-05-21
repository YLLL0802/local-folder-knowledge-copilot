from pathlib import Path
from typing import Any

import streamlit as st

from src.audit import read_recent_audit_logs, write_audit_log
from src.config import get_settings
from src.generator import generate_grounded_answer
from src.guardrails import run_guardrails
from src.indexing import clear_index, index_folder
from src.loaders import load_documents
from src.permissions import ROLES
from src.retriever import retrieve_chunks


def init_session_state() -> None:
    """Initialize chat state used by the Streamlit UI."""

    if "messages" not in st.session_state:
        st.session_state.messages = []


def reset_chat() -> None:
    """Clear chat messages without changing the index or settings."""

    st.session_state.messages = []


def source_rows(chunks: list[Any]) -> list[dict[str, Any]]:
    """Convert retrieved chunks into source rows for display."""

    return [
        {
            "file_name": chunk.metadata.get("file_name", "unknown"),
            "relative_path": chunk.metadata.get("relative_path"),
            "score": round(chunk.score, 4),
            "department": chunk.metadata.get("department"),
            "sensitivity": chunk.metadata.get("sensitivity"),
            "allowed_roles": ", ".join(chunk.metadata.get("allowed_roles", [])),
            "chunk_index": chunk.metadata.get("chunk_index"),
            "snippet": chunk.snippet,
        }
        for chunk in chunks
    ]


def render_sources(chunks: list[Any]) -> None:
    """Render retrieved sources in a compact expander."""

    with st.expander("Sources", expanded=bool(chunks)):
        if not chunks:
            st.caption("No accessible sources were retrieved.")
            return
        for row in source_rows(chunks):
            st.markdown(f"**{row['file_name']}**")
            st.write(
                {
                    "relative_path": row["relative_path"],
                    "score": row["score"],
                    "department": row["department"],
                    "sensitivity": row["sensitivity"],
                    "allowed_roles": row["allowed_roles"],
                    "chunk_index": row["chunk_index"],
                }
            )
            st.caption(row["snippet"])


def render_warnings(warnings: list[str]) -> None:
    """Render guardrail warnings below an assistant answer."""

    if not warnings:
        return
    with st.expander("Warnings", expanded=True):
        for warning in warnings:
            st.warning(warning)


def render_audit_preview() -> None:
    """Render recent JSONL audit events in the sidebar."""

    records = read_recent_audit_logs(settings, limit=5)
    with st.expander("Audit log preview"):
        if not records:
            st.caption("No audit events yet.")
            return
        for record in records:
            st.write(
                {
                    "timestamp": record.get("timestamp"),
                    "role": record.get("user_role"),
                    "status": record.get("answer_status"),
                    "sources": record.get("retrieved_source_count"),
                    "warnings": record.get("warnings", []),
                    "query": record.get("query"),
                }
            )


# Configure the Streamlit page before rendering any widgets.
st.set_page_config(page_title="Local OneDrive Knowledge Copilot", layout="wide")

# Load environment-driven settings once for this Streamlit run.
settings = get_settings()
init_session_state()

st.title("Local OneDrive Knowledge Copilot")

# Sidebar controls represent the local enterprise workspace and indexing settings.
with st.sidebar:
    st.subheader("Workspace")
    default_path = Path("data/sample_docs").resolve()
    folder_path = st.text_input("Local folder path", value=str(default_path))
    user_role = st.selectbox("User role", ROLES, index=0)
    max_file_size_mb = st.number_input("Max file size (MB)", min_value=1, max_value=100, value=10)

    st.subheader("Retrieval Settings")
    st.text_input("Collection", value=settings.qdrant_collection, disabled=True)
    st.text_input("Embedding provider", value=settings.embedding_provider, disabled=True)
    st.text_input("Embedding model", value=settings.embedding_model, disabled=True)
    st.number_input("Top K", value=settings.top_k, disabled=True)
    st.number_input("Min score", value=settings.min_score, disabled=True)

    load_clicked = st.button("Load document preview")
    reindex_clicked = st.button("Re-index documents", type="primary")
    clear_clicked = st.button("Clear index")
    st.button("Clear chat", on_click=reset_chat)
    render_audit_preview()

# Show the selected demo role and retrieval scope.
st.caption(f"Current role: {user_role}")

# Clear index removes the configured Qdrant collection.
if clear_clicked:
    try:
        deleted = clear_index(settings)
    except Exception as exc:
        st.error(str(exc))
    else:
        if deleted:
            st.success(f"Cleared collection '{settings.qdrant_collection}'.")
        else:
            st.info(f"Collection '{settings.qdrant_collection}' did not exist.")

# Re-index runs the Phase 2 pipeline: load, chunk, embed, and upsert.
if reindex_clicked:
    try:
        with st.spinner("Indexing documents into Qdrant..."):
            result = index_folder(
                folder_path,
                settings=settings,
                clear_existing=True,
                max_file_size_mb=max_file_size_mb,
            )
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    st.success(
        f"Indexed {result.document_count} documents into {result.chunk_count} chunks."
    )
    st.write(
        {
            "collection": result.collection_name,
            "vector_size": result.vector_size,
            "indexed_points": result.indexed_point_count,
        }
    )

# Load preview only reads files and metadata; it does not embed or index.
if load_clicked:
    try:
        documents = load_documents(folder_path, max_file_size_mb=max_file_size_mb)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    st.success(f"Loaded {len(documents)} documents")
    if not documents:
        st.info("No supported documents were found.")
        st.stop()

    rows = [
        {
            "file_name": doc.metadata.file_name,
            "relative_path": doc.metadata.relative_path,
            "department": doc.metadata.department,
            "sensitivity": doc.metadata.sensitivity,
            "allowed_roles": ", ".join(doc.metadata.allowed_roles),
            "file_type": doc.metadata.file_type,
            "size_bytes": doc.metadata.size_bytes,
            "modified_at": doc.metadata.modified_at.isoformat(),
            "preview": doc.preview,
        }
        for doc in documents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Raw metadata"):
        for doc in documents:
            st.json(doc.metadata.model_dump(mode="json"))
elif not reindex_clicked and not clear_clicked and not st.session_state.messages:
    # Default empty state tells the user what can be done before indexing.
    st.info("Load the sample folder to preview documents and metadata before indexing.")

# Render chat history after any one-off preview/index status blocks.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant":
            st.caption(message.get("status", ""))
            render_warnings(message.get("warnings", []))
            render_sources(message.get("chunks", []))

# Chat input runs Phase 4 chat UX over the Phase 3 retrieval/generation backend.
if prompt := st.chat_input("Ask indexed documents"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving accessible sources..."):
            try:
                chunks = retrieve_chunks(prompt, user_role, settings)
                guardrails = run_guardrails(prompt, chunks)
                generated = generate_grounded_answer(
                    prompt,
                    chunks,
                    settings,
                    warnings=guardrails.warnings,
                )
                write_audit_log(
                    settings=settings,
                    user_role=user_role,
                    query=prompt,
                    answer_status=generated.answer_status,
                    chunks=chunks,
                    warnings=guardrails.warnings,
                )
            except Exception as exc:
                st.error(str(exc))
                st.stop()

        st.write(generated.answer)
        llm_status = settings.llm_model if generated.used_llm else "no"
        status = (
            f"Role: {user_role} | Status: {generated.answer_status} | "
            f"LLM used: {llm_status} | "
            f"Filtered sources: {len(chunks)}"
        )
        st.caption(status)
        render_warnings(guardrails.warnings)
        render_sources(chunks)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": generated.answer,
            "status": status,
            "chunks": chunks,
            "warnings": guardrails.warnings,
        }
    )
