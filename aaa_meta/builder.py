"""
builder.py
Turns a prompt graph (plus whatever was captured at runtime) into a
GenerationRecord, working backwards from the node that saves the image.

No per-node lookup table. Nodes are recognised by the shape of their inputs:
  - "ksampler" shape:  model + positive links, steps and a seed
  - "custom" shape:    guider + sigmas links (SamplerCustomAdvanced style)
  - "all-in-one" shape: a seed plus a prompt (or steps) on one node
Text, seeds, steps and so on are then read from whatever feeds those inputs.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import datetime
import re
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from .graph import Link, PromptGraph
from .models import base_name, looks_like_model_file, role_for_category, scan_values
from .record import GenerationRecord, ModelRef, SamplingPass
from .resolve import Resolver, as_number

SEED_KEYS = ("seed", "noise_seed")
STEP_KEYS = ("steps", "num_steps", "num_inference_steps")
CFG_KEYS = ("cfg", "cfg_scale", "true_cfg_scale", "guidance_scale")
SAMPLER_KEYS = ("sampler_name", "sampler")
SCHEDULER_KEYS = ("scheduler", "schedule", "sigma_schedule")
DENOISE_KEYS = ("denoise", "denoising_strength", "strength")
PROMPT_KEYS = ("prompt", "positive", "positive_prompt", "text", "instruction", "caption")
NEGATIVE_KEYS = ("negative_prompt", "negative", "neg_prompt")
LATENT_LINK_NAMES = ("latent_image", "latent", "samples", "latents")

_TEXT_HINTS = ("prompt", "text", "caption", "instruction", "positive", "negative",
               "t5xxl", "clip_l", "clip_g", "llama", "string", "tags")
_TEXT_EXCLUDE = ("system", "preset", "path", "file", "template", "prefix", "mode", "type",
                 "name", "notes", "meta", "format", "key", "find", "replace", "delimiter")
_NON_PIXEL_LINK_HINTS = ("cond", "positive", "negative", "prompt", "text", "clip", "instruction")
_ROLE_ORDER = ("checkpoint", "unet", "pipeline", "lora", "text_encoder", "vae")
_STAGE_KEY = re.compile(r"^s(\d+)_([a-z_]+)$")

CategoryLookup = Callable[[str], Optional[str]]


class _Builder:
    def __init__(self, graph: PromptGraph, anchor_id: str, resolver: Resolver,
                 category_lookup: Optional[CategoryLookup]):
        self.graph = graph
        self.anchor = str(anchor_id)
        self.resolver = resolver
        self.category_lookup = category_lookup
        self.record = GenerationRecord(anchor_node=self.anchor)

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _number(self, node_id: str, keys: Tuple[str, ...]) -> Optional[float]:
        inputs = self.graph.inputs(node_id)
        for key in keys:
            if key in inputs:
                value = self.resolver.number(node_id, key)
                if value is not None:
                    return value
        return None

    def _text(self, node_id: str, keys: Tuple[str, ...]) -> Optional[str]:
        inputs = self.graph.inputs(node_id)
        for key in keys:
            if key in inputs:
                value = self.resolver.text(node_id, key)
                if value is not None and value.strip():
                    return value
        return None

    def _find_number(self, start: str, keys: Tuple[str, ...], max_depth: int = 4) -> Optional[float]:
        for node_id, _ in self.graph.walk_upstream([start], max_depth):
            value = self._number(node_id, keys)
            if value is not None:
                return value
        return None

    def _find_text(self, start: str, keys: Tuple[str, ...], max_depth: int = 4) -> Optional[str]:
        for node_id, _ in self.graph.walk_upstream([start], max_depth):
            value = self._text(node_id, keys)
            if value is not None:
                return value
        return None

    @staticmethod
    def _int(value: Optional[float]) -> Optional[int]:
        return int(value) if value is not None else None

    @staticmethod
    def _normalise_steps(sampling: SamplingPass) -> None:
        """An end step at or past the total, or a 0 start with no end, means 'whole range'."""
        if sampling.end_step is not None and sampling.steps is not None and sampling.end_step >= sampling.steps:
            sampling.end_step = None
        if sampling.start_step == 0 and sampling.end_step is None:
            sampling.start_step = None

    # ------------------------------------------------------------------
    # classify nodes by input shape
    # ------------------------------------------------------------------
    def _shape(self, node_id: str) -> Optional[str]:
        links = self.graph.links(node_id)
        names = set(self.graph.inputs(node_id))
        if "guider" in links and "sigmas" in links:
            return "custom"
        if "sigmas" in links and "sampler" in links and ("positive" in links or "model" in links):
            return "custom_inline"
        if "model" in links and "positive" in links and names & set(STEP_KEYS) and names & set(SEED_KEYS):
            return "ksampler"
        has_seed = bool(names & set(SEED_KEYS))
        has_prompt = bool(names & (set(PROMPT_KEYS) | set(NEGATIVE_KEYS)))
        has_steps = bool(names & set(STEP_KEYS)) or any(_STAGE_KEY.match(n) for n in names)
        if has_seed and has_prompt and (has_steps or names & set(CFG_KEYS)):
            return "all_in_one"
        return None

    def _find_generators(self) -> List[Tuple[str, str, int]]:
        """
        Walk the pixel path upstream from the anchor. Returns (node, shape, depth)
        for every generator met, nearest first. A generator's prompt and model
        inputs are not followed, so prompt-writing nodes are never mistaken for
        image generators.
        """
        found: List[Tuple[str, str, int]] = []
        seen = set()
        queue = deque((src, 1) for src, _ in self.graph.links(self.anchor).values())
        while queue:
            node_id, depth = queue.popleft()
            if node_id in seen:
                continue
            seen.add(node_id)
            shape = self._shape(node_id)
            links = self.graph.links(node_id)
            if shape in ("ksampler", "custom", "custom_inline"):
                found.append((node_id, shape, depth))
                follow = [name for name in links if name in LATENT_LINK_NAMES]
            elif shape == "all_in_one":
                found.append((node_id, shape, depth))
                follow = [name for name in links
                          if any(h in name.lower() for h in ("image", "latent", "samples", "frames", "pixels"))]
            else:
                follow = [name for name in links
                          if not any(h in name.lower() for h in _NON_PIXEL_LINK_HINTS)]
            for name in follow:
                queue.append((links[name][0], depth + 1))
        return found

    # ------------------------------------------------------------------
    # prompt text behind a conditioning link
    # ------------------------------------------------------------------
    def _text_inputs(self, node_id: str) -> Dict[str, str]:
        texts: Dict[str, str] = {}
        for name in self.graph.inputs(node_id):
            low = name.lower()
            if any(x in low for x in _TEXT_EXCLUDE) or not any(h in low for h in _TEXT_HINTS):
                continue
            value = self.resolver.input_value(node_id, name)
            if isinstance(value, str) and value.strip() and not looks_like_model_file(value):
                texts[name] = value.strip()
        return texts

    def _conditioning_text(self, link: Optional[Link], role: str) -> Tuple[Optional[str], Optional[float]]:
        """Returns (text or None if not found, guidance value met on the way)."""
        if link is None:
            return None, None
        guidance: Optional[float] = None
        pieces: List[str] = []
        resolved_any = False
        seen = set()
        queue = deque([(link[0], 0)])
        while queue:
            node_id, depth = queue.popleft()
            if node_id in seen or depth > 8:
                continue
            seen.add(node_id)
            class_low = self.graph.class_type(node_id).lower()
            links = self.graph.links(node_id)
            if "guidance" in self.graph.inputs(node_id) and guidance is None:
                guidance = self.resolver.number(node_id, "guidance")
            if "zeroout" in class_low:
                resolved_any = True
                continue
            texts = self._text_inputs(node_id)
            if texts:
                negative_keys = [k for k in texts if "neg" in k.lower()]
                positive_keys = [k for k in texts if "neg" not in k.lower()]
                if role == "negative":
                    chosen = negative_keys or ([] if positive_keys and negative_keys else positive_keys)
                    # a dual-output encoder with only a positive text has an empty negative
                    if not negative_keys and any("neg" in n.lower() for n in self.graph.inputs(node_id)):
                        chosen = []
                else:
                    chosen = positive_keys
                    if not positive_keys:
                        # a positive-looking input exists but has no resolved text
                        # (it arrives over a link we could not follow): do not
                        # mistake the negative text for the prompt
                        unresolved_positive = any(
                            "neg" not in n.lower() and any(h in n.lower() for h in _TEXT_HINTS)
                            and not any(x in n.lower() for x in _TEXT_EXCLUDE)
                            for n in self.graph.inputs(node_id))
                        if unresolved_positive:
                            continue
                        chosen = negative_keys
                for key in chosen:
                    if texts[key] not in pieces:
                        pieces.append(texts[key])
                resolved_any = True
                continue
            follow = [name for name in links if "cond" in name.lower() or name.lower().startswith(role)]
            if role in links and ("positive" in links and "negative" in links):
                follow = [role]
            for name in follow:
                queue.append((links[name][0], depth + 1))
        if not resolved_any:
            return None, guidance
        return "\n".join(pieces), guidance

    # ------------------------------------------------------------------
    # sampling passes
    # ------------------------------------------------------------------
    def _pass_from_ksampler(self, node_id: str) -> Tuple[SamplingPass, Optional[Link], Optional[Link], Optional[Link]]:
        links = self.graph.links(node_id)
        sampling = SamplingPass(index=0, node_id=node_id, node_class=self.graph.class_type(node_id))
        sampling.seed = self._int(self._number(node_id, SEED_KEYS))
        sampling.steps = self._int(self._number(node_id, STEP_KEYS))
        sampling.cfg = self._number(node_id, CFG_KEYS)
        sampling.sampler = self._text(node_id, SAMPLER_KEYS)
        sampling.scheduler = self._text(node_id, SCHEDULER_KEYS)
        sampling.denoise = self._number(node_id, ("denoise",))
        sampling.start_step = self._int(self._number(node_id, ("start_at_step", "start_step")))
        sampling.end_step = self._int(self._number(node_id, ("end_at_step", "end_step")))
        self._normalise_steps(sampling)
        add_noise = self.resolver.input_value(node_id, "add_noise")
        if isinstance(add_noise, str):
            sampling.extras["add_noise"] = add_noise
        return sampling, links.get("positive"), links.get("negative"), links.get("model")

    def _pass_from_custom(self, node_id: str, inline: bool) -> Tuple[SamplingPass, Optional[Link], Optional[Link], Optional[Link]]:
        links = self.graph.links(node_id)
        sampling = SamplingPass(index=0, node_id=node_id, node_class=self.graph.class_type(node_id))
        # noise -> seed
        if "noise" in links:
            sampling.seed = self._int(self._find_number(links["noise"][0], SEED_KEYS, 3))
        if sampling.seed is None:
            sampling.seed = self._int(self._number(node_id, SEED_KEYS))
        # sampler -> name
        if "sampler" in links:
            source = links["sampler"][0]
            sampling.sampler = self._find_text(source, SAMPLER_KEYS, 2) or self.graph.class_type(source)
            if sampling.seed is None:
                sampling.seed = self._int(self._find_number(source, SEED_KEYS, 2))
        # sigmas -> steps / scheduler / denoise, noting a split on the way
        if "sigmas" in links:
            source, out_index = links["sigmas"]
            hops = 0
            while hops < 6:
                if "split" in self.graph.class_type(source).lower():
                    split_at = self._int(self._number(source, ("step", "split_step", "steps")))
                    if split_at is not None:
                        if out_index == 0:
                            sampling.end_step = split_at
                        else:
                            sampling.start_step = split_at
                    upstream = self.graph.link(source, "sigmas")
                    if upstream is None:
                        break
                    source, out_index = upstream
                    hops += 1
                    continue
                break
            sampling.steps = self._int(self._find_number(source, STEP_KEYS, 3))
            sampling.scheduler = self._find_text(source, SCHEDULER_KEYS, 3)
            sampling.denoise = self._find_number(source, ("denoise",), 3)
            if sampling.scheduler is None:
                sampling.scheduler = self.graph.class_type(source)
        # guider -> cfg and conditioning
        positive = negative = model = None
        if inline:
            sampling.cfg = self._number(node_id, CFG_KEYS)
            positive, negative, model = links.get("positive"), links.get("negative"), links.get("model")
        elif "guider" in links:
            for guider_id, _ in self.graph.walk_upstream([links["guider"][0]], 2):
                guider_links = self.graph.links(guider_id)
                if sampling.cfg is None:
                    sampling.cfg = self._number(guider_id, CFG_KEYS)
                if positive is None:
                    positive = guider_links.get("positive") or guider_links.get("conditioning")
                    negative = guider_links.get("negative")
                    model = guider_links.get("model")
                if positive is not None:
                    break
        return sampling, positive, negative, model

    def _passes_from_all_in_one(self, node_id: str) -> List[SamplingPass]:
        class_type = self.graph.class_type(node_id)
        seed = self._int(self._number(node_id, SEED_KEYS))
        names = list(self.graph.inputs(node_id))
        stages: Dict[int, Dict[str, str]] = {}
        for name in names:
            match = _STAGE_KEY.match(name)
            if match:
                stages.setdefault(int(match.group(1)), {})[match.group(2)] = name

        def positive_or_none(value: Optional[float]) -> Optional[float]:
            return value if value is not None and value >= 0 else None

        passes: List[SamplingPass] = []
        for stage in sorted(stages):
            keys = stages[stage]
            if "steps" not in keys:
                continue
            steps = self.resolver.number(node_id, keys["steps"])
            if steps is None or steps <= 0:
                continue
            enabled_key = keys.get("enable") or keys.get("enabled")
            if enabled_key and self.resolver.input_value(node_id, enabled_key) is False:
                continue
            sampling = SamplingPass(index=0, node_id=node_id, node_class=f"{class_type} stage {stage}")
            sampling.seed = seed
            sampling.steps = int(steps)
            if "cfg" in keys:
                sampling.cfg = self.resolver.number(node_id, keys["cfg"])
            for candidate in ("sampler", "sampler_name"):
                if candidate in keys:
                    sampling.sampler = self.resolver.text(node_id, keys[candidate])
            for candidate in ("schedule", "scheduler", "sigma_schedule"):
                if candidate in keys:
                    sampling.scheduler = self.resolver.text(node_id, keys[candidate])
            if "denoise" in keys:
                sampling.denoise = self.resolver.number(node_id, keys["denoise"])
            if "end_step" in keys:
                end_step = self.resolver.number(node_id, keys["end_step"])
                if end_step:
                    sampling.end_step = int(end_step)
                    start_step = self.resolver.number(node_id, keys.get("start_step", ""))
                    sampling.start_step = int(start_step) if start_step is not None else None
            passes.append(sampling)
        if passes:
            return passes
        sampling = SamplingPass(index=0, node_id=node_id, node_class=class_type)
        sampling.seed = seed
        sampling.steps = self._int(positive_or_none(self._number(node_id, STEP_KEYS)))
        sampling.cfg = positive_or_none(self._number(node_id, CFG_KEYS))
        sampling.sampler = self._text(node_id, SAMPLER_KEYS)
        sampling.scheduler = self._text(node_id, SCHEDULER_KEYS)
        sampling.denoise = self._number(node_id, ("denoise",))
        return [sampling]

    # ------------------------------------------------------------------
    # models
    # ------------------------------------------------------------------
    def _collect_models(self) -> None:
        ancestors = self.graph.ancestors(self.anchor)
        refs: List[ModelRef] = []
        seen_keys = set()
        self._loader_nodes = set()

        def add(ref: ModelRef) -> None:
            key = (ref.role, base_name(ref.name), ref.strength_model)
            if key in seen_keys:
                return
            seen_keys.add(key)
            refs.append(ref)

        for node_id in ancestors:
            class_type = self.graph.class_type(node_id)
            runtime: List[ModelRef] = []
            for item in self.resolver.files(node_id):
                role = role_for_category(str(item.get("category", "")))
                if role is None:
                    continue
                runtime.append(ModelRef(role=role, name=str(item.get("name", "")), path=item.get("path"),
                                        node_id=node_id, source="runtime"))
            values: Dict[str, Any] = dict(self.graph.literals(node_id))
            entry = self.resolver.entry(node_id)
            if entry is not None:
                values.update(entry.get("inputs", {}))
            static_found = scan_values(values, class_type)
            disabled = {base_name(f.name) for f in static_found if not f.enabled}
            for found in static_found:
                if not found.enabled:
                    continue
                match = next((r for r in runtime if base_name(r.name) == base_name(found.name)), None)
                if match is not None:
                    match.strength_model = found.strength_model
                    match.strength_clip = found.strength_clip
                    match.extra_strengths = dict(found.extra_strengths)
                    continue
                role = found.role
                if self.category_lookup is not None and looks_like_model_file(found.name):
                    category = self.category_lookup(found.name)
                    looked_up = role_for_category(category) if category else None
                    if looked_up:
                        role = looked_up
                runtime.append(ModelRef(role=role, name=found.name, node_id=node_id, source="static",
                                        strength_model=found.strength_model, strength_clip=found.strength_clip,
                                        extra_strengths=dict(found.extra_strengths)))
            if runtime or static_found:
                self._loader_nodes.add(node_id)
            for ref in runtime:
                if base_name(ref.name) in disabled:
                    continue
                add(ref)

        def rank(ref: ModelRef) -> int:
            return _ROLE_ORDER.index(ref.role) if ref.role in _ROLE_ORDER else len(_ROLE_ORDER)

        refs.sort(key=rank)
        self.record.models = refs

    def _collect_model_chain(self, model_link: Optional[Link]) -> None:
        if model_link is None:
            return
        loader_nodes = getattr(self, "_loader_nodes", set())
        node_id: Optional[str] = model_link[0]
        hops = 0
        while node_id is not None and hops < 30:
            hops += 1
            class_low = self.graph.class_type(node_id).lower()
            if node_id not in loader_nodes and "lora" not in class_low and "load" not in class_low:
                params: Dict[str, Any] = {}
                for name, value in self.graph.literals(node_id).items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and len(params) < 8:
                        params[name] = value
                    elif isinstance(value, str) and 0 < len(value) <= 40 and len(params) < 8:
                        params[name] = value
                self.record.model_chain.append({"class_type": self.graph.class_type(node_id),
                                                "node_id": node_id, "params": params})
            upstream = self.graph.link(node_id, "model")
            node_id = upstream[0] if upstream else None

    # ------------------------------------------------------------------
    # assemble
    # ------------------------------------------------------------------
    def build(self) -> GenerationRecord:
        record = self.record
        record.created = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        if not self.graph.has(self.anchor):
            record.warnings.append(f"anchor node {self.anchor} not in graph")
            return record

        generators = self._find_generators()
        generators.sort(key=lambda item: -item[2])           # furthest from the save node runs first
        first_model_link: Optional[Link] = None
        first_latent_node: Optional[str] = None
        prompts: List[Tuple[Optional[str], Optional[str]]] = []

        for node_id, shape, _ in generators:
            if shape == "all_in_one":
                new_passes = self._passes_from_all_in_one(node_id)
                positive = self._text(node_id, PROMPT_KEYS)
                negative = self._text(node_id, NEGATIVE_KEYS)
                width = self._number(node_id, ("width",))
                height = self._number(node_id, ("height",))
                if record.width is None and width and height and width > 0 and height > 0:
                    record.width, record.height = int(width), int(height)
            else:
                if shape == "ksampler":
                    sampling, pos_link, neg_link, model_link = self._pass_from_ksampler(node_id)
                else:
                    sampling, pos_link, neg_link, model_link = self._pass_from_custom(node_id, shape == "custom_inline")
                positive, guidance = self._conditioning_text(pos_link, "positive")
                negative, _ = self._conditioning_text(neg_link, "negative")
                sampling.guidance = guidance
                new_passes = [sampling]
                if first_model_link is None:
                    first_model_link = model_link
                if first_latent_node is None:
                    first_latent_node = node_id
            published = self.resolver.published(node_id)
            for key in ("seed", "steps", "cfg", "sampler", "scheduler", "denoise", "guidance"):
                if key in published:
                    for sampling in new_passes:
                        setattr(sampling, key, published[key])
            positive = published.get("positive", positive)
            negative = published.get("negative", negative)
            prompts.append((positive, negative))
            for sampling in new_passes:
                sampling.index = len(record.passes)
                record.passes.append(sampling)

        for positive, negative in prompts:
            if not record.positive and positive:
                record.positive = positive
            if not record.negative and negative:
                record.negative = negative

        if record.width is None and first_latent_node is not None:
            for name in LATENT_LINK_NAMES:
                link = self.graph.link(first_latent_node, name)
                if link is not None:
                    width = self._find_number(link[0], ("width",), 5)
                    height = self._find_number(link[0], ("height",), 5)
                    if width and height and width > 0 and height > 0:
                        record.width, record.height = int(width), int(height)
                    break

        self._collect_models()
        self._collect_model_chain(first_model_link)

        if not record.passes:
            record.warnings.append("no sampler found on the image path")
        elif record.seed is None:
            record.warnings.append("seed not resolved")
        if not record.positive:
            record.warnings.append("positive prompt not found")
        if not record.base_models:
            record.warnings.append("no base model found")

        if self.resolver.static_passthrough:
            record.warnings.append(
                "values read through upstream nodes without runtime data (may be pre-rewrite): "
                + ", ".join(sorted(self.resolver.static_passthrough)))
        if self.resolver.used_runtime:
            record.capture_mode = "mixed" if self.resolver.used_static_links else "runtime"
        else:
            record.capture_mode = "static"
        return record


def build_record(graph: PromptGraph, anchor_id: str, captured: Optional[Dict[str, dict]] = None,
                 prompt_id: Optional[str] = None,
                 category_lookup: Optional[CategoryLookup] = None) -> GenerationRecord:
    """
    graph            the prompt graph
    anchor_id        id of the node that receives the final image (the save node)
    captured         shared.state().nodes, or None for a purely static trace
    prompt_id        id of the running prompt (lets fresh captures be trusted outright)
    category_lookup  optional: model file name -> ComfyUI folder category
    """
    resolver = Resolver(graph, captured, prompt_id)
    return _Builder(graph, anchor_id, resolver, category_lookup).build()
