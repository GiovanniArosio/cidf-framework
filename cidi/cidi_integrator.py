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
