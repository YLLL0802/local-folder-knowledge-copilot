import json

from src.retriever import _payload_text, _role_filter


def test_payload_text_reads_llama_index_node_content() -> None:
    """Retriever should extract source text from LlamaIndex Qdrant payloads."""

    payload = {"_node_content": json.dumps({"text": "Source chunk text"})}

    assert _payload_text(payload) == "Source chunk text"


def test_role_filter_is_skipped_for_admin() -> None:
    """Admins should not receive a restrictive Qdrant role filter."""

    assert _role_filter("admin") is None


def test_role_filter_targets_allowed_roles_for_non_admin() -> None:
    """Non-admin retrieval should filter Qdrant payloads by allowed_roles."""

    role_filter = _role_filter("finance")

    assert role_filter is not None
    assert role_filter.must[0].key == "allowed_roles"
    assert role_filter.must[0].match.value == "finance"
