"""
eric_compose/pipeline.py - end-to-end orchestrator.

Single entry point for the compose-crop pipeline. Consumed by ComfyUI nodes
and (eventually) CLI. Pure Python; no ComfyUI dependencies in this module so
it remains testable without a running ComfyUI instance.

Pipeline stages:
  1. Pose parsing      (subjects.parse_pose_keypoint)
  2. Subject selection (subjects.select_primary_subject)
  3. Candidate generation
       - Pose-anchored (when subject available)
       - Grid-anchored (when enable_grid or no subject)
       - No-crop (full image, when allow_no_crop and AR matches)
  4. Optional exclude-mask filter (text overlays, watermarks, etc.)
  5. Composite scoring (currently composition only)
  6. NMS + top-K       (selector.topk_after_nms)

Returns (best_scored_candidate, top_k_scored_list). The top-K list is for
inspection / external rerank; v1 nodes only consume the first.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional
import numpy as np

from .types import ScoredCandidate, Candidate, KP
from .subjects import parse_pose_keypoint, select_primary_subject, Subject
from .presets import PRESETS, applicable_presets
from .candidates import generate_pose_candidates, generate_grid_candidates
from .scorers import CompositionScorer, CompositeScorer
from .selector import topk_after_nms, mask_excluded


def _apply_offcenter_bonus(
    scored: list[ScoredCandidate],
    subject: Optional[Subject],
    strength: float,
) -> None:
    """Mutate ScoredCandidate.report.final in-place to reward off-center crops.

    Measures the horizontal distance of the subject (or brightness-weighted
    centroid for grid candidates) from the crop's own center line.  A subject
    sitting on a thirds line is ~0.17 frame-widths off-center; fully centered
    is 0.  The bonus is proportional to that offset, scaled by `strength`.

    Max additive bonus: 0.30 * strength (when subject is at the crop edge).
    This keeps composition scores in [0, 1] for typical usage.
    """
    if not scored or strength <= 0.0:
        return

    # Determine the subject's horizontal anchor (absolute pixel x).
    sx: Optional[float] = None
    if subject is not None:
        if subject.has(KP.L_EYE) and subject.has(KP.R_EYE):
            sx = (subject.kp(KP.L_EYE)[0] + subject.kp(KP.R_EYE)[0]) / 2.0
        elif subject.has(KP.NOSE):
            sx = float(subject.kp(KP.NOSE)[0])
        elif subject.body_axis_x is not None:
            sx = float(subject.body_axis_x)

    MAX_BONUS = 0.30
    for sc in scored:
        c = sc.candidate
        crop_cx = (c.x1 + c.x2) / 2.0
        w = max(1, c.x2 - c.x1)

        if sx is not None:
            offset_frac = abs(sx - crop_cx) / w   # 0 = centered, ~0.5 = at edge
        else:
            # No subject info: fall back to 0 (no bonus, no penalty)
            offset_frac = 0.0

        # Normalize to [0, 1]: a full-edge position gets score 1.0
        offcenter_score = min(1.0, offset_frac * 2.0)
        bonus = offcenter_score * strength * MAX_BONUS
        sc.report.final = min(1.0, sc.report.final + bonus)
        if bonus > 1e-4:
            sc.report.notes["offcenter_bonus"] = f"{bonus:.4f}"


def _add_no_crop_candidate(
    candidates: list[Candidate],
    image_size: tuple[int, int],
    aspect_ratios: list[float],
    ar_tolerance: float = 0.05,
) -> list[Candidate]:
    """Add the full image as a candidate if its AR matches the allowed set.

    Lets "no crop" compete with proposed crops on equal footing. When the
    original's composition is already good, this candidate wins on the
    composition scorer and the pipeline returns the image unchanged.
    AR check honors the user's AR constraint - returning an uncropped 16:9
    when they asked for 1:1 would violate their request.
    """
    W, H = image_size
    image_ar = W / H
    matches = any(
        abs(image_ar / ar - 1.0) <= ar_tolerance
        for ar in aspect_ratios if ar > 0
    )
    if not matches:
        return candidates
    no_crop = Candidate(
        x1=0, y1=0, x2=W, y2=H,
        source="no_crop:original",
        aspect_ratio=image_ar,
        person_index=None,
        preset=None,
        must_include=None,
    )
    return list(candidates) + [no_crop]


def compose_crop(
    image: np.ndarray,
    pose_keypoint=None,
    preset: str = "auto",
    aspect_ratios: list[float] = None,
    person_index: int = -1,
    min_kp_conf: float = 0.3,
    enable_grid: bool = True,
    nms_iou_thresh: float = 0.7,
    allow_no_crop: bool = True,
    exclude_mask: Optional[np.ndarray] = None,
    exclude_overlap_thresh: float = 0.0,
    top_k_internal: int = 10,
    offcenter_strength: float = 0.0,
    min_crop_area: float = 0.0,
) -> tuple[Optional[ScoredCandidate], list[ScoredCandidate], dict]:
    """Run the full pipeline.

    Args:
        image:          source image as HxWx3 uint8 or HxWx3 float [0, 1].
                        Internal scoring is intensity-only and tolerates
                        either; downstream callers control output dtype.
        pose_keypoint:  ComfyUI POSE_KEYPOINT or None. None -> grid only.
        preset:         "auto" tries every preset whose required keypoints
                        are visible. Otherwise a specific preset name.
        aspect_ratios:  list of allowed AR (w/h) floats. Default [1.0].
        person_index:   -1 = auto pick highest-confidence person.
                        N >= 0 = explicit selection by list index.
        min_kp_conf:    confidence threshold for keypoint visibility.
        enable_grid:    add grid candidates alongside pose-anchored ones.
                        Always-on if no usable subject (gracefully degrades).
        nms_iou_thresh: IoU above which candidates are deduped.
        allow_no_crop:  add the full image as a candidate if its AR matches
                        the allowed set. Lets "don't crop" win when the
                        original composition is already good.
        exclude_mask:   Optional HxW mask. Non-zero pixels are regions
                        candidates must avoid (text, watermarks, etc.).
                        None disables the filter.
        exclude_overlap_thresh: Max fraction of crop area allowed to overlap
                        exclude_mask. 0.0 = no overlap permitted (strictest);
                        1.0 = mask ignored. Has no effect when exclude_mask
                        is None.
        top_k_internal: how many to retain after NMS for the second return.
        min_crop_area:  minimum crop size as a fraction of the source image
                        area [0, 1]. 0.0 = no minimum (default). 0.5 means
                        the crop must cover at least 50% of the original
                        pixels. Filters ALL candidate types (pose-anchored,
                        grid, no-crop). The no-crop candidate always passes
                        since it covers 100% of the image.

    Returns:
        (best_scored, all_top_k_scored, diagnostics)
        - best_scored is None if no valid candidates could be produced
          (degenerate input image, all candidates rejected by validators,
          or all candidates filtered out by exclude_mask).
        - all_top_k_scored is sorted descending by final score; same first
          element as best_scored when not None.
        - diagnostics is a dict with candidate counts at each pipeline stage:
          candidates_generated, candidates_after_filter, candidates_after_nms.
    """
    if aspect_ratios is None:
        aspect_ratios = [1.0]

    H, W = image.shape[:2]
    image_size = (W, H)

    # --- 1. Pose parsing & subject selection ------------------------------
    subjects = parse_pose_keypoint(pose_keypoint, W, H)
    primary: Optional[Subject] = select_primary_subject(subjects, person_index)

    # --- 2. Candidate generation ------------------------------------------
    candidates: list[Candidate] = []

    if primary is not None:
        if preset == "auto":
            presets_to_try = applicable_presets(primary)
        elif preset in PRESETS:
            # Specific preset; only run if applicable to this subject.
            # If not applicable (required keypoints missing), the candidate
            # list will be empty and we fall through to grid (if enabled).
            presets_to_try = [preset] if PRESETS[preset].applicable(primary) else []
        else:
            presets_to_try = []

        if presets_to_try:
            candidates.extend(generate_pose_candidates(
                subject=primary,
                presets_to_try=presets_to_try,
                aspect_ratios=aspect_ratios,
                image_size=image_size,
                min_kp_conf=min_kp_conf,
                offcenter_strength=offcenter_strength,
            ))

    # Grid candidates: always added if no pose-anchored survived (graceful
    # fallback), otherwise added when explicitly enabled.
    if enable_grid or not candidates:
        candidates.extend(generate_grid_candidates(
            image_size=image_size,
            aspect_ratios=aspect_ratios,
        ))

    # --- 3. Optional no-crop candidate ------------------------------------
    # Lets "don't crop at all" compete with proposed crops. Subject to the
    # same AR / mask validators as everything else (added before mask filter
    # so a watermark in the original correctly excludes it).
    if allow_no_crop:
        candidates = _add_no_crop_candidate(
            candidates, image_size, aspect_ratios
        )

    n_generated = len(candidates)

    # --- 4. Optional exclude-mask filter ----------------------------------
    # Applied here so pose-anchored, grid, AND no-crop candidates are all
    # checked. Hard filter only in v1; soft-penalty mode is a v1.5 follow-up.
    if exclude_mask is not None and exclude_overlap_thresh < 1.0:
        candidates = [
            c for c in candidates
            if mask_excluded(c.to_xyxy(), exclude_mask, exclude_overlap_thresh)
        ]

    # --- 4b. Minimum crop-area filter ------------------------------------
    # Discards candidates that throw away too much of the source image.
    # Compared as fraction of original image area; no-crop always passes.
    if min_crop_area > 0.0:
        image_area = W * H
        if image_area > 0:
            candidates = [
                c for c in candidates
                if (c.width * c.height) / image_area >= min_crop_area
            ]

    n_after_filter = len(candidates)

    if not candidates:
        diag = {"candidates_generated": n_generated, "candidates_after_filter": 0, "candidates_after_nms": 0}
        return None, [], diag

    # --- 5. Scoring -------------------------------------------------------
    composition_scorer = CompositionScorer(subject=primary)
    composite = CompositeScorer(scorers=[composition_scorer])
    scored = composite.score(image, candidates)

    # --- 5b. Off-center bonus (optional) -----------------------------------
    # Rewards crops where the subject sits away from the crop center-line,
    # producing more dynamic, asymmetric framing. Strength 0.0 = no effect;
    # 1.0 = up to +0.30 additive bonus for fully edge-positioned subjects.
    _apply_offcenter_bonus(scored, primary, offcenter_strength)

    # --- 6. NMS + top-K ---------------------------------------------------
    top = topk_after_nms(scored, k=top_k_internal, iou_thresh=nms_iou_thresh)
    n_after_nms = len(top)
    diag = {
        "candidates_generated": n_generated,
        "candidates_after_filter": n_after_filter,
        "candidates_after_nms": n_after_nms,
    }
    if not top:
        return None, [], diag

    return top[0], top, diag
