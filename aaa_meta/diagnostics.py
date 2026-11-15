"""
diagnostics.py
A plain-text dump of what the runtime capture holds for every node upstream of
an anchor node, and whether each captured entry is trusted. For debugging the
capture itself: paste this when a record is missing something.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from typing import Any, Dict, Optional

from .graph import PromptGraph
from .resolve import Resolver


def _brief(value: Any) -> str:
    if isinstance(value, str):
        flat = value.replace("\n", " ")
        return f"str[{len(value)}] '{flat[:48]}{'...' if len(flat) > 48 else ''}'"
    if isinstance(value, bool) or value is None:
        return repr(value)
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return f"list[{len(value)}] " + (_brief(value[0]) if value else "")
    if isinstance(value, dict):
        return f"dict{{{', '.join(list(value)[:6])}}}"
    return type(value).__name__


def capture_dump(graph: PromptGraph, anchor_id: str, captured: Optional[Dict[str, dict]],
                 prompt_id: Optional[str]) -> str:
    captured = captured or {}
    resolver = Resolver(graph, captured, prompt_id)
    lines = [f"anchor {anchor_id}  current prompt_id {prompt_id}  captured entries {len(captured)}"]
    ancestors = graph.ancestors(str(anchor_id))
    for node_id, depth in sorted(ancestors.items(), key=lambda item: item[1]):
        raw = captured.get(node_id)
        if raw is None:
            status = "NO ENTRY"
        elif resolver.entry(node_id) is None:
            status = "REJECTED (stale)"
        elif raw.get("prompt_id") == prompt_id:
            status = "this run"
        else:
            status = "earlier run, accepted"
        lines.append(f"[{node_id}] {graph.class_type(node_id)}  depth {depth}  capture: {status}")
        links = graph.links(node_id)
        for name, value in graph.inputs(node_id).items():
            source = f"link {links[name][0]}.{links[name][1]}" if name in links else "literal " + _brief(value)
            got = "-"
            if raw is not None and name in raw.get("inputs", {}):
                got = _brief(raw["inputs"][name])
            lines.append(f"    in  {name}: graph {source} | captured {got}")
        if raw is not None:
            extra = [k for k in raw.get("inputs", {}) if k not in graph.inputs(node_id)]
            if extra:
                lines.append(f"    captured-only inputs: {', '.join(extra[:12])}")
            for index, value in raw.get("outputs", {}).items():
                lines.append(f"    out {index}: {_brief(value)}")
            for item in raw.get("files", []):
                lines.append(f"    file {item.get('category')}: {item.get('name')}")
            if raw.get("class_name"):
                lines.append(f"    python class {raw.get('class_name')}  entry prompt_id {raw.get('prompt_id')}")
    return "\n".join(lines)
