"""
check_companions.py
End-to-end check of the companion nodes without the server (CPU only):
save with "AAA Save Image All PNG WebP JPG PSD TIFF SVG w Metadata", then Entry V3 / Add Measurements v1 /
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
        "9": {"class_type": "AAA_SaveImageAll", "inputs": {"images": ["6", 0]}},
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
                        and parsed["standard"].get("description", "") == "a zqcomp test harbour at dawn"
                        and all(k in keywords for k in ("zqfirst", "zqentry", "zqkeeper", "testModel_v1"))
                        and set(parsed["analysis"]) >= {"sharpness", "unipercept", "blur"}
                        and (parsed.get("record") or {}).get("positive", "").startswith("a zqcomp")
                        and not any(key.startswith("IPTC:") for key in tags))
                # an analysis node written for the old system: its write must also reach the eiqa namespace
                service = importlib.import_module(f"custom_nodes.{os.path.basename(PACK)}").MetadataService(debug=False)
                service.write_metadata(path, {"analysis": {"technical": {"blur": {"score": 412.5, "is_blurry": False}}}},
                                       targets=["embedded"])
                mirrored = read_file(path)
                mirror_ok = (mirrored["analysis"].get("technical", {}).get("blur", {}).get("score") == 412.5
                             and set(mirrored["analysis"]) >= {"sharpness", "unipercept", "blur", "technical"}
                             and mirrored["standard"].get("description", "") == "a zqcomp test harbour at dawn"
                             and mirrored["standard"].get("title") == "Entry title")
                good = good and mirror_ok
                ok = ok and good
                print(f"round trip {extension}: ok={good} old-service mirror={mirror_ok} model={model!r} sharpness={sharpness!r} "
                      f"rating={parsed['standard'].get('rating')} analysis={sorted(parsed['analysis'])} "
                      f"keywords={keywords}")
                if not good:
                    print("   after old-service write:", sorted(mirrored["analysis"]), "| desc:",
                          mirrored["standard"].get("description", "")[:90], "| title:", mirrored["standard"].get("title"))
                    print("   entry status:", status, "| measure:", measure_status, "| title:", parsed["standard"].get("title"),
                          "| iptc:", [k for k in tags if k.startswith("IPTC:")][:5],
                          "| desc:", parsed["standard"].get("description", "")[:80])
            except Exception:
                ok = False
                print(f"round trip {extension}: EXCEPTION\n{traceback.format_exc()[-1500:]}")
    # ---- load nodes: widgets as before, outputs added at the end, layers and 16-bit read back
    try:
        loaders = {}
        for new_module, new_class, old_module, old_class in (
                ("eric_load_image_extended_v2", "EricLoadImageExtendedV2", "eric_load_image_extended", "EricLoadImageExtended"),
                ("eric_load_image_with_layers_v2", "EricLoadImageWithLayersV2", "eric_load_image_with_layers", "EricLoadImageWithLayers")):
            new = getattr(importlib.import_module(base + new_module), new_class)
            old = getattr(importlib.import_module(base + old_module), old_class)
            same = all(list(new.INPUT_TYPES().get(s, {}).keys()) == list(old.INPUT_TYPES().get(s, {}).keys())
                       for s in ("required", "optional"))
            kept = tuple(new.RETURN_NAMES[:len(old.RETURN_NAMES)]) == tuple(old.RETURN_NAMES)
            ok = ok and same and kept
            loaders[new_class] = new()
            print(f"{new_class}: widgets identical={same} first outputs kept={kept} added={list(new.RETURN_NAMES[len(old.RETURN_NAMES):])}")
        with tempfile.TemporaryDirectory() as folder:
            ramp = torch.linspace(0, 1, 2048).view(1, 1, 2048, 1).repeat(1, 64, 1, 3).contiguous()
            defaults = {}
            for section in ("required", "optional"):
                for name, spec in types[section].items():
                    options = spec[1] if isinstance(spec, tuple) and len(spec) > 1 and isinstance(spec[1], dict) else {}
                    if "default" in options:
                        defaults[name] = options["default"]
            defaults.pop("filename_prefix", None)
            results = {}
            for label, extra in (("png16", {"file_format": "png", "bit_depth": "16-bit"}),
                                 ("tiff16_layers", {"file_format": "tiff", "bit_depth": "16-bit",
                                                    "overlay_layer_1": torch.rand(1, 64, 2048, 3), "overlay_1_name": "Glow",
                                                    "overlay_1_blend_mode": "screen", "overlay_1_opacity": 128}),
                                 ("tiff8_layers", {"file_format": "tiff",
                                                   "overlay_layer_1": torch.rand(1, 64, 2048, 3), "overlay_1_name": "Glow"})):
                values = dict(defaults)
                values.update(extra)
                values["custom_output_directory"] = os.path.join(folder, label)
                results[label] = saver.save_with_metadata(ramp, filename_prefix="comp", prompt=prompt,
                                                          extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9",
                                                          **values)["result"][1]
            # the load nodes read from ComfyUI's input folder: put copies there (removed again below)
            import shutil
            import folder_paths
            input_copies = []
            for label in list(results):
                name = f"aaa_check_{label}{os.path.splitext(results[label])[1]}"
                target = os.path.join(folder_paths.get_input_directory(), name)
                shutil.copyfile(results[label], target)
                input_copies.append(target)
                results[label] = name
            out = loaders["EricLoadImageExtendedV2"].load_image(results["png16"])
            levels = int(torch.unique(out[0][0, 0, :, 0]).numel())
            good = levels > 1500 and out[6].startswith("a zqcomp") and '"positive"' in out[8]
            ok = ok and good
            print(f"Extended v2 on 16-bit PNG: ok={good} distinct levels={levels} prompt={out[6][:30]!r}")
            for label in ("tiff16_layers", "tiff8_layers"):
                layered = loaders["EricLoadImageWithLayersV2"]
                everything = layered.load_image(results[label], load_mode="all_layers")
                glow = layered.load_image(results[label], load_mode="layer_by_name", layer_name="Glow")
                composite = layered.load_image(results[label], load_mode="composite")
                good = (everything[0].shape[0] == 2 and tuple(everything[0].shape[1:]) == (64, 2048, 3)
                        and "Main Image, Glow" in everything[4] and glow[0].shape[0] == 1 and "Selected: Glow" in glow[4]
                        and composite[5].startswith("a zqcomp") and composite[0].shape[0] >= 1)
                if label == "tiff16_layers":
                    good = good and int(torch.unique(everything[0][0, 0, :, 0]).numel()) > 1500
                ok = ok and good
                print(f"Layers v2 on {label}: ok={good} batch={tuple(everything[0].shape)} info={everything[4][:90]!r}")
    except Exception:
        ok = False
        print(f"load nodes: EXCEPTION\n{traceback.format_exc()[-1800:]}")
    finally:
        for target in locals().get("input_copies", []):
            try:
                os.remove(target)
            except OSError:
                pass

    previews = os.path.join(COMFY, "output", "node_previews")
    if os.path.isdir(previews):
        for name in os.listdir(previews):
            if name.startswith("comp_"):
                os.remove(os.path.join(previews, name))
    print("COMPANIONS OK" if ok else "COMPANIONS PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
