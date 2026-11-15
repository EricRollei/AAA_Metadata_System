"""
eric_compose - pose-aware aesthetic image cropping.

Subpackage of AAA_Metadata_System. Provides candidate generation, scoring,
and selection for cropping photos based on body-part presets and aesthetic
scorers (GAIC, CACNet, composition).

Public surface (stable):
    from AAA_Metadata_System.eric_compose import (
        ARSpec, ARMode, BodyPreset,        # types
        Subject, parse_pose_keypoint,      # pose
        PRESETS, applicable_presets,       # body presets
    )

Internal modules (subject to change):
    candidates/   - candidate bbox generators
    scorers/      - aesthetic / composition scorers
    selector.py   - geometry, NMS, finalization
    pipeline.py   - end-to-end orchestrator

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use)
Copyright (c) 2025 Eric Hiss. All rights reserved.

Third-party model licenses (for scorers loaded at runtime):
    GAIC weights: research / non-commercial use only
        https://github.com/HuiZeng/Grid-Anchor-based-Image-Cropping-Pytorch
    CACNet weights: research / non-commercial use only
        https://github.com/bo-zhang-cs/CACNet-Pytorch
    See README for full attribution.
"""
from .types import (
    ARMode, ARSpec,
    Candidate, ScoreReport, ScoredCandidate, Scorer,
    KP, KP_NAMES,
    ALL_PRESETS, FACE_EXCLUDE_PRESETS,
)
from .subjects import Subject, parse_pose_keypoint, select_primary_subject
from .presets import PRESETS, PresetDef, applicable_presets

__all__ = [
    # types
    "ARMode", "ARSpec",
    "Candidate", "ScoreReport", "ScoredCandidate", "Scorer",
    "KP", "KP_NAMES",
    "ALL_PRESETS", "FACE_EXCLUDE_PRESETS",
    # pose
    "Subject", "parse_pose_keypoint", "select_primary_subject",
    # presets
    "PRESETS", "PresetDef", "applicable_presets",
]

__version__ = "0.1.0"
