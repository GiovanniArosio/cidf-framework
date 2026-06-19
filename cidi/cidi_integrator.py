"""
CIDI — Cyber-Interpretive Disruption Index
===========================================
Integrates TCI and IVA scores into a single composite index.
Formula: CIDI = 0.40 × TCI + 0.60 × IVA
Includes sensitivity analysis module for robustness testing.

Input:  TCI score + IVA score (floats, 0–1)
Output: CIDI score (float, 0–1) + sensitivity analysis results

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""

from __future__ import annotations
import numpy as np


def calculate_cidi(
    tci: float,
    iva: float,
    alpha: float = 0.40,
    beta: float = 0.60,
) -> float:
    """
    Compute the Cyber-Interpretive Disruption Index.

    CIDI = alpha × TCI + beta × IVA

    The asymmetric weighting (alpha=0.40, beta=0.60) reflects the
    thesis's core argument: the interpretive dimension carries greater
    analytical weight because the real impact of cyber-enabled disruptive
    events lies not in technical sophistication alone, but in the
    communicative disorder they produce.

    Args:
        tci: Technical Complexity Index score (float, 0–1).
        iva: Interpretive Void Analyzer score (float, 0–1).
        alpha: weight for TCI (default 0.40).
        beta: weight for IVA (default 0.60).

    Returns:
        CIDI score as float in [0, 1].
    """
    if not 0.0 <= tci <= 1.0:
        raise ValueError(f"TCI must be in [0, 1], got {tci}")
    if not 0.0 <= iva <= 1.0:
        raise ValueError(f"IVA must be in [0, 1], got {iva}")
    if abs(alpha + beta - 1.0) > 1e-6:
        raise ValueError(f"alpha + beta must equal 1.0, got {alpha + beta}")

    return float(alpha * tci + beta * iva)


def sensitivity_analysis(
    tci: float,
    iva: float,
    alpha_range: tuple[float, float] = (0.20, 0.60),
    steps: int = 9,
) -> dict:
    """
    Grid sweep over alpha values to test stability of CIDI scores.

    Args:
        tci: Technical Complexity Index score.
        iva: Interpretive Void Analyzer score.
        alpha_range: (min, max) range for alpha sweep.
        steps: number of steps in the sweep.

    Returns:
        dict with alpha values, corresponding CIDI scores, and
        the robustness band (min, max CIDI across the sweep).
    """
    alphas = np.linspace(alpha_range[0], alpha_range[1], steps)
    scores = []
    for a in alphas:
        b = 1.0 - a
        scores.append(calculate_cidi(tci, iva, alpha=a, beta=b))

    return {
        "alphas": alphas.tolist(),
        "cidi_scores": scores,
        "baseline_cidi": calculate_cidi(tci, iva),
        "robustness_band": (min(scores), max(scores)),
        "band_width": max(scores) - min(scores),
    }


if __name__ == "__main__":
    cases = [
        ("NotPetya",  0.580, 0.528),
        ("PAP Hack",  0.200, 0.522),
        ("Romania",   0.500, 0.360),
    ]

    print(f"{'Case':<12} {'TCI':>6} {'IVA':>6} {'CIDI':>6} {'Band':>12}")
    print("-" * 50)

    for name, tci, iva in cases:
        cidi = calculate_cidi(tci, iva)
        sa = sensitivity_analysis(tci, iva)
        band = f"{sa['robustness_band'][0]:.3f}–{sa['robustness_band'][1]:.3f}"
        print(f"{name:<12} {tci:>6.3f} {iva:>6.3f} {cidi:>6.3f} {band:>12}")
