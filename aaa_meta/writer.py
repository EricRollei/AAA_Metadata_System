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
import struct
from typing import Any, Dict, Optional

from PIL import Image

from . import embed
from .a1111 import build_parameters
from .fields import StandardFields, UserFields, build_standard_fields
from .record import GenerationRecord
from .verify import verify_file
from .xmp_packet import build_packet, read_analysis_json

_EXIF_IFD = 0x8769
_USER_COMMENT = 0x9286


def _user_comment_exif(text: str) -> bytes:
    """
    A minimal EXIF block holding UserComment in the form A1111-style readers
    expect: type UNDEFINED, "UNICODE\\0" prefix, UTF-16BE text. Built by hand
    because Pillow writes this tag with the wrong EXIF type. Big-endian, like
    piexif's output, so the UTF-16BE text matches the block's byte order.
    """
    comment = b"UNICODE\x00" + text.encode("utf-16-be")
    exif_ifd_offset = 8 + 2 + 12 + 4                      # header + IFD0 with one entry
    data_offset = exif_ifd_offset + 2 + 2 * 12 + 4        # Exif IFD with two entries
    ifd0 = struct.pack(">H", 1) + struct.pack(">HHII", _EXIF_IFD, 4, 1, exif_ifd_offset) + struct.pack(">I", 0)
    exif_ifd = (struct.pack(">H", 2)
                + struct.pack(">HHI4s", 0x9000, 7, 4, b"0232")                       # ExifVersion
                + struct.pack(">HHII", _USER_COMMENT, 7, len(comment), data_offset)
                + struct.pack(">I", 0))
    return b"Exif\x00\x00" + b"MM\x00*" + struct.pack(">I", 8) + ifd0 + exif_ifd + comment


def _creator_tool(record: Optional[GenerationRecord]) -> str:
    version = record.comfyui_version if record is not None else None
    return f"ComfyUI {version}" if version else "ComfyUI"


def save_with_metadata(image: Image.Image, path: str, record: Optional[GenerationRecord] = None,
                       user: Optional[UserFields] = None, analysis: Optional[Dict[str, Any]] = None,
                       png_chunks: Optional[Dict[str, str]] = None, include_paths: bool = False,
                       a1111: bool = True, sidecar: bool = False, verify: bool = True,
                       pixels16: Any = None, icc_profile: Optional[bytes] = None,
                       **save_kwargs) -> Dict[str, Any]:
    """
    Saves `image` to `path` (format from the extension: png, jpg/jpeg, webp, tif/tiff)
    with the metadata embedded in the same pass.

    png_chunks     extra PNG text chunks, normally {"prompt": ..., "workflow": ...}
    include_paths  keep local disk paths of model files in the embedded record
    a1111          also write the A1111 parameters string (PNG chunk / EXIF UserComment)
    pixels16       float array (0..1) to write as true 16-bit (PNG and TIFF only); `image` is then unused
    icc_profile    ICC profile bytes to embed (pixels must already be in that colour space)
    Returns {"path", "format", "embedded", "packet_bytes", "warnings", "verify"}.
    """
    extension = os.path.splitext(path)[1].lower().lstrip(".")
    fields: Optional[StandardFields] = None
    if record is not None or user is not None:
        fields = build_standard_fields(record or GenerationRecord(), user, _creator_tool(record))
    result: Dict[str, Any] = {"path": path, "format": extension, "embedded": True, "warnings": []}

    def packet(with_json: bool = True, omit_prompt_copy: bool = False) -> bytes:
        return build_packet(fields, record, analysis, include_paths, with_json, omit_prompt_copy,
                            project=user.project if user else "", custom=user.custom if user else None)

    parameters = build_parameters(record) if (a1111 and record is not None) else ""
    has_metadata = fields is not None or record is not None or bool(analysis)
    xmp = packet() if has_metadata else None        # nothing to say: write no packet at all

    if icc_profile and pixels16 is None:
        save_kwargs["icc_profile"] = icc_profile

    if extension == "png":
        chunks = dict(png_chunks or {})
        if parameters:
            chunks["parameters"] = parameters
        if pixels16 is not None:
            from .pixels import save_png16
            save_png16(pixels16, path, xmp, chunks, icc_profile, save_kwargs.get("compress_level", 6))
        else:
            embed.save_png(image, path, xmp, chunks, **save_kwargs)
    elif extension in ("jpg", "jpeg"):
        # JPEG holds about 64 KB of XMP: shrink in steps, never silently.
        if xmp and len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False)
            result["warnings"].append("JPEG size limit: JSON copy of the record left out (structured fields kept)")
        if xmp and len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False, omit_prompt_copy=True)
            result["warnings"].append("JPEG size limit: second copy of the prompt left out (description keeps it)")
        if parameters and "exif" not in save_kwargs:
            exif = _user_comment_exif(parameters)
            if len(exif) < 60000:
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
        if pixels16 is not None:
            from .pixels import save_tiff16
            save_tiff16(pixels16, path, xmp, icc_profile, save_kwargs.get("compression16", "deflate"))
        else:
            save_kwargs.pop("compression16", None)
            embed.save_tiff(image, path, xmp, **save_kwargs)
    else:
        raise ValueError(f"save_with_metadata does not write .{extension}; save the file, then use update_metadata()")

    result["packet_bytes"] = len(xmp) if xmp else 0
    if sidecar and xmp:
        result["sidecar"] = embed.write_sidecar(path, xmp)
    if verify and xmp:
        result["verify"] = verify_file(path, fields)
    return result


def update_metadata(path: str, record: Optional[GenerationRecord] = None, user: Optional[UserFields] = None,
                    analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False,
                    verify: bool = True, a1111: bool = False, strip_iim: bool = False) -> Dict[str, Any]:
    """
    Add or replace metadata in an existing file (any format exiftool writes, incl. PSD).
    Pixels and everything else already in the file are kept.
    a1111: also write the A1111 parameters text (PNG text chunk, or EXIF UserComment for JPEG/WebP).
    strip_iim: remove old-style IPTC (IIM) from the file. Capture One shows IIM in
               preference to XMP on JPEG/TIFF, so a stale IIM block hides the new values.
    Measured data already in the file is kept: new analysis entries are added to it.
    """
    if analysis:
        analysis = {**read_analysis_json(embed.read_xmp(path)), **analysis}
    extension = os.path.splitext(path)[1].lower().lstrip(".")
    fields = None
    if record is not None or user is not None:
        fields = build_standard_fields(record or GenerationRecord(), user, _creator_tool(record))
    warnings = []

    def packet(with_json: bool = True, omit_prompt_copy: bool = False) -> bytes:
        return build_packet(fields, record, analysis, include_paths, with_json, omit_prompt_copy,
                            project=user.project if user else "", custom=user.custom if user else None)

    xmp = packet()
    if extension in ("jpg", "jpeg"):
        if len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False)
            warnings.append("JPEG size limit: JSON copy of the record left out (structured fields kept)")
        if len(xmp) > embed.JPEG_XMP_LIMIT:
            xmp = packet(with_json=False, omit_prompt_copy=True)
            warnings.append("JPEG size limit: second copy of the prompt left out (description keeps it)")
    ok, message = embed.update_file(path, xmp, merge=True, extra_args=["-iptc:all="] if strip_iim else None)
    if not ok:
        warnings.append(message)
    if ok and a1111 and record is not None:
        parameters = build_parameters(record)
        tag = {"png": "PNG:Parameters", "jpg": "ExifIFD:UserComment", "jpeg": "ExifIFD:UserComment",
               "webp": "ExifIFD:UserComment"}.get(extension)
        if tag and not (extension != "png" and len(parameters) > 20000):
            written, note = embed.write_text_tag(path, tag, parameters)
            if not written:
                warnings.append(f"A1111 parameters not written: {note}")
    result: Dict[str, Any] = {"path": path, "embedded": ok, "packet_bytes": len(xmp), "warnings": warnings}
    if verify and ok and fields is not None:
        result["verify"] = verify_file(path, fields)
    return result


def build_sidecar_packet(record: Optional[GenerationRecord] = None, user: Optional[UserFields] = None,
                         analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False) -> bytes:
    """The same packet the file gets, for writing as a .xmp sidecar."""
    fields = None
    if record is not None or user is not None:
        fields = build_standard_fields(record or GenerationRecord(), user, _creator_tool(record))
    return build_packet(fields, record, analysis, include_paths,
                        project=user.project if user else "", custom=user.custom if user else None)


_TEXT_FIELDS = ("title", "description", "creator", "rights", "headline", "instructions", "creator_tool",
                "digital_source_type")


def snapshot_standard(path: str) -> Dict[str, Optional[StandardFields]]:
    """
    The text fields a file and its sidecar hold right now, so they can be put back
    after the old writer has touched the file (it garbles an existing
    description when it rewrites it).
    """
    from . import reader

    def fields_of(packet: Optional[bytes]) -> Optional[StandardFields]:
        standard = reader.parse_packet(packet)["standard"] if packet else {}
        values = {name: str(standard[name]) for name in _TEXT_FIELDS if standard.get(name)}
        return StandardFields(**{"digital_source_type": "", **values}) if values else None

    return {"embedded": fields_of(embed.read_xmp(path)), "sidecar": fields_of(embed.read_sidecar(path))}


def _with_restored(fields: Optional[StandardFields], saved: Optional[StandardFields]) -> Optional[StandardFields]:
    if saved is None:
        return fields
    if fields is None:
        return saved
    merged = StandardFields(**{**vars(fields)})
    for name in _TEXT_FIELDS:
        if not getattr(merged, name):
            setattr(merged, name, getattr(saved, name))
    return merged


def patch_metadata(path: str, fields: Optional[StandardFields] = None, record: Optional[GenerationRecord] = None,
                   analysis: Optional[Dict[str, Any]] = None, rating: Optional[int] = None, project: str = "",
                   custom: Optional[Dict[str, Any]] = None, embedded: bool = True, sidecar: bool = False,
                   strip_iim: bool = False,
                   restore: Optional[Dict[str, Optional[StandardFields]]] = None) -> Dict[str, Any]:
    """
    Change only the given values in an existing file and / or its .xmp sidecar.
    Empty values are left alone (nothing is erased); keywords are added to the
    ones already there; measured data is added to what is already stored.
    restore: result of snapshot_standard() taken before another writer touched the
             file; those text fields are written back unless `fields` sets them.
    Returns {"embedded": bool|None, "sidecar": bool|None, "warnings": [...]}.
    """
    result: Dict[str, Any] = {"path": path, "embedded": None, "sidecar": None, "warnings": []}

    restore = restore or {}

    def packet_for(existing: Optional[bytes], target: str = "embedded") -> bytes:
        merged = {**read_analysis_json(existing), **analysis} if analysis else None
        return build_packet(_with_restored(fields, restore.get(target)), record, merged, project=project,
                            custom=custom, rating=rating)

    extension = os.path.splitext(path)[1].lower().lstrip(".")
    if embedded:
        xmp = packet_for(embed.read_xmp(path))
        if extension in ("jpg", "jpeg") and len(xmp) > embed.JPEG_XMP_LIMIT and record is not None:
            merged = {**read_analysis_json(embed.read_xmp(path)), **analysis} if analysis else None
            xmp = build_packet(_with_restored(fields, restore.get("embedded")), record, merged,
                               include_record_json=False, project=project, custom=custom, rating=rating)
            result["warnings"].append("JPEG size limit: JSON copy of the record left out")
        ok, message = embed.update_file(path, xmp, merge=True, extra_args=["-iptc:all="] if strip_iim else None)
        result["embedded"] = ok
        if not ok:
            result["warnings"].append(message)
    if sidecar:
        try:
            embed.write_sidecar(path, packet_for(embed.read_sidecar(path), "sidecar"), merge=True)
            result["sidecar"] = True
        except Exception as exc:
            result["sidecar"] = False
            result["warnings"].append(f"sidecar not written: {exc!r}")
    return result


def add_analysis(path: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Add measured data (eiqa namespace) to an existing file, keeping everything already in it."""
    return update_metadata(path, analysis=analysis, verify=False)
