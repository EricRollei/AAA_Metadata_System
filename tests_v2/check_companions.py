"""
check_companions.py
End-to-end check of the companion nodes without the server (CPU only):
save with "Metadata Save Image v1.0", then Entry V3 / Add Measurements v1 /
Query V4 on the saved file, and confirm nothing already stored was lost.
Also confirms every new version has exactly the widgets of the one before it.

    python tests_v2/check_companions.py

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import importlib
import os
import sys
import tempfile
import traceback

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFY = os.path.dirname(os.path.dirname(PACK))
sys.path.insert(0, COMFY)
sys.argv = [sys.argv[0], "--cpu"]

PAIRS = [   # new module, new class, old module, old class
    ("eric_metadata_entry_v3", "EricMetadataEntryNodeV3", "eric_metadata_entry_v2", "EricMetadataEntryNodeV2"),
    ("eric_metadata_query_node_v4", "MetadataQueryNodeV4", "eric_metadata_query_node_v3", "MetadataQueryNodeV3"),
    ("eric_metadata_filter_v3", "MetadataFilterNodeV3", "eric_metadata_filter_v2", "MetadataFilterNodeV2"),
    ("eric_enhanced_metadata_filter_v3", "EnhancedMetadataFilterNode_V3", "eric_enhanced_metadata_filter_v2", "EnhancedMetadataFilterNode_V2"),
    ("eric_metadata_debugger_v3", "MetadataDebugNodeV3", "eric_metadata_debugger_v2", "MetadataDebugNodeV2"),
    ("eric_metadata_consolidator_node_v3", "MetadataConsolidatorNode_V3", "eric_metadata_consolidator_node_v2", "MetadataConsolidatorNode_V2"),
]


def main() -> int:
    import comfy.options
    comfy.options.enable_args_parsing()
    import torch
    base = f"custom_nodes.{os.path.basename(PACK)}.nodes."
    sys.path.insert(0, PACK)
    from aaa_meta.reader import read_file
    from aaa_meta.verify import read_tags
    ok = True
    classes = {}
    for new_module, new_class, old_module, old_class in PAIRS:
        try:
            new = getattr(importlib.import_module(base + new_module), new_class)
            old = getattr(importlib.import_module(base + old_module), old_class)
            same = all(list(new.INPUT_TYPES().get(s, {}).keys()) == list(old.INPUT_TYPES().get(s, {}).keys())
                       for s in ("required", "optional"))
            instance = new()
            wrapped = type(instance.metadata_service).__name__ == "CompanionService"
            classes[new_class] = instance
            ok = ok and same and wrapped
            print(f"{new_class}: widgets identical={same} service wrapped={wrapped}")
        except Exception:
            ok = False
            print(f"{new_class}: EXCEPTION\n{traceback.format_exc()[-1200:]}")

    save_module = importlib.import_module(base + "eric_metadata_save_image_v100")
    measure_module = importlib.import_module(base + "eric_metadata_add_measurements_v1")
    saver = save_module.MetadataAwareSaveImageV100()
    types = saver.INPUT_TYPES()
    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "testModel_v1.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a zqcomp test harbour at dawn", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 128, "height": 128, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["2", 0],
                                                    "latent_image": ["4", 0], "seed": 777, "steps": 12, "cfg": 4.0,
                                                    "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "MetadataAwareSaveImage_v100", "inputs": {"images": ["6", 0]}},
    }
    image = torch.rand(1, 128, 128, 3)
    with tempfile.TemporaryDirectory() as folder:
        for extension in ("png", "jpg", "tiff"):
            defaults = {}
            for section in ("required", "optional"):
                for name, spec in types[section].items():
                    options = spec[1] if isinstance(spec, tuple) and len(spec) > 1 and isinstance(spec[1], dict) else {}
                    if "default" in options:
                        defaults[name] = options["default"]
            defaults.update({"file_format": extension, "custom_output_directory": os.path.join(folder, extension),
                             "keywords": "zqfirst"})
            defaults.pop("filename_prefix", None)
            try:
                path = saver.save_with_metadata(image, filename_prefix="comp", prompt=prompt,
                                                extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9",
                                                **defaults)["result"][1]
                entry = classes["EricMetadataEntryNodeV3"]
                _, status, success = entry.add_metadata(image, path, title="Entry title", keywords="zqentry",
                                                        rating="4", write_to_xmp=False, embed_metadata=True,
                                                        debug_logging=False)
                measure = measure_module.EricMetadataAddMeasurementsV1()
                measure.add_measurements(path, '{"sharpness": 0.82, "unipercept": {"iaa": 70.5, "note": "soft corners"}}')
                _, _, measure_status = measure.add_measurements(path, "0.31", group_name="blur", keywords="zqkeeper")
                query = classes["MetadataQueryNodeV4"]
                model = query.query_metadata(path, "simple", "ai_info.generation.model", "unknown")[0]
                query.last_filepath = None
                sharpness = query.query_metadata(path, "simple", "analysis.sharpness", "unknown")[0]
                parsed = read_file(path)
                tags = read_tags(path) or {}
                keywords = parsed["standard"].get("keywords", [])
                good = (success and "testModel_v1" in str(model) and "0.82" in str(sharpness)
                        and parsed["standard"].get("title") == "Entry title" and parsed["standard"].get("rating") == 4
                        and "zqcomp test harbour" in parsed["standard"].get("description", "")
                        and all(k in keywords for k in ("zqfirst", "zqentry", "zqkeeper", "testModel_v1"))
                        and set(parsed["analysis"]) >= {"sharpness", "unipercept", "blur"}
                        and (parsed.get("record") or {}).get("positive", "").startswith("a zqcomp")
                        and not any(key.startswith("IPTC:") for key in tags))
                ok = ok and good
                print(f"round trip {extension}: ok={good} model={model!r} sharpness={sharpness!r} "
                      f"rating={parsed['standard'].get('rating')} analysis={sorted(parsed['analysis'])} "
                      f"keywords={keywords}")
                if not good:
                    print("   entry status:", status, "| measure:", measure_status, "| title:", parsed["standard"].get("title"),
                          "| iptc:", [k for k in tags if k.startswith("IPTC:")][:5],
                          "| desc:", parsed["standard"].get("description", "")[:80])
            except Exception:
                ok = False
                print(f"round trip {extension}: EXCEPTION\n{traceback.format_exc()[-1500:]}")
    previews = os.path.join(COMFY, "output", "node_previews")
    if os.path.isdir(previews):
        for name in os.listdir(previews):
            if name.startswith("comp_"):
                os.remove(os.path.join(previews, name))
    print("COMPANIONS OK" if ok else "COMPANIONS PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
