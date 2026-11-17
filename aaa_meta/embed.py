"""
embed.py
Gets an XMP packet into image files.

Two paths:
  save_*()       write pixels and metadata in one pass (PNG, JPEG, WebP, TIFF)
  update_file()  add / replace metadata in a file that already exists, pixels
                 untouched (any format exiftool can write, incl. PSD). This is
                 the path for classification results added after the save.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from .xmp_packet import merge_packets

PNG_XMP_KEY = "XML:com.adobe.xmp"
JPEG_XMP_LIMIT = 65000          # one APP1 segment; larger packets need another route
_exiftool_path: Optional[str] = None
_exiftool_checked = False


# ---------------------------------------------------------------------------
# exiftool
# ---------------------------------------------------------------------------
def find_exiftool() -> Optional[str]:
    global _exiftool_path, _exiftool_checked
    if not _exiftool_checked:
        _exiftool_checked = True
        _exiftool_path = shutil.which("exiftool")
        if _exiftool_path is None:
            for candidate in (r"C:\Program Files\exiftool\exiftool.exe", r"C:\Windows\exiftool.exe"):
                if os.path.isfile(candidate):
                    _exiftool_path = candidate
                    break
    return _exiftool_path


def run_exiftool(args: List[str], binary_output: bool = False, timeout: int = 120) -> Tuple[int, bytes, str]:
    """
    Run exiftool with its arguments passed through a UTF-8 argument file, so
    Unicode paths and values survive on Windows. Returns (returncode, stdout, stderr).
    """
    exe = find_exiftool()
    if exe is None:
        return 127, b"", "exiftool not found"
    handle = tempfile.NamedTemporaryFile("w", suffix=".args", delete=False, encoding="utf-8", newline="\n")
    try:
        handle.write("-charset\nfilename=utf8\n")
        for arg in args:
            handle.write(arg.replace("\r", " ").replace("\n", " ") + "\n")
        handle.close()
        creation = 0x08000000 if os.name == "nt" else 0          # no console window
        proc = subprocess.run([exe, "-@", handle.name], capture_output=True, timeout=timeout,
                              creationflags=creation)
        return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", errors="replace")
    except Exception as exc:
        return 1, b"", repr(exc)
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# save pixels + metadata in one pass
# ---------------------------------------------------------------------------
def save_png(image: Image.Image, path: str, xmp: Optional[bytes] = None,
             text_chunks: Optional[Dict[str, str]] = None, **save_kwargs) -> None:
    """text_chunks: e.g. {"prompt": json, "workflow": json, "parameters": a1111 string}."""
    info = PngInfo()
    for key, value in (text_chunks or {}).items():
        if value:
            info.add_text(key, value)
    if xmp:
        info.add_itxt(PNG_XMP_KEY, xmp.decode("utf-8"))
    image.save(path, "PNG", pnginfo=info, **save_kwargs)


def save_jpeg(image: Image.Image, path: str, xmp: Optional[bytes] = None, **save_kwargs) -> bool:
    """Returns False when the packet was too large for a JPEG segment and was not embedded."""
    if image.mode not in ("RGB", "L", "CMYK"):
        image = image.convert("RGB")
    if xmp and len(xmp) <= JPEG_XMP_LIMIT:
        image.save(path, "JPEG", xmp=xmp, **save_kwargs)
        return True
    image.save(path, "JPEG", **save_kwargs)
    return not xmp


def save_webp(image: Image.Image, path: str, xmp: Optional[bytes] = None, **save_kwargs) -> None:
    if xmp:
        save_kwargs["xmp"] = xmp
    image.save(path, "WEBP", **save_kwargs)


def save_tiff(image: Image.Image, path: str, xmp: Optional[bytes] = None, **save_kwargs) -> None:
    if xmp:
        tiffinfo = save_kwargs.pop("tiffinfo", None) or {}
        tiffinfo[700] = xmp                      # XMLPacket tag
        save_kwargs["tiffinfo"] = tiffinfo
    image.save(path, "TIFF", **save_kwargs)


# ---------------------------------------------------------------------------
# read / update existing files
# ---------------------------------------------------------------------------
def read_xmp(path: str) -> Optional[bytes]:
    """The file's XMP packet, or None. Tries Pillow first, then exiftool."""
    try:
        with Image.open(path) as image:
            raw = image.info.get("xmp") or image.info.get(PNG_XMP_KEY)
            if raw is None and hasattr(image, "tag_v2"):
                raw = image.tag_v2.get(700)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if raw:
            return bytes(raw)
    except Exception:
        pass
    code, out, _ = run_exiftool(["-xmp", "-b", path], binary_output=True)
    return out if code == 0 and out.strip() else None


def update_file(path: str, packet: bytes, merge: bool = True,
                extra_args: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Put `packet` into an existing file without touching its pixels.
    merge=True keeps what is already there (see xmp_packet.merge_packets).
    extra_args: further exiftool arguments for the same pass (e.g. "-iptc:all=").
    Returns (ok, message).
    """
    if find_exiftool() is None:
        return False, "exiftool not found"
    final = merge_packets(read_xmp(path), packet) if merge else packet
    temp = tempfile.NamedTemporaryFile("wb", suffix=".xmp", delete=False)
    try:
        temp.write(final)
        temp.close()
        code, out, err = run_exiftool(["-overwrite_original", "-m", *(extra_args or []), f"-xmp<={temp.name}", path])
        text = (out.decode("utf-8", errors="replace") + " " + err).strip()
        return (code == 0 and "1 image files updated" in text), text
    finally:
        try:
            os.unlink(temp.name)
        except OSError:
            pass


def write_text_tag(path: str, tag: str, text: str) -> Tuple[bool, str]:
    """Set one text tag (e.g. PNG:Parameters) from a temp file, so newlines and Unicode survive."""
    temp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8", newline="")
    try:
        temp.write(text)
        temp.close()
        code, out, err = run_exiftool(["-overwrite_original", "-m", "-charset", "exif=utf8",
                                       f"-{tag}<={temp.name}", path])
        message = (out.decode("utf-8", errors="replace") + " " + err).strip()
        return (code == 0 and "1 image files updated" in message), message
    finally:
        try:
            os.unlink(temp.name)
        except OSError:
            pass


def write_binary_tag(path: str, tag: str, data: bytes) -> Tuple[bool, str]:
    """Set one binary tag from bytes (exiftool "-TAG<=file"). Everything else in the file is kept."""
    temp = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    try:
        temp.write(data)
        temp.close()
        code, out, err = run_exiftool(["-overwrite_original", "-m", f"-{tag}<={temp.name}", path])
        text = (out.decode("utf-8", "replace") if isinstance(out, bytes) else str(out)) + " " + str(err)
        ok = code == 0 and "1 image files updated" in text
        return ok, "" if ok else text.strip()[:300]
    finally:
        try:
            os.unlink(temp.name)
        except OSError:
            pass


def sidecar_path(image_path: str) -> str:
    return os.path.splitext(image_path)[0] + ".xmp"


def read_sidecar(image_path: str) -> Optional[bytes]:
    try:
        with open(sidecar_path(image_path), "rb") as handle:
            return handle.read() or None
    except OSError:
        return None


def write_sidecar(image_path: str, packet: bytes, merge: bool = False) -> str:
    """merge=True keeps what an existing sidecar already holds."""
    sidecar = sidecar_path(image_path)
    if merge:
        packet = merge_packets(read_sidecar(image_path), packet)
    with open(sidecar, "wb") as handle:
        handle.write(packet)
    return sidecar
