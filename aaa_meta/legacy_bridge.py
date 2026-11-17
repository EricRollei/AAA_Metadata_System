"""
legacy_bridge.py
Lets the full-featured v099d save node keep every one of its features and
widgets while its metadata comes from the v2 capture core and is written by
the v2 writer.

The old node asks its metadata service to write to targets ("embedded", "xmp",
"txt", "db"). ServiceBridge stands in for that service:
    embedded -> v2 writer (catalog-searchable fields + hcai / eiqa namespaces)
    xmp      -> v2 sidecar, identical to the embedded packet
    txt, db  -> the old service, fed with the values the v2 core collected

Kept free of ComfyUI imports so it can be tested on its own.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import copy
import json
import os
from typing import Any, Dict, List, Optional

from . import color, embed
from .fields import UserFields
from .record import GenerationRecord
from .writer import build_sidecar_packet, update_metadata

_NO_EMBED_EXTENSIONS = (".svg",)


def map_color_profile(widget_value: str) -> str:
    """Old colour-profile widget value -> v2 colour space used for pixel conversion."""
    low = str(widget_value or "").lower()
    if "adobe" in low:
        return color.PROFILE_ADOBE
    if "prophoto" in low:
        return color.PROFILE_PROPHOTO
    if low == "none":
        return color.PROFILE_NONE
    return color.PROFILE_SRGB


def user_fields_from_widgets(values: Dict[str, Any]) -> UserFields:
    custom: Dict[str, Any] = {}
    raw = values.get("custom_metadata")
    if isinstance(raw, str) and raw.strip() not in ("", "{}"):
        try:
            parsed = json.loads(raw)
            custom = parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            custom = {"text": raw}
    keywords = [k.strip() for k in str(values.get("keywords") or "").split(",") if k.strip()]
    return UserFields(
        title=str(values.get("title") or ""),
        keywords=keywords,
        creator=str(values.get("creator") or ""),
        copyright=str(values.get("copyright") or ""),
        description=str(values.get("description") or ""),
        project=str(values.get("project") or ""),
        custom=custom,
    )


def legacy_generation_overlay(record: GenerationRecord) -> Dict[str, Any]:
    """The v2 record in the shape the old txt / db writers expect under ai_info.generation."""
    first = record.passes[0] if record.passes else None
    base = record.base_models[0] if record.base_models else None
    overlay: Dict[str, Any] = {
        "prompt": record.positive or record.positive_source,
        "negative_prompt": record.negative,
        "source_prompt": record.positive_source,
        "model": base.stem if base else None,
        "model_hash": base.short_hash if base else None,
        "sampler": first.sampler if first else None,
        "scheduler": first.scheduler if first else None,
        "steps": first.steps if first else None,
        "cfg_scale": first.cfg if first else None,
        "seed": first.seed if first else None,
        "denoise": first.denoise if first else None,
        "width": record.width,
        "height": record.height,
        "loras": [{"name": m.stem, "strength": m.strength_model} for m in record.loras] or None,
        "vae": next((m.stem for m in record.by_role("vae")), None),
        "capture_mode": record.capture_mode,
    }
    if len(record.passes) > 1:
        overlay["passes"] = [{k: v for k, v in vars(p).items() if v not in (None, {}, "") and k not in ("node_id",)}
                             for p in record.passes]
    return {k: v for k, v in overlay.items() if v not in (None, "", [])}


class ServiceBridge:
    """Stand-in for the old MetadataService on the v1.0 save node (see module docstring)."""

    def __init__(self, legacy_service: Any):
        self._legacy = legacy_service
        self.debug = getattr(legacy_service, "debug", False)
        self.record: Optional[GenerationRecord] = None
        self.user = UserFields()
        self.include_paths = False
        self.a1111 = True
        self.enabled = True
        self.results: List[Dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:        # everything else behaves as before
        return getattr(self._legacy, name)

    def begin(self, record: Optional[GenerationRecord], user: UserFields, include_paths: bool, a1111: bool) -> None:
        self.record, self.user, self.include_paths, self.a1111 = record, user, include_paths, a1111
        self.results = []

    def write_metadata(self, filepath: str, metadata: Optional[Dict[str, Any]] = None,
                       targets: Optional[List[str]] = None, **kwargs) -> bool:
        targets = list(targets or ["embedded"])
        metadata = metadata or {}
        analysis = metadata.get("analysis") if isinstance(metadata.get("analysis"), dict) else None
        extension = os.path.splitext(filepath)[1].lower()
        ok = True
        if "embedded" in targets and extension not in _NO_EMBED_EXTENSIONS:
            result = update_metadata(filepath, self.record, self.user, analysis,
                                     include_paths=self.include_paths, a1111=self.a1111)
            self.results.append(result)
            ok = ok and bool(result.get("embedded"))
        if "xmp" in targets:
            try:
                embed.write_sidecar(filepath, build_sidecar_packet(self.record, self.user, analysis, self.include_paths))
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": False, "warnings": [f"sidecar not written: {exc!r}"]})
                ok = False
        legacy_targets = [t for t in targets if t in ("txt", "db")]
        if legacy_targets:
            legacy_metadata = copy.deepcopy(metadata)
            if self.record is not None:
                generation = legacy_metadata.setdefault("ai_info", {}).setdefault("generation", {})
                generation.update(legacy_generation_overlay(self.record))
            try:
                self._legacy.write_metadata(filepath, legacy_metadata, targets=legacy_targets)
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": True, "warnings": [f"{'/'.join(legacy_targets)} not written: {exc!r}"]})
        return ok

    def summary(self) -> str:
        lines: List[str] = []
        for result in self.results:
            name = os.path.basename(result.get("path", ""))
            report = result.get("verify")
            if report is not None and report.get("ok"):
                lines.append(f"{name}: metadata verified ({', '.join(report.get('present', []))})")
            elif report is not None:
                problems = report.get("missing", []) + [f"{m} differs" for m in report.get("mismatch", [])]
                lines.append(f"{name}: METADATA PROBLEM - {', '.join(problems)}")
            elif not result.get("embedded", True):
                lines.append(f"{name}: metadata NOT embedded")
            for warning in result.get("warnings", []):
                lines.append(f"  note: {warning}")
        return "\n".join(lines)
