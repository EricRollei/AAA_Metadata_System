# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-18

### Added - Metadata system 2.0
- **AAA Save Image All PNG WebP JPG PSD TIFF SVG w Metadata**: every option of v099d, plus generation data collected automatically while
  the workflow runs and written where Lightroom, XnView MP and Capture One search (caption, keywords,
  headline, instructions) and in the `hcai` / `eiqa` namespaces. Display P3, real colour conversion,
  true 16-bit TIFF and PSD, Photoshop-readable layers in TIFF, automatic collection of measurements.
- Companion nodes on the same core: Metadata Entry V3, Query V4, Filter V3, Enhanced Filter V3, Debugger V3,
  Consolidator V3, Add Measurements to Image v1, Generation Record (debug) v1.
- Load nodes v2: stored prompt / record / measurements as outputs, full-precision 16-bit loading,
  Photoshop layers from TIFF.
- `tools/backfill_library.py`: makes existing PNGs searchable from their embedded workflow.
- **Recipes**: a generator node that returns its own settings as JSON (a dict with a `*_settings_version`
  key, e.g. Eric_Krea2 Ultra) has that statement stored with the image (`recipe` in the record, RECIPE
  section in the .txt). Krea2 parameter sweeps: every image of the batch gets the record of its own cell -
  checkpoint, LoRAs, prompt with trigger words, seed, stage settings - read from the sweep manifest and
  the cell pictures. Stages that did not run are no longer listed as passes.
- Save True SVG v2, Save Qwen Layers v2, file extractors V4 / V3, Workflow Toolkit v3, Civitai extractors V2.

### Changed
- The new save node is called **AAA Save Image All PNG WebP JPG PSD TIFF SVG w Metadata** (id `AAA_SaveImageAll`). The node search also finds it by
  psd, tiff, svg, layers, icc, color management, metadata, xmp, lightroom and similar words (`SEARCH_ALIASES`).
- Every current node has search words (`aaa_meta/search_aliases.py`); deprecated nodes have none, so a
  search leads to the current version. README: new section on AAA Save Image All.
- **Save Image with Metadata v099d now runs the same code.** Existing workflows need no editing: v099d's
  widgets keep their order, the five new ones follow with their defaults. Set `AAA_META_KEEP_OLD_SAVE=1`  
  to keep the original v099d. Note: Adobe RGB / ProPhoto now convert the pixels (v099d only attached the
  profile), and 8-bit PNG / JPG / WebP honour the colour-profile and embed-workflow widgets.
- The pack loads once. Imports by the names `AAA_Metadata_System` and `custom_nodes.AAA_Metadata_System`
  resolve to the loaded pack whatever the folder is called (the registry installs it as
  `aaa-metadata-system`, where those imports used to fail).
- The first runtime-hook module (`eric_metadata/hooks/runtime_capture.py`, off by default) is retired;
  collection is done by `aaa_meta.capture`. A placeholder keeps the old save nodes loading.
- One menu tree, "Eric's Nodes/...", and a quiet console (`AAA_META_VERBOSE=1` for the full output).
- `tifffile` added to `requirements.txt`.
- Nodes with a newer version are labelled "(deprecated)" and listed under "Eric's Nodes/Deprecated".
  They still load and run.
- `nodes/civitai_cache.json` is no longer tracked; the Multi-LoRA template moved to `resources/templates/`.
- Licence classifier in `pyproject.toml` corrected (was MIT; the licence is CC BY-NC 4.0 / commercial).

### Added (2025-10-23) - Wan 2.2 Nodes v2.2 / v1.1
- **Enhanced Size Options for Both Nodes** - Added 2 new size presets
  - ✨ **NEW TINY**: ~200K pixels for ultra-fast previews and testing
  - ✨ **NEW GIGANTIC**: ~2M pixels for maximum quality production renders
  - Now 6 size presets total: tiny, small, medium, large, extra-large, gigantic
  - Aspect Ratio Helper updated to v2.2
  - Size Preset updated to v1.1
  - Both nodes maintain backward compatibility

### Added (2025-01-23) - Wan 2.2 Size Preset v1.0
- **Wan 2.2 Size Preset Node v1.0** - NEW companion node for Wan 2.2 sizing
  - ✨ **NO IMAGE NEEDED**: Generate Wan 2.2 dimensions without input image
  - ✨ **15 PREDEFINED RATIOS**: From 1:3 ultra-tall to 3:1 ultra-wide
  - ✨ **PERFECT FOR T2V**: Ideal for Text-to-Video workflows starting from scratch
  - ✨ **SAME SMART LOGIC**: Uses documented Wan 2.2 training sizes + optimal calculation
  - ✨ **CLEAN UX**: 3 outputs (width, height, info_text), change ratio or size without rewiring
  - Select aspect ratio and size preset from dropdowns
  - Complements Wan 2.2 Aspect Ratio Helper (which requires image input)
  - Files: `Wan22_Size_Preset.py`, `WAN22_SIZE_PRESET_README.md`, `WAN22_NODES_COMPARISON.md`

### Added (2025-01-23) - Wan 2.2 Aspect Ratio Helper v2.1
- **Wan 2.2 Aspect Ratio Helper Node v2.1** - Major UX improvement
  - ✨ **SIMPLIFIED**: Only 3 outputs (width, height, info_text) instead of 13
  - ✨ **BETTER UX**: Change size preset dropdown without rewiring workflow
  - ✨ **CLEARER**: Obvious which outputs to use (width/height)
  - ✨ **INFORMATIVE**: Enhanced info_text with formatted ASCII table showing all 4 size options
  - Users can now test different sizes by just changing dropdown menu
  - Follows standard ComfyUI design patterns
  - Files: `Wan22_AspectRatio_Helper.py`, `WAN22_V2.1_UX_IMPROVEMENT.md`

### Added (2025-01-23) - v2.0
- **Wan 2.2 Aspect Ratio Helper Node v2.0** - Major update with official Wan 2.2 specifications
  - ✨ **NEW**: Divisibility by 8 pixels (official Wan 2.2 requirement, not 16)
  - ✨ **NEW**: Full 1:3 to 3:1 aspect ratio range support (official Wan 2.2 spec)
  - ✨ **NEW**: Dynamic size calculation - matches exact input ratio, not forced to presets
  - ✨ **NEW**: Smart hybrid algorithm - uses known Wan 2.2 sizes when available, calculates optimal otherwise
  - ✨ **NEW**: Better ratio detection and labeling (e.g., "5:6 Portrait" instead of forcing to "3:4")
  - ✨ **NEW**: Enhanced console logging with pixel counts
  - Supports any aspect ratio from ultra-portrait (1:3) to ultra-wide (3:1)
  - Maintains backward compatibility with documented Wan 2.2 training sizes
  - Files: `Wan22_AspectRatio_Helper.py`, 4 documentation files

### Added (2025-01-23) - v1.0
- **Wan 2.2 Aspect Ratio Helper Node v1.0** - Initial release
  - Automatic aspect ratio detection from input images
  - 7 fixed aspect ratios (1:1, 3:4, 4:3, 2:3, 3:2, 9:16, 16:9)
  - 4 size scales per ratio (small, medium, large, extra-large)
  - All dimensions divisible by 16
  - Based on documented Wan 2.2 training sizes
  - Files: `Wan22_AspectRatio_Helper.py`, 3 README docs

- Initial project structure
- License and documentation files

## [0.1.0] - YYYY-MM-DD

### Added
- First release of ComfyUI Custom Nodes
- [List key nodes/features included in initial release]

### Known Issues
- [List any known issues or limitations]
