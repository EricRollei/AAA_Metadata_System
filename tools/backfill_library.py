"""
backfill_library.py
Makes existing ComfyUI PNGs searchable: reads the workflow each file already
carries, rebuilds the generation record from it (graph only - values that only
existed while the workflow ran, such as LLM-rewritten prompts, cannot be
recovered; the typed prompt is used instead), and writes the catalog fields
and the hcai record into the file. Pixels and the embedded workflow are kept.

DRY RUN BY DEFAULT: nothing is modified unless --write is given.

    python tools/backfill_library.py --folder "A:/path/to/images"              (report only)
    python tools/backfill_library.py --folder "A:/path/to/images" --write      (modify files)

Options: --recursive, --limit N, --force (redo files that already have a v2 record),
         --report <csv path>

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import argparse
import csv
import json
import os
import sys
from typing import Dict, Iterator, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image                                             # noqa: E402

from aaa_meta import PromptGraph, build_record                    # noqa: E402
from aaa_meta.embed import read_xmp                               # noqa: E402
from aaa_meta.writer import update_metadata                       # noqa: E402
from aaa_meta.xmp_packet import read_record_json                  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
_IMAGE_LINK_NAMES = ("images", "image", "source", "input")


def find_save_node(graph: PromptGraph) -> Optional[str]:
    """The node that wrote the file: a save-like node fed by an image link."""
    candidates: List[str] = []
    for node_id in graph.nodes:
        class_low = graph.class_type(node_id).lower()
        if "save" in class_low and any(name in graph.links(node_id) for name in _IMAGE_LINK_NAMES):
            candidates.append(node_id)
    if not candidates:
        return None
    # prefer a real image saver over e.g. "save prompt to database" helpers
    candidates.sort(key=lambda n: (0 if "image" in graph.class_type(n).lower() else 1, n))
    return candidates[0]


def iter_pngs(folder: str, recursive: bool) -> Iterator[str]:
    if recursive:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in sorted(files):
                if name.lower().endswith(".png"):
                    yield os.path.join(root, name)
    else:
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".png"):
                yield os.path.join(folder, name)


def process(path: str, write: bool, force: bool) -> Dict[str, str]:
    row = {"file": path, "status": "", "prompt_chars": "", "prompt_kind": "", "model": "", "loras": "",
           "passes": "", "seed": "", "warnings": ""}
    try:
        with Image.open(path) as image:
            raw = image.info.get("prompt")
            width, height = image.size
    except Exception as exc:
        row["status"] = f"unreadable: {exc!r}"
        return row
    if not raw:
        row["status"] = "no workflow in file"
        return row
    if not force:
        existing = read_xmp(path)
        if existing and read_record_json(existing) is not None:
            row["status"] = "already has a v2 record"
            return row
    try:
        graph = PromptGraph.from_prompt(json.loads(raw))
    except Exception as exc:
        row["status"] = f"workflow not parseable: {exc!r}"
        return row
    anchor = find_save_node(graph)
    if anchor is None:
        row["status"] = "no save node found in workflow"
        return row
    record = build_record(graph, anchor)
    record.width, record.height = width, height
    text = record.positive or record.positive_source
    row.update({
        "prompt_chars": str(len(text)),
        "prompt_kind": "final" if record.positive else ("typed (rewritten later)" if record.positive_source else "none"),
        "model": record.base_models[0].stem if record.base_models else "",
        "loras": str(len(record.loras)),
        "passes": str(len(record.passes)),
        "seed": str(record.seed) if record.seed is not None else "",
        "warnings": "; ".join(record.warnings),
    })
    if not write:
        row["status"] = "would write"
        return row
    result = update_metadata(path, record, a1111=False)
    report = result.get("verify", {})
    row["status"] = "written, verified" if (result.get("embedded") and report.get("ok")) else \
        f"WRITE PROBLEM: {result.get('warnings')} {report.get('missing')} {report.get('mismatch')}"
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Add searchable metadata to existing ComfyUI PNGs")
    parser.add_argument("--folder", required=True)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--write", action="store_true", help="modify the files (default: report only)")
    parser.add_argument("--force", action="store_true", help="redo files that already have a v2 record")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    rows: List[Dict[str, str]] = []
    for index, path in enumerate(iter_pngs(args.folder, args.recursive)):
        if args.limit and index >= args.limit:
            break
        rows.append(process(path, args.write, args.force))

    counts: Dict[str, int] = {}
    for row in rows:
        key = row["status"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    kinds: Dict[str, int] = {}
    for row in rows:
        if row["prompt_kind"]:
            kinds[row["prompt_kind"]] = kinds.get(row["prompt_kind"], 0) + 1
    print(f"{len(rows)} PNG files in {args.folder}  ({'WRITE' if args.write else 'dry run, nothing modified'})")
    for key, value in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {value:6d}  {key}")
    print("prompt recovered:", ", ".join(f"{v} {k}" for k, v in kinds.items()) or "n/a")
    with_model = sum(1 for row in rows if row["model"])
    print(f"model found in {with_model} files, sampler pass found in {sum(1 for r in rows if r['passes'] not in ('', '0'))}")

    if args.report and rows:
        with open(args.report, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
