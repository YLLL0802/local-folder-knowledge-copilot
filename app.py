from pathlib import Path

import streamlit as st

from src.config import get_settings
from src.generator import generate_grounded_answer
from src.indexing import clear_index, index_folder
from src.loaders import load_documents
from src.permissions import ROLES
from src.retriever import retrieve_chunks


# Configure the Streamlit page before rendering any widgets.
st.set_page_config(page_title="Local OneDrive Knowledge Copilot", layout="wide")

# Load environment-driven settings once for this Streamlit run.
settings = get_settings()

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

# Show the selected demo role even before retrieval is implemented.
st.caption(f"Current role: {user_role}")

# Minimal Phase 3 query entry point before the full chat UI is built in Phase 4.
question = st.text_input("Ask indexed documents")
ask_clicked = st.button("Ask")

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

# Ask runs Phase 3 retrieval and grounded answer generation.
if ask_clicked:
    try:
        with st.spinner("Retrieving accessible sources..."):
            chunks = retrieve_chunks(question, user_role, settings)
            generated = generate_grounded_answer(question, chunks, settings)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    st.subheader("Answer")
    st.write(generated.answer)
    st.caption(
        f"Status: {generated.answer_status} | "
        f"LLM used: {'yes' if generated.used_llm else 'no'} | "
        f"Filtered sources: {len(chunks)}"
    )

    with st.expander("Sources", expanded=bool(chunks)):
        for chunk in chunks:
            st.markdown(f"**{chunk.metadata.get('file_name', 'unknown')}**")
            st.write(
                {
                    "relative_path": chunk.metadata.get("relative_path"),
                    "score": round(chunk.score, 4),
                    "department": chunk.metadata.get("department"),
                    "sensitivity": chunk.metadata.get("sensitivity"),
                    "allowed_roles": chunk.metadata.get("allowed_roles"),
                    "chunk_index": chunk.metadata.get("chunk_index"),
                }
            )
            st.caption(chunk.snippet)

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
elif not reindex_clicked and not clear_clicked and not ask_clicked:
    # Default empty state tells the user what can be done before indexing.
    st.info("Load the sample folder to preview documents and metadata before indexing.")
