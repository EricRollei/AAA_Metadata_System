# Eric Load Image Extended - Quick Start

## What It Does
A custom ComfyUI load image node that extends the standard LoadImage with:
- 🎯 Additional file format support (TIFF, WebP, SVG, PSD)
- 📄 Outputs the filename and full path
- 🖱️ File picker dialog (same as standard LoadImage)

## Installation
The node is already installed! Just restart ComfyUI.

## Location
File: `custom_nodes/Metadata_system/nodes/eric_load_image_extended.py`

## How to Use
1. Search for "Eric Load Image Extended" in the node menu
2. Click the image selector to pick an image
3. Connect outputs:
   - `image` → your processing nodes
   - `mask` → mask operations (if image has alpha channel)
   - `filename` → string nodes (e.g., for saving with same name)
   - `full_path` → path-based operations

## Outputs
- **image**: The loaded image (IMAGE type)
- **mask**: Alpha channel mask (MASK type)  
- **filename**: Just the file name, e.g., "photo.jpg" (STRING type)
- **full_path**: Complete path, e.g., "C:/ComfyUI/input/photo.jpg" (STRING type)

## Supported Formats
✅ Standard: JPG, JPEG, PNG, BMP, GIF
✅ Extended: TIFF, TIF, WebP, PSD, SVG

## Optional: SVG Support
For best SVG rendering, install:
```bash
pip install cairosvg
```
Without this, SVGs will load as gray placeholders (image will still work, just not pretty).

## Example Workflow
```
[Eric Load Image Extended]
  ├─ image → [Your Image Processing] → [Save Image]
  ├─ filename → [String Display]
  └─ full_path → [String Display]
```

## Notes
- All formats work with the standard PIL/Pillow (already in ComfyUI)
- Multi-frame images (GIF, multi-page TIFF) load all frames as a batch
- PSD files are flattened (merged layers)
- File picker shows files in ComfyUI's `input` folder

## Need More Info?
See: `README_LOAD_IMAGE.md` for complete documentation
