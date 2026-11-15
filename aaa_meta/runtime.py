"""
runtime.py
Glue for nodes running inside ComfyUI: builds the record for the calling node
from the live prompt, the captured runtime values and the model folders.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Dict, Optional

from . import shared
from .builder import build_record
from .graph import PromptGraph
from .hashing import HashCache
from .record import GenerationRecord

_CATEGORIES = ("checkpoints", "diffusion_models", "loras", "vae", "text_encoders", "clip_vision",
               "controlnet", "style_models", "upscale_models", "embeddings")
_hash_cache: Optional[HashCache] = None
_category_index: Dict[str, str] = {}
_category_index_built = False


def _user_data_dir() -> Optional[str]:
    try:
        import folder_paths
        return os.path.join(folder_paths.get_user_directory(), "aaa_metadata")
    except Exception:
        return None


def hash_cache() -> HashCache:
    global _hash_cache
    if _hash_cache is None:
        base = _user_data_dir()
        _hash_cache = HashCache(os.path.join(base, "hash_cache.json") if base else None)
    return _hash_cache


def _build_category_index() -> None:
    global _category_index_built
    _category_index_built = True
    try:
        import folder_paths
    except Exception:
        return
    for category in _CATEGORIES:
        try:
            for name in folder_paths.get_filename_list(category):
                _category_index.setdefault(name.replace("\\", "/").lower(), category)
        except Exception:
            continue


def category_lookup(name: str) -> Optional[str]:
    if not _category_index_built:
        _build_category_index()
    return _category_index.get(name.replace("\\", "/").lower())


def _resolve_paths_and_hashes(record: GenerationRecord, hash_models: str) -> None:
    try:
        import folder_paths
    except Exception:
        folder_paths = None
    cache = hash_cache()
    for model in record.models:
        if model.path is None:
            if os.path.isabs(model.name) and os.path.isfile(model.name):
                model.path = model.name
            elif folder_paths is not None:
                category = category_lookup(model.name)
                if category:
                    try:
                        model.path = folder_paths.get_full_path(category, model.name)
                    except Exception:
                        model.path = None
        if hash_models != "off" and model.path:
            model.sha256 = cache.sha256(model.path, compute=(hash_models == "compute"))
    cache.save()


def _comfyui_version() -> Optional[str]:
    try:
        import comfyui_version
        return str(comfyui_version.__version__)
    except Exception:
        return None


def record_for_node(unique_id: Any, prompt: Optional[dict] = None, dynprompt: Any = None,
                    hash_models: str = "cached", dump_holder: Optional[list] = None) -> GenerationRecord:
    """
    hash_models: "off"     no hashes
                 "cached"  only hashes already known (cache, .sha256, LoRA Manager metadata)
                 "compute" hash files that are not known yet (slow the first time)
    """
    with_dump = dump_holder is not None
    graph = PromptGraph.from_dynprompt(dynprompt, prompt) if dynprompt is not None else PromptGraph.from_prompt(prompt or {})
    prompt_id = None
    try:
        from comfy_execution.utils import get_executing_context
        context = get_executing_context()
        if context is not None:
            prompt_id = context.prompt_id
    except Exception:
        pass
    state = shared.state()
    with state.lock:
        captured = {node_id: dict(entry) for node_id, entry in state.nodes.items()}
    record = build_record(graph, str(unique_id), captured, prompt_id, category_lookup)
    if with_dump:
        from .diagnostics import capture_dump
        try:
            dump_holder.append(capture_dump(graph, str(unique_id), captured, prompt_id))
        except Exception as exc:  # diagnostics must never break a save
            dump_holder.append(f"capture dump failed: {exc!r}")
    record.comfyui_version = _comfyui_version()
    if not state.installed.get("exec_hook"):
        record.warnings.append("runtime capture is not active; values come from the graph only")
    _resolve_paths_and_hashes(record, hash_models)
    return record
