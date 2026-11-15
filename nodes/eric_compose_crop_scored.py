"""
nodes/eric_compose_crop_scored.py - "Eric Compose Crop (Scored)" ComfyUI node.

Extends the basic composition crop with UniPercept aesthetic scoring.
Generates top-K candidate crops via the composition pipeline (rule-of-thirds,
headroom, lead-room, edge-cut avoidance), scores them in a single batch pass
per domain via UniPerceptDirectBackend.batch_score(), then returns the
candidate with the highest blended score.

Requires Eric-image-classification/unipercept_backend.py to be on sys.path.
The backend is cached at class level so the model loads once per session
(~10-30 s first call; negligible thereafter).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

import numpy as np
import torch

# --- eric_compose imports ---------------------------------------------------
try:
    from AAA_Metadata_System.eric_compose.pipeline import compose_crop
    from AAA_Metadata_System.eric_compose.types import ARSpec, ARMode
    from AAA_Metadata_System.eric_compose.presets import PRESETS
except ImportError:
    from eric_compose.pipeline import compose_crop
    from eric_compose.types import ARSpec, ARMode
    from eric_compose.presets import PRESETS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unipercept path - sibling custom_node alongside AAA_Metadata_System
# nodes/ -> AAA_Metadata_System/ -> custom_nodes/ -> Eric-image-classification
# ---------------------------------------------------------------------------
_UNIPERCEPT_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),  # .../nodes
        "..",                                         # .../AAA_Metadata_System
        "..",                                         # .../custom_nodes
        "Eric-image-classification",
    )
)

_PRESET_CHOICES = ["auto"] + list(PRESETS.keys())

# ---------------------------------------------------------------------------
# Aspect-ratio preset dropdown  (shared logic with eric_compose_crop.py)
# ---------------------------------------------------------------------------

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


_DOMAIN_CHOICES  = ["iaa", "iaa+iqa", "iaa+iqa+ista"]
_DEVICE_CHOICES  = ["cuda", "cpu"]


# ---------------------------------------------------------------------------
# Tensor / mask helpers (inlined to avoid cross-node import coupling)
# ---------------------------------------------------------------------------

def _parse_ar_string(mode: str, raw: str) -> ARSpec:
    """Parse ar_ratios string per mode into an ARSpec."""
    raw = (raw or "").strip()

    if mode == "free":
        try:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if len(parts) >= 2:
                lo, hi = float(parts[0]), float(parts[1])
                if 0 < lo < hi:
                    return ARSpec.free(min_ar=lo, max_ar=hi)
        except (ValueError, IndexError):
            pass
        return ARSpec.free()

    ratios: list[tuple[int, int]] = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            try:
                w_str, h_str = tok.split(":", 1)
                w, h = int(float(w_str)), int(float(h_str))
                if w > 0 and h > 0:
                    ratios.append((w, h))
            except ValueError:
                continue
        else:
            try:
                f = float(tok)
                if f > 0:
                    ratios.append((int(round(f * 1000)), 1000))
            except ValueError:
                continue
    if not ratios:
        ratios = [(1, 1)]

    if mode == "single":
        w, h = ratios[0]
        return ARSpec.single(w, h)
    return ARSpec.preset_list(ratios)


def _tensor_to_numpy_uint8(image: torch.Tensor) -> np.ndarray:
    """ComfyUI IMAGE (B,H,W,C float [0,1]) -> first-frame HxWxC uint8."""
    img = image[0] if image.dim() == 4 else image
    arr = img.detach().cpu().numpy()
    return (np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)


def _mask_to_numpy(mask) -> Optional[np.ndarray]:
    """ComfyUI MASK (B,H,W float [0,1]) -> HxW uint8 binary, or None."""
    if mask is None:
        return None
    m = mask[0] if mask.dim() == 3 else mask
    return (m.detach().cpu().numpy() > 0.5).astype(np.uint8)


def _crop_tensor(image: torch.Tensor, x1: int, y1: int,
                 x2: int, y2: int) -> torch.Tensor:
    """Crop first batch frame; returns (1, h, w, C) tensor."""
    if image.dim() == 4:
        return image[:, y1:y2, x1:x2, :]
    return image[y1:y2, x1:x2, :].unsqueeze(0)


def _crop_to_pil(image: torch.Tensor, x1: int, y1: int, x2: int, y2: int):
    """Crop a ComfyUI IMAGE tensor and return a PIL.Image (RGB)."""
    from PIL import Image
    crop_t = _crop_tensor(image, x1, y1, x2, y2)
    arr = (crop_t[0].detach().cpu().numpy() * 255.0).clip(0, 255).astype("uint8")
    return Image.fromarray(arr, mode="RGB")


def _parse_domains(score_domains: str) -> list[str]:
    """'iaa+iqa+ista' -> ['iaa', 'iqa', 'ista']."""
    return [d.strip() for d in score_domains.split("+") if d.strip()]


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class EricComposeCropScored:
    """
    Pose-aware crop with UniPercept aesthetic scoring.

    Generates crop candidates via composition pipeline (rule-of-thirds,
    headroom, lead-room, edge-cut), then re-ranks them with UniPercept
    batch scoring and returns the highest-scoring candidate.

    composition_weight controls the blend between the two scorers:
      0.0 = UniPercept only  (full deep-model ranking)
      1.0 = composition only (identical to basic Eric Compose Crop)
      0.3 = recommended blend: 30 % composition, 70 % UniPercept

    For face-exclude presets (outfit_full, torso_only, legs_only) the face
    is excluded from the crop by construction and validated by selector.

    If UniPercept fails to load or errors during scoring the node falls back
    to the composition-only winner and logs a warning - the workflow continues
    rather than crashing.
    """

    # Class-level backend cache — model loads once per ComfyUI session.
    _backend = None
    _backend_device: Optional[str] = None

    @classmethod
    def _get_scorer(cls, device: str):
        """Return cached UniPerceptDirectBackend, creating it if needed."""
        if cls._backend is None or cls._backend_device != device:
            if _UNIPERCEPT_PATH not in sys.path:
                sys.path.insert(0, _UNIPERCEPT_PATH)
            from unipercept_backend import get_backend
            logger.info("[EricComposeCropScored] Loading UniPercept on %s ...", device)
            cls._backend = get_backend("direct", device=device)
            cls._backend_device = device
            logger.info("[EricComposeCropScored] UniPercept ready.")
        return cls._backend

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": ("Source image to crop. Only the first frame "
                                "of a batch is processed."),
                }),
                "preset": (_PRESET_CHOICES, {
                    "default": "auto",
                    "tooltip": ("Body-region preset. 'auto' tries every preset "
                                "whose required keypoints are visible. Face-exclude "
                                "presets (outfit_full, torso_only, legs_only) crop "
                                "the subject's face out of frame."),
                }),
                "ar_preset": (_AR_PRESET_CHOICES, {
                    "default": _AR_PRESET_DEFAULT,
                    "tooltip": ("Aspect-ratio preset. Sets try all listed ARs and "
                                "the scorer picks the best crop across the set. "
                                "Single formats lock to one specific AR. "
                                "set-7 (default) covers the most useful range from "
                                "16:9 landscape to 9:16 portrait."),
                }),
                "score_domains": (_DOMAIN_CHOICES, {
                    "default": "iaa",
                    "tooltip": ("UniPercept domains to score. "
                                "'iaa' = aesthetics only (fastest, 1 model pass). "
                                "'iaa+iqa' = aesthetics + technical quality (2 passes). "
                                "'iaa+iqa+ista' = all three including structure/texture "
                                "(3 passes, most thorough). For composition-quality "
                                "work 'iaa' is usually sufficient."),
                }),
                "device": (_DEVICE_CHOICES, {
                    "default": "cuda",
                    "tooltip": "Inference device for UniPercept scoring.",
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
                    "tooltip": ("DWPose keypoints. Required for body presets; "
                                "without it only grid candidates are generated."),
                }),
                "person_index": ("INT", {
                    "default": -1, "min": -1, "max": 99,
                    "tooltip": ("-1 = auto-pick highest-confidence pose. "
                                "0+ = explicit index into POSE_KEYPOINT people list."),
                }),
                "min_kp_conf": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("DWPose confidence threshold. Lower = more presets "
                                "considered; higher = stricter anchors. 0.3 is the "
                                "DWPose default."),
                }),
                "enable_grid": ("BOOLEAN", {
                    "default": True,
                    "tooltip": ("Add GAIC-style grid candidates alongside "
                                "pose-anchored ones. Provides coverage when pose "
                                "anchors alone don't find ideal framing."),
                }),
                "nms_iou": ("FLOAT", {
                    "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("IoU threshold for deduplication. Higher = more "
                                "candidates survive (less aggressive). Lower = "
                                "fewer candidates (more aggressive). 0.7 is a "
                                "good default; raise toward 0.9 if UniPercept "
                                "sees too few candidates."),
                }),
                "allow_no_crop": ("BOOLEAN", {
                    "default": True,
                    "tooltip": ("Let 'don't crop' compete as a candidate. When "
                                "the original composition already scores highest "
                                "it is returned unchanged."),
                }),
                "exclude_mask": ("MASK", {
                    "tooltip": ("Regions the crop must avoid (text overlays, "
                                "watermarks, logos). Non-zero pixels = exclude."),
                }),
                "exclude_overlap_thresh": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": ("Max fraction of crop area allowed to overlap "
                                "exclude_mask. 0.0 = strict (no overlap)."),
                }),
                "offcenter_strength": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("Reward crops where the subject sits off-center. "
                                "0.0 = neutral. 0.5 = noticeable off-center preference. "
                                "1.0 = strong push toward asymmetric framing. "
                                "Applied before UniPercept reranking so the top-K "
                                "candidates sent for scoring already reflect the bias."),
                }),
                "min_crop_area": ("FLOAT", {
                    "default": 0.0, "min": 0.0, "max": 0.99, "step": 0.05,
                    "tooltip": ("Minimum crop size as a fraction of the original "
                                "image area. 0.0 = no limit (default). "
                                "0.5 = crop must keep at least 50% of the image. "
                                "Raise this if the cropper is discarding too much."),
                }),
                "composition_weight": ("FLOAT", {
                    "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": ("Weight of the internal composition score vs "
                                "UniPercept. 0.0 = UniPercept only. "
                                "1.0 = composition only (same as basic node). "
                                "0.3 = recommended blend."),
                }),
                "top_k_candidates": ("INT", {
                    "default": 10, "min": 3, "max": 30,
                    "tooltip": ("Number of composition-ranked candidates to pass "
                                "to UniPercept. More = thorough but slower. "
                                "UniPercept scores all of them in one batch pass "
                                "per domain, so 10 vs 20 costs little extra."),
                }),
            },
        }

    RETURN_TYPES  = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES  = ("cropped_image", "bbox", "info")
    FUNCTION      = "execute"
    CATEGORY      = "Eric/Compose"

    # -----------------------------------------------------------------------

    def execute(
        self,
        image: torch.Tensor,
        preset: str,
        ar_preset: str,
        score_domains: str,
        device: str,
        pose_keypoint=None,
        ignore_pose: bool = False,
        person_index: int = -1,
        min_kp_conf: float = 0.3,
        enable_grid: bool = True,
        nms_iou: float = 0.7,
        allow_no_crop: bool = True,
        exclude_mask=None,
        exclude_overlap_thresh: float = 0.0,
        composition_weight: float = 0.3,
        top_k_candidates: int = 10,
        offcenter_strength: float = 0.0,
        min_crop_area: float = 0.0,
    ):
        ar_spec   = _ar_preset_to_spec(ar_preset)
        ratios    = ar_spec.allowed_ratios()
        pk        = None if ignore_pose else pose_keypoint
        np_image  = _tensor_to_numpy_uint8(image)
        np_mask   = _mask_to_numpy(exclude_mask)
        domains   = _parse_domains(score_domains)

        # 1. Composition pipeline: produce top-K pre-ranked candidates --------
        best_comp, top_k, diag = compose_crop(
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
            top_k_internal=top_k_candidates,
            offcenter_strength=offcenter_strength,
            min_crop_area=min_crop_area,
        )

        # No valid candidates at all — return original with diagnostic info.
        if not top_k:
            H, W = np_image.shape[:2]
            reason = "no valid candidates produced"
            if np_mask is not None and exclude_overlap_thresh < 1.0:
                reason += " (check exclude_mask coverage / overlap_thresh)"
            info = json.dumps({
                "status": "fallback",
                "reason": reason,
                "preset": preset,
                "ar_preset": ar_preset,
                "ignore_pose": ignore_pose,
                "score_domains": score_domains,
                "composition_weight": composition_weight,
                "exclude_mask_used": np_mask is not None,
                "candidates_generated": diag.get("candidates_generated", 0),
                "candidates_after_filter": diag.get("candidates_after_filter", 0),
                "candidates_after_nms": diag.get("candidates_after_nms", 0),
            }, indent=2)
            return (image, f"0,0,{W},{H}", info)

        # 2. UniPercept batch scoring ----------------------------------------
        try:
            scorer = self._get_scorer(device)

            # Preprocess all candidate crops once.
            if _UNIPERCEPT_PATH not in sys.path:
                sys.path.insert(0, _UNIPERCEPT_PATH)
            from unipercept_backend import pil_to_pixel_values, SCORE_DESC

            pixel_values_list = [
                pil_to_pixel_values(_crop_to_pil(image, sc.candidate.x1, sc.candidate.y1,
                                                  sc.candidate.x2, sc.candidate.y2),
                                    device)
                for sc in top_k
            ]

            # One model pass per domain (batch over all candidates).
            domain_scores: dict[str, list[float]] = {}
            for d in domains:
                domain_scores[d] = scorer.batch_score(pixel_values_list, SCORE_DESC[d])

            # Composite UniPercept score per candidate (mean of domains).
            n = len(top_k)
            up_composite = [
                round(sum(domain_scores[d][i] for d in domains) / len(domains), 2)
                for i in range(n)
            ]

            # 3. Blend composition + UniPercept scores -----------------------
            # Composition finals are in [0, 1]; normalise to [0, 100].
            comp_finals = [sc.report.final for sc in top_k]
            c_min, c_max = min(comp_finals), max(comp_finals)
            if c_max > c_min:
                comp_norm = [(s - c_min) / (c_max - c_min) * 100.0 for s in comp_finals]
            else:
                comp_norm = [50.0] * n

            w_comp = composition_weight
            w_up   = 1.0 - composition_weight
            blended = [
                round(w_comp * comp_norm[i] + w_up * up_composite[i], 2)
                for i in range(n)
            ]

            best_idx = max(range(n), key=lambda i: blended[i])
            best_sc  = top_k[best_idx]

            c       = best_sc.candidate
            cropped = _crop_tensor(image, c.x1, c.y1, c.x2, c.y2)
            bbox_str = f"{c.x1},{c.y1},{c.x2},{c.y2}"

            info = self._build_info(
                best_sc, best_idx, blended, comp_norm, up_composite,
                domain_scores, domains, top_k,
                preset=preset, ar_preset=ar_preset, ratios_count=len(ratios),
                ignore_pose=ignore_pose, enable_grid=enable_grid,
                allow_no_crop=allow_no_crop,
                exclude_mask_used=(np_mask is not None),
                score_domains=score_domains, composition_weight=composition_weight,
                diag=diag,
            )
            return (cropped, bbox_str, info)

        except Exception as exc:
            # UniPercept unavailable or errored — fall back to composition winner.
            logger.warning(
                "[EricComposeCropScored] UniPercept scoring failed (%s). "
                "Falling back to composition-only winner.", exc,
            )
            if best_comp is None:
                H, W = np_image.shape[:2]
                info = json.dumps({
                    "status": "error",
                    "reason": str(exc),
                    "preset": preset,
                    "ar_preset": ar_preset,
                }, indent=2)
                return (image, f"0,0,{W},{H}", info)

            c        = best_comp.candidate
            cropped  = _crop_tensor(image, c.x1, c.y1, c.x2, c.y2)
            bbox_str = f"{c.x1},{c.y1},{c.x2},{c.y2}"
            r        = best_comp.report
            info = json.dumps({
                "status": "fallback_composition_only",
                "unipercept_error": str(exc),
                "preset_resolved": c.preset,
                "source": c.source,
                "bbox": [c.x1, c.y1, c.x2, c.y2],
                "size": [c.width, c.height],
                "aspect_ratio": round(c.aspect_ratio, 4),
                "score_composition": round(r.final, 4),
                "score_breakdown": {k: round(v, 4) for k, v in r.by_scorer.items()},
                "preset_input": preset,
                "ar_preset": ar_preset,
                "ratios_count": len(ratios),
                "ignore_pose": ignore_pose,
                "enable_grid": enable_grid,
                "allow_no_crop": allow_no_crop,
                "exclude_mask_used": np_mask is not None,
            }, indent=2)
            return (cropped, bbox_str, info)

    # -----------------------------------------------------------------------

    @staticmethod
    def _build_info(
        best_sc,
        best_idx: int,
        blended: list[float],
        comp_norm: list[float],
        up_composite: list[float],
        domain_scores: dict[str, list[float]],
        domains: list[str],
        top_k: list,
        *,
        preset: str,
        ar_preset: str,
        ratios_count: int,
        enable_grid: bool,
        allow_no_crop: bool,
        ignore_pose: bool,
        exclude_mask_used: bool,
        score_domains: str,
        composition_weight: float,
        diag: dict = None,
    ) -> str:
        """Build the info STRING output: winner summary + per-candidate table."""
        c = best_sc.candidate
        r = best_sc.report

        candidates_table = []
        for i, sc in enumerate(top_k):
            ci = sc.candidate
            entry: dict = {
                "rank": i + 1,
                "selected": i == best_idx,
                "source": ci.source,
                "bbox": [ci.x1, ci.y1, ci.x2, ci.y2],
                "score_blended": blended[i],
                "score_comp_norm": round(comp_norm[i], 2),
                "score_up_composite": up_composite[i],
            }
            for d in domains:
                entry[f"up_{d}"] = domain_scores[d][i]
            candidates_table.append(entry)

        payload = {
            "status": "ok",
            "preset_resolved": c.preset,
            "source": c.source,
            "person_index": c.person_index,
            "bbox": [c.x1, c.y1, c.x2, c.y2],
            "size": [c.width, c.height],
            "aspect_ratio": round(c.aspect_ratio, 4),
            "score_blended": blended[best_idx],
            "score_comp_norm": round(comp_norm[best_idx], 2),
            "score_up_composite": up_composite[best_idx],
            "score_comp_raw": round(r.final, 4),
            "score_breakdown_comp": {k: round(v, 4) for k, v in r.by_scorer.items()},
        }
        for d in domains:
            payload[f"up_{d}"] = domain_scores[d][best_idx]
        payload.update({
            "preset_input": preset,
            "ar_preset": ar_preset,
            "ratios_count": ratios_count,
            "enable_grid": enable_grid,
            "allow_no_crop": allow_no_crop,
            "ignore_pose": ignore_pose,
            "exclude_mask_used": exclude_mask_used,
            "score_domains": score_domains,
            "composition_weight": composition_weight,
            "candidates_scored": len(top_k),
            "candidates": candidates_table,
        })
        if diag:
            payload["candidates_generated"] = diag.get("candidates_generated", "?")
            payload["candidates_after_filter"] = diag.get("candidates_after_filter", "?")
            payload["candidates_after_nms"] = diag.get("candidates_after_nms", "?")
        if r.notes:
            payload["notes"] = r.notes

        return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Auto-discovery hooks
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "EricComposeCropScored": EricComposeCropScored,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricComposeCropScored": "Eric Compose Crop (Scored)",
}
