"""
pixels.py
Turns float image data (0..1, HxWx3 or HxWx4) into 8-bit or true 16-bit files.

Pillow has no 16-bit RGB mode, so 16-bit PNG is written by a small encoder
here and 16-bit TIFF by tifffile. Both carry the same metadata as the 8-bit
paths (XMP, ICC profile, PNG text chunks).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import struct
import zlib
from typing import Dict, Optional

import numpy as np
from PIL import Image

PNG_XMP_KEY = "XML:com.adobe.xmp"


def to_uint8(pixels: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(pixels * 255.0), 0, 255).astype(np.uint8)


def to_uint16(pixels: np.ndarray) -> np.ndarray:
    """Real 16-bit quantisation of the float data (not 8-bit values multiplied up)."""
    return np.clip(np.rint(pixels.astype(np.float64) * 65535.0), 0, 65535).astype(np.uint16)


def to_pil(pixels: np.ndarray) -> Image.Image:
    data = to_uint8(pixels)
    if data.ndim == 2:
        return Image.fromarray(data, "L")
    return Image.fromarray(data, "RGBA" if data.shape[2] == 4 else "RGB")


def flatten_alpha(pixels: np.ndarray, matte=(1.0, 1.0, 1.0)) -> np.ndarray:
    """Composite RGBA over a solid colour (for formats without transparency)."""
    if pixels.ndim != 3 or pixels.shape[2] != 4:
        return pixels
    alpha = pixels[..., 3:4]
    return pixels[..., :3] * alpha + np.asarray(matte, dtype=pixels.dtype) * (1.0 - alpha)


# ---------------------------------------------------------------------------
# 16-bit PNG
# ---------------------------------------------------------------------------
def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _text_chunk(key: str, value: str) -> bytes:
    try:
        return _chunk(b"tEXt", key.encode("latin-1") + b"\x00" + value.encode("latin-1"))
    except UnicodeEncodeError:
        return _chunk(b"iTXt", key.encode("latin-1") + b"\x00\x00\x00\x00\x00" + value.encode("utf-8"))


def save_png16(pixels: np.ndarray, path: str, xmp: Optional[bytes] = None,
               text_chunks: Optional[Dict[str, str]] = None, icc_profile: Optional[bytes] = None,
               compress_level: int = 6) -> None:
    data = to_uint16(pixels)
    if data.ndim == 2:
        data = data[..., None]
    height, width, channels = data.shape
    color_type = {1: 0, 2: 4, 3: 2, 4: 6}[channels]
    raw = np.ascontiguousarray(data.astype(">u2")).view(np.uint8).reshape(height, width * channels * 2)
    # PNG "Up" filter: each row stored as the difference from the row above.
    filtered = raw.copy()
    filtered[1:] = raw[1:] - raw[:-1]
    rows = np.empty((height, raw.shape[1] + 1), dtype=np.uint8)
    rows[:, 0] = 2
    rows[:, 1:] = filtered
    parts = [b"\x89PNG\r\n\x1a\n",
             _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16, color_type, 0, 0, 0))]
    if icc_profile:
        parts.append(_chunk(b"iCCP", b"ICC Profile\x00\x00" + zlib.compress(icc_profile)))
    for key, value in (text_chunks or {}).items():
        if value:
            parts.append(_text_chunk(key, value))
    if xmp:
        parts.append(_chunk(b"iTXt", PNG_XMP_KEY.encode("latin-1") + b"\x00\x00\x00\x00\x00" + xmp))
    parts.append(_chunk(b"IDAT", zlib.compress(rows.tobytes(), compress_level)))
    parts.append(_chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(b"".join(parts))


# ---------------------------------------------------------------------------
# 16-bit TIFF
# ---------------------------------------------------------------------------
def save_tiff16(pixels: np.ndarray, path: str, xmp: Optional[bytes] = None,
                icc_profile: Optional[bytes] = None, compression: str = "deflate", dpi: int = 300) -> None:
    import tifffile
    data = to_uint16(pixels)
    extratags = []
    if xmp:
        extratags.append((700, "B", len(xmp), xmp, True))
    if icc_profile:
        extratags.append((34675, "B", len(icc_profile), icc_profile, True))
    kwargs = {"photometric": "rgb" if data.ndim == 3 and data.shape[2] >= 3 else "minisblack",
              "extratags": extratags, "resolution": (dpi, dpi), "resolutionunit": "INCH", "metadata": None}
    if data.ndim == 3 and data.shape[2] == 4:
        kwargs["extrasamples"] = ["unassalpha"]
    if compression == "deflate":
        kwargs["compression"] = "zlib"
    tifffile.imwrite(path, data, **kwargs)
