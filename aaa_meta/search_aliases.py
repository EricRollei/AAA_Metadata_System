"""
search_aliases.py
Words the node search finds each node by.

ComfyUI's node search looks at a node's id, its display name and its
SEARCH_ALIASES - not at the description. This table gives every current node of
the pack the words people actually type. Superseded ("deprecated") nodes get
none, so a search leads to the current version.

A class that defines SEARCH_ALIASES itself keeps its own list.
AAA_META_NO_SEARCH_ALIASES=1 switches this off.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import os
from typing import Any, Dict, List

_METADATA = ["metadata", "xmp", "exif", "iptc", "sidecar", "lightroom", "capture one", "xnview"]
_LORA = ["lora", "lora loader", "lora stack", "multiple loras", "stack loras", "power lora"]
_LORA_TESTER = ["lora", "lora test", "lora database", "lora notes", "lora rating", "trigger words", "lora manager"]
_CHECKPOINT = ["checkpoint", "model test", "checkpoint notes", "checkpoint database", "model rating", "compare models"]
_ASPECT = ["aspect ratio", "resolution", "image size", "width height", "dimensions", "latent size"]

ALIASES: Dict[str, List[str]] = {
    # --- Output
    "EricSaveTrueSVGImage_V2": ["svg", "save svg", "vector", "vector graphics", "export svg", "svg metadata", "inkscape"],
    "EricSaveQwenLayers_V2": ["layers", "save layers", "psd", "layered tiff", "photoshop", "photoshop layers",
                              "qwen layered", "qwen image layered", "rgba layers"],
    "MetadataAwareSaveImage_Simple": ["save image", "metadata", "xmp", "png", "jpg", "webp", "tiff", "icc",
                                      "color profile", "simple save"],
    # --- Input
    "EricLoadImageExtended_V2": ["load image", "open image", "psd", "tiff", "16-bit", "16 bit", "raw", "load metadata",
                                 "read prompt", "load psd", "load tiff", "image from path"],
    "EricLoadImageWithLayers_V2": ["load image", "layers", "load layers", "psd", "load psd", "layered tiff", "photoshop",
                                   "photoshop layers", "extract layers", "16-bit"],
    # --- Metadata
    "Eric_Metadata_Entry_V3": _METADATA + ["add metadata", "write metadata", "edit metadata", "title", "caption",
                                           "keywords", "copyright", "creator", "tag image"],
    "Eric_Metadata_Query_V4": _METADATA + ["read metadata", "query metadata", "get prompt", "jsonpath", "extract value",
                                           "metadata field"],
    "Eric_Metadata_Filter_V3": _METADATA + ["filter images", "filter by metadata", "search images", "select images",
                                            "find images"],
    "EnhancedMetadataFilterNode_V3": _METADATA + ["filter images", "filter by metadata", "search images", "find images",
                                                  "filter by score", "filter by model"],
    "Eric_Metadata_Debugger_V3": _METADATA + ["debug metadata", "inspect metadata", "show metadata", "view metadata"],
    "MetadataConsolidatorNode_V3": _METADATA + ["merge metadata", "consolidate metadata", "sync sidecar", "combine metadata"],
    "Eric_Metadata_Add_Measurements_V1": _METADATA + ["measurements", "scores", "quality score", "aesthetic score",
                                                      "store scores", "image quality", "iqa", "rating"],
    "Eric_Generation_Record_V1": ["generation record", "generation data", "show prompt", "debug metadata",
                                  "what was used", "models used", "capture", "metadata"],
    "PngMetadataExtractorV4": ["png info", "read prompt", "extract prompt", "extract metadata", "image info",
                               "generation parameters", "a1111", "civitai", "metadata"],
    "SplitWorkflowExtractorNode_V3": ["workflow", "extract workflow", "workflow from image", "read workflow", "split workflow",
                                      "metadata"],
    "EricCivitaiPromptExtractor_V2": ["civitai", "extract prompt", "read prompt", "prompt from image", "generation parameters",
                                      "a1111", "metadata"],
    "EricCivitaiPromptExtractorAutoLoader_V2": ["civitai", "extract prompt", "prompt from image", "auto lora", "load loras from image",
                                                "recreate image", "lora"],
    # --- Tools / Workflow
    "PngInfoDiagnosticV4": ["png info", "png chunks", "diagnose png", "inspect png", "text chunks", "metadata"],
    "Eric_Workflow_Toolkit_v3": ["workflow", "workflow tools", "extract workflow", "save workflow", "workflow json",
                                 "analyze workflow"],
    # --- Files
    "Eric_Duplicate_Image_Finder_v05": ["duplicates", "duplicate images", "find duplicates", "similar images", "dedupe",
                                        "image hash", "perceptual hash"],
    "Eric_Fast_Duplicate_Finder": ["duplicates", "duplicate images", "find duplicates", "similar images", "dedupe",
                                   "image hash", "perceptual hash", "fast"],
    "FileOrganizerV2": ["organize files", "sort files", "move files", "sort images", "folders", "rename files", "file manager"],
    "FlattenNestedFiles_v2": ["flatten folders", "nested folders", "move files", "collect files", "subfolders"],
    # --- Color
    "ColorNameToRGB_v01": ["color", "colour", "color name", "rgb", "hex", "hex color", "color picker"],
    "ColorSelector": ["color", "colour", "color picker", "pick color", "rgb", "hex"],
    "CulturalColorPaletteGenerator_v01": ["color", "colour", "palette", "color palette", "color scheme", "swatches"],
    "Eric_Color_Palette_Analyzer_v3": ["color", "colour", "palette", "color palette", "dominant colors", "color analysis",
                                       "extract colors", "swatches"],
    # --- Crop & Compose
    "EricComposeCrop": ["crop", "smart crop", "compose", "composition", "aspect ratio crop", "pose crop", "auto crop"],
    "EricComposeCropScored": ["crop", "smart crop", "compose", "composition", "aesthetic crop", "scored crop", "auto crop",
                              "best crop"],
    "SmartImageCropper": ["crop", "smart crop", "auto crop", "content aware crop", "trim", "remove borders"],
    # --- Size & Aspect
    "AspectRatio2StepLatent": _ASPECT + ["two step", "2 step", "hires"],
    "QwenAspectRatioHelper": _ASPECT + ["qwen"],
    "QwenAspectRatioHelperAdvanced": _ASPECT + ["qwen"],
    "TileCalculator": ["tiles", "tile size", "tiled", "tile count", "upscale tiles", "image size"],
    "Wan22AspectRatioHelper": _ASPECT + ["wan", "wan 2.2", "video size"],
    "Wan22_Size_Preset": _ASPECT + ["wan", "wan 2.2", "video size", "preset"],
    # --- Text
    "EricsWordCloudNode": ["word cloud", "wordcloud", "tag cloud", "text art", "prompt cloud", "typography"],
    "TextOverlayNode_v04": ["text", "text overlay", "caption", "watermark", "label", "add text", "title", "draw text"],
    # --- Loaders
    "Multi-LoRA Loader Flux": _LORA + ["flux"],
    "Multi-LoRA Loader Model-Only": _LORA + ["model only"],
    "Multi-LoRA Loader Qwen": _LORA + ["qwen"],
    "Multi-LoRA Loader Wan-i2v": _LORA + ["wan", "i2v", "video"],
    "Multi-LoRA Loader Wan-t2v": _LORA + ["wan", "t2v", "video"],
    "Multi-LoRA Loader Z-Image": _LORA + ["z-image", "zimage"],
    "Multi-LoRA Loader v02": _LORA + ["filtered"],
    "LoRATester_v03": _LORA_TESTER + ["lora loader"],
    "LoRAInfoSetter_v03": _LORA_TESTER,
    "LoRAInfoViewer_v03": _LORA_TESTER,
    "LoRABatchInfoSetter_v03": _LORA_TESTER + ["batch"],
    "LoRABulkOperations_v03": _LORA_TESTER + ["bulk", "batch"],
    "LoRADatabaseMaintenance_v03": _LORA_TESTER + ["maintenance", "cleanup"],
    "LoRADatabaseStats_v03": _LORA_TESTER + ["statistics", "stats"],
    "LoRAGalleryDisplay_v03": _LORA_TESTER + ["gallery", "preview"],
    "LoRAGalleryWithEdit_v03": _LORA_TESTER + ["gallery", "preview", "edit"],
    "LoRAParamsLoader_v03": _LORA_TESTER + ["lora settings", "recommended strength"],
    "LoRAQuickFeedback_v03": _LORA_TESTER + ["feedback"],
    "TriggerWordManager_v03": _LORA_TESTER + ["trigger word", "activation words"],
    "CheckpointTester_v074": _CHECKPOINT + ["checkpoint loader"],
    "CheckpointInfoSetter_v074": _CHECKPOINT,
    "CheckpointInfoViewer_v074": _CHECKPOINT,
    "CheckpointBatchInfoSetter_v074": _CHECKPOINT + ["batch"],
    "CheckpointParamsLoader_v074": _CHECKPOINT + ["recommended settings", "sampler settings"],
}


def apply(class_mappings: Dict[str, Any], deprecated_category: str = "Eric's Nodes/Deprecated") -> List[str]:
    """Sets SEARCH_ALIASES on the node classes. Returns the ids that received a list."""
    if os.environ.get("AAA_META_NO_SEARCH_ALIASES", "").strip().lower() in ("1", "true", "yes", "on"):
        return []
    done: List[str] = []
    for node_id, words in ALIASES.items():
        node_class = class_mappings.get(node_id)
        if node_class is None or "SEARCH_ALIASES" in vars(node_class):
            continue
        if str(getattr(node_class, "CATEGORY", "")) == deprecated_category:
            continue
        unique: List[str] = []
        for word in words:
            if word not in unique:
                unique.append(word)
        try:
            node_class.SEARCH_ALIASES = unique
            done.append(node_id)
        except Exception:
            pass
    return done
