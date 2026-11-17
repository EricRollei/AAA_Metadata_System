"""
measurements.py
Automatic collection of measured data (image quality scores, classifiers...)
for the image being saved - no wiring.

While a workflow runs, the capture hook keeps every node's small outputs. When
the save node runs, this module looks for measuring nodes that worked on the
image being saved and returns their results, grouped per node:

    {"Eric_UniPercept_V1": {"iaa_score": 71.2, "summary": "...", "results": {...}}, ...}

A node counts as a measuring node when
  * it belongs to one of the measuring packs (default: Eric-image-classification;
    more via the environment variable AAA_META_MEASUREMENT_PACKS, comma separated), or
  * it published its results itself with aaa_meta.publish({"measurements": {...}})
and it is connected to the saved image: the image passes through it on its way
to the save node, or it reads its image from a node on that path.

Only results produced in the current run are used. A node that did not run this
time (ComfyUI reused its cached result) is reported, not guessed at.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from .graph import PromptGraph

DEFAULT_PACKS = ("Eric-image-classification",)
_SKIP_TYPES = ("IMAGE", "MASK", "LATENT", "MODEL", "CLIP", "VAE", "CONDITIONING")
_SKIP_NAMES = ("image", "images", "status", "filepath", "file_path", "output_path")
_VALUE_TYPES = (bool, int, float, dict)

ClassInfo = Callable[[str], Optional[Dict[str, Any]]]


def measuring_packs() -> Tuple[str, ...]:
    extra = [p.strip() for p in os.environ.get("AAA_META_MEASUREMENT_PACKS", "").split(",") if p.strip()]
    return tuple(p.lower() for p in (*DEFAULT_PACKS, *extra))


def _in_measuring_pack(info: Optional[Dict[str, Any]]) -> bool:
    if not info:
        return False
    location = f"{info.get('file') or ''}|{info.get('module') or ''}".replace("\\", "/").lower()
    return any(pack in location for pack in measuring_packs())


def _node_values(entry: dict, info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    names = list((info or {}).get("return_names") or [])
    types = list((info or {}).get("return_types") or [])
    values: Dict[str, Any] = {}
    for index, value in sorted((entry.get("outputs") or {}).items(), key=lambda kv: int(kv[0])):
        index = int(index)
        kind = str(types[index]).upper() if index < len(types) else ""
        name = str(names[index]) if index < len(names) and names[index] else f"output_{index}"
        if kind in _SKIP_TYPES or name.lower() in _SKIP_NAMES or value in (None, "", [], {}):
            continue
        values[name] = value
    return values


def collect_measurements(graph: PromptGraph, anchor_id: str, captured: Dict[str, dict], prompt_id: Optional[str],
                         class_info: Optional[ClassInfo] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Returns (measurements grouped per node, notes for the user)."""
    anchor_id = str(anchor_id)
    notes: List[str] = []
    found: Dict[str, Any] = {}
    if not graph.has(anchor_id):
        return found, notes
    upstream = set(graph.ancestors(anchor_id, include_self=False))
    for node_id in sorted(graph.nodes, key=lambda n: (len(str(n)), str(n))):
        node_id = str(node_id)
        if node_id == anchor_id:
            continue
        entry = captured.get(node_id)
        class_type = graph.class_type(node_id)
        info = class_info(class_type) if class_info else None
        published = (entry or {}).get("published", {}).get("measurements") if isinstance(entry, dict) else None
        if not (_in_measuring_pack(info) or isinstance(published, dict)):
            continue
        sources = {source for source, _ in graph.links(node_id).values()}
        if node_id not in upstream and not (sources & upstream):
            continue                                        # works on some other image
        if not isinstance(entry, dict) or (prompt_id is not None and entry.get("prompt_id") != prompt_id):
            notes.append(f"measurements from {class_type} not included: it did not run this time "
                         f"(cached result, or it runs after the save)")
            continue
        values = dict(published) if isinstance(published, dict) else _node_values(entry, info)
        if not any(isinstance(v, _VALUE_TYPES) for v in values.values()):
            continue                                        # sorters and the like: nothing measured
        key, count = class_type or f"node_{node_id}", 2
        while key in found:
            key, count = f"{class_type}_{count}", count + 1
        found[key] = values
    return found, notes
