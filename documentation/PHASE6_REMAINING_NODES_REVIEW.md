# Phase 6 - remaining nodes: review and options

Date: 2026-11-17. Status: **survey only - nothing in these files has been changed.**
The survey is mechanical (file size, registered node ids, categories, error handling, console output,
whether the node uses the metadata service). It is the basis for choosing what to do, not a code review of
each node's logic.

## What already works for these nodes without touching them

- **Model / LoRA capture**: the capture hook sees every model file a node loads, so the Multi-LoRA loaders,
  LoRA tester and checkpoint tester already show up in the generation record of "Metadata Save Image v1.0".
- **Measurements**: nodes that call `MetadataService.write_metadata` with analysis data
  (duplicate finder v05, colour palette analyzer v3, PNG info diagnostic v3, save true SVG, workflow toolkit v2,
  split workflow extractor V2, PNG metadata extractor v3) are mirrored into the new measurement namespace.

## Inventory

| File | Lines | Node ids | Category | bare `except:` | `print` calls | Uses metadata service |
|---|---|---|---|---|---|---|
| Lora_tester_v03.py | 4644 | 12 (LoRATester_v03, LoRAInfoSetter_v03, ...) | loaders/lora tester | 9 | 54 | no |
| checkpoint_tester_node_v074.py | 2419 | 5 (CheckpointTester_v074, ...) | loaders/checkpoint tester | 5 | 176 | no |
| Multi_LoRA_Loader_Base.py | 628 | (shared base) | - | 2 | 16 | no |
| Multi_LoRA_Loader_v02.py / _Model_Only.py | 880 / 873 | 1 each | loaders/multi-lora | 1 / 1 | 18 / 18 | no |
| Multi_LoRA_Loader_Flux / Qwen / Wan_i2v / Wan_t2v / ZImage | 171-303 | 1 each | loaders/multi-lora/... | 0 | 3 each | no |
| Qwen_AspectRatio_Helper.py | 515 | 2 | loaders/multi-lora/qwen | 0 | 5 | no |
| Wan22_AspectRatio_Helper.py, Wan22_Size_Preset.py | 352, 285 | 1 each | loaders/multi-lora/wan, Wan 2.2 | 0 | 11, 9 | no |
| aspect_ratio_2step_latent.py, tile_calculator.py | 156, 92 | 1 each | image/preprocessing | 0 | 0 | no |
| eric-duplicate-image-finder_v05.py | 1682 | 1 | Eric/Images | 5 | 49 | yes |
| eric_fast_duplicate_finder.py | 466 | 1 | Eric/Images | 0 | 0 | no |
| file-organizer-node_v01.py / _v02.py | 473 / 662 | FileOrganizer / FileOrganizerV2 | Eric/Images, Eric/Files | 0 | 0 | no |
| flatten-nested-images-node_v02.py | 703 | 1 | Eric/Images | 4 | 1 | no |
| eric-smart-image-crop.py | 1152 | 1 | Eric/Image Processing | 0 | 47 | no |
| eric_compose_crop.py / _scored.py | 425 / 634 | 1 each | Eric/Compose | 0 | 0 | no |
| eric_color_pallete_analyzer_v3.py | 1722 | 1 | Eric | 0 | 34 | yes |
| eric_color_pallete_selector.py | 753 | 1 | colors | 6 | 0 | no |
| eric_colorname_to_rgb_hex.py, color_selector.py | 172, 201 | 1 each | colors, ui/color | 3, 3 | 0 | no |
| color_names.py | 1351 | (data) | - | 0 | 0 | no |
| wordcloud_node.py | 1569 | 1 | image/text | 5 | 95 | no |
| text-overlay-node_v04.py | 978 | 1 | image/text | 5 | 23 | no |
| eric_civitai_prompt_extractor_node.py | 1624 | 2 | metadata | 1 | 14 | no |
| Eric_png_metadata_extractor_node_v3.py | 392 | 1 | Eric | 4 | 9 | yes |
| eric_png_info_diagnostic_node_v3.py | 476 | 1 | Eric | 2 | 5 | yes |
| eric_split_workflow_extractor_node_V2.py | 357 | 1 | Eric | 1 | 12 | yes |
| eric_workflow_toolkit_v2.py, eric_workflow_extractor.py | 1170, 53 | 1, 0 | Eric | 2, 0 | 12, 0 | yes, no |
| eric_save_true_svg_image.py | 717 | 1 | image/save | 0 | 25 | yes |
| eric_save_qwen_layers.py | 854 | 1 | Eric | 1 | 10 | no |

All files parse. No node id is registered twice.

## Findings

1. **Console noise at startup and during runs.** The word cloud node prints its colour database on every
   start (seen in every check run); the checkpoint tester has 176 `print` calls. Easy to route through one
   switch (quiet by default, `debug_logging` or an environment variable turns it on).
2. **Categories are spread over seven top-level menus and many sub-menus** (`Eric`, `Eric/Images`, `Eric/Files`, `Eric/Compose`,
   `Eric/Image Processing`, `colors`, `ui/color`, `image/text`, `image/preprocessing`, `image/save`, `metadata`,
   `loaders/...`, `Wan 2.2`) plus `Eric's Nodes/...` for the metadata nodes. Unifying them changes where
   nodes sit in the add-node menu; saved workflows are not affected.
3. **Two generations of the same node are both live**: file organizer v01 / v02, duplicate finder v05 / fast
   duplicate finder, Multi-LoRA loader v02 / Model-Only (near-identical, 880 / 873 lines).
4. **Bare `except:`** in 18 files (60 places) hides real errors, including keyboard interrupts.
5. **Workflow / PNG extractors** (PNG metadata extractor v3, PNG info diagnostic v3, split workflow
   extractor V2, workflow toolkit v2, Civitai prompt extractor) rebuild generation data from the workflow
   graph - the job the new record now does more completely. They could read the stored record first and
   fall back to their own parsing for older files.
6. **Save true SVG** and **Save Qwen layers** write files on their own path, without the automatic
   generation record. Both could get it through the same bridge the save node uses.
7. **Aspect helpers and size presets**: small, self-contained, no issues found by the survey.

## Options (pick any; none is started)

| # | Work | Risk to saved workflows | Size |
|---|---|---|---|
| A | Quiet console: one logging switch across these nodes | none | small |
| B | Save true SVG + Save Qwen layers: new versions with the automatic generation record | none (new node ids) | medium |
| C | Extractor nodes: new versions that read the stored record first | none (new node ids) | medium |
| D | Replace bare `except:` with `except Exception:` and report the error | none | small |
| E | One category tree (`Eric's Nodes/...`) for the whole pack | none; menu positions change | small |
| F | Mark v01 / older twins as deprecated (file organizer v01, etc.) | none | trivial, needs your call on which |
| G | Leave as is | - | - |

Not proposed: rewriting the LoRA tester, checkpoint tester, word cloud or crop nodes. They are large,
working, and outside the metadata goal; a rewrite would need its own review of what you want changed.
