"""
file_loads.py
Records which model files a node looks up while it executes, by wrapping
folder_paths.get_full_path and get_full_path_or_raise. The folder category
('loras', 'diffusion_models', 'vae', ...) tells us the role of the file without
knowing anything about the node that asked for it.

Lookups made outside node execution (UI listing, validation) are ignored.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from typing import Optional

from .. import shared

_MARK = "__aaa_meta_wrapped__"
_FUNCTIONS = ("get_full_path", "get_full_path_or_raise")
_IGNORED_CATEGORIES = {"custom_nodes", "configs", "classifiers"}


def _record(folder_name, filename, full_path: Optional[str]) -> None:
    if not isinstance(folder_name, str) or not isinstance(filename, str) or not full_path:
        return
    if folder_name in _IGNORED_CATEGORIES:
        return
    try:
        from comfy_execution.utils import get_executing_context
        context = get_executing_context()
    except Exception:
        return
    if context is None:
        return
    st = shared.state()
    with st.lock:
        st.stats["file_lookups"] += 1
        entry = st.nodes.get(str(context.node_id))
        if entry is None:
            entry = shared.new_entry("", context.prompt_id)
            entry["files_run"] = []
            st.nodes[str(context.node_id)] = entry
        target = entry["files_run"] if entry.get("files_run") is not None else entry["files"]
        for item in target:
            if item["category"] == folder_name and item["name"] == filename:
                return
        target.append({"category": folder_name, "name": filename, "path": str(full_path)})


def _make_wrapper(original):
    def aaa_meta_get_full_path(folder_name, filename, *args, **kwargs):
        result = original(folder_name, filename, *args, **kwargs)
        try:
            _record(folder_name, filename, result)
        except Exception as exc:
            shared.note_error("file_loads", exc)
        return result

    setattr(aaa_meta_get_full_path, _MARK, True)
    aaa_meta_get_full_path.__wrapped__ = original
    aaa_meta_get_full_path.__name__ = getattr(original, "__name__", "get_full_path")
    aaa_meta_get_full_path.__doc__ = getattr(original, "__doc__", None)
    return aaa_meta_get_full_path


def install(folder_paths_module=None) -> bool:
    st = shared.state()
    if folder_paths_module is None:
        import folder_paths as folder_paths_module
    active = False
    for name in _FUNCTIONS:
        original = getattr(folder_paths_module, name, None)
        if original is None:
            continue
        if getattr(original, _MARK, False):
            active = True
            continue
        setattr(folder_paths_module, name, _make_wrapper(original))
        active = True
    st.installed["file_loads"] = active
    return active
