"""
eric_compose/scorers/base.py - Scorer base class.

The Scorer protocol itself is declared in eric_compose.types so that downstream
typing checks work without importing the scorers subpackage. This module just
provides a convenience BaseScorer class with no-op warmup/unload, since most
trivial scorers don't need either.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
import numpy as np

from ..types import Candidate


class BaseScorer:
    """Convenience base class. Scorers that don't need warmup / unload (i.e.
    the composition scorer, the composite combiner) inherit from this rather
    than implement no-op stubs themselves."""
    name: str = "base"
    needs_gpu: bool = False

    def warmup(self, device: str) -> None:
        """No-op for model-free scorers."""
        pass

    def score_batch(self, image: np.ndarray, candidates: list[Candidate]) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement score_batch")

    def unload(self) -> None:
        """No-op for model-free scorers."""
        pass
