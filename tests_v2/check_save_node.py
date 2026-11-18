"""
check_save_node.py
Offline checks (embedded Python, no server, no GPU, needs exiftool):
  1. the save core writes every format with the pack's real ICC profiles
  2. the bridge used by "AAA Save Image All PNG WebP JPG PSD TIFF SVG w Metadata" writes embedded metadata,
     the .xmp sidecar and the legacy .txt for a file the old writer produced,
     and keeps the workflow chunk already in the PNG

    python tests_v2/check_save_node.py

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import os
import sys
import tempfile

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PACK)


def _record():
    from aaa_meta.record import GenerationRecord
    path = os.path.join(PACK, "tests_v2", "fixtures_local", "record_live_qwen21.json")
    if os.path.isfile(path):
        return GenerationRecord.from_dict(json.load(open(path, encoding="utf-8")))
    return None


def check_core() -> bool:
    import numpy as np
    from aaa_meta import color
    from aaa_meta.save_core import SaveOptions, save_image
    from aaa_meta.verify import read_tags
    record = _record()
    profile_dir = os.path.join(PACK, "nodes", "profiles")
    ramp = np.linspace(0, 1, 1024, dtype=np.float32)[None, :, None].repeat(64, 0).repeat(3, 2).copy()
    ok = True
    cases = [("png", 8, color.PROFILE_SRGB), ("png", 16, color.PROFILE_ADOBE), ("tiff", 16, color.PROFILE_PROPHOTO),
             ("tiff", 8, color.PROFILE_SRGB), ("jpg", 8, color.PROFILE_ADOBE), ("webp", 8, color.PROFILE_SRGB)]
    with tempfile.TemporaryDirectory() as folder:
        for fmt, depth, profile in cases:
            path = os.path.join(folder, f"t_{depth}.{fmt}")
            result = save_image(ramp, path, SaveOptions(file_format=fmt, bit_depth=depth, color_profile=profile,
                                                        profile_dir=profile_dir, png_chunks={"prompt": "{}"}),
                                record=record)
            tags = read_tags(path) or {}
            verified = result.get("verify", {}).get("ok") if record is not None else "n/a"
            good = result["embedded"] and result["color_profile"] == profile and verified in (True, "n/a")
            ok = ok and good
            print(f"core  {fmt:5s} {depth:2d}-bit {profile:18s} verified={verified} "
                  f"icc='{tags.get('ICC_Profile:ProfileDescription')}' notes={result['warnings']}")
    return ok


class _FakeLegacyService:
    """Stands in for the old MetadataService: records what it was asked to write."""
    debug = False

    def __init__(self):
        self.calls = []

    def write_metadata(self, filepath, metadata, targets=None):
        self.calls.append((filepath, metadata, list(targets or [])))
        with open(os.path.splitext(filepath)[0] + ".txt", "w", encoding="utf-8") as handle:
            json.dump(metadata.get("ai_info", {}), handle, ensure_ascii=False)
        return True

    def _merge_metadata(self, a, b):
        return {**a, **b}


def check_bridge() -> bool:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    from aaa_meta.embed import read_xmp
    from aaa_meta.legacy_bridge import ServiceBridge, user_fields_from_widgets
    from aaa_meta.verify import read_tags
    from aaa_meta.xmp_packet import read_record_json
    record = _record()
    if record is None:
        print("bridge check skipped (no local record fixture)")
        return True
    ok = True
    with tempfile.TemporaryDirectory() as folder:
        legacy = _FakeLegacyService()
        bridge = ServiceBridge(legacy)
        widgets = {"title": "Courtyard", "keywords": "surreal, courtyard", "creator": "Eric Hiss",
                   "copyright": "(c) 2026 Eric Hiss", "description": "Test series A", "project": "Qwen tests",
                   "custom_metadata": "{\"client\": \"none\"}"}
        bridge.begin(record, user_fields_from_widgets(widgets), include_paths=False, a1111=True)
        assert bridge._merge_metadata({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}      # passes through to the old service
        for extension in ("png", "jpg", "tiff", "webp", "psd"):
            path = os.path.join(folder, f"old_writer.{extension}")
            image = Image.new("RGB", (96, 96), (30, 120, 90))
            if extension == "png":
                info = PngInfo()
                info.add_text("prompt", "{\"1\": {}}")
                info.add_text("workflow", "{\"nodes\": []}")
                image.save(path, pnginfo=info)
            elif extension == "psd":
                from psd_tools import PSDImage
                PSDImage.frompil(image).save(path)
            else:
                image.save(path)
            bridge.write_metadata(path, {"basic": {"title": "Courtyard"}, "analysis": {"unipercept": {"iaa": 70.5}}},
                                  targets=["embedded", "xmp", "txt"])
            tags = read_tags(path) or {}
            description = str(tags.get("XMP-dc:Description", ""))
            keywords = tags.get("XMP-dc:Subject") or []
            good = (description.startswith("Test series A") and record.positive[:40] in description
                    and "surreal" in keywords and "Qwen tests" in keywords
                    and tags.get("XMP-hcai:Project") == "Qwen tests"
                    and bool(tags.get("XMP-eiqa:Unipercept"))
                    and read_record_json(read_xmp(path) or b"") is not None
                    and os.path.isfile(os.path.splitext(path)[0] + ".xmp"))
            if extension == "png":
                good = good and bool(tags.get("PNG:Prompt")) and bool(tags.get("PNG:Workflow")) \
                    and "Seed:" in str(tags.get("PNG:Parameters", ""))
            if extension in ("jpg", "webp"):
                good = good and "Seed:" in str(tags.get("ExifIFD:UserComment", ""))
            ok = ok and good
            print(f"bridge {extension:5s} ok={good}")
        txt_call = legacy.calls[0][1].get("ai_info", {}).get("generation", {})
        txt_ok = txt_call.get("seed") == record.seed and bool(txt_call.get("prompt"))
        print(f"bridge legacy txt gets v2 values: {txt_ok}")
        print(bridge.summary()[:600])
        ok = ok and txt_ok
    return ok


if __name__ == "__main__":
    core_ok = check_core()
    print("CORE OK" if core_ok else "CORE PROBLEM")
    bridge_ok = check_bridge()
    print("BRIDGE OK" if bridge_ok else "BRIDGE PROBLEM")
    sys.exit(0 if core_ok and bridge_ok else 1)
