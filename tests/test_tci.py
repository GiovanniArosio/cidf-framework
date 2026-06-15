"""
Minimal baseline test for the TCI calculator.
==============================================
Uses a hardcoded NotPetya-style incident to verify the equal-weight
baseline scoring is wired up correctly.

Run with pytest:    pytest tests/test_tci.py
Or directly:        python tests/test_tci.py

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

import sys
from pathlib import Path

# Make the repository root importable when run directly or via pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tci.tci_calculator import calculate_tci

# NotPetya-style incident (June 2017): high-impact, self-propagating wiper.
NOTPETYA_INCIDENT = {
    "tactics": ["execution", "lateral_movement", "impact"],
    "techniques": [
        "EternalBlue",
        "supply_chain_compromise",
        "credential_dumping",
        "wiper",
    ],
    "stealth": 0.4,
    "persistence": False,
    "lateral_movement": True,
}


def test_returns_float():
    score = calculate_tci(NOTPETYA_INCIDENT)
    assert isinstance(score, float)


def test_score_within_bounds():
    score = calculate_tci(NOTPETYA_INCIDENT)
    assert 0.0 <= score <= 1.0


def test_notpetya_score_is_positive():
    score = calculate_tci(NOTPETYA_INCIDENT)
    assert score > 0.0


if __name__ == "__main__":
    result = calculate_tci(NOTPETYA_INCIDENT)
    print(f"NotPetya TCI score: {result}")
    test_returns_float()
    test_score_within_bounds()
    test_notpetya_score_is_positive()
    print("All TCI baseline tests passed.")
