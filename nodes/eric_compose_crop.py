"""
nodes/eric_compose_crop.py - main "Eric Compose Crop" ComfyUI node.

v1 surface: takes an image plus optional DWPose keypoints, returns the single
best crop based on body-preset-aware composition scoring. Wraps
eric_compose.pipeline.compose_crop.

Optional exclude_mask input lets the user mark regions the crop must avoid
(text overlays, watermarks, logos). Mask can come from any source - Florence-2
text detection, EasyOCR, manual paint in ComfyUI's mask editor, etc.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from typing import Optional
import json
import numpy as np
import torch

# Resolve eric_compose imports. The parent package __init__.py registers
# AAA_Metadata_System in sys.modules under both names, so both forms work.
try:
    from AAA_Metadata_System.eric_compose.pipeline import compose_crop
    from AAA_Metadata_System.eric_compose.types import ARSpec, ARMode
    from AAA_Metadata_System.eric_compose.presets import PRESETS
except ImportError:
    # Fallback for direct execution / testing
    from eric_compose.pipeline import compose_crop
    from eric_compose.types import ARSpec, ARMode
    from eric_compose.presets import PRESETS


_PRESET_CHOICES = ["auto"] + list(PRESETS.keys())


# ---------------------------------------------------------------------------
# Aspect-ratio preset dropdown
# ---------------------------------------------------------------------------

# Maps dropdown label -> list of (w, h) tuples for ARSpec.preset_list,
# or "free_any" / "free_standard" sentinels for free-form entries.
_AR_PRESET_MAP: dict = {
    # ── Sets (most common use; default is set-7) ──────────────────────────────────
    "set-3  (3:2 · 1:1 · 2:3)":
        [(3, 2), (1, 1), (2, 3)],
    "set-5  (16:9 · 3:2 · 1:1 · 2:3 · 9:16)":
        [(16, 9), (3, 2), (1, 1), (2, 3), (9, 16)],
    "set-7  (16:9 · 3:2 · 4:3 · 1:1 · 3:4 · 2:3 · 9:16)":
        [(16, 9), (3, 2), (4, 3), (1, 1), (3, 4), (2, 3), (9, 16)],
    "set-9  (16:9 · 3:2 · 7:5 · 4:3 · 1:1 · 3:4 · 5:7 · 2:3 · 9:16)":
        [(16, 9), (3, 2), (7, 5), (4, 3), (1, 1), (3, 4), (5, 7), (2, 3), (9, 16)],
    "set-13 (all common formats)":
        [(16, 9), (3, 2), (7, 5), (5, 4), (4, 3), (7, 6),
         (1, 1),
         (6, 7), (4, 5), (3, 4), (5, 7), (2, 3), (9, 16)],
    # ── Single landscape → square → portrait ───────────────────────────────────
    "16:9 landscape":  [(16, 9)],
    "3:2  landscape":  [(3, 2)],
    "7:5  landscape":  [(7, 5)],
    "4:3  landscape":  [(4, 3)],
    "5:4  landscape":  [(5, 4)],
    "7:6  landscape":  [(7, 6)],
    "1:1  square":     [(1, 1)],
    "6:7  portrait":   [(6, 7)],
    "4:5  portrait":   [(4, 5)],
    "3:4  portrait":   [(3, 4)],
    "5:7  portrait":   [(5, 7)],
    "2:3  portrait":   [(2, 3)],
    "9:16 portrait":   [(9, 16)],
    # ── Free form ────────────────────────────────────────────────────────
    "free 0.5–2.0  (any ratio)":       "free_any",
    "free 0.67–1.5 (standard range)":  "free_standard",
}

_AR_PRESET_CHOICES = list(_AR_PRESET_MAP.keys())
_AR_PRESET_DEFAULT = "set-7  (16:9 · 3:2 · 4:3 · 1:1 · 3:4 · 2:3 · 9:16)"


def _ar_preset_to_spec(preset: str) -> ARSpec:
    """Resolve a dropdown label to an ARSpec. Falls back to 1:1 on unknown key."""
    val = _AR_PRESET_MAP.get(preset)
    if val is None:
        return ARSpec.single(1, 1)
    if val == "free_any":
        return ARSpec.free(0.5, 2.0)
    if val == "free_standard":
        return ARSpec.free(0.67, 1.5)
    ratios: list = val
    if len(ratios) == 1:
        return ARSpec.single(ratios[0][0], ratios[0][1])
    return ARSpec.preset_list(ratios)


# ---------------------------------------------------------------------------
# Tensor <-> numpy helpers
# ---------------------------------------------------------------------------

def _tensor_to_numpy_uint8(image: torch.Tensor) -> np.ndarray:
    """Convert ComfyUI IMAGE (B,H,W,C float [0,1]) -> first-frame HxWxC uint8."""
    if image.dim() == 4:
        img = image[0]
    else:
        img = image
    arr = img.detach().cpu().numpy()
    arr = np.clip(arr, 0.0, 1.0) * 255.0
    return arr.astype(np.uint8)


def _mask_to_numpy(mask) -> Optional[np.ndarray]:
    """Convert ComfyUI MASK (B,H,W float [0,1]) to HxW uint8 binary.

    Treats values > 0.5 as "exclude" pixels. Returns None if input is None
    so the pipeline can short-circuit cleanly without the filter step.
    """
    if mask is None:
        return None
    m = mask[0] if mask.dim() == 3 else mask
    arr = m.detach().cpu().numpy()
    return (arr > 0.5).astype(np.uint8)


def _crop_tensor(image: torch.Tensor, x1: int, y1: int, x2: int, y2: int) -> torch.Tensor:
    """Crop the first batch image at (x1,y1,x2,y2). Returns (1, h, w, C) tensor."""
    if image.dim() == 4:
        cropped = image[:, y1:y2, x1:x2, :]
    else:
        cropped = image[y1:y2, x1:x2, :].unsqueeze(0)
    return cropped


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class EricComposeCrop:
    """
    Pose-aware aesthetic crop. Combines DWPose keypoints (when supplied)
    with composition scoring (rule-of-thirds, headroom, lead-room, edge-cut
    avoidance) to pick the single best crop within an allowed aspect ratio.

    For "outfit / torso / legs" presets, the subject's face is excluded from
    the crop - useful for clothing-style training data.

    Optional exclude_mask input lets the user mark regions the crop must
    avoid - text overlays, watermarks, logos, distracting background.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": ("Source image to crop. Only the first frame "
                                "of a batch is processed in v1."),
                }),
                "preset": (_PRESET_CHOICES, {
                    "default": "auto",
                    "tooltip": ("Body-region preset. 'auto' tries every preset "
                                "whose required keypoints are visible and lets "
                                "the scorer pick the best. Specific presets "
                                "(head_only, half_body, etc.) are pose-anchored "
                                "to that body region. Face-exclude presets "
                                "(outfit_full, torso_only, legs_only) crop the "
                                "subject's face out of frame - intended for "
                                "clothing / styling training data."),
                }),
                "ar_preset": (_AR_PRESET_CHOICES, {
                    "default": _AR_PRESET_DEFAULT,
                    "tooltip": ("Aspect-ratio preset. Sets try all listed ARs and "
                                "the scorer picks the best crop across the set. "
                                "Single formats lock to one specific AR. "
                                "set-7 (default) covers the most useful range from "
                                "16:9 landscape to 9:16 portrait. set-13 includes "
                                "every common format. Free-form samples log-uniformly "
                                "across the specified ratio range."),
                }),
            },
            "optional": {
                "ignore_pose": ("BOOLEAN", {
                    "default": False,
                    "tooltip": ("When enabled, pose keypoints are ignored even if "
                                "connected. Forces grid-only candidate generation - "
                                "useful when the subject occupies only a small part "
                                "of a wide frame and you want free-form compositional "
                                "crops not anchored to the figure."),
                }),
                "pose_keypoint": ("POSE_KEYPOINT", {
                    "tooltip": ("DWPose / OpenPose-format keypoints from a "
                                "DWPose Estimator node. Required for body "
                                "presets to apply; without it, only grid "
                                "candidates are generated."),
                }),
                "person_index": ("INT", {
                    "default": -1, "min": -1, "max": 99,
                    "tooltip": ("Which person to crop around when multiple are "
                                "present. -1 = auto-pick highest-confidence pose. "
                                "0+ = explicit index into the POSE_KEYPOINT "
                                "people list."),
                }),
                "min_kp_conf": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("Confidence threshold below which a DWPose "
                                "keypoint is treated as missing. Lower = more "
                                "presets considered (some may be unreliable). "
                                "Higher = stricter, fewer applicable presets "
                                "but more confident anchors. 0.3 is the DWPose "
                                "default and works well for most photos."),
                }),
                "enable_grid": ("BOOLEAN", {
                    "default": True,
                    "tooltip": ("Add image-content grid candidates alongside "
                                "pose-anchored ones. Helpful when 'auto' preset "
                                "should also consider non-body-centric crops. "
                                "Disable when you want strictly pose-anchored "
                                "output."),
                }),
                "nms_iou": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("IoU threshold for non-max suppression. "
                                "Higher = more candidates survive (less "
                                "aggressive). Lower = fewer candidates "
                                "(more aggressive). 0.7 is a good default; "
                                "check candidates_after_nms in info JSON to "
                                "diagnose if too few candidates are being scored."),
                }),
                "allow_no_crop": ("BOOLEAN", {
                    "default": True,
                    "tooltip": ("Let 'don't crop' compete as a candidate. The "
                                "original image is added to the candidate pool "
                                "if its AR matches the allowed set. When the "
                                "original composition is already good, it wins "
                                "and is returned unchanged. Disable when you "
                                "always want a tighter crop than the original."),
                }),
                "exclude_mask": ("MASK", {
                    "tooltip": ("Optional regions the crop must avoid. Non-zero "
                                "pixels mark exclusion areas (text overlays, "
                                "watermarks, logos, distracting backgrounds). "
                                "Source can be Florence-2 text detection, "
                                "EasyOCR, manual paint in ComfyUI's mask editor, "
                                "or any other MASK output."),
                }),
                "exclude_overlap_thresh": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": ("Max fraction of crop area allowed to overlap "
                                "exclude_mask. 0.0 = no overlap permitted "
                                "(strict). 0.05 = tolerate small edge "
                                "watermarks. 1.0 = mask ignored."),
                }),
                "offcenter_strength": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("Reward crops where the subject sits off-center. "
                                "0.0 = neutral (rules of thirds still apply). "
                                "0.5 = noticeable preference for asymmetric framing. "
                                "1.0 = strong push toward off-center placement. "
                                "Works alongside the thirds scorer, not against it - "
                                "a subject on the left-third intersection gets bonus "
                                "from both."),
                }),
                "min_crop_area": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 0.99, "step": 0.05,
                    "tooltip": ("Minimum crop size as a fraction of the original "
                                "image area. 0.0 = no limit (default). "
                                "0.5 = crop must keep at least 50% of the image "
                                "(discard at most half). 0.25 = at least a quarter. "
                                "Raise this if the cropper is discarding too much."),
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("cropped_image", "bbox", "info")
    FUNCTION = "execute"
    CATEGORY = "Eric/Compose"

    # -----------------------------------------------------------------------

    def execute(
        self,
        image,
        preset: str,
        ar_preset: str,
        pose_keypoint=None,
        ignore_pose: bool = False,
        person_index: int = -1,
        min_kp_conf: float = 0.3,
        enable_grid: bool = True,
        nms_iou: float = 0.7,
        allow_no_crop: bool = True,
        exclude_mask=None,
        exclude_overlap_thresh: float = 0.0,
        offcenter_strength: float = 0.0,
        min_crop_area: float = 0.0,
    ):
        ar_spec = _ar_preset_to_spec(ar_preset)
        ratios  = ar_spec.allowed_ratios()
        pk      = None if ignore_pose else pose_keypoint

        # Convert ComfyUI tensors to numpy for the pipeline.
        np_image = _tensor_to_numpy_uint8(image)
        np_mask = _mask_to_numpy(exclude_mask)

        # Run pipeline
        best, _all, diag = compose_crop(
            image=np_image,
            pose_keypoint=pk,
            preset=preset,
            aspect_ratios=ratios,
            person_index=person_index,
            min_kp_conf=min_kp_conf,
            enable_grid=enable_grid,
            nms_iou_thresh=nms_iou,
            allow_no_crop=allow_no_crop,
            exclude_mask=np_mask,
            exclude_overlap_thresh=exclude_overlap_thresh,
            top_k_internal=10,
            offcenter_strength=offcenter_strength,
            min_crop_area=min_crop_area,
        )

        # Fallback: no valid crop produced. Return original unchanged with a
        # diagnostic info string. This preserves workflow continuity rather
        # than throwing - the user can wire a Show Text node downstream to
        # see why.
        if best is None:
            H, W = np_image.shape[:2]
            reason = "no valid candidates produced"
            if np_mask is not None and exclude_overlap_thresh < 1.0:
                reason += " (check exclude_mask coverage / overlap_thresh)"
            info = self._build_info(
                None, preset=preset, ar_preset=ar_preset,
                ratios_count=len(ratios), enable_grid=enable_grid,
                allow_no_crop=allow_no_crop, ignore_pose=ignore_pose,
                exclude_mask_used=(np_mask is not None),
                offcenter_strength=offcenter_strength,
                fallback_reason=reason, diag=diag,
            )
            return (image, f"0,0,{W},{H}", info)

        c = best.candidate
        cropped = _crop_tensor(image, c.x1, c.y1, c.x2, c.y2)
        bbox_str = f"{c.x1},{c.y1},{c.x2},{c.y2}"
        info = self._build_info(
            best, preset=preset, ar_preset=ar_preset,
            ratios_count=len(ratios), enable_grid=enable_grid,
            allow_no_crop=allow_no_crop, ignore_pose=ignore_pose,
            exclude_mask_used=(np_mask is not None),
            offcenter_strength=offcenter_strength, diag=diag,
        )
        return (cropped, bbox_str, info)

    # -----------------------------------------------------------------------

    @staticmethod
    def _build_info(
        best,
        preset: str,
        ar_preset: str,
        ratios_count: int,
        enable_grid: bool,
        allow_no_crop: bool = True,
        ignore_pose: bool = False,
        exclude_mask_used: bool = False,
        offcenter_strength: float = 0.0,
        fallback_reason: str = None,
        diag: dict = None,
    ) -> str:
        """Compact human-readable summary as STRING for downstream display."""
        if best is None:
            payload = {
                "status": "fallback",
                "reason": fallback_reason or "unknown",
                "preset": preset,
                "ar_preset": ar_preset,
                "ratios_count": ratios_count,
                "enable_grid": enable_grid,
                "allow_no_crop": allow_no_crop,
                "ignore_pose": ignore_pose,
                "exclude_mask_used": exclude_mask_used,
                "offcenter_strength": offcenter_strength,
            }
        else:
            c = best.candidate
            r = best.report
            payload = {
                "status": "ok",
                "preset_resolved": c.preset,
                "source": c.source,
                "person_index": c.person_index,
                "bbox": [c.x1, c.y1, c.x2, c.y2],
                "size": [c.width, c.height],
                "aspect_ratio": round(c.aspect_ratio, 4),
                "score_final": round(r.final, 4),
                "score_breakdown": {k: round(v, 4) for k, v in r.by_scorer.items()},
                "preset_input": preset,
                "ar_preset": ar_preset,
                "ratios_count": ratios_count,
                "enable_grid": enable_grid,
                "allow_no_crop": allow_no_crop,
                "ignore_pose": ignore_pose,
                "exclude_mask_used": exclude_mask_used,
                "offcenter_strength": offcenter_strength,
            }
            if diag:
                payload["candidates_generated"] = diag.get("candidates_generated", "?")
                payload["candidates_after_filter"] = diag.get("candidates_after_filter", "?")
                payload["candidates_after_nms"] = diag.get("candidates_after_nms", "?")
            if r.notes:
                payload["notes"] = r.notes
        return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Auto-discovery hooks for AAA_Metadata_System/__init__.py
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "EricComposeCrop": EricComposeCrop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricComposeCrop": "Eric Compose Crop",
}
