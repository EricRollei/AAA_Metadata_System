"""
eric_generation_record_v1.py
Generation Record (debug) v1 - shows what the v2 capture core collects for the
image passing through it. Wire it between your VAE decode and any save or
preview node; it passes the image through unchanged.

Outputs:
    images       the input images, untouched
    record_json  the full generation record as JSON
    summary      a readable summary (also shown on the node)

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json

from ..aaa_meta import shared
from ..aaa_meta.runtime import record_for_node


class EricGenerationRecordV1:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Images to describe. Passed through unchanged."}),
                "hash_models": (["cached", "off", "compute"], {
                    "default": "cached",
                    "tooltip": "cached: use hashes already known. compute: hash unknown model files "
                               "(slow the first time for large models). off: no hashes.",
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "record_json", "summary")
    FUNCTION = "describe"
    CATEGORY = "Eric's Nodes/Metadata"
    OUTPUT_NODE = True
    DESCRIPTION = "Shows the automatically collected generation record for the images passing through."

    def describe(self, images, hash_models="cached", prompt=None, dynprompt=None, unique_id=None):
        record = record_for_node(unique_id, prompt, dynprompt, hash_models)
        if record.width is None and hasattr(images, "shape") and len(images.shape) == 4:
            record.height, record.width = int(images.shape[1]), int(images.shape[2])
        stats = shared.state().stats
        summary = record.summary()
        summary += f"\n(capture stats: {stats['exec_calls']} node runs, {stats['file_lookups']} file lookups, {stats['errors']} errors)"
        if stats["last_error"]:
            summary += f"\nlast capture error: {stats['last_error']}"
        record_json = json.dumps(record.to_dict(), ensure_ascii=False, indent=2)
        return {"ui": {"text": [summary]}, "result": (images, record_json, summary)}


NODE_CLASS_MAPPINGS = {"Eric_Generation_Record_V1": EricGenerationRecordV1}
NODE_DISPLAY_NAME_MAPPINGS = {"Eric_Generation_Record_V1": "Generation Record (debug) v1"}
