"""
Corpus Schema — Canonical document model + repository adapter
=============================================================
Defines the canonical structure for corpus documents used across
the CIDF framework and a non-destructive adapter that accepts the
repository-native field names without rewriting the raw JSON files.

Repository-native documents use ``doc_id`` / ``source_name``; the
canonical model uses ``id`` / ``source``. Both are accepted through
:func:`normalize_raw_document` / :meth:`CorpusDocument.from_dict`,
which preserve the original payload (``raw``) and surface unsupported
fields rather than discarding or rewriting them.

This module also defines the controlled vocabularies for the manual
attribution coding workflow (see ``docs/attribution_coding_protocol.md``)
and validates the cross-field coding rules.

Input:  raw document fields (or a dict, in either naming convention)
Output: validated, JSON-serializable CorpusDocument

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


# ---------------------------------------------------------------------------
# Attribution coding controlled vocabularies
# (see docs/attribution_coding_protocol.md)
# ---------------------------------------------------------------------------
class AttributionState(str, Enum):
    ATTRIBUTED = "attributed"
    UNCERTAIN = "uncertain"
    NO_CLAIM = "no_claim"
    DENIAL = "denial"


class AttributionActor(str, Enum):
    RUSSIA = "russia"
    CHINA = "china"
    BELARUS = "belarus"
    IRAN = "iran"
    NORTH_KOREA = "north_korea"
    CRIMINAL = "criminal"
    OTHER_STATE = "other_state"
    UNKNOWN = "unknown"
    NONE = "none"


class AttributionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class AttributionBasis(str, Enum):
    OFFICIAL_ATTRIBUTION = "official_attribution"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    INVESTIGATIVE_REPORTING = "investigative_reporting"
    PUBLIC_SPECULATION = "public_speculation"
    NO_CLAIM = "no_claim"


ATTRIBUTION_FIELDS = (
    "attribution_state",
    "attribution_actor",
    "attribution_confidence",
    "attribution_basis",
    "attribution_coding_note",
)

# Canonical fields the adapter understands. Repository-native aliases are
# accepted on input; the original payload is preserved untouched in ``raw``.
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "doc_id"),
    "source": ("source", "source_name"),
}

# Fields that must be resolvable (directly or via alias) on every document.
_REQUIRED_CANONICAL = ("id", "text", "source", "source_type", "date")

# Recognised non-canonical fields that are valid repository metadata and must
# not be flagged as "unsupported" by the validator.
_KNOWN_EXTRA_FIELDS = frozenset(
    {"case", "doc_id", "source_name"} | set(ATTRIBUTION_FIELDS)
)


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


def _resolve_alias(data: dict[str, Any], canonical: str) -> Optional[Any]:
    """Return the value for ``canonical`` looking through known aliases."""
    for key in _FIELD_ALIASES.get(canonical, (canonical,)):
        if key in data:
            return data[key]
    return None


def normalize_raw_document(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a repository-native (or canonical) dict to canonical keys.

    This does **not** mutate or rewrite the source file. It returns a new
    dict with canonical keys resolved through aliases, leaving the original
    payload reachable via the ``raw`` key.

    Raises:
        CorpusValidationError: if a required field has no canonical equivalent.
    """
    if not isinstance(data, dict):
        raise CorpusValidationError("Input must be a dictionary.")

    normalized: dict[str, Any] = {}
    missing = []
    for canonical in _REQUIRED_CANONICAL:
        value = _resolve_alias(data, canonical)
        if value is None:
            missing.append(canonical)
        else:
            normalized[canonical] = value
    if missing:
        aliases = {m: _FIELD_ALIASES.get(m, (m,)) for m in missing}
        raise CorpusValidationError(
            "Missing required field(s) with no canonical equivalent: "
            + ", ".join(f"{m} (accepted: {'/'.join(aliases[m])})" for m in missing)
        )

    normalized["url"] = data.get("url")
    return normalized


def unsupported_fields(data: dict[str, Any]) -> list[str]:
    """Return keys that are neither canonical, a known alias, nor known extra.

    Used by the validator to *flag* (not reject) unexpected fields so that
    schema drift is visible without forcing a destructive migration.
    """
    allowed = set(_REQUIRED_CANONICAL) | {"url"} | _KNOWN_EXTRA_FIELDS
    for aliases in _FIELD_ALIASES.values():
        allowed |= set(aliases)
    return sorted(k for k in data if k not in allowed)


@dataclass
class CorpusDocument:
    """A single, validated corpus document (canonical view).

    The canonical fields (``id``, ``source``) are populated through the
    adapter, so a repository-native ``doc_id`` / ``source_name`` document
    validates without being rewritten on disk. The untouched original
    payload is kept in ``raw``.
    """

    id: str
    text: str
    source: str
    source_type: SourceType
    date: str
    url: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
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
        """Validate required fields, text content, source_type, and date."""
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

    # -- attribution coding ------------------------------------------------
    def has_attribution_coding(self) -> bool:
        """True if all five attribution fields are present in the raw payload."""
        return all(f in self.raw for f in ATTRIBUTION_FIELDS)

    def validate_attribution_coding(self) -> None:
        """Validate the manual attribution coding fields and cross-field rules.

        Raises:
            CorpusValidationError: if coding is absent, malformed, or violates
                the protocol's cross-field consistency rules.
        """
        missing = [f for f in ATTRIBUTION_FIELDS if f not in self.raw]
        if missing:
            raise CorpusValidationError(
                f"Document {self.id}: missing attribution field(s): "
                f"{', '.join(missing)}"
            )
        validate_attribution_payload(self.raw, doc_id=self.id)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable canonical dict."""
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
        """Build a CorpusDocument from a canonical *or* repository-native dict.

        The adapter resolves ``doc_id`` -> ``id`` and ``source_name`` ->
        ``source`` without modifying the input. The original dict is stored
        on ``raw`` so downstream code can still read repository metadata such
        as ``case`` or the attribution coding fields.
        """
        normalized = normalize_raw_document(data)
        return cls(
            id=normalized["id"],
            text=normalized["text"],
            source=normalized["source"],
            source_type=normalized["source_type"],
            date=normalized["date"],
            url=normalized.get("url"),
            raw=dict(data),
        )


def validate_attribution_payload(
    payload: dict[str, Any], doc_id: str = "<unknown>"
) -> None:
    """Validate a raw attribution coding payload against the protocol rules.

    Enforces the controlled vocabularies and the cross-field consistency
    rules defined in ``docs/attribution_coding_protocol.md``:

    * ``no_claim``  -> actor ``none``, confidence ``none``, basis ``no_claim``
    * actor ``none``    only allowed when state is ``no_claim``
    * actor ``unknown`` only allowed when there *is* a claim
                        (state ``attributed`` / ``uncertain`` / ``denial``)
    * a non-empty coding note is mandatory

    Raises:
        CorpusValidationError: on any violation.
    """
    def _enum(value: Any, enum_cls: type[Enum], field_name: str) -> Enum:
        try:
            return enum_cls(value)
        except ValueError as exc:
            valid = ", ".join(e.value for e in enum_cls)
            raise CorpusValidationError(
                f"Document {doc_id}: invalid {field_name} {value!r}. "
                f"Expected one of: {valid}."
            ) from exc

    state = _enum(payload.get("attribution_state"), AttributionState,
                  "attribution_state")
    actor = _enum(payload.get("attribution_actor"), AttributionActor,
                  "attribution_actor")
    confidence = _enum(payload.get("attribution_confidence"),
                       AttributionConfidence, "attribution_confidence")
    basis = _enum(payload.get("attribution_basis"), AttributionBasis,
                  "attribution_basis")

    note = payload.get("attribution_coding_note")
    if not isinstance(note, str) or not note.strip():
        raise CorpusValidationError(
            f"Document {doc_id}: attribution_coding_note must be a non-empty "
            "string referencing the stored corpus text."
        )

    # Cross-field consistency rules.
    if state is AttributionState.NO_CLAIM:
        if actor is not AttributionActor.NONE:
            raise CorpusValidationError(
                f"Document {doc_id}: state 'no_claim' requires actor 'none', "
                f"got {actor.value!r}."
            )
        if confidence is not AttributionConfidence.NONE:
            raise CorpusValidationError(
                f"Document {doc_id}: state 'no_claim' requires confidence "
                f"'none', got {confidence.value!r}."
            )
        if basis is not AttributionBasis.NO_CLAIM:
            raise CorpusValidationError(
                f"Document {doc_id}: state 'no_claim' requires basis "
                f"'no_claim', got {basis.value!r}."
            )
    else:
        if actor is AttributionActor.NONE:
            raise CorpusValidationError(
                f"Document {doc_id}: actor 'none' is only valid when state is "
                f"'no_claim' (state is {state.value!r})."
            )
        if basis is AttributionBasis.NO_CLAIM:
            raise CorpusValidationError(
                f"Document {doc_id}: basis 'no_claim' is only valid when state "
                f"is 'no_claim' (state is {state.value!r})."
            )

    if actor is AttributionActor.UNKNOWN and state is AttributionState.NO_CLAIM:
        raise CorpusValidationError(
            f"Document {doc_id}: actor 'unknown' requires an attribution-related "
            "claim; it cannot co-occur with state 'no_claim'."
        )
