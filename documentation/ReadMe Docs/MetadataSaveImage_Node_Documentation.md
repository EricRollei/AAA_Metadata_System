# MetadataSaveImage Node Documentation

## Overview

The MetadataSaveImage node is an advanced output node for ComfyUI that extends the standard SaveImage functionality with comprehensive metadata embedding, multi-format support, and layer handling capabilities.

## Key Features

- **Multiple Format Support**: Save images in PNG, JPG, WEBP, TIFF, PSD, APNG, and SVG (with vtracer installed)
- **Metadata Embedding**: Embeds comprehensive metadata directly into image files
- **Color Profile Support**: Embed ICC color profiles for color accuracy
- **Layer Support**: Handle layers for formats that support them (TIFF, PSD)
- **16-bit Export**: High-precision 16-bit image export for formats that support it
- **Alpha Channel Handling**: Advanced transparency handling with multiple modes
- **Workflow Embedding**: Save ComfyUI workflow data directly in the image for later reloading
- **Animated PNG**: Create APNGs from multiple input images
- **Multiple Documentation Formats**: Generate XMP sidecar, JSON workflow, and text files

## Detailed Input Parameters

### Required Inputs

#### Basic Settings
- **images**: The ComfyUI image(s) to save. Accepts single images or batches.
- **filename_prefix**: Base name for saved files. Supports date formatting patterns like `%date:yyyy-MM-dd%`. Example: "MyProject_%date:MMM-dd-yyyy%" might output "MyProject_Apr-27-2025.png".
- **file_format**: Image format to save in:
  - **png**: Standard format with lossless compression and alpha support. Best for workflow embedding.
  - **jpg**: Lossy compression without alpha. Good for web sharing with smaller file sizes.
  - **webp**: Modern format with good compression and optional alpha.
  - **tiff**: Professional format supporting layers, 16-bit, and alpha.
  - **apng**: Animated PNG format for sequences of images.
  - **psd**: Adobe Photoshop format supporting layers (requires psd-tools).
  - **svg**: Scalable Vector Graphics format (requires vtracer installation).

### Optional Inputs

#### File Naming Options
- **include_project**: When enabled, adds the project name to the filename (set in the "project" field).
- **include_datetime**: When enabled, adds the current date and time to the filename in "YYYY-MM-DD_HH-MM-SS" format.

#### Layer-related Inputs
- **mask_layer_1/2**: Optional mask layers to include in TIFF or PSD outputs. Masks typically control visibility.
- **mask_1/2_name**: Custom names for the mask layers.
- **mask_1/2_blend_mode**: How the mask layer blends with layers below:
  - **normal**: Standard overlay without special blending
  - **multiply**: Darkens where mask is applied
  - **screen**: Lightens where mask is applied
  - **overlay**: Enhances contrast while preserving highlights and shadows
  - **add**: Adds pixel values, creating a brightening effect
  - **subtract**: Subtracts pixel values, creating a darkening effect
  - **difference**: Shows the absolute difference between layers
  - **darken**: Keeps the darker pixel values between layers
  - **lighten**: Keeps the lighter pixel values between layers
  - **color_dodge**: Brightens the base layer based on the blend layer
  - **color_burn**: Darkens the base layer based on the blend layer
- **mask_1/2_opacity**: Opacity for mask layers (0-255, with 0 being transparent and 255 being fully opaque).

- **overlay_layer_1/2**: Optional overlay layers to include in TIFF or PSD outputs. Overlays add content on top.
- **overlay_1/2_name**: Custom names for the overlay layers.
- **overlay_1/2_blend_mode**: Same options as mask blend modes, controlling how overlays interact with layers below.
- **overlay_1/2_opacity**: Opacity for overlay layers (0-255, with 0 being transparent and 255 being fully opaque).

#### Output Location Options
- **custom_output_directory**: Override default output location. For relative paths, use format like "images/subfolder". Leave empty to use default ComfyUI output folder.
- **output_path_mode**: How to interpret the custom output directory:
  - **Absolute Path**: Use exactly as specified (C:/path/to/folder)
  - **Subfolder in Output**: Create as a subfolder within ComfyUI's output directory
- **filename_format**: How to format sequential filenames:
  - **Default (padded zeros)**: Uses format like "prefix_001.png"
  - **Simple (file1.png)**: Uses format like "prefix1.png"

#### File Format and Quality Options
- **quality_preset**: Quality versus file size tradeoff:
  - **Best Quality**: Minimal compression, larger files
  - **Balanced**: Medium compression, good quality
  - **Smallest File**: Maximum compression, smaller files
- **color_profile**: Color profile to embed in the image:
  - **sRGB v4 Appearance**: Standard web color profile (recommended for most uses)
  - **sRGB v4 Preference**: Alternative sRGB profile
  - **sRGB v4 Display Class**: Display-oriented sRGB profile
  - **Adobe RGB**: Wider gamut for print work
  - **ProPhoto RGB**: Very wide gamut for professional photography
  - **None**: No color profile embedded
- **rendering_intent**: How colors are mapped when converting between color spaces:
  - **Perceptual**: Optimizes for natural-looking images
  - **Relative Colorimetric**: Maintains color accuracy, maps white point
  - **Saturation**: Preserves saturation, good for graphics
  - **Absolute Colorimetric**: Preserves exact colors, no white point adjustment
- **bit_depth**: Save in standard or high-precision format:
  - **8-bit**: Standard precision (256 levels per channel)
  - **16-bit**: High precision (65,536 levels per channel) for formats that support it

#### Alpha Channel Handling
- **alpha_mode**: How to handle transparency:
  - **auto**: Choose best option for the selected format
  - **premultiplied**: Alpha pre-multiplied with color (recommended for most uses)
  - **straight**: Alpha and color stored separately
  - **matte**: Composite onto background color (removes transparency)
- **matte_color**: Background color when saving with matte. Use color name or hex value (e.g., "#FFFFFF" for white).
- **save_alpha_separately**: When enabled, saves alpha channel as a separate image for formats that don't support transparency.

#### APNG Specific Options
- **apng_fps**: Frames per second for animated PNG (1-60).
- **apng_loops**: Number of animation loops (0 = infinite).

#### Secondary Format Options
- **additional_format**: Save a second copy in a different format (e.g., save both PNG and JPG).
- **additional_format_quality**: Quality setting for the additional format.
- **additional_format_suffix**: Suffix for the additional format filename (e.g., "_web" would create "image_web.jpg").
- **additional_format_embed_workflow**: Whether to embed workflow data in the additional format (PNG only).
- **additional_format_color_profile**: Color profile for the additional format.

#### SVG Specific Options
- **svg_colormode**: SVG color mode:
  - **color**: Preserve colors in vector output
  - **binary**: Convert to black and white
- **svg_hierarchical**: SVG hierarchy mode:
  - **stacked**: Layers overlap each other
  - **cutout**: Layers cut out from those below them
- **svg_mode**: SVG curve mode:
  - **spline**: Smooth curves (best quality)
  - **polygon**: Straight line segments
  - **none**: No curve smoothing

#### Metadata Content Options
- **enable_metadata**: Master switch for all metadata writing. When disabled, no structured metadata will be saved.
- **title**: Image title. Used in file browsers, DAM systems, and image search.
- **project**: Project name for organization. Useful for grouping related images.
- **description**: Image description/caption. Provides context about what the image shows.
- **creator**: Creator/artist name. Establishes authorship of the image.
- **copyright**: Copyright information. Protects your intellectual property.
- **keywords**: Comma-separated keywords/tags. Enables better searchability.
- **custom_metadata**: Custom metadata in JSON format. For advanced users who need specialized metadata structures.

#### Metadata Storage Options
- **save_embedded**: Save structured metadata directly inside the image file (separate from workflow embedding).
- **save_workflow_as_json**: Save ComfyUI workflow data as a separate JSON file. Enables re-importing into ComfyUI.
- **save_xmp**: Save metadata in XMP sidecar file (.xmp). Industry-standard metadata format readable by Adobe products.
- **save_txt**: Save human-readable metadata in text file (.txt). Easily accessible without special software.
- **save_db**: Save metadata to database (if configured). For advanced workflow tracking.

#### Advanced Options
- **save_individual_discovery**: Save individual discovery JSON and HTML files for each run (central discovery is always maintained).
- **debug_logging**: Enable detailed debug logging to console. Useful for troubleshooting.
- **embed_workflow**: Embed ComfyUI workflow graph data in the PNG file. Enables re-loading the exact workflow later (PNG only).

## Output

- **images**: The original images (pass-through for connecting to other nodes)
- **filepath**: Path to the saved image file (as a string)

## Usage Examples

### Basic Usage
Connect an image source to the node and set the filename_prefix. The image will be saved to the default ComfyUI output directory.

### Adding Metadata
Enable metadata embedding and fill in title, description, creator, copyright, and keywords to add rich metadata to your images.

### Using Layers
Connect mask or overlay layers to create layered output in formats that support it (TIFF, PSD). Set appropriate blend modes and opacity.

### Creating High-Quality Images
Set bit_depth to "16-bit" and color_profile to "ProPhoto RGB" for maximum quality when working with formats that support it.

### Saving to Custom Directory
Set custom_output_directory to a path like "project/subfolder" to organize your outputs. The directories will be created automatically.

### Creating Animated PNGs
Connect a batch of images to the node and set file_format to "apng". Adjust apng_fps to control animation speed.

## Dependencies

The node requires several Python libraries:
- torch, numpy, opencv-python (cv2)
- psd-tools (for PSD format)
- pillow (PIL)
- Optional: pypng (for better 16-bit support)
- Optional: vtracer (for SVG conversion)

## Notes

- For 16-bit output, "16-bit" bit_depth only works with PNG, TIFF
- When using mask or overlay layers, it's recommended to use TIFF or PSD format
- The node will warn but still save if using formats that don't support certain features
- Workflow embedding works with PNG format only
- Custom color profiles are loaded from system directories if available
- For SVG export, vtracer must be installed separately

## Advanced Workflow Integration

This node integrates with the Metadata system to track workflows, analyze settings, and create rich, searchable image exports. Combine with other metadata-aware nodes for maximum benefit.