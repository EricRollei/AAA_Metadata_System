"""Helpers for generating Automatic1111-compatible parameter strings."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .version import get_metadata_system_version_label

METADATA_SYSTEM_GENERATED_BY = get_metadata_system_version_label()

_EMPTY_SEQUENCE = (None, "", [])


def _ensure_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_prompt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        parts = [_normalize_prompt(item) for item in value]
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        preferred_keys = ("text", "prompt", "positive", "negative", "value", "content")
        parts: List[str] = []
        for key in preferred_keys:
            if key in value:
                part = _normalize_prompt(value[key])
                if part:
                    parts.append(part)
        if not parts:
            parts = [_normalize_prompt(item) for item in value.values()]
        return "\n".join(part for part in parts if part)
    return str(value).strip()


def _first_text(candidates: Iterable[Any]) -> str:
    for candidate in candidates:
        text = _normalize_prompt(candidate)
        if text:
            return text
    return ""


def _pick_value(*candidates: Any) -> Any:
    for candidate in candidates:
        if isinstance(candidate, tuple) and len(candidate) == 2:
            container, key = candidate
            if isinstance(container, dict) and key in container:
                value = container[key]
                if value not in _EMPTY_SEQUENCE:
                    return value
        elif candidate not in _EMPTY_SEQUENCE:
            return candidate
    return None


def _to_int(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def _clean_name(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"\s+", " ", value).strip()


def _coerce_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return float(stripped)
            except ValueError:
                return default
        return default
    return default


def _format_strength(value: float) -> str:
    formatted = f"{value:.2f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def _collect_lora_entries(containers: Iterable[Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for container in containers:
        if isinstance(container, list):
            entries.extend(item for item in container if isinstance(item, dict))
        elif isinstance(container, dict):
            entries.extend(item for item in container.values() if isinstance(item, dict))
    return entries


def _iter_lora_sources(*containers: Any) -> List[Any]:
    sources: List[Any] = []
    for container in containers:
        if isinstance(container, dict):
            sources.append(container)
            for key, value in container.items():
                if isinstance(key, str) and "lora" in key.lower():
                    sources.append(value)
        else:
            sources.append(container)
    return sources


def _pick_dimension(keys: Sequence[str], sources: Sequence[Dict[str, Any]]) -> Any:
    for source in sources:
        for key in keys:
            if key in source and source[key] not in _EMPTY_SEQUENCE:
                return source[key]
    return None


def generate_a1111_parameters(
    metadata: Optional[Dict[str, Any]],
    *,
    format_strength: Optional[Callable[[float], str]] = None,
) -> str:
    if not metadata or not isinstance(metadata, dict):
        return ""

    strength_formatter = format_strength or _format_strength

    root_metadata = metadata
    ai_info = _ensure_dict(root_metadata.get("ai_info"))
    generation = _ensure_dict(ai_info.get("generation"))
    if not generation:
        generation = _ensure_dict(root_metadata.get("generation"))

    prompts_section = _ensure_dict(generation.get("prompts"))
    ai_prompts = _ensure_dict(ai_info.get("prompts"))
    metadata_prompts = _ensure_dict(root_metadata.get("prompts"))
    workflow_info = _ensure_dict(ai_info.get("workflow_info"))
    workflow_prompts = _ensure_dict(workflow_info.get("prompts"))

    positive_prompt = _first_text([
        generation.get("positive_prompt"),
        prompts_section.get("positive"),
        generation.get("prompt"),
        ai_prompts.get("positive"),
        metadata_prompts.get("positive"),
        workflow_prompts.get("positive"),
        root_metadata.get("positive_prompt"),
        root_metadata.get("prompt"),
    ])

    negative_prompt = _first_text([
        generation.get("negative_prompt"),
        prompts_section.get("negative"),
        generation.get("negative"),
        generation.get("negative_prompts"),
        ai_prompts.get("negative"),
        metadata_prompts.get("negative"),
        workflow_prompts.get("negative"),
        root_metadata.get("negative_prompt"),
        root_metadata.get("negative"),
    ])

    params: List[str] = []

    sampling = _ensure_dict(generation.get("sampling"))
    metadata_sampling = _ensure_dict(root_metadata.get("sampling"))
    workflow_sampling = _ensure_dict(workflow_info.get("sampling"))

    steps = _pick_value(
        (sampling, "steps"),
        (workflow_sampling, "steps"),
        (metadata_sampling, "steps"),
        (generation, "steps"),
        (root_metadata, "steps"),
    )
    if steps not in _EMPTY_SEQUENCE:
        params.append(f"Steps: {steps}")

    sampler_value = _pick_value(
        (sampling, "sampler"),
        (sampling, "sampler_name"),
        (workflow_sampling, "sampler"),
        (metadata_sampling, "sampler"),
        (generation, "sampler"),
        (generation, "sampler_name"),
        (root_metadata, "sampler"),
    )
    if sampler_value not in _EMPTY_SEQUENCE:
        params.append(f"Sampler: {sampler_value}")

    cfg_scale = _pick_value(
        (sampling, "cfg_scale"),
        (sampling, "cfg"),
        (workflow_sampling, "cfg_scale"),
        (metadata_sampling, "cfg_scale"),
        (metadata_sampling, "cfg"),
        (generation, "cfg_scale"),
        (generation, "cfg"),
        (root_metadata, "cfg_scale"),
        (root_metadata, "cfg"),
    )
    if cfg_scale not in _EMPTY_SEQUENCE:
        params.append(f"CFG scale: {cfg_scale}")

    seed_value = _pick_value(
        (sampling, "seed"),
        (workflow_sampling, "seed"),
        (metadata_sampling, "seed"),
        (generation, "seed"),
        (root_metadata, "seed"),
    )
    if seed_value not in _EMPTY_SEQUENCE:
        params.append(f"Seed: {seed_value}")

    dimensions = _ensure_dict(generation.get("dimensions"))
    metadata_dimensions = _ensure_dict(root_metadata.get("dimensions"))
    workflow_dimensions = _ensure_dict(workflow_info.get("dimensions"))
    technical = _ensure_dict(root_metadata.get("technical"))
    analysis = _ensure_dict(_ensure_dict(root_metadata.get("analysis")).get("technical"))
    image_info = _ensure_dict(root_metadata.get("image"))
    ai_image = _ensure_dict(ai_info.get("image"))

    dimension_sources: List[Dict[str, Any]] = [
        dimensions,
        metadata_dimensions,
        workflow_dimensions,
        technical,
        analysis,
        image_info,
        ai_image,
        generation,
    ]

    width_value = _pick_dimension(("width", "W"), dimension_sources)
    height_value = _pick_dimension(("height", "H"), dimension_sources)

    if width_value in _EMPTY_SEQUENCE or height_value in _EMPTY_SEQUENCE:
        for source in dimension_sources:
            size_value = source.get("size") if isinstance(source, dict) else None
            if isinstance(size_value, str) and "x" in size_value.lower():
                parts = size_value.lower().replace(" ", "").split("x")
                if len(parts) >= 2:
                    width_value = width_value if width_value not in _EMPTY_SEQUENCE else parts[0]
                    height_value = height_value if height_value not in _EMPTY_SEQUENCE else parts[1]
            elif isinstance(size_value, (list, tuple)) and len(size_value) >= 2:
                width_value = width_value if width_value not in _EMPTY_SEQUENCE else size_value[0]
                height_value = height_value if height_value not in _EMPTY_SEQUENCE else size_value[1]

    width_int = _to_int(width_value)
    height_int = _to_int(height_value)
    if width_int and height_int:
        params.append(f"Size: {width_int}x{height_int}")

    base_model = _ensure_dict(generation.get("base_model"))
    if not base_model:
        base_model = _ensure_dict(ai_info.get("base_model"))
    if not base_model:
        base_model = _ensure_dict(root_metadata.get("base_model"))

    model_name = _pick_value(
        (base_model, "name"),
        (base_model, "model"),
        (base_model, "unet"),
        (base_model, "ckpt_name"),
        (generation, "model"),
        (root_metadata, "model"),
    )
    if model_name not in _EMPTY_SEQUENCE:
        params.append(f"Model: {model_name}")

    model_hash = _pick_value(
        (base_model, "hash"),
        (base_model, "model_hash"),
        (base_model, "sha256"),
        (base_model, "checksum"),
        (base_model, "short_hash"),
        (base_model, "model_hash_sha256"),
        (generation, "model_hash"),
        (generation, "hash"),
        (generation, "checksum"),
        (root_metadata, "model_hash"),
    )
    if model_hash not in _EMPTY_SEQUENCE:
        params.append(f"Model hash: {model_hash}")

    modules = _ensure_dict(generation.get("modules"))
    metadata_modules = _ensure_dict(root_metadata.get("modules"))
    ai_assets = _ensure_dict(ai_info.get("assets"))
    metadata_assets = _ensure_dict(root_metadata.get("assets"))
    generation_assets = _ensure_dict(generation.get("assets"))

    lora_sources = _iter_lora_sources(
        generation.get("loras"),
        modules,
        metadata_modules,
        generation_assets,
        metadata_assets,
        ai_assets,
        root_metadata.get("loras"),
    )

    lora_entries = _collect_lora_entries(lora_sources)

    if lora_entries:
        seen = set()
        formatted_loras: List[str] = []
        for lora in lora_entries:
            name = _clean_name(
                lora.get("name")
                or lora.get("alias")
                or lora.get("title")
                or lora.get("id")
            )
            if not name:
                continue

            raw_model_strength = _pick_value(
                (lora, "strength_model"),
                (lora, "strength"),
                (lora, "weight"),
            )
            raw_clip_strength = _pick_value(
                (lora, "strength_clip"),
                (lora, "clip_strength"),
            )

            strength_model_value = _coerce_float(raw_model_strength, 1.0)
            if raw_model_strength in _EMPTY_SEQUENCE and raw_clip_strength not in _EMPTY_SEQUENCE:
                strength_model_value = _coerce_float(raw_clip_strength, strength_model_value)

            strength_clip_value = _coerce_float(raw_clip_strength, strength_model_value)

            formatted_model = strength_formatter(strength_model_value)
            formatted_clip = strength_formatter(strength_clip_value)

            key = (name.lower(), formatted_model, formatted_clip)
            if key in seen:
                continue
            seen.add(key)

            formatted_loras.append(f"{name} ({formatted_model}, {formatted_clip})")

        if formatted_loras:
            params.append(f"LoRA: {'; '.join(formatted_loras)}")

    has_prompt = bool(positive_prompt or negative_prompt)
    if params:
        params.append(METADATA_SYSTEM_GENERATED_BY)
    elif has_prompt:
        params.append(METADATA_SYSTEM_GENERATED_BY)

    lines: List[str] = []
    if positive_prompt:
        lines.append(positive_prompt)
    if negative_prompt:
        lines.append(f"Negative prompt: {negative_prompt}")
    if params:
        lines.append(", ".join(params))

    if not lines:
        has_ai_section = isinstance(metadata, dict) and metadata.get("ai_info") is not None
        return METADATA_SYSTEM_GENERATED_BY if has_ai_section else ""

    return "\n".join(lines).strip()


__all__ = ["generate_a1111_parameters", "METADATA_SYSTEM_GENERATED_BY"]
