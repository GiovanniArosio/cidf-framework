"""
Corpus Schema — Standard JSON document model
=============================================
Defines the canonical structure for corpus documents used across
the CIDF framework. Every document — institutional, mainstream,
non-institutional, or technical — is validated against this schema
before ingestion into the TCI / IVA pipelines.

Input:  raw document fields (or a dict)
Output: validated, JSON-serializable CorpusDocument

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class CorpusValidationError(ValueError):
    """Raised when a corpus document fails schema validation."""


class SourceType(str, Enum):
    """Controlled vocabulary for the provenance of a corpus document."""

    INSTITUTIONAL = "institutional"
    MAINSTREAM = "mainstream"
    NON_INSTITUTIONAL = "non_institutional"
    TECHNICAL = "technical"


# Fields that must be present and non-empty on every document.
_REQUIRED_FIELDS = ("id", "text", "source", "source_type", "date")


def _is_iso8601(value: str) -> bool:
    """Return True if ``value`` parses as an ISO 8601 date or datetime."""
    candidate = value.strip()
    # datetime.fromisoformat on Python < 3.11 does not accept a trailing 'Z'.
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


@dataclass
class CorpusDocument:
    """A single, validated corpus document.

    Fields:
        id:          unique document identifier
        text:        full document text (must be non-empty)
        source:      human-readable source name (e.g. "ENISA", "Reuters")
        source_type: one of the SourceType values
        date:        publication date as an ISO 8601 string
        url:         optional link to the original document
    """

    id: str
    text: str
    source: str
    source_type: SourceType
    date: str
    url: Optional[str] = None

    def __post_init__(self) -> None:
        # Allow construction directly from the raw string value.
        if isinstance(self.source_type, str):
            try:
                self.source_type = SourceType(self.source_type)
            except ValueError as exc:
                valid = ", ".join(t.value for t in SourceType)
                raise CorpusValidationError(
                    f"Invalid source_type {self.source_type!r}. "
                    f"Expected one of: {valid}."
                ) from exc
        self.validate()

    def validate(self) -> None:
        """Validate required fields, text content, source_type, and date.

        Raises:
            CorpusValidationError: if any check fails.
        """
        # Required string fields must be present and non-empty.
        for name in ("id", "source", "date"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CorpusValidationError(
                    f"Field '{name}' must be a non-empty string."
                )

        if not isinstance(self.text, str) or not self.text.strip():
            raise CorpusValidationError("Field 'text' must be a non-empty string.")

        if not isinstance(self.source_type, SourceType):
            valid = ", ".join(t.value for t in SourceType)
            raise CorpusValidationError(
                f"Field 'source_type' must be a SourceType (one of: {valid})."
            )

        if not _is_iso8601(self.date):
            raise CorpusValidationError(
                f"Field 'date' is not a valid ISO 8601 string: {self.date!r}"
            )

        if self.url is not None and not isinstance(self.url, str):
            raise CorpusValidationError("Field 'url' must be a string or None.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict (source_type as its string value)."""
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "source_type": self.source_type.value,
            "date": self.date,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CorpusDocument":
        """Build a CorpusDocument from a dict, validating on construction."""
        if not isinstance(data, dict):
            raise CorpusValidationError("Input must be a dictionary.")

        missing = [f for f in _REQUIRED_FIELDS if f not in data]
        if missing:
            raise CorpusValidationError(
                f"Missing required field(s): {', '.join(missing)}"
            )

        return cls(
            id=data["id"],
            text=data["text"],
            source=data["source"],
            source_type=data["source_type"],
            date=data["date"],
            url=data.get("url"),
        )
