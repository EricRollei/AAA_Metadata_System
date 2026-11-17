"""
eric_metadata_add_measurements_v1.py
Add Measurements to Image v1

Stores measured data (sharpness, IQA scores, UniPercept results, any numbers or
text) in an image that already exists, in the eiqa namespace. The data is kept
in full and nested as given; earlier measurements in the file stay and new ones
are added beside them. Nothing else in the file is touched.

measurements: JSON text, e.g. {"sharpness": 0.82, "unipercept": {"iaa": 70.5, "note": "soft corners"}}
group_name:   optional - put everything under this name (use it when the JSON
              is a bare number / list / text, or to keep one tool's results together)

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import os

from ..aaa_meta.fields import StandardFields
from ..aaa_meta.writer import patch_metadata


class EricMetadataAddMeasurementsV1:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filepath": ("STRING", {"default": "", "tooltip": "Image file to add the measurements to"}),
                "measurements": ("STRING", {"default": "{}", "multiline": True,
                                            "tooltip": "JSON with the measured values (numbers, text, nested groups)"}),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Passed through unchanged"}),
                "group_name": ("STRING", {"default": "", "tooltip": "Store the measurements under this name"}),
                "rating": (["", "1", "2", "3", "4", "5"], {"default": "", "tooltip": "Star rating (shown by Lightroom, XnView, Capture One)"}),
                "keywords": ("STRING", {"default": "", "tooltip": "Comma-separated keywords to add (e.g. 'sharp, keeper')"}),
                "write_embedded": ("BOOLEAN", {"default": True, "tooltip": "Write into the image file"}),
                "write_sidecar": ("BOOLEAN", {"default": False, "tooltip": "Also write / update the .xmp sidecar"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "filepath", "status")
    FUNCTION = "add_measurements"
    OUTPUT_NODE = True
    CATEGORY = "Eric's Nodes/Metadata"
    DESCRIPTION = "Store measured data (image quality scores etc.) inside an existing image file."

    def add_measurements(self, filepath, measurements, image=None, group_name="", rating="", keywords="",
                         write_embedded=True, write_sidecar=False):
        filepath = str(filepath or "").strip().strip('"')
        if not filepath or not os.path.isfile(filepath):
            return (image, filepath, f"File not found: {filepath!r} - nothing written")
        text = str(measurements or "").strip()
        try:
            data = json.loads(text) if text else {}
        except Exception:
            data = text                                  # plain text is stored as text
        group = str(group_name or "").strip()
        if group:
            analysis = {group: data} if data not in ({}, "", None, []) else {}
        elif isinstance(data, dict):
            analysis = data
        elif data in ("", None, []):
            analysis = {}
        else:
            analysis = {"measurement": data}
        keyword_list = [k.strip() for k in str(keywords or "").split(",") if k.strip()]
        fields = StandardFields(keywords=keyword_list, digital_source_type="") if keyword_list else None
        stars = int(rating) if str(rating).strip() else None
        if not analysis and fields is None and stars is None:
            return (image, filepath, "Nothing to write (no measurements, keywords or rating)")
        if not (write_embedded or write_sidecar):
            return (image, filepath, "Nothing written (both write_embedded and write_sidecar are off)")
        outcome = patch_metadata(filepath, fields, None, analysis or None, rating=stars,
                                 embedded=write_embedded, sidecar=write_sidecar)
        parts = []
        if outcome.get("embedded") is not None:
            parts.append("embedded: ok" if outcome["embedded"] else "embedded: FAILED")
        if outcome.get("sidecar") is not None:
            parts.append("sidecar: ok" if outcome["sidecar"] else "sidecar: FAILED")
        if analysis:
            parts.append("stored: " + ", ".join(list(analysis.keys())[:12]))
        parts.extend(f"note: {w}" for w in outcome.get("warnings", []))
        return (image, filepath, "; ".join(parts))


NODE_CLASS_MAPPINGS = {"Eric_Metadata_Add_Measurements_V1": EricMetadataAddMeasurementsV1}
NODE_DISPLAY_NAME_MAPPINGS = {"Eric_Metadata_Add_Measurements_V1": "Add Measurements to Image v1"}
