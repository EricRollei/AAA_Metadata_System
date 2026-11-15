"""
eric_compose/subjects.py - pose parsing and per-subject body measurements.

Consumes the ComfyUI POSE_KEYPOINT format produced by DWPose / OpenPose-style
preprocessors, returns Subject instances with the derived measurements every
preset's anchor function needs (head_height, body_axis_x, ankle_y, etc.).

POSE_KEYPOINT format (from comfyui_controlnet_aux DWPose):
    [
        {
            "people": [
                {
                    "pose_keypoints_2d": [x1,y1,c1, x2,y2,c2, ...],  # 18*3 = 54 floats
                    "face_keypoints_2d": [...],         # optional, 70 keypoints
                    "hand_left_keypoints_2d":  [...],   # optional
                    "hand_right_keypoints_2d": [...],   # optional
                },
                ...
            ],
            "canvas_width":  W,
            "canvas_height": H,
        }
    ]
Coordinates are NORMALIZED to canvas_width / canvas_height. We rescale to the
target image's pixel space on parse.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal
import numpy as np

from .types import KP, KP_NAMES


# Default confidence threshold below which a keypoint is treated as missing.
# DWPose typically produces conf in [0, 1]; 0.3 is a conservative cutoff that
# rejects clearly-uncertain points without dropping borderline-visible ones.
DEFAULT_KP_CONF = 0.3


@dataclass
class Subject:
    """One person extracted from POSE_KEYPOINT, in target-image pixel space.

    keypoints is shape (18, 3) where each row is [x, y, confidence].
    face_keypoints, when present, is shape (70, 3) - used for face-exclusion
    checks in face_exclude presets.
    """
    keypoints: np.ndarray                       # (18, 3)
    image_w: int
    image_h: int
    person_index: int = 0
    face_keypoints: Optional[np.ndarray] = None # (70, 3) or None

    # --- raw keypoint access -----------------------------------------------

    def kp(self, idx: int) -> tuple[float, float, float]:
        """Return (x, y, conf) for keypoint index."""
        x, y, c = self.keypoints[idx]
        return float(x), float(y), float(c)

    def has(self, idx: int, min_conf: float = DEFAULT_KP_CONF) -> bool:
        return float(self.keypoints[idx, 2]) >= min_conf

    def has_all(self, idxs: tuple[int, ...], min_conf: float = DEFAULT_KP_CONF) -> bool:
        return all(self.has(i, min_conf) for i in idxs)

    def total_confidence(self) -> float:
        """Mean confidence across all 18 body keypoints - used for picking the
        primary person when multiple are present."""
        return float(self.keypoints[:, 2].mean())

    # --- head / face geometry ----------------------------------------------

    @property
    def head_height(self) -> Optional[float]:
        """Estimated head height in pixels.

        Uses anthropometric proportion: head_height ~ 4.5 x inter-eye distance.
        Falls back to 1.6 x |neck.y - nose.y| if eyes aren't visible.
        Returns None if neither nose nor eyes/neck are available.
        """
        if self.has(KP.L_EYE) and self.has(KP.R_EYE):
            lex, ley, _ = self.kp(KP.L_EYE)
            rex, rey, _ = self.kp(KP.R_EYE)
            eye_dist = float(np.hypot(lex - rex, ley - rey))
            if eye_dist > 1.0:                        # avoid div-by-zero / noise
                return 4.5 * eye_dist
        if self.has(KP.NOSE) and self.has(KP.NECK):
            _, ny, _ = self.kp(KP.NOSE)
            _, ncy, _ = self.kp(KP.NECK)
            return 1.6 * abs(ncy - ny)
        return None

    @property
    def head_bbox(self) -> Optional[tuple[float, float, float, float]]:
        """Tight bbox around the head as (x1, y1, x2, y2)."""
        hh = self.head_height
        if hh is None or not self.has(KP.NOSE):
            return None
        nx, ny, _ = self.kp(KP.NOSE)
        # eyes give a better x-center than nose alone (nose can be off-center
        # in 3/4 views); fall back to nose if eyes are missing.
        if self.has(KP.L_EYE) and self.has(KP.R_EYE):
            cx = (self.kp(KP.L_EYE)[0] + self.kp(KP.R_EYE)[0]) / 2
        else:
            cx = nx
        # eye line sits ~50% down the head; crown is 0.5*hh above eyes,
        # chin is 0.5*hh below.
        if self.has(KP.L_EYE) and self.has(KP.R_EYE):
            cy = (self.kp(KP.L_EYE)[1] + self.kp(KP.R_EYE)[1]) / 2
        else:
            cy = ny - 0.1 * hh                        # nose is ~10% below eyes
        # Head width ~ 0.65 * head height (typical anthropometry).
        hw = 0.65 * hh
        return (cx - hw / 2, cy - hh / 2, cx + hw / 2, cy + hh / 2)

    # --- body landmarks (y-coords) -----------------------------------------

    def _avg_y(self, l_idx: int, r_idx: int) -> Optional[float]:
        """Mean y of two paired keypoints, using whichever are visible."""
        ys = []
        if self.has(l_idx): ys.append(self.kp(l_idx)[1])
        if self.has(r_idx): ys.append(self.kp(r_idx)[1])
        return float(np.mean(ys)) if ys else None

    def _avg_x(self, l_idx: int, r_idx: int) -> Optional[float]:
        xs = []
        if self.has(l_idx): xs.append(self.kp(l_idx)[0])
        if self.has(r_idx): xs.append(self.kp(r_idx)[0])
        return float(np.mean(xs)) if xs else None

    @property
    def shoulder_y(self) -> Optional[float]:
        return self._avg_y(KP.L_SHOULDER, KP.R_SHOULDER)

    @property
    def hip_y(self) -> Optional[float]:
        return self._avg_y(KP.L_HIP, KP.R_HIP)

    @property
    def knee_y(self) -> Optional[float]:
        return self._avg_y(KP.L_KNEE, KP.R_KNEE)

    @property
    def ankle_y(self) -> Optional[float]:
        return self._avg_y(KP.L_ANKLE, KP.R_ANKLE)

    @property
    def foot_y(self) -> Optional[float]:
        """Estimated y-coordinate of foot/ground contact (bottom of shoe sole).

        DWPose's ankle keypoint marks the lateral malleolus (ankle bone). The
        distance from the ankle bone to the ground varies significantly by pose:

          - Flat standing:    ankle is ~10% of htoa above ground (shoe sole)
          - Tiptoe / relevé:  ankle rises but toe stays near ground; needs
                              ~25% of htoa to reach the original ground level
          - Pointed foot:     the toe extends below the ankle by up to ~35% of
                              shin length (foot ≈ 38% of shin anthropometrically)

        Strategy: use the larger of two estimates —
          1. 0.25 * htoa  — covers flat stance, moderate heel height, and
                            moderate tiptoe. (Raised from 0.15; extreme ballet
                            relevé may still clip slightly, but that is an
                            atypical shot that usually gets deliberate framing.)
          2. 0.35 * shin_projected_y  — when knee is visible, the downward
                            component of ankle_y − knee_y gives the shin's
                            image-space projection. A fully pointed foot
                            continues that direction for ~38% of shin length;
                            0.35 is slightly conservative to avoid over-cropping
                            on normal standing poses.

        Falls back to knee-based extrapolation (shin ≈ thigh + 20% for foot)
        when ankle keypoints are missing.
        """
        ay = self.ankle_y
        hpy = self.hip_y
        if ay is not None and hpy is not None:
            htoa = max(ay - hpy, 1.0)
            # Baseline: generous flat-stance clearance.
            clearance = 0.25 * htoa
            # Shin-direction refinement: if knee is visible, a pointed or
            # angled foot projects further below the ankle along the shin axis.
            ky = self.knee_y
            if ky is not None:
                shin_y = max(ay - ky, 0.0)   # downward extent of shin in image
                clearance = max(clearance, 0.35 * shin_y)
            return ay + clearance
        # Fallback: estimate from knee when ankle is not detected.
        ky = self.knee_y
        if ky is not None and hpy is not None:
            thigh = max(ky - hpy, 1.0)
            return ky + 1.20 * thigh  # shin ≈ thigh length + 20% for foot
        return None

    # --- body widths (x-spans) ---------------------------------------------

    @property
    def shoulder_width(self) -> Optional[float]:
        if not (self.has(KP.L_SHOULDER) and self.has(KP.R_SHOULDER)):
            return None
        lx = self.kp(KP.L_SHOULDER)[0]
        rx = self.kp(KP.R_SHOULDER)[0]
        return abs(lx - rx)

    @property
    def hip_width(self) -> Optional[float]:
        if not (self.has(KP.L_HIP) and self.has(KP.R_HIP)):
            return None
        lx = self.kp(KP.L_HIP)[0]
        rx = self.kp(KP.R_HIP)[0]
        return abs(lx - rx)

    @property
    def body_axis_x(self) -> Optional[float]:
        """Subject's vertical centerline.

        Mean x of available shoulder/hip points - more robust than nose (nose
        drifts in 3/4 views) and works for face-exclude presets where head
        keypoints aren't part of the anchor.
        """
        xs = []
        for idx in (KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP):
            if self.has(idx):
                xs.append(self.kp(idx)[0])
        return float(np.mean(xs)) if xs else None

    # --- facing direction --------------------------------------------------

    def facing(self) -> Literal["frontal", "left", "right", "back"]:
        """Estimate facing for lead-room placement.

        Heuristic uses ear visibility: both ears = frontal, only one ear = the
        opposite side is facing camera, neither ear with nose visible = facing
        away rear, neither ear and no nose = unknown -> default frontal.
        Simple and reliable for typical photo angles; fancier approaches (face
        landmarks, head pose estimation) can drop in later.
        """
        has_re = self.has(KP.R_EAR)
        has_le = self.has(KP.L_EAR)
        if has_re and has_le:
            return "frontal"
        if has_re and not has_le:
            return "left"           # facing screen-left, lead-room on left
        if has_le and not has_re:
            return "right"          # facing screen-right, lead-room on right
        if self.has(KP.NOSE):
            return "frontal"        # face seen but ears occluded -> assume frontal
        return "back"


# --- POSE_KEYPOINT parsing --------------------------------------------------

def parse_pose_keypoint(
    pose_keypoint,
    image_w: int,
    image_h: int,
) -> list[Subject]:
    """Convert ComfyUI POSE_KEYPOINT to a list of Subject instances.

    Defensively handles both wrapped (list-of-dicts, one per frame) and
    unwrapped (single dict) shapes. Coordinates from POSE_KEYPOINT are
    normalized to canvas_width/height; rescaled here to image pixel space.

    Returns [] if input is None / malformed - caller decides whether to fall
    back to grid-only candidate generation.
    """
    if pose_keypoint is None:
        return []

    # Unwrap the outer list if present (DWPose batch format).
    frames = pose_keypoint if isinstance(pose_keypoint, list) else [pose_keypoint]
    if not frames:
        return []
    frame = frames[0]                              # v1: single-image pipeline
    if not isinstance(frame, dict) or "people" not in frame:
        return []

    canvas_w = float(frame.get("canvas_width", image_w))
    canvas_h = float(frame.get("canvas_height", image_h))
    sx = image_w / canvas_w if canvas_w > 0 else 1.0
    sy = image_h / canvas_h if canvas_h > 0 else 1.0

    subjects: list[Subject] = []
    for i, person in enumerate(frame["people"]):
        body = person.get("pose_keypoints_2d")
        if not body or len(body) < 18 * 3:
            continue
        kps = np.array(body[:18 * 3], dtype=np.float32).reshape(18, 3)
        # rescale x,y to image pixel space; leave confidence alone
        kps[:, 0] *= sx
        kps[:, 1] *= sy

        face = person.get("face_keypoints_2d")
        face_arr = None
        if face and len(face) >= 70 * 3:
            face_arr = np.array(face[:70 * 3], dtype=np.float32).reshape(70, 3)
            face_arr[:, 0] *= sx
            face_arr[:, 1] *= sy

        subjects.append(Subject(
            keypoints=kps,
            image_w=image_w,
            image_h=image_h,
            person_index=i,
            face_keypoints=face_arr,
        ))
    return subjects


def select_primary_subject(
    subjects: list[Subject],
    person_index: int = -1,
) -> Optional[Subject]:
    """Pick the subject to crop around.

    person_index == -1 (auto): highest mean keypoint confidence wins. This is
    "the most clearly visible person" rather than "the largest" - works well
    when one subject is foreground and others are background extras.

    person_index >= 0: explicit selection by list index. Returns None if out
    of range.
    """
    if not subjects:
        return None
    if person_index < 0:
        return max(subjects, key=lambda s: s.total_confidence())
    if person_index >= len(subjects):
        return None
    return subjects[person_index]
