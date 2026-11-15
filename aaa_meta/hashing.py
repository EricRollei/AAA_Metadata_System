"""
hashing.py
SHA-256 for model files, with three ways to avoid reading a 20 GB file:
  1. our own cache (path + size + mtime -> hash), a JSON file
  2. a "<file>.sha256" sidecar (written by the old hash utilities and others)
  3. comfyui-lora-manager's "<stem>.metadata.json" (field "sha256")
Only when all three miss, and compute=True, is the file actually hashed.

Civitai's AutoV2 hash is the first 10 hex digits of the SHA-256.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import hashlib
import json
import os
import re
import threading
from typing import Dict, Optional

_HEX64 = re.compile(r"\b[0-9a-fA-F]{64}\b")
_LOCK = threading.RLock()
_CHUNK = 8 * 1024 * 1024


class HashCache:
    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path
        self._data: Dict[str, str] = {}
        self._loaded = False
        self._dirty = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self.cache_path and os.path.isfile(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    self._data = {str(k): str(v) for k, v in data.items()}
            except Exception:
                self._data = {}

    def save(self) -> None:
        if not self._dirty or not self.cache_path:
            return
        with _LOCK:
            try:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                temp_path = self.cache_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as handle:
                    json.dump(self._data, handle, ensure_ascii=False, indent=0)
                os.replace(temp_path, self.cache_path)
                self._dirty = False
            except Exception:
                pass

    @staticmethod
    def _key(path: str) -> Optional[str]:
        try:
            stat = os.stat(path)
        except OSError:
            return None
        return f"{os.path.normcase(os.path.abspath(path))}|{stat.st_size}|{int(stat.st_mtime)}"

    @staticmethod
    def _from_sidecars(path: str) -> Optional[str]:
        stem = os.path.splitext(path)[0]
        for candidate in (path + ".sha256", stem + ".sha256"):
            if os.path.isfile(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8", errors="ignore") as handle:
                        match = _HEX64.search(handle.read(4096))
                    if match:
                        return match.group(0).lower()
                except Exception:
                    pass
        metadata_json = stem + ".metadata.json"
        if os.path.isfile(metadata_json):
            try:
                with open(metadata_json, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                value = data.get("sha256") if isinstance(data, dict) else None
                if isinstance(value, str) and _HEX64.fullmatch(value.strip()):
                    return value.strip().lower()
            except Exception:
                pass
        return None

    def sha256(self, path: Optional[str], compute: bool = True) -> Optional[str]:
        if not path or not os.path.isfile(path):
            return None
        with _LOCK:
            self._load()
            key = self._key(path)
            if key is None:
                return None
            if key in self._data:
                return self._data[key]
            digest = self._from_sidecars(path)
        if digest is None and compute:
            hasher = hashlib.sha256()
            try:
                with open(path, "rb") as handle:
                    while True:
                        block = handle.read(_CHUNK)
                        if not block:
                            break
                        hasher.update(block)
                digest = hasher.hexdigest()
            except OSError:
                return None
        if digest is not None:
            with _LOCK:
                self._data[key] = digest
                self._dirty = True
        return digest
