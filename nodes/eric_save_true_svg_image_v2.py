"""
eric_save_true_svg_image_v2.py
Eric Save True SVG Image v2

Same widgets as "Eric Save True SVG Image (with Metadata)". What changed:

  * The drawing is no longer re-written when metadata is added. The earlier
    version parsed and re-serialised the whole SVG, which re-indented <text>
    elements (changing word spacing), dropped comments, renamed namespace
    prefixes, and produced an unreadable file when a custom_metadata key was not
    a valid XML name. Now a <metadata> block is inserted as text and the rest
    of the file stays byte for byte as it came in.
  * The metadata is a standard XMP packet (title, description, keywords,
    creator, copyright, project, custom values) that exiftool and XnView read,
    plus the automatically collected generation record when the SVG comes out
    of a generation workflow.
  * The .xmp sidecar (save_xmp) holds the same packet.
  * Second output "summary".

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from .eric_save_true_svg_image import EricSaveTrueSVGImage as _Previous
from ..aaa_meta import svg_meta
from ..aaa_meta.fields import build_standard_fields
from ..aaa_meta.legacy_bridge import user_fields_from_widgets
from ..aaa_meta.record import GenerationRecord
from ..aaa_meta.runtime import record_for_node
from ..aaa_meta.xmp_packet import build_packet


class EricSaveTrueSVGImageV2(_Previous):
    @classmethod
    def INPUT_TYPES(cls):
        types = super().INPUT_TYPES()
        hidden = dict(types.get("hidden", {}))
        hidden["dynprompt"] = "DYNPROMPT"
        types["hidden"] = hidden
        return types

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("saved_path", "summary")
    FUNCTION = "save_svg_with_metadata"
    OUTPUT_NODE = True
    CATEGORY = "Eric's Nodes/Output"

    def __init__(self):
        super().__init__()
        self._v2_packet = None
        self._v2_notes = []

    def add_metadata_to_svg(self, svg_content, metadata, workflow_info=None):
        if self._v2_packet is None:
            return svg_content
        updated, done = svg_meta.embed_xmp(svg_content, self._v2_packet)
        if not done:
            self._v2_notes.append("no <svg> element found - metadata not embedded, drawing saved unchanged")
        return updated

    def _save_xmp_sidecar(self, xmp_path, metadata, workflow_info=None):
        if self._v2_packet is None:
            return super()._save_xmp_sidecar(xmp_path, metadata, workflow_info)
        with open(xmp_path, "wb") as handle:
            handle.write(self._v2_packet)

    def save_svg_with_metadata(self, svg_content, filename_prefix="wordcloud_svg", prompt=None, extra_pnginfo=None,
                               unique_id=None, dynprompt=None, **kwargs):
        self._v2_notes = []
        self._v2_packet = None
        record = None
        if kwargs.get("enable_metadata", True):
            try:
                candidate = record_for_node(unique_id, prompt, dynprompt, "cached")
                if candidate.positive or candidate.positive_source or candidate.passes:
                    record = candidate
            except Exception as exc:
                self._v2_notes.append(f"automatic collection failed: {exc!r}")
            try:
                user = user_fields_from_widgets(kwargs)
                fields = build_standard_fields(record or GenerationRecord(), user)
                if record is None:
                    fields.digital_source_type = ""          # a drawing, not necessarily AI-generated
                    fields.headline = ""
                    fields.instructions = ""
                self._v2_packet = build_packet(fields, record, project=user.project, custom=user.custom)
            except Exception as exc:
                self._v2_notes.append(f"metadata not built: {exc!r}")
        result = super().save_svg_with_metadata(svg_content, filename_prefix=filename_prefix, prompt=prompt,
                                                extra_pnginfo=extra_pnginfo, unique_id=unique_id, **kwargs)
        saved_path = result[0] if isinstance(result, tuple) and result else ""
        lines = [f"saved: {saved_path}"]
        if self._v2_packet is not None and kwargs.get("save_embedded", True) and not self._v2_notes:
            lines.append("metadata embedded (XMP)" + (" with generation record" if record is not None else ""))
        lines.extend(f"note: {note}" for note in self._v2_notes)
        if record is not None:
            lines.extend(["", record.summary()])
        return (saved_path, "\n".join(lines))


NODE_CLASS_MAPPINGS = {"EricSaveTrueSVGImage_V2": EricSaveTrueSVGImageV2}
NODE_DISPLAY_NAME_MAPPINGS = {"EricSaveTrueSVGImage_V2": "Eric Save True SVG Image v2"}
