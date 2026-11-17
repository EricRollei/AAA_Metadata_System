"""
service_mirror.py
Every analysis node written against the old system does

    from AAA_Metadata_System import MetadataService
    service.write_metadata(path, {"analysis": {...}}, targets=[...])

install() wraps that one method so the measured data ALSO lands in the eiqa
namespace the v2 tools read (embedded and / or sidecar, matching the targets
the node asked for). The old write still happens first, unchanged. Nothing in
the analysis packs needs editing.

Disable with the environment variable AAA_META_MIRROR=0.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import contextlib
import functools
import os
import threading
from typing import Any

_MARK = "_aaa_meta_mirrored"
_local = threading.local()


@contextlib.contextmanager
def suppressed():
    """Used by the v2 bridges, which write the v2 data themselves."""
    previous = getattr(_local, "off", False)
    _local.off = True
    try:
        yield
    finally:
        _local.off = previous


def _wanted(filepath: Any, metadata: Any) -> bool:
    return (not getattr(_local, "off", False) and isinstance(metadata, dict)
            and isinstance(metadata.get("analysis"), dict) and bool(metadata.get("analysis"))
            and isinstance(filepath, str) and os.path.isfile(filepath))


def _snapshot(filepath: Any, metadata: Any, targets: Any) -> Any:
    """Text fields as they are before the old writer runs (it garbles an existing description)."""
    try:
        if _wanted(filepath, metadata):
            from .writer import snapshot_standard
            return snapshot_standard(filepath)
    except Exception:
        pass
    return None


def _mirror(filepath: str, metadata: Any, targets: Any, saved: Any = None) -> None:
    if not _wanted(filepath, metadata):
        return
    analysis = metadata["analysis"]
    targets = list(targets) if targets is not None else ["embedded", "xmp"]
    embedded = "embedded" in targets and not filepath.lower().endswith(".svg")
    sidecar = "xmp" in targets
    if not (embedded or sidecar):
        return
    from .writer import patch_metadata
    patch_metadata(filepath, None, None, analysis, embedded=embedded, sidecar=sidecar, strip_iim=embedded,
                   restore=saved)


def install(service_class: Any) -> bool:
    if os.environ.get("AAA_META_MIRROR", "1").strip().lower() in ("0", "false", "off", "no"):
        return False
    original = getattr(service_class, "write_metadata", None)
    if original is None or getattr(original, _MARK, False):
        return False

    @functools.wraps(original)
    def write_metadata(self, filepath, metadata, targets=None, *args, **kwargs):
        saved = _snapshot(filepath, metadata, targets)
        result = original(self, filepath, metadata, targets, *args, **kwargs)
        try:
            _mirror(filepath, metadata, targets, saved)
        except Exception as exc:                              # never break the node that called us
            print(f"[AAA Metadata] v2 mirror of measurements failed for {filepath}: {exc!r}")
        return result

    setattr(write_metadata, _MARK, True)
    service_class.write_metadata = write_metadata
    return True
