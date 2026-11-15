"""
eric_compose/candidates - candidate bbox generators.

Two strategies:
  - pose_anchored: variations around a preset's anchor box (when DWPose
    keypoints are present and at least one preset is applicable).
  - grid: GAIC-style anchor grid (image-content-driven, no pose required).

Both produce lists of Candidate objects. The pipeline pools all candidates,
scores them, runs NMS, and returns top-K.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (Non-Commercial and Commercial Use) - matches AAA_Metadata_System
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""
from .pose_anchored import generate_pose_candidates
from .grid import generate_grid_candidates

__all__ = ["generate_pose_candidates", "generate_grid_candidates"]
