from pathlib import Path

from src.audit import read_recent_audit_logs, write_audit_log
from src.config import Settings
from src.retriever import RetrievedChunk


def test_write_and_read_recent_audit_logs(tmp_path: Path) -> None:
    """Audit logger should append JSONL records and read the latest entries."""

    settings = Settings(audit_log_path=tmp_path / "audit.jsonl")
    chunk = RetrievedChunk(
        text="Payment process text.",
        score=0.8,
        metadata={
            "file_name": "vendor-payment-process.md",
            "relative_path": "finance/vendor-payment-process.md",
            "chunk_index": 0,
            "sensitivity": "confidential",
        },
    )

    write_audit_log(
        settings=settings,
        user_email="finance.user@defaultemail.com",
        user_role="finance",
        query="What is the vendor payment process?",
        answer_status="answered",
        chunks=[chunk],
        warnings=["email_detected_in_context"],
    )

    records = read_recent_audit_logs(settings)

    assert len(records) == 1
    assert records[0]["user_email"] == "finance.user@defaultemail.com"
    assert records[0]["user_role"] == "finance"
    assert records[0]["retrieved_source_count"] == 1
    assert records[0]["warnings"] == ["email_detected_in_context"]
