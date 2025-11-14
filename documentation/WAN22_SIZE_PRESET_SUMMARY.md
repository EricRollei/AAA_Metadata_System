# Wan 2.2 Size Preset - Quick Reference

## What Is It?

Generate optimized Wan 2.2 video dimensions **without needing an input image**. Select aspect ratio and size from dropdowns - perfect for Text-to-Video workflows.

---

## Quick Start

### Basic Workflow

```
Wan 2.2 Size Preset
├─ aspect_ratio: "16:9 Widescreen"  (dropdown)
├─ size_preset: "medium"             (dropdown)
└─ outputs:
    ├─ width (1080) ──→ Empty Latent Video (width)
    ├─ height (608) ──→ Empty Latent Video (height)
    └─ info_text ──→ Show Text (optional)
```

---

## Inputs

| Input | Type | Options | Default |
|-------|------|---------|---------|
| **aspect_ratio** | Dropdown | 15 predefined ratios | "16:9 Widescreen" |
| **size_preset** | Dropdown | small/medium/large/extra-large | "medium" |

---

## 15 Available Aspect Ratios

### Portrait (Vertical)
- 1:3 Ultra-Tall Portrait
- 9:21 Tall Portrait
- 9:19.5 Tall Portrait
- 9:16 Tall Portrait (Instagram, TikTok)
- 3:4 Portrait
- 5:6 Portrait

### Square
- 1:1 Square

### Landscape (Horizontal)
- 6:5 Landscape
- 4:3 Standard
- 16:10 Widescreen
- 16:9 Widescreen (YouTube, HD)
- 19.5:9 Widescreen
- 21:9 Ultra-Wide (Cinematic)
- 3:1 Ultra-Wide Landscape

---

## Size Presets

| Preset | Target Pixels | Example (16:9) | Use For |
|--------|--------------|----------------|---------|
| **small** | ~400K | 848×480 | Quick tests |
| **medium** | ~650K | 1080×608 | Standard quality |
| **large** | ~900K | 1280×720 | High quality |
| **extra-large** | ~1.4M | 1600×904 | Maximum quality |

---

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| **width** | INT | Selected width (changes with dropdown) |
| **height** | INT | Selected height (changes with dropdown) |
| **info_text** | STRING | Formatted table showing all 4 sizes |

---

## Common Use Cases

### YouTube Video (16:9)
```
aspect_ratio: "16:9 Widescreen"
size_preset: "large"
→ 1280×720
```

### Instagram Reel (9:16)
```
aspect_ratio: "9:16 Tall Portrait"
size_preset: "medium"
→ 408×720
```

### Cinematic (21:9)
```
aspect_ratio: "21:9 Ultra-Wide"
size_preset: "extra-large"
→ 1408×608
```

### Square Social (1:1)
```
aspect_ratio: "1:1 Square"
size_preset: "medium"
→ 720×720
```

---

## vs. Aspect Ratio Helper

| Feature | Size Preset | Aspect Ratio Helper |
|---------|-------------|-------------------|
| **Input Image** | ❌ Not needed | ✅ Required |
| **Best For** | T2V workflows | I2V workflows |
| **Ratio Selection** | Manual (15 options) | Auto-detected |
| **Use When** | Starting from scratch | Matching existing image |

**Rule of Thumb:**
- Have reference image? → Use **Aspect Ratio Helper**
- Starting from text prompt? → Use **Size Preset**

---

## Features

✅ **No Image Required** - Perfect for T2V  
✅ **15 Platform-Optimized Ratios** - YouTube, Instagram, TikTok, etc.  
✅ **4 Size Presets** - Small to Extra-Large  
✅ **Smart Algorithm** - Uses documented Wan 2.2 training sizes when available  
✅ **Official Specs** - All dimensions divisible by 8, ratios 1:3 to 3:1  
✅ **Change Without Rewiring** - Switch ratio or size via dropdown  

---

## Workflow Tips

### 1. Start with Medium
Always test "medium" preset first for best speed/quality balance.

### 2. Platform-Specific Quick Picks
- **YouTube:** 16:9 Widescreen
- **Instagram/TikTok:** 9:16 Tall Portrait
- **Instagram Square:** 1:1 Square
- **Cinematic:** 21:9 Ultra-Wide

### 3. Size Progression
Test workflow: small → medium → Run final at large/extra-large

### 4. Check Info Text
Connect info_text to "Show Text" node to see all 4 size options.

---

## Technical Details

- **Divisibility:** 8 pixels (both width and height)
- **Ratio Range:** 1:3 to 3:1 (official Wan 2.2 spec)
- **Known Sizes:** Uses 28 documented Wan 2.2 training sizes when available
- **Calculation:** Optimal dimensions calculated when no match found
- **Console Logging:** Detailed output for debugging

---

## Files

- **Node:** `nodes/Wan22_Size_Preset.py`
- **Full Guide:** `documentation/WAN22_SIZE_PRESET_README.md`
- **Comparison:** `documentation/WAN22_NODES_COMPARISON.md`
- **Changelog:** `CHANGELOG.md`

---

## Version

**v1.0** - Released January 23, 2025

---

## Quick Example

**Goal:** Create 16:9 YouTube video at high quality

**Setup:**
1. Add "Wan 2.2 Size Preset" node
2. Set aspect_ratio: "16:9 Widescreen"
3. Set size_preset: "large"
4. Connect width → Empty Latent Video (width)
5. Connect height → Empty Latent Video (height)
6. Run workflow

**Result:** 1280×720 dimensions optimized for Wan 2.2

---

## Need More?

- **Full documentation:** See `WAN22_SIZE_PRESET_README.md`
- **Node comparison:** See `WAN22_NODES_COMPARISON.md`
- **Integration examples:** See `WAN22_WORKFLOW_COMPARISON.md`

---

**Author:** Eric | **Category:** Wan 2.2 | **Type:** Preset Node
