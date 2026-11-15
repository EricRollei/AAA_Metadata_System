"""
color.py
Real colour conversion for saving. ComfyUI images are sRGB. Choosing another
profile converts the pixel values into that colour space AND embeds its ICC
profile, so the file looks the same in a colour-managed viewer. (The old save
node only attached the profile, which shifted the colours.)

The maths is done in floating point from the published primaries, so it works
for 8-bit and 16-bit output alike. sRGB fits inside all three wider spaces, so
nothing is clipped.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Dict, Optional, Tuple

import numpy as np

PROFILE_SRGB = "sRGB"
PROFILE_ADOBE = "Adobe RGB (1998)"
PROFILE_PROPHOTO = "ProPhoto RGB"
PROFILE_NONE = "none (untagged sRGB)"
PROFILE_CHOICES = [PROFILE_SRGB, PROFILE_ADOBE, PROFILE_PROPHOTO, PROFILE_NONE]

_D65 = (0.3127, 0.3290)
_D50 = (0.3457, 0.3585)
_SPACES: Dict[str, dict] = {
    PROFILE_SRGB: {"primaries": ((0.64, 0.33), (0.30, 0.60), (0.15, 0.06)), "white": _D65},
    PROFILE_ADOBE: {"primaries": ((0.64, 0.33), (0.21, 0.71), (0.15, 0.06)), "white": _D65,
                    "gamma": 2.19921875, "file": "AdobeRGB1998.icc"},
    PROFILE_PROPHOTO: {"primaries": ((0.7347, 0.2653), (0.1596, 0.8404), (0.0366, 0.0001)), "white": _D50,
                       "gamma": 1.8, "file": "ProPhoto.icm"},
}
_BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])


def _xy_to_xyz(xy: Tuple[float, float]) -> np.ndarray:
    x, y = xy
    return np.array([x / y, 1.0, (1.0 - x - y) / y])


def _rgb_to_xyz_matrix(space: dict) -> np.ndarray:
    primaries = np.stack([_xy_to_xyz(p) for p in space["primaries"]], axis=1)
    scale = np.linalg.solve(primaries, _xy_to_xyz(space["white"]))
    return primaries * scale


def _adaptation(source_white: Tuple[float, float], target_white: Tuple[float, float]) -> np.ndarray:
    if source_white == target_white:
        return np.eye(3)
    source = _BRADFORD @ _xy_to_xyz(source_white)
    target = _BRADFORD @ _xy_to_xyz(target_white)
    return np.linalg.inv(_BRADFORD) @ np.diag(target / source) @ _BRADFORD


def _srgb_decode(values: np.ndarray) -> np.ndarray:
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def _encode(linear: np.ndarray, profile: str) -> np.ndarray:
    linear = np.clip(linear, 0.0, 1.0)
    if profile == PROFILE_PROPHOTO:
        return np.where(linear < 1.0 / 512.0, linear * 16.0, linear ** (1.0 / 1.8))
    return linear ** (1.0 / _SPACES[profile]["gamma"])


def convert_from_srgb(rgb: np.ndarray, profile: str) -> np.ndarray:
    """rgb: float array [..., 3] in 0..1, sRGB encoded. Returns the same shape in `profile`."""
    if profile not in (PROFILE_ADOBE, PROFILE_PROPHOTO):
        return rgb
    source, target = _SPACES[PROFILE_SRGB], _SPACES[profile]
    matrix = (np.linalg.inv(_rgb_to_xyz_matrix(target)) @ _adaptation(source["white"], target["white"])
              @ _rgb_to_xyz_matrix(source))
    linear = _srgb_decode(np.clip(rgb.astype(np.float64), 0.0, 1.0))
    return _encode(linear @ matrix.T, profile).astype(np.float32)


def icc_bytes(profile: str, profile_dir: Optional[str] = None) -> Optional[bytes]:
    """ICC profile to embed, or None (untagged, or the profile file is missing)."""
    if profile == PROFILE_NONE:
        return None
    if profile == PROFILE_SRGB:
        from PIL import ImageCms
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    name = _SPACES.get(profile, {}).get("file")
    if not name or not profile_dir:
        return None
    path = os.path.join(profile_dir, name)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()
