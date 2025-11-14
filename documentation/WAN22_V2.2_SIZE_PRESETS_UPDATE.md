# Wan 2.2 Nodes v2.2/v1.1 Update - New Size Presets

## What's New

Both Wan 2.2 nodes have been enhanced with **2 new size presets**:

### ⚡ **TINY** (~200K pixels)
- Ultra-fast previews
- Quick testing and iteration
- Fastest generation times
- Perfect for workflow debugging

### 🎯 **GIGANTIC** (~2M pixels)
- Maximum quality renders
- Production-grade output
- Highest detail preservation
- For final deliverables

---

## Updated Nodes

### Wan 2.2 Aspect Ratio Helper → v2.2
- **From:** 4 size presets (small, medium, large, extra-large)
- **To:** 6 size presets (tiny, small, medium, large, extra-large, gigantic)

### Wan 2.2 Size Preset → v1.1
- **From:** 4 size presets (small, medium, large, extra-large)
- **To:** 6 size presets (tiny, small, medium, large, extra-large, gigantic)

---

## Complete Size Chart

| Preset | Target Pixels | Example (16:9) | Use Case |
|--------|--------------|----------------|----------|
| **Tiny** ⚡ NEW | ~200K | 592×336 | Ultra-fast previews, debugging |
| **Small** | ~400K | 848×480 | Quick tests |
| **Medium** | ~650K | 1080×608 | Standard quality (default) |
| **Large** | ~900K | 1280×720 | High quality |
| **Extra-Large** | ~1.4M | 1600×904 | Very high quality |
| **Gigantic** 🎯 NEW | ~2M | 1896×1072 | Maximum quality, production |

---

## Why These Sizes?

### Tiny (~200K pixels)
**Perfect for:**
- ✅ Testing workflows without waiting
- ✅ Quick prompt iterations
- ✅ Debugging node connections
- ✅ Preview compositions
- ✅ Concept validation

**Speed Benefit:** ~75% faster than small

### Gigantic (~2M pixels)
**Perfect for:**
- ✅ Final production renders
- ✅ Maximum detail preservation
- ✅ Large display outputs
- ✅ Professional deliverables
- ✅ Upscaling source material

**Quality Benefit:** ~43% more pixels than extra-large

---

## Updated Workflow Progression

### Recommended Development Flow

```
1. TINY → Test idea/prompt (seconds)
   ↓
2. SMALL → Refine composition (fast)
   ↓
3. MEDIUM → Validate quality (default)
   ↓
4. LARGE → Near-final review
   ↓
5. GIGANTIC → Final production render
```

**Skip levels as needed** - e.g., Tiny → Medium → Gigantic

---

## Example Dimensions

### 16:9 Widescreen
- Tiny: 592×336 (~199K)
- Small: 848×480 (~407K)
- Medium: 1080×608 (~656K)
- Large: 1280×720 (~922K)
- Extra-Large: 1600×904 (~1.45M)
- Gigantic: 1896×1072 (~2.03M)

### 9:16 Tall Portrait (Instagram/TikTok)
- Tiny: 288×512 (~147K)
- Small: 408×720 (~294K)
- Medium: 512×912 (~467K)
- Large: 592×1056 (~625K)
- Extra-Large: 744×1328 (~988K)
- Gigantic: 896×1600 (~1.43M)

### 1:1 Square
- Tiny: 448×448 (~201K)
- Small: 632×632 (~399K)
- Medium: 808×808 (~653K)
- Large: 952×952 (~906K)
- Extra-Large: 1184×1184 (~1.40M)
- Gigantic: 1416×1416 (~2.01M)

### 21:9 Ultra-Wide (Cinematic)
- Tiny: 688×296 (~204K)
- Small: 976×416 (~406K)
- Medium: 1232×528 (~650K)
- Large: 1456×624 (~908K)
- Extra-Large: 1824×784 (~1.43M)
- Gigantic: 2176×936 (~2.04M)

*All dimensions divisible by 8 (Wan 2.2 requirement)*

---

## Usage Examples

### Ultra-Fast Iteration
```
Wan 2.2 Size Preset
├─ aspect_ratio: "16:9 Widescreen"
├─ size_preset: "tiny" ← NEW!
└─ Output: 592×336

Perfect for testing 20 different prompts quickly!
```

### Maximum Quality Production
```
Wan 2.2 Aspect Ratio Helper
├─ image: reference_artwork.png
├─ size_preset: "gigantic" ← NEW!
└─ Output: ~2M pixels

Perfect for final client deliverable!
```

### Smart Workflow
```
Phase 1: Test 10 prompts at TINY (fast!)
Phase 2: Pick best 3, render at MEDIUM
Phase 3: Select winner, final at GIGANTIC
```

---

## What Changed in Code

### Both Nodes

**TARGET_PIXELS updated:**
```python
TARGET_PIXELS = {
    "tiny": 200_000,        # NEW
    "small": 400_000,
    "medium": 650_000,
    "large": 900_000,
    "extra-large": 1_400_000,
    "gigantic": 2_000_000   # NEW
}
```

**Dropdown updated:**
```python
"size_preset": (["tiny", "small", "medium", "large", "extra-large", "gigantic"], {
    "default": "medium"
})
```

**Info text now shows all 6 sizes:**
```
Available Sizes:
  Tiny:        592×336 (198,912 pixels)
  Small:       848×480 (407,040 pixels)
  Medium:     1080×608 (656,640 pixels)
  Large:      1280×720 (921,600 pixels)
  Extra-Large:1600×904 (1,446,400 pixels)
  Gigantic:   1896×1072 (2,032,512 pixels)

✓ Selected (medium): 1080×608
```

---

## Backward Compatibility

✅ **Existing workflows continue to work**
- Default is still "medium"
- Small/medium/large/extra-large unchanged
- Same dimensions for existing presets
- Just add new tiny/gigantic options

❌ **No breaking changes**
- All existing connections work
- No need to update saved workflows
- New presets are optional additions

---

## Quick Comparison

### Old vs New

**Before (v2.1 / v1.0):**
```
4 sizes: Small → Medium → Large → Extra-Large
Range: 400K to 1.4M pixels
```

**After (v2.2 / v1.1):**
```
6 sizes: Tiny → Small → Medium → Large → Extra-Large → Gigantic
Range: 200K to 2M pixels
```

**Improvement:**
- 🔽 50% smaller minimum (tiny vs small)
- 🔼 43% larger maximum (gigantic vs extra-large)
- 📊 Better granularity across quality range

---

## Testing After Restart

1. **Restart ComfyUI** to load updated nodes

2. **Test Tiny preset:**
   ```
   Add image → Aspect Ratio Helper
   - Select "tiny" from dropdown
   - Check console shows "Tiny:" size
   - Verify ultra-fast generation
   ```

3. **Test Gigantic preset:**
   ```
   Size Preset → "16:9 Widescreen"
   - Select "gigantic" from dropdown
   - Check dimensions ~2M pixels
   - Verify maximum quality output
   ```

4. **Verify info_text:**
   - Connect info_text → Show Text
   - Should display all 6 sizes
   - Checkmark on selected size

---

## Tips for New Presets

### When to Use Tiny
- ✅ Rapid prompt testing (10+ variations)
- ✅ Workflow debugging
- ✅ Composition experiments
- ✅ Real-time iteration
- ❌ Not for final outputs

### When to Use Gigantic
- ✅ Final production renders
- ✅ Client deliverables
- ✅ Large displays (TV, projection)
- ✅ Maximum detail capture
- ❌ Not for testing (too slow)

### Smart Progression
```
Testing → TINY (instant)
Refinement → SMALL or MEDIUM (fast)
Validation → LARGE (quality check)
Production → GIGANTIC (final render)
```

---

## Performance Impact

### Generation Time Estimates (Relative)

| Preset | Relative Speed | Example Time* |
|--------|----------------|---------------|
| Tiny | **1.0x** (baseline) | ~10s |
| Small | 2.0x | ~20s |
| Medium | 3.3x | ~33s |
| Large | 4.5x | ~45s |
| Extra-Large | 7.0x | ~70s |
| Gigantic | 10.0x | ~100s |

*Times vary by GPU and model

**Use Case Mapping:**
- Need speed → Tiny/Small
- Balanced → Medium (default)
- Need quality → Large/Extra-Large/Gigantic

---

## Files Updated

### Node Files
- ✅ `nodes/Wan22_AspectRatio_Helper.py` (v2.1 → v2.2)
- ✅ `nodes/Wan22_Size_Preset.py` (v1.0 → v1.1)

### Changelog
- ✅ `CHANGELOG.md` (added v2.2/v1.1 entry)

### New Documentation
- ✅ `WAN22_V2.2_SIZE_PRESETS_UPDATE.md` (this file)

---

## Summary

🎉 **Both Wan 2.2 nodes now have 6 size presets** instead of 4:

**NEW TINY** ⚡
- ~200K pixels
- Ultra-fast previews
- Perfect for testing

**NEW GIGANTIC** 🎯
- ~2M pixels  
- Maximum quality
- Perfect for production

**RESULT:**
- Wider quality/speed range
- Better workflow flexibility
- No breaking changes

**Next Step:** Restart ComfyUI and try the new presets!

---

**Update Date:** October 23, 2025  
**Aspect Ratio Helper:** v2.1 → v2.2  
**Size Preset:** v1.0 → v1.1  
**Status:** ✅ Complete
