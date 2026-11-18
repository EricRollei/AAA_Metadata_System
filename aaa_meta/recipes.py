"""
recipes.py
Recipes: what a generator node itself says it used.

Some all-in-one nodes return their complete settings as a JSON string - a dict
that carries a "<name>_settings_version" key (Eric_Krea2: "krea2_settings_version").
The capture hook already keeps that output. When such a node feeds the image
being saved, its statement is attached to the generation record ("recipe") and,
where the layout is known, used to correct the record:

  Eric_Krea2 Ultra
    * stages that did not run (upscale_to_stage2 / 3 = 0) are not listed as passes
    * parameter sweeps: the IMAGE output is a batch of cells, each made with its
      own checkpoint / LoRAs / prompt / settings. Batch image i is matched to its
      cell through the sweep manifest, and the exact recipe is read from the
      cell picture the sweep wrote (its "krea2_settings" text chunk). Every saved
      image then gets the record of its own cell.

Nothing here imports ComfyUI. Nothing in Eric_Krea2 needs to change.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import copy
import json
import os
import re
import struct
import zlib
from typing import Any, Dict, List, Optional, Tuple

from .graph import PromptGraph
from .record import GenerationRecord, ModelRef, SamplingPass
from .resolve import Resolver

VERSION_SUFFIX = "_settings_version"
_MULTI_BASE_WARNING = "base models were loaded in this run"
_ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")
_STACK_ITEM = re.compile(r"^(.*?)(?:\s*@\s*(-?\d+(?:\.\d+)?))?$")
_manifest_cache: Dict[str, Tuple[float, Optional[dict]]] = {}


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
def parse_settings(text: Any) -> Optional[Dict[str, Any]]:
    """A settings string -> dict, when it is one (JSON object with a *_settings_version key)."""
    if not isinstance(text, str) or VERSION_SUFFIX not in text or not text.lstrip().startswith("{"):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None                                         # e.g. cut off by the capture size limit
    if isinstance(data, dict) and any(str(key).endswith(VERSION_SUFFIX) for key in data):
        return data
    return None


def recipe_kind(doc: Dict[str, Any]) -> str:
    for key in doc:
        if str(key).endswith(VERSION_SUFFIX):
            return str(key)[: -len("_version")]              # "krea2_settings"
    return "settings"


def read_png_text(path: str, key: str) -> Optional[str]:
    """One text chunk (tEXt / zTXt / iTXt) of a PNG, without loading the picture."""
    try:
        with open(path, "rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            wanted = key.encode("latin-1", "replace")
            while True:
                head = handle.read(8)
                if len(head) < 8:
                    return None
                length, kind = struct.unpack(">I4s", head)
                if kind in (b"IDAT", b"IEND"):
                    return None                             # text chunks are written before the pixels
                if kind not in (b"tEXt", b"zTXt", b"iTXt"):
                    handle.seek(length + 4, 1)
                    continue
                data = handle.read(length)
                handle.seek(4, 1)
                name, _, rest = data.partition(b"\x00")
                if name != wanted:
                    continue
                if kind == b"tEXt":
                    return rest.decode("latin-1")
                if kind == b"zTXt":
                    return zlib.decompress(rest[1:]).decode("latin-1")
                compressed = rest[0:1] == b"\x01"
                _, _, rest = rest[2:].partition(b"\x00")     # language tag
                _, _, rest = rest.partition(b"\x00")         # translated keyword
                return (zlib.decompress(rest) if compressed else rest).decode("utf-8", "replace")
    except Exception:
        return None


def load_manifest(path: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(path, str) or not path.lower().endswith(".json") or len(path) > 1024:
        return None
    try:
        if not os.path.isfile(path):
            return None
        stamp = os.path.getmtime(path)
        cached = _manifest_cache.get(path)
        if cached and cached[0] == stamp:
            return cached[1]
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not (isinstance(data, dict) and "sweep_manifest_version" in data and isinstance(data.get("cells"), list)):
            data = None
        _manifest_cache.clear()                              # one at a time: manifests can be large
        _manifest_cache[path] = (stamp, data)
        return data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# the plan for one save
# ---------------------------------------------------------------------------
class RecipePlan:
    """What the nearest recipe-stating node upstream of the save said."""

    def __init__(self) -> None:
        self.node_id: str = ""
        self.class_type: str = ""
        self.base: Optional[Dict[str, Any]] = None           # settings document (panel values)
        self.sweep_id: str = ""
        self.manifest_path: str = ""
        self.cells: List[Dict[str, Any]] = []                # batch order; see _sweep_cells
        self.notes: List[str] = []
        self._cell_docs: Dict[int, Optional[Dict[str, Any]]] = {}

    @property
    def is_sweep(self) -> bool:
        return bool(self.cells)

    def cell_settings(self, index: int) -> Optional[Dict[str, Any]]:
        """Exact settings of one cell, from the picture the sweep wrote for it."""
        if index not in self._cell_docs:
            doc = None
            cell = self.cells[index]
            if cell.get("file") and self.manifest_path:
                path = os.path.join(os.path.dirname(self.manifest_path), str(cell["file"]))
                kind = recipe_kind(self.base) if self.base else "krea2_settings"
                doc = parse_settings(read_png_text(path, kind) or "")
            self._cell_docs[index] = doc
        return self._cell_docs[index]


def _sweep_cells(settings: Optional[dict], manifest: Optional[dict]) -> List[Dict[str, Any]]:
    """Cells in the order of the IMAGE batch: [{cell_index, overrides, file, seed, loras, resolved, metrics}]."""
    listed = ((settings or {}).get("sweep") or {}).get("cells") if isinstance(settings, dict) else None
    saved = [c for c in (manifest or {}).get("cells", []) if isinstance(c, dict) and c.get("file")]
    by_index = {c.get("index"): c for c in saved}
    cells: List[Dict[str, Any]] = []
    if isinstance(listed, list) and listed:                  # the node's own batch -> cell mapping
        for item in sorted((c for c in listed if isinstance(c, dict)), key=lambda c: c.get("batch_index", 0)):
            full = by_index.get(item.get("cell_index"), {})
            cells.append({"cell_index": item.get("cell_index"),
                          "overrides": item.get("overrides") or full.get("overrides") or {}, **_cell_extras(full)})
    else:                                                    # same rule the node uses: saved cells, in order
        for full in saved:
            cells.append({"cell_index": full.get("index"), "overrides": full.get("overrides") or {},
                          **_cell_extras(full)})
    return cells


def _cell_extras(full: Dict[str, Any]) -> Dict[str, Any]:
    return {key: full[key] for key in ("file", "seed", "loras", "words", "resolved", "metrics", "label")
            if full.get(key) not in (None, "", {}, [])}


def find_plan(graph: PromptGraph, anchor_id: Any, captured: Dict[str, dict],
              prompt_id: Optional[str] = None) -> Optional[RecipePlan]:
    """The recipe stated by the nearest upstream node that states one, or None."""
    anchor_id = str(anchor_id)
    if not graph.has(anchor_id):
        return None
    resolver = Resolver(graph, captured, prompt_id)
    for node_id, _depth in sorted(graph.ancestors(anchor_id).items(), key=lambda kv: kv[1]):
        entry = resolver.entry(node_id)                      # this run, or a cached node with matching inputs
        if not entry:
            continue
        outputs = [value for _, value in sorted((entry.get("outputs") or {}).items(), key=lambda kv: int(kv[0]))]
        texts = [value for value in outputs if isinstance(value, str)]
        settings, cut_off = None, False
        for text in texts:
            settings = parse_settings(text)
            if settings is not None:
                break
            if VERSION_SUFFIX in text[:400] and text.lstrip().startswith("{"):
                cut_off = True                               # a settings string too long to keep whole
        manifest_path, manifest = "", None
        candidates = [((settings or {}).get("sweep") or {}).get("manifest")] if settings else []
        for candidate in candidates + texts:
            manifest = load_manifest(candidate)
            if manifest is not None:
                manifest_path = str(candidate)
                break
        if settings is None and manifest is None:
            if cut_off:
                plan = RecipePlan()
                plan.notes.append(f"{graph.class_type(node_id)} returned settings too long to keep and no "
                                  f"sweep manifest was found - recipe not stored")
                return plan
            continue
        plan = RecipePlan()
        plan.node_id, plan.class_type = node_id, graph.class_type(node_id)
        plan.manifest_path = manifest_path
        plan.base = settings
        if plan.base is None and manifest is not None:        # big sweep: rebuild the panel values
            kind_key = "krea2_settings_version"
            plan.base = {kind_key: 1, "ultra": dict(manifest.get("base") or {})}
        sweep = (settings or {}).get("sweep") if settings else None
        if isinstance(sweep, dict) or (manifest is not None and (cut_off or settings is None)):
            plan.cells = _sweep_cells(settings, manifest)
            plan.sweep_id = str((sweep or {}).get("sweep_id") or (manifest or {}).get("sweep_id") or "")
            if manifest is None:
                plan.notes.append("sweep manifest not readable - cell settings taken from the listed overrides only")
        if entry.get("prompt_id") != prompt_id and prompt_id is not None:
            plan.notes.append(f"recipe of {plan.class_type} comes from its last run (the node was cached this time)")
        return plan
    return None


# ---------------------------------------------------------------------------
# applying a recipe to a record
# ---------------------------------------------------------------------------
def _strip_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_strip_paths(item) for item in value]
    if isinstance(value, str) and _ABSOLUTE_PATH.match(value) and "\n" not in value and len(value) < 600:
        return re.split(r"[\\/]", value.rstrip("\\/"))[-1]
    return value


def recipe_for_embedding(recipe: Dict[str, Any], include_paths: bool) -> Dict[str, Any]:
    return copy.deepcopy(recipe) if include_paths else _strip_paths(recipe)


def _number(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _krea2_passes(record: GenerationRecord, ultra: Dict[str, Any], seed: Optional[int]) -> List[SamplingPass]:
    stage_passes = [p for p in record.passes if re.search(r" stage \d+$", p.node_class or "")]
    template = stage_passes[0] if stage_passes else (record.passes[0] if record.passes else None)
    node_id = template.node_id if template else ""
    class_base = re.sub(r" stage \d+$", "", template.node_class) if template else "Krea2 Ultra"
    old_seeds = {int(re.search(r"(\d+)$", p.node_class).group(1)): p.seed for p in stage_passes}
    up2, up3 = _number(ultra.get("upscale_to_stage2")), _number(ultra.get("upscale_to_stage3"))
    runs = {1: True,
            2: (up2 > 0) if up2 is not None else bool(ultra.get("s2_steps")),
            3: ((up2 is None or up2 > 0) and up3 > 0) if up3 is not None else bool(ultra.get("s3_steps"))}
    same_seed = str(ultra.get("seed_mode", "same_all_stages")) == "same_all_stages"
    passes: List[SamplingPass] = []
    for stage in (1, 2, 3):
        steps = _number(ultra.get(f"s{stage}_steps"))
        if not runs[stage] or not steps or steps <= 0:
            continue
        item = SamplingPass(index=len(passes), node_id=node_id, node_class=f"{class_base} stage {stage}")
        item.steps = int(steps)
        item.cfg = _number(ultra.get(f"s{stage}_cfg"))
        item.sampler = ultra.get(f"s{stage}_sampler") or None
        item.scheduler = ultra.get(f"s{stage}_schedule") or None
        end_step = _number(ultra.get(f"s{stage}_end_step"))
        if end_step:
            item.end_step = int(end_step)
            start_step = _number(ultra.get(f"s{stage}_start_step"))
            item.start_step = int(start_step) if start_step is not None else None
        if seed is not None:
            item.seed = seed if (stage == 1 or same_seed) else None
        else:
            item.seed = old_seeds.get(stage, template.seed if (template and same_seed) else None)
        for key in ("noise", "eta", "hybrid_steps"):
            value = ultra.get(f"s{stage}_{key}")
            if value not in (None, "", 0) or (key == "eta" and value == 0):
                item.extras[key] = value
        passes.append(item)
    return passes or record.passes


def _replace_role(record: GenerationRecord, roles: Tuple[str, ...], new: List[ModelRef]) -> None:
    known = {m.stem.lower(): m for m in record.models if m.sha256}
    for ref in new:
        old = known.get(ref.stem.lower())
        if old is not None:
            ref.sha256 = old.sha256
    position = next((i for i, m in enumerate(record.models) if m.role in roles), len(record.models))
    kept_before = [m for m in record.models[:position] if m.role not in roles]
    kept_after = [m for m in record.models[position:] if m.role not in roles]
    record.models = kept_before + new + kept_after


def _path_ref(role: str, path: str, name: str = "") -> ModelRef:
    return ModelRef(role=role, name=name or path, path=path if _ABSOLUTE_PATH.match(path) else None, source="recipe")


def _parse_stack(text: Any) -> List[Tuple[str, Optional[float]]]:
    """'name @1' lines (or ' + ' / ',' separated) -> [(name, strength)]."""
    items: List[Tuple[str, Optional[float]]] = []
    for part in re.split(r"[\n|]+|\s\+\s", str(text or "")):
        match = _STACK_ITEM.match(part.strip())
        if match and match.group(1).strip():
            items.append((match.group(1).strip(), float(match.group(2)) if match.group(2) else None))
    return items


def _apply_krea2_cell(record: GenerationRecord, doc: Optional[Dict[str, Any]], cell: Dict[str, Any]) -> None:
    overrides = cell.get("overrides") if isinstance(cell.get("overrides"), dict) else {}
    loader = (doc or {}).get("loader") if isinstance((doc or {}).get("loader"), dict) else {}
    # --- base model, text encoder, VAE
    transformer = str(loader.get("transformer_path") or "")
    checkpoint = str(overrides.get("checkpoint") or "")
    if transformer or checkpoint:
        _replace_role(record, ("checkpoint", "unet"), [_path_ref("unet", transformer or checkpoint, checkpoint)])
    if loader.get("base_pipeline_path"):
        _replace_role(record, ("pipeline",), [_path_ref("pipeline", str(loader["base_pipeline_path"]))])
    if loader.get("text_encoder_path"):
        path = str(loader["text_encoder_path"])
        _replace_role(record, ("text_encoder",), [_path_ref("text_encoder", path, os.path.basename(path.replace("\\", "/")))])
    if loader.get("vae_path"):
        _replace_role(record, ("vae",), [_path_ref("vae", str(loader["vae_path"]))])
    # --- LoRAs
    loras: Optional[List[ModelRef]] = None
    stack = (doc or {}).get("lora")
    if isinstance(stack, list):
        loras = []
        for item in stack:
            if not isinstance(item, dict):
                continue
            name = str(item.get("lora_name") or item.get("filename") or item.get("path") or "")
            if not name:
                continue
            ref = ModelRef(role="lora", name=name, path=str(item["path"]) if item.get("path") else None,
                           strength_model=_number(item.get("strength")), source="recipe")
            ref.extra_strengths = {key: float(item[key]) for key in ("weight_s1", "weight_s2", "weight_s3")
                                   if _number(item.get(key)) is not None}
            loras.append(ref)
    elif cell.get("loras") or overrides.get("lora_stack") or overrides.get("lora_file"):
        if cell.get("loras"):                                # the manifest lists the whole stack of the cell
            pairs = _parse_stack(cell["loras"])
        elif overrides.get("lora_stack"):
            pairs = _parse_stack(overrides["lora_stack"])
        else:
            pairs = [(str(overrides["lora_file"]), _number(overrides.get("lora_strength")))]
        loras = [ModelRef(role="lora", name=name, strength_model=strength, source="recipe") for name, strength in pairs]
    if loras is not None:
        _replace_role(record, ("lora",), loras)
    # --- prompt
    typed = str(overrides.get("prompt") or "").strip()
    sent = str((doc or {}).get("sweep_prompt") or "").strip()
    if sent or typed:
        record.positive = sent or typed
        if sent and typed and sent != typed:
            record.positive_source, record.prompt_rewriter = typed, "LoRA trigger words (sweep)"
        elif typed:
            record.positive_source, record.prompt_rewriter = "", ""
    record.warnings = [w for w in record.warnings if _MULTI_BASE_WARNING not in w]


def apply_plan(record: GenerationRecord, plan: Optional[RecipePlan], frame_index: int = 0,
               frame_count: int = 1) -> GenerationRecord:
    """A copy of the record with the recipe attached and, for known layouts, applied.
    frame_index / frame_count: which image of the saved batch this record is for."""
    if plan is None:
        return record
    out = copy.deepcopy(record)
    for note in plan.notes:
        if note not in out.warnings:
            out.warnings.append(note)
    if plan.base is None:
        return out
    kind = recipe_kind(plan.base)
    base_doc = {key: value for key, value in plan.base.items() if key != "sweep"}
    recipe: Dict[str, Any] = {"kind": kind, "node": plan.class_type, "settings": base_doc}
    doc, cell = base_doc, None
    if plan.is_sweep:
        if frame_count == len(plan.cells) and 0 <= frame_index < len(plan.cells):
            cell = plan.cells[frame_index]
            cell_doc = plan.cell_settings(frame_index)
            if cell_doc is not None:
                doc = cell_doc
            elif isinstance(cell.get("resolved"), dict):      # manifest values of the cell
                doc = {**base_doc, "ultra": {**(base_doc.get("ultra") or {}), **cell["resolved"]}}
                out.warnings.append("sweep cell picture not readable - recipe taken from the sweep manifest")
            else:
                ultra_overrides = {k: v for k, v in (cell.get("overrides") or {}).items() if re.match(r"s\d_", k)}
                doc = {**base_doc, "ultra": {**(base_doc.get("ultra") or {}), **ultra_overrides}}
                out.warnings.append("sweep cell picture not readable - recipe is the panel settings plus the "
                                    "listed overrides")
            recipe["settings"] = doc
            recipe["sweep"] = {key: value for key, value in (
                ("sweep_id", plan.sweep_id), ("cell_index", cell.get("cell_index")), ("cell_file", cell.get("file")),
                ("batch_index", frame_index), ("overrides", cell.get("overrides")), ("metrics", cell.get("metrics")),
                ("manifest", plan.manifest_path)) if value not in (None, "", {})}
        else:
            recipe["sweep"] = {"sweep_id": plan.sweep_id, "manifest": plan.manifest_path, "cells": len(plan.cells)}
            out.warnings.append(
                f"the generator made a sweep of {len(plan.cells)} cells but {frame_count} image(s) reached the "
                f"save - cells could not be matched to images, so the settings listed are the panel values, "
                f"not this image's cell")
    out.recipe = recipe
    if kind == "krea2_settings":
        ultra = doc.get("ultra") if isinstance(doc.get("ultra"), dict) else {}
        seed = None
        if cell is not None:
            seed_value = cell.get("seed", (cell.get("overrides") or {}).get("_seed"))
            seed = int(seed_value) if isinstance(seed_value, (int, float)) else None
        if ultra and any(re.match(r"s\d_steps$", key) for key in ultra):
            out.passes = _krea2_passes(out, ultra, seed)
        if cell is not None:
            _apply_krea2_cell(out, doc if doc is not base_doc else None, cell)
    # the graph reader's "not found" notes no longer hold once the recipe supplied the value
    settled = {"no base model found": bool(out.base_models), "positive prompt not found": bool(out.positive),
               "seed not resolved": out.seed is not None}
    out.warnings = [w for w in out.warnings if not settled.get(w, False)]
    return out
