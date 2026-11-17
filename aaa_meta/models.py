"""
models.py
Finds model / LoRA references in a node's (resolved) input values without
knowing the node: plain filename widgets, dict widgets such as
{"on": true, "lora": "x.safetensors", "strength": 0.8}, and JSON state strings.

Runtime file lookups (capture/file_loads.py) are the stronger evidence; this
static scan supplies strengths, catches loaders that cache, and is the only
source when reading old images.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".sft", ".bin", ".onnx")
_NONE_NAMES = {"", "none", "null", "disabled", "off", "auto", "default"}
_ENABLE_FLAGS = ("on", "enabled", "enable", "active", "is_active", "is_enabled")

# ComfyUI folder category -> role
CATEGORY_ROLES = {
    "checkpoints": "checkpoint",
    "diffusion_models": "unet",
    "unet": "unet",
    "unet_gguf": "unet",
    "loras": "lora",
    "vae": "vae",
    "text_encoders": "text_encoder",
    "clip": "text_encoder",
    "clip_gguf": "text_encoder",
    "clip_vision": "clip_vision",
    "controlnet": "controlnet",
    "style_models": "style_model",
    "upscale_models": "upscaler",
    "embeddings": "embedding",
    "ipadapter": "ipadapter",
    "model_patches": "model_patch",
    "gligen": "gligen",
    "hypernetworks": "hypernetwork",
    "photomaker": "photomaker",
}
_IGNORED_CATEGORIES = {"vae_approx", "configs", "custom_nodes", "classifiers", "diffusers"}

# Path-style widgets on pipeline loaders: key -> role
_PATH_KEYS = {
    "model_path": "pipeline",
    "base_pipeline_path": "pipeline",
    "pipeline_path": "pipeline",
    "transformer_path": "unet",
    "text_encoder_path": "text_encoder",
    "vae_path": "vae",
    "vae_source": "vae",
}


def role_for_category(category: str) -> Optional[str]:
    if category in _IGNORED_CATEGORIES:
        return None
    return CATEGORY_ROLES.get(category, category)


def role_for_key(key: str, class_type: str) -> str:
    low = key.lower()
    cls = class_type.lower()
    if "lora" in low:
        return "lora"
    if "ckpt" in low or "checkpoint" in low:
        return "checkpoint" if ("checkpoint" in cls or "ckpt" in cls or "loader" in cls) else "model"
    if "unet" in low or "diffusion" in low or "transformer" in low:
        return "unet"
    if "clip_vision" in low or "clipvision" in cls or "clip_vision" in cls:
        return "clip_vision"
    if "vae" in low:
        return "vae"
    if "clip" in low or "text_encoder" in low or "t5" in low or "llm" in low:
        return "text_encoder"
    if "control" in low:
        return "controlnet"
    if "upscale" in low:
        return "upscaler"
    if "style" in low:
        return "style_model"
    if "lora" in cls:
        return "lora"
    if "vae" in cls:
        return "vae"
    if "upscal" in cls:
        return "upscaler"
    if "controlnet" in cls:
        return "controlnet"
    if "unet" in cls or "dit" in cls or "diffusion" in cls:
        return "unet"
    return "model"


def _role_from_key_only(key: str) -> Optional[str]:
    low = key.lower()
    for words, role in ((("lora",), "lora"), (("unet", "diffusion", "transformer"), "unet"),
                        (("clip_vision",), "clip_vision"), (("vae",), "vae"),
                        (("text_encoder", "clip", "t5", "llm"), "text_encoder"),
                        (("ckpt", "checkpoint"), "checkpoint"), (("control",), "controlnet"),
                        (("upscale",), "upscaler")):
        if any(word in low for word in words):
            return role
    return None


def _role_from_path(path: List[str], top_key: str, class_type: str) -> str:
    """
    Role of a file name found under `path` (outermost key first). The key closest
    to the value decides: {"transformer_path": ..., "text_encoder_path": ...} inside
    a pipeline object means the same wherever that object is plugged in - it must
    not turn into a LoRA because the node holding it has LoRA in its name.
    """
    for key in reversed(path[1:]):
        role = _role_from_key_only(key)
        if role is not None:
            return role
    if len(path) > 1:
        # inside a structure with no telling key: the top-level widget name may still say,
        # the node's class name does not
        return _role_from_key_only(top_key) or "model"
    return role_for_key(top_key, class_type)


def looks_like_model_file(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 400 or "\n" in value:
        return False
    return value.strip().lower().endswith(MODEL_EXTENSIONS)


@dataclass
class FoundModel:
    name: str
    role: str
    key: str                                   # top-level input name it was found under
    enabled: bool = True
    strength_model: Optional[float] = None
    strength_clip: Optional[float] = None
    extra_strengths: Dict[str, float] = field(default_factory=dict)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _strengths_from_mapping(mapping: Dict[str, Any], found: FoundModel) -> None:
    for key, value in mapping.items():
        number = _num(value)
        if number is None:
            continue
        low = key.lower()
        if low in ("strength", "strength_model", "model_strength", "model_weight", "weight", "lora_strength", "scale", "sm"):
            if found.strength_model is None:
                found.strength_model = number
        elif low in ("strengthtwo", "strength_clip", "clip_strength", "clip_weight", "sc"):
            found.strength_clip = number
        elif "strength" in low or "weight" in low:
            found.extra_strengths[key] = number
    if found.strength_model is None and found.extra_strengths:
        first_key = next(iter(found.extra_strengths))
        found.strength_model = found.extra_strengths[first_key]


def _trailing_number(key: str) -> Optional[str]:
    match = re.search(r"(\d+)$", key)
    return match.group(1) if match else None


def _apply_sibling_values(found: FoundModel, values: Dict[str, Any]) -> None:
    """Strengths and on/off flags that sit beside a plain filename widget."""
    number = _trailing_number(found.key)
    if number is None:
        siblings = {k: v for k, v in values.items()
                    if k != found.key and ("strength" in k.lower() or "weight" in k.lower())}
        _strengths_from_mapping(siblings, found)
        return
    siblings = {}
    for key, value in values.items():
        if key == found.key:
            continue
        digits = re.findall(r"\d+", key)
        if not digits or digits[0] != number:
            continue
        low = key.lower()
        stripped = re.sub(r"[\d_]+", "", low)
        if stripped in _ENABLE_FLAGS or low.startswith(("on_", "enable", "use_")) or low.endswith(("_on", "_enabled")):
            if value is False:
                found.enabled = False
        elif "strength" in low or "weight" in low or "_wt" in low:
            numeric = _num(value)
            if numeric is not None:
                found.extra_strengths[key] = numeric
    if found.extra_strengths:
        found.strength_model = next(iter(found.extra_strengths.values()))
        if len(found.extra_strengths) == 1:
            found.extra_strengths = {}


def _walk(value: Any, top_key: str, path: List[str], context: Optional[dict],
          class_type: str, depth: int = 0) -> Iterator[FoundModel]:
    if depth > 6:
        return
    if isinstance(value, str):
        text = value.strip()
        if looks_like_model_file(text):
            if text.lower() in _NONE_NAMES:
                return
            role = _role_from_path(path, top_key, class_type)
            found = FoundModel(name=text, role=role, key=top_key)
            if context is not None:
                for flag in _ENABLE_FLAGS:
                    if context.get(flag) is False:
                        found.enabled = False
                _strengths_from_mapping(context, found)
            yield found
        elif text[:1] in "{[" and len(text) < 400_000:
            try:
                parsed = json.loads(text)
            except Exception:
                return
            yield from _walk(parsed, top_key, path, None, class_type, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, top_key, path + [str(key)], value, class_type, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item, top_key, path, context, class_type, depth + 1)


def scan_values(values: Dict[str, Any], class_type: str) -> List[FoundModel]:
    """Find model references in a node's resolved input values."""
    results: List[FoundModel] = []
    for key, value in values.items():
        for found in _walk(value, key, [key], None, class_type):
            if isinstance(value, str) and looks_like_model_file(value):
                _apply_sibling_values(found, values)
            results.append(found)
    # Path-style widgets on pipeline loaders (folders, repo ids).
    for key, role in _PATH_KEYS.items():
        value = values.get(key)
        if isinstance(value, str) and value.strip().lower() not in _NONE_NAMES and not looks_like_model_file(value):
            if len(value) < 400 and "\n" not in value:
                if key == "model_path" and "vae" in class_type.lower():
                    role = "vae"
                results.append(FoundModel(name=value.strip(), role=role, key=key))
    # Named models on loader nodes without a file extension.
    if "load" in class_type.lower():
        for key in ("model_name", "model"):
            value = values.get(key)
            if (isinstance(value, str) and value.strip().lower() not in _NONE_NAMES
                    and not looks_like_model_file(value) and len(value) < 200 and "\n" not in value):
                results.append(FoundModel(name=value.strip(), role="pipeline", key=key))
    return results


def base_name(name: str) -> str:
    return name.replace("\\", "/").rstrip("/").split("/")[-1].lower()
