from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .retriever import RetrievedChunk


def write_audit_log(
    settings: Settings,
    user_role: str,
    query: str,
    answer_status: str,
    chunks: list[RetrievedChunk],
    warnings: list[str],
) -> None:
    """Append one question-answer audit event to the JSONL audit log."""

    log_path = Path(settings.audit_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_role": user_role,
        "query": query,
        "answer_status": answer_status,
        "retrieved_source_count": len(chunks),
        "sources": [_source_record(chunk) for chunk in chunks],
        "warnings": warnings,
    }
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_recent_audit_logs(settings: Settings, limit: int = 5) -> list[dict[str, Any]]:
    """Read recent audit log entries for the Streamlit sidebar preview."""

    log_path = Path(settings.audit_log_path)
    if not log_path.exists():
        return []

    lines = log_path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(records))


def _source_record(chunk: RetrievedChunk) -> dict[str, Any]:
    """Convert a retrieved chunk into compact audit source metadata."""

    return {
        "file_name": chunk.metadata.get("file_name"),
        "relative_path": chunk.metadata.get("relative_path"),
        "chunk_index": chunk.metadata.get("chunk_index"),
        "score": round(chunk.score, 4),
        "sensitivity": chunk.metadata.get("sensitivity"),
    }
