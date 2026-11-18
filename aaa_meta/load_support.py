"""
load_support.py
Helpers for the load nodes:

  metadata_outputs(path)   what the v2 nodes stored in a file, as node outputs
  load_full_depth(path)    16-bit PNG / TIFF pixels without the 8-bit detour
  select_layers(...)       layer choice for the "with layers" loader

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import reader
from .record import GenerationRecord

METADATA_OUTPUT_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
METADATA_OUTPUT_NAMES = ("prompt", "negative_prompt", "record_json", "measurements_json", "metadata_summary")


def metadata_outputs(path: str) -> Tuple[str, str, str, str, str]:
    """(prompt, negative prompt, generation record JSON, measurements JSON, readable summary)."""
    empty = ("", "", "{}", "{}", "no stored metadata found")
    if not path or not os.path.isfile(path):
        return empty
    try:
        parsed = reader.read_file(path)
    except Exception as exc:
        return ("", "", "{}", "{}", f"metadata could not be read: {exc!r}")
    record_data = parsed.get("record")
    flat = reader.generation_summary(parsed)
    analysis = parsed.get("analysis") or {}
    if not record_data and not flat and not analysis:
        description = (parsed.get("standard") or {}).get("description", "")
        return (description, "", "{}", "{}", "no generation record in this file"
                + (" (caption returned as prompt)" if description else ""))
    lines: List[str] = [f"source: {parsed.get('source') or 'file'}"]
    if record_data:
        try:
            lines.append(GenerationRecord.from_dict(record_data).summary())
        except Exception:
            lines.extend(f"{key}: {value}" for key, value in flat.items() if key not in ("prompt", "negative_prompt"))
    else:
        lines.extend(f"{key}: {value}" for key, value in flat.items() if key not in ("prompt", "negative_prompt"))
    if analysis:
        lines.append("measurements: " + ", ".join(list(analysis.keys())[:20]))
    return (str(flat.get("prompt") or ""), str(flat.get("negative_prompt") or ""),
            json.dumps(record_data or {}, ensure_ascii=False, indent=1),
            json.dumps(analysis, ensure_ascii=False, indent=1), "\n".join(lines))


def _png_is_16bit(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            header = handle.read(26)
        return header[:8] == b"\x89PNG\r\n\x1a\n" and header[24] == 16
    except (OSError, IndexError):
        return False


def load_full_depth(path: str) -> Optional[Tuple[np.ndarray, Optional[np.ndarray]]]:
    """
    (rgb float32 H x W x 3 in 0..1, alpha float32 H x W or None) for 16-bit PNG and
    TIFF files, at full precision. None for anything else (the normal loader handles it).
    """
    extension = os.path.splitext(path)[1].lower()
    array = None
    try:
        if extension in (".tif", ".tiff"):
            import tifffile
            with tifffile.TiffFile(path) as tif:
                page = tif.pages[0]
                if int(page.bitspersample) != 16 or page.photometric.name not in ("RGB", "MINISBLACK"):
                    return None
                array = page.asarray()
        elif extension == ".png" and _png_is_16bit(path):
            import cv2
            decoded = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if decoded is None or decoded.dtype != np.uint16:
                return None
            if decoded.ndim == 3 and decoded.shape[2] == 3:
                decoded = decoded[..., ::-1]                     # BGR -> RGB
            elif decoded.ndim == 3 and decoded.shape[2] == 4:
                decoded = decoded[..., [2, 1, 0, 3]]
            array = decoded
    except Exception:
        return None
    if array is None or array.dtype != np.uint16:
        return None
    if array.ndim == 2:
        array = array[..., None]
    if array.ndim != 3 or array.shape[2] not in (1, 2, 3, 4):
        return None
    values = array.astype(np.float32) / 65535.0
    channels = values.shape[2]
    rgb = np.repeat(values[..., :1], 3, axis=2) if channels in (1, 2) else values[..., :3]
    alpha = values[..., 1] if channels == 2 else (values[..., 3] if channels == 4 else None)
    return np.ascontiguousarray(rgb), alpha


def select_layers(layers: List[Dict[str, Any]], load_mode: str, layer_name: str = "",
                  layer_index: int = 0) -> Tuple[List[Dict[str, Any]], str]:
    """Layers to return for a load mode, plus a note. An empty list means: use the composite."""
    if load_mode == "all_layers":
        return layers, ""
    if load_mode == "visible_only":
        visible = [layer for layer in layers if layer.get("visible", True)] or layers
        return visible, f"Visible: {len(visible)}"
    if load_mode == "layer_by_name":
        wanted = str(layer_name or "").strip()
        match = next((layer for layer in layers if layer["name"] == wanted), None) \
            or next((layer for layer in layers if layer["name"].lower() == wanted.lower()), None)
        return ([match], f"Selected: {match['name']}") if match else ([], "Layer not found")
    if load_mode == "layer_by_index":
        if 0 <= int(layer_index) < len(layers):
            return [layers[int(layer_index)]], f"Selected: {layers[int(layer_index)]['name']} (index {layer_index})"
        return [], "Invalid index"
    return [], ""


def file_generation(path: str) -> Dict[str, Any]:
    """
    Generation data for a file, best source first:
      "stored"          the record the v2 save node put into the file / sidecar
      "workflow graph"  rebuilt from the ComfyUI workflow inside a PNG (older files)
      ""                nothing found
    Returns {"origin", "record" (dict), "analysis" (dict), "flat" (prompt, model, seed...), "summary" (text)}.
    """
    result: Dict[str, Any] = {"origin": "", "record": {}, "analysis": {}, "flat": {}, "summary": ""}
    if not path or not os.path.isfile(path):
        return result
    try:
        parsed = reader.read_file(path)
    except Exception:
        parsed = {}
    result["analysis"] = parsed.get("analysis") or {}
    record = None
    if parsed.get("record"):
        try:
            record = GenerationRecord.from_dict(parsed["record"])
            result["origin"] = "stored"
        except Exception:
            record = None
    if record is None and path.lower().endswith(".png"):
        try:
            from PIL import Image
            from .builder import build_record
            from .graph import PromptGraph
            with Image.open(path) as image:
                raw = image.info.get("prompt")
                size = image.size
            if raw:
                graph = PromptGraph.from_prompt(json.loads(raw))
                savers = sorted((node_id for node_id in graph.nodes
                                 if "save" in graph.class_type(node_id).lower()
                                 and any(name in graph.links(node_id) for name in ("images", "image", "source", "input"))),
                                key=lambda n: (0 if "image" in graph.class_type(n).lower() else 1, str(n)))
                if savers:
                    candidate = build_record(graph, savers[0])
                    if candidate.positive or candidate.positive_source or candidate.passes:
                        candidate.width, candidate.height = size
                        record = candidate
                        result["origin"] = "workflow graph"
        except Exception:
            record = None
    if record is not None:
        result["record"] = record.to_dict()
        first = record.passes[0] if record.passes else None
        base = record.base_models[0] if record.base_models else None
        result["flat"] = {key: value for key, value in {
            "prompt": record.positive or record.positive_source, "negative_prompt": record.negative,
            "model": base.stem if base else None, "sampler": first.sampler if first else None,
            "scheduler": first.scheduler if first else None, "steps": first.steps if first else None,
            "cfg": first.cfg if first else None, "seed": first.seed if first else None,
            "loras": [m.stem for m in record.loras] or None}.items() if value not in (None, "", [])}
        result["summary"] = (f"Generation record ({'stored in the file' if result['origin'] == 'stored' else 'rebuilt from the workflow in the file'}):\n"
                             + record.summary())
    if result["analysis"]:
        result["summary"] = (result["summary"] + "\n" if result["summary"] else "") \
            + "Measurements: " + ", ".join(list(result["analysis"].keys())[:20])
    return result
