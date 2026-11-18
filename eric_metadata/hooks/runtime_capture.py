"""Placeholder for the first runtime-hook module (removed 2026-11).

The hooks that used to live here wrapped ComfyUI's executor. Automatic collection
is now done by aaa_meta.capture, which the v1.0 save node and its companions use.
This file only keeps the names that "Metadata Save Image v099d" and "save image
simple" import, so those older nodes still load; every call reports "nothing
captured" and they fall back to reading the workflow graph, as they did whenever
the hooks were switched off (the default).
"""

from typing import Any, Dict, List, Optional


class HookSession:                                           # kept for type hints in the old nodes
    prompt_id: str = ""
    prompt_payload: Any = None
    events: List[Dict[str, Any]] = []


def enable_hooks(*_args: Any, **_kwargs: Any) -> bool:
    return False


def disable_hooks(*_args: Any, **_kwargs: Any) -> bool:
    return False


def hooks_enabled() -> bool:
    return False


def get_session(prompt_id: str) -> Optional[HookSession]:
    return None


def consume_session(prompt_id: str) -> Optional[HookSession]:
    return None


def active_prompt_ids() -> List[str]:
    return []


def auto_enable_from_env(*_args: Any, **_kwargs: Any) -> None:
    return None


def reset_state_for_tests() -> None:
    return None


__all__ = ["HookSession", "enable_hooks", "disable_hooks", "hooks_enabled", "get_session", "consume_session",
           "active_prompt_ids", "auto_enable_from_env", "reset_state_for_tests"]
