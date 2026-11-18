"""
deprecation.py
Marks nodes that have a newer version: " (deprecated)" after the display name
and the category "Eric's Nodes/Deprecated". Nothing is removed - saved
workflows keep loading and the old nodes stay usable from that category.

Only applied when the newer node actually loaded. Switch off with the
environment variable AAA_META_KEEP_OLD_LABELS=1.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Dict, List

DEPRECATED_CATEGORY = "Eric's Nodes/Deprecated"
SUFFIX = " (deprecated)"

# old node id -> the node that replaces it
SUPERSEDED = {
    "MetadataAwareSaveImage_v099d": "AAA_SaveImageAll",
    "MetadataAwareSaveImage_v100": "AAA_SaveImageAll",          # its first, unpublished id
    "Eric_Metadata_Entry_V2": "Eric_Metadata_Entry_V3",
    "Eric_Metadata_Query_V3": "Eric_Metadata_Query_V4",
    "Eric_Metadata_Filter_V2": "Eric_Metadata_Filter_V3",
    "EnhancedMetadataFilterNode_V2": "EnhancedMetadataFilterNode_V3",
    "Eric_Metadata_Debugger_V2": "Eric_Metadata_Debugger_V3",
    "MetadataConsolidatorNode_V2": "MetadataConsolidatorNode_V3",
    "EricLoadImageExtended": "EricLoadImageExtended_V2",
    "EricLoadImageWithLayers": "EricLoadImageWithLayers_V2",
    "EricSaveTrueSVGImage": "EricSaveTrueSVGImage_V2",
    "EricSaveQwenLayers": "EricSaveQwenLayers_V2",
    "PngMetadataExtractorV3": "PngMetadataExtractorV4",
    "PngInfoDiagnosticV3": "PngInfoDiagnosticV4",
    "SplitWorkflowExtractorNode_V2": "SplitWorkflowExtractorNode_V3",
    "Eric_Workflow_Toolkit_v2": "Eric_Workflow_Toolkit_v3",
    "EricCivitaiPromptExtractor": "EricCivitaiPromptExtractor_V2",
    "EricCivitaiPromptExtractorAutoLoader": "EricCivitaiPromptExtractorAutoLoader_V2",
    "FileOrganizer": "FileOrganizerV2",
}


def apply(class_mappings: Dict[str, Any], display_names: Dict[str, str]) -> List[str]:
    if os.environ.get("AAA_META_KEEP_OLD_LABELS", "").strip().lower() in ("1", "true", "yes", "on"):
        return []
    pairs = [(old, new) for old, new in SUPERSEDED.items() if old in class_mappings and new in class_mappings]
    # The new nodes are subclasses of the old ones: give each its own category first,
    # so moving the old class does not drag the new one along.
    for _old, new in pairs:
        new_class = class_mappings[new]
        if "CATEGORY" not in vars(new_class):
            new_class.CATEGORY = getattr(new_class, "CATEGORY", "Eric's Nodes")
    marked: List[str] = []
    for old, _new in pairs:
        class_mappings[old].CATEGORY = DEPRECATED_CATEGORY
        name = display_names.get(old, old)
        if not name.endswith(SUFFIX):
            display_names[old] = name + SUFFIX
        marked.append(old)
    return marked
