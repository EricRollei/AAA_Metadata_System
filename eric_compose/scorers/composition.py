"""
eric_compose/scorers/composition.py - rule-based composition scorer.

Pure-Python, model-free scorer that evaluates four classical photographic
principles per candidate. Runs fast (vectorized over candidates, no per-pixel
work for most sub-scores), needs no GPU, gives the system a useful ranking
signal even with all deep scorers disabled.

The four sub-scores, each in [0, 1], combined into a final [0, 1]:

    1. Rule of thirds (weight 0.30)
       Distance from subject center (or brightness-weighted crop center) to
       the nearest "third line" intersection. Closer = higher score.

    2. Headroom (weight 0.25)
       For include-face presets: ratio of empty space above the head to
       head_height. Sweet spot ~0.30-0.50 head heights; less feels cramped,
       more feels disconnected. Triangle penalty around the optimum.
       Returns neutral 0.5 for face-exclude presets and non-pose candidates.

    3. Lead-room (weight 0.20)
       For subjects facing left/right: ratio of empty space ahead vs behind.
       >1.0 (more space ahead) = good. Returns neutral for frontal/back/none.

    4. Edge-cut sanity (weight 0.25)
       For pose-anchored candidates: penalize crops cutting at joints
       (knees, elbows, neck base). Presets try to avoid this but AR-conform
       can land cuts in awkward places.

Weights sum to 1.0; ALL ARE TUNABLE STARTING DEFAULTS, documented inline at
the top of CompositionScorer.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional
import numpy as np

from ..types import Candidate, KP, FACE_EXCLUDE_PRESETS
from ..subjects import Subject
from .base import BaseScorer


# ============================================================================
# Tunable constants for the four sub-scores. Documented and centralized here
# so a single edit changes behavior without code archaeology.
# ============================================================================

# Sub-score weights. Must be > 0 and sum to 1.0.
W_THIRDS    = 0.30   # rule-of-thirds positioning - the strongest single cue
W_HEADROOM  = 0.25   # composition convention for portraits
W_LEADROOM  = 0.20   # narrative breathing space in directional shots
W_EDGECUT   = 0.25   # avoid amputating limbs at joints

assert abs(W_THIRDS + W_HEADROOM + W_LEADROOM + W_EDGECUT - 1.0) < 1e-6, \
    "composition sub-score weights must sum to 1.0"

# Headroom optimum: empty space above head as fraction of head_height.
# 0.40 is the photographic convention for a relaxed but tight portrait;
# 0.20 starts to feel cramped, 0.70 starts to feel disconnected.
HEADROOM_OPTIMUM = 0.40
HEADROOM_TOLERANCE = 0.50   # full score within +/-50% of optimum, decays linearly

# Lead-room sweet spot: ratio of (space ahead in facing direction) /
# (space behind). 1.5 means subject sits ~60% of frame from the back-edge,
# leaving 60% of frame to look into. <1.0 is bad (looking out of frame).
LEADROOM_OPTIMUM = 1.5
LEADROOM_FALLOFF = 1.5      # how fast score drops as ratio diverges from optimum

# Edge-cut zones - keypoint indices that produce ugly cuts when the crop edge
# passes through them. We penalize candidates whose top/bottom/left/right
# edges land near these joints. Distance threshold is 0.5 * head_height.
EDGECUT_KEYPOINTS = (
    KP.NECK,         # cutting at the neck base looks like decapitation
    KP.L_ELBOW, KP.R_ELBOW,
    KP.L_KNEE,  KP.R_KNEE,
    KP.L_WRIST, KP.R_WRIST,
)
EDGECUT_THRESH_FRAC = 0.5   # fraction of head_height; closer = bigger penalty


# ============================================================================
# Helper: where is the "subject center" for thirds scoring?
# ============================================================================

def _subject_center(
    candidate: Candidate,
    subject: Optional[Subject],
    image: Optional[np.ndarray] = None,
) -> tuple[float, float]:
    """Return (cx, cy) for the candidate's salient point in absolute coords.

    Priority:
      1. Subject's eye midpoint (most natural focal point)
      2. Subject's nose
      3. Subject's body axis x at shoulder y
      4. Brightness-weighted center of the crop region
      5. Geometric center of the crop (last resort)
    """
    if subject is not None:
        if subject.has(KP.L_EYE) and subject.has(KP.R_EYE):
            cx = (subject.kp(KP.L_EYE)[0] + subject.kp(KP.R_EYE)[0]) / 2
            cy = (subject.kp(KP.L_EYE)[1] + subject.kp(KP.R_EYE)[1]) / 2
            return cx, cy
        if subject.has(KP.NOSE):
            x, y, _ = subject.kp(KP.NOSE)
            return x, y
        bx = subject.body_axis_x
        sy = subject.shoulder_y
        if bx is not None and sy is not None:
            return bx, sy

    if image is not None:
        x1, y1, x2, y2 = candidate.to_xyxy()
        roi = image[y1:y2, x1:x2]
        if roi.size > 0:
            if roi.ndim == 3:
                gray = roi.mean(axis=2)
            else:
                gray = roi
            total = gray.sum()
            if total > 1e-6:
                ys = np.arange(y1, y2, dtype=np.float32)
                xs = np.arange(x1, x2, dtype=np.float32)
                cy = float((gray.sum(axis=1) * ys).sum() / total)
                cx = float((gray.sum(axis=0) * xs).sum() / total)
                return cx, cy

    # geometric center fallback
    return (candidate.x1 + candidate.x2) / 2, (candidate.y1 + candidate.y2) / 2


# ============================================================================
# Sub-score computations
# ============================================================================

def _score_thirds(
    candidate: Candidate,
    subject: Optional[Subject],
    image: Optional[np.ndarray],
) -> float:
    """Distance of subject center from the nearest of 4 third-line crossings.

    Score = 1.0 when subject is exactly on a thirds intersection,
    decays linearly to 0.0 at the far corner of its quadrant.
    """
    cx, cy = _subject_center(candidate, subject, image)
    # convert to candidate-local fractional coords
    fx = (cx - candidate.x1) / max(1, candidate.width)
    fy = (cy - candidate.y1) / max(1, candidate.height)
    fx = np.clip(fx, 0.0, 1.0)
    fy = np.clip(fy, 0.0, 1.0)

    # four thirds intersections
    intersections = ((1/3, 1/3), (2/3, 1/3), (1/3, 2/3), (2/3, 2/3))
    min_dist = min(np.hypot(fx - ix, fy - iy) for ix, iy in intersections)
    # max possible distance from any thirds point to the farthest corner
    # is sqrt((2/3)^2 + (2/3)^2) ~ 0.943
    max_dist = np.hypot(2/3, 2/3)
    return float(1.0 - min(1.0, min_dist / max_dist))


def _score_headroom(
    candidate: Candidate,
    subject: Optional[Subject],
) -> float:
    """How well the empty space above the head matches the optimum.

    Returns 0.5 (neutral) if face-exclude preset, no head bbox, or no subject.
    """
    if subject is None:
        return 0.5
    if candidate.preset in FACE_EXCLUDE_PRESETS:
        return 0.5
    hb = subject.head_bbox
    hh = subject.head_height
    if hb is None or hh is None or hh <= 0:
        return 0.5

    head_top_y = hb[1]
    space_above = head_top_y - candidate.y1
    if space_above < 0:
        return 0.0   # head is above the crop entirely - shouldn't happen but defend
    ratio = space_above / hh

    # Triangle penalty around HEADROOM_OPTIMUM with HEADROOM_TOLERANCE width.
    # Score 1.0 at optimum, linearly decreases to 0.0 at +/-tolerance.
    diff = abs(ratio - HEADROOM_OPTIMUM)
    if diff > HEADROOM_TOLERANCE:
        return 0.0
    return float(1.0 - diff / HEADROOM_TOLERANCE)


def _score_leadroom(
    candidate: Candidate,
    subject: Optional[Subject],
) -> float:
    """Ratio of frame space ahead of subject vs behind, in facing direction.

    Returns 0.5 (neutral) for frontal / back / no-subject candidates.
    """
    if subject is None:
        return 0.5
    facing = subject.facing()
    if facing not in ("left", "right"):
        return 0.5

    bx = subject.body_axis_x
    if bx is None:
        return 0.5
    if bx < candidate.x1 or bx > candidate.x2:
        return 0.0  # subject outside crop somehow

    if facing == "left":
        # subject looks left; space ahead is to the LEFT of bx
        ahead = bx - candidate.x1
        behind = candidate.x2 - bx
    else:
        ahead = candidate.x2 - bx
        behind = bx - candidate.x1

    if behind <= 1.0:
        return 1.0   # tons of lead-room; max score
    ratio = ahead / behind
    # Score peaks at LEADROOM_OPTIMUM and decays as ratio diverges
    diff = abs(ratio - LEADROOM_OPTIMUM)
    return float(max(0.0, 1.0 - diff / LEADROOM_FALLOFF))


def _score_edgecut(
    candidate: Candidate,
    subject: Optional[Subject],
) -> float:
    """Penalize cuts near joints. Returns 1.0 if no joint cuts, else lower.

    Per joint inside the crop, we compute the distance from each crop edge
    and take the minimum. If that min-distance is < EDGECUT_THRESH_FRAC * hh,
    we penalize (closer = bigger penalty).
    """
    if subject is None:
        return 0.5
    hh = subject.head_height
    if hh is None or hh <= 0:
        return 0.5
    threshold = EDGECUT_THRESH_FRAC * hh

    x1, y1, x2, y2 = candidate.x1, candidate.y1, candidate.x2, candidate.y2
    penalty = 0.0
    n_joints_evaluated = 0

    for kp_idx in EDGECUT_KEYPOINTS:
        if not subject.has(kp_idx):
            continue
        kx, ky, _ = subject.kp(kp_idx)
        if kx < x1 or kx > x2 or ky < y1 or ky > y2:
            continue   # joint not inside this crop, can't be cut by an edge

        # distance to nearest edge
        d_left  = kx - x1
        d_right = x2 - kx
        d_top   = ky - y1
        d_bot   = y2 - ky
        min_d = min(d_left, d_right, d_top, d_bot)
        n_joints_evaluated += 1

        if min_d < threshold:
            # linearly proportional penalty: closer to edge = larger penalty
            joint_penalty = 1.0 - (min_d / threshold)
            penalty = max(penalty, joint_penalty)

    if n_joints_evaluated == 0:
        return 0.5  # no info, neutral
    return float(1.0 - penalty)


# ============================================================================
# Public scorer
# ============================================================================

class CompositionScorer(BaseScorer):
    """Rule-based composition scorer.

    Construct without arguments for default behavior. Pass `subject` at
    construction time OR per-call via score_batch_with_subject; latter is
    used by the pipeline (different subjects per image batch in future).
    """
    name: str = "composition"
    needs_gpu: bool = False

    def __init__(self, subject: Optional[Subject] = None):
        self._subject = subject

    def set_subject(self, subject: Optional[Subject]) -> None:
        """Update the reference subject. Called by pipeline before scoring."""
        self._subject = subject

    def score_batch(
        self,
        image: np.ndarray,
        candidates: list[Candidate],
    ) -> np.ndarray:
        """Score every candidate. Returns shape (N,) float in [0, 1]."""
        if not candidates:
            return np.zeros((0,), dtype=np.float32)
        subj = self._subject
        scores = np.empty(len(candidates), dtype=np.float32)
        for i, c in enumerate(candidates):
            s_thirds = _score_thirds(c, subj, image)
            s_head   = _score_headroom(c, subj)
            s_lead   = _score_leadroom(c, subj)
            s_edge   = _score_edgecut(c, subj)
            scores[i] = (W_THIRDS   * s_thirds +
                         W_HEADROOM * s_head   +
                         W_LEADROOM * s_lead   +
                         W_EDGECUT  * s_edge)
        return scores
