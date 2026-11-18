"""
check_pack_load.py
Loads the whole pack the way ComfyUI does (CPU only, no server) and checks:
  * every node module loads (no "Error loading node module")
  * every node sits under "Eric's Nodes/...", superseded ones under Deprecated
  * Save True SVG v2, Save Qwen Layers v2 and the file extractors work on real files

    python tests_v2/check_pack_load.py

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import contextlib
import importlib
import io
import os
import sys
import tempfile
import traceback
import xml.etree.ElementTree as ET

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFY = os.path.dirname(os.path.dirname(PACK))
sys.path.insert(0, COMFY)
sys.argv = [sys.argv[0], "--cpu"]

SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- word cloud -->
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80" viewBox="0 0 200 80">
<style><![CDATA[ .a > .b { fill: red; } ]]></style>
<text x="10" y="40" xml:space="preserve">Hello <tspan fill="red">big</tspan> <tspan>world</tspan></text>
</svg>'''


def main() -> int:
    import comfy.options
    comfy.options.enable_args_parsing()
    import torch
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        # exactly ComfyUI's way (nodes.load_custom_node): the module is named after its disk path
        import importlib.util
        real_name = PACK.replace(".", "_x_")
        spec = importlib.util.spec_from_file_location(real_name, os.path.join(PACK, "__init__.py"))
        pack = importlib.util.module_from_spec(spec)
        sys.modules[real_name] = pack
        spec.loader.exec_module(pack)
    startup = buffer.getvalue().splitlines()
    # one copy only: the names old nodes import the pack by must be this very module
    by_alias = importlib.import_module("custom_nodes.AAA_Metadata_System")
    plain = importlib.import_module("AAA_Metadata_System")
    deep = importlib.import_module("custom_nodes.AAA_Metadata_System.eric_metadata.utils.workflow_parser")
    copies = {}
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None) or ""
        if module is not None and file.startswith(PACK) and "tests_v2" not in file:
            copies.setdefault(file, set()).add(id(module))
    twice = sorted(os.path.relpath(file, PACK) for file, ids in copies.items() if len(ids) > 1)
    loaded_lines = [line for line in startup if "nodes loaded" in line]
    single = (by_alias is pack and plain is pack and not twice and len(loaded_lines) == 1
              and deep is sys.modules.get(real_name + ".eric_metadata.utils.workflow_parser"))
    print(f"single load: ok={single} (alias names point at the loaded pack={by_alias is pack and plain is pack}, "
          f"modules loaded twice={twice[:6]}, 'nodes loaded' printed {len(loaded_lines)}x, "
          f"{len(copies)} pack modules, version {pack.__version__})")
    errors = [line for line in startup if "Error loading node module" in line or "not applied" in line
              or "not installed" in line]
    ok = not errors and single
    print(f"start-up: {len(startup)} console lines, {len(pack.NODE_CLASS_MAPPINGS)} nodes, load errors: {len(errors)}")
    for line in errors:
        print("   ", line[:300])

    sys.path.insert(0, PACK)
    from aaa_meta.categories import ROOT
    from aaa_meta.deprecation import DEPRECATED_CATEGORY, SUPERSEDED
    from aaa_meta.reader import read_file
    from aaa_meta.verify import read_tags
    outside = {node_id: getattr(cls, "CATEGORY", None) for node_id, cls in pack.NODE_CLASS_MAPPINGS.items()
               if not str(getattr(cls, "CATEGORY", "")).startswith(ROOT)}
    marked = [old for old in SUPERSEDED if old in pack.NODE_CLASS_MAPPINGS
              and pack.NODE_CLASS_MAPPINGS[old].CATEGORY == DEPRECATED_CATEGORY
              and pack.NODE_DISPLAY_NAME_MAPPINGS.get(old, "").endswith("(deprecated)")]
    dragged = [new for new in SUPERSEDED.values() if new in pack.NODE_CLASS_MAPPINGS
               and pack.NODE_CLASS_MAPPINGS[new].CATEGORY == DEPRECATED_CATEGORY]
    present = [old for old in SUPERSEDED if old in pack.NODE_CLASS_MAPPINGS and SUPERSEDED[old] in pack.NODE_CLASS_MAPPINGS]
    good = not outside and len(marked) == len(present) and not dragged
    ok = ok and good
    print(f"categories: outside the tree={outside} deprecated marked={len(marked)}/{len(present)} "
          f"new nodes wrongly in Deprecated={dragged}")
    tree = {}
    for node_id, cls in pack.NODE_CLASS_MAPPINGS.items():
        tree.setdefault(cls.CATEGORY, []).append(node_id)
    for category in sorted(tree):
        print(f"   {category}: {len(tree[category])}")

    nodes = pack.NODE_CLASS_MAPPINGS
    # ---- the v099d node id runs the v1.0 code, with v099d's widgets first and in order
    try:
        import json
        from PIL import Image
        v099d_module = sys.modules[real_name + ".nodes.eric_metadata_save_image_v099d"]
        original, upgraded = v099d_module.MetadataAwareSaveImage, nodes["MetadataAwareSaveImage_v099d"]
        old_types, new_types = original.INPUT_TYPES(), upgraded.INPUT_TYPES()
        same_order = all(list(new_types[s])[:len(old_types[s])] == list(old_types[s]) for s in ("required", "optional"))
        appended = list(new_types["optional"])[len(old_types["optional"]):]
        runs_v100 = issubclass(upgraded, nodes["AAA_SaveImageAll"]) and upgraded is not nodes["AAA_SaveImageAll"]
        outputs_kept = tuple(upgraded.RETURN_TYPES[:len(original.RETURN_TYPES)]) == tuple(original.RETURN_TYPES)
        values = {}                                           # only what a v099d workflow sends: v099d's own inputs
        for section in ("required", "optional"):
            for name, spec in old_types[section].items():
                if name == "images" or not isinstance(spec, tuple):
                    continue
                options = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
                if "default" in options:
                    values[name] = options["default"]
                elif isinstance(spec[0], list) and spec[0]:
                    values[name] = spec[0][0]
        values.pop("filename_prefix", None)
        with tempfile.TemporaryDirectory() as old_folder, contextlib.redirect_stdout(io.StringIO()):
            values.update({"custom_output_directory": old_folder, "file_format": "jpg", "keywords": "zqold",
                           "hash_models": False})          # a stray stored value from an older v099d layout
            old_prompt = {
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "zqoldModel.safetensors"}},
                "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a zqold harbour", "clip": ["1", 1]}},
                "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "seed": 7, "steps": 5,
                                                            "cfg": 2.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
                "9": {"class_type": "MetadataAwareSaveImage_v099d", "inputs": {"images": ["5", 0]}}}
            result = upgraded().save_with_metadata(torch.rand(1, 48, 64, 3), filename_prefix="oldid", prompt=old_prompt,
                                                   extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9", **values)
            path = result["result"][1]
            tags = read_tags(path) if path and os.path.isfile(path) else {}
        written = ("zqold harbour" in str(tags.get("XMP-dc:Description", "")) and "zqoldModel" in (tags.get("XMP-dc:Subject") or [])
                   and path.lower().endswith(".jpg"))
        good = same_order and runs_v100 and outputs_kept and written and upgraded.CATEGORY == DEPRECATED_CATEGORY \
            and nodes["AAA_SaveImageAll"].CATEGORY != DEPRECATED_CATEGORY
        first_id = nodes.get("MetadataAwareSaveImage_v100")
        aliases = getattr(nodes["AAA_SaveImageAll"], "SEARCH_ALIASES", [])
        named = (pack.NODE_DISPLAY_NAME_MAPPINGS["AAA_SaveImageAll"].startswith("AAA Save Image All")
                 and first_id is not None and issubclass(first_id, nodes["AAA_SaveImageAll"])
                 and first_id.CATEGORY == DEPRECATED_CATEGORY and not first_id.SEARCH_ALIASES and not upgraded.SEARCH_ALIASES
                 and all(word in aliases for word in ("psd", "layers", "color management", "lightroom", "xmp")))
        with_words = [i for i, cls in nodes.items() if getattr(cls, "SEARCH_ALIASES", None)]
        current = [i for i, cls in nodes.items() if cls.CATEGORY != DEPRECATED_CATEGORY]
        old_with_words = [i for i in with_words if nodes[i].CATEGORY == DEPRECATED_CATEGORY]
        named = named and not old_with_words and sorted(with_words) == sorted(current)
        print(f"search aliases: {len(with_words)} of {len(current)} current nodes have them, deprecated nodes with aliases={old_with_words}")
        good = good and named
        ok = ok and good
        print(f"save node name / first id kept / search aliases ({len(aliases)}): ok={named} "
              f"name={pack.NODE_DISPLAY_NAME_MAPPINGS['AAA_SaveImageAll']!r}")
        print(f"v099d id on v1.0 code: ok={good} widget order kept={same_order} appended={appended} outputs kept={outputs_kept} "
              f"JPEG saved with prompt + model keyword from v099d inputs only={written}")
        # saved workflows: how many values each stored v099d node carries, against the widgets v099d defines
        widget_types = ("INT", "FLOAT", "STRING", "BOOLEAN")
        expected = sum(1 for s in ("required", "optional") for spec in old_types[s].values()
                       if isinstance(spec, tuple) and (isinstance(spec[0], list) or spec[0] in widget_types))
        counts = {}
        workflow_root = os.path.join(COMFY, "user", "default", "workflows")
        for root, _dirs, files in os.walk(workflow_root):
            for name in files:
                if not name.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                except Exception:
                    continue
                stack = [data] if isinstance(data, dict) else []
                while stack:
                    item = stack.pop()
                    for node in item.get("nodes", []) if isinstance(item.get("nodes"), list) else []:
                        if isinstance(node, dict) and node.get("type") == "MetadataAwareSaveImage_v099d":
                            length = len(node.get("widgets_values") or [])
                            counts[length] = counts.get(length, 0) + 1
                    definitions = item.get("definitions")
                    if isinstance(definitions, dict):
                        stack.extend(d for d in definitions.get("subgraphs", []) if isinstance(d, dict))
        print(f"   saved workflows: v099d nodes by number of stored widget values {dict(sorted(counts.items()))}; "
              f"v099d defines {expected} widgets, the upgraded node {expected + len(appended)}")
    except Exception:
        ok = False
        print(f"v099d id on v1.0 code: EXCEPTION\n{traceback.format_exc()[-1500:]}")
    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "testModel_v1.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a zqpack lighthouse in fog", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "zqneg blurry", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 128, "height": 96, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                                                    "latent_image": ["4", 0], "seed": 4242, "steps": 9, "cfg": 3.5,
                                                    "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["6", 0]}},
    }
    with tempfile.TemporaryDirectory() as folder:
        # ---- Save True SVG v2
        try:
            saver = nodes["EricSaveTrueSVGImage_V2"]()
            path, summary = saver.save_svg_with_metadata(
                SVG, filename_prefix="svgcheck", custom_output_directory=os.path.join(folder, "svg"),
                output_path_mode="Absolute Path", title="Cloud & <title>", keywords="zqsvg, cloud", creator="Eric Hiss",
                custom_metadata='{"my key!": "v", "1bad": "x"}', save_xmp=True, save_workflow_as_json=False)
            text = open(path, encoding="utf-8").read()
            root = ET.fromstring(text.split("?>", 1)[1])
            tags = read_tags(path) or {}
            good = ('Hello <tspan fill="red">big</tspan> <tspan>world</tspan>' in text and "<![CDATA[" in text
                    and "<!-- word cloud -->" in text and root[0].tag.endswith("metadata")
                    and "zqsvg" in str(tags.get("XMP-dc:Subject")) and "Cloud" in str(tags.get("XMP-dc:Title"))
                    and os.path.isfile(os.path.splitext(path)[0] + ".xmp"))
            ok = ok and good
            print(f"Save True SVG v2: ok={good} title={tags.get('XMP-dc:Title')!r} keywords={tags.get('XMP-dc:Subject')}")
            if not good:
                print("   ", summary[:300], "|", sorted(k for k in tags if k.startswith("XMP"))[:8])
        except Exception:
            ok = False
            print(f"Save True SVG v2: EXCEPTION\n{traceback.format_exc()[-1500:]}")

        # ---- Save Qwen Layers v2
        try:
            layer_node = nodes["EricSaveQwenLayers_V2"]()
            layers = torch.rand(3, 96, 128, 4)
            for file_format in ("psd", "tiff"):
                output = layer_node.save_layers(layers, "layercheck", file_format, layer_names="Sky, Hill, Boat",
                                                blend_modes="normal, multiply, screen", opacities="255, 200, 128",
                                                custom_output_directory=os.path.join(folder, "layers_" + file_format),
                                                prompt=prompt, unique_id="9")
                path, summary = output[0], output[3]
                parsed = read_file(path)
                good = (parsed["standard"].get("description") == "a zqpack lighthouse in fog"
                        and "testModel_v1" in parsed["standard"].get("keywords", []) and "metadata verified" in summary)
                if file_format == "tiff":
                    from aaa_meta import psd_writer
                    stack = psd_writer.read_tiff_layers(path)
                    names = [layer["name"] for layer in stack]
                    good = good and sorted(names) == ["Boat", "Hill", "Sky"] and "Photoshop layers added" in summary
                    print(f"   tiff layers: {[(l['name'], l['blend'], l['opacity']) for l in stack]}")
                ok = ok and good
                print(f"Save Qwen Layers v2 {file_format}: ok={good}")
                if not good:
                    print("   ", summary[:500])
        except Exception:
            ok = False
            print(f"Save Qwen Layers v2: EXCEPTION\n{traceback.format_exc()[-1500:]}")

        # ---- file extractors: a v2-saved PNG (stored record) and an old-style PNG (workflow only)
        try:
            import json
            from PIL import Image
            from PIL.PngImagePlugin import PngInfo
            types = nodes["AAA_SaveImageAll"].INPUT_TYPES()
            defaults = {}
            for section in ("required", "optional"):
                for name, spec in types[section].items():
                    options = spec[1] if isinstance(spec, tuple) and len(spec) > 1 and isinstance(spec[1], dict) else {}
                    if "default" in options:
                        defaults[name] = options["default"]
            defaults.pop("filename_prefix", None)
            defaults["custom_output_directory"] = os.path.join(folder, "png")
            prompt_v100 = dict(prompt)
            prompt_v100["9"] = {"class_type": "AAA_SaveImageAll", "inputs": {"images": ["6", 0]}}
            new_png = nodes["AAA_SaveImageAll"]().save_with_metadata(
                torch.rand(1, 96, 128, 3), filename_prefix="extract", prompt=prompt_v100,
                extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9", **defaults)["result"][1]
            old_png = os.path.join(folder, "old.png")
            info = PngInfo()
            info.add_text("prompt", json.dumps(prompt))
            Image.new("RGB", (64, 64)).save(old_png, pnginfo=info)
            for label, path, origin in (("stored record", new_png, "stored"), ("old PNG", old_png, "workflow graph")):
                metadata, _json_text, summary = nodes["PngMetadataExtractorV4"]().extract_metadata(path)
                diag_info, _name, diag = nodes["PngInfoDiagnosticV4"]().diagnose_png(path)
                record = metadata.get("generation_record", {})
                good = (metadata.get("generation_source") == origin and record.get("positive") == "a zqpack lighthouse in fog"
                        and record.get("negative") == "zqneg blurry" and "Generation record" in summary
                        and diag.get("generation_source") == origin and "Generation record" in diag_info)
                ok = ok and good
                print(f"extractors on {label}: ok={good} source={metadata.get('generation_source')!r}")
                if not good:
                    print("   ", summary[-300:])
        except Exception:
            ok = False
            print(f"file extractors: EXCEPTION\n{traceback.format_exc()[-1500:]}")

    previews = os.path.join(COMFY, "output", "node_previews")
    if os.path.isdir(previews):
        for name in os.listdir(previews):
            if name.startswith("extract_"):
                os.remove(os.path.join(previews, name))
    print("PACK OK" if ok else "PACK PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
