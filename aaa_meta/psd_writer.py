"""
psd_writer.py
Writes Photoshop layer data directly, for the two cases psd-tools does not cover:

  * a 16-bit layered PSD                      write_psd(...)
  * layers inside a TIFF that Photoshop opens  photoshop_tiff_block(...)
    (TIFF tag 37724 "ImageSourceData" - the same layer structure a PSD uses)

A layer is a dict:
    {"name": str, "pixels": float array H x W x 4 (RGBA, 0..1),
     "blend": "normal" | "multiply" | ... , "opacity": 0..255, "visible": bool}
Layers are listed bottom first. All layers cover the full canvas. Channel data
is stored uncompressed (valid for every Photoshop version; files are larger).

byte_order: ">" for PSD files and big-endian TIFFs, "<" for little-endian TIFFs
(inside a TIFF the layer data follows the TIFF's byte order, signatures reversed).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import struct
from typing import Any, Dict, List, Optional

import numpy as np

BLEND_KEYS = {
    "normal": b"norm", "multiply": b"mul ", "screen": b"scrn", "overlay": b"over",
    "add": b"lddg", "linear_dodge": b"lddg", "subtract": b"fsub", "difference": b"diff",
    "darken": b"dark", "lighten": b"lite", "color_dodge": b"div ", "color_burn": b"idiv",
    "soft_light": b"sLit", "hard_light": b"hLit", "exclusion": b"smud", "hue": b"hue ",
    "saturation": b"sat ", "color": b"colr", "luminosity": b"lum ",
}
TIFF_BLOCK_HEADER = b"Adobe Photoshop Document Data Block\x00"
TIFF_TAG_IMAGE_SOURCE_DATA = 37724


def _key(key: bytes, byte_order: str) -> bytes:
    return key if byte_order == ">" else key[::-1]


def _plane(values: np.ndarray, depth: int) -> bytes:
    """One channel, float 0..1 -> raw samples. Pixel data is big-endian in PSD and
    in the TIFF layer block alike (only the structure around it follows the TIFF byte order)."""
    clipped = np.clip(values.astype(np.float64), 0.0, 1.0)
    if depth == 16:
        return np.round(clipped * 65535.0).astype(">u2").tobytes()
    return np.round(clipped * 255.0).astype(np.uint8).tobytes()


def _rgba(pixels: Any) -> np.ndarray:
    array = np.asarray(pixels, dtype=np.float32)
    if array.ndim == 2:
        array = array[..., None]
    if array.shape[-1] == 1:
        array = np.repeat(array, 3, axis=-1)
    if array.shape[-1] == 3:
        array = np.concatenate([array, np.ones(array.shape[:2] + (1,), dtype=np.float32)], axis=-1)
    return array[..., :4]


def _layer_record(layer: Dict[str, Any], height: int, width: int, plane_bytes: int, byte_order: str) -> bytes:
    bo = byte_order
    name = str(layer.get("name") or "Layer")
    record = struct.pack(bo + "4i", 0, 0, height, width)
    record += struct.pack(bo + "H", 4)
    for channel_id in (-1, 0, 1, 2):                         # transparency, R, G, B
        record += struct.pack(bo + "hI", channel_id, 2 + plane_bytes)
    record += _key(b"8BIM", bo) + _key(BLEND_KEYS.get(str(layer.get("blend", "normal")).lower(), b"norm"), bo)
    opacity = max(0, min(int(layer.get("opacity", 255)), 255))
    flags = 0x08 | (0 if layer.get("visible", True) else 0x02)
    record += struct.pack("4B", opacity, 0, flags, 0)

    legacy_name = name.encode("latin-1", "replace")[:255]
    pascal = bytes([len(legacy_name)]) + legacy_name
    pascal += bytes((4 - len(pascal) % 4) % 4)
    unicode_name = name.encode("utf-16-be" if bo == ">" else "utf-16-le")
    luni = struct.pack(bo + "I", len(unicode_name) // 2) + unicode_name
    luni += bytes((4 - len(luni) % 4) % 4)
    extra = struct.pack(bo + "I", 0) + struct.pack(bo + "I", 0) + pascal        # no layer mask, no blending ranges
    extra += _key(b"8BIM", bo) + _key(b"luni", bo) + struct.pack(bo + "I", len(luni)) + luni
    return record + struct.pack(bo + "I", len(extra)) + extra


def layer_info_bytes(layers: List[Dict[str, Any]], depth: int = 8, byte_order: str = ">") -> bytes:
    """The Photoshop "layer info" structure: layer count, layer records, channel image data."""
    if depth not in (8, 16):
        raise ValueError("depth must be 8 or 16")
    prepared = [(_rgba(layer["pixels"]), layer) for layer in layers]
    if not prepared:
        raise ValueError("no layers")
    height, width = prepared[0][0].shape[:2]
    plane_bytes = height * width * (depth // 8)
    out = [struct.pack(byte_order + "h", len(prepared))]
    for pixels, layer in prepared:
        if pixels.shape[:2] != (height, width):
            raise ValueError(f"layer {layer.get('name')!r} is {pixels.shape[1]}x{pixels.shape[0]}, canvas is {width}x{height}")
        out.append(_layer_record(layer, height, width, plane_bytes, byte_order))
    compression = struct.pack(byte_order + "H", 0)
    for pixels, _ in prepared:
        for channel in (3, 0, 1, 2):
            out.append(compression)
            out.append(_plane(pixels[..., channel], depth))
    data = b"".join(out)
    return data + bytes(len(data) % 2)


def photoshop_tiff_block(layers: List[Dict[str, Any]], depth: int = 8, byte_order: str = "<") -> bytes:
    """Value for TIFF tag 37724 (ImageSourceData) so Photoshop shows the layers of a TIFF."""
    info = layer_info_bytes(layers, depth, byte_order)
    info += bytes((4 - len(info) % 4) % 4)
    key = b"Layr" if depth == 8 else b"Lr16"
    block = (TIFF_BLOCK_HEADER + _key(b"8BIM", byte_order) + _key(key, byte_order)
             + struct.pack(byte_order + "I", len(info)) + info)
    # global layer mask info with Photoshop's default values (Photoshop writes this block too)
    user_mask = b"\xff\xff" + bytes(10) + b"\x80\x00"
    block += (_key(b"8BIM", byte_order) + _key(b"LMsk", byte_order)
              + struct.pack(byte_order + "I", len(user_mask)) + user_mask + bytes(2))
    return block


def _resource(resource_id: int, data: bytes) -> bytes:
    block = b"8BIM" + struct.pack(">H", resource_id) + b"\x00\x00" + struct.pack(">I", len(data)) + data
    return block + bytes(len(data) % 2)


def write_psd(path: str, composite: Any, layers: List[Dict[str, Any]], depth: int = 16,
              icc_profile: Optional[bytes] = None) -> None:
    """
    composite: float array H x W x 3 (the flattened picture other programs show).
    Layers as described in the module docstring. depth 8 or 16.
    """
    flat = np.asarray(composite, dtype=np.float32)[..., :3]
    height, width = flat.shape[:2]
    info = layer_info_bytes(layers, depth, ">")
    header = b"8BPS" + struct.pack(">H", 1) + bytes(6) + struct.pack(">HIIHH", 3, height, width, depth, 3)
    resources = _resource(0x040F, icc_profile) if icc_profile else b""
    if depth == 16:
        padded = info + bytes((4 - len(info) % 4) % 4)
        body = struct.pack(">II", 0, 0) + b"8BIM" + b"Lr16" + struct.pack(">I", len(padded)) + padded
    else:
        body = struct.pack(">I", len(info)) + info + struct.pack(">I", 0)
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack(">I", 0))                               # colour mode data
        handle.write(struct.pack(">I", len(resources)) + resources)
        handle.write(struct.pack(">I", len(body)) + body)
        handle.write(struct.pack(">H", 0))                               # composite: uncompressed
        for channel in range(3):
            handle.write(_plane(flat[..., channel], depth))
