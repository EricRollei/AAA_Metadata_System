"""
record.py
The canonical generation record. Everything downstream (XMP fields, A1111
string, sidecars, the inspector) is derived from this one structure.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

# Roles that count as "the model" for keywords and summaries.
BASE_MODEL_ROLES = ("checkpoint", "unet", "pipeline")
_MODEL_FILE_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".sft", ".bin", ".onnx")


@dataclass
class ModelRef:
    role: str                              # checkpoint, unet, lora, vae, text_encoder, controlnet, ...
    name: str                              # name as given to the loader (may include subfolders)
    path: Optional[str] = None             # resolved absolute path when known
    sha256: Optional[str] = None
    strength_model: Optional[float] = None
    strength_clip: Optional[float] = None
    extra_strengths: Dict[str, float] = field(default_factory=dict)
    node_id: Optional[str] = None
    source: str = "static"                 # "runtime" (seen being loaded) or "static" (read from graph)

    @property
    def stem(self) -> str:
        """File name without folders or extension - the keyword form."""
        base = self.name.replace("\\", "/").rstrip("/").split("/")[-1]
        root, extension = os.path.splitext(base)
        # only a real model-file extension is cut: "Wan2.1-VAE-upscale2x" is a name, not name + ".1-VAE..."
        return root if extension.lower() in _MODEL_FILE_EXTENSIONS else base

    @property
    def short_hash(self) -> Optional[str]:
        """Civitai AutoV2 hash: first 10 hex digits of the SHA-256."""
        return self.sha256[:10] if self.sha256 else None


@dataclass
class SamplingPass:
    index: int
    node_id: str
    node_class: str
    seed: Optional[int] = None
    steps: Optional[int] = None
    cfg: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    denoise: Optional[float] = None
    start_step: Optional[int] = None
    end_step: Optional[int] = None
    guidance: Optional[float] = None
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationRecord:
    positive: str = ""                     # the text the image model actually received
    negative: str = ""
    positive_source: str = ""              # what was typed, when a node rewrote it on the way
    prompt_rewriter: str = ""              # class type of the node that rewrote it
    models: List[ModelRef] = field(default_factory=list)
    passes: List[SamplingPass] = field(default_factory=list)
    model_chain: List[Dict[str, Any]] = field(default_factory=list)   # patches between loader and sampler
    width: Optional[int] = None
    height: Optional[int] = None
    capture_mode: str = "static"           # "runtime", "mixed" or "static"
    anchor_node: Optional[str] = None
    comfyui_version: Optional[str] = None
    created: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # ---- convenience views ---------------------------------------------
    def by_role(self, *roles: str) -> List[ModelRef]:
        return [model for model in self.models if model.role in roles]

    @property
    def base_models(self) -> List[ModelRef]:
        return self.by_role(*BASE_MODEL_ROLES)

    @property
    def loras(self) -> List[ModelRef]:
        return self.by_role("lora")

    @property
    def seed(self) -> Optional[int]:
        for sampling_pass in self.passes:
            if sampling_pass.seed is not None:
                return sampling_pass.seed
        return None

    def keywords(self) -> List[str]:
        """Model, LoRA and sampler keywords (file stems kept whole)."""
        words: List[str] = []
        for model in self.base_models + self.loras:
            if model.stem and model.stem not in words:
                words.append(model.stem)
        for sampling_pass in self.passes:
            if sampling_pass.sampler and sampling_pass.sampler not in words:
                words.append(sampling_pass.sampler)
        return words

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationRecord":
        # Tolerant: the copy stored in files leaves out empty values and node ids, and
        # records written by other versions may carry fields this one does not know.
        def known(kind, values: Dict[str, Any]) -> Dict[str, Any]:
            names = {f.name for f in fields(kind)}
            return {key: value for key, value in values.items() if key in names}

        models = [ModelRef(**{"role": "model", "name": "", **known(ModelRef, m)})
                  for m in data.get("models", []) if isinstance(m, dict)]
        passes = [SamplingPass(**{"index": index, "node_id": "", "node_class": "", **known(SamplingPass, p)})
                  for index, p in enumerate(data.get("passes", [])) if isinstance(p, dict)]
        payload = known(cls, {k: v for k, v in data.items() if k not in ("models", "passes")})
        return cls(models=models, passes=passes, **payload)

    def summary(self) -> str:
        lines: List[str] = [f"capture: {self.capture_mode}"]
        lines.append(f"positive: {self.positive[:300]}{'...' if len(self.positive) > 300 else ''}")
        if self.positive_source:
            lines.append(f"source prompt (before {self.prompt_rewriter or 'rewrite'}): "
                         f"{self.positive_source[:200]}{'...' if len(self.positive_source) > 200 else ''}")
        if self.negative:
            lines.append(f"negative: {self.negative[:200]}{'...' if len(self.negative) > 200 else ''}")
        for model in self.models:
            bits = [f"{model.role}: {model.name}"]
            if model.strength_model is not None:
                bits.append(f"strength {model.strength_model}")
            if model.strength_clip is not None and model.strength_clip != model.strength_model:
                bits.append(f"clip {model.strength_clip}")
            if model.short_hash:
                bits.append(f"hash {model.short_hash}")
            bits.append(f"[{model.source}]")
            lines.append("  ".join(bits))
        for sampling_pass in self.passes:
            parts = [f"pass {sampling_pass.index + 1} ({sampling_pass.node_class})"]
            for label in ("sampler", "scheduler", "steps", "cfg", "guidance", "seed", "denoise",
                          "start_step", "end_step"):
                value = getattr(sampling_pass, label)
                if value is not None:
                    parts.append(f"{label}={value}")
            lines.append(", ".join(parts))
        if self.width and self.height:
            lines.append(f"size: {self.width}x{self.height}")
        for item in self.model_chain:
            params = ", ".join(f"{k}={v}" for k, v in item.get("params", {}).items())
            lines.append(f"model patch: {item.get('class_type')}{' (' + params + ')' if params else ''}")
        for warning in self.warnings:
            lines.append(f"warning: {warning}")
        return "\n".join(lines)
