"""
ComfyUI Node: Cultural Color Palette Generator
Description: Generate harmonious color palettes based on color theory and cultural meanings

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
colorsys, numpy, PIL (Pillow), torch

"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import sys
import math
import colorsys


# Add data directory to path if needed
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))

# Import data
from color_data.color_names_v2 import COLOR_NAMES
# Import cultural data
from color_data.color_culture_table import COLOR_CULTURE_DATA, RGB_CULTURE_CONCEPTS

# Color categories for organized selection
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

# Color harmony models
HARMONY_MODELS = {
    "Complementary": "Colors opposite each other on the color wheel",
    "Analogous": "Colors adjacent to each other on the color wheel",
    "Triadic": "Three colors equally spaced around the color wheel",
    "Tetradic": "Four colors forming a rectangle on the color wheel",
    "Square": "Four colors equally spaced around the color wheel",
    "Split-Complementary": "Base color plus two colors adjacent to its complement",
    "Monochromatic": "Different shades and tints of the same color"
}

# Available cultures from color_culture_table.py
CULTURES = [
    "western_american", "japanese", "hindu", "native_american",
    "chinese", "asian", "eastern_european", "arab", 
    "african", "south_american"
]

# Display-friendly culture names
CULTURE_DISPLAY_NAMES = {
    "western_american": "Western/American",
    "japanese": "Japanese",
    "hindu": "Hindu/Indian",
    "native_american": "Native American",
    "chinese": "Chinese",
    "asian": "Asian (General)",
    "eastern_european": "Eastern European",
    "arab": "Arab/Middle Eastern",
    "african": "African",
    "south_american": "South American"
}

class CulturalColorPaletteGeneratorNode:
    """Generate harmonious color palettes with cultural context"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Extract concepts from COLOR_CULTURE_DATA for the dropdown
        concepts = sorted(list(set(item["concept"] for item in COLOR_CULTURE_DATA)))
        
        # Get the full color list for direct color selection
        all_colors_sorted = sorted(list(COLOR_NAMES.keys()))
        
        return {
            "required": {
                "color_selection_method": (["By Category", "By Name"], {"default": "By Category"}),
                "base_color_category": (list(COLOR_CATEGORIES.keys()), {"default": "Basic"}),
                "base_color_from_category": (COLOR_CATEGORIES["Basic"], {"default": "blue"}),
                "base_color_from_list": (all_colors_sorted, {"default": "blue"}),
                "harmony_model": (list(HARMONY_MODELS.keys()), {"default": "Complementary"}),
                "culture": (list(CULTURE_DISPLAY_NAMES.values()), {"default": "Western/American"}),
                "concept": (concepts, {"default": concepts[0] if concepts else "Celebration"}),
                "palette_size": ("INT", {"default": 5, "min": 3, "max": 6, "step": 1}),
            },
            "optional": {
                "use_secondary_color": ("BOOLEAN", {"default": False}),
                "secondary_color_method": (["By Category", "By Name"], {"default": "By Category"}),
                "secondary_color_category": (list(COLOR_CATEGORIES.keys()), {"default": "Basic"}),
                "secondary_color_from_category": (COLOR_CATEGORIES["Basic"], {"default": "red"}),
                "secondary_color_from_list": (all_colors_sorted, {"default": "red"}),
                "custom_base_color": ("STRING", {"default": "", "placeholder": "Custom hex code or color name"}),
                "custom_secondary_color": ("STRING", {"default": "", "placeholder": "Custom hex code or color name"}),
                "cultural_influence": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, 
                                               "tooltip": "How strongly to apply cultural preferences (0=none, 1=strong)"}),
                "saturation": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1}),
                "value": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1}),
                "preview_width": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 64}),
                "preview_height": ("INT", {"default": 1024, "min": 256, "max": 2048, "step": 64}),
                "color_preview": ("BOOLEAN", {"default": True, "label": "Show Color Preview"})
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("color1", "color2", "color3", "color4", "color5", "color6", "palette_preview", "color_picker")
    FUNCTION = "generate_palette"
    CATEGORY = "colors"
    
    def __init__(self):
        self.display_to_internal_culture = {v: k for k, v in CULTURE_DISPLAY_NAMES.items()}
        # Cache for dynamic UI updates
        self.color_options = {category: colors for category, colors in COLOR_CATEGORIES.items()}
    
    def get_rgb_for_color(self, color_name):
        """Convert a color name or hex code to an RGB tuple"""
        # If it's a hex code
        if color_name.startswith("#"):
            try:
                if len(color_name) == 7:  # #RRGGBB
                    r = int(color_name[1:3], 16)
                    g = int(color_name[3:5], 16)
                    b = int(color_name[5:7], 16)
                    return (r, g, b)
                elif len(color_name) == 9:  # #RRGGBBAA
                    r = int(color_name[1:3], 16)
                    g = int(color_name[3:5], 16)
                    b = int(color_name[5:7], 16)
                    return (r, g, b)
            except:
                pass
        
        # Check if it's in our color names dictionary
        if color_name in COLOR_NAMES:
            return COLOR_NAMES[color_name]
        
        # Default to a medium blue if color not found
        return (52, 152, 219)
    
    def rgb_to_hex(self, r, g, b):
        """Convert RGB values to a hex color code"""
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def rgb_to_hsv(self, r, g, b):
        """Convert RGB to HSV"""
        r, g, b = r/255.0, g/255.0, b/255.0
        return colorsys.rgb_to_hsv(r, g, b)
    
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r*255), int(g*255), int(b*255))
    
    def get_cultural_colors(self, culture_display, concept):
        """Get colors associated with a concept in a specific culture"""
        culture = self.display_to_internal_culture.get(culture_display, "western_american")
        
        # Find concept in COLOR_CULTURE_DATA
        cultural_colors = []
        for item in COLOR_CULTURE_DATA:
            if item["concept"].lower() == concept.lower():
                hex_code = item.get(culture, "")
                if hex_code:
                    # Convert hex to RGB
                    try:
                        r = int(hex_code[0:2], 16)
                        g = int(hex_code[2:4], 16)
                        b = int(hex_code[4:6], 16)
                        cultural_colors.append((r, g, b))
                    except:
                        pass
                break
        
        return cultural_colors
    
    def generate_harmony_palette(self, base_rgb, model, palette_size, secondary_rgb=None, sat=0.8, val=0.8):
        """Generate a color palette based on the selected harmony model"""
        # Convert base color to HSV
        r, g, b = base_rgb
        h, s, v = self.rgb_to_hsv(r, g, b)
        
        # If secondary color is provided, get its HSV
        sec_h, sec_s, sec_v = None, None, None
        if secondary_rgb:
            sec_r, sec_g, sec_b = secondary_rgb
            sec_h, sec_s, sec_v = self.rgb_to_hsv(sec_r, sec_g, sec_b)
        
        palette = []
        
        # Always start with the base color
        palette.append(base_rgb)
        
        # Different logic based on harmony model
        if model == "Complementary":
            # If secondary color is provided, use it instead of calculating complement
            if secondary_rgb:
                palette.append(secondary_rgb)
            else:
                # Complementary color (opposite on wheel)
                comp_h = (h + 0.5) % 1.0
                palette.append(self.hsv_to_rgb(comp_h, sat, val))
            
            # Add additional colors if needed
            if palette_size > 2:
                # Add analogous to both main colors
                for i in range(palette_size - 2):
                    angle = (i / (palette_size - 2)) * 0.3 - 0.15  # Spread around main colors
                    if i % 2 == 0:
                        new_h = (h + angle) % 1.0
                    else:
                        # Use secondary color's hue if available, otherwise use complementary
                        second_h = sec_h if sec_h is not None else (h + 0.5) % 1.0
                        new_h = (second_h + angle) % 1.0
                    palette.append(self.hsv_to_rgb(new_h, sat, val))
                    
        elif model == "Analogous":
            # If secondary color is provided and within analogous range, use as second color
            if secondary_rgb and abs((sec_h - h + 1.0) % 1.0 - 0.5) >= 0.35:  # Not too far apart
                palette.append(secondary_rgb)
                start_idx = 2
            else:
                start_idx = 1
                
            # Calculate colors for the rest of the palette
            spread = 0.05  # 0.05 of the wheel = 18 degrees
            
            # Generate remaining colors in the palette
            for i in range(start_idx, palette_size):
                # Space them evenly around the base color
                offset = (i - (palette_size - 1) / 2) * spread
                new_h = (h + offset) % 1.0
                # Vary saturation slightly for interest
                new_s = min(1.0, sat * (0.9 + 0.2 * (i / (palette_size - 1))))
                palette.append(self.hsv_to_rgb(new_h, new_s, val))
                
        elif model == "Triadic":
            # If secondary is provided, use it as second color if it's roughly triadic
            if secondary_rgb:
                palette.append(secondary_rgb)
                
                # Third color completes the triad based on the first two
                if palette_size > 2:
                    # Calculate third point of triangle
                    # Average hue and add 0.33 (120 degrees)
                    avg_h = (h + sec_h) / 2
                    third_h = (avg_h + 0.33) % 1.0
                    palette.append(self.hsv_to_rgb(third_h, sat, val))
            else:
                # Standard triadic colors (120 degrees apart)
                for i in range(1, min(palette_size, 3)):
                    new_h = (h + i/3) % 1.0
                    palette.append(self.hsv_to_rgb(new_h, sat, val))
            
            # If more than 3 colors requested, add intermediate shades
            if palette_size > len(palette):
                for i in range(palette_size - len(palette)):
                    idx1 = i % (len(palette) - 1)
                    idx2 = (idx1 + 1) % len(palette)
                    
                    h1 = self.rgb_to_hsv(*palette[idx1])[0]
                    h2 = self.rgb_to_hsv(*palette[idx2])[0]
                    
                    # Find intermediate hue
                    h_diff = (h2 - h1) % 1.0
                    if h_diff > 0.5:
                        h_diff = 1.0 - h_diff
                        new_h = (h1 - h_diff/2) % 1.0
                    else:
                        new_h = (h1 + h_diff/2) % 1.0
                        
                    palette.append(self.hsv_to_rgb(new_h, sat, val))
                    
        elif model == "Tetradic" or model == "Square":
            # If secondary color is provided, use it
            if secondary_rgb:
                palette.append(secondary_rgb)
                
                # Calculate remaining colors for tetradic/square
                if palette_size > 2:
                    # For tetradic, the other two corners depend on the first two points
                    h_diff = (sec_h - h) % 1.0
                    if h_diff > 0.5:
                        h_diff = 1.0 - h_diff
                    
                    # Third color: complement of base
                    third_h = (h + 0.5) % 1.0
                    palette.append(self.hsv_to_rgb(third_h, sat, val))
                    
                    # Fourth color: complement of secondary
                    if palette_size > 3:
                        fourth_h = (sec_h + 0.5) % 1.0
                        palette.append(self.hsv_to_rgb(fourth_h, sat, val))
            else:
                # Calculate angle between colors
                angle = 0.25 if model == "Square" else 0.5  # Square = 90°, Tetradic rectangle = 180°
                
                # Generate remaining colors
                for i in range(1, min(palette_size, 4)):
                    new_h = (h + i * angle) % 1.0
                    palette.append(self.hsv_to_rgb(new_h, sat, val))
                
            # If more than 4 colors are needed, add intermediates
            if palette_size > len(palette):
                for i in range(palette_size - len(palette)):
                    idx = i % len(palette)
                    next_idx = (idx + 1) % len(palette)
                    
                    h1 = self.rgb_to_hsv(*palette[idx])[0]
                    h2 = self.rgb_to_hsv(*palette[next_idx])[0]
                    
                    # Interpolate between adjacent colors
                    h_diff = (h2 - h1) % 1.0
                    if h_diff > 0.5:
                        h_diff = 1.0 - h_diff
                        new_h = (h1 - h_diff/2) % 1.0
                    else:
                        new_h = (h1 + h_diff/2) % 1.0
                        
                    palette.append(self.hsv_to_rgb(new_h, sat * 0.9, val))
                    
        elif model == "Split-Complementary":
            # If secondary color provided and reasonably close to a split-complement, use it
            if secondary_rgb:
                palette.append(secondary_rgb)
                
                # Add third color to complete the split-complement if needed
                if palette_size > 2:
                    comp_h = (h + 0.5) % 1.0
                    
                    # Determine if secondary color is on which side of complement
                    h_diff = (sec_h - comp_h + 1.0) % 1.0
                    if h_diff < 0.5:  # Secondary is to the "left" of complement
                        third_h = (comp_h + 0.05) % 1.0  # Add third to the "right"
                    else:  # Secondary is to the "right" of complement
                        third_h = (comp_h - 0.05) % 1.0  # Add third to the "left"
                        
                    palette.append(self.hsv_to_rgb(third_h, sat, val))
            else:
                # Two colors adjacent to the complement
                comp_h = (h + 0.5) % 1.0
                palette.append(self.hsv_to_rgb((comp_h - 0.05) % 1.0, sat, val))
                
                if palette_size > 2:
                    palette.append(self.hsv_to_rgb((comp_h + 0.05) % 1.0, sat, val))
            
            # Add additional colors if needed
            if palette_size > len(palette):
                # Add colors between the splits
                for i in range(palette_size - len(palette)):
                    # Interpolate between existing colors
                    idx1 = i % len(palette)
                    idx2 = (idx1 + 1) % len(palette)
                    
                    h1 = self.rgb_to_hsv(*palette[idx1])[0]
                    h2 = self.rgb_to_hsv(*palette[idx2])[0]
                    
                    # Find intermediate hue
                    h_diff = (h2 - h1) % 1.0
                    if h_diff > 0.5:
                        h_diff = 1.0 - h_diff
                        new_h = (h1 - h_diff/2) % 1.0
                    else:
                        new_h = (h1 + h_diff/2) % 1.0
                        
                    palette.append(self.hsv_to_rgb(new_h, sat, val))
                    
        elif model == "Monochromatic":
            # If secondary color provided and same hue family, use it
            if secondary_rgb:
                sec_h, sec_s, sec_v = self.rgb_to_hsv(*secondary_rgb)
                # Check if secondary color is reasonably close in hue to base
                h_diff = abs((sec_h - h + 1.0) % 1.0 - 0.5)
                if h_diff <= 0.05:  # Allows for small hue variations
                    palette.append(secondary_rgb)
                else:
                    # Otherwise generate a color that fits the monochromatic scheme
                    palette.append(self.hsv_to_rgb(h, max(0.1, s * 0.7), min(0.9, v * 1.2)))
            else:
                # Generate first variant with higher/lower saturation
                palette.append(self.hsv_to_rgb(h, max(0.1, s * 0.7), min(0.9, v * 1.2)))
            
            # Generate remaining colors in the palette
            for i in range(len(palette), palette_size):
                # Distribute across saturation and value space
                progress = i / (palette_size - 1) if palette_size > 1 else 0
                
                new_s = sat * (0.4 + 0.6 * (1 - progress))
                new_v = val * (0.5 + 0.5 * progress)
                
                palette.append(self.hsv_to_rgb(h, new_s, new_v))
        
        # Ensure we have exactly palette_size colors
        if len(palette) < palette_size:
            # If we need more colors, add variations with slight hue shifts
            while len(palette) < palette_size:
                idx = len(palette) % len(palette)
                base = palette[idx]
                base_h, base_s, base_v = self.rgb_to_hsv(*base)
                shift = 0.02 * (len(palette) - idx)
                new_color = self.hsv_to_rgb((base_h + shift) % 1.0, base_s, base_v)
                palette.append(new_color)
        
        # Trim if we have too many
        palette = palette[:palette_size]
        
        return palette
    
    def blend_palettes(self, harmony_palette, cultural_palette, influence, preserve_base=True, preserve_secondary=True):
        """Blend the harmony-based palette with culturally relevant colors"""
        if not cultural_palette:
            return harmony_palette
            
        blended_palette = []
        
        for i, harmony_color in enumerate(harmony_palette):
            # If we should preserve base color or secondary color
            if (i == 0 and preserve_base) or (i == 1 and preserve_secondary and len(harmony_palette) > 1):
                blended_palette.append(harmony_color)
                continue
                
            # If we have a matching cultural color, blend them
            if i < len(cultural_palette):
                cultural_color = cultural_palette[i]
                
                # Convert to HSV for better blending
                h1, s1, v1 = self.rgb_to_hsv(*harmony_color)
                h2, s2, v2 = self.rgb_to_hsv(*cultural_color)
                
                # Blend the colors based on influence
                # For hue, we need to handle the circular nature
                h_diff = (h2 - h1) % 1.0
                if h_diff > 0.5:
                    h_diff -= 1.0
                new_h = (h1 + influence * h_diff) % 1.0
                
                # Blend saturation and value linearly
                new_s = s1 + influence * (s2 - s1)
                new_v = v1 + influence * (v2 - v1)
                
                blended_palette.append(self.hsv_to_rgb(new_h, new_s, new_v))
            else:
                # Keep original harmony color if no cultural match
                blended_palette.append(harmony_color)
                
        return blended_palette
    
    def create_palette_preview(self, palette, width, height, descriptions=None):
        """Create a visual preview of the color palette"""
        # Create a new image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate swatch width - ensure minimum width per swatch
        min_swatch_width = 210 # Minimum width per color patch
        calculated_width = len(palette) * min_swatch_width
        
        # If calculated width exceeds provided width, use calculated width
        if calculated_width > width:
            # Create a wider image than requested
            img = Image.new('RGBA', (calculated_width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            swatch_width = min_swatch_width
        else:
            swatch_width = width // len(palette)
        
        # Try to load a font for color labels
        font = None
        try:
            font_size = min(16, height // 6)  # Slightly larger font
            # Try to find a system font
            if sys.platform == "win32":
                font_path = os.path.join(os.environ["WINDIR"], "Fonts", "Arial.ttf")
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
            # Add other OS font paths here
        except:
            pass
            
        if font is None:
            try:
                font = ImageFont.load_default()
            except:
                pass
    
        # Draw each color swatch
        for i, color in enumerate(palette):
            x1 = i * swatch_width
            x2 = (i + 1) * swatch_width
            
            # Draw the color rectangle
            draw.rectangle([x1, 0, x2, height], fill=color)
            
            # Add separator line
            if i < len(palette) - 1:
                draw.line([x2, 0, x2, height], fill=(0, 0, 0, 128), width=1)
                
            # Add color hex text if font is available
            if font is not None:
                hex_color = self.rgb_to_hex(*color)
                text_color = (0, 0, 0, 255) if sum(color) > 384 else (255, 255, 255, 255)
                
                # Position text in the center of swatch
                text_x = x1 + swatch_width // 2
                text_y = height - 20
                
                # Draw text with slight outline for readability
                draw.text((text_x-1, text_y), hex_color, fill=(0, 0, 0, 200), font=font, anchor="ms")
                draw.text((text_x+1, text_y), hex_color, fill=(0, 0, 0, 200), font=font, anchor="ms")
                draw.text((text_x, text_y-1), hex_color, fill=(0, 0, 0, 200), font=font, anchor="ms")
                draw.text((text_x, text_y+1), hex_color, fill=(0, 0, 0, 200), font=font, anchor="ms")
                draw.text((text_x, text_y), hex_color, fill=text_color, font=font, anchor="ms")
                
                # Add description if provided
                if descriptions and i < len(descriptions) and descriptions[i]:
                    desc_y = 15
                    # Truncate description if too long
                    desc = descriptions[i]
                    if len(desc) > 20:
                        desc = desc[:17] + "..."
                    
                    # Draw description text with outline
                    draw.text((text_x-1, desc_y), desc, fill=(0, 0, 0, 200), font=font, anchor="ms")
                    draw.text((text_x+1, desc_y), desc, fill=(0, 0, 0, 200), font=font, anchor="ms")
                    draw.text((text_x, desc_y-1), desc, fill=(0, 0, 0, 200), font=font, anchor="ms")
                    draw.text((text_x, desc_y+1), desc, fill=(0, 0, 0, 200), font=font, anchor="ms")
                    draw.text((text_x, desc_y), desc, fill=text_color, font=font, anchor="ms")
        
        # Add border around the entire palette
        draw.rectangle([0, 0, width-1, height-1], outline=(0, 0, 0, 255), width=1)
        
        # Convert to tensor for ComfyUI
        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None, ...]
        
        return img_tensor
    
    def generate_palette(self, 
                         color_selection_method, base_color_category, base_color_from_category, base_color_from_list,
                         harmony_model, culture, concept, palette_size,
                         use_secondary_color=False, secondary_color_method="By Category", 
                         secondary_color_category="Basic", secondary_color_from_category="red", secondary_color_from_list="red",
                         custom_base_color="", custom_secondary_color="",
                         cultural_influence=0.5, saturation=0.8, value=0.8,
                         preview_width=512, preview_height=128, color_preview=True):
        """Generate a harmonious color palette with cultural influence"""
        # Determine base color based on selection method
        if custom_base_color:
            selected_base_color = custom_base_color
        elif color_selection_method == "By Category":
            selected_base_color = base_color_from_category
        else:  # By Name
            selected_base_color = base_color_from_list
            
        base_rgb = self.get_rgb_for_color(selected_base_color)
        
        # Determine if we should use a secondary color and which one
        secondary_rgb = None
        if use_secondary_color:
            if custom_secondary_color:
                selected_secondary_color = custom_secondary_color
            elif secondary_color_method == "By Category":
                selected_secondary_color = secondary_color_from_category
            else:  # By Name
                selected_secondary_color = secondary_color_from_list
                
            secondary_rgb = self.get_rgb_for_color(selected_secondary_color)
        
        # Generate harmony-based palette
        harmony_palette = self.generate_harmony_palette(
            base_rgb, harmony_model, palette_size, secondary_rgb, saturation, value
        )
        
        # Get culturally significant colors
        cultural_palette = self.get_cultural_colors(culture, concept)
        
        # Blend the palettes
        final_palette = self.blend_palettes(
            harmony_palette, 
            cultural_palette, 
            cultural_influence,
            preserve_base=True,
            preserve_secondary=(use_secondary_color and secondary_rgb is not None)
        )
        
        # Create descriptions (for display purposes)
        descriptions = []
        for i, color in enumerate(final_palette):
            if i == 0:
                descriptions.append("Base")
            elif i == 1 and secondary_rgb and harmony_model in ["Complementary", "Tetradic"]:
                descriptions.append("Secondary")
            else:
                descriptions.append("")
        
        # Create palette preview
        preview = self.create_palette_preview(final_palette, preview_width, preview_height, descriptions)
        
        # Convert to hex strings
        hex_colors = [self.rgb_to_hex(*color) for color in final_palette]
        
        # Pad with empty strings if needed
        while len(hex_colors) < 6:
            hex_colors.append("")
        
        # If color_preview is enabled, create a color picker preview
        if color_preview:
            # Create color picker preview
            color_picker_preview = self.create_color_picker_preview(preview_width, preview_height)
            # Add the color picker preview to the outputs after the palette preview
            return tuple(hex_colors + [preview, color_picker_preview])
        
        return tuple(hex_colors + [preview])
    
    def create_color_picker_preview(self, width, height):
        """Create a visual preview of available colors for picking"""
        # Calculate layout
        colors_per_row = 16
        swatch_width = width // colors_per_row
        swatch_height = 24
        
        # Calculate how many rows we need
        all_colors = list(COLOR_NAMES.keys())
        num_colors = len(all_colors)
        rows = (num_colors + colors_per_row - 1) // colors_per_row
        
        # Create image with enough height for all rows
        total_height = rows * swatch_height
        img = Image.new('RGBA', (width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Try to load a font for color labels
        font = None
        try:
            font_size = 10
            # Try to find a system font
            if sys.platform == "win32":
                font_path = os.path.join(os.environ["WINDIR"], "Fonts", "Arial.ttf")
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
            # Add other OS font paths here
        except:
            pass
            
        if font is None:
            try:
                font = ImageFont.load_default()
            except:
                pass
        
        # Sort colors by hue for a better visual representation
        def rgb_to_hsv(r, g, b):
            r, g, b = r/255.0, g/255.0, b/255.0
            return colorsys.rgb_to_hsv(r, g, b)
        
        color_with_hsv = []
        for color_name in all_colors:
            r, g, b = COLOR_NAMES[color_name]
            h, s, v = rgb_to_hsv(r, g, b)
            color_with_hsv.append((color_name, (r, g, b), h))
        
        # Sort by hue
        color_with_hsv.sort(key=lambda x: x[2])
        
        # Draw color swatches
        for i, (color_name, rgb, _) in enumerate(color_with_hsv):
            row = i // colors_per_row
            col = i % colors_per_row
            
            x1 = col * swatch_width
            y1 = row * swatch_height
            x2 = x1 + swatch_width
            y2 = y1 + swatch_height
            
            # Draw the color rectangle
            draw.rectangle([x1, y1, x2, y2], fill=rgb)
            
            # Add color name if font is available and there's enough space
            if font is not None and swatch_width > 30:
                # Determine text color (white on dark colors, black on light colors)
                text_color = (0, 0, 0, 255) if sum(rgb) > 384 else (255, 255, 255, 255)
                
                # Truncate name if too long
                display_name = color_name
                if len(display_name) > 8:
                    display_name = display_name[:7] + "…"
                
                # Draw text centered in swatch
                text_x = x1 + swatch_width // 2
                text_y = y1 + swatch_height // 2
                draw.text((text_x, text_y), display_name, fill=text_color, font=font, anchor="mm")
        
        # Convert to tensor for ComfyUI
        img_np = np.array(img).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None, ...]
        
        return img_tensor
    
    # Add these update methods correctly as instance methods
    def update_base_color_options(self, **kwargs):
        category = kwargs.get("base_color_category", "Basic")
        
        if category in self.color_options:
            return {"base_color_from_category": self.color_options[category]}
        else:
            return {"base_color_from_category": self.color_options["Basic"]}

    def update_secondary_color_options(self, **kwargs):
        category = kwargs.get("secondary_color_category", "Basic")
        
        if category in self.color_options:
            return {"secondary_color_from_category": self.color_options[category]}
        else:
            return {"secondary_color_from_category": self.color_options["Basic"]}

# Register the node with UI update methods
NODE_CLASS_MAPPINGS = {
    "CulturalColorPaletteGenerator_v01": CulturalColorPaletteGeneratorNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CulturalColorPaletteGenerator_v01": "Cultural Color Palette Generator V01"
}