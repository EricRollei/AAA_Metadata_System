# 🎨 Eric Load Image with Layers - Quick Start

## 🚀 Installation

1. **Install psd-tools** (for PSD layer support):
   ```bash
   pip install psd-tools
   ```

2. **Restart ComfyUI**

3. Find node: `🎨 Eric Load Image with Layers`

## 📖 Basic Usage

### Default: Load Flattened Image
```
[Eric Load Image with Layers]
  - image: (click to select)
  - load_mode: composite
```
→ Works exactly like standard LoadImage!

### Load All PSD Layers as Batch
```
[Eric Load Image with Layers]
  - image: my_artwork.psd
  - load_mode: all_layers
```
→ Outputs batch with each layer as separate image

### Load Specific Layer by Name
```
[Eric Load Image with Layers]
  - image: character.psd
  - load_mode: layer_by_name
  - layer_name: "Character Base"
```
→ Outputs only the named layer

### Load Specific Layer by Index
```
[Eric Load Image with Layers]
  - image: scene.psd
  - load_mode: layer_by_index
  - layer_index: 0
```
→ Outputs the first layer (0-based indexing)

## 🎯 Outputs

1. **image**: IMAGE tensor (single or batch)
2. **mask**: MASK tensor (alpha channels)
3. **filename**: STRING (e.g., "artwork.psd")
4. **full_path**: STRING (full file path)
5. **layer_info**: STRING (layer details)

## 🔄 Load Modes

| Mode | Description | Output |
|------|-------------|--------|
| `composite` | Flattened image (default) | Single image |
| `all_layers` | All layers | Batch of images |
| `layer_by_name` | Specific layer by name | Single image |
| `layer_by_index` | Specific layer by number | Single image |
| `visible_only` | Only visible layers | Batch of images |

## 💡 Common Workflows

### Workflow 1: Edit Individual Layers
```
[Load with Layers] → mode: all_layers
   ↓
[Batch Split]
   ↓
[Process Each] → upscale, denoise, etc.
   ↓
[Batch Combine]
   ↓
[Eric Save Image] → save as layered PSD
```

### Workflow 2: Round-Trip Editing
```
[Your Process] → [Eric Save Image v099d]
                   - format: psd
                   - with overlay/mask layers
                   ↓
              Layered PSD saved
                   ↓
[Eric Load Image with Layers]
  - mode: layer_by_name
  - extract specific layer
                   ↓
[Edit that layer]
                   ↓
[Save again with layers]
```

### Workflow 3: Quick Layer Check
```
[Eric Load Image with Layers]
  - mode: all_layers
  - load_mode: composite for preview
  ↓
Check layer_info output to see:
  "Total Layers: 5 | Names: BG, Char, FX, Shadow, Highlight"
```

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "psd-tools not installed" | `pip install psd-tools` |
| Layer not found | Check spelling (case-sensitive!) |
| Empty output | Try `visible_only` mode |
| SVG won't load | `pip install cairosvg` |

## 📦 Supported Formats

- ✅ **JPG, PNG, BMP, GIF** - All standard features
- ✅ **TIFF** - Multi-page support (loads as batch)
- ✅ **WebP** - Animated WebP support
- ✅ **SVG** - Rasterized to 1024x1024 (requires cairosvg)
- ✅ **PSD** - Full layer support (requires psd-tools)

## ⚡ Performance Tips

- Use `composite` for fastest loading
- Use `layer_by_name` or `layer_by_index` for specific layers
- Use `all_layers` only when you need every layer
- Use `visible_only` to skip hidden layers

## 🆚 When to Use Each Node

### Use **Eric Load Image Extended** when:
- ✅ You just need flattened images
- ✅ You want extended format support (TIFF, WebP, SVG)
- ✅ You don't need PSD layer access
- ✅ You want the fastest/simplest option

### Use **Eric Load Image with Layers** when:
- ✅ You work with layered PSDs
- ✅ You need to load specific layers
- ✅ You're round-tripping with Eric Save Image v099d
- ✅ You need batch processing of all layers
- ✅ You want layer metadata info

## 🎓 Pro Tips

1. **Always check layer_info output** to see what layers are available
2. **Install psd-tools** for full functionality
3. **Use composite mode first** to ensure PSD loads correctly
4. **Layer names are case-sensitive** - check spelling!
5. **Groups are expanded automatically** - all nested layers are found

## 📝 Example: Complete Round-Trip

```
STEP 1 - CREATE:
[Text to Image] → [Eric Save Image v099d]
  - format: psd
  - overlay_layer_1: watermark
  - mask_layer_1: selection
  → Saves: artwork.psd (3 layers)

STEP 2 - LOAD ALL:
[Eric Load Image with Layers]
  - image: artwork.psd
  - mode: all_layers
  → Outputs batch: [main, watermark, selection]

STEP 3 - EDIT ONE:
[Eric Load Image with Layers]
  - image: artwork.psd
  - mode: layer_by_name
  - layer_name: "watermark"
  → Outputs just watermark layer
  ↓
[Edit Watermark]
  ↓
[Eric Save Image v099d]
  - save edited version with layers
```

## 🔗 Related Documentation

- Full documentation: `README_LOAD_IMAGE_LAYERS.md`
- Basic node guide: `README_LOAD_IMAGE.md`
- Save node: Check `eric_metadata_save_image_v099d` docs

---

**Perfect companion to Eric Save Image v099d!** 🎨✨
