"""
eric_compose/presets.py - body-preset definitions for pose-anchored cropping.

Each preset declares:
  - which DWPose keypoints it requires (with min confidence)
  - whether the subject's face must be excluded from the crop
  - an anchor function: subject -> (x1, y1, x2, y2) "must-include" bbox
  - suggested aspect ratios when AR mode is auto

The anchor box is the TIGHT region the candidate must contain. The candidate
generator then expands outward (variations of looseness) and conforms to the
target AR. So coefficients here control how tight the minimum is, not the
final crop size.

ALL NUMERIC COEFFICIENTS ARE TUNABLE STARTING DEFAULTS. Each is documented
with what it represents and the photographic / anthropometric reasoning
behind the value. Tweak in this file only - no code changes needed elsewhere.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

from .types import KP, FACE_EXCLUDE_PRESETS
from .subjects import Subject


AnchorBox = tuple[float, float, float, float]   # x1, y1, x2, y2 (floats)
AnchorFn  = Callable[[Subject], Optional[AnchorBox]]


@dataclass(frozen=True)
class PresetDef:
    name: str
    description: str
    required_kps: tuple[int, ...]
    min_kp_conf: float
    face_policy: str                             # "include" or "exclude"
    suggested_ars: tuple[tuple[int, int], ...]   # for AR=auto suggestions
    anchor_fn: AnchorFn

    def applicable(self, subj: Subject) -> bool:
        """True iff every required keypoint is visible at min_kp_conf."""
        return subj.has_all(self.required_kps, self.min_kp_conf)


# ============================================================================
# Anchor functions - one per preset.
#
# Each function returns the TIGHT anchor box (x1, y1, x2, y2) in pixel space,
# or None if required measurements aren't computable. Pose-anchored
# candidate generation will expand variations outward from this box.
#
# Coefficient naming convention used in comments:
#   hh = head_height (estimated, see Subject.head_height)
#   sw = shoulder_width
#   hw = hip_width
#   stoh = shoulder-to-hip vertical distance
#   htoa = hip-to-ankle vertical distance
# ============================================================================


def _anchor_head_only(s: Subject) -> Optional[AnchorBox]:
    """HEAD_ONLY - tight portrait crop, head fills frame.

    Coefficients:
      0.20 * hh top:    leaves room for hair / forehead lighting.
                        Tighter (0.10) feels claustrophobic, looser (0.40)
                        starts to feel like a half-bust.
      0.20 * hh bottom: avoids cutting into the chin. 0.0 cuts at the jawline
                        which photographers consider awkward.
      0.30 * hh sides:  ear safety margin; 0.0 risks clipping ears in 3/4 views.
                        0.50 starts looking like a bust crop.
    """
    hb = s.head_bbox
    hh = s.head_height
    if hb is None or hh is None:
        return None
    x1, y1, x2, y2 = hb
    return (x1 - 0.30 * hh, y1 - 0.20 * hh,
            x2 + 0.30 * hh, y2 + 0.20 * hh)


def _anchor_head_and_shoulders(s: Subject) -> Optional[AnchorBox]:
    """HEAD_AND_SHOULDERS - the "salvage from full-body" preset.

    Top extends above the crown; bottom is mid-chest (40% from shoulders to
    hips) to keep the crop compact while including upper torso. Width is
    1.4 * shoulder_width which gives breathing room without too much empty
    space at the sides.

    Coefficients:
      0.30 * hh above head_top: comfortable headroom for portrait composition.
                                Less (0.10) feels cramped; more (0.60) wastes
                                upper frame on background.
      0.40 * stoh below shoulders: lands at upper chest. Photographic "head
                                    and shoulders" traditionally cuts here.
      1.40 * sw width:          shoulder + ~20% margin each side.
    """
    hb = s.head_bbox
    hh = s.head_height
    sy = s.shoulder_y
    hpy = s.hip_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, sy, hpy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    stoh = hpy - sy
    top    = head_y1 - 0.30 * hh
    bottom = sy + 0.40 * stoh
    half_w = 0.70 * sw                   # 1.4 * sw / 2
    # x extent: max of (shoulder span * 1.4) and (head bbox + margin)
    left  = min(bx - half_w, head_x1 - 0.10 * hh)
    right = max(bx + half_w, head_x2 + 0.10 * hh)
    return (left, top, right, bottom)


def _anchor_bust(s: Subject) -> Optional[AnchorBox]:
    """BUST - classic portrait, head + upper chest, ends just below shoulders.

    Tighter than head_and_shoulders. The 0.30 * stoh below shoulders is the
    classic "passport-plus" crop used in editorial portraits.
    """
    hb = s.head_bbox
    hh = s.head_height
    sy = s.shoulder_y
    hpy = s.hip_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, sy, hpy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    stoh = hpy - sy
    top    = head_y1 - 0.30 * hh
    bottom = sy + 0.30 * stoh
    half_w = 0.65 * sw                   # 1.3 * sw / 2 - slightly tighter than h&s
    left  = min(bx - half_w, head_x1 - 0.05 * hh)
    right = max(bx + half_w, head_x2 + 0.05 * hh)
    return (left, top, right, bottom)


def _anchor_half_body(s: Subject) -> Optional[AnchorBox]:
    """HALF_BODY - head to just past hips. Good for fashion catalog / look book.

    Bottom at hip_y + 10% of stoh so we don't cut exactly at the hipline,
    which looks like an amputation. Width = 1.4 * sw matches head_and_shoulders.
    """
    hb = s.head_bbox
    hh = s.head_height
    sy = s.shoulder_y
    hpy = s.hip_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, sy, hpy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    stoh = hpy - sy
    top    = head_y1 - 0.30 * hh
    bottom = hpy + 0.10 * stoh           # 10% below hip line
    half_w = 0.70 * sw                   # 1.4 * sw / 2
    left  = min(bx - half_w, head_x1 - 0.10 * hh)
    right = max(bx + half_w, head_x2 + 0.10 * hh)
    return (left, top, right, bottom)


def _anchor_three_quarter(s: Subject) -> Optional[AnchorBox]:
    """THREE_QUARTER - head to mid-thigh. Fashion-shot standard.

    Bottom is midway between hips and knees: hip_y + 0.5 * (knee_y - hip_y).
    This is the "no awkward cut" zone - anywhere from upper thigh to mid-thigh
    reads as intentional; cutting AT the knee or AT the hip looks accidental.
    """
    hb = s.head_bbox
    hh = s.head_height
    hpy = s.hip_y
    ky = s.knee_y
    hw = s.hip_width
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, hpy, ky, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    width_ref = hw if hw else (sw if sw else 0.0)
    if width_ref <= 0:
        return None
    top    = head_y1 - 0.30 * hh
    bottom = hpy + 0.5 * (ky - hpy)      # mid-thigh
    half_w = 0.70 * width_ref            # 1.4 * width_ref / 2
    left  = min(bx - half_w, head_x1 - 0.10 * hh)
    right = max(bx + half_w, head_x2 + 0.10 * hh)
    return (left, top, right, bottom)


def _anchor_full_body_loose(s: Subject) -> Optional[AnchorBox]:
    """FULL_BODY_LOOSE - head to feet with breathing room.

    Half a head_height above the crown; foot_y (ankle bone + shoe/sole
    estimate, 0.15 * htoa) plus a small ground clearance below the sole.
    Generous; pairs well with vertical AR (4:5, 9:16) where empty space at
    top and bottom is composition, not waste.
    """
    hb = s.head_bbox
    hh = s.head_height
    hpy = s.hip_y
    ay = s.ankle_y
    fy = s.foot_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, hpy, ay, fy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    htoa = ay - hpy
    top    = head_y1 - 0.50 * hh        # extra headroom
    bottom = fy + 0.05 * htoa           # foot_y + slight ground clearance
    half_w = 0.80 * sw                  # 1.6 * sw / 2 - wider for full body
    left  = min(bx - half_w, head_x1 - 0.20 * hh)
    right = max(bx + half_w, head_x2 + 0.20 * hh)
    return (left, top, right, bottom)


def _anchor_full_body_tight(s: Subject) -> Optional[AnchorBox]:
    """FULL_BODY_TIGHT - head to feet, minimal margin.

    For square / horizontal ARs where extra empty space looks unintentional,
    or where you want the figure to fill the frame. Bottom stops at foot_y
    (ankle + shoe estimate) with no extra clearance so the figure fills the
    frame without wasted ground below.
    """
    hb = s.head_bbox
    hh = s.head_height
    hpy = s.hip_y
    ay = s.ankle_y
    fy = s.foot_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, hpy, ay, fy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    htoa = ay - hpy
    top    = head_y1 - 0.10 * hh
    bottom = fy                          # foot_y = ankle + shoe; figure fills frame
    half_w = 0.60 * sw                  # 1.2 * sw / 2
    left  = min(bx - half_w, head_x1 - 0.05 * hh)
    right = max(bx + half_w, head_x2 + 0.05 * hh)
    return (left, top, right, bottom)


def _anchor_wide_context(s: Subject) -> Optional[AnchorBox]:
    """WIDE_CONTEXT - subject as a smaller element within the scene.

    Deliberately generous margins so the crop includes substantial
    environmental context around the full figure. Useful when the input
    is a wide landscape with the subject occupying only part of the frame,
    or when you want the setting rather than the person to fill the frame.

    Coefficients (3-5x looser than full_body_loose):
      1.50 * hh above crown:    generous headroom; sky/ceiling/background shows.
      0.60 * htoa below ankles: visible ground and setting beneath the feet.
      1.50 * sw half-width:     3 * shoulder_width total lateral context.
    """
    hb = s.head_bbox
    hh = s.head_height
    hpy = s.hip_y
    ay = s.ankle_y
    fy = s.foot_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hb, hh, hpy, ay, fy, sw, bx):
        return None
    head_x1, head_y1, head_x2, _ = hb
    htoa = ay - hpy
    top    = head_y1 - 1.50 * hh        # 3x more headroom than full_body_loose
    bottom = fy + 0.45 * htoa           # foot_y + generous ground/environment
    half_w = 1.50 * sw                  # 3 * shoulder_width total
    left   = min(bx - half_w, head_x1 - 0.50 * hh)
    right  = max(bx + half_w, head_x2 + 0.50 * hh)
    return (left, top, right, bottom)


# --- face-EXCLUDE presets (training data, no identity) ---------------------

def _anchor_outfit_full(s: Subject) -> Optional[AnchorBox]:
    """OUTFIT_FULL - full clothing crop, head EXCLUDED.

    Top is 0.40 * hh below the chin so the ENTIRE head is out of frame, not
    just the face. The candidate generator additionally validates that no
    face_keypoint exceeds min_conf inside the final box.

    Bottom and width track full_body_loose so the crop feels natural for
    head-to-toe outfit reference shots, just with the head cropped off.
    """
    hh = s.head_height
    hpy = s.hip_y
    ay = s.ankle_y
    fy = s.foot_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    sy = s.shoulder_y
    if None in (hh, hpy, ay, fy, sw, bx, sy):
        return None
    # chin estimation: nose.y + 0.4*hh OR shoulder_y - 0.5*hh; take min
    chin_y_estimate = sy - 0.5 * hh
    if s.has(KP.NOSE):
        chin_y_estimate = max(chin_y_estimate, s.kp(KP.NOSE)[1] + 0.4 * hh)
    htoa = ay - hpy
    top    = chin_y_estimate + 0.40 * hh   # well below chin
    bottom = fy                            # foot_y = ankle + shoe estimate
    half_w = 0.75 * sw                     # 1.5 * sw / 2
    return (bx - half_w, top, bx + half_w, bottom)


def _anchor_torso_only(s: Subject) -> Optional[AnchorBox]:
    """TORSO_ONLY - shoulders to hips, head EXCLUDED. For top / jacket training.

    Slight extension below shoulders (0.10 * stoh) so the cut isn't at the
    shoulder line. Same below hips. This is the cleanest "garment isolation"
    crop for upper-body clothing.
    """
    sy = s.shoulder_y
    hpy = s.hip_y
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (sy, hpy, sw, bx):
        return None
    stoh = hpy - sy
    top    = sy - 0.10 * stoh
    bottom = hpy + 0.05 * stoh
    half_w = 0.65 * sw                     # 1.3 * sw / 2
    return (bx - half_w, top, bx + half_w, bottom)


def _anchor_legs_only(s: Subject) -> Optional[AnchorBox]:
    """LEGS_ONLY - hips to feet, head EXCLUDED. For shoes / pants / skirts.

    Top sits just above the hip line so the crop reads as "lower body" rather
    than "from the waist down" (which would imply a torso crop with a head cut).
    """
    hpy = s.hip_y
    ay = s.ankle_y
    hw = s.hip_width
    sw = s.shoulder_width
    bx = s.body_axis_x
    if None in (hpy, ay, bx):
        return None
    width_ref = hw if hw else sw
    if not width_ref:
        return None
    fy = s.foot_y
    if fy is None:
        return None
    htoa = ay - hpy
    top    = hpy - 0.05 * htoa
    bottom = fy                            # foot_y = ankle + shoe estimate
    half_w = 0.75 * width_ref             # 1.5 * width_ref / 2
    return (bx - half_w, top, bx + half_w, bottom)


# ============================================================================
# Preset registry. Anchor coefficients above are the only place you'd tune
# behavior; everything else (required keypoints, face policy, suggested ARs)
# is structural.
# ============================================================================

PRESETS: dict[str, PresetDef] = {
    "head_only": PresetDef(
        name="head_only",
        description="Tight head crop. Head fills frame.",
        required_kps=(KP.NOSE, KP.L_EYE, KP.R_EYE),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((1, 1), (4, 5), (3, 4)),
        anchor_fn=_anchor_head_only,
    ),
    "head_and_shoulders": PresetDef(
        name="head_and_shoulders",
        description="Head plus upper chest. Salvage crop for awkward full-body shots.",
        required_kps=(KP.NOSE, KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((4, 5), (1, 1), (3, 4)),
        anchor_fn=_anchor_head_and_shoulders,
    ),
    "bust": PresetDef(
        name="bust",
        description="Classic portrait. Head plus shoulders, just below clavicle.",
        required_kps=(KP.NOSE, KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((4, 5), (1, 1), (3, 4)),
        anchor_fn=_anchor_bust,
    ),
    "half_body": PresetDef(
        name="half_body",
        description="Head to just past hips. Editorial / catalog standard.",
        required_kps=(KP.NOSE, KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((4, 5), (3, 4), (2, 3)),
        anchor_fn=_anchor_half_body,
    ),
    "three_quarter": PresetDef(
        name="three_quarter",
        description="Head to mid-thigh. Fashion-shot standard.",
        required_kps=(KP.NOSE, KP.L_HIP, KP.R_HIP, KP.L_KNEE, KP.R_KNEE),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((4, 5), (2, 3), (3, 4)),
        anchor_fn=_anchor_three_quarter,
    ),
    "full_body_loose": PresetDef(
        name="full_body_loose",
        description="Head to feet with breathing room. Pairs well with vertical AR.",
        required_kps=(KP.NOSE, KP.L_HIP, KP.R_HIP, KP.L_ANKLE, KP.R_ANKLE),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((9, 16), (4, 5), (2, 3)),
        anchor_fn=_anchor_full_body_loose,
    ),
    "full_body_tight": PresetDef(
        name="full_body_tight",
        description="Head to feet, minimal margin. Square / horizontal-friendly.",
        required_kps=(KP.NOSE, KP.L_HIP, KP.R_HIP, KP.L_ANKLE, KP.R_ANKLE),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((1, 1), (4, 5), (2, 3)),
        anchor_fn=_anchor_full_body_tight,
    ),
    "wide_context": PresetDef(
        name="wide_context",
        description="Subject in environmental context. Generous padding places the "
                    "person as a smaller element in the scene. Good for wide "
                    "landscapes where the figure occupies only part of the frame.",
        required_kps=(KP.NOSE, KP.L_HIP, KP.R_HIP, KP.L_ANKLE, KP.R_ANKLE),
        min_kp_conf=0.3,
        face_policy="include",
        suggested_ars=((16, 9), (3, 2), (1, 1)),
        anchor_fn=_anchor_wide_context,
    ),
    "outfit_full": PresetDef(
        name="outfit_full",
        description="Full clothing, head EXCLUDED. For outfit / style training.",
        required_kps=(KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP,
                      KP.L_ANKLE, KP.R_ANKLE),
        min_kp_conf=0.3,
        face_policy="exclude",
        suggested_ars=((9, 16), (4, 5), (2, 3)),
        anchor_fn=_anchor_outfit_full,
    ),
    "torso_only": PresetDef(
        name="torso_only",
        description="Shoulders to hips, head EXCLUDED. For top / jacket training.",
        required_kps=(KP.L_SHOULDER, KP.R_SHOULDER, KP.L_HIP, KP.R_HIP),
        min_kp_conf=0.3,
        face_policy="exclude",
        suggested_ars=((1, 1), (4, 5), (3, 4)),
        anchor_fn=_anchor_torso_only,
    ),
    "legs_only": PresetDef(
        name="legs_only",
        description="Hips to feet, head EXCLUDED. For shoes / pants / skirts.",
        required_kps=(KP.L_HIP, KP.R_HIP, KP.L_ANKLE, KP.R_ANKLE),
        min_kp_conf=0.3,
        face_policy="exclude",
        suggested_ars=((9, 16), (4, 5), (2, 3)),
        anchor_fn=_anchor_legs_only,
    ),
}


def applicable_presets(subj: Subject) -> list[str]:
    """Return preset names whose required keypoints are all visible."""
    return [name for name, p in PRESETS.items() if p.applicable(subj)]


# Sanity check: face_policy column matches FACE_EXCLUDE_PRESETS in types.py.
# Catches accidental drift between the two declarations on import.
_face_excl_table = {n for n, p in PRESETS.items() if p.face_policy == "exclude"}
assert _face_excl_table == FACE_EXCLUDE_PRESETS, (
    f"presets.py face_policy disagrees with types.FACE_EXCLUDE_PRESETS: "
    f"{_face_excl_table ^ FACE_EXCLUDE_PRESETS}"
)
