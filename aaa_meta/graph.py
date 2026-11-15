"""
graph.py
A thin, read-only view of a ComfyUI prompt graph (API format):
    { node_id: {"class_type": str, "inputs": {name: literal | [src_id, out_index]}} }

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Tuple

Link = Tuple[str, int]


class PromptGraph:
    def __init__(self, nodes: Dict[str, dict]):
        self.nodes: Dict[str, dict] = {
            str(node_id): node for node_id, node in nodes.items()
            if isinstance(node, dict) and "class_type" in node
        }

    # ---- construction -------------------------------------------------
    @classmethod
    def from_prompt(cls, prompt: Dict[str, dict]) -> "PromptGraph":
        return cls(prompt or {})

    @classmethod
    def from_dynprompt(cls, dynprompt: Any, fallback_prompt: Optional[dict] = None) -> "PromptGraph":
        """Build from comfy_execution.graph.DynamicPrompt (includes expanded nodes)."""
        try:
            nodes = {str(node_id): dynprompt.get_node(node_id) for node_id in dynprompt.all_node_ids()}
            if nodes:
                return cls(nodes)
        except Exception:
            pass
        return cls(fallback_prompt or {})

    # ---- basic access -------------------------------------------------
    def has(self, node_id: str) -> bool:
        return str(node_id) in self.nodes

    def class_type(self, node_id: str) -> str:
        return str(self.nodes.get(str(node_id), {}).get("class_type", ""))

    def title(self, node_id: str) -> str:
        meta = self.nodes.get(str(node_id), {}).get("_meta") or {}
        return str(meta.get("title", "")) if isinstance(meta, dict) else ""

    def inputs(self, node_id: str) -> Dict[str, Any]:
        inputs = self.nodes.get(str(node_id), {}).get("inputs")
        return inputs if isinstance(inputs, dict) else {}

    def as_link(self, value: Any) -> Optional[Link]:
        if (isinstance(value, (list, tuple)) and len(value) == 2
                and isinstance(value[0], (str, int)) and not isinstance(value[0], bool)
                and isinstance(value[1], int) and not isinstance(value[1], bool)
                and str(value[0]) in self.nodes):
            return str(value[0]), int(value[1])
        return None

    def link(self, node_id: str, input_name: str) -> Optional[Link]:
        return self.as_link(self.inputs(node_id).get(input_name))

    def links(self, node_id: str) -> Dict[str, Link]:
        found = {}
        for name, value in self.inputs(node_id).items():
            link = self.as_link(value)
            if link is not None:
                found[name] = link
        return found

    def literals(self, node_id: str) -> Dict[str, Any]:
        return {name: value for name, value in self.inputs(node_id).items()
                if self.as_link(value) is None}

    # ---- traversal ----------------------------------------------------
    def ancestors(self, node_id: str, include_self: bool = False) -> Dict[str, int]:
        """All upstream nodes mapped to their shortest link distance from node_id."""
        start = str(node_id)
        depth: Dict[str, int] = {start: 0}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for src, _ in self.links(current).values():
                if src not in depth:
                    depth[src] = depth[current] + 1
                    queue.append(src)
        if not include_self:
            depth.pop(start, None)
        return depth

    def walk_upstream(self, start: Iterable[str], max_depth: int = 6) -> List[Tuple[str, int]]:
        """Breadth-first list of (node_id, depth) starting at the given nodes."""
        order: List[Tuple[str, int]] = []
        seen = set()
        queue = deque((str(node_id), 0) for node_id in start)
        while queue:
            current, level = queue.popleft()
            if current in seen or current not in self.nodes:
                continue
            seen.add(current)
            order.append((current, level))
            if level >= max_depth:
                continue
            for src, _ in self.links(current).values():
                if src not in seen:
                    queue.append((src, level + 1))
        return order
