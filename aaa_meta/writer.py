"""
writer.py
One call that saves an image with catalog-searchable metadata, and one call
that adds measured data to a file that already exists.

    save_with_metadata(image, path, record=..., user=..., analysis=...)
    add_analysis(path, {"unipercept": {...}, "blur": {...}})

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Dict, Optional

from PIL import Image

from . import embed
from .a1111 import build_parameters
from .fields import StandardFields, UserFields, build_standard_fields
from .record import GenerationRecord
from .verify import verify_file
from .xmp_packet import build_packet

_EXIF_IFD = 0x8769
_USER_COMMENT = 0x9286


def _user_comment_exif(text: str) -> Image.Exif:
    """EXIF UserComment in the encoding A1111-style readers expect (UNICODE + UTF-16BE)."""
    exif = Image.Exif()
    exif.get_ifd(_EXIF_IFD)[_USER_COMMENT] = b"UNICODE\x00" + text.encode("utf-16-be")
    return exif


def _creator_tool(record: Optional[GenerationRecord]) -> str:
    version = record.comfyui_version if record is not None else None
    return f"ComfyUI {version}" if version else "ComfyUI"


def save_with_metadata(image: Image.Image, path: str, record: Optional[GenerationRecord] = None,
                       user: Optional[UserFields] = None, analysis: Optional[Dict[str, Any]] = None,
                       png_chunks: Optional[Dict[str, str]] = None, include_paths: bool = False,
                       a1111: bool = True, sidecar: bool = False, verify: bool = True,
                       **save_kwargs) -> Dict[str, Any]:
    """
    Saves `image` to `path` (format from the extension: png, jpg/jpeg, webp, tif/tiff)
    with the metadata embedded in the same pass.

    png_chunks     extra PNG text chunks, normally {"prompt": ..., "workflow": ...}
    include_paths  keep local disk paths of model files in the embedded record
    a1111          also write the A1111 parameters string (PNG chunk / EXIF UserComment)
    Returns {"path", "format", "embedded", "packet_bytes", "warnings", "verify"}.
    """
    extension = os.path.splitext(path)[1].lower().lstrip(".")
    fields: Optional[StandardFields] = None
    if record is not None or user is not None:
        fields = build_standard_fields(record or GenerationRecord(), user, _creator_tool(record))
    result: Dict[str, Any] = {"path": path, "format": extension, "embedded": True, "warnings": []}

    def packet(with_json: bool = True, omit_prompt_copy: bool = False) -> bytes:
        return build_packet(fields, record, analysis, include_paths, with_json, omit_prompt_copy)

    parameters = build_parameters(record) if (a1111 and record is not None) else ""
    xmp = packet()

    if extension == "png":
        chunks = dict(png_chunks or {})
        if parameters:
            chunks["parameters"] = parameters
        embed.save_png(image, path, xmp, chunks, **save_kwargs)
    elif extension in ("jpg", "jpeg"):
        # JPEG holds about 64 KB of XMP: shrink in steps, never silently.
        if len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False)
            result["warnings"].append("JPEG size limit: JSON copy of the record left out (structured fields kept)")
        if len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False, omit_prompt_copy=True)
            result["warnings"].append("JPEG size limit: second copy of the prompt left out (description keeps it)")
        if parameters and "exif" not in save_kwargs:
            exif = _user_comment_exif(parameters)
            if len(exif.tobytes()) < 60000:
                save_kwargs["exif"] = exif
            else:
                result["warnings"].append("JPEG size limit: A1111 parameters string left out")
        if not embed.save_jpeg(image, path, xmp, **save_kwargs):
            result["embedded"] = False
            result["warnings"].append(
                f"metadata ({len(xmp)} bytes) exceeds what a JPEG can hold; use PNG, TIFF or WebP for this image")
    elif extension == "webp":
        if parameters and "exif" not in save_kwargs:
            save_kwargs["exif"] = _user_comment_exif(parameters)
        embed.save_webp(image, path, xmp, **save_kwargs)
    elif extension in ("tif", "tiff"):
        embed.save_tiff(image, path, xmp, **save_kwargs)
    else:
        raise ValueError(f"save_with_metadata does not write .{extension}; save the file, then use update_metadata()")

    result["packet_bytes"] = len(xmp)
    if sidecar:
        result["sidecar"] = embed.write_sidecar(path, xmp)
    if verify:
        result["verify"] = verify_file(path, fields)
    return result


def update_metadata(path: str, record: Optional[GenerationRecord] = None, user: Optional[UserFields] = None,
                    analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False,
                    verify: bool = True) -> Dict[str, Any]:
    """Add or replace metadata in an existing file (any format exiftool writes, incl. PSD). Pixels untouched."""
    fields = None
    if record is not None or user is not None:
        fields = build_standard_fields(record or GenerationRecord(), user, _creator_tool(record))
    xmp = build_packet(fields, record, analysis, include_paths)
    ok, message = embed.update_file(path, xmp, merge=True)
    result: Dict[str, Any] = {"path": path, "embedded": ok, "packet_bytes": len(xmp),
                              "warnings": [] if ok else [message]}
    if verify and ok and fields is not None:
        result["verify"] = verify_file(path, fields)
    return result


def add_analysis(path: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Add measured data (eiqa namespace) to an existing file, keeping everything already in it."""
    return update_metadata(path, analysis=analysis, verify=False)
