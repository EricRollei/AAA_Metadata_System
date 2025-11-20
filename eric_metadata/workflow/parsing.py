"""Workflow parsing, prompt extraction, and traversal helpers.

This module provides a thin, well-documented façade around the sprawling
ad-hoc helpers that used to live in ``eric_metadata.utils.workflow_parser``.
It exposes focused entry points for prompt parsing, asset discovery, and graph
traversal so upcoming features (LoRA detection, BFS prioritisation, runtime
hooks) can plug into a stable API.
"""

from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


FLOAT_PATTERN = r"(?:\d*\.\d+|\d+|\.\d+)"
LORA_STRICT = re.compile(
    rf"<lora:\s*([^:>]+?)\s*:\s*({FLOAT_PATTERN})\s*(?::\s*({FLOAT_PATTERN})\s*)?>",
    re.IGNORECASE,
)
LORA_LEGACY = re.compile(r"<lora:\s*([^>]+?)\s*>", re.IGNORECASE)
EMBEDDING_TAG = re.compile(r"<embedding:\s*([^>]+?)\s*>", re.IGNORECASE)


RawWorkflow = Dict[str, Any]
NodeDict = Dict[str, Any]
Link = Any


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """Return a mapping representation for ``candidate`` if possible."""
    if isinstance(candidate, dict):
        return {str(key): value for key, value in candidate.items()}
    if isinstance(candidate, list):
        mapping: Dict[str, Any] = {}
        for entry in candidate:
            if isinstance(entry, dict):
                node_id = entry.get("id")
                if node_id is None:
                    continue
                mapping[str(node_id)] = entry
        return mapping
    return {}


def _normalise_links(raw_links: Any) -> List[Link]:
    if isinstance(raw_links, list):
        return raw_links
    return []


def _normalise_asset_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return re.sub(r"\s+", " ", name).strip()


def _normalise_asset_key(name: str) -> str:
    return _normalise_asset_name(name).lower()


@dataclass
class WorkflowGraph:
    """Normalised view of a ComfyUI workflow graph."""

    nodes: Dict[str, NodeDict]
    links: List[Link]
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    reverse_adjacency: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_workflow(cls, workflow: RawWorkflow) -> "WorkflowGraph":
        prompt_section = workflow.get("prompt") if isinstance(workflow, dict) else {}

        if isinstance(prompt_section, dict) and prompt_section:
            nodes = _coerce_mapping(prompt_section.get("nodes"))
            links = _normalise_links(
                prompt_section.get("links") or prompt_section.get("connections")
            )
        else:
            nodes = _coerce_mapping(workflow.get("nodes"))
            links = _normalise_links(workflow.get("links") or workflow.get("connections"))

        graph = cls(nodes=nodes, links=links)
        graph._build_adjacency()
        return graph

    def _build_adjacency(self) -> None:
        """Populate adjacency tables from ``self.links``."""

        adj: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}
        rev: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}

        for link in self.links:
            from_node: Optional[str] = None
            to_node: Optional[str] = None

            if isinstance(link, list):
                if len(link) >= 5:
                    from_node, to_node = str(link[1]), str(link[3])
                elif len(link) >= 4:
                    from_node, to_node = str(link[0]), str(link[2])
            elif isinstance(link, dict):  # some toolchains use dict links
                from_node = str(link.get("from", "")) or None
                to_node = str(link.get("to", "")) or None

            if not from_node or not to_node:
                continue

            if from_node not in adj:
                adj[from_node] = []
                rev[from_node] = []
            if to_node not in adj:
                adj[to_node] = []
                rev[to_node] = []

            adj[from_node].append(to_node)
            rev[to_node].append(from_node)

        self.adjacency = adj
        self.reverse_adjacency = rev

    def parents(self, node_id: str) -> List[str]:
        return self.reverse_adjacency.get(node_id, [])

    def children(self, node_id: str) -> List[str]:
        return self.adjacency.get(node_id, [])

    def bfs(self, start_node: str, *, direction: str = "backward", max_depth: Optional[int] = None) -> Dict[str, int]:
        """Perform a breadth-first search returning distances.

        Args:
            start_node: Anchor node for traversal.
            direction: ``"backward"`` (default) walks inputs, ``"forward"`` walks outputs.
            max_depth: Optional depth cap (inclusive).

        Returns:
            Mapping of node ID to distance (0 for ``start_node``).
        """

        if start_node not in self.nodes:
            logger.debug("WorkflowGraph.bfs: start node %s not found", start_node)
            return {}

        adjacency = self.reverse_adjacency if direction == "backward" else self.adjacency

        visited: Dict[str, int] = {start_node: 0}
        queue: Deque[str] = deque([start_node])

        while queue:
            current = queue.popleft()
            current_distance = visited[current]
            if max_depth is not None and current_distance >= max_depth:
                continue

            for neighbour in adjacency.get(current, []):
                if neighbour in visited:
                    continue
                visited[neighbour] = current_distance + 1
                queue.append(neighbour)

        return visited


@dataclass
class PromptText:
    node_id: str
    text: str
    is_negative: bool = False
    source: str = "node"
    distance: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "node_id": self.node_id,
            "text": self.text,
            "is_negative": self.is_negative,
            "source": self.source,
        }
        if self.distance is not None:
            payload["distance"] = self.distance
        return payload


@dataclass
class PromptParseResult:
    positive: List[PromptText] = field(default_factory=list)
    negative: List[PromptText] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "positive": [entry.to_dict() for entry in self.positive],
            "negative": [entry.to_dict() for entry in self.negative],
        }


@dataclass
class AssetRecord:
    name: str
    node_id: str
    source: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {"name": self.name, "node_id": self.node_id, "source": self.source}
        if self.extra:
            payload["extra"] = self.extra
        return payload


@dataclass
class AssetDiscovery:
    loras: List[AssetRecord] = field(default_factory=list)
    embeddings: List[AssetRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "loras": [record.to_dict() for record in self.loras],
            "embeddings": [record.to_dict() for record in self.embeddings],
        }


@dataclass
class SamplerCandidate:
    node_id: str
    class_type: str
    distance: int
    priority: int
    inputs: Dict[str, Any]
    reason: str


@dataclass
class PromptNodeRef:
    node_id: str
    class_type: str
    distance: int
    is_negative: bool
    texts: Dict[str, str]
    sources: Dict[str, str] = field(default_factory=dict)


class WorkflowParsingService:
    """High level service orchestrating workflow parsing tasks."""

    def __init__(self, *, debug: bool = False) -> None:
        self.debug = debug

    def parse_prompts(self, workflow: RawWorkflow, *, anchor_node: Optional[str] = None) -> PromptParseResult:
        graph = WorkflowGraph.from_workflow(workflow)
        distances: Dict[str, int] = {}
        if anchor_node:
            distances = graph.bfs(anchor_node, direction="backward")

        result = PromptParseResult()

        for node_id, node in graph.nodes.items():
            class_type = str(node.get("class_type") or node.get("type") or "")
            if not class_type:
                continue
            inputs = _coerce_mapping(node.get("inputs"))
            text_value = inputs.get("text") if inputs else None

            if text_value is None:
                # Some nodes use "prompt" or other keys
                for alt_key in ("prompt", "string", "value"):
                    if alt_key in inputs:
                        text_value = inputs[alt_key]
                        break

            if not isinstance(text_value, str):
                continue

            is_negative = self._infer_negative_flag(class_type, inputs)
            payload = PromptText(
                node_id=node_id,
                text=text_value,
                is_negative=is_negative,
                source=class_type,
                distance=distances.get(node_id),
            )

            if is_negative:
                result.negative.append(payload)
            else:
                result.positive.append(payload)

        return result

    def discover_assets(self, workflow: RawWorkflow) -> AssetDiscovery:
        graph = WorkflowGraph.from_workflow(workflow)
        discovery = AssetDiscovery()

        for node_id, node in graph.nodes.items():
            class_type = str(node.get("class_type") or node.get("type") or "")
            lowered = class_type.lower()
            inputs = _coerce_mapping(node.get("inputs"))

            if "multi" in lowered and "lora" in lowered:
                discovery.loras.extend(
                    self._extract_multi_lora_assets(node_id, class_type, inputs)
                )
                continue

            if "lora" in lowered:
                name = (
                    inputs.get("lora_name")
                    or inputs.get("name")
                    or inputs.get("lora")
                )
                if isinstance(name, str) and name and name.lower() != "none":
                    extra: Dict[str, Any] = {}
                    for key in ("strength", "strength_model", "strength_clip"):
                        coerced = _as_float(inputs.get(key))
                        if coerced is not None:
                            extra[key] = coerced
                    record = AssetRecord(
                        name=name,
                        node_id=node_id,
                        source="loader",
                        extra=extra,
                    )
                    discovery.loras.append(record)
                continue

            if lowered.startswith("embedding") or "embed" in lowered:
                name = inputs.get("embedding") or inputs.get("name") or inputs.get("text")
                if isinstance(name, str) and name:
                    discovery.embeddings.append(
                        AssetRecord(name=name, node_id=node_id, source="loader")
                    )

        prompt_parse = self.parse_prompts(workflow)
        for prompt_entry in prompt_parse.positive + prompt_parse.negative:
            self._extract_inline_assets(prompt_entry, discovery)

        return discovery

    def trace_from_node(
        self,
        workflow: RawWorkflow,
        node_id: str,
        *,
        max_depth: Optional[int] = None,
        direction: str = "backward",
    ) -> Dict[str, Dict[str, Any]]:
        graph = WorkflowGraph.from_workflow(workflow)
        if node_id not in graph.nodes:
            return {}

        distances = graph.bfs(node_id, direction=direction, max_depth=max_depth)
        if not distances:
            return {}

        adjacency = graph.reverse_adjacency if direction == "backward" else graph.adjacency
        edge_key = "parents" if direction == "backward" else "children"

        trace: Dict[str, Dict[str, Any]] = {}
        for current_id, distance in distances.items():
            node = graph.nodes.get(current_id, {})
            class_type = str(node.get("class_type") or node.get("type") or "")
            neighbours = [str(neighbour) for neighbour in adjacency.get(current_id, [])]

            payload: Dict[str, Any] = {
                "distance": distance,
                "class_type": class_type,
            }
            if neighbours:
                payload[edge_key] = neighbours

            trace[str(current_id)] = payload

        return trace

    def find_sampler_candidates(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        max_depth: int = 6,
    ) -> List[SamplerCandidate]:
        """Rank potential sampler nodes walking backward from ``start_node``."""

        graph = WorkflowGraph.from_workflow(workflow)
        if start_node not in graph.nodes:
            return []

        distances = graph.bfs(start_node, direction="backward", max_depth=max_depth)
        candidates: List[SamplerCandidate] = []

        start_entry = graph.nodes.get(start_node)
        if start_entry:
            class_type = str(start_entry.get("class_type") or start_entry.get("type") or "")
            inputs = _coerce_mapping(start_entry.get("inputs"))
            scored = self._score_sampler_candidate(class_type, inputs)
            if scored is not None:
                priority, reason = scored
                candidates.append(
                    SamplerCandidate(
                        node_id=start_node,
                        class_type=class_type,
                        distance=0,
                        priority=priority,
                        inputs=inputs,
                        reason=reason,
                    )
                )

        for node_id, distance in distances.items():
            if node_id == start_node:
                continue

            node = graph.nodes.get(node_id)
            if not node:
                continue

            class_type = str(node.get("class_type") or node.get("type") or "")
            inputs = _coerce_mapping(node.get("inputs"))

            score = self._score_sampler_candidate(class_type, inputs)
            if score is None:
                continue

            priority, reason = score
            candidates.append(
                SamplerCandidate(
                    node_id=node_id,
                    class_type=class_type,
                    distance=distance,
                    priority=priority,
                    inputs=inputs,
                    reason=reason,
                )
            )

        candidates.sort(
            key=lambda item: (item.priority, item.distance, item.class_type.lower(), item.node_id)
        )
        return candidates

    def find_best_sampler(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        max_depth: int = 6,
    ) -> Optional[SamplerCandidate]:
        """Return the highest-ranked sampler candidate for ``start_node``."""

        candidates = self.find_sampler_candidates(
            workflow,
            start_node,
            max_depth=max_depth,
        )
        return candidates[0] if candidates else None

    def discover_text_nodes(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        max_depth: int = 5,
        min_length: int = 5,
    ) -> List[PromptNodeRef]:
        """Locate text-bearing nodes nearest to ``start_node``."""

        graph = WorkflowGraph.from_workflow(workflow)
        if start_node not in graph.nodes:
            return []

        distances = graph.bfs(start_node, direction="backward", max_depth=max_depth)
        results: List[PromptNodeRef] = []

        for node_id, distance in distances.items():
            if node_id == start_node:
                continue

            node = graph.nodes.get(node_id)
            if not node:
                continue

            class_type = str(node.get("class_type") or node.get("type") or "")
            inputs = _coerce_mapping(node.get("inputs"))
            texts = self._collect_text_inputs(inputs, min_length=min_length)

            sources: Dict[str, str] = {key: "input" for key in texts}

            widget_values = node.get("widgets_values")
            if isinstance(widget_values, list):
                for index, value in enumerate(widget_values):
                    if not isinstance(value, str):
                        continue
                    candidate = value.strip()
                    if len(candidate) < min_length:
                        continue
                    key = f"widget_{index}"
                    # Ensure we do not clobber input-derived keys
                    while key in texts:
                        key = f"widget_{index}_{len(texts)}"
                    texts[key] = candidate
                    sources[key] = "widget"

            if not texts:
                continue

            results.append(
                PromptNodeRef(
                    node_id=node_id,
                    class_type=class_type,
                    distance=distance,
                    is_negative=self._infer_negative_flag(class_type, inputs),
                    texts=texts,
                    sources=sources,
                )
            )

        results.sort(
            key=lambda item: (item.distance, 1 if item.is_negative else 0, item.class_type.lower(), item.node_id)
        )
        return results

    def discover_prompt_nodes(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        max_depth: int = 5,
        min_length: int = 5,
    ) -> List[PromptNodeRef]:
        """Locate prompt-oriented nodes (inputs only) nearest to ``start_node``."""

        text_nodes = self.discover_text_nodes(
            workflow,
            start_node,
            max_depth=max_depth,
            min_length=min_length,
        )

        filtered: List[PromptNodeRef] = []
        for node_ref in text_nodes:
            input_texts = {
                key: value
                for key, value in node_ref.texts.items()
                if node_ref.sources.get(key) != "widget"
            }
            if not input_texts:
                continue

            input_sources = {
                key: source
                for key, source in node_ref.sources.items()
                if source != "widget"
            }

            filtered.append(
                PromptNodeRef(
                    node_id=node_ref.node_id,
                    class_type=node_ref.class_type,
                    distance=node_ref.distance,
                    is_negative=node_ref.is_negative,
                    texts=input_texts,
                    sources=input_sources,
                )
            )

        return filtered

    @staticmethod
    def _infer_negative_flag(class_type: str, inputs: Dict[str, Any]) -> bool:
        lowered = class_type.lower()
        if "negative" in lowered:
            return True
        marker = inputs.get("is_negative")
        if isinstance(marker, bool):
            return marker
        if isinstance(marker, str):
            return marker.lower() in {"true", "1", "yes"}
        return False

    def _extract_multi_lora_assets(
        self,
        node_id: str,
        class_type: str,
        inputs: Dict[str, Any],
    ) -> List[AssetRecord]:
        records: List[AssetRecord] = []

        for slot in range(1, 9):
            enabled = _is_truthy(inputs.get(f"lora_{slot}_enable"))
            name = inputs.get(f"lora_{slot}_name")

            if not (enabled and isinstance(name, str) and name and name.lower() != "none"):
                continue

            strength_model = _as_float(inputs.get(f"lora_{slot}_strength"))
            clip_strength = _as_float(inputs.get(f"lora_{slot}_clip_strength"))

            extra: Dict[str, Any] = {"slot": slot}
            if strength_model is not None:
                extra["strength_model"] = strength_model
            if clip_strength is not None:
                extra["strength_clip"] = clip_strength

            numeric = [value for value in (strength_model, clip_strength) if value is not None]
            if numeric:
                extra["strength"] = sum(numeric) / len(numeric)

            records.append(
                AssetRecord(
                    name=name,
                    node_id=node_id,
                    source="multi_loader",
                    extra=extra,
                )
            )

        return records

    def _extract_inline_assets(self, prompt: PromptText, discovery: AssetDiscovery) -> None:
        prompt_role = "negative" if prompt.is_negative else "positive"

        inline_loras = list(LORA_STRICT.finditer(prompt.text))
        seen_spans = {match.span() for match in inline_loras}

        for match in inline_loras:
            name = _normalise_asset_name(match.group(1))
            if not name:
                continue

            strength_model = _as_float(match.group(2))
            if strength_model is None:
                continue

            strength_clip = _as_float(match.group(3)) if match.lastindex and match.lastindex >= 3 else None

            extra: Dict[str, Any] = {
                "source_prompt": prompt.node_id,
                "prompt_role": prompt_role,
            }

            if strength_model is not None:
                extra["strength_model"] = strength_model
            if strength_clip is not None:
                extra["strength_clip"] = strength_clip

            numeric = [value for value in (strength_model, strength_clip) if value is not None]
            if numeric:
                extra["strength"] = sum(numeric) / len(numeric)

            discovery.loras.append(
                AssetRecord(
                    name=name,
                    node_id=prompt.node_id,
                    source="inline",
                    extra=extra,
                )
            )

        # Fallback legacy format <lora:name>
        for match in LORA_LEGACY.finditer(prompt.text):
            if match.span() in seen_spans:
                continue
            raw_payload = _normalise_asset_name(match.group(1))
            if not raw_payload or ":" in raw_payload:
                continue

            discovery.loras.append(
                AssetRecord(
                    name=raw_payload,
                    node_id=prompt.node_id,
                    source="inline",
                    extra={
                        "source_prompt": prompt.node_id,
                        "prompt_role": prompt_role,
                    },
                )
            )

        for match in EMBEDDING_TAG.finditer(prompt.text):
            name = _normalise_asset_name(match.group(1))
            if not name:
                continue

            discovery.embeddings.append(
                AssetRecord(
                    name=name,
                    node_id=prompt.node_id,
                    source="inline",
                    extra={
                        "source_prompt": prompt.node_id,
                        "prompt_role": prompt_role,
                    },
                )
            )

    @staticmethod
    def _collect_text_inputs(inputs: Dict[str, Any], *, min_length: int = 5) -> Dict[str, str]:
        texts: Dict[str, str] = {}
        for key, value in inputs.items():
            if not isinstance(value, str):
                continue
            candidate = value.strip()
            if not candidate:
                continue
            lowered = key.lower()
            if lowered in {"text", "prompt", "string", "value", "content"} or len(candidate) >= min_length:
                texts[key] = candidate
        return texts

    @staticmethod
    def _score_sampler_candidate(class_type: str, inputs: Dict[str, Any]) -> Optional[Tuple[int, str]]:
        if not class_type:
            return None

        lowered = class_type.lower()
        if "sampler" in lowered:
            return 0, "class_match"

        if not inputs:
            return None

        keys = [key.lower() for key in inputs]
        has_steps = any("step" in key for key in keys)
        has_cfg = any("cfg" in key or "guidance" in key for key in keys)
        has_sched = any("sched" in key for key in keys)
        has_seed = any("seed" in key for key in keys)

        if has_steps and has_cfg:
            return 1, "steps_cfg"
        if has_steps and has_sched:
            return 2, "steps_scheduler"
        if has_steps and has_seed:
            return 2, "steps_seed"
        if has_steps:
            return 3, "steps_only"

        return None
