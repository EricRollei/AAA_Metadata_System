"""
eric_compose/types.py - core types for compose-crop pipeline.

Shared data structures used across:
  - subjects.py   (pose parsing)
  - presets.py    (body-preset table)
  - candidates/*  (candidate generators)
  - scorers/*     (aesthetic / composition / quality scorers)
  - selector.py   (AR conform, clipping, NMS)
  - pipeline.py   (orchestrator)

All coordinates are pixel space relative to the source image unless noted.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable
from enum import Enum
import numpy as np


# --- DWPose body_18 keypoint indices ----------------------------------------
# OpenPose-style 18-keypoint format used by ComfyUI POSE_KEYPOINT (DWPose,
# controlnet_aux DWPose preprocessor, etc.). DO NOT renumber - these match
# upstream conventions and any change here breaks pose parsing.
class KP:
    NOSE       = 0
    NECK       = 1
    R_SHOULDER = 2
    R_ELBOW    = 3
    R_WRIST    = 4
    L_SHOULDER = 5
    L_ELBOW    = 6
    L_WRIST    = 7
    R_HIP      = 8
    R_KNEE     = 9
    R_ANKLE    = 10
    L_HIP      = 11
    L_KNEE     = 12
    L_ANKLE    = 13
    R_EYE      = 14
    L_EYE      = 15
    R_EAR      = 16
    L_EAR      = 17

KP_NAMES: tuple[str, ...] = (
    "nose", "neck", "r_shoulder", "r_elbow", "r_wrist",
    "l_shoulder", "l_elbow", "l_wrist",
    "r_hip", "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle",
    "r_eye", "l_eye", "r_ear", "l_ear",
)


# --- Body presets -----------------------------------------------------------
# String literals (not Enum) so they pass cleanly through ComfyUI dropdown
# inputs without serialization friction.

ALL_PRESETS: tuple[str, ...] = (
    "head_only", "head_and_shoulders", "bust",
    "half_body", "three_quarter",
    "full_body_loose", "full_body_tight", "wide_context",
    "outfit_full", "torso_only", "legs_only",
)

# Presets where the subject's face MUST NOT appear in the final crop.
# Used for clothing / outfit / body-part training-data, where the model
# should not learn anything about the subject's identity.
FACE_EXCLUDE_PRESETS: frozenset[str] = frozenset({
    "outfit_full", "torso_only", "legs_only",
})


# --- AR specification -------------------------------------------------------

class ARMode(str, Enum):
    FREE        = "free"          # any AR within [free_min, free_max]
    SINGLE      = "single"        # exactly one AR
    PRESET_LIST = "preset_list"   # one of a list (best score across set wins)


@dataclass(frozen=True)
class ARSpec:
    """Aspect-ratio constraint for candidate generation.

    FREE mode samples log-uniformly between free_min and free_max so 1:2..2:1
    are evenly weighted visually. SINGLE pins to one exact AR. PRESET_LIST
    tries each AR and the scorer picks the winner.
    """
    mode: ARMode
    ratios: tuple[tuple[int, int], ...] = ()
    free_min: float = 0.5
    free_max: float = 2.0
    free_steps: int = 9

    def allowed_ratios(self) -> list[float]:
        if self.mode == ARMode.FREE:
            lo, hi = np.log(self.free_min), np.log(self.free_max)
            return list(np.exp(np.linspace(lo, hi, self.free_steps)))
        return [w / h for w, h in self.ratios]

    @classmethod
    def free(cls, min_ar: float = 0.5, max_ar: float = 2.0, steps: int = 9) -> "ARSpec":
        return cls(mode=ARMode.FREE, free_min=min_ar, free_max=max_ar, free_steps=steps)

    @classmethod
    def single(cls, w: int, h: int) -> "ARSpec":
        return cls(mode=ARMode.SINGLE, ratios=((w, h),))

    @classmethod
    def preset_list(cls, ratios: list[tuple[int, int]]) -> "ARSpec":
        return cls(mode=ARMode.PRESET_LIST, ratios=tuple(ratios))


# --- Candidate crop ---------------------------------------------------------

@dataclass
class Candidate:
    """A proposed crop region. All coords are source-image pixel space."""
    x1: int
    y1: int
    x2: int
    y2: int
    source: str                                  # e.g. "pose:half_body:tight", "grid:5x5"
    aspect_ratio: float                          # w/h, for fast filter checks
    person_index: Optional[int] = None
    preset: Optional[str] = None
    must_include: Optional[tuple[int, int, int, int]] = None  # tight anchor inside

    @property
    def width(self)  -> int: return self.x2 - self.x1
    @property
    def height(self) -> int: return self.y2 - self.y1
    @property
    def area(self)   -> int: return self.width * self.height

    def to_xyxy(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


# --- Scoring ----------------------------------------------------------------

@dataclass
class ScoreReport:
    """Per-candidate scoring breakdown. final is the combined weighted score."""
    final: float
    by_scorer: dict[str, float] = field(default_factory=dict)   # raw per-scorer
    normalized: dict[str, float] = field(default_factory=dict)  # min-maxed in batch
    notes: dict[str, str]        = field(default_factory=dict)  # debug strings


@dataclass
class ScoredCandidate:
    candidate: Candidate
    report: ScoreReport


# --- Scorer protocol --------------------------------------------------------

@runtime_checkable
class Scorer(Protocol):
    """Surface every scorer implements.

    Implementations may load models lazily (in warmup) or eagerly (__init__).
    score_batch processes ALL candidates in one call - implementations are
    expected to batch internally for GPU efficiency where applicable.
    """
    name: str          # stable id, used as key in ScoreReport.by_scorer
    needs_gpu: bool    # used by loader to decide warmup order

    def warmup(self, device: str) -> None: ...
    def score_batch(self, image: np.ndarray, candidates: list[Candidate]) -> np.ndarray: ...
    def unload(self) -> None: ...
