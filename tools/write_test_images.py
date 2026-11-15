"""
write_test_images.py
Phase 2 check: writes one small image per format with a REAL generation record
through the new writer, verifies each with exiftool, and exercises the
"add measurements later" path. Import the output folder into Lightroom,
XnView MP and Capture One and search for a word from the prompt, the model
number, or the seed.

    python tools/write_test_images.py --record <record.json> --out <folder>

<record.json> is the record_json output of the "Generation Record (debug) v1" node.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                    # noqa: E402

from aaa_meta.embed import read_xmp                                  # noqa: E402
from aaa_meta.fields import UserFields                               # noqa: E402
from aaa_meta.record import GenerationRecord                         # noqa: E402
from aaa_meta.verify import read_tags                                # noqa: E402
from aaa_meta.writer import add_analysis, save_with_metadata, update_metadata   # noqa: E402
from aaa_meta.xmp_packet import read_record_json                     # noqa: E402

COLORS = {"png": (40, 90, 160), "jpg": (160, 70, 40), "tiff": (50, 130, 80), "webp": (120, 60, 150), "psd": (150, 130, 40)}
SAMPLE_ANALYSIS = {
    "unipercept": {"composite": 71.4, "iaa": 73.0, "iqa": 68.9, "ista": 72.2, "model": "UniPercept v1"},
    "blur_v7": {"variance": 0.412, "sharpness_class": "sharp", "regions": [{"name": "subject", "score": 0.61},
                                                                           {"name": "background", "score": 0.22}]},
    "noise_v4": {"digital_noise_level": 0.19, "film_grain": 0.03, "note": "clean, no JPEG artefacts"},
}


def card(label: str, color) -> Image.Image:
    image = Image.new("RGB", (768, 768), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 40, 728, 728], outline=(255, 255, 255), width=6)
    draw.text((80, 80), f"AAA writer test\n{label}", fill=(255, 255, 255))
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.record, "r", encoding="utf-8") as handle:
        record = GenerationRecord.from_dict(json.load(handle))
    os.makedirs(args.out, exist_ok=True)
    user = UserFields(creator="Eric Hiss", keywords=["writer test"])
    failures = 0

    for extension in ("png", "jpg", "tiff", "webp"):
        path = os.path.join(args.out, f"writer_test_{extension}.{extension}")
        result = save_with_metadata(card(extension.upper(), COLORS[extension]), path, record=record, user=user)
        report = result.get("verify", {})
        print(f"{extension:5s} packet={result['packet_bytes']:6d}B ok={report.get('ok')} "
              f"missing={report.get('missing')} mismatch={report.get('mismatch')} warnings={result['warnings']}")
        failures += 0 if report.get("ok") else 1

    # PSD: saved by psd-tools, metadata added afterwards without touching pixels
    try:
        from psd_tools import PSDImage
        path = os.path.join(args.out, "writer_test_psd.psd")
        PSDImage.frompil(card("PSD", COLORS["psd"])).save(path)
        result = update_metadata(path, record=record, user=user)
        report = result.get("verify", {})
        print(f"psd   packet={result['packet_bytes']:6d}B ok={report.get('ok')} missing={report.get('missing')} "
              f"mismatch={report.get('mismatch')} warnings={result['warnings']}")
        failures += 0 if report.get("ok") else 1
    except ImportError:
        print("psd   skipped (psd-tools not installed)")

    # measurements added later to an existing file: everything else must survive
    path = os.path.join(args.out, "writer_test_png.png")
    before = read_tags(path) or {}
    result = add_analysis(path, SAMPLE_ANALYSIS)
    after = read_tags(path) or {}
    kept = all(after.get(tag) == before.get(tag) for tag in
               ("XMP-dc:Description", "XMP-dc:Subject", "XMP-hcai:Seed", "PNG:Parameters"))
    measured = after.get("XMP-eiqa:Unipercept") or after.get("XMP-eiqa:unipercept")
    round_trip = read_record_json(read_xmp(path) or b"")
    print(f"add_analysis: written={result['embedded']} earlier fields kept={kept} "
          f"unipercept={measured} record still readable={bool(round_trip)} {result['warnings']}")
    failures += 0 if (result["embedded"] and kept and measured and round_trip) else 1

    print("ALL OK" if failures == 0 else f"{failures} PROBLEM(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
