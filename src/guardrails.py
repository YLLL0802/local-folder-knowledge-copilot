from __future__ import annotations

import re
from dataclasses import dataclass, field

from .retriever import RetrievedChunk


PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (the )?(system|developer|previous) prompt",
    r"reveal (the )?(hidden|system|developer) prompt",
    r"show me (all )?(hidden|restricted|confidential) documents",
    r"\bjailbreak\b",
    r"\bact as\b",
]

SENSITIVE_DATA_PATTERNS = {
    "email_detected": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "phone_detected": r"\b(?:\+?\d[\d .()/-]{7,}\d)\b",
    "api_key_like_value_detected": r"\b(?:sk|pk|api|key|token)[-_]?[A-Za-z0-9]{16,}\b",
    "secret_keyword_detected": r"\b(password|secret|token|api[_ -]?key)\b",
}


@dataclass
class GuardrailResult:
    """Warnings detected in the user query and retrieved context."""

    warnings: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        """Return true when any warning was detected."""

        return bool(self.warnings)


def run_guardrails(query: str, chunks: list[RetrievedChunk]) -> GuardrailResult:
    """Run prompt injection and sensitive-data checks for a question and context."""

    warnings: list[str] = []
    warnings.extend(_prompt_injection_warnings(query, "query"))
    warnings.extend(_sensitive_data_warnings(query, "query"))

    context = "\n\n".join(chunk.text for chunk in chunks)
    warnings.extend(_prompt_injection_warnings(context, "context"))
    warnings.extend(_sensitive_data_warnings(context, "context"))

    return GuardrailResult(warnings=_dedupe(warnings))


def _prompt_injection_warnings(text: str, location: str) -> list[str]:
    """Detect prompt-injection phrases in user input or retrieved context."""

    if not text:
        return []
    return [
        f"prompt_injection_detected_in_{location}"
        for pattern in PROMPT_INJECTION_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]


def _sensitive_data_warnings(text: str, location: str) -> list[str]:
    """Detect basic sensitive-data patterns in user input or retrieved context."""

    if not text:
        return []
    warnings = []
    for warning_name, pattern in SENSITIVE_DATA_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            warnings.append(f"{warning_name}_in_{location}")
    return warnings


def _dedupe(items: list[str]) -> list[str]:
    """Preserve warning order while removing duplicates."""

    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
