"""
check_node_v100.py
End-to-end check of "Metadata Save Image v1.0" without the server (CPU only):
  * its widgets are exactly v099d's, same order, with the new ones appended
  * it really saves files into a chosen folder and the metadata verifies

    python tests_v2/check_node_v100.py

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
import sys
import tempfile
import traceback

PACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFY = os.path.dirname(os.path.dirname(PACK))
sys.path.insert(0, COMFY)
sys.argv = [sys.argv[0], "--cpu"]


def main() -> int:
    import comfy.options
    comfy.options.enable_args_parsing()
    import importlib
    import torch
    pack_name = os.path.basename(PACK)
    old_module = importlib.import_module(f"custom_nodes.{pack_name}.nodes.eric_metadata_save_image_v099d")
    new_module = importlib.import_module(f"custom_nodes.{pack_name}.nodes.eric_metadata_save_image_v100")
    old_types = old_module.MetadataAwareSaveImage.INPUT_TYPES()
    new_types = new_module.MetadataAwareSaveImageV100.INPUT_TYPES()
    ok = True
    for section in ("required", "optional"):
        old_names = list(old_types.get(section, {}).keys())
        new_names = list(new_types.get(section, {}).keys())
        same = new_names[:len(old_names)] == old_names
        ok = ok and same
        print(f"{section}: v099d {len(old_names)} widgets, v1.0 {len(new_names)}; order kept={same}; "
              f"appended={new_names[len(old_names):]}")

    node = new_module.MetadataAwareSaveImageV100()
    from aaa_meta_tags import read_tags
    gradient = torch.linspace(0, 1, 256).view(1, 1, 256, 1).repeat(1, 128, 1, 3).contiguous()
    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "testModel_v1.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a zqnode test courtyard at dusk", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 256, "height": 128, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                                                    "latent_image": ["4", 0], "seed": 1234567, "steps": 20, "cfg": 5.5,
                                                    "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "MetadataAwareSaveImage_v100", "inputs": {"images": ["6", 0]}},
    }
    cases = [
        {"file_format": "png"},
        {"file_format": "png", "bit_depth": "16-bit", "color_profile": "Adobe RGB"},
        {"file_format": "jpg", "additional_format": "webp"},
        {"file_format": "tiff", "bit_depth": "16-bit", "color_profile": "ProPhoto RGB"},
        {"file_format": "psd"},
        {"file_format": "webp"},
        {"file_format": "png", "color_profile": "Display P3"},
        {"file_format": "jpg", "color_profile": "Adobe RGB"},
        {"file_format": "webp", "color_profile": "ProPhoto RGB"},
        {"file_format": "apng"},
        {"file_format": "psd", "_layers": True},
        {"file_format": "tiff", "_layers": True},
        {"file_format": "png", "_layers": True},
        {"file_format": "psd", "bit_depth": "16-bit", "_layers": True},
        {"file_format": "psd", "bit_depth": "16-bit", "color_profile": "ProPhoto RGB"},
        {"file_format": "tiff", "bit_depth": "16-bit", "_layers": True},
        {"file_format": "jpg", "color_profile": "Display P3"},
    ]
    with tempfile.TemporaryDirectory() as folder:
        for number, case in enumerate(cases):
            target = os.path.join(folder, f"case{number}")
            defaults = {}
            for section in ("required", "optional"):
                for name, spec in new_types[section].items():
                    if name in ("images",) or not isinstance(spec, tuple):
                        continue
                    options = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
                    if "default" in options:
                        defaults[name] = options["default"]
                    elif isinstance(spec[0], list) and spec[0]:
                        defaults[name] = spec[0][0]
            defaults.update({k: v for k, v in case.items() if not k.startswith("_")})
            if case.get("_layers"):
                yy, xx = torch.meshgrid(torch.linspace(0, 1, 128), torch.linspace(0, 1, 256), indexing="ij")
                glow = torch.exp(-(((xx - 0.7) / 0.18) ** 2 + ((yy - 0.4) / 0.3) ** 2))     # soft disc, right of centre
                glow_rgb = torch.stack([glow, glow * 0.8, glow * 0.3], dim=-1)[None]
                left_half = (xx < 0.5).float()[None, ..., None].repeat(1, 1, 1, 3)
                top_half = (yy < 0.5).float()[None, ..., None]
                defaults.update({"overlay_layer_1": glow_rgb, "overlay_1_name": "Glow",
                                 "overlay_1_blend_mode": "screen", "overlay_1_opacity": 128,
                                 "mask_layer_1": left_half, "mask_1_name": "Subject",
                                 "mask_layer_2": top_half, "mask_2_name": "Sky",
                                 "include_mask_layers": True})
            defaults.update({"custom_output_directory": target, "title": "Node check", "keywords": "zqkw, check",
                             "project": "zqproject", "description": "typed description", "save_xmp": True,
                             "save_txt": True})
            defaults.pop("filename_prefix", None)
            try:
                output = node.save_with_metadata(gradient, filename_prefix="nodecheck", prompt=prompt,
                                                 extra_pnginfo={"workflow": {"nodes": []}}, unique_id="9", **defaults)
            except Exception:
                ok = False
                print(f"case {case}: EXCEPTION\n{traceback.format_exc()[-1500:]}")
                continue
            filepath, summary = output["result"][1], output["result"][2]
            written = []
            for root, _dirs, files in os.walk(folder):
                written += [os.path.relpath(os.path.join(root, f), folder) for f in files if f"case{number}" in root]
            tags = read_tags(filepath) if filepath and os.path.isfile(filepath) else {}
            description = str(tags.get("XMP-dc:Description", ""))
            good = (bool(filepath) and filepath.startswith(target) and "zqnode test courtyard" in description
                    and "zqkw" in (tags.get("XMP-dc:Subject") or []) and "METADATA PROBLEM" not in summary
                    and not any(key.startswith("IPTC:") for key in tags)        # no old-style IPTC left behind
                    and (case.get("color_profile") is None
                         or case["color_profile"].split()[0] in str(tags.get("ICC_Profile:ProfileDescription")))
                    and "NOT embedded" not in summary)
            ok = ok and good
            if case.get("_layers") and filepath.lower().endswith(".psd"):
                from psd_tools import PSDImage
                layers = [(layer.name, str(layer.blend_mode).split(".")[-1], layer.opacity) for layer in PSDImage.open(filepath)]
                print("   psd layers:", layers)
                good = good and any(name == "Glow" and "SCREEN" in mode.upper() for name, mode, _ in layers)
                ok = ok and good
            if filepath.lower().endswith(".psd") and case.get("bit_depth") == "16-bit":
                from psd_tools import PSDImage
                psd = PSDImage.open(filepath)
                print("   psd depth:", psd.depth, "layers:", [layer.name for layer in psd])
                good = good and psd.depth == 16 and psd[0].name == "Main Image"
                ok = ok and good
            if case.get("_layers") and filepath.lower().endswith((".tif", ".tiff")):
                import tifffile
                with tifffile.TiffFile(filepath) as tif:
                    tag = tif.pages[0].tags.get(37724)
                    value = bytes(tag.value) if tag is not None else b""
                    pages = len(tif.pages)
                    bits = int(tif.pages[0].bitspersample)
                expected_key = b"MIB861rL" if bits == 16 else b"MIB8ryaL"
                if tif.byteorder == ">":
                    expected_key = b"8BIMLr16" if bits == 16 else b"8BIMLayr"
                good = good and value[36:44] == expected_key and bits == (16 if case.get("bit_depth") == "16-bit" else 8)
                has_block = value.startswith(b"Adobe Photoshop Document Data Block")
                print(f"   tiff: pages={pages} photoshop layer block={has_block} ({len(value)} bytes) "
                      f"key={value[36:44]!r} bits={bits}")
                good = good and has_block
                ok = ok and good
            keep = os.environ.get("AAA_KEEP_SAMPLES", "").strip()
            if keep and filepath and (case.get("_layers") or case.get("bit_depth") == "16-bit") \
                    and filepath.lower().endswith((".psd", ".tif", ".tiff")):
                import shutil
                os.makedirs(keep, exist_ok=True)
                label = f"{'16bit' if case.get('bit_depth') == '16-bit' else '8bit'}" \
                        f"{'_layers' if case.get('_layers') else ''}{os.path.splitext(filepath)[1]}"
                shutil.copyfile(filepath, os.path.join(keep, "sample_" + label))
            print(f"case {case}: ok={good} saved_as={os.path.basename(filepath)}\n   files={sorted(written)}\n   icc={tags.get('ICC_Profile:ProfileDescription')} "
                  f"bits={tags.get('PNG:BitDepth') or tags.get('IFD0:BitsPerSample')} headline={tags.get('XMP-photoshop:Headline')}")
            if not good:
                print("   summary:", summary[:900])
    previews = os.path.join(COMFY, "output", "node_previews")       # the node writes UI previews here
    if os.path.isdir(previews):
        for name in os.listdir(previews):
            if name.startswith("nodecheck_"):
                os.remove(os.path.join(previews, name))
    print("NODE OK" if ok else "NODE PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.modules.setdefault("aaa_meta_tags", __import__("types").ModuleType("aaa_meta_tags"))
    sys.path.insert(0, PACK)
    from aaa_meta.verify import read_tags as _read_tags
    sys.modules["aaa_meta_tags"].read_tags = _read_tags
    sys.exit(main())
