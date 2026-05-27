"""
IVA Module 1 — Attribution Drift
==================================
Measures the instability of responsibility claims over time.
Uses LLM-assisted extraction to identify attribution claims
and computes: actor plurality, temporal instability,
convergence delay, confidence dispersion.

Input:  public and technical corpus (JSON)
Output: attribution drift score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""
