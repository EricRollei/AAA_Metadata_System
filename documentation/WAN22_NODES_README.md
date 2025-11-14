# Wan 2.2 Video Generation Nodes

Complete toolkit for generating optimized dimensions for Wan 2.2 video generation in ComfyUI.

## Overview

Two complementary nodes that generate Wan 2.2 compliant video dimensions:

| Node | Best For | Input | Ratios |
|------|----------|-------|--------|
| **Aspect Ratio Helper** | I2V workflows | IMAGE (required) | Any (auto-detected) |
| **Size Preset** | T2V workflows | None (dropdowns only) | 15 predefined |

Both nodes follow official Wan 2.2 specifications:
- ✅ Divisibility by 8 pixels
- ✅ Aspect ratio range: 1:3 to 3:1 (0.333 to 3.0)
- ✅ Smart hybrid algorithm using 28 documented training sizes

---

## Quick Start

### For Image-to-Video (I2V)

```
Load Image → Wan 2.2 Aspect Ratio Helper → Empty Latent Video
- Auto-detects aspect ratio from input image
- Generates optimized dimensions matching your reference
```

### For Text-to-Video (T2V)

```
Wan 2.2 Size Preset → Empty Latent Video
- Select aspect ratio from 15 presets
- Choose size preset (tiny to gigantic)
- Perfect for starting from scratch
```

---

## Wan 2.2 Aspect Ratio Helper v2.2

### Features
- 📷 Analyzes input image aspect ratio automatically
- 🎯 Generates 6 optimized sizes (tiny → gigantic)
- 🔄 Change size preset without rewiring
- 📊 Smart hybrid: uses known Wan 2.2 sizes when available
- ⚡ Handles any ratio from 1:3 to 3:1

### Inputs
- **image**: IMAGE tensor (required)
- **size_preset**: tiny | small | medium | large | extra-large | gigantic (default: medium)

### Outputs
- **width**: INT - Selected width based on preset
- **height**: INT - Selected height based on preset
- **info_text**: STRING - Formatted display of all 6 sizes

### Example
```
Load Image (1920×1080)
    ↓
Aspect Ratio Helper
├─ Detects: 16:9 ratio (1.778)
├─ size_preset: "medium"
└─ Output: 1080×608
```

---

## Wan 2.2 Size Preset v1.1

### Features
- 📐 15 predefined aspect ratios
- 🎯 6 size presets (tiny → gigantic)
- 🚫 No image input needed
- 🔄 Change ratio or size without rewiring
- ⚡ Perfect for platform-specific formats

### Inputs
- **aspect_ratio**: 15 predefined options (default: "16:9 Widescreen")
- **size_preset**: tiny | small | medium | large | extra-large | gigantic (default: medium)

### Outputs
- **width**: INT - Selected width
- **height**: INT - Selected height
- **info_text**: STRING - Formatted display of all 6 sizes

### Available Aspect Ratios

**Portrait (Vertical)**
- 1:3 Ultra-Tall Portrait
- 9:21 Tall Portrait
- 9:19.5 Tall Portrait
- 9:16 Tall Portrait (Instagram, TikTok)
- 3:4 Portrait
- 5:6 Portrait

**Square**
- 1:1 Square (Instagram)

**Landscape (Horizontal)**
- 6:5 Landscape
- 4:3 Standard
- 16:10 Widescreen
- 16:9 Widescreen (YouTube, HD)
- 19.5:9 Widescreen
- 21:9 Ultra-Wide (Cinematic)
- 3:1 Ultra-Wide Landscape

### Example
```
Size Preset
├─ aspect_ratio: "16:9 Widescreen"
├─ size_preset: "medium"
└─ Output: 1080×608
```

---

## Size Presets

Both nodes offer 6 size options:

| Preset | Target Pixels | Example (16:9) | Use Case |
|--------|--------------|----------------|----------|
| **Tiny** ⚡ | ~200K | 592×336 | Ultra-fast testing, iteration |
| **Small** | ~400K | 848×480 | Quick tests |
| **Medium** ✨ | ~650K | 1080×608 | Standard quality (default) |
| **Large** | ~900K | 1280×720 | High quality |
| **Extra-Large** | ~1.4M | 1600×904 | Very high quality |
| **Gigantic** 🎯 | ~2M | 1896×1072 | Maximum quality, production |

### Recommended Workflow
```
1. TINY → Test ideas quickly (seconds)
2. SMALL/MEDIUM → Refine composition
3. LARGE → Quality validation
4. GIGANTIC → Final production render
```

---

## Platform Quick Reference

### YouTube (16:9 Widescreen)
```
Size Preset
├─ aspect_ratio: "16:9 Widescreen"
├─ size_preset: "large"
└─ Output: 1280×720
```

### Instagram Reel / TikTok (9:16 Portrait)
```
Size Preset
├─ aspect_ratio: "9:16 Tall Portrait"
├─ size_preset: "medium"
└─ Output: 408×720
```

### Instagram Square (1:1)
```
Size Preset
├─ aspect_ratio: "1:1 Square"
├─ size_preset: "medium"
└─ Output: 720×720
```

### Cinematic (21:9 Ultra-Wide)
```
Size Preset
├─ aspect_ratio: "21:9 Ultra-Wide"
├─ size_preset: "extra-large"
└─ Output: 1408×608
```

---

## Decision Matrix

Use this to pick the right node:

| Your Situation | Use This Node |
|---------------|---------------|
| Have reference image | Aspect Ratio Helper |
| Starting from scratch | Size Preset |
| I2V workflow | Aspect Ratio Helper |
| T2V workflow | Size Preset |
| Need exact ratio from artwork | Aspect Ratio Helper |
| Know target platform | Size Preset |
| Custom/unusual ratio | Aspect Ratio Helper |
| Standard ratio (16:9, 9:16) | Size Preset |

---

## Technical Details

### Smart Hybrid Algorithm

Both nodes use the same intelligent sizing:

1. **Check Known Sizes**: Searches 28 documented Wan 2.2 training sizes
2. **Match Criteria**: Ratio within 5% AND pixels within 30%
3. **Use Documented**: If match found, use known size (better model performance)
4. **Calculate Optimal**: If no match, calculate ideal dimensions
5. **Round to 8**: Ensures all dimensions divisible by 8

### Known Wan 2.2 Training Sizes (28 total)

**Square**: 720×720

**Portrait**: 560×720, 560×896, 560×1088, 560×1280, 688×880, 688×1072, 848×1088

**Landscape**: 720×560, 896×560, 1088×560, 1280×560, 880×688, 1072×688, 1088×848, 1280×720, 1280×800, 1280×544, 1600×640

**Additional**: 1088×672, 672×1088, 1088×704, 704×1088, 1072×672, 672×1072, 1280×768, 768×1280

### Size Calculation Formula

When no known size matches:
```python
height = sqrt(target_pixels / aspect_ratio)
width = aspect_ratio × height
# Round both to nearest multiple of 8
```

---

## Integration

Both nodes integrate seamlessly with:

### Multi-LoRA Loaders
```
[Aspect Ratio Helper OR Size Preset]
├─ width ──→ Empty Latent Video (width)
└─ height ──→ Empty Latent Video (height)

Multi-LoRA Loader (Wan T2V/I2V/Qwen)
└─ model ──→ Wan Model Node
```

### Standard ComfyUI Nodes
- Empty Latent Video
- Show Text (for info_text)
- Note (for documentation)
- Reroute (for clean connections)

---

## Console Output

Both nodes print detailed information:

```
==================================================
Wan 2.2 Aspect Ratio Helper
==================================================
Input Image Dimensions: 1920×1080
Detected Aspect Ratio: 16:9 Widescreen (1.778)

All Available Sizes:
   tiny: 592×336 (198,912 pixels)
   small: 848×480 (407,040 pixels)
 → medium: 1080×608 (656,640 pixels)
   large: 1280×720 (921,600 pixels)
   extra-large: 1600×904 (1,446,400 pixels)
   gigantic: 1896×1072 (2,032,512 pixels)

Selected Output: 1080×608
==================================================
```

---

## Troubleshooting

### Q: Node not appearing in menu?
**A:** Restart ComfyUI - new nodes load on startup.

### Q: Dimensions seem wrong?
**A:** Check console output for detailed breakdown. All dimensions guaranteed divisible by 8.

### Q: Which size preset to use?
**A:** Start with "medium" (default) for best balance. Use "tiny" for testing, "gigantic" for final renders.

### Q: Can I add custom ratios to Size Preset?
**A:** Yes! Edit `ASPECT_RATIOS` dictionary in `Wan22_Size_Preset.py`.

### Q: Input image ratio out of range?
**A:** Aspect Ratio Helper automatically clamps to valid range (1:3 to 3:1) with console warning.

---

## Version History

### v2.2 / v1.1 (2025-10-24)
- ✨ Added "tiny" preset (~200K pixels) for ultra-fast testing
- ✨ Added "gigantic" preset (~2M pixels) for maximum quality
- Now 6 size presets total

### v2.1 / v1.0 (2025-01-23)
- ✨ Simplified to 3 outputs (width, height, info_text)
- ✨ Size Preset node created as T2V companion
- ✨ Change presets without rewiring

### v2.0 (2025-01-23)
- ✨ Dynamic calculation with official Wan 2.2 specs
- ✨ Divisibility by 8 (not 16)
- ✨ Full ratio range 1:3 to 3:1

### v1.0 (2025-01-23)
- 🎉 Initial Aspect Ratio Helper release

---

## Files

### Node Files
- `nodes/Wan22_AspectRatio_Helper.py` - Image-based aspect ratio node
- `nodes/Wan22_Size_Preset.py` - Preset-based size selection node

### Documentation
- `documentation/WAN22_NODES_README.md` - This file
- `CHANGELOG.md` - Detailed version history

---

## Credits

**Author**: Eric  
**Category**: Wan 2.2 / Video Generation  
**License**: MIT  
**Created**: January 2025  
**Updated**: October 2025

---

## Related Resources

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Main framework
- [Wan 2.2 Model](https://huggingface.co/Wan2.2) - Video generation model
- Multi-LoRA Loaders - Compatible LoRA management nodes

---

## Support

For issues, feature requests, or questions:
1. Check console output for error details
2. Review this documentation
3. Open an issue on GitHub

---

**Quick Links:**
- [Installation](#quick-start)
- [Decision Matrix](#decision-matrix)
- [Size Presets](#size-presets)
- [Platform Examples](#platform-quick-reference)
- [Troubleshooting](#troubleshooting)
