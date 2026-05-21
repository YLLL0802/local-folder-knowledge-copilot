from pathlib import Path
from typing import Any

import streamlit as st

from src.audit import read_recent_audit_logs, write_audit_log
from src.auth import AuthenticatedUser, authenticate_user, resolve_user
from src.config import Settings, get_settings
from src.generator import generate_grounded_answer
from src.guardrails import run_guardrails
from src.indexing import clear_index, index_folder
from src.loaders import load_documents
from src.permissions import ROLES
from src.retriever import retrieve_chunks
from src.user_store import delete_user, list_users, upsert_user


def init_session_state() -> None:
    """Initialize authentication and chat state used by Streamlit."""

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_email" not in st.session_state:
        st.session_state.user_email = None


def reset_chat() -> None:
    """Clear chat messages without changing the index or login state."""

    st.session_state.messages = []


def logout() -> None:
    """Clear the local demo login session."""

    st.session_state.user_email = None
    reset_chat()


def current_user(settings: Settings) -> AuthenticatedUser | None:
    """Resolve the current session email to the latest stored user role."""

    email = st.session_state.get("user_email")
    if not email:
        return None
    return resolve_user(str(email), settings)


def render_login(settings: Settings) -> None:
    """Render the local demo login form."""

    st.caption("Sign in with a demo email account.")
    with st.form("login_form"):
        email = st.text_input("Email", value=settings.admin_email)
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if not submitted:
        st.info(
            "Default local admin is configured with ADMIN_EMAIL and ADMIN_PASSWORD in .env."
        )
        return

    user = authenticate_user(email=email, password=password, settings=settings)
    if not user:
        st.error("Invalid email or password.")
        return

    st.session_state.user_email = user.email
    reset_chat()
    st.rerun()


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


def render_audit_preview(settings: Settings) -> None:
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
                    "user": record.get("user_email"),
                    "role": record.get("user_role"),
                    "status": record.get("answer_status"),
                    "sources": record.get("retrieved_source_count"),
                    "warnings": record.get("warnings", []),
                    "query": record.get("query"),
                }
            )


def render_sidebar(settings: Settings, user: AuthenticatedUser) -> dict[str, Any]:
    """Render sidebar controls and return admin action state."""

    default_path = Path("data/sample_docs").resolve()
    controls = {
        "folder_path": str(default_path),
        "max_file_size_mb": 10,
        "load_clicked": False,
        "reindex_clicked": False,
        "clear_clicked": False,
        "view": "Chat",
    }

    with st.sidebar:
        st.subheader("Signed in")
        st.caption(user.email)
        st.caption(f"Role: {user.role}")
        st.button("Logout", on_click=logout)
        st.button("Clear chat", on_click=reset_chat)

        if user.is_admin:
            controls["view"] = st.radio("View", ["Chat", "Admin"], horizontal=True)

            st.subheader("Admin Workspace")
            controls["folder_path"] = st.text_input(
                "Local folder path",
                value=str(default_path),
            )
            controls["max_file_size_mb"] = st.number_input(
                "Max file size (MB)",
                min_value=1,
                max_value=100,
                value=10,
            )
            controls["load_clicked"] = st.button("Load document preview")
            controls["reindex_clicked"] = st.button(
                "Re-index documents",
                type="primary",
            )
            controls["clear_clicked"] = st.button("Clear index")

        st.subheader("Retrieval Settings")
        st.text_input("Collection", value=settings.qdrant_collection, disabled=True)
        st.text_input("Embedding provider", value=settings.embedding_provider, disabled=True)
        st.text_input("Embedding model", value=settings.embedding_model, disabled=True)
        st.number_input("Top K", value=settings.top_k, disabled=True)
        st.number_input("Min score", value=settings.min_score, disabled=True)

        if user.is_admin:
            render_audit_preview(settings)

    return controls


def render_admin_panel(settings: Settings) -> None:
    """Render local demo user management for administrators."""

    st.subheader("Admin")
    st.caption(
        "Manage demo user roles. The default admin account is controlled by .env."
    )

    users = [
        {
            "email": settings.admin_email.strip().lower(),
            "role": "admin",
            "source": "env_admin",
            "created_at": None,
            "updated_at": None,
        },
        *list_users(settings),
    ]
    st.dataframe(users, use_container_width=True, hide_index=True)

    with st.form("upsert_user_form"):
        st.markdown("**Add or update user**")
        email = st.text_input("User email", placeholder="finance.user@defaultemail.com")
        role = st.selectbox("Role", ROLES, index=0)
        password = st.text_input(
            "Password",
            type="password",
            help="Required for new users. Leave blank to keep an existing user's password.",
        )
        submitted = st.form_submit_button("Save user")

    if submitted:
        try:
            upsert_user(
                settings=settings,
                email=email,
                role=role,
                password=password,
            )
        except Exception as exc:
            st.error(str(exc))
        else:
            st.success(f"Saved {email.strip().lower()}.")
            st.rerun()

    with st.form("delete_user_form"):
        st.markdown("**Delete user**")
        delete_email = st.text_input("Email to delete")
        delete_submitted = st.form_submit_button("Delete user")

    if delete_submitted:
        try:
            deleted = delete_user(settings=settings, email=delete_email)
        except Exception as exc:
            st.error(str(exc))
        else:
            if deleted:
                st.success(f"Deleted {delete_email.strip().lower()}.")
                st.rerun()
            else:
                st.info("No matching local user was found.")


def render_load_preview(folder_path: str, max_file_size_mb: int) -> None:
    """Load documents and display metadata without indexing."""

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


def render_chat(user: AuthenticatedUser, settings: Settings) -> None:
    """Render chat history and handle new questions for one authenticated user."""

    st.caption(f"Current user: {user.email} | Role: {user.role}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(message.get("status", ""))
                render_warnings(message.get("warnings", []))
                render_sources(message.get("chunks", []))

    if prompt := st.chat_input("Ask indexed documents"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving accessible sources..."):
                try:
                    chunks = retrieve_chunks(prompt, user.role, settings)
                    guardrails = run_guardrails(prompt, chunks)
                    generated = generate_grounded_answer(
                        prompt,
                        chunks,
                        settings,
                        warnings=guardrails.warnings,
                    )
                    write_audit_log(
                        settings=settings,
                        user_email=user.email,
                        user_role=user.role,
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
                f"User: {user.email} | Role: {user.role} | "
                f"Status: {generated.answer_status} | "
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


st.set_page_config(page_title="Local Folder Knowledge Copilot", layout="wide")

settings = get_settings()
init_session_state()

st.title("Local Folder Knowledge Copilot")

user = current_user(settings)
if not user:
    if st.session_state.get("user_email"):
        st.warning("Your demo user no longer exists. Sign in again.")
        logout()
    render_login(settings)
    st.stop()

controls = render_sidebar(settings, user)

if user.is_admin and controls["clear_clicked"]:
    try:
        deleted = clear_index(settings)
    except Exception as exc:
        st.error(str(exc))
    else:
        if deleted:
            st.success(f"Cleared collection '{settings.qdrant_collection}'.")
        else:
            st.info(f"Collection '{settings.qdrant_collection}' did not exist.")

if user.is_admin and controls["reindex_clicked"]:
    try:
        with st.spinner("Indexing documents into Qdrant..."):
            result = index_folder(
                controls["folder_path"],
                settings=settings,
                clear_existing=True,
                max_file_size_mb=controls["max_file_size_mb"],
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

if user.is_admin and controls["load_clicked"]:
    render_load_preview(
        controls["folder_path"],
        max_file_size_mb=controls["max_file_size_mb"],
    )
elif controls["view"] == "Admin":
    render_admin_panel(settings)
else:
    if not st.session_state.messages and not controls["reindex_clicked"]:
        st.info("Ask a question after an administrator has indexed documents.")
    render_chat(user, settings)
