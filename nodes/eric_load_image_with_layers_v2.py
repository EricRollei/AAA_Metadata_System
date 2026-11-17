"""
eric_load_image_with_layers_v2.py
Eric Load Image with Layers v2

Same widgets and the same first five outputs as "Eric Load Image with Layers".
Added:
  * the layer modes (all_layers, visible_only, layer_by_name, layer_by_index) also
    work on TIFF files that carry Photoshop layers - written by Photoshop or by
    "Metadata Save Image v1.0". Each layer comes back at full canvas size, at the
    file's bit depth, its transparency as the mask.
  * five more outputs at the end with what the v2 save node stored in the file:
    prompt, negative_prompt, record_json, measurements_json, metadata_summary

PSD files and the composite mode behave as before.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os

import folder_paths
import numpy as np
import torch

from .eric_load_image_with_layers import EricLoadImageWithLayers as _Previous
from ..aaa_meta import psd_writer
from ..aaa_meta.load_support import METADATA_OUTPUT_NAMES, METADATA_OUTPUT_TYPES, metadata_outputs, select_layers


class EricLoadImageWithLayersV2(_Previous):
    CATEGORY = "image"
    RETURN_TYPES = tuple(_Previous.RETURN_TYPES) + METADATA_OUTPUT_TYPES
    RETURN_NAMES = tuple(_Previous.RETURN_NAMES) + METADATA_OUTPUT_NAMES
    FUNCTION = "load_image"

    def _load_tiff_layers(self, image_path, filename, load_mode, layer_name, layer_index):
        layers = psd_writer.read_tiff_layers(image_path)
        if not layers:
            return None
        names = [layer["name"] for layer in layers]
        info = " | ".join(["Format: TIFF (Photoshop layers)", f"Mode: {load_mode}", f"Total Layers: {len(layers)}",
                           "Layer Names: " + ", ".join(names[:5]) + ("..." if len(names) > 5 else "")])
        chosen, note = select_layers(layers, load_mode, layer_name, layer_index)
        if not chosen:
            return None, f"{info} | {note}" if note else info       # composite, with the note
        images = torch.from_numpy(np.stack([layer["pixels"][..., :3] for layer in chosen]).astype(np.float32))
        masks = 1.0 - torch.from_numpy(np.stack([layer["pixels"][..., 3] for layer in chosen]).astype(np.float32))
        return (images, masks, filename, image_path, f"{info} | {note}" if note else info), None

    def load_image(self, image, load_mode="composite", layer_name="", layer_index=0):
        image_path = folder_paths.get_annotated_filepath(image)
        filename = os.path.basename(image_path)
        outputs = None
        note = None
        if os.path.splitext(filename)[1].lower() in (".tif", ".tiff") and load_mode != "composite":
            try:
                found = self._load_tiff_layers(image_path, filename, load_mode, layer_name, layer_index)
                if found is not None:
                    outputs, note = found
            except Exception as exc:
                print(f"[EricLoadImageWithLayersV2] TIFF layers not read ({exc!r}); loading as before")
        if outputs is None:
            outputs = list(super().load_image(image, load_mode=load_mode, layer_name=layer_name,
                                              layer_index=layer_index))
            if note:
                outputs[4] = note
        return tuple(outputs) + metadata_outputs(image_path)


NODE_CLASS_MAPPINGS = {"EricLoadImageWithLayers_V2": EricLoadImageWithLayersV2}
NODE_DISPLAY_NAME_MAPPINGS = {"EricLoadImageWithLayers_V2": "🎨 Eric Load Image with Layers v2"}
