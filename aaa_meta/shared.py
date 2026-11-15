"""
shared.py
Process-wide capture state.

The pack's __init__ can be imported twice under two module names (ComfyUI's
path-based name and the 'AAA_Metadata_System' alias). Two copies of this module
would then hold two separate stores: the hook would write to one and the save
node would read the other. To make that impossible the state lives in a tiny
synthetic module registered in sys.modules, holding only plain dicts and lists.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import sys
import threading
import types

_STATE_NAME = "_aaa_meta_shared_state"

# Longest string kept per captured value (prompts can be long; images never get here).
MAX_STRING_CHARS = 100_000
# Oldest entries are dropped beyond this many node entries.
MAX_NODE_ENTRIES = 4000


def state() -> types.ModuleType:
    """Return the single shared state object, creating it on first use."""
    mod = sys.modules.get(_STATE_NAME)
    if mod is None:
        mod = types.ModuleType(_STATE_NAME)
        mod.nodes = {}          # node_id -> entry dict (see new_entry)
        mod.lock = threading.RLock()
        mod.installed = {}      # hook name -> True
        mod.stats = {"exec_calls": 0, "file_lookups": 0, "errors": 0, "last_error": ""}
        mod.run_counter = 0
        sys.modules[_STATE_NAME] = mod
    return mod


def new_entry(class_name: str, prompt_id) -> dict:
    return {
        "class_name": class_name,   # Python class name (not the registry key)
        "prompt_id": prompt_id,
        "inputs": {},               # input name -> scalar / list / small dict
        "outputs": {},              # output index -> scalar / list
        "files": [],                # [{"category", "name", "path"}] last known
        "files_run": None,          # list while the node is executing, else None
        "published": {},            # values stated explicitly via aaa_meta.publish()
        "run": 0,
    }


def note_error(where: str, exc: Exception) -> None:
    st = state()
    st.stats["errors"] += 1
    st.stats["last_error"] = f"{where}: {type(exc).__name__}: {exc}"


def trim_if_needed() -> None:
    st = state()
    if len(st.nodes) <= MAX_NODE_ENTRIES:
        return
    ordered = sorted(st.nodes.items(), key=lambda kv: kv[1].get("run", 0))
    for node_id, _ in ordered[: len(ordered) - MAX_NODE_ENTRIES]:
        st.nodes.pop(node_id, None)
