"""
extract_prompt_fixtures.py
Collect a varied sample of embedded ComfyUI prompt graphs from existing PNG
outputs, for use as LOCAL regression fixtures (never committed: they contain
your own prompts).

Usage:
    python tools/extract_prompt_fixtures.py --src <output folder> --dst tests_v2/fixtures_local

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import argparse
import json
import os
import sys
from typing import Dict, List

from PIL import Image


def _newest_pngs(folder: str, per_dir: int, max_files: int) -> List[str]:
    picked: List[str] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d != "AAA_acceptance_set"]
        pngs = [os.path.join(root, f) for f in files if f.lower().endswith(".png")]
        pngs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        picked.extend(pngs[:per_dir])
        if len(picked) >= max_files:
            break
    return picked[:max_files]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--per-dir", type=int, default=2)
    parser.add_argument("--max-files", type=int, default=600)
    parser.add_argument("--max-fixtures", type=int, default=14)
    args = parser.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    seen: Dict[str, str] = {}
    for path in _newest_pngs(args.src, args.per_dir, args.max_files):
        try:
            with Image.open(path) as img:
                raw = img.info.get("prompt")
        except Exception:
            continue
        if not raw:
            continue
        try:
            graph = json.loads(raw)
        except Exception:
            continue
        classes = sorted({str(n.get("class_type")) for n in graph.values() if isinstance(n, dict)})
        signature = "|".join(classes)
        if signature in seen:
            continue
        seen[signature] = path
        index = len(seen)
        out = os.path.join(args.dst, f"fixture_{index:02d}.json")
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"source_image": path, "prompt": graph}, handle, ensure_ascii=False, indent=1)
        print(f"fixture_{index:02d}  nodes={len(graph):3d}  {os.path.basename(path)}")
        print("    " + ", ".join(classes)[:900])
        if len(seen) >= args.max_fixtures:
            break
    print(f"{len(seen)} fixtures written to {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
