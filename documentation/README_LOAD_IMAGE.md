# Eric Load Image Extended Node

## Overview
This custom ComfyUI node extends the standard LoadImage node with additional features:

### Features
- ✅ **File Picker Dialog**: Click on the image pane to open a Windows file system dialog for easy image selection
- ✅ **Extended Format Support**: 
  - Standard formats: JPG, PNG, BMP, GIF
  - **NEW**: TIFF (.tiff, .tif)
  - **NEW**: WebP (.webp)
  - **NEW**: SVG (.svg) - Vector images are rasterized to 1024x1024
  - **NEW**: PSD (.psd) - Photoshop files
- ✅ **Additional Outputs**:
  - `image`: Standard IMAGE tensor
  - `mask`: Alpha channel mask
  - `filename`: Just the filename (e.g., "myimage.jpg")
  - `full_path`: Complete file path (e.g., "C:/ComfyUI/input/myimage.jpg")

## Usage

1. Add the node to your workflow: Search for "Eric Load Image Extended" or "📁 Eric Load Image Extended"
2. Click on the image selector dropdown or image preview area
3. Browse to select your image file
4. The node outputs:
   - **image**: The loaded image as a tensor
   - **mask**: Alpha channel (or empty mask if no alpha)
   - **filename**: Name of the file
   - **full_path**: Complete path to the file

## Use Cases

### Get Filename for Metadata
Connect the `filename` output to other nodes that need the original filename for metadata tracking or file organization.

### Get Full Path for File Operations
Use the `full_path` output when you need to:
- Create sidecar files in the same directory
- Reference the original file location
- Build file organization systems

### Load Special Formats
- **TIFF**: Load high-quality TIFF images with multiple layers/pages
- **WebP**: Load modern WebP compressed images
- **SVG**: Load vector graphics (automatically rasterized)
- **PSD**: Load Photoshop files (flattened to single layer)

## Dependencies

### Basic Usage (JPG, PNG, BMP, GIF, TIFF, WebP, PSD)
No additional dependencies needed! These formats are supported by PIL/Pillow, which is already included in ComfyUI.

### SVG Support (Optional)
To properly render SVG files, install one of these packages:

**Option 1: CairoSVG (Recommended)**
```bash
pip install cairosvg
```

**Option 2: svglib + reportlab**
```bash
pip install svglib reportlab
```

**Fallback**: If neither package is installed, SVG files will load as a gray placeholder image.

## Examples

### Example 1: Basic Image Loading with Metadata Tracking
```
[Eric Load Image Extended] → image → [Your Processing Nodes]
                         → filename → [Text Display or Save]
```

### Example 2: Process and Save with Original Filename
```
[Eric Load Image Extended] → image → [Image Processing]
                         → filename → [Custom Save Node]
```

### Example 3: Load SVG Logo
```
[Eric Load Image Extended (SVG file)] → image → [Image Composite]
```

## Technical Notes

### Multi-frame Images
- GIF animations: All frames are loaded as a batch
- Multi-page TIFF: All pages are loaded as a batch

### Color Spaces
- All images are converted to RGB
- Alpha channels are extracted as separate masks
- 16-bit images are normalized to 8-bit

### File Picker Behavior
The file picker works through ComfyUI's `image_upload` parameter, which:
1. Shows files from the ComfyUI `input` folder by default
2. Allows uploading new files
3. Automatically refreshes the file list

## Comparison with Standard LoadImage

| Feature | Standard LoadImage | Eric Load Image Extended |
|---------|-------------------|-------------------------|
| JPG, PNG, BMP, GIF | ✅ | ✅ |
| TIFF | ❌ | ✅ |
| WebP | ❌ | ✅ |
| SVG | ❌ | ✅ |
| PSD | ❌ | ✅ |
| Filename output | ❌ | ✅ |
| Full path output | ❌ | ✅ |
| File picker dialog | ✅ | ✅ |

## Troubleshooting

### Issue: SVG files appear as gray boxes
**Solution**: Install SVG rendering library:
```bash
pip install cairosvg
```

### Issue: PSD files won't load
**Solution**: Ensure you have Pillow 9.1.0 or higher:
```bash
pip install --upgrade Pillow
```

### Issue: Node doesn't appear in menu
**Solution**: 
1. Restart ComfyUI
2. Check console for error messages
3. Verify the file is in `custom_nodes/Metadata_system/nodes/`

## Version History

- **v1.0.0** (2025-10-18): Initial release
  - Extended format support (TIFF, WebP, SVG, PSD)
  - Filename and path outputs
  - File picker integration

## Author
Eric's Metadata System
