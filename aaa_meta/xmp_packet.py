"""
xmp_packet.py
Builds the XMP packet. One builder for every file format and for sidecars, so
the embedded copy and a sidecar can never disagree.

Namespaces written:
    dc, xmp, photoshop, xmpRights, lr, Iptc4xmpExt   standard fields
    hcai   http://historic.camera/ns/ai/2.0/          generation record
    eiqa   http://historic.camera/ns/eiqa/2.0/        measured data (analysis)

Structured values are real XMP structures (rdf:parseType="Resource", rdf:Seq),
never stringified Python.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import datetime
import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional

from .fields import StandardFields
from .record import GenerationRecord

NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "photoshop": "http://ns.adobe.com/photoshop/1.0/",
    "xmpRights": "http://ns.adobe.com/xap/1.0/rights/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
    "Iptc4xmpExt": "http://iptc.org/std/Iptc4xmpExt/2008-02-29/",
    "hcai": "http://historic.camera/ns/ai/2.0/",
    "eiqa": "http://historic.camera/ns/eiqa/2.0/",
}
# Namespaces written by the pre-2026 system; read for compatibility only.
LEGACY_NS = {
    "ai": "http://ericproject.org/schemas/ai/1.0/",
    "eiqa": "http://ericproject.org/schemas/eiqa/1.0/",
}
RECORD_VERSION = "2.0"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)

_INVALID_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_NAME_BAD = re.compile(r"[^A-Za-z0-9_.-]")


def q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def clean_text(value: Any) -> str:
    """Text safe for XML 1.0 (control characters removed)."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return _INVALID_XML.sub("", str(value))


def safe_name(key: Any) -> str:
    """Turn any dict key into a valid XML element name."""
    name = _NAME_BAD.sub("_", str(key).strip()) or "item"
    if not (name[0].isalpha() or name[0] == "_"):
        name = "_" + name
    return name


# ---------------------------------------------------------------------------
# element helpers
# ---------------------------------------------------------------------------
def _simple(parent: ET.Element, prefix: str, name: str, value: Any) -> None:
    if value is None or value == "":
        return
    ET.SubElement(parent, q(prefix, name)).text = clean_text(value)


def _lang_alt(parent: ET.Element, prefix: str, name: str, value: str) -> None:
    if not value:
        return
    alt = ET.SubElement(ET.SubElement(parent, q(prefix, name)), q("rdf", "Alt"))
    item = ET.SubElement(alt, q("rdf", "li"))
    item.set(XML_LANG, "x-default")
    item.text = clean_text(value)


def _array(parent: ET.Element, prefix: str, name: str, values: Iterable[Any], kind: str) -> None:
    values = [v for v in values if v not in (None, "")]
    if not values:
        return
    container = ET.SubElement(ET.SubElement(parent, q(prefix, name)), q("rdf", kind))
    for value in values:
        ET.SubElement(container, q("rdf", "li")).text = clean_text(value)


def add_value(parent: ET.Element, prefix: str, name: str, value: Any) -> None:
    """Generic: dict -> structure, list -> ordered array, scalar -> text. None/empty skipped."""
    if value is None or value == "" or value == {} or value == []:
        return
    element = ET.SubElement(parent, q(prefix, safe_name(name)))
    _fill(element, prefix, value)


def _fill(element: ET.Element, prefix: str, value: Any) -> None:
    if isinstance(value, dict):
        element.set(q("rdf", "parseType"), "Resource")
        for key, item in value.items():
            add_value(element, prefix, key, item)
    elif isinstance(value, (list, tuple)):
        sequence = ET.SubElement(element, q("rdf", "Seq"))
        for item in value:
            if item is None:
                continue
            _fill(ET.SubElement(sequence, q("rdf", "li")), prefix, item)
    else:
        element.text = clean_text(value)


# ---------------------------------------------------------------------------
# generation record -> hcai
# ---------------------------------------------------------------------------
def record_for_embedding(record: GenerationRecord, include_paths: bool = False) -> Dict[str, Any]:
    """The record as a plain dict, with local disk paths removed unless asked for."""
    data = record.to_dict()
    data.pop("anchor_node", None)
    for model in data.get("models", []):
        if not include_paths:
            model.pop("path", None)
        model.pop("node_id", None)
        if not model.get("extra_strengths"):
            model.pop("extra_strengths", None)
    for sampling in data.get("passes", []):
        sampling.pop("node_id", None)
        if not sampling.get("extras"):
            sampling.pop("extras", None)
    for item in data.get("model_chain", []):
        item.pop("node_id", None)
    return data


def _pascal(key: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in str(key).split("_") if part)


def _pascal_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {_pascal(k): _pascal_keys(v) for k, v in value.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [_pascal_keys(v) for v in value]
    return value


def _add_generation(desc: ET.Element, record: GenerationRecord, include_paths: bool,
                    include_record_json: bool, omit_prompt_copy: bool = False) -> None:
    data = record_for_embedding(record, include_paths)
    _simple(desc, "hcai", "RecordVersion", RECORD_VERSION)
    if not omit_prompt_copy:              # dc:description already carries it
        _simple(desc, "hcai", "Prompt", record.positive)
    _simple(desc, "hcai", "NegativePrompt", record.negative)
    _simple(desc, "hcai", "SourcePrompt", record.positive_source)
    _simple(desc, "hcai", "PromptRewriter", record.prompt_rewriter)
    _simple(desc, "hcai", "Seed", record.seed)
    _simple(desc, "hcai", "Width", record.width)
    _simple(desc, "hcai", "Height", record.height)
    _simple(desc, "hcai", "CaptureMode", record.capture_mode)
    _simple(desc, "hcai", "ComfyUIVersion", record.comfyui_version)
    _simple(desc, "hcai", "Created", record.created)
    models = []
    for model in data.get("models", []):
        item = _pascal_keys(model)
        sha = model.get("sha256")
        if sha:
            item["AutoV2"] = sha[:10]
        models.append(item)
    add_value(desc, "hcai", "Models", models)
    add_value(desc, "hcai", "Passes", [_pascal_keys(p) for p in data.get("passes", [])])
    add_value(desc, "hcai", "ModelChain", [_pascal_keys(p) for p in data.get("model_chain", [])])
    if record.warnings:
        _array(desc, "hcai", "Warnings", record.warnings, "Bag")
    if include_record_json:
        _simple(desc, "hcai", "RecordJSON", json.dumps(data, ensure_ascii=False, separators=(",", ":")))


# ---------------------------------------------------------------------------
# packet
# ---------------------------------------------------------------------------
def _serialize(root: ET.Element) -> bytes:
    ET.indent(root, space=" ")
    body = ET.tostring(root, encoding="unicode")
    packet = ('<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
              + body + '\n<?xpacket end="w"?>')
    return packet.encode("utf-8")


def build_packet(fields: Optional[StandardFields] = None, record: Optional[GenerationRecord] = None,
                 analysis: Optional[Dict[str, Any]] = None, include_paths: bool = False,
                 include_record_json: bool = True, omit_prompt_copy: bool = False,
                 project: str = "", custom: Optional[Dict[str, Any]] = None,
                 rating: Optional[int] = None) -> bytes:
    """
    fields    standard catalog fields (from fields.build_standard_fields)
    record    generation record -> hcai namespace
    analysis  measured data, {analysis_name: value or nested dict} -> eiqa namespace
    include_record_json / omit_prompt_copy   size reductions for JPEG, whose
              metadata block is limited to about 64 KB
    """
    root = ET.Element(q("x", "xmpmeta"))
    rdf = ET.SubElement(root, q("rdf", "RDF"))
    desc = ET.SubElement(rdf, q("rdf", "Description"))
    desc.set(q("rdf", "about"), "")

    if fields is not None:
        _lang_alt(desc, "dc", "title", fields.title)
        _lang_alt(desc, "dc", "description", fields.description)
        _array(desc, "dc", "subject", fields.keywords, "Bag")
        _array(desc, "lr", "hierarchicalSubject", fields.hierarchical_keywords, "Bag")
        if fields.creator:
            _array(desc, "dc", "creator", [fields.creator], "Seq")
        if fields.rights:
            _lang_alt(desc, "dc", "rights", fields.rights)
            _simple(desc, "xmpRights", "Marked", "True")
        _simple(desc, "photoshop", "Headline", fields.headline)
        _simple(desc, "photoshop", "Instructions", fields.instructions)
        _simple(desc, "xmp", "CreatorTool", fields.creator_tool)
        _simple(desc, "xmp", "CreateDate", fields.create_date)
        _simple(desc, "xmp", "MetadataDate",
                datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
        _simple(desc, "Iptc4xmpExt", "DigitalSourceType", fields.digital_source_type)

    if record is not None:
        _add_generation(desc, record, include_paths, include_record_json, omit_prompt_copy)

    if rating is not None:
        _simple(desc, "xmp", "Rating", int(rating))
    _simple(desc, "hcai", "Project", project)
    if custom:
        add_value(desc, "hcai", "Custom", custom)

    if analysis:
        for name, value in analysis.items():
            add_value(desc, "eiqa", name, value)
        _simple(desc, "eiqa", "AnalysisJSON", json.dumps(analysis, ensure_ascii=False, separators=(",", ":"), default=str))

    return _serialize(root)


# ---------------------------------------------------------------------------
# merge (updating a file that already has XMP)
# ---------------------------------------------------------------------------
UNION_PROPERTIES = (q("dc", "subject"), q("lr", "hierarchicalSubject"))


def _strip_packet_wrapper(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    start = text.find("<x:xmpmeta")
    if start < 0:
        start = text.find("<rdf:RDF")
    end = max(text.rfind("</x:xmpmeta>") + len("</x:xmpmeta>") if "</x:xmpmeta>" in text else -1,
              text.rfind("</rdf:RDF>") + len("</rdf:RDF>") if "</rdf:RDF>" in text else -1)
    return text[start:end] if start >= 0 and end > start else ""


def _descriptions(root: ET.Element) -> List[ET.Element]:
    return list(root.iter(q("rdf", "Description")))


def _array_items(prop: ET.Element) -> List[str]:
    return [li.text or "" for li in prop.iter(q("rdf", "li"))]


def merge_packets(existing: Optional[bytes], new: bytes) -> bytes:
    """
    Put the properties of `new` into `existing`. A property present in `new`
    replaces the same property in `existing`; keyword lists are unioned;
    everything else already in the file is kept.
    """
    existing_body = _strip_packet_wrapper(existing) if existing else ""
    if not existing_body:
        return new
    try:
        old_root = ET.fromstring(existing_body)
    except ET.ParseError:
        return new
    new_root = ET.fromstring(_strip_packet_wrapper(new))
    new_props = [child for d in _descriptions(new_root) for child in list(d)]
    old_descs = _descriptions(old_root)
    if not old_descs:
        return new
    for prop in new_props:
        if prop.tag in UNION_PROPERTIES:
            merged: List[str] = []
            for d in old_descs:
                for old in d.findall(prop.tag):
                    merged.extend(_array_items(old))
            for value in _array_items(prop):
                if value not in merged:
                    merged.append(value)
            container = next(iter(prop), None)
            if container is not None:
                for li in list(container):
                    container.remove(li)
                for value in merged:
                    ET.SubElement(container, q("rdf", "li")).text = value
        for d in old_descs:
            for old in d.findall(prop.tag):
                d.remove(old)
            if prop.tag in d.attrib:          # property written in attribute shorthand
                del d.attrib[prop.tag]
    target = old_descs[0]
    for prop in new_props:
        target.append(prop)
    if old_root.tag != q("x", "xmpmeta"):
        wrapper = ET.Element(q("x", "xmpmeta"))
        wrapper.append(old_root)
        old_root = wrapper
    return _serialize(old_root)


# ---------------------------------------------------------------------------
# reading our own data back
# ---------------------------------------------------------------------------
def read_record_json(packet: bytes) -> Optional[Dict[str, Any]]:
    body = _strip_packet_wrapper(packet)
    if not body:
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    for element in root.iter(q("hcai", "RecordJSON")):
        try:
            return json.loads(element.text or "")
        except Exception:
            return None
    for d in _descriptions(root):
        raw = d.attrib.get(q("hcai", "RecordJSON"))
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
    return None


def read_analysis_json(packet: Optional[bytes]) -> Dict[str, Any]:
    """The measured data (eiqa) already in a packet, as written by build_packet. {} when none."""
    body = _strip_packet_wrapper(packet) if packet else ""
    if not body:
        return {}
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {}
    raw = None
    for element in root.iter(q("eiqa", "AnalysisJSON")):
        raw = element.text
        break
    if raw is None:
        for d in _descriptions(root):
            raw = d.attrib.get(q("eiqa", "AnalysisJSON")) or raw
    try:
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
