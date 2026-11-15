"""
verify.py
Reads a written file back with exiftool and reports which fields actually
landed. The save node shows this instead of assuming the write worked.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
from typing import Any, Dict, List, Optional

from .embed import find_exiftool, run_exiftool
from .fields import StandardFields

# report label -> exiftool tag (group1:name)
CHECKS = {
    "description": "XMP-dc:Description",
    "keywords": "XMP-dc:Subject",
    "hierarchical keywords": "XMP-lr:HierarchicalSubject",
    "headline": "XMP-photoshop:Headline",
    "instructions": "XMP-photoshop:Instructions",
    "digital source type": "XMP-iptcExt:DigitalSourceType",
    "generation record": "XMP-hcai:RecordVersion",
    "models": "XMP-hcai:Models",
    "passes": "XMP-hcai:Passes",
}


def read_tags(path: str) -> Optional[Dict[str, Any]]:
    if find_exiftool() is None:
        return None
    code, out, _ = run_exiftool(["-j", "-G1", "-struct", "-a", "-api", "largefilesupport=1", path])
    if code != 0 or not out.strip():
        return None
    try:
        data = json.loads(out.decode("utf-8", errors="replace"))
        return data[0] if data else None
    except Exception:
        return None


def verify_file(path: str, expected: Optional[StandardFields] = None) -> Dict[str, Any]:
    """
    Returns {"ok": bool, "present": [...], "missing": [...], "mismatch": [...], "tags": N}
    'mismatch' lists standard fields whose value differs from what was intended.
    """
    report: Dict[str, Any] = {"ok": False, "present": [], "missing": [], "mismatch": [], "tags": 0}
    tags = read_tags(path)
    if tags is None:
        report["missing"] = ["(could not read the file with exiftool)"]
        return report
    report["tags"] = len(tags)
    for label, tag in CHECKS.items():
        (report["present"] if tags.get(tag) not in (None, "", []) else report["missing"]).append(label)
    if expected is not None:
        got_description = tags.get("XMP-dc:Description")
        if expected.description and str(got_description or "").strip() != expected.description.strip():
            report["mismatch"].append("description")
        got_keywords = tags.get("XMP-dc:Subject")
        got_list: List[str] = [str(k) for k in got_keywords] if isinstance(got_keywords, list) else (
            [str(got_keywords)] if got_keywords not in (None, "") else [])
        if sorted(got_list) != sorted(expected.keywords):
            report["mismatch"].append("keywords")
        if not expected.description and "description" in report["missing"]:
            report["missing"].remove("description")
    report["ok"] = not report["missing"] and not report["mismatch"]
    return report
