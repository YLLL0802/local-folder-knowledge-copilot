from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata attached to a whole source document before chunking."""

    doc_id: str
    source_path: str
    relative_path: str
    file_name: str
    file_type: str
    modified_at: datetime
    department: str
    sensitivity: str
    allowed_roles: list[str] = Field(default_factory=list)
    checksum: str
    size_bytes: int


class LoadedDocument(BaseModel):
    """A loaded source document containing raw text plus document metadata."""

    text: str
    metadata: DocumentMetadata

    @property
    def preview(self) -> str:
        """Return a short one-line text preview for CLI and UI tables."""

        normalized = " ".join(self.text.split())
        return normalized[:280]
