# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
