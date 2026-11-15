"""
capture - runtime hooks.

install() is idempotent and never raises: if ComfyUI internals have changed
shape, the affected hook stays off and the builder falls back to static graph
tracing.

Set environment variable AAA_META_CAPTURE=0 to disable all hooks.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Dict


def install(verbose: bool = True) -> Dict[str, bool]:
    result = {"exec_hook": False, "file_loads": False}
    if os.environ.get("AAA_META_CAPTURE", "1").strip().lower() in ("0", "false", "off", "no"):
        if verbose:
            print("[AAA Metadata] runtime capture disabled by AAA_META_CAPTURE")
        return result
    try:
        from . import exec_hook
        result["exec_hook"] = exec_hook.install()
    except Exception as exc:  # pragma: no cover - safety net
        print(f"[AAA Metadata] execution hook not installed: {exc}")
    try:
        from . import file_loads
        result["file_loads"] = file_loads.install()
    except Exception as exc:  # pragma: no cover - safety net
        print(f"[AAA Metadata] file-load hook not installed: {exc}")
    if verbose:
        print(f"[AAA Metadata] runtime capture: execution={result['exec_hook']} file_loads={result['file_loads']}")
    return result
