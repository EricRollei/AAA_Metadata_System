# Wan 2.2 Nodes Comparison Guide

Complete comparison of the two Wan 2.2 sizing nodes to help you choose the right tool.

---

## Quick Decision Matrix

| Your Situation | Use This Node |
|---------------|---------------|
| Have reference image to match | **Aspect Ratio Helper** |
| Starting workflow from scratch | **Size Preset** |
| Image-to-Video (I2V) workflow | **Aspect Ratio Helper** |
| Text-to-Video (T2V) workflow | **Size Preset** |
| Need exact ratio from artwork | **Aspect Ratio Helper** |
| Know target platform (YouTube, Instagram, etc.) | **Size Preset** |
| Custom/unusual aspect ratio | **Aspect Ratio Helper** |
| Standard aspect ratio (16:9, 9:16, etc.) | **Size Preset** |
| Testing multiple ratios quickly | **Size Preset** |
| Ensuring consistency with input | **Aspect Ratio Helper** |

---

## Feature Comparison

| Feature | Aspect Ratio Helper | Size Preset |
|---------|-------------------|-------------|
| **Primary Input** | IMAGE (required) | None (just dropdowns) |
| **Ratio Detection** | Automatic from image | Manual selection (15 options) |
| **Ratio Range** | Any (with clamping to 1:3–3:1) | 15 predefined (1:3–3:1) |
| **Size Options** | 4 (S/M/L/XL) | 4 (S/M/L/XL) |
| **Output Count** | 3 (width, height, info_text) | 3 (width, height, info_text) |
| **Divisibility** | 8 pixels | 8 pixels |
| **Known Wan Sizes** | 28 training sizes | 28 training sizes |
| **Smart Hybrid** | ✅ Yes | ✅ Yes |
| **Console Logging** | ✅ Yes | ✅ Yes |
| **Change Without Rewiring** | ✅ Yes (size preset) | ✅ Yes (ratio + size) |
| **ComfyUI Category** | "Wan 2.2" | "Wan 2.2" |

---

## Input Comparison

### Aspect Ratio Helper Inputs

```python
INPUTS:
├─ image: IMAGE          # Required - analyzes this image's ratio
└─ size_preset: DROPDOWN # "small" | "medium" | "large" | "extra-large"
```

**Example Values After Processing:**
- Input: 1920×1080 image
- Detected Ratio: 16:9 (1.778)
- Generates 4 size options matching 1.778 ratio

### Size Preset Inputs

```python
INPUTS:
├─ aspect_ratio: DROPDOWN  # 15 predefined options
└─ size_preset: DROPDOWN   # "small" | "medium" | "large" | "extra-large"
```

**Example Values After Selection:**
- Selected: "16:9 Widescreen"
- Ratio Value: 1.778
- Generates 4 size options for 1.778 ratio

---

## Available Aspect Ratios

### Aspect Ratio Helper
**Auto-detects any ratio from input image:**
- Clamps to 1:3 minimum (ultra-tall portrait)
- Clamps to 3:1 maximum (ultra-wide landscape)
- Examples: 5:6, 21:9, custom ratios like 1.234

**Named Ratios Recognized:**
- 1:3, 9:21, 9:19.5, 9:16 (portraits)
- 3:4, 5:6 (portrait-ish)
- 1:1 (square)
- 6:5, 4:3 (standard landscape)
- 16:10, 16:9, 19.5:9 (widescreen)
- 21:9, 3:1 (ultra-wide)

### Size Preset
**15 predefined options:**
1. 1:3 Ultra-Tall Portrait (0.333)
2. 9:21 Tall Portrait (0.429)
3. 9:19.5 Tall Portrait (0.462)
4. 9:16 Tall Portrait (0.563)
5. 3:4 Portrait (0.750)
6. 5:6 Portrait (0.833)
7. 1:1 Square (1.000)
8. 6:5 Landscape (1.200)
9. 4:3 Standard (1.333)
10. 16:10 Widescreen (1.600)
11. 16:9 Widescreen (1.778)
12. 19.5:9 Widescreen (2.167)
13. 21:9 Ultra-Wide (2.333)
14. 3:1 Ultra-Wide Landscape (3.000)

---

## Workflow Examples

### Workflow 1: I2V with Existing Artwork

**Scenario:** You have concept art at 1536×2048 (3:4), want to generate video matching it

**Solution:** Use Aspect Ratio Helper

```
Load Image (1536×2048)
    ↓
Wan 2.2 Aspect Ratio Helper
├─ size_preset: "medium"
└─ Detects 3:4 ratio automatically
    ↓
width: 624, height: 832
    ↓
Empty Latent Video → I2V Model → KSampler → Save Video
```

**Why This Node?**
- Automatically detects 3:4 ratio from your artwork
- Ensures video dimensions match reference perfectly
- No need to manually figure out the ratio

---

### Workflow 2: T2V YouTube Content

**Scenario:** Creating YouTube video from scratch, need 16:9 standard

**Solution:** Use Size Preset

```
Wan 2.2 Size Preset
├─ aspect_ratio: "16:9 Widescreen"
├─ size_preset: "large"
└─ Outputs: 1280×720
    ↓
Empty Latent Video → T2V Model → KSampler → Save Video
```

**Why This Node?**
- No image needed to start
- 16:9 is standard YouTube format
- Quick selection from dropdown

---

### Workflow 3: Social Media Vertical Video

**Scenario:** Creating Instagram Reels (9:16 vertical)

**Solution:** Use Size Preset

```
Wan 2.2 Size Preset
├─ aspect_ratio: "9:16 Tall Portrait"
├─ size_preset: "medium"
└─ Outputs: 408×720
    ↓
Empty Latent Video → T2V Model → KSampler → Save Video
```

**Why This Node?**
- 9:16 is predefined for social media
- No reference image needed
- Fast iteration for testing

---

### Workflow 4: Match Character Sheet

**Scenario:** Have character reference at 768×1024, want to maintain exact proportions

**Solution:** Use Aspect Ratio Helper

```
Load Image (character sheet: 768×1024)
    ↓
Wan 2.2 Aspect Ratio Helper
├─ size_preset: "medium"
└─ Detects 3:4 ratio (0.75)
    ↓
width: 624, height: 832
    ↓
Empty Latent Video → T2V with character prompt → KSampler
```

**Why This Node?**
- Character sheet is 3:4, must maintain for consistency
- Auto-detection ensures exact ratio match
- No guessing or manual calculation

---

### Workflow 5: Cinematic Ultra-Wide

**Scenario:** Creating cinematic 21:9 ultra-wide video

**Solution:** Use Size Preset

```
Wan 2.2 Size Preset
├─ aspect_ratio: "21:9 Ultra-Wide"
├─ size_preset: "extra-large"
└─ Outputs: 1408×608
    ↓
Empty Latent Video → T2V Model → KSampler → Save Video
```

**Why This Node?**
- 21:9 is standard cinematic format
- Predefined for quick access
- No image input required

---

### Workflow 6: Custom Ratio from Sketch

**Scenario:** Have sketch at unusual 5:6 ratio (833×1000), need to match it

**Solution:** Use Aspect Ratio Helper

```
Load Image (sketch: 833×1000)
    ↓
Wan 2.2 Aspect Ratio Helper
├─ size_preset: "large"
└─ Detects 5:6 ratio (0.833)
    ↓
width: 768, height: 920
    ↓
Empty Latent Video → I2V Model
```

**Why This Node?**
- 5:6 is not a standard ratio
- Size Preset doesn't have 5:6 predefined
- Aspect Ratio Helper handles any custom ratio

---

## Algorithm Comparison

Both nodes use identical smart hybrid algorithm:

### Step 1: Search Known Wan 2.2 Sizes

28 documented training sizes stored in both nodes:

```python
WAN22_KNOWN_SIZES = [
    (720, 720),           # 1:1 Square
    (560, 720),           # Portrait
    (1280, 720),          # 16:9 Landscape
    # ... 25 more sizes
]
```

**Matching Criteria:**
- Ratio difference ≤ 5%
- Pixel count difference ≤ 30%

**If match found:** Use documented size (better model performance)

### Step 2: Calculate Optimal Size

**If no match found:** Calculate optimal dimensions

```python
# Formula
height = sqrt(target_pixels / aspect_ratio)
width = aspect_ratio * height

# Round to nearest multiple of 8
width = ((width + 4) // 8) * 8
height = ((height + 4) // 8) * 8
```

### Step 3: Generate All 4 Presets

Both nodes generate all 4 sizes (Small/Medium/Large/Extra-Large) using same logic.

### Step 4: Return Selected Pair

User's `size_preset` dropdown determines which width/height pair is output.

---

## Output Comparison

Both nodes return identical structure:

```python
RETURN_TYPES = ("INT", "INT", "STRING")
RETURN_NAMES = ("width", "height", "info_text")
```

### Example: 16:9 at Medium

**Aspect Ratio Helper** (with 1920×1080 input):
```
width: 1080
height: 608
info_text:
    Wan 2.2 Aspect Ratio Helper
    ═══════════════════════════
    Input: 1920×1080
    Detected Ratio: 16:9 Widescreen (1.778)
    
    Available Sizes:
      Small: 848×480 (~407K pixels)
    ✓ Medium: 1080×608 (~656K pixels)
      Large: 1280×720 (~922K pixels)
      Extra-Large: 1600×904 (~1.4M pixels)
```

**Size Preset** (selected "16:9 Widescreen"):
```
width: 1080
height: 608
info_text:
    Wan 2.2 Size Preset
    ═══════════════════════════
    Selected Ratio: 16:9 Widescreen
    Ratio Value: 1.778
    
    Available Sizes:
      Small: 848×480 (~407K pixels)
    ✓ Medium: 1080×608 (~656K pixels)
      Large: 1280×720 (~922K pixels)
      Extra-Large: 1600×904 (~1.4M pixels)
```

**Result:** Identical dimensions! Only info text differs slightly.

---

## Use Case Decision Tree

```
┌─────────────────────────────┐
│ Do you have a reference     │
│ image/artwork to match?     │
└─────────┬───────────────────┘
          │
    ┌─────┴─────┐
    │           │
   YES         NO
    │           │
    ↓           ↓
┌────────────┐ ┌────────────┐
│  Aspect    │ │   Size     │
│  Ratio     │ │   Preset   │
│  Helper    │ │            │
└────────────┘ └────────────┘
     │              │
     ↓              ↓
  I2V Flow      T2V Flow
```

---

## Performance Comparison

| Metric | Aspect Ratio Helper | Size Preset |
|--------|-------------------|-------------|
| **Execution Speed** | ~10-20ms | ~5-10ms |
| **Memory Usage** | Minimal (+image tensor) | Minimal |
| **Node Weight** | Requires image loading | No image needed |
| **Iteration Speed** | Change size dropdown | Change ratio OR size |

**Winner:** Size Preset is slightly faster (no image processing), but difference is negligible.

---

## Integration with Multi-LoRA Loaders

Both nodes integrate identically with your existing Multi-LoRA Loader workflow:

### Pattern 1: Aspect Ratio Helper + Multi-LoRA

```
Load Image
    ↓
Wan 2.2 Aspect Ratio Helper
├─ width ──→ Empty Latent Video (width)
└─ height ──→ Empty Latent Video (height)

Multi-LoRA Loader (Wan I2V)
└─ model ──→ Wan I2V Model Node
```

### Pattern 2: Size Preset + Multi-LoRA

```
Wan 2.2 Size Preset
├─ width ──→ Empty Latent Video (width)
└─ height ──→ Empty Latent Video (height)

Multi-LoRA Loader (Wan T2V)
└─ model ──→ Wan T2V Model Node
```

Both patterns work perfectly with your existing Multi-LoRA nodes!

---

## Best Practices

### When to Use Aspect Ratio Helper

✅ **Image-to-Video workflows**
- Have reference artwork, character sheets, storyboards
- Need exact ratio match with existing visuals
- Custom/unusual aspect ratios

✅ **Consistency requirements**
- Multiple videos from same reference
- Maintaining brand/style consistency
- Matching existing content library

### When to Use Size Preset

✅ **Text-to-Video workflows**
- Starting from prompt only
- No reference image available
- Platform-specific formats (YouTube, Instagram, TikTok)

✅ **Rapid prototyping**
- Testing multiple aspect ratios
- Experimenting with different formats
- Quick concept validation

### Pro Tip: Use Both!

Many workflows benefit from **both nodes**:

**Hybrid Workflow Example:**
```
TESTING PHASE:
    Size Preset → Test different ratios quickly → Find best format
    
PRODUCTION PHASE:
    Create reference image at chosen ratio → 
    Aspect Ratio Helper → Match reference exactly →
    Final video generation
```

---

## Migration Guide

### Coming from Aspect Ratio Helper v2.0

If you used the old 13-output version:

**Old v2.0 Pattern:**
```
Aspect Ratio Helper
├─ selected_width ──→ Empty Latent Video (width)
└─ selected_height ──→ Empty Latent Video (height)
```

**New v2.1 Pattern (both nodes):**
```
Aspect Ratio Helper OR Size Preset
├─ width ──→ Empty Latent Video (width)
└─ height ──→ Empty Latent Video (height)
```

**Changes:**
- Output names simplified: `selected_width` → `width`
- Output names simplified: `selected_height` → `height`
- Removed 8 separate size outputs (small/medium/large/xlarge width/height)

---

## Technical Deep Dive

### Aspect Ratio Detection (Helper Only)

```python
# Extract dimensions from image tensor
batch, height, width, channels = image.shape

# Calculate ratio
aspect_ratio = width / height

# Clamp to Wan 2.2 valid range
if aspect_ratio < 0.333:
    aspect_ratio = 0.333  # 1:3 minimum
    print("WARNING: Ratio too narrow, clamped to 1:3")
    
if aspect_ratio > 3.0:
    aspect_ratio = 3.0  # 3:1 maximum
    print("WARNING: Ratio too wide, clamped to 3:1")
```

### Ratio Name Mapping (Both Nodes)

```python
def _get_ratio_name(aspect_ratio):
    # Check standard ratios
    if abs(aspect_ratio - 1.0) < 0.02: return "1:1 Square"
    if abs(aspect_ratio - 16/9) < 0.02: return "16:9 Widescreen"
    if abs(aspect_ratio - 9/16) < 0.02: return "9:16 Tall Portrait"
    # ... more checks
    
    # Simplify to fraction
    return _simplify_ratio(aspect_ratio)
```

### Size Generation (Identical in Both)

```python
def _generate_optimal_sizes(aspect_ratio):
    sizes = {}
    
    for preset, target_pixels in TARGET_PIXELS.items():
        # Try known Wan 2.2 size first
        known = _find_closest_known_size(aspect_ratio, target_pixels)
        
        if known:
            sizes[preset] = known
        else:
            # Calculate optimal
            sizes[preset] = _calculate_optimal_size(aspect_ratio, target_pixels)
    
    return sizes
```

---

## Console Output Examples

### Aspect Ratio Helper

```
==================================================
Wan 2.2 Aspect Ratio Helper
==================================================
Input Image Dimensions: 1024×768
Detected Aspect Ratio: 4:3 Standard (1.333)
Ratio within valid range (1:3 to 3:1)

All Available Sizes:
   small: 560×424 (~237K pixels)
 → medium: 720×544 (~392K pixels)
   large: 880×664 (~584K pixels)
   extra-large: 1104×832 (~918K pixels)

Selected Output: 720×544
==================================================
```

### Size Preset

```
==================================================
Wan 2.2 Size Preset Generated
==================================================
Aspect Ratio: 4:3 Standard (1.333)
Size Preset: medium

All Available Sizes:
   small: 560×424 (237440 pixels)
 → medium: 720×544 (391680 pixels)
   large: 880×664 (584320 pixels)
   extra-large: 1104×832 (918528 pixels)

Selected Output: 720×544
==================================================
```

---

## Summary Table

| Feature | Aspect Ratio Helper | Size Preset |
|---------|-------------------|-------------|
| **Best For** | I2V workflows | T2V workflows |
| **Input Required** | IMAGE | None |
| **Ratio Selection** | Auto-detected | Manual dropdown |
| **Ratio Options** | Unlimited (with clamping) | 15 predefined |
| **Outputs** | 3 (width, height, info_text) | 3 (width, height, info_text) |
| **Size Presets** | 4 (S/M/L/XL) | 4 (S/M/L/XL) |
| **Smart Hybrid** | ✅ Yes | ✅ Yes |
| **Known Wan Sizes** | 28 training sizes | 28 training sizes |
| **Divisibility** | 8 pixels | 8 pixels |
| **Valid Ratio Range** | 1:3 to 3:1 | 1:3 to 3:1 |
| **Console Logging** | ✅ Yes | ✅ Yes |
| **Change Without Rewiring** | ✅ Yes | ✅ Yes |
| **Version** | v2.1 | v1.0 |

---

## Related Documentation

- `WAN22_ASPECT_RATIO_HELPER_README.md` - Full guide for image-based node
- `WAN22_SIZE_PRESET_README.md` - Full guide for preset-based node
- `WAN22_WORKFLOW_COMPARISON.md` - Multi-LoRA integration examples
- `CHANGELOG.md` - Version history for both nodes

---

## Author

**Eric**  
Created: January 23, 2025  

Part of the Metadata System custom nodes for ComfyUI.
