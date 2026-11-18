"""
console.py
One switch for what the pack's nodes write to the console.

Node files use it by adding one line after their imports:

    from ..aaa_meta.console import quiet_print as print, note_error as _note_error

After that, every print(...) in the file goes through quiet_print:

  * problems are always shown (the text mentions an error, warning, failure...)
  * a node whose own debug switch is on (debug_logging / debug widget, self.debug)
    prints everything, as before
  * everything else - progress chatter, start-up listings - is shown only in
    verbose mode

Verbose mode: environment variable AAA_META_VERBOSE=1, or console.set_verbose(True).

note_error(error, where) reports an exception that a node deliberately ignores;
shown in verbose mode only.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import builtins
import os
import sys
from typing import Any

_PROBLEM_WORDS = ("error", "warning", "warn:", "failed", "failure", "exception", "traceback", "could not",
                  "couldn't", "cannot", "can't", "unable", "not found", "missing", "invalid", "denied")
_DEBUG_NAMES = ("debug_logging", "debug", "verbose", "debug_mode")
_FRAMES_TO_CHECK = 6
_verbose = os.environ.get("AAA_META_VERBOSE", "").strip().lower() in ("1", "true", "yes", "on")


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = bool(value)


def is_verbose() -> bool:
    return _verbose


def _caller_wants_output(depth: int = 2) -> bool:
    """True when a function up the call chain has its debug switch on."""
    try:
        frame = sys._getframe(depth)
    except ValueError:
        return False
    for _ in range(_FRAMES_TO_CHECK):
        if frame is None:
            break
        local_values = frame.f_locals
        for name in _DEBUG_NAMES:
            if local_values.get(name) is True:
                return True
        owner = local_values.get("self")
        if owner is not None:
            for name in _DEBUG_NAMES:
                if getattr(owner, name, False) is True:
                    return True
        keyword_values = local_values.get("kwargs")
        if isinstance(keyword_values, dict) and any(keyword_values.get(name) is True for name in _DEBUG_NAMES):
            return True
        frame = frame.f_back
    return False


def quiet_print(*values: Any, **options: Any) -> None:
    if not _verbose:
        target = options.get("file")
        if target is None or target is sys.stdout:
            text = " ".join(str(value) for value in values).lower()
            if not any(word in text for word in _PROBLEM_WORDS) and not _caller_wants_output():
                return
    builtins.print(*values, **options)


def note_error(error: BaseException, where: str = "") -> None:
    """An exception a node chose to ignore. Reported in verbose mode or when the node's debug switch is on."""
    if _verbose or _caller_wants_output():
        builtins.print(f"[AAA Metadata] ignored {type(error).__name__} in {where}: {error}")
