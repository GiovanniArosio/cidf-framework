"""
IVA Module 3 — Technical-Public Gap
=====================================
Quantifies the semantic distance between expert and
public discourse using sentence-transformers.
Computes: cosine distance between corpus centroids,
Jaccard lexical distance, complexity differential.

Input:  technical corpus + public corpus (JSON)
Output: technical-public gap score (float, 0–1)

Part of the CIDF framework — LUISS Guido Carli, 2026
Author: Giovanni Arosio
"""
