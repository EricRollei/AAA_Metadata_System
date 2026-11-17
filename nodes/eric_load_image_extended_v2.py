"""
eric_load_image_extended_v2.py
Eric Load Image Extended v2

Same widgets and the same first six outputs as "Eric Load Image Extended".
Added:
  * five more outputs at the end with what the v2 save node stored in the file:
    prompt, negative_prompt, record_json (full generation record), measurements_json,
    metadata_summary
  * 16-bit PNG and TIFF files are loaded at full precision (the earlier version
    went through 8-bit)

With original_path set, the metadata is read from that file (the image itself
still comes from the ComfyUI input folder, as before).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os

import folder_paths
import torch

from .eric_load_image_extended import EricLoadImageExtended as _Previous
from ..aaa_meta.load_support import METADATA_OUTPUT_NAMES, METADATA_OUTPUT_TYPES, load_full_depth, metadata_outputs


class EricLoadImageExtendedV2(_Previous):
    CATEGORY = "image"
    RETURN_TYPES = tuple(_Previous.RETURN_TYPES) + METADATA_OUTPUT_TYPES
    RETURN_NAMES = tuple(_Previous.RETURN_NAMES) + METADATA_OUTPUT_NAMES
    FUNCTION = "load_image"

    def load_image(self, image, original_path=None):
        outputs = list(super().load_image(image, original_path=original_path))
        image_path = folder_paths.get_annotated_filepath(image)
        try:
            full = load_full_depth(image_path)
            if full is not None and torch.is_tensor(outputs[0]) and outputs[0].shape[0] == 1 \
                    and tuple(outputs[0].shape[1:3]) == full[0].shape[:2]:
                outputs[0] = torch.from_numpy(full[0])[None,]
                if full[1] is not None:
                    outputs[1] = (1.0 - torch.from_numpy(full[1]))[None,]
        except Exception as exc:
            print(f"[EricLoadImageExtendedV2] full-depth load skipped: {exc!r}")
        source = str(original_path).strip() if original_path is not None and str(original_path).strip() else ""
        metadata_path = source if source and os.path.isfile(source) else image_path
        return tuple(outputs) + metadata_outputs(metadata_path)


NODE_CLASS_MAPPINGS = {"EricLoadImageExtended_V2": EricLoadImageExtendedV2}
NODE_DISPLAY_NAME_MAPPINGS = {"EricLoadImageExtended_V2": "📁 Eric Load Image Extended v2"}
