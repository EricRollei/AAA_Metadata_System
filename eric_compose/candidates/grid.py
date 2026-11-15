"""
eric_compose/candidates/grid.py - GAIC-style anchor grid candidates.

Generates a list of candidate crops by sliding rectangles of varying size
across a grid laid over the source image. AR-prefiltered: only emits crops
within +/- ar_tolerance of any target AR. No model required; pure geometry.

This is the fallback / generalist generator:
  - Used when no DWPose subject is present (non-person photos, landscapes,
    products, art reproductions).
  - Used alongside pose-anchored candidates when the user picks "auto" preset
    so the final ranked list includes both subject-tight and content-driven
    options.

Reference: GAIC (Zeng et al., CVPR 2019 / TPAMI 2020) used a 4x4 to 6x6
anchor grid with up to ~90 candidates per image. Here we expose the grid
size and per-cell span as parameters so callers can tune density/cost.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional

from ..types import Candidate
from ..selector import finalize_candidate


# ============================================================================
# Defaults - tunable constants
#
# grid_size:        N x N grid of anchor points across the image. 5 yields
#                   25 anchor positions; combined with the cell-span sweep
#                   below this produces several hundred raw candidates per
#                   image, of which AR filtering keeps a manageable subset.
# cell_spans:       crop sizes in (cells_w, cells_h). Each tuple defines one
#                   crop size to slide across the grid. Mix of square,
#                   landscape, and portrait sizes so AR prefilter has options
#                   to match against.
# ar_tolerance:     fractional tolerance for AR matching. 0.05 = within 5%
#                   of target AR. Tighter (0.02) drops too many candidates
#                   on small images; looser (0.10) lets the AR conformer do
#                   more work and produces more near-duplicates after NMS.
# ============================================================================

DEFAULT_GRID_SIZE: int = 5

DEFAULT_CELL_SPANS: tuple[tuple[int, int], ...] = (
    # square-ish
    (3, 3), (4, 4),
    # landscape (wider than tall)
    (4, 3), (5, 3), (5, 4),
    # portrait (taller than wide)
    (3, 4), (3, 5), (4, 5),
)

DEFAULT_AR_TOLERANCE: float = 0.05

DEFAULT_MIN_AREA_FRAC: float = 0.20  # don't bother with tiny grid crops


# ============================================================================
# Public API
# ============================================================================

def generate_grid_candidates(
    image_size: tuple[int, int],
    aspect_ratios: list[float],
    grid_size: int = DEFAULT_GRID_SIZE,
    cell_spans: Optional[tuple[tuple[int, int], ...]] = None,
    ar_tolerance: float = DEFAULT_AR_TOLERANCE,
    min_area_frac: float = DEFAULT_MIN_AREA_FRAC,
) -> list[Candidate]:
    """Generate grid-anchored candidates AR-filtered to allowed ratios.

    Args:
        image_size:    (W, H) source image dimensions
        aspect_ratios: list of target ARs (w/h). Empty list = no AR filter
                       (every candidate accepted, AR conformer becomes the
                       only AR control).
        grid_size:     N for an N x N grid of anchor positions
        cell_spans:    list of (cells_w, cells_h) crop sizes to try.
                       Defaults to a balanced mix of square / landscape /
                       portrait spans (see DEFAULT_CELL_SPANS).
        ar_tolerance:  fractional tolerance when matching candidate AR to a
                       target AR. Candidates outside tolerance for ALL targets
                       are skipped.
        min_area_frac: minimum candidate area as fraction of image area.
                       Filters out spans that produce tiny crops on small
                       images.

    Returns:
        list of Candidate. Each candidate has source = "grid:NxM:cWxcH" for
        debugging.
    """
    W, H = image_size
    if cell_spans is None:
        cell_spans = DEFAULT_CELL_SPANS

    cell_w = W / grid_size
    cell_h = H / grid_size
    img_area = W * H

    candidates: list[Candidate] = []

    for span_w_cells, span_h_cells in cell_spans:
        if span_w_cells > grid_size or span_h_cells > grid_size:
            continue
        crop_w = cell_w * span_w_cells
        crop_h = cell_h * span_h_cells
        if crop_w <= 0 or crop_h <= 0:
            continue
        # area filter
        if (crop_w * crop_h) / img_area < min_area_frac:
            continue
        candidate_ar = crop_w / crop_h

        # AR prefilter: skip if no target AR is within tolerance
        if aspect_ratios:
            best_ar = None
            best_diff = float("inf")
            for tar in aspect_ratios:
                if tar <= 0:
                    continue
                diff = abs(candidate_ar / tar - 1.0)
                if diff < best_diff:
                    best_diff = diff
                    best_ar = tar
            if best_ar is None or best_diff > ar_tolerance:
                continue
            target_ar = best_ar
        else:
            target_ar = candidate_ar

        # slide across grid
        max_x_anchor = grid_size - span_w_cells
        max_y_anchor = grid_size - span_h_cells
        for ai in range(max_x_anchor + 1):
            for aj in range(max_y_anchor + 1):
                x1 = ai * cell_w
                y1 = aj * cell_h
                x2 = x1 + crop_w
                y2 = y1 + crop_h
                box = (x1, y1, x2, y2)

                source_str = (f"grid:{grid_size}x{grid_size}"
                              f":{span_w_cells}x{span_h_cells}"
                              f":a{ai}_{aj}")
                cand = finalize_candidate(
                    box=box,
                    image_size=image_size,
                    target_ar=target_ar,
                    source=source_str,
                    must_include=None,
                    person_index=None,
                    preset=None,
                )
                if cand is not None:
                    candidates.append(cand)

    return candidates
