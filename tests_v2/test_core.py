"""
Tests for the v2 capture core. Run with the embedded Python:
    python -m pytest tests_v2 -q        (or)        python tests_v2/test_core.py

Synthetic graphs only - no personal prompts. The local fixtures in
tests_v2/fixtures_local (git-ignored) are exercised when present.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import asyncio
import glob
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aaa_meta import PromptGraph, build_record, shared                     # noqa: E402
from aaa_meta.capture import exec_hook, file_loads                         # noqa: E402
from aaa_meta.models import scan_values                                    # noqa: E402
from aaa_meta.record import GenerationRecord                               # noqa: E402

BASIC = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sdxl\\base.safetensors"}},
    "2": {"class_type": "LoraLoader", "inputs": {"lora_name": "style\\ink.safetensors", "strength_model": 0.8,
                                                  "strength_clip": 0.6, "model": ["1", 0], "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red fox", "clip": ["2", 1]}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["2", 1]}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 768, "batch_size": 1}},
    "6": {"class_type": "KSampler", "inputs": {"seed": ["9", 0], "steps": 30, "cfg": 6.5, "sampler_name": "dpmpp_2m",
                                               "scheduler": "karras", "denoise": 1.0, "model": ["2", 0],
                                               "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}},
    "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
    "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "x", "images": ["7", 0]}},
    "9": {"class_type": "SeedGenerator", "inputs": {"seed": 4242}},
}

CUSTOM = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux\\dev.safetensors"}},
    "2": {"class_type": "LLMPrompt", "inputs": {"prompt": "short idea", "temperature": 0.7}},
    "3": {"class_type": "DualEncode", "inputs": {"prompt": ["2", 0], "negative_prompt": "bad", "clip": ["10", 0]}},
    "4": {"class_type": "CFGGuider", "inputs": {"cfg": 3.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["3", 1]}},
    "5": {"class_type": "RandomNoise", "inputs": {"noise_seed": 777}},
    "6": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
    "7": {"class_type": "BasicScheduler", "inputs": {"scheduler": "simple", "steps": 20, "denoise": 1.0, "model": ["1", 0]}},
    "8": {"class_type": "SplitSigmas", "inputs": {"step": 12, "sigmas": ["7", 0]}},
    "9": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
    "10": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5.safetensors"}},
    "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["5", 0], "guider": ["4", 0], "sampler": ["6", 0],
                                                             "sigmas": ["8", 0], "latent_image": ["9", 0]}},
    "12": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["5", 0], "guider": ["4", 0], "sampler": ["6", 0],
                                                             "sigmas": ["8", 1], "latent_image": ["11", 0]}},
    "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["14", 0]}},
    "14": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "15": {"class_type": "SaveImage", "inputs": {"images": ["13", 0]}},
}


def test_basic_static():
    record = build_record(PromptGraph.from_prompt(BASIC), "8")
    assert record.positive == "a red fox" and record.negative == "blurry"
    assert record.seed == 4242, "seed must be followed through the seed node"
    sampling = record.passes[0]
    assert (sampling.steps, sampling.cfg, sampling.sampler, sampling.scheduler) == (30, 6.5, "dpmpp_2m", "karras")
    assert (record.width, record.height) == (1024, 768)
    assert [m.role for m in record.models] == ["checkpoint", "lora"]
    lora = record.loras[0]
    assert lora.strength_model == 0.8 and lora.strength_clip == 0.6
    assert record.keywords() == ["base", "ink", "dpmpp_2m"]
    assert record.capture_mode == "static"


def test_custom_two_pass_static():
    record = build_record(PromptGraph.from_prompt(CUSTOM), "15")
    assert len(record.passes) == 2
    first, second = record.passes
    assert first.node_id == "11" and second.node_id == "12"
    assert first.seed == 777 and first.sampler == "euler" and first.steps == 20 and first.cfg == 3.0
    assert first.end_step == 12 and second.start_step == 12
    assert record.negative == "bad"
    # the prompt comes over a link from an LLM node: statically we only see its input
    assert record.positive == "short idea"
    assert any("pre-rewrite" in w for w in record.warnings)


def test_runtime_overrides_static():
    captured = {"3": {"class_name": "DualEncode", "prompt_id": "p1",
                      "inputs": {"prompt": "the long text the LLM actually wrote", "negative_prompt": "bad"},
                      "outputs": {}, "files": [], "published": {}},
                "1": {"class_name": "UNETLoader", "prompt_id": "p1", "inputs": {"unet_name": "flux\\dev.safetensors"},
                      "outputs": {}, "published": {},
                      "files": [{"category": "diffusion_models", "name": "flux\\dev.safetensors", "path": "X:/m/flux/dev.safetensors"}]}}
    record = build_record(PromptGraph.from_prompt(CUSTOM), "15", captured, "p1")
    assert record.positive == "the long text the LLM actually wrote"
    assert record.capture_mode in ("runtime", "mixed")
    unet = record.by_role("unet")[0]
    assert unet.source == "runtime" and unet.path == "X:/m/flux/dev.safetensors"


def test_stale_capture_is_ignored():
    # same node id, different workflow: literal 'negative_prompt' no longer matches
    captured = {"3": {"class_name": "Other", "prompt_id": "old",
                      "inputs": {"prompt": "from another workflow", "negative_prompt": "DIFFERENT"},
                      "outputs": {}, "files": [], "published": {}}}
    record = build_record(PromptGraph.from_prompt(CUSTOM), "15", captured, "p2")
    assert record.positive == "short idea"


def test_prompt_writer_is_not_a_generator():
    graph = dict(BASIC)
    graph["3"] = {"class_type": "CLIPTextEncode", "inputs": {"text": ["20", 0], "clip": ["2", 1]}}
    graph["20"] = {"class_type": "PromptWriter", "inputs": {"prompt": "idea", "seed": 5, "steps": 3}}
    record = build_record(PromptGraph.from_prompt(graph), "8")
    assert len(record.passes) == 1 and record.passes[0].node_class == "KSampler"


def test_lora_widgets():
    power = scan_values({"lora_1": {"on": True, "lora": "a.safetensors", "strength": 0.5},
                         "lora_2": {"on": False, "lora": "b.safetensors", "strength": 1.0}}, "Power Lora Loader (rgthree)")
    assert [(f.name, f.enabled, f.strength_model) for f in power] == [("a.safetensors", True, 0.5), ("b.safetensors", False, 1.0)]
    numbered = scan_values({"on_1": True, "lora_1": "a.safetensors", "strength_1s1": 0.7, "strength_1s2": 0.4,
                            "on_2": False, "lora_2": "b.safetensors", "strength_2s1": 1.0}, "MultiLoRA")
    assert numbered[0].enabled and numbered[0].strength_model == 0.7 and len(numbered[0].extra_strengths) == 2
    assert not numbered[1].enabled
    state = scan_values({"state": json.dumps({"loras": [{"name": "c.safetensors", "on": True, "sm": 0.9, "sc": 0.8}]})}, "PixaromaLoraLoader")
    assert state[0].role == "lora" and state[0].strength_model == 0.9 and state[0].strength_clip == 0.8


def test_all_in_one_stages():
    graph = {"1": {"class_type": "UltraGen", "inputs": {"prompt": "p", "negative_prompt": "n", "seed": 9,
                                                         "s1_steps": 12, "s1_cfg": 1.0, "s1_sampler": "euler",
                                                         "s2_steps": 0, "s3_steps": 8, "s3_schedule": "beta"}},
             "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0]}}}
    record = build_record(PromptGraph.from_prompt(graph), "2")
    assert [p.steps for p in record.passes] == [12, 8]
    assert record.positive == "p" and record.negative == "n" and record.seed == 9


def test_record_roundtrip():
    record = build_record(PromptGraph.from_prompt(BASIC), "8")
    again = GenerationRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert again.to_dict() == record.to_dict()


def test_exec_hook_and_file_hook():
    state = shared.state()
    state.nodes.clear()

    class Node:
        FUNCTION = "run"

    fake_execution = types.ModuleType("fake_execution")

    async def _async_map_node_over_list(prompt_id, unique_id, obj, input_data_all, func, allow_interrupt=False,
                                        execution_block_cb=None, pre_execute_cb=None, v3_data=None):
        return [("final text", 123, object())]

    fake_execution._async_map_node_over_list = _async_map_node_over_list
    assert exec_hook.install(fake_execution) is True
    assert exec_hook.install(fake_execution) is True          # idempotent
    wrapped = fake_execution._async_map_node_over_list
    assert getattr(wrapped.__wrapped__, "__name__", "") == "_async_map_node_over_list", "must not double wrap"

    inputs = {"prompt": ["hello"], "seed": [5], "image": [object()], "cfg": [1.5],
              "lora": [{"on": True, "lora": "x.safetensors", "strength": 1}]}
    results = asyncio.run(wrapped("p9", "42", Node(), inputs, "run"))
    assert results[0][0] == "final text", "results must pass through untouched"
    entry = state.nodes["42"]
    assert entry["inputs"]["prompt"] == "hello" and entry["inputs"]["seed"] == 5 and "image" not in entry["inputs"]
    assert entry["inputs"]["lora"]["lora"] == "x.safetensors"
    assert entry["outputs"] == {0: "final text", 1: 123}
    # side calls (lazy status etc.) are not recorded
    asyncio.run(wrapped("p9", "43", Node(), inputs, "check_lazy_status"))
    assert "43" not in state.nodes

    fake_paths = types.ModuleType("fake_folder_paths")
    fake_paths.get_full_path = lambda folder, name: f"X:/{folder}/{name}"
    fake_paths.get_full_path_or_raise = lambda folder, name: fake_paths.get_full_path(folder, name)
    assert file_loads.install(fake_paths) is True
    assert fake_paths.get_full_path("loras", "a.safetensors") == "X:/loras/a.safetensors"   # no context: ignored, still works


def test_local_fixtures_do_not_crash():
    here = os.path.dirname(os.path.abspath(__file__))
    for path in glob.glob(os.path.join(here, "fixtures_local", "fixture_*.json")):
        data = json.load(open(path, encoding="utf-8"))
        graph = PromptGraph.from_prompt(data["prompt"])
        for node_id in graph.nodes:
            if "Save" in graph.class_type(node_id):
                record = build_record(graph, node_id)
                json.dumps(record.to_dict())


def test_source_prompt_and_prompt_llm():
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "m.safetensors"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "enc.safetensors"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "llm.safetensors"}},
        "4": {"class_type": "TextGenerate", "inputs": {"prompt": "a fox", "max_length": 100, "clip": ["3", 0],
                                                       "system_prompt": ["9", 0]}},
        "5": {"class_type": "PreviewAny", "inputs": {"source": ["4", 0]}},
        "6": {"class_type": "DualEncode", "inputs": {"prompt": ["5", 0], "negative_prompt": "", "clip": ["2", 0]}},
        "7": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 4, "cfg": 1.0, "sampler_name": "euler",
                                                   "scheduler": "simple", "denoise": 1.0, "model": ["1", 0],
                                                   "positive": ["6", 0], "negative": ["6", 1], "latent_image": ["8", 0]}},
        "8": {"class_type": "EmptyLatentImage", "inputs": {"width": 64, "height": 64, "batch_size": 1}},
        "9": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "You rewrite prompts."}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["7", 0]}},
    }
    def entry(inputs, outputs=None):
        return {"class_name": "x", "prompt_id": "p", "inputs": inputs, "outputs": outputs or {}, "files": [], "published": {}}
    captured = {
        "4": entry({"prompt": "a fox", "max_length": 100, "system_prompt": "You rewrite prompts."}, {0: "A red fox at dawn, long text"}),
        "5": entry({"source": "A red fox at dawn, long text"}, {0: "A red fox at dawn, long text"}),
        "6": entry({"prompt": "A red fox at dawn, long text", "negative_prompt": ""}),
    }
    record = build_record(PromptGraph.from_prompt(graph), "10", captured, "p")
    assert record.positive == "A red fox at dawn, long text"
    assert record.positive_source == "a fox" and record.prompt_rewriter == "TextGenerate"
    roles = {m.name: m.role for m in record.models}
    assert roles["enc.safetensors"] == "text_encoder" and roles["llm.safetensors"] == "prompt_llm"
    # no rewrite: typed text reaches the encoder unchanged -> no source prompt recorded
    plain = build_record(PromptGraph.from_prompt(BASIC), "8")
    assert plain.positive_source == "" and plain.prompt_rewriter == ""


def _sample_record():
    from aaa_meta.record import ModelRef, SamplingPass
    return GenerationRecord(
        positive="a red fox \x01 & <b> 评估", negative="blurry", positive_source="fox", prompt_rewriter="TextGenerate",
        models=[ModelRef("unet", "Qwen21\\x\\3370753_red_3258922.safetensors", path="A:\\m.safetensors", sha256="30532b445e" + "0" * 54),
                ModelRef("lora", "style\\ink.safetensors", strength_model=0.8, sha256="ab" * 32)],
        passes=[SamplingPass(0, "1", "KSampler", seed=447606998181262, steps=30, cfg=1.0, sampler="lcm", scheduler="beta", denoise=1.0)],
        width=1536, height=2048, created="2026-11-15T11:54:36-08:00", comfyui_version="0.45.0", capture_mode="runtime")


def test_standard_fields_and_a1111():
    from aaa_meta.a1111 import build_parameters
    from aaa_meta.fields import UserFields, build_standard_fields
    record = _sample_record()
    fields = build_standard_fields(record, UserFields(keywords=["mine", "LCM"], creator="Eric"))
    assert fields.description == record.positive
    assert fields.keywords == ["3370753_red_3258922", "ink", "lcm", "mine"]          # de-duplicated, case-insensitive
    assert fields.hierarchical_keywords == ["AI|Model|3370753_red_3258922", "AI|LoRA|ink", "AI|Sampler|lcm"]
    assert fields.headline == "3370753_red_3258922"
    assert fields.instructions == "Steps 30, lcm/beta, CFG 1, Seed 447606998181262, 1536x2048"
    parameters = build_parameters(record)
    assert "Negative prompt: blurry" in parameters and "Seed: 447606998181262" in parameters
    assert "Model hash: 30532b445e" in parameters and '"lora:ink": "ababababab"' in parameters


def test_packet_structure_merge_and_roundtrip():
    import xml.etree.ElementTree as ET
    from aaa_meta.fields import build_standard_fields
    from aaa_meta.xmp_packet import NS, build_packet, merge_packets, read_record_json
    record = _sample_record()
    packet = build_packet(build_standard_fields(record), record,
                          {"unipercept": {"iaa": 71.2}, "blur v7": {"regions": [{"x": 1}, {"x": 2}]}})
    text = packet.decode("utf-8")
    body = text[text.index("<x:xmpmeta"):text.index("</x:xmpmeta>") + 12]
    root = ET.fromstring(body)                                   # well-formed, control char removed
    assert "\x01" not in text and "评估" in text
    assert "rdf:Description {" not in text                       # the old stringified-struct bug
    models = root.find(f".//{{{NS['hcai']}}}Models/{{{NS['rdf']}}}Seq")
    assert len(list(models)) == 2 and models[0].find(f"{{{NS['hcai']}}}AutoV2").text == "30532b445e"
    assert root.find(f".//{{{NS['eiqa']}}}unipercept/{{{NS['eiqa']}}}iaa").text == "71.2"
    assert root.find(f".//{{{NS['eiqa']}}}blur_v7") is not None  # key with a space made a valid name
    data = read_record_json(packet)
    assert data["passes"][0]["seed"] == 447606998181262
    assert "path" not in data["models"][0], "local disk paths must not be embedded by default"
    assert "path" in read_record_json(build_packet(None, record, include_paths=True))["models"][0]
    old = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
           b'<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xmp="http://ns.adobe.com/xap/1.0/" '
           b'xmp:Rating="4" xmp:CreatorTool="Old"><dc:subject><rdf:Bag><rdf:li>keepme</rdf:li><rdf:li>ink</rdf:li></rdf:Bag>'
           b'</dc:subject></rdf:Description></rdf:RDF></x:xmpmeta>')
    merged = merge_packets(old, packet).decode("utf-8")
    assert 'Rating="4"' in merged and "keepme" in merged and "Old" not in merged and merged.count(">ink<") == 1
    # adding analysis later keeps the generation record
    later = merge_packets(build_packet(build_standard_fields(record), record), build_packet(analysis={"noise": {"level": 0.2}}))
    assert read_record_json(later)["passes"][0]["steps"] == 30 and "eiqa:noise" in later.decode("utf-8")


def test_writer_embeds_in_every_pillow_format():
    import tempfile
    from PIL import Image
    from aaa_meta.embed import read_xmp
    from aaa_meta.writer import save_with_metadata
    from aaa_meta.xmp_packet import read_record_json
    record = _sample_record()
    image = Image.new("RGB", (32, 32), (10, 90, 160))
    with tempfile.TemporaryDirectory() as folder:
        for extension in ("png", "jpg", "webp", "tiff"):
            path = os.path.join(folder, f"t.{extension}")
            result = save_with_metadata(image, path, record=record, verify=False)
            assert result["embedded"] and not result["warnings"], (extension, result)
            data = read_record_json(read_xmp(path))
            assert data and data["passes"][0]["seed"] == 447606998181262, extension
        assert "Seed: 447606998181262" in Image.open(os.path.join(folder, "t.png")).info["parameters"]
        # JPEG size limit: shrinks in steps and says so
        record.positive = "word " * 9000
        big = save_with_metadata(image, os.path.join(folder, "big.jpg"), record=record, verify=False)
        assert big["embedded"] and big["warnings"] and read_xmp(os.path.join(folder, "big.jpg"))


def test_colour_conversion_reference_values():
    import numpy as np
    from aaa_meta import color
    samples = np.array([[[1.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 0.0, 0.0]]], dtype=np.float32)
    adobe = np.rint(color.convert_from_srgb(samples, color.PROFILE_ADOBE)[0] * 255).astype(int).tolist()
    prophoto = np.rint(color.convert_from_srgb(samples, color.PROFILE_PROPHOTO)[0] * 255).astype(int).tolist()
    assert adobe == [[219, 0, 0], [255, 255, 255], [0, 0, 0]]          # published sRGB-red in Adobe RGB
    assert prophoto == [[179, 70, 26], [255, 255, 255], [0, 0, 0]]     # published sRGB-red in ProPhoto
    assert color.convert_from_srgb(samples, color.PROFILE_SRGB) is samples


def test_save_core_true_16bit_and_formats():
    import struct, tempfile, zlib
    import numpy as np
    import tifffile
    from PIL import Image
    from aaa_meta import color
    from aaa_meta.embed import read_xmp
    from aaa_meta.pixels import to_uint16
    from aaa_meta.save_core import SaveOptions, describe_result, save_image
    from aaa_meta.xmp_packet import read_record_json
    record = _sample_record()
    ramp = np.linspace(0, 1, 2048, dtype=np.float32)[None, :, None].repeat(4, 0).repeat(3, 2).copy()
    with tempfile.TemporaryDirectory() as folder:
        # 16-bit PNG: every one of the 2048 ramp levels must survive (8-bit x 256 would give 256)
        path = os.path.join(folder, "a.png")
        result = save_image(ramp, path, SaveOptions(file_format="png", bit_depth=16, verify=False,
                                                    png_chunks={"prompt": "{}"}), record=record)
        assert result["bit_depth"] == 16
        blob = open(path, "rb").read(); pos = 8; idat = b""
        while pos < len(blob):
            size, kind = struct.unpack(">I4s", blob[pos:pos + 8])
            if kind == b"IDAT":
                idat += blob[pos + 8:pos + 8 + size]
            pos += 12 + size
        raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(4, -1)
        rows = np.cumsum(raw[:, 1:].astype(np.uint64), axis=0).astype(np.uint8).reshape(4, 2048, 3, 2)
        values = rows[..., 0].astype(np.uint16) * 256 + rows[..., 1]
        assert np.array_equal(values, to_uint16(ramp)) and len(np.unique(values)) == 2048
        info = Image.open(path).info
        assert info.get("prompt") == "{}" and "Seed: 447606998181262" in info.get("parameters", "")
        assert read_record_json(read_xmp(path))["passes"][0]["steps"] == 30
        # 16-bit TIFF
        path = os.path.join(folder, "a.tiff")
        save_image(ramp, path, SaveOptions(file_format="tiff", bit_depth=16, verify=False), record=record)
        with tifffile.TiffFile(path) as tif:
            assert tif.asarray().dtype == np.uint16 and len(np.unique(tif.asarray())) == 2048
        assert read_record_json(read_xmp(path))
        # 8-bit formats, RGBA into JPEG flattens instead of failing
        rgba = np.dstack([ramp, np.full(ramp.shape[:2], 0.5, np.float32)])
        for fmt in ("jpg", "webp", "tiff", "png"):
            path = os.path.join(folder, f"b.{fmt}")
            result = save_image(rgba, path, SaveOptions(file_format=fmt, verify=False), record=record)
            assert result["embedded"] and read_record_json(read_xmp(path)), fmt
            assert "8-bit" in describe_result(result)
        # metadata off: nothing about the generation leaves in the file
        path = os.path.join(folder, "c.png")
        save_image(ramp, path, SaveOptions(file_format="png", embed_metadata=False, verify=False,
                                           png_chunks={"prompt": "{}"}), record=record)
        info = Image.open(path).info
        assert "prompt" not in info and "parameters" not in info and read_xmp(path) is None
        # colour profile: missing profile file falls back to sRGB and says so
        result = save_image(ramp, os.path.join(folder, "d.png"),
                            SaveOptions(file_format="png", color_profile=color.PROFILE_ADOBE, profile_dir=folder, verify=False))
        assert result["color_profile"] == color.PROFILE_SRGB and any("not found" in w for w in result["warnings"])


if __name__ == "__main__":
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"PASS {name}")
            except Exception as exc:
                failed += 1
                import traceback
                print(f"FAIL {name}: {exc!r}")
                traceback.print_exc()
    sys.exit(1 if failed else 0)
