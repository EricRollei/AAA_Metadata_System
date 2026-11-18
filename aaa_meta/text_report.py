"""
text_report.py
The human-readable .txt written beside an image ("save_txt" on the save node).

Plain sections, one value per line, long text kept whole. Written fresh from
the generation record each time the image is saved.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import datetime
import os
from typing import Any, Dict, List, Optional

from .fields import UserFields
from .record import BASE_MODEL_ROLES, GenerationRecord, ModelRef

_ROLE_LABELS = {
    "checkpoint": "Base model", "unet": "Base model", "pipeline": "Base pipeline", "lora": "LoRA",
    "text_encoder": "Text encoder", "vae": "VAE", "prompt_llm": "Prompt LLM", "clip_vision": "CLIP vision",
    "controlnet": "ControlNet", "upscaler": "Upscaler", "post_model": "Post-processing model",
    "sams": "Segmentation model", "grounding-dino": "Detection model", "model": "Model",
}
_WIDTH = 22


def _number(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _line(label: str, value: Any) -> str:
    return f"  {((label + ':') if label else ''):<{_WIDTH}} {value}"


def _model_line(model: ModelRef) -> str:
    label = _ROLE_LABELS.get(model.role, model.role.replace("_", " ").replace("-", " ").capitalize())
    notes: List[str] = []
    if model.strength_model is not None:
        notes.append(f"strength {_number(model.strength_model)}")
    if model.strength_clip is not None and model.strength_clip != model.strength_model:
        notes.append(f"clip {_number(model.strength_clip)}")
    if model.extra_strengths:
        notes.append(", ".join(f"{key} {_number(value)}" for key, value in model.extra_strengths.items()))
    if model.short_hash:
        notes.append(f"hash {model.short_hash}")
    return _line(label, model.stem + (f"   ({'; '.join(notes)})" if notes else ""))


def _flatten(data: Dict[str, Any], prefix: str = "") -> List[str]:
    lines: List[str] = []
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            lines.extend(_flatten(value, path))
        elif isinstance(value, (list, tuple)):
            if value and all(not isinstance(v, (dict, list)) for v in value):
                lines.append(_line(path, ", ".join(_number(v) for v in value)))
            else:
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        lines.extend(_flatten(item, f"{path}[{index + 1}]"))
                    else:
                        lines.append(_line(f"{path}[{index + 1}]", _number(item)))
        elif value not in (None, ""):
            lines.append(_line(path, _number(value)))
    return lines


def build_report(image_path: str, record: Optional[GenerationRecord], user: Optional[UserFields] = None,
                 analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False) -> str:
    user = user or UserFields()
    out: List[str] = [os.path.basename(image_path),
                      "Saved " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""]

    def section(title: str, lines: List[str]) -> None:
        if lines:
            out.append(title)
            out.extend(lines)
            out.append("")

    details: List[str] = []
    for label, value in (("Title", user.title), ("Project", user.project), ("Description", user.description),
                         ("Creator", user.creator), ("Copyright", user.copyright),
                         ("Keywords", ", ".join(user.keywords))):
        if str(value or "").strip():
            details.append(_line(label, str(value).strip()))
    for key, value in (user.custom or {}).items():
        details.append(_line(str(key), _number(value) if not isinstance(value, (dict, list)) else str(value)))
    section("DETAILS", details)

    if record is not None:
        section("PROMPT", [record.positive.strip()] if record.positive.strip() else [])
        if record.positive_source.strip() and record.positive_source.strip() != record.positive.strip():
            by = f" (before rewriting by {record.prompt_rewriter})" if record.prompt_rewriter else " (as typed)"
            section("TYPED PROMPT" + by, [record.positive_source.strip()])
        section("NEGATIVE PROMPT", [record.negative.strip()] if record.negative.strip() else [])

        models: List[str] = []
        for model in record.models:
            models.append(_model_line(model))
            if include_paths and model.path:
                models.append(_line("", model.path))
        section("MODELS", models)

        sampling: List[str] = []
        many = len(record.passes) > 1
        for item in record.passes:
            parts = [f"{label} {_number(getattr(item, key))}" for key, label in (
                ("sampler", "sampler"), ("scheduler", "scheduler"), ("steps", "steps"), ("cfg", "cfg"),
                ("guidance", "guidance"), ("denoise", "denoise"), ("start_step", "from step"),
                ("end_step", "to step"), ("seed", "seed")) if getattr(item, key) is not None]
            label = f"Pass {item.index + 1}" if many else "Sampling"
            sampling.append(_line(label, ", ".join(parts)))
            if item.node_class:
                sampling.append(_line("", f"node: {item.node_class}"))
        if record.width and record.height:
            sampling.append(_line("Size", f"{record.width} x {record.height}"))
        for patch in record.model_chain:
            params = ", ".join(f"{k} {_number(v)}" for k, v in patch.get("params", {}).items())
            sampling.append(_line("Model patch", f"{patch.get('class_type')}{' (' + params + ')' if params else ''}"))
        section("SAMPLING", sampling)

    if record is not None and record.recipe:
        from .recipes import recipe_for_embedding
        recipe = recipe_for_embedding(record.recipe, include_paths)
        settings = dict(recipe.get("settings") or {})
        settings.pop("sweep_prompt", None)                   # shown above as the prompt
        sweep = dict(recipe.get("sweep") or {})
        if isinstance(sweep.get("overrides"), dict):
            sweep["overrides"] = {k: v for k, v in sweep["overrides"].items() if k != "prompt"}
        title = f"RECIPE ({recipe.get('kind', 'settings')} as stated by {recipe.get('node', 'the generator node')})"
        section(title, (_flatten({"sweep": sweep}) if sweep else []) + _flatten(settings))

    section("MEASUREMENTS", _flatten(analysis) if analysis else [])

    if record is not None:
        about = [_line("Collected", {"runtime": "while the workflow ran", "static": "from the workflow graph",
                                     "mixed": "while the workflow ran + from the graph",
                                     "manual": "entered by hand"}.get(record.capture_mode, record.capture_mode))]
        if record.comfyui_version:
            about.append(_line("ComfyUI", record.comfyui_version))
        if record.created:
            about.append(_line("Generated", record.created))
        section("ABOUT", about)
        section("NOTES", [f"  - {warning}" for warning in record.warnings])
    return "\n".join(out).rstrip() + "\n"


def write_report(image_path: str, record: Optional[GenerationRecord], user: Optional[UserFields] = None,
                 analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False) -> str:
    path = os.path.splitext(image_path)[0] + ".txt"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_report(image_path, record, user, analysis, include_paths))
    return path
