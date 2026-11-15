"""
resolve.py
Answers "what value did this input actually have?".

Order of trust:
  1. values a node published explicitly (aaa_meta.publish)
  2. values captured at runtime by the execution hook
  3. the literal in the prompt graph
  4. for links without runtime data: a small static follow-through of
     pass-through style nodes (primitives, seed nodes, switches)

Captured entries are keyed by node id only, so an entry may belong to another
workflow or an older edit of this one. An entry is trusted when it comes from
the current prompt, or when every literal the graph holds for that node equals
what was captured (ComfyUI only reuses a cached node if its inputs are unchanged).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from typing import Any, Dict, Optional

from .graph import PromptGraph

# Input names that carry "the value" on primitive / pass-through nodes.
_PASSTHROUGH_KEYS = (
    "value", "seed", "noise_seed", "text", "string", "prompt", "Number", "number",
    "int", "float", "INT", "FLOAT", "STRING", "val", "input", "any", "anything",
)


def as_number(value: Any) -> Optional[float]:
    """int/float as-is, numeric strings converted, everything else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text or len(text) > 40:
            return None
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return None
    return None


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= 1e-9 * max(1.0, abs(float(left)), abs(float(right)))
    return left == right


class Resolver:
    def __init__(self, graph: PromptGraph, captured: Optional[Dict[str, dict]] = None,
                 prompt_id: Optional[str] = None):
        self.graph = graph
        self.captured = captured or {}
        self.prompt_id = prompt_id
        self._valid_cache: Dict[str, Optional[dict]] = {}
        self.used_runtime = False
        self.used_static_links = False
        self.static_passthrough = set()     # class types read through without runtime data

    # ---- captured entries ----------------------------------------------
    def entry(self, node_id: str) -> Optional[dict]:
        node_id = str(node_id)
        if node_id in self._valid_cache:
            return self._valid_cache[node_id]
        entry = self.captured.get(node_id)
        valid: Optional[dict] = None
        if isinstance(entry, dict) and self.graph.has(node_id):
            if self.prompt_id is not None and entry.get("prompt_id") == self.prompt_id:
                valid = entry
            else:
                captured_inputs = entry.get("inputs", {})
                literals = self.graph.literals(node_id)
                comparable = [(name, value) for name, value in literals.items()
                              if isinstance(value, (str, int, float, bool)) and name in captured_inputs]
                if comparable and all(_equal(value, captured_inputs[name]) for name, value in comparable):
                    valid = entry
                elif not literals and (captured_inputs or entry.get("outputs")):
                    valid = entry
        self._valid_cache[node_id] = valid
        return valid

    def files(self, node_id: str) -> list:
        entry = self.entry(node_id)
        return list(entry.get("files", [])) if entry else []

    def published(self, node_id: str) -> dict:
        entry = self.captured.get(str(node_id))
        if isinstance(entry, dict) and (self.prompt_id is None or entry.get("prompt_id") == self.prompt_id):
            return dict(entry.get("published", {}))
        return {}

    # ---- values -------------------------------------------------------
    def input_value(self, node_id: str, name: str, _depth: int = 0) -> Any:
        node_id = str(node_id)
        entry = self.entry(node_id)
        if entry is not None and name in entry.get("inputs", {}):
            self.used_runtime = True
            return entry["inputs"][name]
        raw = self.graph.inputs(node_id).get(name)
        link = self.graph.as_link(raw)
        if link is None:
            return raw
        return self.output_value(link[0], link[1], _depth + 1)

    def output_value(self, node_id: str, index: int, _depth: int = 0) -> Any:
        node_id = str(node_id)
        entry = self.entry(node_id)
        if entry is not None:
            outputs = entry.get("outputs", {})
            if index in outputs:
                self.used_runtime = True
                return outputs[index]
            if str(index) in outputs:
                self.used_runtime = True
                return outputs[str(index)]
        if _depth > 6:
            return None
        # Static follow-through for primitive-like nodes.
        inputs = self.graph.inputs(node_id)
        for key in _PASSTHROUGH_KEYS:
            if key in inputs:
                value = self.input_value(node_id, key, _depth + 1)
                if isinstance(value, (str, int, float, bool)):
                    self.used_static_links = True
                    # A text read through a node that has other inputs too may have
                    # been rewritten by that node (LLM expanders, wildcard processors).
                    if isinstance(value, str) and len(inputs) > 1:
                        self.static_passthrough.add(self.graph.class_type(node_id))
                    return value
        scalars = [name for name, value in inputs.items()
                   if isinstance(value, (str, int, float)) and not isinstance(value, bool)]
        if len(inputs) == 1 and len(scalars) == 1:
            self.used_static_links = True
            return inputs[scalars[0]]
        return None

    def number(self, node_id: str, name: str) -> Optional[float]:
        return as_number(self.input_value(node_id, name))

    def text(self, node_id: str, name: str) -> Optional[str]:
        value = self.input_value(node_id, name)
        return value if isinstance(value, str) else None
