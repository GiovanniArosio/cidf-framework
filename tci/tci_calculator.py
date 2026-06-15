"""
TCI — Technical Complexity Index
=================================
Measures the operational sophistication of cyber incidents
using the MITRE ATT&CK framework.

Input:  JSON document with ATT&CK technique mappings
Output: TCI score (float, 0–1)

Baseline model: an equal-weight average across five components
(tactics, techniques, stealth, persistence, lateral movement).

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations

from typing import Any

# Normalization caps for the count-based components.
MAX_TACTICS = 10
MAX_TECHNIQUES = 20

# Number of equally weighted components in the baseline TCI.
_NUM_COMPONENTS = 5

_REQUIRED_KEYS = (
    "tactics",
    "techniques",
    "stealth",
    "persistence",
    "lateral_movement",
)


class TCIValidationError(ValueError):
    """Raised when the TCI input payload is malformed."""


def _validate(incident: dict[str, Any]) -> None:
    """Validate the incident payload before scoring."""
    if not isinstance(incident, dict):
        raise TCIValidationError("Input must be a dictionary.")

    missing = [key for key in _REQUIRED_KEYS if key not in incident]
    if missing:
        raise TCIValidationError(f"Missing required key(s): {', '.join(missing)}")

    if not isinstance(incident["tactics"], list):
        raise TCIValidationError("'tactics' must be a list.")
    if not isinstance(incident["techniques"], list):
        raise TCIValidationError("'techniques' must be a list.")

    stealth = incident["stealth"]
    # bool is a subclass of int — reject it explicitly so True/False is not
    # silently treated as a stealth level.
    if isinstance(stealth, bool) or not isinstance(stealth, (int, float)):
        raise TCIValidationError("'stealth' must be a number between 0 and 1.")
    if not 0.0 <= float(stealth) <= 1.0:
        raise TCIValidationError("'stealth' must be between 0 and 1.")

    if not isinstance(incident["persistence"], bool):
        raise TCIValidationError("'persistence' must be a boolean.")
    if not isinstance(incident["lateral_movement"], bool):
        raise TCIValidationError("'lateral_movement' must be a boolean.")


def calculate_tci(incident: dict[str, Any]) -> float:
    """Compute the Technical Complexity Index for a single incident.

    Args:
        incident: dict with keys ``tactics`` (list), ``techniques`` (list),
            ``stealth`` (float 0–1), ``persistence`` (bool) and
            ``lateral_movement`` (bool).

    Returns:
        TCI score as a float in [0, 1] — the equal-weight average of the
        five component scores.

    Raises:
        TCIValidationError: if the payload is malformed.
    """
    _validate(incident)

    tactics_score = min(len(incident["tactics"]) / MAX_TACTICS, 1.0)
    techniques_score = min(len(incident["techniques"]) / MAX_TECHNIQUES, 1.0)
    stealth_score = float(incident["stealth"])
    persistence_score = 1.0 if incident["persistence"] else 0.0
    lateral_movement_score = 1.0 if incident["lateral_movement"] else 0.0

    return (
        tactics_score
        + techniques_score
        + stealth_score
        + persistence_score
        + lateral_movement_score
    ) / _NUM_COMPONENTS
