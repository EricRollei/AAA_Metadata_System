"""Helpers for deriving generation parameters from ComfyUI workflows.

These utilities focus on identifying sampler configuration, model selection,
latent dimensions, and other generation-related values. They are intentionally
lenient so preparation work can stabilise before we introduce strict schema
expectations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from .parsing import AssetDiscovery, WorkflowGraph, WorkflowParsingService

logger = logging.getLogger(__name__)


def extract_generation_parameters(
    workflow: Dict[str, Any],
    *,
    parsing_service: Optional[WorkflowParsingService] = None,
) -> Dict[str, Any]:
    """Return a best-effort dictionary of generation controls.

    The intent is not to be perfect, but to provide stable hooks for upcoming
    refactors and tests. When values cannot be derived they are simply omitted.
    """

    if not isinstance(workflow, dict):
        return {}

    parsing = parsing_service or WorkflowParsingService()
    graph = WorkflowGraph.from_workflow(workflow)
    nodes = graph.nodes

    generation: Dict[str, Any] = {}

    sampler_payload = _extract_sampler_settings(nodes)
    if sampler_payload:
        generation.update(sampler_payload)

    dimensions = _extract_dimensions(nodes)
    if dimensions:
        generation.update(dimensions)

    model_name = _extract_model_name(nodes)
    if model_name:
        generation["model"] = model_name

    vae_name = _extract_first_string(nodes, ("vae", "vae_name"))
    if vae_name:
        generation["vae"] = vae_name

    assets = parsing.discover_assets(workflow)
    lora_entries = _build_lora_entries(assets)
    if lora_entries:
        generation["loras"] = lora_entries

    return generation


def _extract_sampler_settings(nodes: Dict[str, Any]) -> Dict[str, Any]:
    best_candidate: Optional[Dict[str, Any]] = None
    best_score = -1

    for node_id, node in nodes.items():
        class_type = _get_class_type(node)
        lowered = class_type.lower()
        if "sampler" not in lowered:
            continue

        inputs = _extract_inputs(node)
        score = _score_sampler_inputs(inputs)
        if score > best_score:
            best_candidate = inputs
            best_score = score

    if not best_candidate:
        return {}

    payload: Dict[str, Any] = {}

    sampler_name = _first_string(best_candidate, ("sampler", "sampler_name"))
    if sampler_name:
        payload["sampler"] = sampler_name

    scheduler = _first_string(best_candidate, ("scheduler", "scheduler_name"))
    if scheduler:
        payload["scheduler"] = scheduler

    steps = _first_numeric(best_candidate, ("steps", "max_steps", "sampling_steps"), coerce=int)
    if steps is not None:
        payload["steps"] = steps

    cfg = _first_numeric(best_candidate, ("cfg_scale", "cfg", "guidance_scale", "scale"))
    if cfg is not None:
        payload["cfg_scale"] = cfg

    seed = _first_numeric(best_candidate, ("seed", "noise_seed", "latent_seed"), coerce=int)
    if seed is not None:
        payload["seed"] = seed

    denoise = _first_numeric(best_candidate, ("denoise", "denoise_strength", "sigma_start"))
    if denoise is not None:
        payload["denoise"] = denoise

    return payload


def _score_sampler_inputs(inputs: Dict[str, Any]) -> int:
    if not inputs:
        return -1
    score = 0
    for key in ("steps", "cfg", "cfg_scale", "sampler", "sampler_name", "seed"):
        if key in inputs:
            score += 1
    return score


def _extract_dimensions(nodes: Dict[str, Any]) -> Dict[str, Any]:
    for node in nodes.values():
        inputs = _extract_inputs(node)
        width = _first_numeric(inputs, ("width", "w"), coerce=int)
        height = _first_numeric(inputs, ("height", "h"), coerce=int)
        if width is not None and height is not None:
            return {"width": width, "height": height}
    return {}


def _extract_model_name(nodes: Dict[str, Any]) -> Optional[str]:
    preferred_order = (
        "CheckpointLoaderSimple",
        "CheckpointLoader",
        "ModelLoader",
        "DiffusersLoader",
        "unCLIPCheckpointLoader",
    )

    best_name: Optional[str] = None
    best_priority = len(preferred_order)

    for node in nodes.values():
        class_type = _get_class_type(node)
        inputs = _extract_inputs(node)
        candidate = _first_string(
            inputs,
            (
                "ckpt_name",
                "model_name",
                "model",
                "checkpoint",
                "checkpoint_name",
            ),
        )
        if not candidate:
            continue

        try:
            priority = preferred_order.index(class_type)
        except ValueError:
            priority = len(preferred_order)

        if best_name is None or priority < best_priority:
            best_name = candidate
            best_priority = priority

    return best_name


def _extract_first_string(nodes: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for node in nodes.values():
        inputs = _extract_inputs(node)
        candidate = _first_string(inputs, keys)
        if candidate:
            return candidate
    return None


def _build_lora_entries(assets: AssetDiscovery) -> Optional[list]:
    if not assets.loras:
        return None

    entries = []
    for record in assets.loras:
        strength = record.extra.get("strength_model")
        if strength is None:
            strength = record.extra.get("strength")
        strength_value = _coerce_float(strength) or 1.0

        clip_strength = _coerce_float(record.extra.get("clip_strength"))

        payload: Dict[str, Any] = {
            "name": record.name,
            "strength": strength_value,
            "source": record.source,
        }
        if clip_strength is not None:
            payload["clip_strength"] = clip_strength

        entries.append(payload)

    return entries or None


def _get_class_type(node: Dict[str, Any]) -> str:
    value = node.get("class_type") or node.get("type") or ""
    return str(value)


def _extract_inputs(node: Dict[str, Any]) -> Dict[str, Any]:
    raw = node.get("inputs")
    if isinstance(raw, dict):
        return raw

    if isinstance(raw, list):
        mapping: Dict[str, Any] = {}
        for entry in raw:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("key")
                if name:
                    mapping[str(name)] = entry.get("value")
        return mapping

    return {}


def _first_string(inputs: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    value = _first(inputs, keys)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_numeric(
    inputs: Dict[str, Any],
    keys: Iterable[str],
    *,
    coerce=float,
) -> Optional[float]:
    value = _first(inputs, keys)
    return _coerce_numeric(value, coerce=coerce)


def _first(inputs: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in inputs:
            return inputs[key]
    return None


def _coerce_numeric(value: Any, *, coerce=float) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return coerce(value)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return coerce(float(stripped) if coerce is float else int(float(stripped)))
        except (TypeError, ValueError):
            return None
    return None


def _coerce_float(value: Any) -> Optional[float]:
    return _coerce_numeric(value, coerce=float)
