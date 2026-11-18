"""
eric_save_qwen_layers_v2.py
Save Qwen Layers v2

Same widgets and first three outputs as "Save Qwen Layers" (the node that writes
a layer stack - e.g. from Qwen-Image-Layered - as PSD, TIFF, PNG sequence or ZIP).
The earlier version stored no generation data at all. Added:

  * PSD and TIFF: the automatically collected generation record, written to the
    fields Lightroom / XnView / Capture One search (prompt, model and LoRA
    keywords, settings) and to the hcai namespace
  * TIFF: besides the pages written before, the layer stack in the form
    Photoshop reads (names, blend modes, opacity, visibility)
  * one new widget at the end, embed_metadata (on), and a fourth output "summary"

PNG sequence and ZIP are written as before (several files; nothing embedded).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os

import numpy as np

from .eric_save_qwen_layers import EricSaveQwenLayers as _Previous
from ..aaa_meta import embed, psd_writer
from ..aaa_meta.runtime import record_for_node
from ..aaa_meta.writer import update_metadata


class EricSaveQwenLayersV2(_Previous):
    @classmethod
    def INPUT_TYPES(cls):
        types = super().INPUT_TYPES()
        optional = dict(types.get("optional", {}))
        optional["embed_metadata"] = ("BOOLEAN", {
            "default": True,
            "tooltip": "PSD / TIFF: store the automatically collected generation data (prompt, models, settings) "
                       "in the file; TIFF also gets Photoshop-readable layers."})
        types["optional"] = optional
        hidden = dict(types.get("hidden", {}))
        hidden.update({"prompt": "PROMPT", "unique_id": "UNIQUE_ID", "dynprompt": "DYNPROMPT"})
        types["hidden"] = hidden
        return types

    RETURN_TYPES = tuple(_Previous.RETURN_TYPES) + ("STRING",)
    RETURN_NAMES = tuple(_Previous.RETURN_NAMES) + ("summary",)
    FUNCTION = "save_layers"
    OUTPUT_NODE = True
    CATEGORY = "Eric's Nodes/Output"

    def __init__(self):
        super().__init__()
        self._v2_stack = None

    def _generate_layer_preview(self, layers, names, blend_modes, opacities, visibility, width, height):
        # the final layer order and settings, as the old node worked them out
        self._v2_stack = (list(layers), list(names), list(blend_modes), list(opacities), list(visibility))
        return super()._generate_layer_preview(layers, names, blend_modes, opacities, visibility, width, height)

    def _add_photoshop_layers(self, path):
        layers, names, blend_modes, opacities, visibility = self._v2_stack
        stack = [{"name": str(name), "pixels": np.asarray(layer.convert("RGBA"), dtype=np.float32) / 255.0,
                  "blend": str(blend), "opacity": int(opacity), "visible": bool(visible)}
                 for layer, name, blend, opacity, visible in zip(layers, names, blend_modes, opacities, visibility)]
        with open(path, "rb") as handle:
            byte_order = "<" if handle.read(2) == b"II" else ">"
        block = psd_writer.photoshop_tiff_block(stack, 8, byte_order)
        return embed.write_binary_tag(path, "IFD0:ImageSourceData", block)

    def save_layers(self, layers, filename_prefix, file_format, *args, embed_metadata=True, prompt=None,
                    unique_id=None, dynprompt=None, **kwargs):
        self._v2_stack = None
        output = super().save_layers(layers, filename_prefix, file_format, *args, **kwargs)
        path = output[0] if isinstance(output, tuple) and output else ""
        lines = [f"saved: {path}"]
        extension = os.path.splitext(str(path))[1].lower()
        if not embed_metadata:
            lines.append("metadata not embedded (embed_metadata is off)")
        elif extension not in (".psd", ".tif", ".tiff") or not os.path.isfile(str(path)):
            lines.append("metadata not embedded (only PSD and TIFF hold it; PNG sequence / ZIP are several files)")
        else:
            if extension != ".psd" and self._v2_stack:
                try:
                    done, message = self._add_photoshop_layers(path)
                    lines.append("Photoshop layers added to the TIFF" if done else f"note: Photoshop layers not added: {message}")
                except Exception as exc:
                    lines.append(f"note: Photoshop layers not added: {exc!r}")
            try:
                record = record_for_node(unique_id, prompt, dynprompt, "cached")
                if hasattr(layers, "shape") and len(layers.shape) == 4:
                    record.height, record.width = int(layers.shape[1]), int(layers.shape[2])
                result = update_metadata(path, record, strip_iim=True)
                report = result.get("verify") or {}
                lines.append("metadata verified" if result.get("embedded") and report.get("ok")
                             else f"note: metadata problem: {result.get('warnings')} {report.get('missing')}")
                lines.extend(["", record.summary()])
            except Exception as exc:
                lines.append(f"note: metadata not written: {exc!r}")
        return tuple(output) + ("\n".join(lines),)


NODE_CLASS_MAPPINGS = {"EricSaveQwenLayers_V2": EricSaveQwenLayersV2}
NODE_DISPLAY_NAME_MAPPINGS = {"EricSaveQwenLayers_V2": "🎨 Save Qwen Layers v2"}
