"""
categories.py
One menu tree for the whole pack: everything under "Eric's Nodes/...".

Applied once from the pack's __init__ after all nodes are loaded. Node files are
not edited; saved workflows are not affected (ComfyUI stores node ids, not menu
positions). Switch off with the environment variable AAA_META_KEEP_OLD_CATEGORIES=1.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Dict

ROOT = "Eric's Nodes"

# old category -> place in the tree (categories already under ROOT are kept)
CATEGORY_MAP = {
    "metadata": f"{ROOT}/Metadata",
    "image": f"{ROOT}/Input",
    "image/save": f"{ROOT}/Output",
    "image/text": f"{ROOT}/Text",
    "image/preprocessing": f"{ROOT}/Size & Aspect",
    "Wan 2.2": f"{ROOT}/Size & Aspect",
    "Eric/Images": f"{ROOT}/Files",
    "Eric/Files": f"{ROOT}/Files",
    "Eric/Image Processing": f"{ROOT}/Crop & Compose",
    "Eric/Compose": f"{ROOT}/Crop & Compose",
    "Eric": f"{ROOT}/Tools",
    "colors": f"{ROOT}/Color",
    "ui/color": f"{ROOT}/Color",
    "loaders/checkpoint tester": f"{ROOT}/Loaders/Checkpoint Tester",
    "loaders/lora tester": f"{ROOT}/Loaders/LoRA Tester",
    "loaders/multi-lora": f"{ROOT}/Loaders/Multi-LoRA",
    "loaders/multi-lora/flux": f"{ROOT}/Loaders/Multi-LoRA",
    "loaders/multi-lora/qwen": f"{ROOT}/Loaders/Multi-LoRA",
    "loaders/multi-lora/wan": f"{ROOT}/Loaders/Multi-LoRA",
    "loaders/multi-lora/zimage": f"{ROOT}/Loaders/Multi-LoRA",
}

# nodes whose old category did not say what they are
NODE_OVERRIDES = {
    "QwenAspectRatioHelper": f"{ROOT}/Size & Aspect",
    "QwenAspectRatioHelperAdvanced": f"{ROOT}/Size & Aspect",
    "Wan22AspectRatioHelper": f"{ROOT}/Size & Aspect",
    "Eric_Color_Palette_Analyzer_v3": f"{ROOT}/Color",
    "Eric_Duplicate_Image_Finder_v05": f"{ROOT}/Files",
    "EricSaveQwenLayers": f"{ROOT}/Output",
    "EricSaveQwenLayers_V2": f"{ROOT}/Output",
}


def apply(class_mappings: Dict[str, Any]) -> Dict[str, str]:
    """Returns {node id: new category} for the nodes that moved."""
    if os.environ.get("AAA_META_KEEP_OLD_CATEGORIES", "").strip().lower() in ("1", "true", "yes", "on"):
        return {}
    # decide everything first: classes inherit CATEGORY from each other
    decided: Dict[str, str] = {}
    for node_id, node_class in class_mappings.items():
        current = str(getattr(node_class, "CATEGORY", "") or "")
        target = NODE_OVERRIDES.get(node_id) or CATEGORY_MAP.get(current)
        if target is None:
            target = current if current.startswith(ROOT) else f"{ROOT}/Other"
        decided[node_id] = target
    moved: Dict[str, str] = {}
    for node_id, target in decided.items():
        node_class = class_mappings[node_id]
        if vars(node_class).get("CATEGORY") != target:
            if str(getattr(node_class, "CATEGORY", "")) != target:
                moved[node_id] = target
            node_class.CATEGORY = target
    return moved
