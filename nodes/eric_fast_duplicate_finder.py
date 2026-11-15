"""
ComfyUI Node: Fast Duplicate Image Finder
Description:
Streamlined duplicate finder optimized for speed over tens of thousands of files.
Uses dual perceptual hashing (phash + dhash) to find exact duplicates across
folder trees.  No metadata, no XMP, no console output — just fast dedup.

Performance features:
  - Threaded parallel hashing (saturates disk I/O across all cores)
  - JPEG draft decoding (skips full-res decode — imagehash only needs 32×32)
  - Multi-index pigeonhole comparison: near-O(n) instead of O(n²)
  - Integer XOR + popcount for candidate verification
  - Vectorised numpy fallback for low thresholds

Actions:
  - dry_run: Report duplicates without touching files
  - move:    Keep largest file in place; move smaller duplicates plus a
             _kept reference copy into  <root>/duplicates/group_NNNN/
  - delete:  Permanently remove duplicates (keeps largest)

Author: Eric Hiss (GitHub: EricRollei)
Version: 1.1.0
Date: March 2026
License: Dual License (Non-Commercial and Commercial Use)
"""

import os
import json
import time
import shutil
import multiprocessing
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

try:
    import imagehash
except ImportError:
    imagehash = None

# Supported image extensions
_IMAGE_EXTS = frozenset(('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif', '.gif'))


# ---- module-level worker (needed for ThreadPoolExecutor.map) ---------- #
def _hash_single_image(path):
    """Hash one image file (phash + dhash).  Returns dict or None."""
    try:
        size = os.path.getsize(path)
        img = Image.open(path)
        # JPEG speed-up: tell the decoder to do a reduced-resolution IDCT.
        # imagehash only needs 32×32, so 256×256 is more than enough.
        if img.format == 'JPEG':
            try:
                img.draft('RGB', (256, 256))
            except Exception:
                pass
        img.load()
        ph = int(str(imagehash.phash(img)), 16)
        dh = int(str(imagehash.dhash(img)), 16)
        return {"path": path, "size": size, "phash": ph, "dhash": dh}
    except Exception:
        return None


class FastDuplicateFinder:
    """Ultra-fast duplicate finder using dual perceptual hashing with
    multi-index candidate selection and threaded I/O."""

    @classmethod
    def INPUT_TYPES(cls):
        cpu = multiprocessing.cpu_count()
        return {
            "required": {
                "folder_path": ("STRING", {
                    "default": "",
                    "tooltip": "Root folder to scan (all subfolders included)."
                }),
                "threshold": ("FLOAT", {
                    "default": 0.97,
                    "min": 0.80,
                    "max": 1.0,
                    "step": 0.005,
                    "tooltip": "Combined similarity (70 % phash + 30 % dhash). 0.97 = strict exact match."
                }),
                "action": (["dry_run", "move", "delete"], {
                    "default": "dry_run",
                    "tooltip": "dry_run = report only; move = relocate duplicates; delete = permanent."
                }),
            },
            "optional": {
                "additional_folders": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "One extra folder path per line",
                    "tooltip": "Additional root folders to include in the scan."
                }),
                "workers": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 32,
                    "step": 1,
                    "tooltip": f"Parallel hashing threads (0 = auto ≈ {max(1, cpu - 1)} on this machine)."
                }),
                "confirm_delete": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Safety lock — must be True to allow the delete action."
                }),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("report", "duplicate_count", "stats_json")
    FUNCTION = "find_duplicates"
    CATEGORY = "Eric/Images"

    # ================================================================== #
    #  Main entry point                                                    #
    # ================================================================== #
    def find_duplicates(self, folder_path, threshold=0.97, action="dry_run",
                        additional_folders="", workers=0, confirm_delete=False):
        if imagehash is None:
            return ("ERROR: pip install imagehash", 0,
                    json.dumps({"error": "imagehash missing"}))
        if action == "delete" and not confirm_delete:
            return ("ERROR: confirm_delete must be True.", 0,
                    json.dumps({"error": "delete not confirmed"}))

        t0 = time.time()

        # --- 1. Collect paths ------------------------------------------------
        folders = [folder_path] + [
            f.strip() for f in additional_folders.splitlines() if f.strip()
        ]
        image_paths = self._collect_images(folders)
        if not image_paths:
            return ("No images found.", 0, json.dumps({"images_found": 0}))
        t1 = time.time()

        # --- 2. Hash (parallel, threaded) ------------------------------------
        if workers <= 0:
            workers = max(1, multiprocessing.cpu_count() - 1)
        records = self._hash_images(image_paths, workers)
        if len(records) < 2:
            return ("Fewer than 2 valid images.", 0,
                    json.dumps({"images_hashed": len(records)}))
        t2 = time.time()

        # --- 3. Find duplicate groups ----------------------------------------
        groups = self._find_groups(records, threshold)
        dup_count = sum(len(g) - 1 for g in groups)
        t3 = time.time()

        # --- 4. Act on groups ------------------------------------------------
        action_stats = {"files_moved": 0, "files_deleted": 0}
        if groups:
            if action == "move":
                action_stats = self._action_move(groups, folder_path)
            elif action == "delete":
                action_stats = self._action_delete(groups)
        t4 = time.time()

        # --- 5. Build report -------------------------------------------------
        stats = {
            "images_scanned": len(image_paths),
            "images_hashed": len(records),
            "duplicate_groups": len(groups),
            "total_duplicates": dup_count,
            "action": action,
            "threshold": threshold,
            "workers": workers,
            "time_collect": round(t1 - t0, 3),
            "time_hash": round(t2 - t1, 3),
            "time_compare": round(t3 - t2, 3),
            "time_action": round(t4 - t3, 3),
            "elapsed_seconds": round(t4 - t0, 2),
            **action_stats,
        }
        return (self._build_report(groups, stats), dup_count,
                json.dumps(stats, indent=2))

    # ================================================================== #
    #  Step 1 — Collect image paths                                        #
    # ================================================================== #
    @staticmethod
    def _collect_images(folders):
        paths = []
        for folder in folders:
            if not os.path.isdir(folder):
                continue
            for root, _, files in os.walk(folder):
                for fname in files:
                    if os.path.splitext(fname)[1].lower() in _IMAGE_EXTS:
                        paths.append(os.path.join(root, fname))
        return paths

    # ================================================================== #
    #  Step 2 — Parallel threaded hashing                                  #
    # ================================================================== #
    @staticmethod
    def _hash_images(image_paths, workers):
        """Hash every image using a thread pool (I/O + C-extension work
        releases the GIL, so threads give near-linear speed-up)."""
        records = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(_hash_single_image, image_paths):
                if result is not None:
                    records.append(result)
        return records

    # ================================================================== #
    #  Step 3 — Duplicate detection  (auto-selects strategy)               #
    # ================================================================== #
    def _find_groups(self, records, threshold):
        """Pick the fastest comparison strategy for the given threshold."""
        n = len(records)
        # Maximum phash bit-diff that can still pass the threshold
        # (worst case: all difference in phash, dhash identical)
        max_ph = int((1.0 - threshold) * 64.0 / 0.7)
        # For tight thresholds on large sets → multi-index  O(n·k)
        if max_ph <= 8 and n > 200:
            return self._groups_indexed(records, threshold, max_ph)
        # Fallback: vectorised brute-force  O(n²)
        return self._groups_brute(records, threshold)

    # ------ Multi-index  (pigeonhole / locality-sensitive) ------------- #
    def _groups_indexed(self, records, threshold, max_ph):
        """Near-O(n) duplicate detection using multi-index hashing.

        Idea:  split each 64-bit phash into (max_ph + 1) chunks.
        By the pigeonhole principle, two hashes that differ in ≤ max_ph
        bits MUST share at least one identical chunk.  We bucket by each
        chunk and only verify pairs that land in the same bucket.
        """
        n = len(records)
        ph = [r["phash"] for r in records]
        dh = [r["dhash"] for r in records]

        num_chunks = max_ph + 1
        chunk_bits = 64 // num_chunks
        extra = 64 % num_chunks          # first 'extra' chunks get +1 bit

        # chunk boundaries: list of (bit_start, width)
        bounds = []
        pos = 0
        for c in range(num_chunks):
            w = chunk_bits + (1 if c < extra else 0)
            bounds.append((pos, w))
            pos += w

        # Build index tables:  chunk_id → chunk_value → [record indices]
        tables = [defaultdict(list) for _ in range(num_chunks)]
        for idx in range(n):
            h = ph[idx]
            for c, (start, width) in enumerate(bounds):
                val = (h >> (64 - start - width)) & ((1 << width) - 1)
                tables[c][val].append(idx)

        # Gather candidate pairs (share at least one identical chunk)
        cands = set()
        for tbl in tables:
            for bucket in tbl.values():
                bl = len(bucket)
                if bl < 2:
                    continue
                cap = min(bl, 500)        # safety cap for pathological buckets
                for a in range(cap):
                    for b in range(a + 1, cap):
                        i, j = bucket[a], bucket[b]
                        cands.add((i, j) if i < j else (j, i))

        # Verify candidates with full dual-hash similarity
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i, j in cands:
            pd = bin(ph[i] ^ ph[j]).count('1')
            dd = bin(dh[i] ^ dh[j]).count('1')
            if 1.0 - (0.7 * pd + 0.3 * dd) / 64.0 >= threshold:
                union(i, j)

        return self._uf_to_groups(records, parent, n)

    # ------ Brute-force vectorised  (numpy) ---------------------------- #
    def _groups_brute(self, records, threshold):
        """O(n²) pairwise comparison using vectorised numpy — used when
        the threshold is too loose for multi-index to be efficient."""
        n = len(records)

        def _int_to_bits(key):
            return np.array(
                [[(r[key] >> (63 - b)) & 1 for b in range(64)]
                 for r in records], dtype=np.uint8)

        ph_m = _int_to_bits("phash")    # (n, 64)
        dh_m = _int_to_bits("dhash")

        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(n - 1):
            pd = np.count_nonzero(ph_m[i] != ph_m[i + 1:], axis=1)
            dd = np.count_nonzero(dh_m[i] != dh_m[i + 1:], axis=1)
            sim = 1.0 - (0.7 * pd + 0.3 * dd) / 64.0
            for m in np.where(sim >= threshold)[0]:
                union(i, i + 1 + int(m))

        return self._uf_to_groups(records, parent, n)

    # ------ Shared: union-find → sorted group list ---------------------- #
    @staticmethod
    def _uf_to_groups(records, parent, n):
        """Collect connected components from a union-find structure."""
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        clusters = defaultdict(list)
        for i in range(n):
            clusters[find(i)].append(records[i])
        groups = [sorted(g, key=lambda r: r["size"], reverse=True)
                  for g in clusters.values() if len(g) > 1]
        groups.sort(key=len, reverse=True)
        return groups

    # ================================================================== #
    #  Step 4a — Move action                                               #
    # ================================================================== #
    def _action_move(self, groups, root_folder):
        """Keep largest in place, move others + a '_kept' reference copy
        into  <root_folder>/duplicates/group_NNNN/"""
        dup_root = os.path.join(root_folder, "duplicates")
        moved = 0

        for idx, group in enumerate(groups, 1):
            kept = group[0]   # largest
            group_dir = os.path.join(dup_root, f"group_{idx:04d}")
            os.makedirs(group_dir, exist_ok=True)

            # Copy reference with '_kept' suffix
            kb, ke = os.path.splitext(os.path.basename(kept["path"]))
            try:
                shutil.copy2(kept["path"],
                             os.path.join(group_dir, f"{kb}_kept{ke}"))
            except Exception:
                pass   # non-fatal

            # Move duplicates
            for dup in group[1:]:
                dest = self._unique_path(
                    os.path.join(group_dir, os.path.basename(dup["path"])))
                try:
                    shutil.move(dup["path"], dest)
                    moved += 1
                except Exception:
                    pass
        return {"files_moved": moved}

    # ================================================================== #
    #  Step 4b — Delete action                                             #
    # ================================================================== #
    @staticmethod
    def _action_delete(groups):
        deleted = 0
        for group in groups:
            for dup in group[1:]:
                try:
                    os.remove(dup["path"])
                    deleted += 1
                except Exception:
                    pass
        return {"files_deleted": deleted}

    # ================================================================== #
    #  Helpers                                                             #
    # ================================================================== #
    @staticmethod
    def _unique_path(path):
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        c = 2
        while True:
            p = f"{base}_{c}{ext}"
            if not os.path.exists(p):
                return p
            c += 1

    @staticmethod
    def _fmt_size(b):
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"

    # ================================================================== #
    #  Report builder                                                      #
    # ================================================================== #
    def _build_report(self, groups, stats):
        lines = [
            "=== Fast Duplicate Finder ===",
            f"Scanned {stats['images_scanned']}  |  Hashed {stats['images_hashed']}  |  "
            f"{stats['elapsed_seconds']}s  "
            f"(hash {stats['time_hash']}s · compare {stats['time_compare']}s)",
            f"Threshold {stats['threshold']}  |  Action: {stats['action']}  |  "
            f"Workers: {stats['workers']}",
            f"Groups: {stats['duplicate_groups']}  |  "
            f"Duplicates: {stats['total_duplicates']}",
        ]
        if stats.get("files_moved"):
            lines.append(f"Files moved: {stats['files_moved']}")
        if stats.get("files_deleted"):
            lines.append(f"Files deleted: {stats['files_deleted']}")

        for i, group in enumerate(groups[:30], 1):
            kept = group[0]
            lines.append(
                f"\nGroup {i} ({len(group)} files)  —  kept: "
                f"{os.path.basename(kept['path'])} ({self._fmt_size(kept['size'])})")
            for dup in group[1:5]:
                lines.append(
                    f"  dup: {os.path.basename(dup['path'])} "
                    f"({self._fmt_size(dup['size'])})")
            if len(group) > 5:
                lines.append(f"  … and {len(group) - 5} more")

        if len(groups) > 30:
            lines.append(f"\n… {len(groups) - 30} more groups not shown")

        return "\n".join(lines)


# ====================================================================== #
#  ComfyUI registration                                                    #
# ====================================================================== #
NODE_CLASS_MAPPINGS = {
    "Eric_Fast_Duplicate_Finder": FastDuplicateFinder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Fast_Duplicate_Finder": "Eric Fast Duplicate Finder ⚡",
}
