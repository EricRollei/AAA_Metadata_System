"""
eric_compose/candidates/pose_anchored.py - pose-anchored candidate generation.

For each (preset, target_AR) pair, generates a small set of candidate crops
varying in looseness, vertical placement of the subject, and lead-room.
Every candidate goes through selector.finalize_candidate (AR conform +
clipping + size sanity) before being emitted.

Face-exclude presets get an additional check via selector.face_excluded:
candidates that contain any face keypoint above min confidence are dropped.
This is enforced HERE rather than in the pipeline so a face-exclude preset
that can't satisfy its own contract returns an empty list cleanly, instead
of polluting the candidate pool with invalid options.

Variation knobs (defaults documented inline in _VARIATION_TABLE below):
  - looseness:  multipliers on anchor padding (tight / medium / loose)
  - v_anchor:   where the subject's "eyes" or "anchor center" lands
                vertically in the final frame (upper third / center)
  - lead_room:  optional horizontal shift in the subject's facing direction

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ..types import Candidate, FACE_EXCLUDE_PRESETS
from ..subjects import Subject
from ..presets import PRESETS, AnchorBox
from ..selector import (
    finalize_candidate, face_excluded, contains, box_area,
)


# ============================================================================
# Variation table - the only place to tune candidate diversity per preset.
#
# Each row produces one variation. The pose-anchored generator cross-products
# this with the list of allowed aspect ratios, so a 6-row table x 3 ARs = 18
# candidates per preset before validation. Most will pass; some will be
# rejected by AR-conform-within-bounds or face-exclusion checks.
#
# Values are conservative starting defaults. If the pipeline is producing
# too few candidates (lots of rejections) lower the looseness max; if it's
# producing too many duplicates increase looseness step or remove a row.
# ============================================================================

@dataclass(frozen=True)
class Variation:
    """One variation of an anchor box.

    Fields:
      label      - human-readable id appended to source string for debugging
      pad_factor - extra padding outside anchor as a fraction of anchor extent.
                   0.0 = anchor as-is; 0.15 = 15% bigger in each direction;
                   0.30 = 30% bigger. Higher = more breathing room.
      v_offset   - vertical bias as a fraction of anchor height. Negative
                   shifts crop UP (subject moves DOWN in frame, more space
                   above). Positive shifts crop DOWN (subject moves UP, less
                   space above). 0.0 = centered.
                   Photographic norm: subject's eyes on upper-third = subject
                   high in frame = crop shifted UP = v_offset negative.
      h_lead     - horizontal lead-room. -1 / +1 = shift opposite the facing
                   direction by 10% of crop width (gives the subject space
                   to look into). 0 = no shift. Sign convention: lead_room
                   is APPLIED in the direction the subject is facing, so
                   if facing right, the crop shifts left to put the subject
                   on the right side of the frame.
      h_offset   - unconditional horizontal shift as a fraction of crop width.
                   Positive = shift crop RIGHT (subject moves LEFT in frame).
                   Negative = shift crop LEFT (subject moves RIGHT in frame).
                   +0.167 places subject on the right third; -0.167 on the
                   left third. Unlike h_lead, this is NOT gated by facing
                   direction -- it fires for every subject orientation.
                   0.0 = no shift (default, all existing rows).
    """
    label: str
    pad_factor: float
    v_offset: float
    h_lead: int                            # -1, 0, or +1
    h_offset: float = 0.0                  # unconditional horizontal shift


# Six variations per preset. Documented choices:
#   - tight_centered:    baseline, subject centered, no extras
#   - tight_thirds:      subject on upper-third (classic portrait composition)
#   - medium_centered:   slightly looser baseline
#   - medium_thirds:     looser version of the rule-of-thirds composition
#   - loose_centered:    most padding, full breathing room
#   - lead_room:         medium loose with horizontal shift if subject is
#                        facing left/right (no-op for frontal/back)
_VARIATION_TABLE: tuple[Variation, ...] = (
    Variation("tight_centered",  pad_factor=0.00, v_offset= 0.00, h_lead=0),
    Variation("tight_thirds",    pad_factor=0.00, v_offset=-0.12, h_lead=0),
    Variation("medium_centered", pad_factor=0.15, v_offset= 0.00, h_lead=0),
    Variation("medium_thirds",   pad_factor=0.15, v_offset=-0.12, h_lead=0),
    Variation("loose_centered",  pad_factor=0.30, v_offset= 0.00, h_lead=0),
    Variation("lead_room",       pad_factor=0.20, v_offset=-0.08, h_lead=1),
)


# ============================================================================
# Internal helpers
# ============================================================================

def _apply_padding(box: AnchorBox, pad_factor: float) -> AnchorBox:
    """Expand box by pad_factor of its current extent in each direction."""
    if pad_factor <= 0:
        return box
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    px, py = w * pad_factor, h * pad_factor
    return (x1 - px, y1 - py, x2 + px, y2 + py)


def _apply_v_offset(box: AnchorBox, v_offset: float) -> AnchorBox:
    """Shift box vertically by v_offset * box_height.

    NOTE: This shifts the FRAME, not the must-include anchor. Caller is
    responsible for keeping the must_include separate so finalize_candidate
    can verify the offset frame still contains it.
    """
    if v_offset == 0:
        return box
    x1, y1, x2, y2 = box
    h = y2 - y1
    dy = v_offset * h
    return (x1, y1 + dy, x2, y2 + dy)


def _apply_h_lead(box: AnchorBox, h_lead: int, facing: str) -> AnchorBox:
    """Shift box horizontally to give subject lead-room.

    facing      effect when h_lead != 0
    --------    ------------------------------------------------
    "left"      subject faces screen-left, shift frame right so
                the subject is on the right side of the frame
    "right"     subject faces screen-right, shift frame left
    "frontal"   no shift (h_lead is no-op)
    "back"      no shift

    Magnitude is 10% of crop width - large enough to be a visible composition
    choice, small enough that the must_include anchor still fits.
    """
    if h_lead == 0 or facing not in ("left", "right"):
        return box
    x1, y1, x2, y2 = box
    w = x2 - x1
    dx = 0.10 * w * h_lead
    if facing == "left":
        # subject looking screen-left -> empty space should be on left ->
        # shift FRAME left (negative dx) so subject lands on the right
        dx = -abs(dx)
    else:  # "right"
        # subject looking screen-right -> empty space on right ->
        # shift FRAME right so subject lands on the left
        dx = abs(dx)
    return (x1 + dx, y1, x2 + dx, y2)


def _apply_h_offset(box: AnchorBox, h_offset: float) -> AnchorBox:
    """Shift box unconditionally by h_offset * crop_width.

    Positive h_offset shifts the FRAME right, moving the subject toward the
    LEFT side of the frame. Negative shifts FRAME left, subject moves RIGHT.
    Used for off-center composition variants: h_offset=+0.167 puts the
    subject on the right third of frame; -0.167 puts it on the left third.
    """
    if h_offset == 0.0:
        return box
    x1, y1, x2, y2 = box
    w = x2 - x1
    dx = h_offset * w
    return (x1 + dx, y1, x2 + dx, y2)


def _build_variation_box(
    anchor: AnchorBox,
    var: Variation,
    facing: str,
) -> AnchorBox:
    """Apply one variation row to an anchor box.

    Order matters: pad first (so v_offset and h_lead are scaled to the
    padded box, not the tight anchor), then v_offset, then h_lead, then
    the unconditional h_offset.
    """
    box = _apply_padding(anchor, var.pad_factor)
    box = _apply_v_offset(box, var.v_offset)
    box = _apply_h_lead(box, var.h_lead, facing)
    box = _apply_h_offset(box, var.h_offset)
    return box


# ============================================================================
# Public API
# ============================================================================

def generate_pose_candidates(
    subject: Subject,
    presets_to_try: list[str],
    aspect_ratios: list[float],
    image_size: tuple[int, int],
    min_kp_conf: float = 0.3,
    offcenter_strength: float = 0.0,
) -> list[Candidate]:
    """Generate candidates for one subject across the given presets and ARs.

    For each applicable preset, computes its anchor box, applies the
    variation table, conforms each variation to each target AR, and validates
    (clipping + face exclusion for face_exclude presets).

    When offcenter_strength > 0, additional left-third and right-third offset
    variations are generated by replaying each base variation with an extra
    horizontal shift (magnitude scales with strength, capped at 1/3 of crop
    width). This ensures the candidate pool actually includes off-center
    framings rather than only re-scoring existing ones.

    Args:
        subject:           the person to crop around
        presets_to_try:    subset of PRESETS to consider.
        aspect_ratios:     list of target aspect ratios (w/h).
        image_size:        (W, H) of source image
        min_kp_conf:       confidence threshold for face-exclusion check
        offcenter_strength: 0.0 = no off-center variants generated.
                           >0 = add left-third + right-third offset variants;
                           magnitude is offcenter_strength * 0.167 of crop width
                           (0.167 is one rule-of-thirds unit).

    Returns:
        list of Candidate. Empty if no preset can produce a valid crop.
    """
    candidates: list[Candidate] = []
    facing = subject.facing()

    # Build the full variation set for this run. The base table is always
    # included. When offcenter_strength > 0 we append offset variants that
    # shift each base variation left or right to place the subject on the
    # opposite thirds of the frame. Offset magnitude scales with strength so
    # that 1.0 = exactly one thirds unit (1/6 of crop width each side).
    variation_set = list(_VARIATION_TABLE)
    if offcenter_strength > 0.0:
        h_mag = offcenter_strength * (1.0 / 6.0)   # 1/6 ≈ one-third unit
        for base_var in _VARIATION_TABLE:
            variation_set.append(Variation(
                label=f"{base_var.label}:left_third",
                pad_factor=max(base_var.pad_factor, 0.10),  # need room to shift
                v_offset=base_var.v_offset,
                h_lead=0,   # no facing-conditional shift; h_offset handles it
                h_offset=-h_mag,   # frame shifts left -> subject on right third
            ))
            variation_set.append(Variation(
                label=f"{base_var.label}:right_third",
                pad_factor=max(base_var.pad_factor, 0.10),
                v_offset=base_var.v_offset,
                h_lead=0,
                h_offset=+h_mag,   # frame shifts right -> subject on left third
            ))

    for preset_name in presets_to_try:
        if preset_name not in PRESETS:
            continue
        preset = PRESETS[preset_name]
        if not preset.applicable(subject):
            continue

        anchor = preset.anchor_fn(subject)
        if anchor is None:
            continue

        is_face_excl = preset_name in FACE_EXCLUDE_PRESETS

        # The anchor is the must_include for the standard presets. For face-
        # exclude presets, we use the anchor as must_include too - it already
        # excludes the head by construction (see _anchor_outfit_full etc.),
        # so as long as the final frame contains the anchor and doesn't grow
        # in the "wrong" direction (up), face exclusion is preserved. We still
        # do an explicit face_excluded check below as belt-and-suspenders.
        #
        # Clamp must_include to image bounds: anchor functions (e.g. full_body)
        # can place the bottom below image_h to account for feet/shoe clearance.
        # Without clamping, finalize_candidate's contains() check always fails
        # for subjects whose ankles are near the image bottom edge.
        W, H = image_size
        must_include = (
            max(0.0, anchor[0]),
            max(0.0, anchor[1]),
            min(float(W), anchor[2]),
            min(float(H), anchor[3]),
        )

        for var in variation_set:
            varied = _build_variation_box(anchor, var, facing)

            for ar in aspect_ratios:
                source_str = f"pose:{preset_name}:{var.label}:ar{ar:.3f}"
                cand = finalize_candidate(
                    box=varied,
                    image_size=image_size,
                    target_ar=ar,
                    source=source_str,
                    must_include=must_include,
                    person_index=subject.person_index,
                    preset=preset_name,
                )
                if cand is None:
                    continue

                # Face-exclusion validation for outfit / body-part presets.
                # If the AR-conformed frame ended up containing a face, drop it.
                if is_face_excl:
                    final_box = (cand.x1, cand.y1, cand.x2, cand.y2)
                    if not face_excluded(
                        final_box,
                        face_keypoints=subject.face_keypoints,
                        body_keypoints=subject.keypoints,
                        min_conf=min_kp_conf,
                    ):
                        continue

                candidates.append(cand)

    return candidates
