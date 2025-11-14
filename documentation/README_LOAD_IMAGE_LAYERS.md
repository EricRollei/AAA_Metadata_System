# Eric Load Image with Layers - Complete Guide

## Overview
This is the **advanced version** of the load image node that provides full PSD layer support, perfectly complementing the `eric_metadata_save_image_v099d` node.

## 🎯 Key Features

### Layer Loading Modes
- **composite** (default): Load flattened/merged image (like standard LoadImage)
- **all_layers**: Load all layers as separate images in a batch
- **layer_by_name**: Load a specific layer by its name
- **layer_by_index**: Load a specific layer by its position (0-based)
- **visible_only**: Load only visible layers from the PSD

### Additional Features
- ✅ File picker dialog (click to browse)
- ✅ Extended format support: TIFF, WebP, SVG, PSD
- ✅ Outputs: image, mask, filename, full_path, **layer_info**
- ✅ Multi-frame support (GIF, multi-page TIFF)
- ✅ Alpha channel extraction for all formats

## 📦 Dependencies

### Required (Should already be installed with ComfyUI)
- PIL/Pillow
- torch
- numpy

### Optional for PSD Layer Support
```bash
pip install psd-tools
```

**Without psd-tools**: PSD files still load but only as flattened composite images (like standard LoadImage).

**With psd-tools**: Full layer support with all modes available! ✨

### Optional for SVG Support
```bash
pip install cairosvg
```

## 🎨 Use Cases

### Use Case 1: Load Individual Layers for Processing
```
[Eric Load Image with Layers]
  - mode: layer_by_name
  - layer_name: "Character"
  ├─ image → [Process Character] → [Save]
  └─ mask → [Mask Operations]
```

### Use Case 2: Load All Layers as Batch
```
[Eric Load Image with Layers]
  - mode: all_layers
  └─ image (batch of all layers) → [Batch Processing] → [Combine]
```

### Use Case 3: Round-Trip with Save Node
```
[Your Workflow] → [Eric Save Image v099d]
                  - format: psd
                  - overlay layers
                  - mask layers
                  ↓
                  Saved PSD with layers
                  ↓
[Eric Load Image with Layers] → [Edit Individual Layers]
  - mode: layer_by_name
  - or: all_layers
```

### Use Case 4: Extract Specific Layer
```
[Eric Load Image with Layers]
  - mode: layer_by_index
  - layer_index: 2  (third layer)
  └─ image → [Your Processing]
```

## 📋 Parameters

### Required
- **image**: File to load (supports JPG, PNG, BMP, GIF, TIFF, WebP, PSD, SVG)
- **load_mode**: How to handle layers
  - `composite`: Flattened image (default, works for all formats)
  - `all_layers`: All layers as batch (PSD only, needs psd-tools)
  - `layer_by_name`: Load specific layer by name (PSD only)
  - `layer_by_index`: Load specific layer by index (PSD only)
  - `visible_only`: Only visible layers (PSD only)

### Optional
- **layer_name**: Name of layer to load (for `layer_by_name` mode)
- **layer_index**: Index of layer (0-based, for `layer_by_index` mode)

## 🔄 Outputs

1. **image**: IMAGE tensor
   - Single image for: composite, layer_by_name, layer_by_index
   - Batch of images for: all_layers, visible_only
2. **mask**: MASK tensor (alpha channel or empty)
3. **filename**: STRING - just the filename (e.g., "artwork.psd")
4. **full_path**: STRING - complete path
5. **layer_info**: STRING - detailed information about loaded layers
   - Example: `"Format: PSD | Mode: all_layers | Total Layers: 5 | Layer Names: Main Image, Overlay 1, Overlay 2..."`

## 📖 Examples

### Example 1: Load PSD Composite (Default Behavior)
```
[Eric Load Image with Layers]
  - image: "my_artwork.psd"
  - load_mode: composite
  
Output: Flattened image (just like standard LoadImage)
```

### Example 2: Load All Layers for Batch Processing
```
[Eric Load Image with Layers]
  - image: "layered_design.psd"
  - load_mode: all_layers
  
Output: 
  - image: Batch containing all layers [Layer1, Layer2, Layer3, ...]
  - mask: Corresponding alpha masks for each layer
  - layer_info: "Format: PSD | Mode: all_layers | Total Layers: 5 | ..."
```

### Example 3: Load Specific Layer by Name
```
[Eric Load Image with Layers]
  - image: "character_sheet.psd"
  - load_mode: layer_by_name
  - layer_name: "Character Base"
  
Output: Just the "Character Base" layer
```

### Example 4: Load Background Layer (First Layer)
```
[Eric Load Image with Layers]
  - image: "scene.psd"
  - load_mode: layer_by_index
  - layer_index: 0
  
Output: The first layer (index 0)
```

### Example 5: Load Only Visible Layers
```
[Eric Load Image with Layers]
  - image: "work_in_progress.psd"
  - load_mode: visible_only
  
Output: Batch of only layers that are marked as visible in Photoshop
```

## 🎯 Integration with Save Node

This node is designed to work perfectly with `eric_metadata_save_image_v099d`:

### Round-Trip Workflow
```
1. CREATE LAYERS:
   [Generate Images] → [Eric Save Image v099d]
     - main image
     - overlay_layer_1
     - overlay_layer_2
     - mask_layer_1
     → Saves as PSD with all layers

2. LOAD LAYERS BACK:
   [Eric Load Image with Layers]
     - mode: all_layers
     → Loads all layers as separate images
   
3. EDIT INDIVIDUAL LAYERS:
   [Split Batch] → [Process Each Layer] → [Recombine]
   
4. SAVE AGAIN:
   [Eric Save Image v099d]
     → Saves edited version with layers preserved
```

## 🔍 Layer Information Output

The `layer_info` output provides detailed information:

```
Format: PSD | Mode: all_layers | Total Layers: 5 | Layer Names: Background, Character, Overlay 1, Shadow, Highlights
```

You can use this to:
- Display in a text node to see what layers are available
- Debug layer loading
- Verify the correct layers were loaded

## ⚡ Performance Notes

### Loading Modes Speed (Fastest to Slowest)
1. **composite**: ⚡⚡⚡ Very fast (uses PIL composite)
2. **layer_by_index**: ⚡⚡ Fast (loads single layer)
3. **layer_by_name**: ⚡⚡ Fast (loads single layer)
4. **visible_only**: ⚡ Moderate (filters and loads subset)
5. **all_layers**: ⚡ Slower (loads every layer individually)

### Recommendations
- Use `composite` for simple workflows (fastest)
- Use `layer_by_name` or `layer_by_index` when you need specific layers
- Use `all_layers` when you need to process all layers as a batch
- Use `visible_only` to skip hidden/disabled layers

## 🐛 Troubleshooting

### Issue: "psd-tools not installed" warning
**Solution**: 
```bash
pip install psd-tools
```
**Workaround**: Node still works with `composite` mode without psd-tools

### Issue: Layer not found (layer_by_name)
**Symptoms**: Node falls back to composite mode with warning
**Solutions**:
- Check layer name spelling (case-sensitive!)
- Use `all_layers` mode first to see all layer names in `layer_info` output
- Try `layer_by_index` instead

### Issue: Empty/black output with all_layers
**Cause**: All layers might be hidden or empty
**Solution**: Try `visible_only` mode or check PSD in Photoshop

### Issue: SVG appears as gray box
**Solution**: Install cairosvg: `pip install cairosvg`

## 🆚 Comparison with Standard Node

| Feature | Standard LoadImage | Eric Load Image Extended | Eric Load Image **with Layers** |
|---------|-------------------|-------------------------|------------------------------|
| File picker | ✅ | ✅ | ✅ |
| JPG/PNG/GIF | ✅ | ✅ | ✅ |
| TIFF/WebP | ❌ | ✅ | ✅ |
| SVG | ❌ | ✅ | ✅ |
| PSD composite | ✅ | ✅ | ✅ |
| PSD layers | ❌ | ❌ | ✅✨ |
| Filename output | ❌ | ✅ | ✅ |
| Full path output | ❌ | ✅ | ✅ |
| Layer info output | ❌ | ❌ | ✅✨ |
| Load all layers | ❌ | ❌ | ✅✨ |
| Load by name | ❌ | ❌ | ✅✨ |
| Load by index | ❌ | ❌ | ✅✨ |

## 🔗 Related Nodes

- **eric_load_image_extended.py**: Simpler version without layer support (lighter weight)
- **eric_metadata_save_image_v099d.py**: Companion save node that creates layered PSDs

## 📝 Technical Details

### PSD Layer Structure
The node recognizes:
- Regular PixelLayers
- Nested layers in Groups
- Layer visibility flags
- Layer names and indices

### Layer Traversal
Groups are automatically expanded to find all PixelLayers:
```
PSD Root
├─ Layer 1 (PixelLayer) ← Loaded
├─ Group A
│  ├─ Layer 2 (PixelLayer) ← Loaded
│  └─ Layer 3 (PixelLayer) ← Loaded
└─ Layer 4 (PixelLayer) ← Loaded
```

### Fallback Behavior
If layer loading fails, the node:
1. Prints warning to console
2. Falls back to composite mode
3. Still returns valid image output
4. Updates layer_info with error details

## 🎓 Best Practices

1. **Always check layer_info output** when working with PSDs to see what was loaded
2. **Use composite mode** for simple workflows (faster and more compatible)
3. **Use all_layers mode** for batch operations on all layers
4. **Use layer_by_name** when you know the exact layer structure
5. **Install psd-tools** if you regularly work with layered PSDs

## 📜 Version History

- **v1.0.0** (2025-10-18): Initial release
  - Full PSD layer support via psd-tools
  - Multiple loading modes
  - Layer info output
  - Integration with eric_metadata_save_image_v099d

## 👨‍💻 Author
Eric's Metadata System

Perfect complement to the Save Image v099d node! 🎨
