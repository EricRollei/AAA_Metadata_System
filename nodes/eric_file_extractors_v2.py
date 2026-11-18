"""
eric_file_extractors_v2.py
New versions of the nodes that read generation data out of image files:

    PNG Metadata Extractor V4            (was V3)
    PNG Info Diagnostic V4               (was V3)
    Split Workflow Extractor V3          (was V2)
    Eric's Workflow Toolkit v3           (was v2)
    Eric Civitai Prompt Extractor v2     (and "+ Auto LoRA Loader v2")

Same widgets and outputs as the versions before them. Each one now asks first
for the generation record the v2 save node stored in the file; for older PNGs
it is rebuilt from the workflow inside the file by following the connections
back from the save node (which tells positive from negative prompt and reads
custom sampler nodes). What the previous version extracted is still returned;
the record is added to it.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import json
import os

from .Eric_png_metadata_extractor_node_v3 import PngMetadataExtractorNodeV3 as _PngExtractorV3
from .eric_png_info_diagnostic_node_v3 import PngInfoDiagnosticNode_V3 as _PngDiagnosticV3
from .eric_split_workflow_extractor_node_V2 import SplitWorkflowExtractorNode_V2 as _SplitExtractorV2
from .eric_workflow_toolkit_v2 import WorkflowToolkitNode as _WorkflowToolkitV2
from .eric_civitai_prompt_extractor_node import EricCivitaiPromptExtractor as _CivitaiV1
from .eric_civitai_prompt_extractor_node import EricCivitaiPromptExtractorAutoLoader as _CivitaiAutoV1
from ..aaa_meta.load_support import file_generation


def _clean_path(value) -> str:
    return str(value or "").strip().strip('"')


class PngMetadataExtractorNodeV4(_PngExtractorV3):
    CATEGORY = "Eric's Nodes/Metadata"

    def extract_metadata(self, input_filepath, extraction_mode="all", key_filter="", debug_logging=False):
        metadata, json_text, summary = super().extract_metadata(input_filepath, extraction_mode, key_filter, debug_logging)
        found = file_generation(_clean_path(input_filepath))
        if not found["record"] and not found["analysis"]:
            return (metadata, json_text, summary)
        filters = [part.strip().lower() for part in str(key_filter or "").split(",") if part.strip()]
        additions = {"generation_record": found["record"], "generation_source": found["origin"],
                     "measurements": found["analysis"]}
        if filters:
            additions = {key: value for key, value in additions.items() if any(part in key for part in filters)}
        additions = {key: value for key, value in additions.items() if value}
        if additions and isinstance(metadata, dict):
            metadata = {**metadata, **additions}
            json_text = json.dumps(metadata, indent=2, ensure_ascii=False, default=str)
        return (metadata, json_text, (summary + "\n\n" if summary else "") + found["summary"])


class PngInfoDiagnosticNodeV4(_PngDiagnosticV3):
    CATEGORY = "Eric's Nodes/Tools"

    def diagnose_png(self, input_filepath, output_mode="summary", include_workflow=True, include_sidecar=True,
                     debug_logging=False):
        info, filename, metadata = super().diagnose_png(input_filepath, output_mode, include_workflow,
                                                        include_sidecar, debug_logging)
        path = _clean_path(input_filepath)
        found = file_generation(path)
        if not found["record"] and not found["analysis"]:
            return (info, filename, metadata)
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata["generation_record"] = found["record"]
        metadata["generation_source"] = found["origin"]
        if found["analysis"]:
            metadata["measurements"] = found["analysis"]
        if str(info).startswith("File is not a PNG"):
            # the stored record is readable from JPEG / TIFF / WebP / PSD as well
            info = f"{os.path.basename(path)} (not a PNG - showing the stored record only)"
        if output_mode != "summary" and str(info).lstrip().startswith("{"):
            info = json.dumps(metadata, indent=2, ensure_ascii=False, default=str)
        else:
            info = f"{info}\n\n{found['summary']}"
        return (info, filename or os.path.basename(path), metadata)


class SplitWorkflowExtractorNodeV3(_SplitExtractorV2):
    CATEGORY = "Eric's Nodes/Metadata"

    def extract_workflow(self, image, input_filepath, write_to_xmp=True, embed_metadata=True, write_text_file=False,
                         write_to_database=False, overwrite_existing=False, debug_logging=False):
        output = super().extract_workflow(image, input_filepath, write_to_xmp, embed_metadata, write_text_file,
                                          write_to_database, overwrite_existing, debug_logging)
        found = file_generation(_clean_path(input_filepath))
        if not found["summary"]:
            return output
        return (output[0], f"{found['summary']}\n\n{output[1]}", output[2])


class WorkflowToolkitNodeV3(_WorkflowToolkitV2):
    CATEGORY = "Eric's Nodes/Workflow"

    def process_workflow(self, input_filepath, operation_mode, *args, **kwargs):
        result, workflow_data, analysis, image = super().process_workflow(input_filepath, operation_mode, *args, **kwargs)
        found = file_generation(_clean_path(input_filepath))
        if not found["record"] and not found["analysis"]:
            return (result, workflow_data, analysis, image)
        analysis = dict(analysis) if isinstance(analysis, dict) else {}
        analysis["generation_record"] = found["record"]
        analysis["generation_source"] = found["origin"]
        if found["analysis"]:
            analysis["measurements"] = found["analysis"]
        return (f"{result}\n\n{found['summary']}", workflow_data, analysis, image)


def _with_record(outputs, offset):
    """Civitai extractor outputs with the stored / rebuilt record filled in.
    outputs[offset + 3] is full_path; prompts and sampler settings follow it."""
    values = list(outputs)
    found = file_generation(_clean_path(values[offset + 3]))
    flat = found["flat"]
    if not flat:
        return tuple(values)
    stored = found["origin"] == "stored"                     # a stored record is exact: it wins

    def pick(index, key, convert=str):
        current = values[index]
        if key in flat and (stored or current in ("", None, 0, 0.0)):
            try:
                values[index] = convert(flat[key])
            except (TypeError, ValueError):
                pass

    pick(offset + 4, "prompt")
    pick(offset + 5, "negative_prompt")
    pick(offset + 6, "sampler")
    pick(offset + 7, "cfg", float)
    pick(offset + 8, "seed", int)
    return tuple(values)


class EricCivitaiPromptExtractorV2(_CivitaiV1):
    CATEGORY = "Eric's Nodes/Metadata"

    def load_and_extract(self, *args, **kwargs):
        return _with_record(super().load_and_extract(*args, **kwargs), 0)


class EricCivitaiPromptExtractorAutoLoaderV2(_CivitaiAutoV1, EricCivitaiPromptExtractorV2):
    # The auto-loader fetches its prompts through load_and_extract of the next class in line,
    # which is the v2 extractor above - so the record reaches its outputs and its LoRA lookup too.
    CATEGORY = "Eric's Nodes/Metadata"


NODE_CLASS_MAPPINGS = {
    "PngMetadataExtractorV4": PngMetadataExtractorNodeV4,
    "PngInfoDiagnosticV4": PngInfoDiagnosticNodeV4,
    "SplitWorkflowExtractorNode_V3": SplitWorkflowExtractorNodeV3,
    "Eric_Workflow_Toolkit_v3": WorkflowToolkitNodeV3,
    "EricCivitaiPromptExtractor_V2": EricCivitaiPromptExtractorV2,
    "EricCivitaiPromptExtractorAutoLoader_V2": EricCivitaiPromptExtractorAutoLoaderV2,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PngMetadataExtractorV4": "PNG Metadata Extractor V4",
    "PngInfoDiagnosticV4": "PNG Info Diagnostic V4",
    "SplitWorkflowExtractorNode_V3": "Split Workflow Extractor V3",
    "Eric_Workflow_Toolkit_v3": "Eric's Workflow Toolkit v3",
    "EricCivitaiPromptExtractor_V2": "Eric Civitai Prompt Extractor v2",
    "EricCivitaiPromptExtractorAutoLoader_V2": "Eric Civitai Prompt Extractor + Auto LoRA Loader v2",
}
