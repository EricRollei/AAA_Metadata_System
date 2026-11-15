"""
exec_hook.py
Wraps execution._async_map_node_over_list, the single function ComfyUI calls to
run a node. At that point every input is resolved to its real value (including
values that arrived over links, such as an LLM-written prompt or a generated
seed) and the node's outputs come back as the return value.

Only small plain values are kept: strings, numbers, booleans, short lists and
small dicts of those. Tensors, models and images are never touched.

The wrapper is transparent (*args/**kwargs pass straight through) and chains on
top of whatever is already installed (comfyui-lora-manager wraps the same
function).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import asyncio
import inspect
from typing import Any, Optional

from .. import shared

_SKIP = object()
_TARGET = "_async_map_node_over_list"
_MARK = "__aaa_meta_wrapped__"
_MAX_LIST = 64
_MAX_DICT_KEYS = 48


def simplify(value: Any, depth: int = 0) -> Any:
    """Reduce a runtime value to something small and JSON-safe, or _SKIP."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value[: shared.MAX_STRING_CHARS]
    if depth >= 3:
        return _SKIP
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_LIST:
            return _SKIP
        out = []
        for item in value:
            simple = simplify(item, depth + 1)
            if simple is _SKIP:
                return _SKIP
            out.append(simple)
        return out
    if isinstance(value, dict):
        if len(value) > _MAX_DICT_KEYS:
            return _SKIP
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                return _SKIP
            simple = simplify(item, depth + 1)
            if simple is _SKIP:
                continue
            out[key] = simple
        return out if out else _SKIP
    return _SKIP


def _capture_inputs(input_data_all: Any) -> dict:
    captured = {}
    if not isinstance(input_data_all, dict):
        return captured
    for name, values in input_data_all.items():
        if not isinstance(name, str) or not isinstance(values, (list, tuple)) or not values:
            continue
        simple = simplify(values[0]) if len(values) == 1 else simplify(list(values))
        if simple is not _SKIP:
            captured[name] = simple
    return captured


def _unwrap_result(result: Any) -> Optional[tuple]:
    """A node result can be a tuple, a {'ui','result'} dict, or a V3 NodeOutput."""
    if result is None or isinstance(result, asyncio.Task):
        return None
    if isinstance(result, dict):
        result = result.get("result")
    else:
        for attr in ("result", "args"):
            inner = getattr(result, attr, None)
            if isinstance(inner, (tuple, list)):
                result = inner
                break
    if isinstance(result, (tuple, list)):
        return tuple(result)
    return None


def _capture_outputs(results: Any) -> dict:
    outputs = {}
    if not isinstance(results, (list, tuple)) or not results:
        return outputs
    values = _unwrap_result(results[0])
    if values is None:
        return outputs
    for index, value in enumerate(values):
        simple = simplify(value)
        if simple is not _SKIP:
            outputs[index] = simple
    return outputs


def _before(args: tuple, kwargs: dict) -> Optional[str]:
    prompt_id = args[0] if len(args) > 0 else kwargs.get("prompt_id")
    unique_id = args[1] if len(args) > 1 else kwargs.get("unique_id")
    obj = args[2] if len(args) > 2 else kwargs.get("obj")
    input_data_all = args[3] if len(args) > 3 else kwargs.get("input_data_all")
    func = args[4] if len(args) > 4 else kwargs.get("func")
    if unique_id is None or obj is None:
        return None
    if func != getattr(obj, "FUNCTION", None):
        return None  # lazy-status checks and similar side calls
    node_id = str(unique_id)
    cls = obj if inspect.isclass(obj) else type(obj)
    st = shared.state()
    with st.lock:
        st.stats["exec_calls"] += 1
        st.run_counter += 1
        previous = st.nodes.get(node_id)
        entry = shared.new_entry(cls.__name__, prompt_id)
        if previous is not None and previous.get("class_name") == cls.__name__:
            entry["files"] = previous.get("files", [])
        entry["inputs"] = _capture_inputs(input_data_all)
        entry["files_run"] = []
        entry["run"] = st.run_counter
        st.nodes[node_id] = entry
        shared.trim_if_needed()
    return node_id


def _after(node_id: str, results: Any) -> None:
    st = shared.state()
    with st.lock:
        entry = st.nodes.get(node_id)
        if entry is None:
            return
        entry["outputs"] = _capture_outputs(results)
        files_run = entry.get("files_run")
        if files_run:
            entry["files"] = files_run
        entry["files_run"] = None
    # Async nodes return unfinished tasks; pick their outputs up when they finish.
    if isinstance(results, (list, tuple)) and results and isinstance(results[0], asyncio.Task):
        def _done(task: "asyncio.Task", _node_id: str = node_id) -> None:
            try:
                if task.cancelled() or task.exception() is not None:
                    return
                with st.lock:
                    late = st.nodes.get(_node_id)
                    if late is not None:
                        late["outputs"] = _capture_outputs([task.result()])
            except Exception as exc:  # pragma: no cover
                shared.note_error("exec_hook.async_done", exc)
        try:
            results[0].add_done_callback(_done)
        except Exception as exc:  # pragma: no cover
            shared.note_error("exec_hook.add_done_callback", exc)


def publish_for_current_node(fields: dict) -> bool:
    try:
        from comfy_execution.utils import get_executing_context
        context = get_executing_context()
    except Exception:
        return False
    if context is None:
        return False
    st = shared.state()
    with st.lock:
        entry = st.nodes.get(str(context.node_id))
        if entry is None:
            entry = shared.new_entry("", context.prompt_id)
            st.nodes[str(context.node_id)] = entry
        for key, value in fields.items():
            simple = simplify(value)
            if simple is not _SKIP:
                entry["published"][key] = simple
    return True


def make_wrapper(original):
    async def aaa_meta_map_node_over_list(*args, **kwargs):
        node_id = None
        try:
            node_id = _before(args, kwargs)
        except Exception as exc:
            shared.note_error("exec_hook.before", exc)
        results = await original(*args, **kwargs)
        if node_id is not None:
            try:
                _after(node_id, results)
            except Exception as exc:
                shared.note_error("exec_hook.after", exc)
        return results

    setattr(aaa_meta_map_node_over_list, _MARK, True)
    aaa_meta_map_node_over_list.__wrapped__ = original
    return aaa_meta_map_node_over_list


def _already_wrapped(func) -> bool:
    seen = 0
    while func is not None and seen < 20:
        if getattr(func, _MARK, False):
            return True
        func = getattr(func, "__wrapped__", None)
        seen += 1
    return False


def install(execution_module=None) -> bool:
    """Install the wrapper. Returns True when active (now or already)."""
    st = shared.state()
    if execution_module is None:
        import execution as execution_module  # ComfyUI's execution.py
    original = getattr(execution_module, _TARGET, None)
    if original is None or not inspect.iscoroutinefunction(original):
        return False
    if _already_wrapped(original):
        st.installed["exec_hook"] = True
        return True
    setattr(execution_module, _TARGET, make_wrapper(original))
    st.installed["exec_hook"] = True
    return True
