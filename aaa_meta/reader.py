"""
reader.py
Reads what the v2 writer put into a file (or its .xmp sidecar) back into plain
Python data, and also understands the namespaces the pre-2026 system wrote.

    read_file(path) -> {
        "source":   "embedded" | "sidecar" | None,
        "standard": {title, description, keywords, hierarchical_keywords, creator, rights,
                     headline, instructions, rating, creator_tool, digital_source_type},
        "record":   generation record as a dict (None when the file has none),
        "generation": the hcai fields as stored (structured),
        "analysis": measured data (eiqa),
        "project":  str, "custom": dict,
        "legacy":   {"ai": {...}, "eiqa": {...}}   data in the old ericproject.org namespaces
    }

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from . import embed
from .xmp_packet import LEGACY_NS, NS, XML_LANG, _strip_packet_wrapper, q

_RDF = "{%s}" % NS["rdf"]
_STANDARD = {
    q("dc", "title"): "title", q("dc", "description"): "description", q("dc", "subject"): "keywords",
    q("lr", "hierarchicalSubject"): "hierarchical_keywords", q("dc", "creator"): "creator",
    q("dc", "rights"): "rights", q("photoshop", "Headline"): "headline",
    q("photoshop", "Instructions"): "instructions", q("xmp", "Rating"): "rating",
    q("xmp", "CreatorTool"): "creator_tool", q("Iptc4xmpExt", "DigitalSourceType"): "digital_source_type",
}
_LIST_FIELDS = ("keywords", "hierarchical_keywords")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _namespace(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def _scalar(text: Optional[str]) -> Any:
    """Text as stored -> number / bool when it clearly is one."""
    if text is None:
        return ""
    value = text.strip()
    if value in ("True", "False"):
        return value == "True"
    try:
        if value and (value.lstrip("-").isdigit()):
            return int(value)
        if value and any(c.isdigit() for c in value) and all(c in "0123456789.-+eE" for c in value):
            return float(value)
    except ValueError:
        pass
    return text


def element_value(element: ET.Element, coerce: bool = True) -> Any:
    """An XMP property -> text, list or dict."""
    children = list(element)
    if not children:
        attributes = {_local(k): (_scalar(v) if coerce else v) for k, v in element.attrib.items()
                      if not k.startswith(_RDF) and k != XML_LANG}
        if attributes and not (element.text or "").strip():
            return attributes
        return _scalar(element.text) if coerce else (element.text or "")
    first = children[0]
    if first.tag == _RDF + "Alt":
        items = list(first)
        chosen = next((i for i in items if i.get(XML_LANG) == "x-default"), items[0] if items else None)
        return (chosen.text or "") if chosen is not None else ""
    if first.tag in (_RDF + "Bag", _RDF + "Seq"):
        return [element_value(item, coerce) for item in first]
    if first.tag == _RDF + "Description":
        return {_local(c.tag): element_value(c, coerce) for c in first}
    return {_local(c.tag): element_value(c, coerce) for c in children}


def parse_packet(packet: Optional[bytes]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"standard": {}, "record": None, "generation": {}, "analysis": {}, "project": "",
                           "custom": {}, "legacy": {"ai": {}, "eiqa": {}}}
    body = _strip_packet_wrapper(packet) if packet else ""
    if not body:
        return out
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return out
    structured_analysis: Dict[str, Any] = {}
    analysis_json = None
    containers = [root] if root.tag == _RDF + "RDF" else list(root.iter(_RDF + "RDF"))
    top_level = [child for rdf in containers for child in rdf if child.tag == _RDF + "Description"]
    for description in top_level:
        properties = [(child.tag, child) for child in description]
        properties += [(key, value) for key, value in description.attrib.items() if not key.startswith(_RDF)]
        for tag, item in properties:
            namespace, name = _namespace(tag), _local(tag)
            is_element = isinstance(item, ET.Element)
            if tag in _STANDARD:
                value = element_value(item, coerce=False) if is_element else item
                key = _STANDARD[tag]
                if key in _LIST_FIELDS:
                    value = [str(v) for v in value] if isinstance(value, list) else [str(value)]
                elif isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                if key == "rating":
                    try:
                        value = int(float(value))
                    except (TypeError, ValueError):
                        continue
                out["standard"][key] = value
            elif namespace == NS["hcai"]:
                if name == "RecordJSON":
                    try:
                        out["record"] = json.loads(item.text if is_element else item)
                    except Exception:
                        pass
                elif name == "Project":
                    out["project"] = (item.text if is_element else item) or ""
                elif name == "Custom":
                    value = element_value(item) if is_element else item
                    out["custom"] = value if isinstance(value, dict) else {"value": value}
                else:
                    keep_text = name in ("Prompt", "NegativePrompt", "SourcePrompt")
                    out["generation"][name] = element_value(item, coerce=not keep_text) if is_element else item
            elif namespace == NS["eiqa"]:
                if name == "AnalysisJSON":
                    analysis_json = item.text if is_element else item
                else:
                    structured_analysis[name] = element_value(item) if is_element else _scalar(item)
            elif namespace == LEGACY_NS["ai"]:
                out["legacy"]["ai"][name] = element_value(item) if is_element else _scalar(item)
            elif namespace == LEGACY_NS["eiqa"]:
                out["legacy"]["eiqa"][name] = element_value(item) if is_element else _scalar(item)
    if analysis_json:
        try:
            parsed = json.loads(analysis_json)
            if isinstance(parsed, dict):
                out["analysis"] = parsed
        except Exception:
            pass
    for name, value in structured_analysis.items():        # anything not covered by the JSON copy
        out["analysis"].setdefault(name, value)
    return out


def _has_data(parsed: Dict[str, Any]) -> bool:
    return bool(parsed["standard"] or parsed["record"] or parsed["generation"] or parsed["analysis"]
                or parsed["legacy"]["ai"] or parsed["legacy"]["eiqa"])


def read_file(path: str, prefer: str = "embedded") -> Dict[str, Any]:
    """prefer: "embedded" (fall back to the sidecar) or "sidecar" (fall back to the file)."""
    order = ["embedded", "sidecar"] if prefer != "sidecar" else ["sidecar", "embedded"]
    for source in order:
        packet = embed.read_xmp(path) if source == "embedded" else embed.read_sidecar(path)
        parsed = parse_packet(packet)
        if _has_data(parsed):
            parsed["source"] = source
            return parsed
    empty = parse_packet(None)
    empty["source"] = None
    return empty


def generation_summary(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Flat, friendly view of the generation data: prompt, model, loras, sampler, seed..."""
    record = parsed.get("record") or {}
    generation = parsed.get("generation") or {}
    models: List[Dict[str, Any]] = record.get("models") or []
    passes: List[Dict[str, Any]] = record.get("passes") or []
    base = next((m for m in models if m.get("role") in ("checkpoint", "unet", "diffusion_model")), None)
    first = passes[0] if passes else {}

    def stem(model: Dict[str, Any]) -> str:
        name = str(model.get("name") or "").replace("\\", "/").rsplit("/", 1)[-1]
        return name.rsplit(".", 1)[0] if "." in name else name

    flat = {
        "prompt": record.get("positive") or generation.get("Prompt") or record.get("positive_source")
                  or generation.get("SourcePrompt"),
        "negative_prompt": record.get("negative") or generation.get("NegativePrompt"),
        "source_prompt": record.get("positive_source") or generation.get("SourcePrompt"),
        "model": stem(base) if base else None,
        "model_hash": (base.get("sha256") or "")[:10] if base else None,
        "loras": [{"name": stem(m), "strength": m.get("strength_model")} for m in models if m.get("role") == "lora"],
        "sampler": first.get("sampler"), "scheduler": first.get("scheduler"), "steps": first.get("steps"),
        "cfg_scale": first.get("cfg"), "seed": first.get("seed") if first.get("seed") is not None else generation.get("Seed"),
        "denoise": first.get("denoise"),
        "width": record.get("width") or generation.get("Width"), "height": record.get("height") or generation.get("Height"),
        "capture_mode": record.get("capture_mode") or generation.get("CaptureMode"),
    }
    return {k: v for k, v in flat.items() if v not in (None, "", [])}
