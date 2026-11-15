"""
check_save_node.py
Offline checks for the v1.0 save node, run with the embedded Python (no server,
no GPU):
  1. the save core writes every format with the pack's real ICC profiles and
     exiftool confirms the metadata
  2. the node's V3 schema builds against this ComfyUI's comfy_api

    python tests_v2/check_save_node.py

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import importlib
import json
import os
import sys
import tempfile
import types

os.environ["CUDA_VISIBLE_DEVICES"] = ""
PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFY = os.path.dirname(os.path.dirname(PACK))
sys.path.insert(0, PACK)


def check_core() -> bool:
    import numpy as np
    from aaa_meta import color
    from aaa_meta.record import GenerationRecord
    from aaa_meta.save_core import SaveOptions, describe_result, save_image
    from aaa_meta.verify import read_tags

    record_path = os.path.join(PACK, "tests_v2", "fixtures_local", "record_live_qwen21.json")
    record = None
    if os.path.isfile(record_path):
        record = GenerationRecord.from_dict(json.load(open(record_path, encoding="utf-8")))
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
            profile_name = tags.get("ICC_Profile:ProfileDescription") or tags.get("ICC-header:ProfileDescription")
            bits = tags.get("PNG:BitDepth") or tags.get("IFD0:BitsPerSample") or tags.get("File:BitsPerSample")
            verified = result.get("verify", {}).get("ok") if record is not None else "n/a"
            good = result["embedded"] and result["color_profile"] == profile and verified in (True, "n/a")
            ok = ok and good
            print(f"{fmt:5s} {depth:2d}-bit {profile:18s} verified={verified} bits={bits} icc='{profile_name}' "
                  f"notes={result['warnings']}")
    return ok


def check_schema() -> bool:
    sys.path.insert(0, COMFY)
    sys.argv = [sys.argv[0], "--cpu"]
    import comfy.options
    comfy.options.enable_args_parsing()
    package = types.ModuleType("aaa_pkg")
    package.__path__ = [PACK]
    sys.modules["aaa_pkg"] = package
    module = importlib.import_module("aaa_pkg.nodes.eric_metadata_save_image_v100")
    node = module.NODE_CLASS_MAPPINGS["MetadataAwareSaveImage_v100"]
    schema = node.GET_SCHEMA()
    info = node.INPUT_TYPES()
    names = list(info.get("required", {})) + list(info.get("optional", {}))
    print("schema node_id:", schema.node_id, "| display:", schema.display_name)
    print("inputs:", names)
    print("hidden:", info.get("hidden"))
    print("outputs:", getattr(node, "RETURN_TYPES", None), "| output node:", getattr(node, "OUTPUT_NODE", None),
          "| function:", getattr(node, "FUNCTION", None))
    return schema.node_id == "MetadataAwareSaveImage_v100" and "format" in names


if __name__ == "__main__":
    core_ok = check_core()
    print("CORE OK" if core_ok else "CORE PROBLEM")
    try:
        schema_ok = check_schema()
        print("SCHEMA OK" if schema_ok else "SCHEMA PROBLEM")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"SCHEMA CHECK DID NOT RUN: {exc!r}")
        schema_ok = False
    sys.exit(0 if core_ok and schema_ok else 1)
