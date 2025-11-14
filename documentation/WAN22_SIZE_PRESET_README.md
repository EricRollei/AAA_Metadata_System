# Wan 2.2 Size Preset Node - Complete Guide

## Overview

The **Wan 2.2 Size Preset** node is a companion to the Wan 2.2 Aspect Ratio Helper that generates optimized video dimensions **without requiring an input image**. Perfect for starting workflows from scratch when you know the aspect ratio you want.

### Key Features

✅ **No Image Input Required** - Just pick ratio and size  
✅ **15 Predefined Aspect Ratios** - From 1:3 ultra-tall to 3:1 ultra-wide  
✅ **4 Size Presets** - Small, Medium, Large, Extra-Large  
✅ **Same Smart Logic** - Uses documented Wan 2.2 training sizes when available  
✅ **Official Specs Compliant** - All dimensions divisible by 8, ratios 1:3 to 3:1  
✅ **Clean UX** - 3 outputs (width, height, info_text), change settings without rewiring  

---

## Node Comparison

| Feature | Aspect Ratio Helper | Size Preset (New!) |
|---------|--------------------|--------------------|
| **Input** | Requires image | No image needed |
| **Ratio Selection** | Auto-detected from image | Manual dropdown |
| **Use Case** | Match existing image | Start from scratch |
| **Ratios Available** | Any (auto-detected) | 15 predefined |
| **Size Presets** | 4 (S/M/L/XL) | 4 (S/M/L/XL) |
| **Outputs** | width, height, info_text | width, height, info_text |

---

## Inputs

### 1. Aspect Ratio (Dropdown)

Select from 15 predefined aspect ratios:

#### Portrait Ratios
- **1:3 Ultra-Tall Portrait** - Extreme vertical (0.333)
- **9:21 Tall Portrait** - Very tall (0.429)
- **9:19.5 Tall Portrait** - Tall (0.462)
- **9:16 Tall Portrait** - Standard phone (0.563)
- **3:4 Portrait** - Classic portrait (0.750)
- **5:6 Portrait** - Slightly tall (0.833)

#### Square
- **1:1 Square** - Perfect square (1.000)

#### Landscape Ratios
- **6:5 Landscape** - Slightly wide (1.200)
- **4:3 Standard** - Classic TV (1.333)
- **16:10 Widescreen** - Computer monitor (1.600)
- **16:9 Widescreen** - HD standard (1.778)
- **19.5:9 Widescreen** - Phone landscape (2.167)
- **21:9 Ultra-Wide** - Cinematic (2.333)
- **3:1 Ultra-Wide Landscape** - Extreme horizontal (3.000)

### 2. Size Preset (Dropdown)

Choose target pixel count:

| Preset | Target Pixels | Typical Use |
|--------|--------------|-------------|
| **Small** | ~400K | Quick tests, previews |
| **Medium** | ~650K | Standard quality |
| **Large** | ~900K | High quality |
| **Extra-Large** | ~1.4M | Maximum quality |

---

## Outputs

### 1. Width (INT)
Selected width value based on ratio + size preset

### 2. Height (INT)
Selected height value based on ratio + size preset

### 3. Info Text (STRING)
Formatted display showing:
- Selected aspect ratio and numeric value
- All 4 available sizes with pixel counts
- Checkmark (✓) showing selected size
- Reminder about divisibility by 8

**Example Info Text:**
```
Wan 2.2 Size Preset
═══════════════════════════
Selected Ratio: 16:9 Widescreen
Ratio Value: 1.778

Available Sizes:
  Small: 560×320 (~179K pixels)
✓ Medium: 720×408 (~294K pixels)
  Large: 848×480 (~407K pixels)
  Extra-Large: 1056×592 (~625K pixels)

All dimensions divisible by 8
```

---

## Workflow Examples

### Example 1: Start T2V Workflow from Scratch

**Goal:** Create 16:9 widescreen video at medium quality

```
Wan 2.2 Size Preset
├─ aspect_ratio: "16:9 Widescreen"
├─ size_preset: "medium"
└─ outputs:
    ├─ width (720) ──→ Empty Latent Video (width)
    ├─ height (408) ──→ Empty Latent Video (height)
    └─ info_text ──→ Show Text Node
```

### Example 2: Test Multiple Sizes Quickly

**Goal:** Compare small vs large renders

**Setup Once:**
```
Wan 2.2 Size Preset → Empty Latent Video → Wan Model → KSampler → Save Video
```

**Then Just Change Dropdown:**
- Run 1: size_preset = "small" → 560×320
- Run 2: size_preset = "large" → 848×480
- No rewiring needed!

### Example 3: Portrait Video for Social Media

**Goal:** Create 9:16 vertical video (Instagram/TikTok)

```
Wan 2.2 Size Preset
├─ aspect_ratio: "9:16 Tall Portrait"
├─ size_preset: "medium"
└─ outputs:
    ├─ width (408) ──→ Empty Latent Video (width)
    └─ height (720) ──→ Empty Latent Video (height)
```

### Example 4: Ultra-Wide Cinematic

**Goal:** Create 21:9 cinematic video

```
Wan 2.2 Size Preset
├─ aspect_ratio: "21:9 Ultra-Wide"
├─ size_preset: "large"
└─ outputs:
    ├─ width (1120) ──→ Empty Latent Video (width)
    └─ height (480) ──→ Empty Latent Video (height)
```

---

## How It Works Internally

### Smart Hybrid Algorithm

The node uses the same smart logic as Wan 2.2 Aspect Ratio Helper:

1. **Check Known Wan 2.2 Sizes First**
   - Searches 28 documented training sizes
   - Matches if ratio within 5% AND pixels within 30%
   - Prefers documented sizes for better model performance

2. **Calculate Optimal If No Match**
   - Uses formula: `height = sqrt(target_pixels / aspect_ratio)`
   - Calculates: `width = aspect_ratio × height`
   - Rounds to nearest multiple of 8

3. **Generate All 4 Sizes**
   - Creates Small/Medium/Large/Extra-Large options
   - User can switch between them via dropdown

4. **Output Selected Pair**
   - Returns width/height for chosen size preset
   - Info text shows all options for reference

### Example: 16:9 at Medium

**Input:**
- aspect_ratio: "16:9 Widescreen" (1.778)
- size_preset: "medium"
- target_pixels: 650,000

**Processing:**
1. Check known sizes → Found 720×408 (ratio 1.765, pixels 294K)
2. Within tolerances? Ratio diff 0.7%, pixel diff 54% → **No match**
3. Calculate optimal: height = sqrt(650000/1.778) = 605 → round to 608
4. width = 1.778 × 608 = 1081 → round to 1080
5. Result: **1080×608**

**All Generated Sizes:**
- Small: 848×480 (~407K) - uses known Wan 2.2 size
- Medium: 1080×608 (~656K) - calculated optimal
- Large: 1280×720 (~922K) - uses known Wan 2.2 size
- Extra-Large: 1600×904 (~1.4M) - calculated optimal

---

## When to Use Each Node

### Use **Wan 2.2 Aspect Ratio Helper** When:
- ✅ You have an existing image to match
- ✅ You want the exact ratio of a reference image
- ✅ Working with I2V (Image-to-Video) workflows
- ✅ Need to maintain consistency with input artwork

### Use **Wan 2.2 Size Preset** When:
- ✅ Starting T2V (Text-to-Video) from scratch
- ✅ You know the aspect ratio you want
- ✅ No reference image available yet
- ✅ Testing different ratios quickly
- ✅ Creating videos for specific platforms (9:16 for social, 16:9 for YouTube, etc.)

---

## Best Practices

### 1. Start with Medium
Always test with "medium" preset first - good balance of quality and generation speed.

### 2. Use Known Ratios
The 15 predefined ratios are optimized for Wan 2.2. Stick to these for best results.

### 3. Check Info Text
Always connect info_text to a "Show Text" node during setup - helps verify dimensions.

### 4. Match Your Platform
- **YouTube/Web:** 16:9 Widescreen
- **Instagram/TikTok:** 9:16 Tall Portrait
- **Instagram Square:** 1:1 Square
- **Cinematic:** 21:9 Ultra-Wide

### 5. Size Scaling for Testing
Use this progression:
1. Small: Quick proof of concept (seconds)
2. Medium: Full quality test (minutes)
3. Large: Near-final quality
4. Extra-Large: Final production render

---

## Technical Specifications

### Wan 2.2 Requirements (Official)
- ✅ Divisibility: 8 pixels (both width and height)
- ✅ Ratio Range: 1:3 to 3:1 (0.333 to 3.0)
- ✅ All 15 predefined ratios are within range

### Known Wan 2.2 Training Sizes (28 Total)
The node uses these documented sizes when they match your selection:

**Square:**
720×720

**Portrait:**
560×720, 560×896, 560×1088, 560×1280, 688×880, 688×1072, 848×1088

**Landscape:**
720×560, 896×560, 1088×560, 1280×560, 880×688, 1072×688, 1088×848

**Wide Landscape:**
1280×720, 1280×800, 1280×544, 1600×640

**Additional:**
1088×672, 672×1088, 1088×704, 704×1088, 1072×672, 672×1072, 1280×768, 768×1280

### Pixel Count Targets
| Preset | Target | Range |
|--------|--------|-------|
| Small | 400K | 350K-450K |
| Medium | 650K | 550K-750K |
| Large | 900K | 800K-1000K |
| Extra-Large | 1.4M | 1.2M-1.6M |

---

## Troubleshooting

### Q: Why doesn't my ratio option exist?
**A:** The 15 predefined ratios cover the full Wan 2.2 range (1:3 to 3:1). If you need a custom ratio, use the Aspect Ratio Helper with an image at your desired ratio.

### Q: Can I add more aspect ratios?
**A:** Yes! Edit the `ASPECT_RATIOS` dictionary in `Wan22_Size_Preset.py`. Keep ratios between 0.333 and 3.0.

### Q: Dimensions seem smaller than expected
**A:** This is normal - the node optimizes for specific pixel counts. Try "large" or "extra-large" presets for bigger dimensions.

### Q: How do I verify divisibility by 8?
**A:** Check the console output or info_text. The node guarantees all dimensions are divisible by 8.

### Q: Should I use this or the Aspect Ratio Helper?
**A:** 
- **This node** → No image input, pick ratio from dropdown
- **Aspect Ratio Helper** → Has image input, auto-detects ratio

---

## Integration with Multi-LoRA Loaders

Both Wan 2.2 nodes work seamlessly with your Multi-LoRA Loader nodes:

```
Wan 2.2 Size Preset
├─ width ──→ Empty Latent Video (width)
└─ height ──→ Empty Latent Video (height)

Multi-LoRA Loader (Wan T2V/I2V)
└─ model ──→ Wan Model Node

OR

Multi-LoRA Loader (Wan Qwen)
└─ model ──→ Qwen Model Node
```

---

## Console Output

The node prints detailed info to the console for debugging:

```
==================================================
Wan 2.2 Size Preset Generated
==================================================
Aspect Ratio: 16:9 Widescreen (1.778)
Size Preset: medium

All Available Sizes:
   small: 848×480 (407040 pixels)
 → medium: 1080×608 (656640 pixels)
   large: 1280×720 (921600 pixels)
   extra-large: 1600×904 (1446400 pixels)

Selected Output: 1080×608
==================================================
```

---

## Version History

### v1.0 (2025-01-23)
- Initial release
- 15 predefined aspect ratios
- 4 size presets (Small/Medium/Large/Extra-Large)
- Smart hybrid algorithm (known sizes + calculated optimal)
- 3-output UX design (width, height, info_text)
- Companion to Wan 2.2 Aspect Ratio Helper v2.1

---

## Related Documentation

- `WAN22_ASPECT_RATIO_HELPER_README.md` - Image-based aspect ratio node
- `WAN22_SIZE_PRESET_COMPARISON.md` - Detailed comparison of both nodes
- `WAN22_WORKFLOW_COMPARISON.md` - Integration examples
- `CHANGELOG.md` - All version history

---

## Author

**Eric**  
Created: January 23, 2025  
Version: 1.0

Part of the Metadata System custom nodes for ComfyUI.
