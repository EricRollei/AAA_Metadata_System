"""
ComfyUI Node: Color Selector
Description: Select colors by name or hex code with live preview

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
- pillow: PIL Software License (Python Imaging Library) 

"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import re

# Add data directory to path if needed
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))

# Import data
from color_data.color_names_v2 import COLOR_NAMES

class ColorNameToRGBNode:
    """Node to provide an easy color selection interface using the full color dictionary"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Sort all color names alphabetically for the dropdown
        all_colors_sorted = sorted(list(COLOR_NAMES.keys()))
        
        return {
            "required": {
                "color": (all_colors_sorted, {"default": "white"}),
            },
            "optional": {
                "custom_color": ("STRING", {"default": "", "placeholder": "Enter hex code or color name"}),
                "preview_size": ("INT", {"default": 64, "min": 16, "max": 256, "step": 8})
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "INT", "INT", "IMAGE")
    RETURN_NAMES = ("hex_color", "red", "green", "blue", "preview")
    FUNCTION = "select_color"
    CATEGORY = "colors"
    
    def select_color(self, color, custom_color="", preview_size=64):
        """Select a color and generate a preview image"""
        # Determine the final color value
        if custom_color and custom_color.strip():
            selected_color = custom_color.strip()
        else:
            selected_color = color
            
        # Generate a preview image of the selected color
        img = Image.new('RGBA', (preview_size, preview_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Create color swatch
        rgb_value = self.get_rgb_for_color(selected_color)
        draw.rectangle([0, 0, preview_size, preview_size], fill=rgb_value)
        
        # Add a border for visibility
        draw.rectangle([0, 0, preview_size-1, preview_size-1], outline=(0, 0, 0, 255), width=1)
        
        # Add color name text at the bottom
        try:
            font_size = max(10, preview_size // 8)
            # Try to find a system font
            system_font = None
            try:
                if sys.platform == "win32":
                    font_path = os.path.join(os.environ["WINDIR"], "Fonts", "Arial.ttf")
                    if os.path.exists(font_path):
                        system_font = ImageFont.truetype(font_path, font_size)
                # Add other OS font paths as needed
            except:
                pass
                
            if system_font is None:
                system_font = ImageFont.load_default()
                
            # Create a text background for better readability
            text_width = preview_size
            text_height = font_size + 4
            text_y = preview_size - text_height
            
            text_bg = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 180))
            img.paste(text_bg, (0, text_y), text_bg)
            
            # Truncate color name if too long
            display_text = selected_color
            if len(display_text) > 15:
                display_text = display_text[:12] + "..."
                
            # Draw the text
            draw.text((3, text_y + 2), display_text, fill=(255, 255, 255, 255), font=system_font)
        except:
            # If text rendering fails, just show the color swatch
            pass
        
        # Convert to tensor for ComfyUI
        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None, ...]
        
        # Get RGB components
        r, g, b, _ = self.get_rgb_for_color(selected_color)
        
        # Get hex value
        hex_color = self.rgb_to_hex(r, g, b)
        
        return (hex_color, r, g, b, img_tensor)
    
    def get_rgb_for_color(self, color_name):
        """Convert a color name or hex code to an RGB tuple"""
        # If it's a hex code
        if color_name.startswith("#"):
            try:
                if len(color_name) == 7:  # #RRGGBB
                    r = int(color_name[1:3], 16)
                    g = int(color_name[3:5], 16)
                    b = int(color_name[5:7], 16)
                    return (r, g, b, 255)
                elif len(color_name) == 9:  # #RRGGBBAA
                    r = int(color_name[1:3], 16)
                    g = int(color_name[3:5], 16)
                    b = int(color_name[5:7], 16)
                    a = int(color_name[7:9], 16)
                    return (r, g, b, a)
            except:
                pass
        
        # Check if it's in our color names dictionary
        if color_name in COLOR_NAMES:
            r, g, b = COLOR_NAMES[color_name]
            return (r, g, b, 255)
        
        # Default to white if color not found
        return (255, 255, 255, 255)
    
    def rgb_to_hex(self, r, g, b):
        """Convert RGB values to a hex color code"""
        return f"#{r:02x}{g:02x}{b:02x}"

# Register the node
NODE_CLASS_MAPPINGS = {
    "ColorNameToRGB_v01": ColorNameToRGBNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ColorNameToRGB_v01": "Color Name to RGB and Hex v01",
}