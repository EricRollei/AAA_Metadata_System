"""
ComfyUI Node: Text Overlay Node v04
Description: Overlay text on an image with various effects and options.
    This node allows you to customize font, size, color, alignment, and more.
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 1.0.0
Date: [March 2025]
License: Dual License (Non-Commercial and Commercial Use)
Copyright (c) 2025 Eric Hiss. All rights reserved.

Dual License:
1. Non-Commercial Use: This software is licensed under the terms of the
   Creative Commons Attribution-NonCommercial 4.0 International License.
   To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/4.0/
   
2. Commercial Use: For commercial use, a separate license is required.
   Please contact Eric Hiss at [eric@historic.camera, eric@rollei.us] for licensing options.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT.

Dependencies:
This code depends on several third-party libraries, each with its own license:
- torch: BSD 3-Clause
- numpy: BSD 3-Clause
- textwrap: BSD 3-Clause
- markdown: BSD 3-Clause
- bs4 (BeautifulSoup): MIT License

"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageFilter, ImageChops
import os
import re
import markdown
import textwrap
from html.parser import HTMLParser
from bs4 import BeautifulSoup
import sys
import time
# Import color names dictionary
from .color_names import COLOR_NAMES

# Get system fonts directory based on OS
def get_system_fonts_directory():
    if sys.platform == "win32":
        return os.path.join(os.environ["WINDIR"], "Fonts")
    elif sys.platform == "darwin":  # macOS
        return "/System/Library/Fonts"
    else:  # Linux and others
        font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts")
        ]
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                return font_dir
        return "/usr/share/fonts"  # Default fallback

# Get a list of available system fonts
def get_available_fonts():
    fonts = []
    font_dir = get_system_fonts_directory()
    
    # Default fallback fonts in case system fonts discovery fails
    default_fonts = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia"]
    
    try:
        if os.path.exists(font_dir):
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if file.lower().endswith(('.ttf', '.otf')):
                        # Extract font name from filename by removing extension and special characters
                        font_name = os.path.splitext(file)[0]
                        font_name = re.sub(r'[_-]', ' ', font_name)  # Replace underscores and hyphens with spaces
                        fonts.append((font_name, os.path.join(root, file)))
            
            # Sort fonts by name
            fonts.sort(key=lambda x: x[0].lower())
        
        # If no fonts found, use default fonts
        if not fonts:
            print("No system fonts found, using default font list")
            fonts = [(font, font) for font in default_fonts]
    except Exception as e:
        print(f"Error discovering system fonts: {str(e)}")
        fonts = [(font, font) for font in default_fonts]
    
    return fonts

# HTML to plain text converter for markdown files
class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        
    def handle_data(self, data):
        self.text.append(data)
        
    def get_text(self):
        return ''.join(self.text)

# Text Overlay Node for ComfyUI
class TextOverlayNode:
    @classmethod
    def INPUT_TYPES(cls):
        fonts = get_available_fonts()
        font_names = [font[0] for font in fonts]
        
        # For testing if the font list is empty or failed
        if not font_names:
            font_names = ["Arial", "Helvetica", "Times New Roman"]
        
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Your text here", "placeholder": "Enter text or leave empty to load from file"}),
                "width": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 512, "min": 16, "max": 8192, "step": 1}),
                "font": (font_names, {"default": font_names[0] if font_names else "Arial"}),
                "font_size": ("INT", {"default": 32, "min": 8, "max": 256, "step": 1}),
                "color": ("STRING", {"default": "#FFFFFF", "placeholder": "Color name or hex code (e.g. #FF0000)"}),
                "align": (["left", "center", "right"], {"default": "center"}),
                "v_align": (["top", "middle", "bottom"], {"default": "middle"}),
                "transparent_background": ("BOOLEAN", {"default": True, "tooltip": "Use a transparent background (if false, uses background color)"}),
                "background_color": ("STRING", {"default": "#000000", "placeholder": "Background color name or hex code", "tooltip": "Background color when not using transparent background"}),
                "background_opacity": ("INT", {"default": 100, "min": 0, "max": 100, "step": 1, "tooltip": "Background opacity percentage (0-100%)"}),
                "x_offset_pct": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.1, "tooltip": "Horizontal offset as percentage of image width (-100% to 100%)"}),
                "y_offset_pct": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.1, "tooltip": "Vertical offset as percentage of image height (-100% to 100%)"}),
                "line_spacing": ("FLOAT", {"default": 1.2, "min": 0.5, "max": 3.0, "step": 0.1}),
                "padding": ("INT", {"default": 20, "min": 0, "max": 500, "step": 1}),
                "wrap_width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 1, "tooltip": "Max characters per line (0 = auto based on width)"}),
            },
            "optional": {
                "reference_image": ("IMAGE", {"tooltip": "Optional image to get dimensions from"}),
                "outline_color": ("STRING", {"default": "", "placeholder": "Leave empty for no outline or enter color"}),
                "outline_width": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "text_file": ("STRING", {"default": "", "placeholder": "Path to .txt or .md file (optional)"}),
                "bold": ("BOOLEAN", {"default": False}),
                "italic": ("BOOLEAN", {"default": False}),
                "shadow": ("BOOLEAN", {"default": False}),
                "shadow_color": ("STRING", {"default": "#000000"}),
                "shadow_offset": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "layer_blend_mode": (["normal", "multiply", "screen", "overlay"], {"default": "normal", "tooltip": "How the text layer should blend with background when composited"}),
                "text_effect": (["none", "gradient", "metal", "neon", "emboss"], {"default": "none", "tooltip": "Special effect to apply to text"}),
                "gradient_color": ("STRING", {"default": "#0000FF", "placeholder": "Second color for gradient effect"}),
                "show_font_preview": ("BOOLEAN", {"default": False, "tooltip": "Generate a preview image showing all available fonts"}),
                "preview_text": ("STRING", {"default": "The quick brown fox jumps over the lazy dog", "multiline": False, "tooltip": "Sample text to use for font preview"}),
                "fonts_per_page": ("INT", {"default": 30, "min": 5, "max": 100, "step": 1, "tooltip": "Number of fonts to show per page in font preview"}),
                "preview_page": ("INT", {"default": 1, "min": 1, "step": 1, "tooltip": "Current page to show in font preview"})
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("image", "preview")
    FUNCTION = "render_text"
    CATEGORY = "image/text"

    def __init__(self):
        self.fonts_cache = {}
        self.system_fonts = dict(get_available_fonts())
        self.debug = True  # Set to True to enable debug messages
        
        # Create a sorted list of fonts for preview
        self.sorted_fonts = sorted(self.system_fonts.keys(), key=lambda x: x.lower())

    def load_font(self, font_name, size, bold=False, italic=False):
        """Load font from system fonts with caching"""
        cache_key = f"{font_name}_{size}_{bold}_{italic}"
        
        # Check font cache first for performance
        if cache_key in self.fonts_cache:
            return self.fonts_cache[cache_key]
        
        try:
            # Try to get the font path from our discovered fonts
            if font_name in self.system_fonts:
                font_path = self.system_fonts[font_name]
                try:
                    font = ImageFont.truetype(font_path, size)
                    self.fonts_cache[cache_key] = font
                    return font
                except Exception as e:
                    if self.debug:
                        print(f"Error loading font {font_name} from {font_path}: {str(e)}")
            
            # Fallback: try loading by name directly (works on some systems)
            try:
                font = ImageFont.truetype(font_name, size)
                self.fonts_cache[cache_key] = font
                return font
            except:
                pass
            
            # Final fallback: use default font
            try:
                # Try platform-specific defaults
                if sys.platform == "win32":
                    for fallback in ["arial.ttf", "Arial.ttf", "verdana.ttf", "Verdana.ttf", "segoeui.ttf"]:
                        try:
                            font = ImageFont.truetype(os.path.join(os.environ["WINDIR"], "Fonts", fallback), size)
                            self.fonts_cache[cache_key] = font
                            return font
                        except:
                            continue
                elif sys.platform == "darwin":  # macOS
                    for fallback in [
                        "/System/Library/Fonts/Helvetica.ttc", 
                        "/System/Library/Fonts/Geneva.ttf",
                        "/Library/Fonts/Arial.ttf",
                        "/System/Library/Fonts/SFNSText.ttf"  # San Francisco font
                    ]:
                        try:
                            font = ImageFont.truetype(fallback, size)
                            self.fonts_cache[cache_key] = font
                            return font
                        except:
                            continue
                else:  # Linux and others
                    # Try common Linux font locations with more options
                    for fallback in [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 
                        "/usr/share/fonts/TTF/Arial.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
                    ]:
                        if os.path.exists(fallback):
                            try:
                                font = ImageFont.truetype(fallback, size)
                                self.fonts_cache[cache_key] = font
                                return font
                            except:
                                continue
            except:
                pass
            
            # Last resort: use PIL's default font
            if self.debug:
                print(f"Using default font as fallback for {font_name}")
            font = ImageFont.load_default()
            self.fonts_cache[cache_key] = font
            return font
            
        except Exception as e:
            if self.debug:
                print(f"Error loading font {font_name}: {str(e)}")
            font = ImageFont.load_default()
            self.fonts_cache[cache_key] = font
            return font

    def load_text_from_file(self, file_path):
        """Load text from a .txt or .md file"""
        if not file_path or not os.path.exists(file_path):
            return None
            
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if file_ext == '.md':
                # Convert Markdown to HTML, then extract plain text
                try:
                    # Try using BeautifulSoup for better HTML parsing if available
                    html = markdown.markdown(content)
                    soup = BeautifulSoup(html, 'html.parser')
                    return soup.get_text('\n')
                except ImportError:
                    # Fallback to simpler HTML parser
                    html = markdown.markdown(content)
                    parser = HTMLTextExtractor()
                    parser.feed(html)
                    return parser.get_text()
            else:
                # Assume it's a plain text file
                return content
        except Exception as e:
            print(f"Error loading text from file {file_path}: {str(e)}")
            return None

    def parse_color(self, color_str):
        """Parse color string to RGBA tuple"""
        if not color_str:
            return None
            
        try:
            # If it's a hex code with alpha
            if color_str.startswith('#') and len(color_str) == 9:
                r = int(color_str[1:3], 16)
                g = int(color_str[3:5], 16)
                b = int(color_str[5:7], 16)
                a = int(color_str[7:9], 16)
                return (r, g, b, a)
            
            # Check if it's in our color names dictionary
            if color_str in COLOR_NAMES:
                r, g, b = COLOR_NAMES[color_str]
                return (r, g, b, 255)  # Add alpha channel
                
            # If it's a regular color name or hex
            rgba = ImageColor.getrgb(color_str)
            
            # Add alpha channel if not present
            if len(rgba) == 3:
                rgba = rgba + (255,)
            
            return rgba
        except Exception as e:
            print(f"Error parsing color {color_str}: {str(e)}")
            # Default to white
            return (255, 255, 255, 255)

    def blend_images(self, background, foreground, mode="normal"):
        """
        Blend foreground image onto background with specified blend mode
        
        Args:
            background: PIL Image background
            foreground: PIL Image foreground (with alpha)
            mode: Blending mode (normal, multiply, screen, overlay, etc.)
            
        Returns:
            PIL.Image: Blended image
        """
        if background.mode != 'RGBA':
            background = background.convert('RGBA')
        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')
            
        # Ensure images are the same size
        if background.size != foreground.size:
            foreground = foreground.resize(background.size, Image.LANCZOS)
            
        # Convert to numpy arrays for easier manipulation
        bg = np.array(background).astype(np.float32) / 255
        fg = np.array(foreground).astype(np.float32) / 255
        
        # Extract alpha channels
        bg_alpha = bg[..., 3:4]
        fg_alpha = fg[..., 3:4]
        
        # RGB channels
        bg_rgb = bg[..., :3]
        fg_rgb = fg[..., :3]
        
        # Final alpha calculation (using Porter-Duff "over" operation)
        out_alpha = fg_alpha + bg_alpha * (1 - fg_alpha)
        
        # Apply different blend modes
        if mode == "normal":
            # Standard alpha composition
            out_rgb = fg_rgb * fg_alpha + bg_rgb * bg_alpha * (1 - fg_alpha)
            out_rgb = out_rgb / np.maximum(out_alpha, 1e-8)  # Prevent division by zero
            
        elif mode == "multiply":
            # Multiply blend mode
            blended = bg_rgb * fg_rgb
            out_rgb = fg_rgb * fg_alpha + bg_rgb * bg_alpha * (1 - fg_alpha)
            # Apply multiply only where foreground has alpha
            mask = fg_alpha > 0
            out_rgb[mask] = blended[mask]
            
        elif mode == "screen":
            # Screen blend mode
            blended = 1 - (1 - bg_rgb) * (1 - fg_rgb)
            out_rgb = fg_rgb * fg_alpha + bg_rgb * bg_alpha * (1 - fg_alpha)
            # Apply screen only where foreground has alpha
            mask = fg_alpha > 0
            out_rgb[mask] = blended[mask]
            
        elif mode == "overlay":
            # Overlay blend mode
            # Conditionally blend based on background brightness
            blended = np.zeros_like(bg_rgb)
            
            # Where background is light (> 0.5)
            light_mask = bg_rgb > 0.5
            blended[light_mask] = 1 - 2 * (1 - bg_rgb[light_mask]) * (1 - fg_rgb[light_mask])
            
            # Where background is dark (<= 0.5)
            dark_mask = ~light_mask
            blended[dark_mask] = 2 * bg_rgb[dark_mask] * fg_rgb[dark_mask]
            
            out_rgb = fg_rgb * fg_alpha + bg_rgb * bg_alpha * (1 - fg_alpha)
            # Apply overlay only where foreground has alpha
            mask = fg_alpha > 0
            out_rgb[mask] = blended[mask]
            
        else:
            # Default to normal blending for unknown modes
            out_rgb = fg_rgb * fg_alpha + bg_rgb * bg_alpha * (1 - fg_alpha)
            out_rgb = out_rgb / np.maximum(out_alpha, 1e-8)
        
        # Create output array
        out = np.zeros_like(bg)
        out[..., :3] = np.clip(out_rgb, 0, 1)
        out[..., 3:4] = np.clip(out_alpha, 0, 1)
        
        # Convert back to 8-bit and create PIL image
        out_8bit = (out * 255).astype(np.uint8)
        result = Image.fromarray(out_8bit)
        
        return result

    def apply_text_effect(self, img, text_effect, color, gradient_color=None):
        """
        Apply special effects to the text
        
        Args:
            img: PIL Image with text
            text_effect: Name of effect to apply (gradient, metal, neon, emboss)
            color: Base text color
            gradient_color: Secondary color for gradient effects
            
        Returns:
            PIL.Image: Text with effect applied
        """
        if text_effect == "none" or not text_effect:
            return img
            
        # Extract alpha channel
        alpha = img.split()[3] if img.mode == 'RGBA' else None
        
        # Get dimensions
        width, height = img.size
        
        # Ensure we're working with RGB
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create working copy
        result = img.copy()
        
        # Parse colors
        base_color = self.parse_color(color) or (255, 255, 255, 255)
        second_color = self.parse_color(gradient_color) or (0, 0, 255, 255)
            
        # Apply effect based on type
        if text_effect == "gradient":
            # Create a gradient mask from top to bottom
            gradient_mask = Image.new('L', (width, height))
            gradient_draw = ImageDraw.Draw(gradient_mask)
            
            for y in range(height):
                # Calculate gradient intensity (0 to 255)
                intensity = int(255 * y / height)
                gradient_draw.line([(0, y), (width, y)], fill=intensity)
            
            # Create two solid color images
            color1 = Image.new('RGBA', (width, height), base_color)
            color2 = Image.new('RGBA', (width, height), second_color)
            
            # Use the gradient mask to blend between the two colors
            blended = Image.composite(color1, color2, gradient_mask)
            
            # Apply this gradient only where the original text was
            if alpha:
                # Use alpha as mask
                result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                blended.putalpha(alpha)
                result.paste(blended, (0, 0), blended)
            else:
                result = blended
                
        elif text_effect == "metal":
            # Create metallic effect with emboss and gradient
            # First apply emboss filter
            emboss_kernel = [
                -2, -1, 0,
                -1, 1, 1,
                0, 1, 2
            ]
            embossed = img.filter(ImageFilter.Kernel((3, 3), emboss_kernel, 1, 0))
            
            # Create metallic gradient
            gradient_mask = Image.new('L', (width, height))
            gradient_draw = ImageDraw.Draw(gradient_mask)
            
            # Diagonal gradient
            for y in range(height):
                for x in range(width):
                    # Calculate diagonal gradient
                    intensity = int(255 * ((x/width) + (y/height))/2)
                    gradient_draw.point((x, y), fill=intensity)
            
            # Create metallic silver gradient (light gray to white)
            silver1 = Image.new('RGBA', (width, height), (192, 192, 192, 255))
            silver2 = Image.new('RGBA', (width, height), (240, 240, 240, 255))
            
            # Blend silver gradient
            metallic = Image.composite(silver1, silver2, gradient_mask)
            
            # Combine embossed image with metallic gradient
            result = ImageChops.multiply(embossed, metallic)
            result.putalpha(alpha if alpha else Image.new('L', (width, height), 255))
            
        elif text_effect == "neon":
            # Create bright center with glowing edges
            # First create a blurred version for the glow
            glow = img.filter(ImageFilter.GaussianBlur(radius=5))
            glow_color = Image.new('RGBA', (width, height), second_color)
            
            # Use the original alpha as mask for the glow
            if alpha:
                glow_mask = alpha.filter(ImageFilter.GaussianBlur(radius=5))
                glow_color.putalpha(glow_mask)
            
            # Create bright center
            center_color = Image.new('RGBA', (width, height), (255, 255, 255, 255))
            if alpha:
                center_color.putalpha(alpha)
            
            # Paste glow first, then bright center on top
            result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            result = Image.alpha_composite(result, glow_color)
            result = Image.alpha_composite(result, center_color)
            
        elif text_effect == "emboss":
            # Create embossed effect
            emboss_kernel = [
                -2, -1, 0,
                -1, 1, 1,
                0, 1, 2
            ]
            result = img.filter(ImageFilter.Kernel((3, 3), emboss_kernel, 1, 0))
            
            # Ensure we maintain the original alpha
            if alpha:
                result.putalpha(alpha)
        
        return result

    def generate_font_preview(self, sample_text, width, height, font_size, color, bold, italic, 
                           background_color, outline_color, outline_width, shadow, shadow_color, shadow_offset,
                           fonts_per_page=30, page_number=1):
        """
        Generate a preview image showing the sample text in available fonts, paginated
        
        Args:
            sample_text: Text to display for each font
            width, height: Dimensions of the preview image
            fonts_per_page: Maximum number of fonts to show per page
            page_number: Which page of fonts to display (1-based)
            Other parameters: Same styling as regular rendering
            
        Returns:
            tuple: (PIL.Image, int, int) - Generated preview image, current page, total pages
        """
        # Parse colors
        text_color = self.parse_color(color) or (255, 255, 255, 255)
        bg_color = self.parse_color(background_color) or (0, 0, 0, 255)  # Use black background by default for preview
        outline_color_parsed = self.parse_color(outline_color)
        shadow_color_parsed = self.parse_color(shadow_color) or (0, 0, 0, 255)
        
        # Calculate pagination
        num_fonts = len(self.sorted_fonts)
        total_pages = max(1, (num_fonts + fonts_per_page - 1) // fonts_per_page)  # Ceiling division
        
        # Ensure valid page number
        page_number = max(1, min(page_number, total_pages))
        
        # Calculate which fonts to display on this page
        start_idx = (page_number - 1) * fonts_per_page
        end_idx = min(start_idx + fonts_per_page, num_fonts)
        page_fonts = self.sorted_fonts[start_idx:end_idx]
        
        # Calculate dynamic height based on font count for this page
        line_height = int(font_size * 1.5)
        title_height = int(font_size * 3)  # More space for title and pagination info
        calculated_height = title_height + (len(page_fonts) * int(font_size * 2.2)) + 100  # Add padding
        preview_height = max(height, calculated_height)
        
        # Create image with background
        if bg_color[3] == 0:  # If transparent, use dark gray for better visibility
            img = Image.new('RGBA', (width, preview_height), (30, 30, 30, 255))
        else:
            img = Image.new('RGBA', (width, preview_height), bg_color)
            
        draw = ImageDraw.Draw(img)
        
        # Calculate layout
        title_font = self.load_font(self.sorted_fonts[0] if self.sorted_fonts else "Arial", font_size * 1.2, bold, italic)
        
        # Draw title with pagination info
        title_text = f"Font Preview - Page {page_number} of {total_pages} ({num_fonts} fonts total)"
        draw.text((width // 2, 20), title_text, fill=text_color, font=title_font, anchor="mt")
        
        # Draw page navigation help
        subtitle_font = self.load_font(self.sorted_fonts[0] if self.sorted_fonts else "Arial", font_size * 0.8, bold, italic)
        nav_text = "Adjust 'preview_page' parameter to navigate between pages"
        draw.text((width // 2, 20 + font_size * 1.5), nav_text, fill=text_color, font=subtitle_font, anchor="mt")
        
        # Layout parameters
        entry_height = int(font_size * 2.2)  # Space between entries
        font_name_size = int(font_size * 0.8)  # Smaller font for names
        side_padding = 20
        
        # Draw each font for this page
        for idx, font_name in enumerate(page_fonts):
            y_position = title_height + (idx * entry_height) + 30  # Added spacing after title
            
            try:
                # Load font - gracefully handle failures
                try:
                    font_obj = self.load_font(font_name, font_size, bold, italic)
                except Exception as e:
                    # If font fails to load, use a fallback but still show the name
                    print(f"Font preview: Failed to load font {font_name}: {str(e)}")
                    font_obj = self.load_font(self.sorted_fonts[0] if idx > 0 else "Arial", font_size, bold, italic)
                
                # Draw font index and name
                name_display = f"{start_idx + idx + 1}. {font_name[:40] + '...' if len(font_name) > 40 else font_name}"
                draw.text((side_padding, y_position), name_display, 
                        fill=text_color, font=subtitle_font)
                
                # Draw sample text (below the name)
                sample_y = y_position + font_name_size + 5
                
                # Draw shadow if enabled
                if shadow:
                    draw.text((side_padding + shadow_offset, sample_y + shadow_offset), 
                            sample_text, font=font_obj, fill=shadow_color_parsed)
                
                # Draw text outline if enabled
                if outline_color_parsed:
                    for offset_x in range(-outline_width, outline_width + 1):
                        for offset_y in range(-outline_width, outline_width + 1):
                            if offset_x == 0 and offset_y == 0:
                                continue
                            draw.text((side_padding + offset_x, sample_y + offset_y), 
                                    sample_text, font=font_obj, fill=outline_color_parsed)
                
                # Draw main text
                draw.text((side_padding, sample_y), sample_text, font=font_obj, fill=text_color)
                
                # Draw separator line
                separator_y = y_position + entry_height - 5
                draw.line([(side_padding, separator_y), (width - side_padding, separator_y)], 
                         fill=(text_color[0], text_color[1], text_color[2], 100), width=1)
                
            except Exception as e:
                # Draw error message if rendering fails
                error_msg = f"Error with font '{font_name}': {str(e)}"
                draw.text((side_padding, y_position + font_name_size + 5), error_msg, font=subtitle_font, fill=(255, 0, 0, 255))
        
        # Draw page navigation at bottom
        nav_y = preview_height - int(font_size * 1.5)
        
        nav_text = f"Page {page_number} of {total_pages}"
        if total_pages > 1:
            if page_number > 1:
                nav_text += f" | Use preview_page={page_number-1} for previous page"
            if page_number < total_pages:
                nav_text += f" | Use preview_page={page_number+1} for next page"
        
        draw.text((width // 2, nav_y), nav_text, fill=text_color, font=subtitle_font, anchor="mm")
        
        return img, page_number, total_pages

    def auto_wrap_text(self, text, font, max_width, max_chars=0):
        """
        Wrap text based on maximum width or maximum characters per line
        """
        if not text:
            return []
            
        lines = text.splitlines()
        wrapped_lines = []
        
        for line in lines:
            if not line.strip():
                wrapped_lines.append("")
                continue
                
            if max_chars > 0:
                # Wrap based on character count
                wrapped = textwrap.fill(line, width=max_chars)
                wrapped_lines.extend(wrapped.splitlines())
            else:
                # Wrap based on pixel width
                words = line.split()
                current_line = []
                current_width = 0
                
                for word in words:
                    word_width = font.getlength(word + " ")
                    
                    if current_width + word_width <= max_width:
                        current_line.append(word)
                        current_width += word_width
                    else:
                        if current_line:
                            wrapped_lines.append(" ".join(current_line))
                        current_line = [word]
                        current_width = font.getlength(word + " ")
                
                if current_line:
                    wrapped_lines.append(" ".join(current_line))
        
        return wrapped_lines

    def ensure_compatible_format(self, tensor):
        """Ensure tensor is in the format expected by ComfyUI nodes"""
        # Check if we need to convert format
        if tensor.shape[-1] != 4:
            print("TextOverlayNode: Warning - tensor doesn't have 4 channels, attempting to convert")
            # Add alpha channel if missing
            if tensor.shape[-1] == 3:
                alpha = torch.ones((*tensor.shape[:-1], 1), device=tensor.device)
                tensor = torch.cat([tensor, alpha], dim=-1)
        
        # Ensure batch dimension exists
        if len(tensor.shape) == 3:
            tensor = tensor.unsqueeze(0)
            
        # Log the final format
        if self.debug:
            print(f"TextOverlayNode: Final tensor shape: {tensor.shape}, dtype: {tensor.dtype}")
            
        return tensor

    def render_text(self, text, width, height, font, font_size, color="#FFFFFF", align="center", 
                v_align="middle", transparent_background=True, background_color="#000000", background_opacity=100,
                x_offset_pct=0.0, y_offset_pct=0.0, line_spacing=1.2, padding=20, wrap_width=0, 
                reference_image=None, outline_color=None, 
                outline_width=1, text_file=None, bold=False, italic=False, 
                shadow=False, shadow_color="#000000", shadow_offset=2,
                layer_blend_mode="normal", text_effect=None, gradient_color=None,
                show_font_preview=False, preview_text="The quick brown fox jumps over the lazy dog",
                fonts_per_page=30, preview_page=1):
        """Render text onto a transparent image"""
        
        # Initialize the preview tensor with None
        preview_tensor = None
        
        # Check if we should generate a font preview
        if show_font_preview:
            preview_img, current_page, total_pages = self.generate_font_preview(
                preview_text, width, height, font_size, color, bold, italic, 
                background_color, outline_color, outline_width, shadow, shadow_color, shadow_offset,
                fonts_per_page, preview_page
            )
            
            # Convert preview to tensor
            preview_np = np.array(preview_img).astype(np.float32) / 255.0
            preview_tensor = torch.from_numpy(preview_np)[None, ...]
            preview_tensor = self.ensure_compatible_format(preview_tensor)
            
            if self.debug:
                print(f"TextOverlayNode: Generated font preview page {current_page}/{total_pages} with {fonts_per_page} fonts per page")
                
                # Save a debug image of the preview
                try:
                    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_path = os.path.join(debug_dir, f"font_preview_page{current_page}_{int(time.time())}.png")
                    preview_img.save(debug_path)
                    print(f"TextOverlayNode: Saved font preview to {debug_path}")
                except Exception as e:
                    print(f"TextOverlayNode: Failed to save font preview: {str(e)}")
            
            # Return both the preview as main image and as preview output
            return (preview_tensor, preview_tensor)
            
        # Use reference image dimensions if provided
        if reference_image is not None:
            # Handle both ComfyUI's NHWC and HWC formats
            if len(reference_image.shape) == 4:
                batch_size, height, width, _ = reference_image.shape
            else:
                height, width, _ = reference_image.shape
                
            if self.debug:
                print(f"Using reference image dimensions: {width}x{height}")
        
        # Load text from file if specified and text input is empty
        file_text = None
        if text_file:
            file_text = self.load_text_from_file(text_file)
        
        # Determine which text to use
        if file_text is not None:
            render_text = file_text
        elif text.strip():
            render_text = text
        else:
            render_text = "No text provided"
        
        # Parse colors
        text_color = self.parse_color(color) or (255, 255, 255, 255)
        outline_color = self.parse_color(outline_color)
        shadow_color = self.parse_color(shadow_color) or (0, 0, 0, 255)
        
        # Create reference image if provided
        reference_pil = None
        if reference_image is not None:
            if torch.is_tensor(reference_image):
                if len(reference_image.shape) == 4:
                    ref_np = reference_image[0].cpu().numpy()
                else:
                    ref_np = reference_image.cpu().numpy()
                
                # Convert to 8-bit for PIL
                if ref_np.max() <= 1.0:
                    ref_np = (ref_np * 255).astype(np.uint8)
                else:
                    ref_np = ref_np.astype(np.uint8)
                    
                reference_pil = Image.fromarray(ref_np)
        
        # Process background color and opacity
        if transparent_background:
            # Create transparent image regardless of background_color
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        else:
            # Create image with background color and specified opacity
            bg_color = self.parse_color(background_color) or (0, 0, 0, 255)
            # Apply opacity - convert to list to modify alpha
            bg_color_list = list(bg_color)
            if len(bg_color_list) == 3:
                # If RGB tuple, add alpha
                bg_color_list.append(int(255 * background_opacity / 100))
            else:
                # If RGBA tuple, modify alpha
                bg_color_list[3] = int(255 * background_opacity / 100)
            
            img = Image.new('RGBA', (width, height), tuple(bg_color_list))
        
        # Create a separate image for text rendering (for effects)
        text_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_img)
        
        # Load font
        font_obj = self.load_font(font, font_size, bold, italic)
        
        # Calculate effective width for text wrapping (accounting for padding)
        effective_width = width - (2 * padding)
        if wrap_width > 0:
            # Use character-based wrapping
            wrapped_lines = self.auto_wrap_text(render_text, font_obj, effective_width, wrap_width)
        else:
            # Use pixel-based wrapping
            wrapped_lines = self.auto_wrap_text(render_text, font_obj, effective_width)
        
        # Calculate total text height based on line count and spacing
        line_height = font_size * line_spacing
        total_text_height = len(wrapped_lines) * line_height
        
        # Calculate vertical position based on alignment
        if v_align == "top":
            y_position = padding
        elif v_align == "bottom":
            y_position = height - total_text_height - padding
        else:  # middle
            y_position = (height - total_text_height) / 2
            
        # Calculate actual pixel offsets from percentages
        x_offset = int((x_offset_pct / 100.0) * width)
        y_offset = int((y_offset_pct / 100.0) * height)
        
        if self.debug:
            print(f"TextOverlayNode: X offset: {x_offset_pct}% = {x_offset}px, Y offset: {y_offset_pct}% = {y_offset}px")
        
        # Apply y_offset to the base position
        y_position += y_offset
        
        # Draw each line
        for line in wrapped_lines:
            if not line:
                y_position += line_height
                continue
                
            # Calculate line width for horizontal alignment
            line_width = font_obj.getlength(line)
            
            # Determine x position based on alignment
            if align == "left":
                x_position = padding
            elif align == "right":
                x_position = width - line_width - padding
            else:  # center
                x_position = (width - line_width) / 2
                
            # Apply x_offset to the base position
            x_position += x_offset
            
            # Draw shadow if enabled
            if shadow:
                draw.text((x_position + shadow_offset, y_position + shadow_offset), 
                        line, font=font_obj, fill=shadow_color)
            
            # Draw text outline if color is specified
            if outline_color:
                for offset_x in range(-outline_width, outline_width + 1):
                    for offset_y in range(-outline_width, outline_width + 1):
                        if offset_x == 0 and offset_y == 0:
                            continue
                        draw.text((x_position + offset_x, y_position + offset_y), 
                                line, font=font_obj, fill=outline_color)
            
            # Draw main text
            draw.text((x_position, y_position), line, font=font_obj, fill=text_color)
            
            # Move to next line
            y_position += line_height
            
        # Apply text effect if specified
        if text_effect and text_effect != "none":
            text_img = self.apply_text_effect(text_img, text_effect, color, gradient_color)
            
        # Blend with background/reference image if using a blend mode other than normal
        if layer_blend_mode != "normal" and reference_pil is not None:
            # Blend using reference image
            img = self.blend_images(reference_pil, text_img, layer_blend_mode)
        elif layer_blend_mode != "normal":
            # Blend with background
            img = self.blend_images(img, text_img, layer_blend_mode)
        else:
            # Standard composite for transparent background or normal blend
            img = Image.alpha_composite(img, text_img)
        
        # Convert PIL image to tensor
        img_np = np.array(img).astype(np.float32) / 255.0
        
        # Convert to tensor and ensure batch dimension
        img_tensor = torch.from_numpy(img_np)[None, ...]
        
        # Ensure the tensor is in the format expected by other ComfyUI nodes
        img_tensor = self.ensure_compatible_format(img_tensor)
        
        # Debug output
        if self.debug:
            print(f"TextOverlayNode: Generated overlay with shape: {img_tensor.shape}")
            print(f"TextOverlayNode: Value range - min: {img_tensor.min()}, max: {img_tensor.max()}")
            print(f"TextOverlayNode: Text rendered with color {text_color}, font {font}, size {font_size}")
            print(f"TextOverlayNode: Background: {'Transparent' if transparent_background else f'Opaque ({background_color})'}")
            if not transparent_background:
                print(f"TextOverlayNode: Background opacity: {background_opacity}%")
            
            # Check for empty/transparent image which might not be visible
            alpha_values = img_tensor[0, :, :, 3] if img_tensor.shape[-1] == 4 else torch.ones_like(img_tensor[0, :, :, 0])
            non_zero_alpha = (alpha_values > 0).sum().item()
            total_pixels = alpha_values.numel()
            print(f"TextOverlayNode: Non-transparent pixels: {non_zero_alpha}/{total_pixels} ({non_zero_alpha/total_pixels*100:.2f}%)")
            
            # Save a debug image to disk to verify rendering
            try:
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug")
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f"text_overlay_debug_{int(time.time())}.png")
                img.save(debug_path)
                print(f"TextOverlayNode: Saved debug image to {debug_path}")
            except Exception as e:
                print(f"TextOverlayNode: Failed to save debug image: {str(e)}")
        
        # Free up memory from intermediate objects
        del img_np
        
        # Clear PIL drawing objects
        del draw
        
        # Return both the main image and None for preview (since we're not generating a preview)
        return (img_tensor, preview_tensor or img_tensor)

# Registration of the node for ComfyUI
NODE_CLASS_MAPPINGS = {
    "TextOverlayNode_v04": TextOverlayNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TextOverlayNode_v04": "Text Overlay Node v04"
}