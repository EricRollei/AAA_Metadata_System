"""
ComfyUI Node: Eric's Color Selector Node
Description: A node that organizes colors into logical categories (Basic, Reds, Blues, etc.)
It provides a two-step selection process: first choose a category, then a color from that category
It includes a custom color input field for manual entry of hex codes or color names
Generates a visual preview of the selected color, which helps users confirm their selection
The output color string can be directly connected to the text overlay node
This node is designed to be user-friendly and visually appealing, making it easy for users to select colors for text overlays

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

"""
import os
import sys
from .color_names import COLOR_NAMES

# Organize colors into categories for easier selection
COLOR_CATEGORIES = {
    "Basic": ["white", "black", "red", "green", "blue", "yellow", "cyan", "magenta", "gray"],
    "Grayscale": ["white", "black", "Gray10", "Gray30", "Gray50", "Gray70", "Gray90"],
    "Reds": ["red", "dark_red", "crimson", "FireBrick1", "IndianRed1", "Salmon1", "tomato", "coral", "Coral1"],
    "Oranges": ["orange", "dark_orange", "tangerine", "OrangeRed2", "Chocolate1", "Chocolate2", "Tan1"],
    "Yellows": ["yellow", "yellow_green", "khaki", "LightGoldenrod1", "gold", "Goldenrod1", "DarkGoldenrod1"],
    "Greens": ["green", "dark_green", "lime", "SpringGreen2", "turquoise", "sea_green", "olive", "mint"],
    "Blues": ["blue", "navy", "DeepSkyBlue2", "SkyBlue1", "RoyalBlue1", "steel_blue", "cornflower_blue", "azure"],
    "Purples": ["purple", "indigo", "violet", "fuchsia", "magenta", "MediumOrchid1", "medium_purple", "plum"],
    "Browns": ["brown", "chocolate", "sienna", "saddle_brown", "peru", "tan", "wheat", "khaki_brown"],
    "Pinks": ["pink", "hot_pink", "DeepPink1", "PaleVioletRed1", "HotPink1", "VioletRed1", "LightPink1"],
    "Cyans": ["cyan", "turquoise", "teal", "aquamarine", "LightCyan2", "PaleTurquoise1", "CadetBlue1"],
    "Pastels": ["lavender", "misty_rose", "mint_cream", "honeydew", "alice_blue", "LightGoldenrod1", "LightBlue1"],
    "Vibrant": ["neon_green", "electric_blue", "shocking_pink", "vivid_orange", "fluorescent_yellow", "laser_blue"],
    "Web Safe": ["#000000", "#333333", "#666666", "#999999", "#CCCCCC", "#FFFFFF", 
                "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF"]
}

class ColorSelectorNode:
    """Node to provide an easy color selection interface using predefined color categories"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get unique color names from all categories
        unique_colors = set()
        for category, colors in COLOR_CATEGORIES.items():
            for color in colors:
                unique_colors.add(color)
        
        # Sort the unique colors alphabetically for the "All Colors" category
        all_colors_sorted = sorted(list(unique_colors))
        
        return {
            "required": {
                "category": (list(COLOR_CATEGORIES.keys()) + ["All Colors"], {"default": "Basic"}),
                "color": (COLOR_CATEGORIES["Basic"], {"default": "white"}),
            },
            "optional": {
                "custom_color": ("STRING", {"default": "", "placeholder": "Enter hex code or color name"}),
                "preview_size": ("INT", {"default": 64, "min": 16, "max": 256, "step": 8})
            }
        }
    
    RETURN_TYPES = ("STRING", "IMAGE")
    RETURN_NAMES = ("color", "preview")
    FUNCTION = "select_color"
    CATEGORY = "ui/color"
    
    def __init__(self):
        # Cache for dynamic UI updates
        self.color_options = {category: colors for category, colors in COLOR_CATEGORIES.items()}
        self.color_options["All Colors"] = sorted(list({color for colors in COLOR_CATEGORIES.values() for color in colors}))
        
    def select_color(self, category, color, custom_color="", preview_size=64):
        """Select a color and generate a preview image"""
        import torch
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        
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
        
        return (selected_color, img_tensor)
    
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

# This function is called to update UI elements based on user input
def update_color_options(self, **kwargs):
    category = kwargs.get("category", "Basic")
    
    if category in self.color_options:
        return {"color": self.color_options[category]}
    else:
        return {"color": self.color_options["Basic"]}

# Add the update method to the node class
ColorSelectorNode.CATEGORY_MAPPING = update_color_options

# Register the node
NODE_CLASS_MAPPINGS = {
    "ColorSelector": ColorSelectorNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ColorSelector": "Color Selector"
}
