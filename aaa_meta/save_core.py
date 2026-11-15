"""
save_core.py
The work behind the save node, kept free of ComfyUI imports so it can be
tested on its own: takes float images and a set of options, writes the files.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from . import color, pixels
from .fields import UserFields
from .record import GenerationRecord
from .writer import save_with_metadata

EXTENSIONS = {"png": "png", "jpg": "jpg", "webp": "webp", "tiff": "tiff"}
_TIFF_COMPRESSION_8BIT = {"lzw": "tiff_lzw", "deflate": "tiff_adobe_deflate", "none": None}


@dataclass
class SaveOptions:
    file_format: str = "png"               # png | jpg | webp | tiff
    bit_depth: int = 8                     # 8 or 16 (16: png and tiff only)
    quality: int = 95                      # jpg / lossy webp
    lossless: bool = False                 # webp
    compress_level: int = 4                # png
    tiff_compression: str = "deflate"      # lzw | deflate | none
    color_profile: str = color.PROFILE_SRGB
    profile_dir: Optional[str] = None      # folder holding AdobeRGB1998.icc / ProPhoto.icm
    embed_metadata: bool = True
    embed_workflow: bool = True
    embed_a1111: bool = True
    include_model_paths: bool = False
    sidecar: bool = False
    verify: bool = True
    png_chunks: Dict[str, str] = field(default_factory=dict)   # prompt / workflow JSON


def save_image(image: np.ndarray, path: str, options: SaveOptions, record: Optional[GenerationRecord] = None,
               user: Optional[UserFields] = None, analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """image: float array HxWx3 or HxWx4, values 0..1, sRGB. Returns the writer's result dict."""
    notes: List[str] = []
    fmt = options.file_format
    data = np.asarray(image, dtype=np.float32)
    if fmt == "jpg":
        data = pixels.flatten_alpha(data)

    icc = color.icc_bytes(options.color_profile, options.profile_dir)
    profile = options.color_profile
    if profile in (color.PROFILE_ADOBE, color.PROFILE_PROPHOTO):
        if icc is None:
            notes.append(f"ICC profile file for {profile} not found: saved as sRGB instead")
            profile = color.PROFILE_SRGB
            icc = color.icc_bytes(profile)
        else:
            converted = color.convert_from_srgb(data[..., :3], profile)
            data = np.concatenate([converted, data[..., 3:]], axis=-1) if data.shape[-1] == 4 else converted
            if options.bit_depth == 8:
                notes.append(f"{profile} at 8-bit can show banding in smooth gradients; 16-bit PNG or TIFF avoids it")

    sixteen = options.bit_depth == 16 and fmt in ("png", "tiff")
    if options.bit_depth == 16 and not sixteen:
        notes.append(f"{fmt} has no 16-bit mode here: saved as 8-bit")

    save_kwargs: Dict[str, Any] = {}
    if fmt == "png":
        save_kwargs["compress_level"] = int(options.compress_level)
    elif fmt == "jpg":
        save_kwargs.update(quality=int(options.quality), subsampling=0 if options.quality >= 90 else 2)
    elif fmt == "webp":
        save_kwargs.update(quality=int(options.quality), lossless=bool(options.lossless))
    elif fmt == "tiff":
        if sixteen:
            if options.tiff_compression == "lzw":
                notes.append("16-bit TIFF uses deflate (LZW needs a codec that is not installed)")
            save_kwargs["compression16"] = "none" if options.tiff_compression == "none" else "deflate"
        else:
            compression = _TIFF_COMPRESSION_8BIT.get(options.tiff_compression, "tiff_adobe_deflate")
            if compression:
                save_kwargs["compression"] = compression
            save_kwargs["dpi"] = (300, 300)

    metadata_on = options.embed_metadata
    result = save_with_metadata(
        None if sixteen else pixels.to_pil(data), path,
        record=record if metadata_on else None,
        user=user if metadata_on else None,
        analysis=analysis if metadata_on else None,
        png_chunks=options.png_chunks if (metadata_on and options.embed_workflow) else None,
        include_paths=options.include_model_paths,
        a1111=options.embed_a1111 and metadata_on,
        sidecar=options.sidecar and metadata_on,
        verify=options.verify and metadata_on,
        pixels16=data if sixteen else None,
        icc_profile=icc,
        **save_kwargs)
    result["warnings"] = notes + result.get("warnings", [])
    result["color_profile"] = profile
    result["bit_depth"] = 16 if sixteen else 8
    return result


def describe_result(result: Dict[str, Any]) -> str:
    """One readable block per saved file for the node's summary output."""
    lines = [f"{os.path.basename(result['path'])}  ({result['bit_depth']}-bit, {result['color_profile']}, "
             f"metadata {result.get('packet_bytes', 0)} bytes)"]
    report = result.get("verify")
    if report is not None:
        if report.get("ok"):
            lines.append(f"  verified: {', '.join(report.get('present', []))}")
        else:
            if report.get("missing"):
                lines.append(f"  MISSING after save: {', '.join(report['missing'])}")
            if report.get("mismatch"):
                lines.append(f"  DIFFERENT from intended: {', '.join(report['mismatch'])}")
    for warning in result.get("warnings", []):
        lines.append(f"  note: {warning}")
    return "\n".join(lines)
