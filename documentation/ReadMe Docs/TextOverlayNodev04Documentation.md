# Text Overlay Node v04 Documentation

## Overview

The Text Overlay Node is a versatile ComfyUI component that allows you to overlay customizable text on images with extensive styling options. It supports various text effects, formatting, and blending modes to create professional-looking text overlays for any ComfyUI workflow.

## Key Features

- **Rich Text Styling**: Customize font, size, color, alignment, and spacing
- **Special Effects**: Apply gradient, metal, neon, and emboss effects to text
- **Layer Blending**: Various blend modes for integrating text with images
- **Shadow & Outline**: Add depth with customizable text shadows and outlines
- **Dynamic Text Wrapping**: Automatic wrapping based on width or character count
- **Font Preview**: Browse and preview all available system fonts
- **External Text Support**: Load text content from TXT or Markdown files
- **Transparent Background**: Create text overlays with transparent backgrounds
- **Position Control**: Precise positioning with percentage-based offsets

## Input Parameters

### Required Inputs

#### Basic Text Settings
- **text**: Text content to display (supports multi-line). Leave empty to load from file.
- **width**: Width of the output image in pixels (16-8192).
- **height**: Height of the output image in pixels (16-8192).
- **font**: Font to use for text rendering (uses system fonts).
- **font_size**: Size of the font in pixels (8-256).
- **color**: Text color (hex code or color name, e.g., "#FFFFFF" or "red").
- **align**: Horizontal text alignment ("left", "center", "right").
- **v_align**: Vertical text alignment ("top", "middle", "bottom").
- **transparent_background**: Whether to use a transparent background.
- **background_color**: Background color when not using transparent background.
- **background_opacity**: Background opacity percentage (0-100%).
- **x_offset_pct**: Horizontal position offset as percentage of width (-100.0 to 100.0%).
- **y_offset_pct**: Vertical position offset as percentage of height (-100.0 to 100.0%).
- **line_spacing**: Multiplier for space between lines (0.5-3.0).
- **padding**: Margin space around text in pixels (0-500).
- **wrap_width**: Maximum characters per line (0 = auto based on width).

### Optional Inputs

#### Reference and Text Source
- **reference_image**: Optional image to get dimensions from.
- **text_file**: Path to .txt or .md file to load text from.

#### Text Styling
- **bold**: Apply bold styling to text.
- **italic**: Apply italic styling to text.
- **outline_color**: Color for text outline (leave empty for no outline).
- **outline_width**: Width of outline in pixels (1-10).
- **shadow**: Enable drop shadow behind text.
- **shadow_color**: Color for drop shadow.
- **shadow_offset**: Shadow distance from text in pixels (1-10).
- **text_effect**: Special effect to apply to text:
  - **none**: No special effect
  - **gradient**: Vertical color gradient
  - **metal**: Metallic embossed appearance
  - **neon**: Bright center with glowing edges
  - **emboss**: 3D embossed effect
- **gradient_color**: Second color for gradient effect.
- **layer_blend_mode**: How the text layer blends with background:
  - **normal**: Standard overlay without special blending
  - **multiply**: Darkens where text is applied
  - **screen**: Lightens where text is applied
  - **overlay**: Enhances contrast while preserving highlights and shadows

#### Font Preview Options
- **show_font_preview**: Generate a preview showing all available fonts.
- **preview_text**: Sample text to use for font preview.
- **fonts_per_page**: Number of fonts to show per page in preview.
- **preview_page**: Current page to show in font preview.

## Output

- **image**: Final rendered image with text overlay.
- **preview**: Same as image, or font preview when show_font_preview is enabled.

## Detailed Parameter Descriptions

### Text Options

- **text**: The main text content to display. Supports multiple lines and can be left empty if loading from a file.
- **text_file**: Path to a text (.txt) or Markdown (.md) file to load content from. Markdown will be converted to plain text.
- **wrap_width**: Controls how text wrapping works:
  - **0**: Automatically wraps based on available width
  - **>0**: Wraps when reaching the specified number of characters per line

### Font and Styling

- **font**: Select from available system fonts. The node scans your system for installed fonts.
- **font_size**: Controls the size of the text in pixels.
- **bold**/**italic**: Toggles for text weight and style (may not work with all fonts).
- **color**: Text color using hex code (e.g., "#FF0000" for red) or standard color names.
- **line_spacing**: Controls vertical distance between lines as a multiplier of font size.
- **padding**: Space between text and image edges in pixels.

### Text Effects

- **outline_color**/**outline_width**: Creates an outline around text characters.
- **shadow**/**shadow_color**/**shadow_offset**: Adds a drop shadow effect.
- **text_effect**: Special rendering effects:
  - **gradient**: Blends from text color to gradient_color vertically
  - **metal**: Creates a metallic embossed appearance with lighting
  - **neon**: Creates a bright center with colored glow effect
  - **emboss**: Adds a 3D raised effect to text

### Positioning

- **align**: Controls horizontal text alignment within the image.
- **v_align**: Controls vertical text alignment within the image.
- **x_offset_pct**/**y_offset_pct**: Fine-tune position using percentage of image dimensions. Negative values move left/up, positive values move right/down.

### Background Options

- **transparent_background**: When enabled, creates text with transparent background.
- **background_color**: Color to use when transparent_background is disabled.
- **background_opacity**: Controls transparency of the background (0-100%).
- **layer_blend_mode**: How the text integrates with background or reference image:
  - **normal**: Standard overlay without special effects
  - **multiply**: Darkens image where text appears (good for light backgrounds)
  - **screen**: Lightens image where text appears (good for dark backgrounds)
  - **overlay**: Increases contrast while preserving highlights and shadows

### Font Preview System

- **show_font_preview**: When enabled, generates a preview image showing available fonts.
- **preview_text**: Text sample to display for each font in the preview.
- **fonts_per_page**: Controls how many fonts appear on each preview page.
- **preview_page**: Navigate between pages of the font preview.

## Usage Examples

### Basic Text Overlay
Connect the node to your workflow and set basic parameters like text, font, size, and color to create a simple text overlay.

### Styled Title with Shadow
Create a title with shadow effect by enabling the shadow option, adjusting shadow_offset, and using a contrasting shadow_color.

### Gradient Text Effect
Set text_effect to "gradient", choose a base color and gradient_color to create a smooth vertical color transition.

### Neon Glow Text
Set text_effect to "neon" and use bright colors to create text with a glowing effect, perfect for artistic compositions.

### Watermarking
Use transparent_background with position offsets and reduced opacity to create subtle watermarks on images.

### Font Selection
Enable show_font_preview to browse through available system fonts and choose the perfect typography for your project.

### Loading from Markdown
Set text_file to a Markdown document path to render formatted content as plain text overlay.

## Compatibility Notes

- The node automatically adapts to ComfyUI's tensor format requirements.
- Font availability depends on the system where ComfyUI is running.
- When using reference_image, the text overlay will match its dimensions.
- Text effects work best with larger font sizes.
- For best results with transparent backgrounds, use PNG format when saving.

## Advanced Tips

- Use blending modes to integrate text with specific image types:
  - multiply: Works well for adding text to light backgrounds
  - screen: Ideal for adding text to dark backgrounds
  - overlay: Creates high-contrast text that adapts to background brightness
- When working with long text content, use a text file instead of entering directly in the node.
- The font preview system helps quickly identify which fonts look best for your project.
- For most readable text, use contrasting colors with outlines or shadows.
- Position offsets can be used to create precise alignments or interesting compositions.

## Troubleshooting

- If fonts don't appear properly, check system font directories.
- For performance reasons, extremely large text on small images may appear cut off.
- If the text wrapping isn't working as expected, adjust the wrap_width parameter.
- When using reference_image, ensure it's connected properly to provide dimensions.

## Technical Details

The node uses PIL (Python Imaging Library) for text rendering and supports system fonts through automatic detection. The blending modes use standard Porter-Duff compositing algorithms for high-quality results.