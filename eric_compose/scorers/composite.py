"""
eric_compose/scorers/composite.py - weighted multi-scorer combiner.

Wraps multiple Scorer instances, runs each, normalizes, combines with
user-supplied weights. Stores per-scorer raw and normalized scores on
ScoreReport for inspection.

Normalization: min-max within each batch. This is intentional rather than
absolute - it makes scorers with different output ranges (GAIC ~0.2-0.8,
CACNet ~0.3-0.9, composition 0-1) directly comparable in the combined score.
The downside is that absolute scores aren't comparable across runs; for
that, use the raw `by_scorer` values from ScoreReport.

Edge cases handled:
  - Empty candidate list: returns empty list
  - Single scorer: skips normalization (raw score = normalized score)
  - Scorer returns single unique value: treated as 0.5 contribution to all
    candidates, noted in ScoreReport.notes for debugging
  - Scorer returns NaN: replaced with 0.0 + noted

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional, Mapping
import numpy as np

from ..types import Candidate, ScoreReport, ScoredCandidate, Scorer
from .base import BaseScorer


class CompositeScorer:
    """Combine multiple scorers with weighted, normalized scores.

    Unlike individual scorers, CompositeScorer produces ScoredCandidate
    objects (candidate + report) rather than a bare numpy array. This is
    where raw scores meet metadata.

    Args:
        scorers: list of Scorer instances. Order is preserved in reports.
        weights: dict {scorer_name: weight}. Missing entries default to 1.0;
                 weights are normalized to sum to 1.0 internally so callers
                 can pass any positive numbers.

    Usage:
        comp = CompositeScorer(
            scorers=[gaic, cacnet, composition],
            weights={"gaic": 1.0, "cacnet": 1.0, "composition": 0.5},
        )
        comp.warmup(device="cuda")
        scored = comp.score(image, candidates)   # list[ScoredCandidate]
    """

    def __init__(
        self,
        scorers: list[Scorer],
        weights: Optional[Mapping[str, float]] = None,
    ):
        if not scorers:
            raise ValueError("CompositeScorer requires at least one scorer")
        self.scorers = list(scorers)
        self._weights = dict(weights) if weights else {}
        # Default missing weights to 1.0; normalize sum to 1.0 internally.
        self._normalized_weights = self._compute_normalized_weights()

    def _compute_normalized_weights(self) -> dict[str, float]:
        raw = {s.name: float(self._weights.get(s.name, 1.0)) for s in self.scorers}
        total = sum(max(0.0, w) for w in raw.values())
        if total <= 0:
            # Degenerate: all weights zero. Equal weighting instead of NaN.
            return {name: 1.0 / len(raw) for name in raw}
        return {name: max(0.0, w) / total for name, w in raw.items()}

    def update_weights(self, weights: Mapping[str, float]) -> None:
        """Hot-update weights without rebuilding scorers."""
        self._weights = dict(weights)
        self._normalized_weights = self._compute_normalized_weights()

    @property
    def normalized_weights(self) -> dict[str, float]:
        return dict(self._normalized_weights)

    # --- model lifecycle ----------------------------------------------------

    def warmup(self, device: str) -> None:
        """Warmup each underlying scorer. CPU-only scorers warm first so GPU
        ones don't hold memory longer than necessary."""
        for s in sorted(self.scorers, key=lambda x: x.needs_gpu):
            s.warmup(device)

    def unload(self) -> None:
        for s in self.scorers:
            s.unload()

    # --- scoring ------------------------------------------------------------

    def score(
        self,
        image: np.ndarray,
        candidates: list[Candidate],
    ) -> list[ScoredCandidate]:
        """Score every candidate via every scorer, combine, return reports."""
        if not candidates:
            return []

        n = len(candidates)
        raw_scores: dict[str, np.ndarray] = {}
        notes_per_scorer: dict[str, str] = {}

        # 1. Run each scorer.
        for s in self.scorers:
            arr = np.asarray(s.score_batch(image, candidates), dtype=np.float32)
            if arr.shape != (n,):
                # Defensive: guard against scorer bugs
                raise RuntimeError(
                    f"scorer '{s.name}' returned shape {arr.shape}, expected ({n},)"
                )
            # Replace NaN/Inf with neutral 0.0; record in notes
            mask_bad = ~np.isfinite(arr)
            if mask_bad.any():
                notes_per_scorer[s.name] = (
                    f"{int(mask_bad.sum())} non-finite values replaced with 0.0"
                )
                arr = np.where(mask_bad, 0.0, arr)
            raw_scores[s.name] = arr

        # 2. Normalize each scorer's output min-max, unless single scorer.
        normalized: dict[str, np.ndarray] = {}
        if len(self.scorers) == 1:
            sole = self.scorers[0].name
            normalized[sole] = raw_scores[sole].copy()
        else:
            for name, arr in raw_scores.items():
                lo, hi = float(arr.min()), float(arr.max())
                if hi - lo < 1e-9:
                    # All candidates got the same score from this scorer.
                    # Treat as neutral (0.5) contribution; document in notes.
                    normalized[name] = np.full_like(arr, 0.5, dtype=np.float32)
                    notes_per_scorer[name] = (
                        notes_per_scorer.get(name, "")
                        + f" all-equal raw={lo:.4f}, normalized to 0.5"
                    ).strip()
                else:
                    normalized[name] = (arr - lo) / (hi - lo)

        # 3. Combine into final scores.
        weights = self._normalized_weights
        final = np.zeros(n, dtype=np.float32)
        for name, norm in normalized.items():
            w = weights.get(name, 0.0)
            final += w * norm

        # 4. Build reports.
        reports: list[ScoredCandidate] = []
        for i, c in enumerate(candidates):
            by_scorer = {name: float(raw_scores[name][i]) for name in raw_scores}
            norm_dict = {name: float(normalized[name][i]) for name in normalized}
            notes = {name: msg for name, msg in notes_per_scorer.items() if msg}
            report = ScoreReport(
                final=float(final[i]),
                by_scorer=by_scorer,
                normalized=norm_dict,
                notes=notes,
            )
            reports.append(ScoredCandidate(candidate=c, report=report))
        return reports
