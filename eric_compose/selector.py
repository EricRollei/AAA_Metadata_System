"""
eric_compose/selector.py - geometry, AR conforming, validation, NMS.

Pure functions consumed by the candidate generators and the pipeline. No model
loading, no torch beyond NMS. Boxes are passed as (x1, y1, x2, y2) tuples of
floats during computation; rounded to ints when materialized as Candidates.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import torch
from torchvision.ops import nms as tv_nms

from .types import Candidate, ScoredCandidate


Box = tuple[float, float, float, float]   # x1, y1, x2, y2


# --- geometry primitives ----------------------------------------------------

def box_area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def iou(a: Box, b: Box) -> float:
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    return inter / (box_area(a) + box_area(b) - inter)


def contains(outer: Box, inner: Box, tol: float = 1.0) -> bool:
    """True iff outer fully contains inner (with float tolerance)."""
    return (outer[0] <= inner[0] + tol and outer[1] <= inner[1] + tol and
            outer[2] >= inner[2] - tol and outer[3] >= inner[3] - tol)


def round_box(b: Box) -> tuple[int, int, int, int]:
    return (int(round(b[0])), int(round(b[1])),
            int(round(b[2])), int(round(b[3])))


# --- AR conforming ----------------------------------------------------------

def expand_to_ar(
    box: Box,
    target_ar: float,
    image_size: tuple[int, int],
    must_include: Optional[Box] = None,
) -> Optional[Box]:
    """Grow box to match target_ar by expanding the smaller dimension.

    Never shrinks the box, so must_include is preserved. If expanding hits an
    image edge, shifts the expansion to the other side. Returns None if the
    target AR cannot be reached within image bounds while preserving
    must_include.

    image_size is (W, H). target_ar is w/h.
    """
    W, H = image_size
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    cur_ar = w / h
    if abs(cur_ar - target_ar) < 0.005:
        return box

    if cur_ar < target_ar:
        # too tall -> widen
        new_w = h * target_ar
        delta = (new_w - w) / 2
        nx1, nx2 = x1 - delta, x2 + delta
        if nx1 < 0:
            nx2 += -nx1
            nx1 = 0
        if nx2 > W:
            nx1 -= (nx2 - W)
            nx2 = W
            if nx1 < 0:
                return None
        out = (nx1, y1, nx2, y2)
    else:
        # too wide -> heighten
        new_h = w / target_ar
        delta = (new_h - h) / 2
        ny1, ny2 = y1 - delta, y2 + delta
        if ny1 < 0:
            ny2 += -ny1
            ny1 = 0
        if ny2 > H:
            ny1 -= (ny2 - H)
            ny2 = H
            if ny1 < 0:
                return None
        out = (x1, ny1, x2, ny2)

    if must_include is not None and not contains(out, must_include):
        return None
    return out


def clip_to_bounds(box: Box, image_size: tuple[int, int]) -> Box:
    W, H = image_size
    return (max(0.0, box[0]), max(0.0, box[1]),
            min(float(W), box[2]), min(float(H), box[3]))


# --- validation -------------------------------------------------------------

def face_excluded(
    box: Box,
    face_keypoints: Optional[np.ndarray],
    body_keypoints: Optional[np.ndarray] = None,
    min_conf: float = 0.3,
) -> bool:
    """True iff no face keypoint with conf > min_conf falls inside box.

    Checks face_keypoints (70 landmarks) when available, otherwise falls back
    to the four facial points in body_keypoints (eyes + ears). Either source
    being clean is sufficient.
    """
    x1, y1, x2, y2 = box
    if face_keypoints is not None and len(face_keypoints) > 0:
        for x, y, c in face_keypoints:
            if c >= min_conf and x1 <= x <= x2 and y1 <= y <= y2:
                return False
        return True
    if body_keypoints is not None:
        # body indices 14..17 are eyes / ears; nose (0) excluded since it can
        # be just outside the head area in extreme angles
        for idx in (14, 15, 16, 17):
            x, y, c = body_keypoints[idx]
            if c >= min_conf and x1 <= x <= x2 and y1 <= y <= y2:
                return False
    return True


def mask_excluded(
    box: Box,
    mask: Optional[np.ndarray],
    overlap_thresh: float = 0.0,
) -> bool:
    """True iff box's overlap with mask is at or below overlap_thresh.

    Used to enforce exclusion regions (text overlays, watermarks, logos,
    or any user-painted "stay out of here" mask). overlap_thresh is the
    maximum acceptable fraction of crop pixels that fall on non-zero mask
    pixels:

        0.0  -> any overlap rejects the candidate (strict)
        0.05 -> allow up to 5% overlap (lenient; tolerates edge watermarks)
        1.0  -> mask ignored entirely (feature off)

    mask is HxW with non-zero where exclusion is required. None = no mask,
    all candidates pass. Out-of-bounds clipping is handled defensively
    rather than raising.
    """
    if mask is None or overlap_thresh >= 1.0:
        return True
    x1, y1, x2, y2 = (int(round(v)) for v in box)
    H, W = mask.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(W, x2); y2 = min(H, y2)
    if x2 <= x1 or y2 <= y1:
        return True   # degenerate; size-sanity rejects elsewhere
    region = mask[y1:y2, x1:x2]
    if region.size == 0:
        return True
    overlap_frac = float(np.count_nonzero(region)) / region.size
    return overlap_frac <= overlap_thresh


def passes_size_bounds(
    box: Box,
    image_size: tuple[int, int],
    min_area_frac: float = 0.05,
    max_area_frac: float = 0.99,
    min_dim_px: int = 64,
) -> bool:
    """Size sanity: not too small, not the whole image, not degenerate."""
    W, H = image_size
    img_area = W * H
    a = box_area(box)
    if a / img_area < min_area_frac or a / img_area > max_area_frac:
        return False
    if (box[2] - box[0]) < min_dim_px or (box[3] - box[1]) < min_dim_px:
        return False
    return True


# --- NMS / top-K ------------------------------------------------------------

def nms_candidates(
    scored: list[ScoredCandidate],
    iou_thresh: float = 0.7,
) -> list[ScoredCandidate]:
    """Drop near-duplicate candidates. Highest-scored survives each cluster.

    Uses torchvision.ops.nms internally (fast, on CPU since N is small).
    """
    if len(scored) <= 1:
        return list(scored)
    boxes = torch.tensor(
        [sc.candidate.to_xyxy() for sc in scored], dtype=torch.float32)
    scores = torch.tensor(
        [sc.report.final for sc in scored], dtype=torch.float32)
    keep = tv_nms(boxes, scores, iou_thresh)
    return [scored[i] for i in keep.tolist()]


def topk_after_nms(
    scored: list[ScoredCandidate],
    k: int,
    iou_thresh: float = 0.7,
) -> list[ScoredCandidate]:
    """NMS, then take top-k by final score."""
    deduped = nms_candidates(scored, iou_thresh)
    deduped.sort(key=lambda sc: sc.report.final, reverse=True)
    return deduped[:k]


# --- Candidate finalization helpers ----------------------------------------

def finalize_candidate(
    box: Box,
    image_size: tuple[int, int],
    target_ar: float,
    source: str,
    must_include: Optional[Box] = None,
    person_index: Optional[int] = None,
    preset: Optional[str] = None,
) -> Optional[Candidate]:
    """End-of-pipeline: expand to AR, clip, validate, materialize Candidate.

    Returns None if the box can't satisfy the AR within bounds while preserving
    must_include, or fails size sanity. Caller handles None by skipping.
    """
    expanded = expand_to_ar(box, target_ar, image_size, must_include)
    if expanded is None:
        return None
    clipped = clip_to_bounds(expanded, image_size)
    if not passes_size_bounds(clipped, image_size):
        return None
    if must_include is not None and not contains(clipped, must_include):
        return None

    rx1, ry1, rx2, ry2 = round_box(clipped)
    if rx2 - rx1 < 1 or ry2 - ry1 < 1:
        return None
    mi = round_box(must_include) if must_include is not None else None
    return Candidate(
        x1=rx1, y1=ry1, x2=rx2, y2=ry2,
        source=source,
        aspect_ratio=(rx2 - rx1) / max(1, (ry2 - ry1)),
        person_index=person_index,
        preset=preset,
        must_include=mi,
    )
