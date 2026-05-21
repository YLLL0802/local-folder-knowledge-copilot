from src.config import Settings
from src.generator import generate_grounded_answer
from src.retriever import RetrievedChunk


def test_generate_grounded_answer_refuses_without_sources() -> None:
    """Generator should refuse when retrieval returns no accessible evidence."""

    answer = generate_grounded_answer("question", [], Settings())

    assert answer.answer_status == "no_evidence"
    assert "do not contain enough accessible evidence" in answer.answer


def test_generate_grounded_answer_uses_extractive_fallback_without_llm() -> None:
    """Generator should produce a local grounded answer when LLM config is absent."""

    chunk = RetrievedChunk(
        text="Vendor invoices require a valid purchase order.",
        score=0.8,
        metadata={"file_name": "vendor-payment-process.md", "chunk_index": 0},
    )

    answer = generate_grounded_answer("What is required?", [chunk], Settings())

    assert answer.answer_status == "answered_without_llm"
    assert "Vendor invoices require" in answer.answer
    assert "[source: vendor-payment-process.md, chunk 0]" in answer.answer
