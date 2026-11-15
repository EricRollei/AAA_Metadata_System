"""
make_acceptance_set.py
Phase 0 of the v2 overhaul: build a set of test images whose metadata fields
each carry a unique, searchable marker token, so we can see exactly which
fields Lightroom Classic, XnView MP and Capture One index and display.

Usage (embedded Python):
    python tools/make_acceptance_set.py --out "A:/path/to/folder"

Requires: Pillow, psd-tools (for the PSD), exiftool on PATH.

Token scheme:  zq<field><fmt>
    field = 4-letter field code (see FIELDS below)
    fmt   = png | jpg | tif | web | psd
Example: "zqdescpng" is dc:description inside the PNG.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EXIFTOOL_CONFIG = os.path.join(HERE, "exiftool_hcai.config")

DIGITAL_SOURCE_TYPE = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

# (field code, exiftool tag, human label, formats it applies to or None for all)
# A value template of None means "use the token"; otherwise {t} is the token.
FIELDS: List[Tuple[str, str, str, object, object]] = [
    ("titl", "XMP-dc:Title", "XMP dc:title", None, None),
    ("desc", "XMP-dc:Description", "XMP dc:description", None, None),
    ("subj", "XMP-dc:Subject", "XMP dc:subject (keyword)", None, None),
    ("hier", "XMP-lr:HierarchicalSubject", "XMP lr:hierarchicalSubject", None, "zqhtop|{t}"),
    ("crea", "XMP-dc:Creator", "XMP dc:creator", None, None),
    ("rght", "XMP-dc:Rights", "XMP dc:rights", None, None),
    ("head", "XMP-photoshop:Headline", "XMP photoshop:Headline", None, None),
    ("inst", "XMP-photoshop:Instructions", "XMP photoshop:Instructions", None, None),
    ("tool", "XMP-xmp:CreatorTool", "XMP xmp:CreatorTool", None, None),
    ("cmod", "XMP-hcai:Model", "Custom namespace hcai:Model", None, None),
    ("cprm", "XMP-hcai:Prompt", "Custom namespace hcai:Prompt", None, None),
    ("icap", "IPTC:Caption-Abstract", "IPTC-IIM Caption", ("jpg", "tif", "psd"), None),
    ("ikey", "IPTC:Keywords", "IPTC-IIM Keywords", ("jpg", "tif", "psd"), None),
    ("ihed", "IPTC:Headline", "IPTC-IIM Headline", ("jpg", "tif", "psd"), None),
    ("edsc", "EXIF:ImageDescription", "EXIF ImageDescription", ("jpg", "tif", "web", "png"), None),
    ("eucm", "EXIF:UserComment", "EXIF UserComment", ("jpg", "tif", "web", "png"), None),
    ("xpkw", "EXIF:XPKeywords", "EXIF XPKeywords (Windows)", ("jpg", "tif"), None),
    ("xpcm", "EXIF:XPComment", "EXIF XPComment (Windows)", ("jpg", "tif"), None),
    ("parm", "PNG:Parameters", "PNG text chunk 'parameters' (A1111)", ("png",), None),
]

FORMATS: Dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "tif": "TIFF",
    "web": "WEBP",
    "psd": "PSD",
}

SIDE_TOKENS = {"subj": "zqsidesubj", "desc": "zqsidedesc"}


def _make_picture(fmt_code: str, size: int = 768) -> Image.Image:
    """A plain labelled card so the files are easy to tell apart in a grid."""
    colors = {"png": (40, 90, 160), "jpg": (160, 70, 40), "tif": (50, 130, 80),
              "web": (120, 60, 150), "psd": (150, 130, 40)}
    img = Image.new("RGB", (size, size), colors[fmt_code])
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, size - 40, size - 40], outline=(255, 255, 255), width=6)
    draw.text((80, 80), f"AAA metadata acceptance\n{FORMATS[fmt_code]}", fill=(255, 255, 255))
    return img


def _save_base(img: Image.Image, fmt_code: str, path: str) -> None:
    if fmt_code == "psd":
        from psd_tools import PSDImage
        PSDImage.frompil(img).save(path)
    elif fmt_code == "jpg":
        img.save(path, "JPEG", quality=92)
    elif fmt_code == "web":
        img.save(path, "WEBP", lossless=True)
    elif fmt_code == "tif":
        img.save(path, "TIFF", compression="tiff_lzw")
    else:
        img.save(path, "PNG")


def _run_exiftool(args: List[str]) -> Tuple[int, str]:
    cmd = ["exiftool", "-config", EXIFTOOL_CONFIG, "-charset", "utf8",
           "-overwrite_original", "-m"] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def build(out_dir: str) -> int:
    if shutil.which("exiftool") is None:
        print("exiftool not found on PATH")
        return 2
    os.makedirs(out_dir, exist_ok=True)

    rows: List[Dict[str, str]] = []
    problems: List[str] = []

    for fmt_code in FORMATS:
        ext = "webp" if fmt_code == "web" else ("tiff" if fmt_code == "tif" else fmt_code)
        path = os.path.join(out_dir, f"acceptance_{fmt_code}.{ext}")
        _save_base(_make_picture(fmt_code), fmt_code, path)

        args: List[str] = []
        for code, tag, label, only, template in FIELDS:
            if only is not None and fmt_code not in only:
                continue
            token = f"zq{code}{fmt_code}"
            value = template.format(t=token) if template else token
            args.append(f"-{tag}={value}")
            rows.append({"format": FORMATS[fmt_code], "field": label, "token": token,
                         "Lightroom": "", "XnView MP": "", "Capture One": ""})
        args.append(f"-XMP-iptcExt:DigitalSourceType={DIGITAL_SOURCE_TYPE}")
        args.append(path)
        code_rc, output = _run_exiftool(args)
        if code_rc != 0 or "1 image files updated" not in output:
            problems.append(f"{os.path.basename(path)}: {output}")

    # Sidecar-only test: a PNG with NO embedded metadata plus a .xmp next to it.
    side_png = os.path.join(out_dir, "acceptance_sidecar_only.png")
    _save_base(_make_picture("png"), "png", side_png)
    side_xmp = os.path.splitext(side_png)[0] + ".xmp"
    if os.path.exists(side_xmp):
        os.remove(side_xmp)
    code_rc, output = _run_exiftool([
        f"-XMP-dc:Subject={SIDE_TOKENS['subj']}",
        f"-XMP-dc:Description={SIDE_TOKENS['desc']}",
        side_xmp,
    ])
    if code_rc != 0:
        problems.append(f"sidecar: {output}")
    for code, label in (("subj", "Sidecar .xmp dc:subject"), ("desc", "Sidecar .xmp dc:description")):
        rows.append({"format": "PNG + .xmp", "field": label, "token": SIDE_TOKENS[code],
                     "Lightroom": "", "XnView MP": "", "Capture One": ""})

    csv_path = os.path.join(out_dir, "acceptance_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(FORMATS) + 1} images and {len(rows)} tokens to {out_dir}")
    print(f"Results sheet: {csv_path}")
    for line in problems:
        print(f"PROBLEM: {line}")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the metadata acceptance test set")
    parser.add_argument("--out", required=True, help="Output folder")
    sys.exit(build(parser.parse_args().out))
