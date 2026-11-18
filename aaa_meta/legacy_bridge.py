"""
legacy_bridge.py
Lets the full-featured v099d save node keep every one of its features and
widgets while its metadata comes from the v2 capture core and is written by
the v2 writer.

The old node asks its metadata service to write to targets ("embedded", "xmp",
"txt", "db"). ServiceBridge stands in for that service:
    embedded -> v2 writer (catalog-searchable fields + hcai / eiqa namespaces)
    xmp      -> v2 sidecar, identical to the embedded packet
    txt      -> text_report (plain, readable)
    db       -> the old service, fed with the values the v2 core collected

Kept free of ComfyUI imports so it can be tested on its own.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import copy
import json
import os
from typing import Any, Dict, List, Optional

from . import color, embed, reader, service_mirror, text_report
from .fields import StandardFields, UserFields, build_standard_fields
from .record import GenerationRecord, ModelRef, SamplingPass
from .writer import build_sidecar_packet, patch_metadata, snapshot_standard, update_metadata

_NO_EMBED_EXTENSIONS = (".svg",)


def map_color_profile(widget_value: str) -> str:
    """Old colour-profile widget value -> v2 colour space used for pixel conversion."""
    low = str(widget_value or "").lower()
    if "p3" in low:
        return color.PROFILE_P3
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
        self.measurements: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []
        self.frame_index = 0                                # set by the node: which image of the batch
        self.record_for_frame = None                        # optional: frame index -> record of that image

    def __getattr__(self, name: str) -> Any:        # everything else behaves as before
        return getattr(self._legacy, name)

    def begin(self, record: Optional[GenerationRecord], user: UserFields, include_paths: bool, a1111: bool,
              measurements: Optional[Dict[str, Any]] = None) -> None:
        self.record, self.user, self.include_paths, self.a1111 = record, user, include_paths, a1111
        self.measurements = dict(measurements or {})
        self.results = []
        self.frame_index, self.record_for_frame = 0, None

    def write_metadata(self, filepath: str, metadata: Optional[Dict[str, Any]] = None,
                       targets: Optional[List[str]] = None, **kwargs) -> Dict[str, bool]:
        targets = list(targets or ["embedded"])
        metadata = metadata or {}
        analysis = metadata.get("analysis") if isinstance(metadata.get("analysis"), dict) else None
        if self.measurements:                               # collected automatically for this image
            analysis = {**self.measurements, **(analysis or {})}
        extension = os.path.splitext(filepath)[1].lower()
        status: Dict[str, bool] = {target: True for target in targets}
        if self.record_for_frame is not None and self.record is not None:
            try:                                            # sweeps: every image has its own record
                self.record = self.record_for_frame(self.frame_index) or self.record
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": True,
                                     "warnings": [f"per-image recipe not applied: {exc!r}"]})
        if not os.path.isfile(filepath):                    # the image itself was not saved
            self.results.append({"path": filepath, "embedded": False, "warnings": ["image file was not written"]})
            return {target: False for target in targets}
        if "embedded" in targets and extension not in _NO_EMBED_EXTENSIONS:
            result = update_metadata(filepath, self.record, self.user, analysis,
                                     include_paths=self.include_paths, a1111=self.a1111, strip_iim=True)
            self.results.append(result)
            status["embedded"] = bool(result.get("embedded"))
        if "xmp" in targets:
            try:
                embed.write_sidecar(filepath, build_sidecar_packet(self.record, self.user, analysis, self.include_paths))
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": False, "warnings": [f"sidecar not written: {exc!r}"]})
                status["xmp"] = False
        if "txt" in targets:
            # own plain-text report (the old writer printed raw Python structures)
            try:
                report_analysis = {k: v for k, v in (analysis or {}).items() if k != "layer_info"} or None
                text_report.write_report(filepath, self.record, self.user, report_analysis, self.include_paths)
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": True, "warnings": [f"txt not written: {exc!r}"]})
                status["txt"] = False
        legacy_targets = [t for t in targets if t == "db"]
        if legacy_targets:
            legacy_metadata = copy.deepcopy(metadata)
            if self.record is not None:
                generation = legacy_metadata.setdefault("ai_info", {}).setdefault("generation", {})
                generation.update(legacy_generation_overlay(self.record))
            if self.measurements and isinstance(legacy_metadata.get("analysis", {}), dict):
                legacy_metadata["analysis"] = {**self.measurements, **legacy_metadata.get("analysis", {})}
            try:
                with service_mirror.suppressed():
                    self._legacy.write_metadata(filepath, legacy_metadata, targets=legacy_targets)
            except Exception as exc:
                self.results.append({"path": filepath, "embedded": True, "warnings": [f"{'/'.join(legacy_targets)} not written: {exc!r}"]})
                for target in legacy_targets:
                    status[target] = False
        return status

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


# ---------------------------------------------------------------------------
# companion nodes (entry, query, filter, debugger, consolidator)
# ---------------------------------------------------------------------------
_BASE_ROLES = ("checkpoint", "unet", "diffusion_model")


def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target


def apply_typed_generation(record: Optional[GenerationRecord], typed: Dict[str, Any]) -> GenerationRecord:
    """Hand-entered generation values (old ai_info.generation keys) placed onto a record."""
    record = record or GenerationRecord(capture_mode="manual")
    if typed.get("prompt"):
        record.positive = str(typed["prompt"])
    if typed.get("negative_prompt"):
        record.negative = str(typed["negative_prompt"])
    if typed.get("model"):
        record.models = [m for m in record.models if m.role not in _BASE_ROLES]
        record.models.insert(0, ModelRef(role="checkpoint", name=str(typed["model"]), source="manual"))
    sampling_keys = {"seed": "seed", "steps": "steps", "cfg_scale": "cfg", "sampler": "sampler",
                     "scheduler": "scheduler", "denoise": "denoise"}
    if any(typed.get(key) not in (None, "") for key in sampling_keys):
        if not record.passes:
            record.passes.append(SamplingPass(index=0, node_id="", node_class="manual"))
        for key, attribute in sampling_keys.items():
            if typed.get(key) not in (None, ""):
                setattr(record.passes[0], attribute, typed[key])
    if typed.get("width"):
        record.width = int(typed["width"])
    if typed.get("height"):
        record.height = int(typed["height"])
    return record


def to_legacy_shape(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """reader.read_file() result in the layout the old nodes query: basic / ai_info / analysis."""
    out: Dict[str, Any] = {}
    standard = parsed.get("standard") or {}
    basic = {new: standard[old] for old, new in (("title", "title"), ("description", "description"),
                                                 ("keywords", "keywords"), ("creator", "creator"),
                                                 ("rights", "rights"), ("rating", "rating"),
                                                 ("headline", "headline"), ("instructions", "instructions"))
             if standard.get(old) not in (None, "", [])}
    if parsed.get("project"):
        basic["project"] = parsed["project"]
    if basic:
        out["basic"] = basic
    generation = reader.generation_summary(parsed)
    if generation or parsed.get("record"):
        out["ai_info"] = {"generation": generation}
        if parsed.get("record"):
            out["ai_info"]["record"] = parsed["record"]
    if parsed.get("analysis"):
        out["analysis"] = parsed["analysis"]
    if parsed.get("custom"):
        out["custom"] = parsed["custom"]
    return out


class CompanionService:
    """
    Stand-in for the old MetadataService on the entry / query / filter / debugger /
    consolidator nodes. The old service still does everything it did (so the
    database, text files and old-format data keep working); on top of that
      * reads return what the v2 writer stored (generation record, measured data)
      * writes also go into the catalog-searchable fields and the hcai / eiqa
        namespaces, without erasing what the file already holds
    """

    def __init__(self, legacy_service: Any):
        self._legacy = legacy_service
        self.last_warnings: List[str] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._legacy, name)

    @property
    def debug(self) -> bool:
        return getattr(self._legacy, "debug", False)

    @debug.setter
    def debug(self, value: bool) -> None:
        self._legacy.debug = value

    # -- read ---------------------------------------------------------------
    def read_metadata(self, filepath: str, source: str = "embedded", fallback: bool = True) -> Dict[str, Any]:
        try:
            result = self._legacy.read_metadata(filepath, source=source, fallback=fallback) or {}
        except Exception:
            result = {}
        if source in ("txt", "db") or not os.path.exists(filepath):
            return result
        try:
            if fallback:
                parsed = reader.read_file(filepath, prefer="sidecar" if source == "xmp" else "embedded")
            else:
                packet = embed.read_sidecar(filepath) if source == "xmp" else embed.read_xmp(filepath)
                parsed = reader.parse_packet(packet)
            overlay = to_legacy_shape(parsed)
        except Exception:
            overlay = {}
        if overlay:
            result = _deep_update(copy.deepcopy(result) if isinstance(result, dict) else {}, overlay)
        return result

    # -- write --------------------------------------------------------------
    def write_metadata(self, filepath: str, metadata: Optional[Dict[str, Any]] = None,
                       targets: Optional[List[str]] = None, **kwargs) -> Dict[str, bool]:
        targets = list(targets) if targets is not None else ["embedded", "xmp", "txt", "db"]
        metadata = metadata or {}
        self.last_warnings = []
        try:
            saved = snapshot_standard(filepath) if os.path.exists(filepath) else None
        except Exception:
            saved = None
        try:
            with service_mirror.suppressed():
                results = self._legacy.write_metadata(filepath, metadata, targets=targets)
            results = dict(results) if isinstance(results, dict) else {t: bool(results) for t in targets}
        except Exception as exc:
            results = {t: False for t in targets}
            self.last_warnings.append(f"old writer: {exc!r}")
        want_embedded = "embedded" in targets and os.path.splitext(filepath)[1].lower() not in _NO_EMBED_EXTENSIONS
        want_sidecar = "xmp" in targets
        if not (want_embedded or want_sidecar) or not os.path.exists(filepath):
            return results

        basic = metadata.get("basic") if isinstance(metadata.get("basic"), dict) else {}
        ai_info = metadata.get("ai_info") if isinstance(metadata.get("ai_info"), dict) else {}
        typed = ai_info.get("generation") if isinstance(ai_info.get("generation"), dict) else {}
        typed = {k: v for k, v in typed.items() if k != "timestamp" and v not in (None, "")}
        analysis = metadata.get("analysis") if isinstance(metadata.get("analysis"), dict) else None
        keywords = basic.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        user = UserFields(title=str(basic.get("title") or ""), keywords=[str(k) for k in keywords],
                          creator=str(basic.get("creator") or ""), copyright=str(basic.get("rights") or ""),
                          description=str(basic.get("description") or ""), project=str(basic.get("project") or ""))
        rating = basic.get("rating")
        try:
            rating = int(rating) if rating not in (None, "") else None
        except (TypeError, ValueError):
            rating = None

        try:
            existing = reader.read_file(filepath)
            record = GenerationRecord.from_dict(existing["record"]) if existing.get("record") else None
        except Exception:
            record = None
        write_record = None
        if typed:
            record = apply_typed_generation(record, typed)
            write_record = record
            fields = build_standard_fields(record, user, "ComfyUI")
        else:
            # only what was typed; a typed description is placed above the prompt already stored
            fields = StandardFields(title=user.title.strip(), keywords=list(user.keywords), creator=user.creator.strip(),
                                    rights=user.copyright.strip(), digital_source_type="")
            if user.description.strip():
                fields.description = build_standard_fields(record or GenerationRecord(), user).description
            if user.project.strip():
                fields.keywords.append(user.project.strip())
                fields.hierarchical_keywords.append(f"Project|{user.project.strip()}")

        outcome = patch_metadata(filepath, fields, write_record, analysis, rating=rating, project=user.project,
                                 embedded=want_embedded, sidecar=want_sidecar, strip_iim=True, restore=saved)
        self.last_warnings.extend(outcome.get("warnings", []))
        if outcome.get("embedded") is not None:
            results["embedded"] = bool(outcome["embedded"])
        if outcome.get("sidecar") is not None:
            results["xmp"] = bool(outcome["sidecar"])
        return results
