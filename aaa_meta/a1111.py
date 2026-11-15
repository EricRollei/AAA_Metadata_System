"""
a1111.py
The "parameters" string in Automatic1111 format. Catalog software ignores it;
Civitai and AI image browsers read it to show the prompt and link the models
and LoRAs by hash.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
from typing import Dict, List

from .record import GenerationRecord


def _fmt(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def build_parameters(record: GenerationRecord) -> str:
    lines: List[str] = [record.positive or record.positive_source or ""]
    if record.negative:
        lines.append(f"Negative prompt: {record.negative}")

    settings: List[str] = []
    first = record.passes[0] if record.passes else None
    if first is not None:
        if first.steps is not None:
            settings.append(f"Steps: {first.steps}")
        if first.sampler:
            settings.append(f"Sampler: {first.sampler}")
        if first.scheduler:
            settings.append(f"Schedule type: {first.scheduler}")
        if first.cfg is not None:
            settings.append(f"CFG scale: {_fmt(first.cfg)}")
        if first.guidance is not None:
            settings.append(f"Distilled CFG Scale: {_fmt(first.guidance)}")
        if first.seed is not None:
            settings.append(f"Seed: {first.seed}")
        if first.denoise is not None and first.denoise != 1:
            settings.append(f"Denoising strength: {_fmt(first.denoise)}")
    if record.width and record.height:
        settings.append(f"Size: {record.width}x{record.height}")

    hashes: Dict[str, str] = {}
    base = record.base_models[0] if record.base_models else None
    if base is not None:
        if base.short_hash:
            settings.append(f"Model hash: {base.short_hash}")
            hashes["model"] = base.short_hash
        settings.append(f"Model: {base.stem}")
    for vae in record.by_role("vae")[:1]:
        settings.append(f"VAE: {vae.stem}")
        if vae.short_hash:
            hashes["vae"] = vae.short_hash
    lora_bits: List[str] = []
    for lora in record.loras:
        if lora.short_hash:
            lora_bits.append(f"{lora.stem}: {lora.short_hash}")
            hashes[f"lora:{lora.stem}"] = lora.short_hash
    if lora_bits:
        settings.append('Lora hashes: "' + ", ".join(lora_bits) + '"')
    if hashes:
        settings.append("Hashes: " + json.dumps(hashes, ensure_ascii=False))
    settings.append("Version: ComfyUI" + (f" {record.comfyui_version}" if record.comfyui_version else ""))
    lines.append(", ".join(settings))
    return "\n".join(lines)
