"""Runtime hook infrastructure for optional ComfyUI capture."""

from __future__ import annotations

import copy
import datetime
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

HookCallable = Callable[..., Any]


@dataclass
class HookSession:
    """Lightweight container for per-prompt runtime capture."""

    prompt_id: str
    prompt_payload: Any
    start_ts: float
    events: List[Dict[str, Any]] = field(default_factory=list)
    resolved_inputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    # Performance tracking
    hook_call_count: int = 0
    hook_total_time: float = 0.0
    hook_max_time: float = 0.0


@dataclass
class HookState:
    """Mutable runtime hook status flags."""

    enabled: bool = False
    conflict_detected: bool = False
    auto_disabled: bool = False
    disable_reason: Optional[str] = None
    executor_class: Optional[Type[Any]] = None


_LOCK = threading.RLock()
_STATE = HookState()
_SESSIONS: Dict[str, HookSession] = {}
_EXECUTOR_PROMPTS: Dict[int, str] = {}
_BASELINES: Dict[int, Dict[str, HookCallable]] = {}
_ORIGINALS: Dict[str, HookCallable] = {}
_ERROR_SUPPRESSION: Dict[str, bool] = {}
_ENV_FLAG = "AAA_METADATA_ENABLE_HOOKS"


def _log(message: str) -> None:
    print(f"[AAA Metadata Hooks] {message}")


def _log_performance_metrics(session: HookSession) -> None:
    """Log performance metrics for a completed session."""
    try:
        from ..utils.config import get_runtime_log_performance, get_debug_enabled
        
        if not (get_runtime_log_performance() and get_debug_enabled()):
            return
        
        total_time_ms = session.hook_total_time * 1000
        max_time_ms = session.hook_max_time * 1000
        avg_time_ms = (total_time_ms / session.hook_call_count) if session.hook_call_count > 0 else 0
        
        _log(
            f"Performance: {session.prompt_id[:8]}... - "
            f"{session.hook_call_count} calls, "
            f"total={total_time_ms:.2f}ms, "
            f"avg={avg_time_ms:.3f}ms, "
            f"max={max_time_ms:.3f}ms"
        )
    except Exception:
        # Don't fail session consumption due to logging issues
        pass


def _register_baseline(executor_class: Type[Any]) -> Dict[str, HookCallable]:
    class_id = id(executor_class)
    baseline = _BASELINES.get(class_id)
    if baseline:
        return baseline

    pre_execute = getattr(executor_class, "pre_execute", None)
    pre_get_input = getattr(executor_class, "pre_get_input_data", None)

    baseline = {
        "pre_execute": pre_execute,
        "pre_get_input_data": pre_get_input,
    }
    _BASELINES[class_id] = baseline
    return baseline


def _is_conflicting(current: Optional[HookCallable], baseline: Optional[HookCallable]) -> bool:
    if current is None or baseline is None:
        return False
    if current is baseline:
        return False
    if getattr(current, "__aaa_metadata_wrapper__", False):
        return False
    return True


def _extract_prompt_id(prompt_payload: Any) -> str:
    if isinstance(prompt_payload, dict):
        for key in ("prompt_id", "id", "uuid"):
            value = prompt_payload.get(key)
            if value:
                return str(value)
    return f"prompt-{int(time.time() * 1000)}"


def _snapshot_prompt(payload: Any) -> Any:
    try:
        return copy.deepcopy(payload)
    except Exception:
        return payload


def _record_event(session: HookSession, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    event = {
        "type": event_type,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if data:
        event.update(data)
    session.events.append(event)


def _capture_pre_execute(executor: Any, *args: Any, **kwargs: Any) -> None:
    hook_start = time.perf_counter()
    
    prompt_payload = args[0] if args else kwargs.get("prompt")
    prompt_id = _extract_prompt_id(prompt_payload)

    session = HookSession(
        prompt_id=prompt_id,
        prompt_payload=_snapshot_prompt(prompt_payload),
        start_ts=time.time(),
    )
    _record_event(session, "pre_execute", {"executor_id": id(executor)})

    with _LOCK:
        _SESSIONS[prompt_id] = session
        _EXECUTOR_PROMPTS[id(executor)] = prompt_id
    
    # Track performance
    hook_elapsed = time.perf_counter() - hook_start
    session.hook_call_count += 1
    session.hook_total_time += hook_elapsed
    session.hook_max_time = max(session.hook_max_time, hook_elapsed)


def _capture_pre_get_input_data(executor: Any, *args: Any, **kwargs: Any) -> None:
    hook_start = time.perf_counter()
    
    with _LOCK:
        prompt_id = _EXECUTOR_PROMPTS.get(id(executor))
        session = _SESSIONS.get(prompt_id) if prompt_id else None

    if not session:
        return
    
    # Track performance at end of function
    def _track_performance():
        hook_elapsed = time.perf_counter() - hook_start
        session.hook_call_count += 1
        session.hook_total_time += hook_elapsed
        session.hook_max_time = max(session.hook_max_time, hook_elapsed)

    node_id: Optional[str] = None
    if args:
        for value in args:
            if isinstance(value, dict) and "id" in value:
                node_id = str(value.get("id"))
                break
            if isinstance(value, str):
                node_id = value
                break
    if node_id is None:
        candidate = kwargs.get("node") or kwargs.get("node_id") or kwargs.get("key")
        if isinstance(candidate, (str, int)):
            node_id = str(candidate)

    payload_extract = None
    if args:
        for value in reversed(args):
            if isinstance(value, dict):
                payload_extract = value
                break
    if payload_extract is None:
        payload_extract = kwargs.get("inputs")

    safe_payload = None
    if isinstance(payload_extract, dict):
        safe_payload = {}
        for key, value in payload_extract.items():
            if isinstance(value, (str, int, float, bool)):
                safe_payload[key] = value

    _record_event(
        session,
        "pre_get_input_data",
        {
            "node_id": node_id or "unknown",
            "captured_fields": list(safe_payload.keys()) if safe_payload else [],
        },
    )

    if safe_payload:
        with _LOCK:
            session.resolved_inputs.setdefault(node_id or "unknown", {}).update(safe_payload)
    
    # Track performance
    _track_performance()


def _wrap_callback(name: str, original: HookCallable, capture_fn: Callable[..., None]) -> HookCallable:
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            capture_fn(self, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - safety path
            key = f"{name}_error"
            if not _ERROR_SUPPRESSION.get(key):
                _ERROR_SUPPRESSION[key] = True
                _log(f"Error inside {name} hook: {exc}. Auto-disabling hooks.")
            with _LOCK:
                _STATE.auto_disabled = True
            disable_hooks(auto=True)
        return original(self, *args, **kwargs)

    wrapper.__aaa_metadata_wrapper__ = True
    wrapper.__aaa_metadata_original__ = original
    return wrapper


def enable_hooks(*, executor_class: Optional[Type[Any]] = None) -> bool:
    with _LOCK:
        if _STATE.enabled:
            return True

        target_cls = executor_class or _import_prompt_executor()
        if target_cls is None:
            _STATE.disable_reason = "PromptExecutor not available"
            return False

        baseline = _register_baseline(target_cls)
        current_pre_execute = getattr(target_cls, "pre_execute", None)
        current_pre_get = getattr(target_cls, "pre_get_input_data", None)

        if _is_conflicting(current_pre_execute, baseline["pre_execute"]):
            _STATE.conflict_detected = True
            _STATE.disable_reason = "pre_execute already wrapped"
            return False
        if _is_conflicting(current_pre_get, baseline["pre_get_input_data"]):
            _STATE.conflict_detected = True
            _STATE.disable_reason = "pre_get_input_data already wrapped"
            return False

        if baseline["pre_execute"] is None:
            _STATE.disable_reason = "pre_execute missing"
            return False

        wrapped_pre_execute = _wrap_callback("pre_execute", baseline["pre_execute"], _capture_pre_execute)
        setattr(target_cls, "pre_execute", wrapped_pre_execute)
        _ORIGINALS["pre_execute"] = baseline["pre_execute"]

        if baseline["pre_get_input_data"] is not None:
            wrapped_pre_get = _wrap_callback("pre_get_input_data", baseline["pre_get_input_data"], _capture_pre_get_input_data)
            setattr(target_cls, "pre_get_input_data", wrapped_pre_get)
            _ORIGINALS["pre_get_input_data"] = baseline["pre_get_input_data"]

        _STATE.enabled = True
        _STATE.executor_class = target_cls
        _STATE.auto_disabled = False
        _STATE.disable_reason = None
        _STATE.conflict_detected = False
        _log("Runtime hooks enabled")
        return True


def disable_hooks(*, auto: bool = False) -> bool:
    with _LOCK:
        target_cls = _STATE.executor_class
        if not target_cls:
            _STATE.enabled = False
            if auto:
                _STATE.auto_disabled = True
            _SESSIONS.clear()
            _EXECUTOR_PROMPTS.clear()
            return False

        baseline = _register_baseline(target_cls)
        if "pre_execute" in _ORIGINALS and baseline["pre_execute"] is not None:
            setattr(target_cls, "pre_execute", baseline["pre_execute"])
        if "pre_get_input_data" in _ORIGINALS and baseline["pre_get_input_data"] is not None:
            setattr(target_cls, "pre_get_input_data", baseline["pre_get_input_data"])

        _STATE.enabled = False
        _STATE.executor_class = None
        _STATE.auto_disabled = _STATE.auto_disabled or auto
        _STATE.disable_reason = None
        _STATE.conflict_detected = False
        _ORIGINALS.clear()
        _ERROR_SUPPRESSION.clear()
        _SESSIONS.clear()
        _EXECUTOR_PROMPTS.clear()
        _log("Runtime hooks disabled")
        return True


def hooks_enabled() -> bool:
    with _LOCK:
        return _STATE.enabled and not _STATE.auto_disabled


def get_session(prompt_id: str) -> Optional[HookSession]:
    with _LOCK:
        session = _SESSIONS.get(prompt_id)
        return copy.deepcopy(session) if session else None


def consume_session(prompt_id: str) -> Optional[HookSession]:
    with _LOCK:
        session = _SESSIONS.pop(prompt_id, None)
        if session:
            keys_to_remove = [key for key, value in _EXECUTOR_PROMPTS.items() if value == prompt_id]
            for key in keys_to_remove:
                _EXECUTOR_PROMPTS.pop(key, None)
            
            # Log performance metrics if enabled
            _log_performance_metrics(session)
        
        return session


def active_prompt_ids() -> List[str]:
    with _LOCK:
        return list(_SESSIONS.keys())


def auto_enable_from_env(*, executor_class: Optional[Type[Any]] = None) -> None:
    """
    Auto-enable hooks based on configuration.
    
    Priority order:
    1. Environment variable AAA_METADATA_ENABLE_HOOKS
    2. config.json runtime_hooks.enabled setting
    3. Default: disabled
    """
    try:
        from ..utils.config import get_runtime_hooks_enabled
        if get_runtime_hooks_enabled():
            enable_hooks(executor_class=executor_class)
    except Exception as exc:
        # Fallback to environment variable only
        flag = os.environ.get(_ENV_FLAG, "").strip().lower()
        if flag in {"1", "true", "yes", "on"}:
            enable_hooks(executor_class=executor_class)


def _import_prompt_executor() -> Optional[Type[Any]]:
    try:
        from comfy.executor import PromptExecutor  # type: ignore
    except Exception:  # pragma: no cover - not available during tests
        return None
    return PromptExecutor


def reset_state_for_tests() -> None:
    with _LOCK:
        if _STATE.executor_class:
            disable_hooks()
        _SESSIONS.clear()
        _EXECUTOR_PROMPTS.clear()
        _ERROR_SUPPRESSION.clear()
        _STATE.enabled = False
        _STATE.conflict_detected = False
        _STATE.auto_disabled = False
        _STATE.disable_reason = None
        _STATE.executor_class = None


__all__ = [
    "HookSession",
    "enable_hooks",
    "disable_hooks",
    "hooks_enabled",
    "get_session",
    "consume_session",
    "active_prompt_ids",
    "auto_enable_from_env",
    "reset_state_for_tests",
]
