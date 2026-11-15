"""
eric_compose/scorers - candidate scoring strategies.

Scorers conform to the Scorer protocol in eric_compose.types. Each takes the
source image and a list of Candidate boxes, returns one float per candidate
(higher = better, range [0, 1] by convention).

Available scorers:
    composition.py  - rule-of-thirds, headroom, lead-room, edge-cut sanity.
                      Pure Python, no model. Always available.
    composite.py    - combines multiple scorers with per-scorer weights and
                      min-max normalization.
    gaic.py         - Grid Anchor based Image Cropping (Zeng et al. 2019/2020).
                      Requires GAIC model weights. Non-commercial license.
    cacnet.py       - Composing Photos Like a Photographer (CACNet).
                      Requires CACNet model weights. Non-commercial license.

The pose-aware composition scorer can use a Subject reference to compute
headroom, lead-room, and edge-cut penalties; without one it falls back to
brightness-centered rule-of-thirds only.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from .composition import CompositionScorer
from .composite import CompositeScorer

__all__ = ["CompositionScorer", "CompositeScorer"]
