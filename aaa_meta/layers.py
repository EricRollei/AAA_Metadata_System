"""
layers.py
The layer stack of the save node, as plain float arrays, in the same order and
with the same names / blend modes / opacities the v099d PSD writer produces:

    Main Image
    overlay 1, overlay 2                      (name, blend mode, opacity from the widgets)
    "<mask name> (Masked Image)" per mask     (main picture with the mask as transparency, hidden)
    mask 1, mask 2 as pictures                (only with include_mask_layers)

Used for the 16-bit PSD and for the Photoshop layer block inside TIFF files.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from typing import Any, Dict, List

import numpy as np
from PIL import Image


def to_float_array(image: Any) -> np.ndarray:
    """Tensor / array / PIL image -> float32 H x W x C in 0..1 (first image of a batch)."""
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGBA" if "A" in image.mode else "RGB"), dtype=np.float32) / 255.0
    if hasattr(image, "detach"):
        image = image.detach().cpu().numpy()
    array = np.asarray(image)
    if array.ndim == 4:
        array = array[0]
    if array.ndim == 2:
        array = array[..., None]
    if array.ndim == 3 and array.shape[0] in (1, 3, 4) and array.shape[-1] > 4:
        array = np.transpose(array, (1, 2, 0))                     # C x H x W
    if array.dtype == np.uint8:
        return array.astype(np.float32) / 255.0
    if array.dtype == np.uint16:
        return array.astype(np.float32) / 65535.0
    return np.clip(array.astype(np.float32), 0.0, 1.0)


def _fit(array: np.ndarray, height: int, width: int) -> np.ndarray:
    if array.shape[:2] == (height, width):
        return array
    channels = [np.asarray(Image.fromarray(array[..., c], mode="F").resize((width, height), Image.BILINEAR))
                for c in range(array.shape[-1])]
    return np.stack(channels, axis=-1)


def _rgb(array: np.ndarray) -> np.ndarray:
    return np.repeat(array, 3, axis=-1) if array.shape[-1] == 1 else array[..., :3]


def _rgba(array: np.ndarray) -> np.ndarray:
    if array.shape[-1] >= 4:
        return array[..., :4]
    return np.concatenate([_rgb(array), np.ones(array.shape[:2] + (1,), dtype=np.float32)], axis=-1)


def build_layers(main_image: Any, widgets: Dict[str, Any]) -> List[Dict[str, Any]]:
    main = to_float_array(main_image)
    height, width = main.shape[:2]
    layers: List[Dict[str, Any]] = [{"name": "Main Image", "pixels": _rgba(main), "blend": "normal",
                                     "opacity": 255, "visible": True}]
    for index in (1, 2):
        overlay = widgets.get(f"overlay_layer_{index}")
        if overlay is None:
            continue
        layers.append({"name": str(widgets.get(f"overlay_{index}_name") or f"Overlay {index}"),
                       "pixels": _rgba(_fit(to_float_array(overlay), height, width)),
                       "blend": str(widgets.get(f"overlay_{index}_blend_mode") or "normal"),
                       "opacity": max(0, min(int(widgets.get(f"overlay_{index}_opacity", 255)), 255)),
                       "visible": True})
    masks = []
    for index in (1, 2):
        mask = widgets.get(f"mask_layer_{index}")
        if mask is None:
            continue
        array = _fit(to_float_array(mask), height, width)
        rgb = _rgb(array)
        luminance = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
        name = str(widgets.get(f"mask_{index}_name") or f"Mask {index}")
        blend = str(widgets.get(f"mask_{index}_blend_mode") or "normal")
        opacity = max(0, min(int(widgets.get(f"mask_{index}_opacity", 255)), 255))
        masks.append((name, blend, opacity, array))
        layers.append({"name": f"{name} (Masked Image)",
                       "pixels": np.concatenate([_rgb(main), luminance[..., None]], axis=-1),
                       "blend": blend, "opacity": opacity, "visible": False})
    if widgets.get("include_mask_layers", False):
        for name, blend, opacity, array in masks:
            layers.append({"name": name, "pixels": _rgba(array), "blend": blend, "opacity": opacity, "visible": True})
    return layers


def layer_summary(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"layer_count": len(layers),
            "layers": [{"name": layer["name"], "blend_mode": layer["blend"], "opacity": layer["opacity"],
                        "visible": bool(layer.get("visible", True))} for layer in layers]}
