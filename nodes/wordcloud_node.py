"""
ComfyUI Node: WordCloud Generator Node
Description: Generate word clouds with comprehensive customization options including
    fonts, colors, layouts, special words placement, and cultural color harmonies.
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
- wordcloud: MIT License
- PIL (Pillow): HPND License
- matplotlib: PSF License
- random: Python Standard Library

"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor
import os
import sys
import re
import json
import random
import time
import random
import time
from collections import Counter, defaultdict
import json

# WordCloud library imports
try:
    from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator, get_single_color_func, random_color_func
    WORDCLOUD_AVAILABLE = True
except ImportError:
    print("WordCloud library not available. Please install with: pip install wordcloud")
    WORDCLOUD_AVAILABLE = False

# Import color names dictionary and cultural color data
try:
    from .color_names import COLOR_NAMES
except ImportError:
    try:
        from ..data.color_names import COLOR_NAMES
    except ImportError:
        # Fallback basic colors if color_names not available
        COLOR_NAMES = {
            'red': (255, 0, 0), 'green': (0, 255, 0), 'blue': (0, 0, 255),
            'white': (255, 255, 255), 'black': (0, 0, 0), 'yellow': (255, 255, 0),
            'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'orange': (255, 165, 0),
            'purple': (128, 0, 128), 'pink': (255, 192, 203), 'brown': (165, 42, 42)
        }

# Import cultural color data
try:
    from ..data.color_data.color_combinations_cultural import color_combinations
    from ..data.color_data.color_across_cultures import colors_across_cultures
    from ..data.color_data.color_significance_gpt import color_significance
    CULTURAL_DATA_AVAILABLE = True
except ImportError:
    print("Cultural color data not available, using built-in color sets")
    color_combinations = []
    colors_across_cultures = []
    color_significance = {}
    CULTURAL_DATA_AVAILABLE = False

# Helper function to extract colors from cultural data
def extract_cultural_colors():
    """Extract color combinations from cultural data"""
    cultural_sets = {}
    
    if CULTURAL_DATA_AVAILABLE and color_combinations:
        for combo in color_combinations:
            combo_name = combo.get("combo_name", "").replace(" & ", "_").replace(" ", "_").lower()
            if combo_name:
                # Extract colors from combo name
                colors = []
                color_words = combo["combo_name"].lower().split()
                for word in color_words:
                    word = word.replace(",", "").replace("&", "").strip()
                    # Map color names to hex values
                    if word == "red":
                        colors.append("#DC143C")
                    elif word == "white":
                        colors.append("#FFFFFF")
                    elif word == "green":
                        colors.append("#228B22")
                    elif word == "blue":
                        colors.append("#0000FF")
                    elif word == "yellow" or word == "gold":
                        colors.append("#FFD700")
                    elif word == "black":
                        colors.append("#000000")
                
                if colors:
                    cultural_sets[combo_name] = colors
    
    return cultural_sets

def extract_regional_colors():
    """Extract colors based on regional significance"""
    regional_sets = {}
    
    if CULTURAL_DATA_AVAILABLE and color_significance:
        for color, regions in color_significance.items():
            color_rgb = None
            # Get RGB value for this color
            for name, rgb in COLOR_NAMES.items():
                if name.lower() == color.lower():
                    color_rgb = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    break
            
            if not color_rgb:
                # Fallback color mapping
                color_map = {
                    "Red": "#DC143C", "White": "#FFFFFF", "Black": "#000000",
                    "Green": "#228B22", "Yellow": "#FFD700", "Blue": "#0000FF",
                    "Purple": "#800080", "Pink": "#FFC0CB", "Brown": "#8B4513"
                }
                color_rgb = color_map.get(color, "#808080")
            
            # Create sets by region
            for region in regions.keys():
                region_key = f"{region.lower()}_theme"
                if region_key not in regional_sets:
                    regional_sets[region_key] = []
                regional_sets[region_key].append(color_rgb)
    
    return regional_sets

def create_color_harmonies():
    """Create color harmony sets based on color theory"""
    harmonies = {}
    
    # Create complementary pairs from COLOR_NAMES
    primary_colors = {}
    for name, rgb in list(COLOR_NAMES.items())[:200]:  # Use first 200 colors
        # Group colors by approximate hue
        r, g, b = rgb
        if r > g and r > b:
            primary_colors.setdefault('red_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
        elif g > r and g > b:
            primary_colors.setdefault('green_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
        elif b > r and b > g:
            primary_colors.setdefault('blue_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
        elif r == g and r > b:
            primary_colors.setdefault('yellow_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
        elif r == b and r > g:
            primary_colors.setdefault('purple_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
        elif g == b and g > r:
            primary_colors.setdefault('cyan_family', []).append(f"#{r:02x}{g:02x}{b:02x}")
    
    # Create harmony sets
    for family_name, colors in primary_colors.items():
        if len(colors) >= 3:
            harmonies[f"{family_name}_harmony"] = colors[:7]  # Take first 7 colors
    
    # Add some specific harmonies
    harmonies.update({
        "warm_harmony": ["#FF4500", "#FF6347", "#FF8C00", "#FFD700", "#FFA500", "#DC143C"],
        "cool_harmony": ["#4169E1", "#1E90FF", "#00CED1", "#20B2AA", "#32CD32", "#00FA9A"],
        "pastel_harmony": ["#FFB6C1", "#E6E6FA", "#F0E68C", "#98FB98", "#AFEEEE", "#DDA0DD"],
        "earth_harmony": ["#8B4513", "#A0522D", "#CD853F", "#DEB887", "#F4A460", "#DAA520"],
        "jewel_harmony": ["#8B008B", "#4B0082", "#191970", "#006400", "#8B0000", "#B8860B"]
    })
    
    return harmonies

# Create color harmonies
COLOR_HARMONIES = create_color_harmonies()

# Get colors from your cultural data
CULTURAL_COLOR_SETS_FROM_DATA = extract_cultural_colors()
REGIONAL_COLOR_SETS = extract_regional_colors()

# Cultural and emotional color sets (enhanced with your data)
CULTURAL_COLOR_SETS = {
    # Your existing data-driven sets
    **CULTURAL_COLOR_SETS_FROM_DATA,
    **REGIONAL_COLOR_SETS,
    
    # Color harmony sets
    **COLOR_HARMONIES,
    
    # Enhanced built-in sets
    "western_vibrant": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"],
    "eastern_harmony": ["#D63031", "#74B9FF", "#00B894", "#FDCB6E", "#6C5CE7", "#FD79A8", "#E17055"],
    "earth_tones": ["#8B4513", "#D2691E", "#CD853F", "#DEB887", "#F4A460", "#DAA520", "#B8860B"],
    "ocean_blues": ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087", "#f95d6a", "#ff7c43"],
    "forest_greens": ["#1B4332", "#2D5016", "#40916C", "#52B788", "#74C69D", "#95D5B2", "#B7E4C7"],
    "sunset_warm": ["#FF6B35", "#F7931E", "#FFD23F", "#EE4266", "#540D6E", "#F15BB5", "#FEE75C"],
    "nordic_cool": ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51", "#6A994E", "#A7C957"],
    "japanese_traditional": ["#DC143C", "#FF1493", "#4169E1", "#32CD32", "#FFD700", "#FF8C00", "#9932CC"],
    "minimalist_mono": ["#2C3E50", "#34495E", "#7F8C8D", "#95A5A6", "#BDC3C7", "#ECF0F1", "#FFFFFF"],
    "retro_80s": ["#FF006E", "#00F5FF", "#FFBE0B", "#8338EC", "#3A86FF", "#06FFA5", "#FB5607"],
    
    # Christmas/Holiday combinations from your data
    "christmas_traditional": ["#DC143C", "#228B22", "#FFD700", "#FFFFFF"],  # Red, Green, Gold, White
    "pan_african": ["#228B22", "#FFD700", "#DC143C"],  # Green, Yellow, Red
    "islamic_colors": ["#228B22", "#FFFFFF"],  # Green and White
    "scandinavian": ["#0000FF", "#FFFFFF", "#FFD700"],  # Blue, White, Gold
}

EMOTIONAL_COLOR_SETS = {
    "energetic": ["#FF0040", "#FF8C00", "#FFD700", "#32CD32", "#00CED1", "#FF1493", "#FF69B4"],
    "calming": ["#87CEEB", "#98FB98", "#F0E68C", "#DDA0DD", "#FFB6C1", "#B0E0E6", "#E6E6FA"],
    "professional": ["#2C3E50", "#34495E", "#2980B9", "#27AE60", "#F39C12", "#E74C3C", "#9B59B6"],
    "creative": ["#E91E63", "#9C27B0", "#673AB7", "#3F51B5", "#2196F3", "#00BCD4", "#009688"],
    "warm_cozy": ["#8B4513", "#CD853F", "#D2691E", "#FF8C69", "#FFA07A", "#F0E68C", "#DDA0DD"],
    "cool_modern": ["#1E3A8A", "#1E40AF", "#3B82F6", "#06B6D4", "#10B981", "#8B5CF6", "#A855F7"],
    "nature_inspired": ["#228B22", "#32CD32", "#9ACD32", "#ADFF2F", "#7CFC00", "#00FF7F", "#00FA9A"],
    "romantic": ["#FF69B4", "#FFB6C1", "#FFC0CB", "#FFCCCB", "#F08080", "#FA8072", "#E9967A"],
    "bold_confident": ["#DC143C", "#B22222", "#FF4500", "#FF6347", "#FF7F50", "#FF8C00", "#FFA500"],
    "mysterious": ["#2F2F2F", "#4B0082", "#483D8B", "#6A5ACD", "#7B68EE", "#9370DB", "#8A2BE2"]
}

# Get system fonts directory based on OS (borrowed from text overlay node)
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

class EricsWordCloudNode:
    @classmethod
    def INPUT_TYPES(cls):
        if not WORDCLOUD_AVAILABLE:
            return {
                "required": {
                    "error_message": ("STRING", {"default": "WordCloud library not installed. Please run: pip install wordcloud", "multiline": True})
                }
            }
        
        fonts = get_available_fonts()
        font_names = [font[0] for font in fonts]
        
        # For testing if the font list is empty or failed
        if not font_names:
            font_names = ["Arial", "Helvetica", "Times New Roman"]
        
        cultural_sets = list(CULTURAL_COLOR_SETS.keys())
        emotional_sets = list(EMOTIONAL_COLOR_SETS.keys())
        
        # Create list of named colors from your color database - prioritize common colors
        basic_colors = ['white', 'black', 'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'cyan', 'magenta']
        other_colors = [name for name in COLOR_NAMES.keys() if name not in basic_colors][:37]  # Take 37 more for total of 50
        named_color_list = basic_colors + other_colors
        
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "word cloud text generation sample example", 
                                  "placeholder": "Enter text to generate word cloud from"}),
                "width": ("INT", {"default": 800, "min": 100, "max": 4096, "step": 1}),
                "height": ("INT", {"default": 600, "min": 100, "max": 4096, "step": 1}),
                "max_words": ("INT", {"default": 200, "min": 10, "max": 1000, "step": 10}),
                "min_font_size": ("INT", {"default": 8, "min": 4, "max": 100, "step": 1}),
                "max_font_size": ("INT", {"default": 100, "min": 10, "max": 500, "step": 1}),
                "background_mode": (["transparent", "solid_color"], {"default": "solid_color"}),
                "background_color": ("STRING", {"default": "#000000", "placeholder": "Background color (hex or name)"}),
            },
            "optional": {
                # Color options
                "color_mode": (["single_color_hex", "single_color_name", "random_colors", "cultural_set", "emotional_set", "color_harmony", "custom_range", "matplotlib_colormap"], 
                              {"default": "random_colors"}),
                "single_color_hex": ("STRING", {"default": "#FFFFFF", "placeholder": "Hex color for all words (e.g. #FF0000)"}),
                "single_color_name": (named_color_list, {"default": named_color_list[0] if named_color_list else "Red"}),
                "cultural_color_set": (cultural_sets, {"default": cultural_sets[0] if cultural_sets else "western_vibrant"}),
                "emotional_color_set": (emotional_sets, {"default": emotional_sets[0] if emotional_sets else "energetic"}),
                "color_harmony_set": (list(COLOR_HARMONIES.keys()), {"default": list(COLOR_HARMONIES.keys())[0] if COLOR_HARMONIES else "warm_harmony"}),
                "custom_color_range": ("STRING", {"default": "#FF0000,#00FF00,#0000FF", 
                                                "placeholder": "Comma-separated hex colors or named colors"}),
                "matplotlib_colormap": (["viridis", "plasma", "inferno", "magma", "cividis", "turbo", "hot", "cool", "spring", "summer", "autumn", "winter", 
                                        "Blues", "Reds", "Greens", "Oranges", "Purples", "Greys", "rainbow", "jet"], 
                                       {"default": "viridis", "tooltip": "Matplotlib colormap for scientific color schemes"}),
                
                # Font options
                "font_mode": (["single_font", "random_font_per_word", "random_font_per_cloud", "font_set"], 
                             {"default": "single_font"}),
                "primary_font": (font_names, {"default": font_names[0] if font_names else "Arial"}),
                "font_set": ("STRING", {"default": "Arial,Times New Roman,Courier New", 
                                       "placeholder": "Comma-separated font names"}),
                
                # Layout options
                "prefer_horizontal": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, 
                                               "tooltip": "Ratio of horizontal vs vertical words"}),
                "allow_vertical": ("BOOLEAN", {"default": True}),
                # Note: WordCloud library doesn't support upside down or diagonal text
                # "allow_upside_down": ("BOOLEAN", {"default": False}),
                # "allow_diagonal": ("BOOLEAN", {"default": False}),
                "margin": ("INT", {"default": 5, "min": 0, "max": 50, "step": 1, 
                                  "tooltip": "Margin between words and canvas edge"}),
                "word_spacing": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1, 
                                          "tooltip": "Font scaling factor - higher values = larger fonts and more spacing"}),
                
                # Text processing options
                "generation_mode": (["from_text", "from_frequencies"], {"default": "from_text", "tooltip": "Generate from text or predefined word frequencies"}),
                "word_frequencies": ("STRING", {"default": "", "multiline": True, 
                                               "placeholder": "word1:0.8\nword2:0.5\nword3:0.2\n(Only used in from_frequencies mode)"}),
                "include_numbers": ("BOOLEAN", {"default": False}),
                "normalize_plurals": ("BOOLEAN", {"default": True, "tooltip": "Combine plural/singular words (cats+cat→cat) for cleaner clouds"}),
                "text_case": (["as_input", "uppercase", "lowercase", "title_case"], {"default": "as_input", "tooltip": "Transform text case before processing"}),
                "collocations": ("BOOLEAN", {"default": True, "tooltip": "Include word pairs/phrases"}),
                "min_word_length": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1}),
                "collocation_threshold": ("INT", {"default": 30, "min": 10, "max": 100, "step": 5, 
                                                  "tooltip": "Min frequency for word pairs to become phrases (requires more text to see effect)"}),
                "custom_stopwords": ("STRING", {"default": "", "multiline": True, 
                                               "placeholder": "Additional words to exclude (one per line)"}),
                
                # Special words and phrases
                "special_words": ("STRING", {"default": "", "multiline": True, 
                                           "placeholder": "Special words/phrases with settings (JSON format)",
                                           "tooltip": "Boost word frequency/size using JSON. Note: Positioning not supported by WordCloud library"}),
                "special_words_example": ("STRING", {"default": '{"IMPORTANT": {"size_multiplier": 3.0}, "key phrase": {"size_multiplier": 2.5}}', 
                                                   "multiline": True, "tooltip": "Example: Boost word frequency to make them larger (positioning not supported)"}),
                
                # Preview options
                "preview_text": ("STRING", {"default": "Font Preview Sample", "tooltip": "Text for font preview"}),
                
                # Advanced options
                "enable_svg_export": ("BOOLEAN", {"default": False, "tooltip": "Generate SVG version as string output"}),
                "svg_embed_font": ("BOOLEAN", {"default": False, "tooltip": "Embed font in SVG (requires fontTools)"}),
                "relative_scaling": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.1, 
                                             "tooltip": "Balance frequency vs rank sizing: 0=uniform sizes, 1=high variation, 0.8=balanced"}),
                "repeat_words": ("BOOLEAN", {"default": False, "tooltip": "Repeat words to fill space"}),
                "random_seed": ("INT", {"default": 42, "min": 0, "max": 999999, "step": 1, 
                                       "tooltip": "Random seed for reproducible results"}),
                
                # Text file input
                "text_file_path": ("STRING", {"default": "", "placeholder": "Path to .txt file (optional, will override text field)"}),
                
                # Image and mask options
                "mask_placement": (["inside_mask", "outside_mask"], {"default": "inside_mask", "tooltip": "Place words inside or outside mask area"}),
                
                # Optional image inputs
                "input_image": ("IMAGE", {"tooltip": "Optional background image to overlay word cloud on"}),
                "mask_image": ("MASK", {"tooltip": "Optional mask to control word placement area"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("wordcloud", "font_preview", "color_preview", "svg_export", "used_words")
    FUNCTION = "generate_wordcloud"
    CATEGORY = "image/text"

    def __init__(self):
        self.fonts_cache = {}
        self.system_fonts = dict(get_available_fonts())
        self.debug = True  # Set to True to enable debug messages
        
        # Create a sorted list of fonts for preview
        self.sorted_fonts = sorted(self.system_fonts.keys(), key=lambda x: x.lower())

    def load_text_from_file(self, file_path):
        """Load text from a text file"""
        if not file_path or not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"Error loading text from file {file_path}: {str(e)}")
            return None

    def parse_color(self, color_str):
        """Parse color string to RGB tuple using comprehensive color database"""
        if not color_str:
            return None
            
        try:
            # Log the input for debugging
            if self.debug:
                print(f"EricsWordCloudNode: Parsing color: '{color_str}'")
            
            # First check for exact match (case insensitive) in our comprehensive color names dictionary
            for name, rgb in COLOR_NAMES.items():
                if name.lower() == color_str.lower():
                    if self.debug:
                        print(f"EricsWordCloudNode: Exact match found: {name} -> {rgb}")
                    return rgb
            
            # If it's a hex color, handle it directly
            if color_str.startswith('#'):
                result = ImageColor.getrgb(color_str)
                if self.debug:
                    print(f"EricsWordCloudNode: Hex color parsed: {color_str} -> {result}")
                return result
            
            # Try to parse as standard PIL color name
            try:
                result = ImageColor.getrgb(color_str)
                if self.debug:
                    print(f"EricsWordCloudNode: PIL color parsed: {color_str} -> {result}")
                return result
            except ValueError:
                pass  # Not a standard PIL color
            
            # Check for partial matches (case insensitive) as fallback
            color_lower = color_str.lower()
            for name, rgb in COLOR_NAMES.items():
                if color_lower in name.lower():
                    if self.debug:
                        print(f"EricsWordCloudNode: Partial match found: {color_str} matched {name} -> {rgb}")
                    return rgb
                    
        except Exception as e:
            print(f"EricsWordCloudNode: Error parsing color {color_str}: {str(e)}")
        
        # Default to white if nothing works
        if self.debug:
            print(f"EricsWordCloudNode: Color '{color_str}' not found, defaulting to white")
        return (255, 255, 255)

    def get_color_function(self, color_mode, single_color_hex=None, single_color_name=None, cultural_set=None, 
                          emotional_set=None, color_harmony_set=None, custom_colors=None, matplotlib_colormap=None, random_seed=42):
        """Create a color function based on the selected color mode"""
        random.seed(random_seed)
        
        if color_mode == "single_color_hex":
            color = self.parse_color(single_color_hex) or (255, 255, 255)
            if self.debug:
                print(f"EricsWordCloudNode: Using single hex color: {single_color_hex} -> rgb{color}")
            return lambda *args, **kwargs: f"rgb({color[0]}, {color[1]}, {color[2]})"
            
        elif color_mode == "single_color_name":
            if self.debug:
                print(f"EricsWordCloudNode: Processing single_color_name: '{single_color_name}'")
            color = self.parse_color(single_color_name) or (255, 255, 255)
            if self.debug:
                print(f"EricsWordCloudNode: Using single named color: {single_color_name} -> rgb{color}")
            return lambda *args, **kwargs: f"rgb({color[0]}, {color[1]}, {color[2]})"
            
        elif color_mode == "cultural_set":
            colors = CULTURAL_COLOR_SETS.get(cultural_set, CULTURAL_COLOR_SETS.get("western_vibrant", ["#FF6B6B"]))
            parsed_colors = [self.parse_color(c) for c in colors]
            if self.debug:
                print(f"EricsWordCloudNode: Using cultural set: {cultural_set} with {len(colors)} colors")
            def cultural_color_func(*args, **kwargs):
                color = random.choice(parsed_colors)
                return f"rgb({color[0]}, {color[1]}, {color[2]})"
            return cultural_color_func
            
        elif color_mode == "emotional_set":
            colors = EMOTIONAL_COLOR_SETS.get(emotional_set, EMOTIONAL_COLOR_SETS.get("energetic", ["#FF0040"]))
            parsed_colors = [self.parse_color(c) for c in colors]
            if self.debug:
                print(f"EricsWordCloudNode: Using emotional set: {emotional_set} with {len(colors)} colors")
            def emotional_color_func(*args, **kwargs):
                color = random.choice(parsed_colors)
                return f"rgb({color[0]}, {color[1]}, {color[2]})"
            return emotional_color_func
            
        elif color_mode == "color_harmony":
            colors = COLOR_HARMONIES.get(color_harmony_set, COLOR_HARMONIES.get("warm_harmony", ["#FF4500"]))
            parsed_colors = [self.parse_color(c) for c in colors]
            if self.debug:
                print(f"EricsWordCloudNode: Using color harmony: {color_harmony_set} with {len(colors)} colors")
            def harmony_color_func(*args, **kwargs):
                color = random.choice(parsed_colors)
                return f"rgb({color[0]}, {color[1]}, {color[2]})"
            return harmony_color_func
            
        elif color_mode == "custom_range":
            if custom_colors:
                color_list = [c.strip() for c in custom_colors.split(',')]
                parsed_colors = [self.parse_color(c) for c in color_list if c.strip()]
                if parsed_colors:
                    if self.debug:
                        print(f"EricsWordCloudNode: Using custom colors: {len(parsed_colors)} colors parsed")
                    def custom_color_func(*args, **kwargs):
                        color = random.choice(parsed_colors)
                        return f"rgb({color[0]}, {color[1]}, {color[2]})"
                    return custom_color_func
        
        elif color_mode == "matplotlib_colormap":
            if matplotlib_colormap:
                return self.get_matplotlib_colormap_function(matplotlib_colormap, random_seed)
            
        # Default to random colors
        if self.debug:
            print(f"EricsWordCloudNode: Using random colors (default)")
        return random_color_func

    def get_font_function(self, font_mode, primary_font, font_set=None, random_seed=42):
        """Create a font function based on the selected font mode"""
        random.seed(random_seed)
        
        if font_mode == "single_font":
            font_path = self.system_fonts.get(primary_font)
            if font_path and os.path.exists(font_path):
                if self.debug:
                    print(f"EricsWordCloudNode: Using single font: {primary_font} at {font_path}")
                return font_path
            else:
                if self.debug:
                    print(f"EricsWordCloudNode: Font not found: {primary_font}, using default")
                return None  # Let WordCloud use default font
            
        elif font_mode == "font_set":
            # For font_set mode, we need to return a function that selects randomly from the set
            if font_set:
                font_list = [f.strip() for f in font_set.split(',')]
                available_fonts = []
                for f in font_list:
                    if f.strip() in self.system_fonts:
                        font_path = self.system_fonts[f.strip()]
                        if os.path.exists(font_path):
                            available_fonts.append(font_path)
                
                if available_fonts:
                    if self.debug:
                        print(f"EricsWordCloudNode: Font set mode with {len(available_fonts)} available fonts")
                    # Return the first font as WordCloud doesn't support per-word font variation natively
                    # We'll use a random one from the set
                    selected_font = random.choice(available_fonts)
                    return selected_font
                else:
                    if self.debug:
                        print(f"EricsWordCloudNode: No fonts from set found, using default")
                    return None
            
        elif font_mode == "random_font_per_cloud":
            if self.sorted_fonts:
                random_font = random.choice(self.sorted_fonts)
                font_path = self.system_fonts.get(random_font)
                if font_path and os.path.exists(font_path):
                    if self.debug:
                        print(f"EricsWordCloudNode: Random font selected: {random_font} at {font_path}")
                    return font_path
                else:
                    if self.debug:
                        print(f"EricsWordCloudNode: Random font path not found, using default")
                    return None
                
        elif font_mode == "random_font_per_word":
            # WordCloud doesn't support per-word fonts natively, so we'll fall back to random per cloud
            # In the future, this could be implemented with a custom WordCloud subclass
            if self.debug:
                print(f"EricsWordCloudNode: Per-word font variation not supported by WordCloud library, using random font per cloud")
            if self.sorted_fonts:
                random_font = random.choice(self.sorted_fonts)
                font_path = self.system_fonts.get(random_font)
                if font_path and os.path.exists(font_path):
                    if self.debug:
                        print(f"EricsWordCloudNode: Random font selected (fallback): {random_font} at {font_path}")
                    return font_path
                else:
                    if self.debug:
                        print(f"EricsWordCloudNode: Random font path not found, using default")
                    return None
        
        # Default to primary font
        font_path = self.system_fonts.get(primary_font)
        if font_path and os.path.exists(font_path):
            if self.debug:
                print(f"EricsWordCloudNode: Default to primary font: {primary_font} at {font_path}")
            return font_path
        else:
            if self.debug:
                print(f"EricsWordCloudNode: Primary font not found, using system default")
            return None

    def parse_word_frequencies(self, freq_text):
        """Parse word frequencies from text input"""
        if not freq_text.strip():
            return {}
            
        frequencies = {}
        try:
            for line in freq_text.strip().split('\n'):
                line = line.strip()
                if line and ':' in line:
                    word, freq_str = line.split(':', 1)
                    word = word.strip()
                    freq = float(freq_str.strip())
                    if word and 0.0 <= freq <= 1.0:
                        frequencies[word] = freq
                    elif self.debug:
                        print(f"EricsWordCloudNode: Invalid frequency for '{word}': {freq_str} (must be 0.0-1.0)")
        except Exception as e:
            print(f"EricsWordCloudNode: Error parsing word frequencies: {str(e)}")
            
        if self.debug and frequencies:
            print(f"EricsWordCloudNode: Parsed {len(frequencies)} word frequencies")
            
        return frequencies

    def get_matplotlib_colormap_function(self, colormap_name, random_seed=42):
        """Create a color function using matplotlib colormap"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.colors as mcolors
                        
            # Get the colormap
            cmap = plt.get_cmap(colormap_name)
            
            def colormap_func(*args, **kwargs):
                # Use random value to sample from colormap
                random.seed(random_seed + hash(str(args) + str(kwargs)) % 1000)
                t = random.random()  # Random value between 0 and 1
                rgba = cmap(t)
                # Convert to RGB (ignore alpha for wordcloud)
                rgb = tuple(int(c * 255) for c in rgba[:3])
                return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
            
            if self.debug:
                print(f"EricsWordCloudNode: Using matplotlib colormap: {colormap_name}")
                
            return colormap_func
            
        except ImportError:
            if self.debug:
                print("EricsWordCloudNode: Matplotlib not available, falling back to random colors")
            return random_color_func
        except Exception as e:
            if self.debug:
                print(f"EricsWordCloudNode: Error with colormap {colormap_name}: {str(e)}, falling back to random colors")
            return random_color_func

    def parse_special_words(self, special_words_json):
        """Parse special words JSON configuration"""
        if not special_words_json.strip():
            return {}
            
        try:
            special_config = json.loads(special_words_json)
            return special_config
        except json.JSONDecodeError as e:
            print(f"Error parsing special words JSON: {str(e)}")
            return {}

    def apply_special_words(self, text, special_config):
        """Apply special words configuration by boosting their frequency in the text"""
        if not special_config:
            return text
        
        # For each special word, repeat it in the text based on size_multiplier
        # This is a workaround since WordCloud doesn't support positioned text natively
        enhanced_text = text
        
        for word, config in special_config.items():
            # Remove quotes if present
            clean_word = word.strip('"\'')
            size_multiplier = config.get('size_multiplier', 1.0)
            
            # Calculate repetitions based on size multiplier
            # size_multiplier 2.0 = repeat word 3 extra times (total 4x frequency)
            extra_repetitions = max(0, int((size_multiplier - 1.0) * 3))
            
            if extra_repetitions > 0:
                # Add the word multiple times to boost its frequency
                repeat_text = " " + (" " + clean_word + " ") * extra_repetitions
                enhanced_text += repeat_text
                
                if self.debug:
                    print(f"EricsWordCloudNode: Boosted '{clean_word}' with {extra_repetitions} repetitions (size_multiplier: {size_multiplier})")
        
        return enhanced_text

    def transform_text_case(self, text, case_mode):
        """Transform text case based on selected mode"""
        if case_mode == "uppercase":
            return text.upper()
        elif case_mode == "lowercase":
            return text.lower()
        elif case_mode == "title_case":
            return text.title()
        else:  # "as_input"
            return text

    def generate_color_preview(self, color_mode, cultural_set=None, emotional_set=None, color_harmony_set=None, custom_colors=None, single_color_hex=None, single_color_name=None):
        """Generate a compact color palette preview image"""
        
        # Get colors based on mode
        colors = []
        title = "Color Preview"
        
        if color_mode == "single_color_hex":
            colors = [single_color_hex if single_color_hex else "#FFFFFF"]
            title = "Single Color (Hex)"
        elif color_mode == "single_color_name":
            colors = [single_color_name if single_color_name else "Red"]
            title = "Single Color (Named)"
        elif color_mode == "cultural_set" and cultural_set:
            colors = CULTURAL_COLOR_SETS.get(cultural_set, [])
            title = f"Cultural: {cultural_set.replace('_', ' ').title()}"
        elif color_mode == "emotional_set" and emotional_set:
            colors = EMOTIONAL_COLOR_SETS.get(emotional_set, [])
            title = f"Emotional: {emotional_set.replace('_', ' ').title()}"
        elif color_mode == "color_harmony" and color_harmony_set:
            colors = COLOR_HARMONIES.get(color_harmony_set, [])
            title = f"Harmony: {color_harmony_set.replace('_', ' ').title()}"
        elif color_mode == "custom_range" and custom_colors:
            colors = [c.strip() for c in custom_colors.split(',')]
            title = "Custom Colors"
        elif color_mode == "random_colors":
            # Show a sample of random colors
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
            title = "Random Colors (Sample)"
        else:
            # Fallback
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
            title = "Default Colors"
        
        if not colors:
            colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]  # Fallback
            
        # Calculate compact dimensions
        num_colors = len(colors)
        cols = min(6, num_colors)  # Max 6 columns for compact display
        rows = (num_colors + cols - 1) // cols
        
        swatch_size = 60  # Square swatches
        margin = 10
        header_height = 40
        
        width = (cols * swatch_size) + ((cols + 1) * margin)
        height = header_height + (rows * swatch_size) + ((rows + 1) * margin)
        
        # Create compact image
        img = Image.new('RGB', (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            title_font = ImageFont.truetype("arial.ttf", 16)
            small_font = ImageFont.truetype("arial.ttf", 10)
        except:
            try:
                title_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            except:
                title_font = small_font = None
            
        # Draw title
        draw.text((width // 2, 10), title, fill=(0, 0, 0), anchor="mt", font=title_font)
        
        # Draw color swatches
        for i, color_str in enumerate(colors):
            col = i % cols
            row = i // cols
            
            x = margin + col * (swatch_size + margin)
            y = header_height + row * (swatch_size + margin)
            
            # Parse color
            try:
                color_rgb = self.parse_color(color_str)
                if color_rgb:
                    # Draw color swatch
                    draw.rectangle([x, y, x + swatch_size, y + swatch_size], 
                                 fill=color_rgb, outline=(100, 100, 100))
                    
                    # Draw color label below swatch (truncated)
                    label = color_str[:8] if len(color_str) > 8 else color_str
                    label_y = y + swatch_size + 2
                    draw.text((x + swatch_size // 2, label_y), label, 
                            fill=(60, 60, 60), anchor="mt", font=small_font)
                            
            except Exception as e:
                # Draw error swatch
                draw.rectangle([x, y, x + swatch_size, y + swatch_size], 
                             fill=(128, 128, 128), outline=(100, 100, 100))
                draw.text((x + swatch_size // 2, y + swatch_size // 2), "ERR", 
                        fill=(255, 255, 255), anchor="mm", font=small_font)
        
        return img

    def generate_font_preview(self, sample_text, target_width, target_height):
        """Generate a comprehensive font preview showing all fonts in a multi-column layout"""
        num_fonts = len(self.sorted_fonts)
        
        if num_fonts == 0:
            # Create simple error image
            img = Image.new('RGB', (800, 200), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((400, 100), "No fonts available", fill=(255, 0, 0), anchor="mm")
            return img, 1, 1
        
        # Font preview configuration
        base_font_size = 24
        font_name_size = 16
        line_height = 70  # Height per font entry
        column_width = 400  # Width per column
        margin = 20
        header_height = 80
        
        # Calculate optimal layout
        # Try different column counts to find best fit
        best_columns = 1
        best_height = float('inf')
        
        for cols in range(1, 6):  # Test 1-5 columns
            rows_per_column = (num_fonts + cols - 1) // cols
            calc_width = margin + (cols * column_width) + ((cols - 1) * margin) + margin
            calc_height = header_height + (rows_per_column * line_height) + margin * 2
            
            # Prefer layouts that aren't too wide or too tall
            if calc_width <= 2000 and calc_height < best_height:
                best_columns = cols
                best_height = calc_height
        
        # Calculate final dimensions
        columns = best_columns
        rows_per_column = (num_fonts + columns - 1) // columns
        preview_width = margin + (columns * column_width) + ((columns - 1) * margin) + margin
        preview_height = header_height + (rows_per_column * line_height) + margin * 2
        
        # Create image
        img = Image.new('RGB', (preview_width, preview_height), (245, 245, 245))
        draw = ImageDraw.Draw(img)
        
        # Load fonts for UI text
        try:
            title_font = ImageFont.truetype("arial.ttf", 28)
            subtitle_font = ImageFont.truetype("arial.ttf", 18)
            name_font = ImageFont.truetype("arial.ttf", font_name_size)
        except:
            try:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
            except:
                title_font = subtitle_font = name_font = None
        
        # Draw header
        draw.rectangle([0, 0, preview_width, header_height], fill=(230, 230, 230), outline=(200, 200, 200))
        title_text = f"Font Preview - All {num_fonts} Available Fonts"
        draw.text((preview_width // 2, 20), title_text, fill=(0, 0, 0), anchor="mt", font=title_font)
        
        subtitle_text = f"Sample text: \"{sample_text}\" | Layout: {columns} columns × {rows_per_column} rows"
        draw.text((preview_width // 2, 50), subtitle_text, fill=(100, 100, 100), anchor="mt", font=subtitle_font)
        
        # Draw fonts in columns
        fonts_drawn = 0
        
        for col in range(columns):
            if fonts_drawn >= num_fonts:
                break
                
            # Calculate column position
            col_x = margin + col * (column_width + margin)
            
            # Draw column background
            col_bg_x1 = col_x - 10
            col_bg_x2 = col_x + column_width + 10
            col_bg_y1 = header_height + 10
            col_bg_y2 = preview_height - margin
            draw.rectangle([col_bg_x1, col_bg_y1, col_bg_x2, col_bg_y2], 
                          fill=(255, 255, 255), outline=(220, 220, 220))
            
            # Draw fonts in this column
            for row in range(rows_per_column):
                if fonts_drawn >= num_fonts:
                    break
                    
                font_name = self.sorted_fonts[fonts_drawn]
                y_pos = header_height + margin + (row * line_height)
                
                try:
                    # Get font path
                    font_path = self.system_fonts.get(font_name)
                    sample_font = None
                    
                    if font_path and os.path.exists(font_path):
                        try:
                            sample_font = ImageFont.truetype(font_path, base_font_size)
                        except Exception as e:
                            if self.debug:
                                print(f"EricsWordCloudNode: Could not load font {font_name}: {str(e)}")
                    
                    # If we couldn't load the font, use default
                    if sample_font is None:
                        sample_font = name_font
                    
                    # Draw font name (always in default font for consistency)
                    name_y = y_pos + 5
                    draw.text((col_x, name_y), font_name, fill=(80, 80, 80), font=name_font)
                    
                    # Draw sample text in the actual font
                    sample_y = y_pos + 25
                    
                    # Truncate sample text if too long for column
                    display_text = sample_text
                    if len(display_text) > 25:  # Approximate character limit per column
                        display_text = display_text[:22] + "..."
                    
                    # Try to draw with the actual font, fall back to default if it fails
                    try:
                        draw.text((col_x, sample_y), display_text, fill=(20, 20, 20), font=sample_font)
                    except Exception as e:
                        # Font might not support certain characters
                        try:
                            # Try with ASCII-only version
                            ascii_text = ''.join(char for char in display_text if ord(char) < 128)
                            if ascii_text:
                                draw.text((col_x, sample_y), ascii_text, fill=(20, 20, 20), font=sample_font)
                            else:
                                draw.text((col_x, sample_y), "Sample Text", fill=(20, 20, 20), font=sample_font)
                        except:
                            # If all else fails, use default font
                            draw.text((col_x, sample_y), display_text, fill=(20, 20, 20), font=name_font)
                            # Add indicator that font failed
                            draw.text((col_x + column_width - 60, sample_y), "[unsupported]", fill=(200, 100, 100), font=name_font)
                    
                    # Draw separator line
                    if row < rows_per_column - 1 and fonts_drawn < num_fonts - 1:
                        line_y = y_pos + line_height - 5
                        draw.line([col_x, line_y, col_x + column_width - 20, line_y], fill=(230, 230, 230), width=1)
                    
                except Exception as e:
                    # Draw error indicator
                    draw.text((col_x, y_pos + 5), f"{font_name} [ERROR]", fill=(255, 0, 0), font=name_font)
                    draw.text((col_x, y_pos + 25), "Font could not be loaded", fill=(150, 150, 150), font=name_font)
                
                fonts_drawn += 1
        
        # Draw footer with statistics
        footer_y = preview_height - 15
        footer_text = f"Total fonts available: {num_fonts} | Successfully displayed: {fonts_drawn}"
        draw.text((preview_width // 2, footer_y), footer_text, fill=(120, 120, 120), anchor="mt", font=name_font)
        
        if self.debug:
            print(f"EricsWordCloudNode: Generated font preview with {fonts_drawn} fonts in {columns} columns")
        
        return img, 1, 1

    def create_custom_wordcloud_class(self, font_function=None, orientation_options=None):
        """Create a custom WordCloud class with enhanced orientation support"""
        
        class CustomWordCloud(WordCloud):
            def __init__(self, *args, **kwargs):
                self.custom_font_function = font_function
                self.orientation_options = orientation_options or {}
                super().__init__(*args, **kwargs)
                
            def choose_font_size(self, word, font_size, position, orientation, **kwargs):
                # Override font selection if using custom font function
                if self.custom_font_function and callable(self.custom_font_function):
                    return self.custom_font_function(word, font_size, position, orientation, **kwargs)
                return super().choose_font_size(word, font_size, position, orientation, **kwargs)
        
        return CustomWordCloud

    def ensure_compatible_format(self, tensor):
        """Ensure tensor is in the format expected by ComfyUI nodes"""
        # Check if we need to convert format
        if len(tensor.shape) == 3:
            tensor = tensor.unsqueeze(0)
            
        # Ensure we have RGBA format
        if tensor.shape[-1] == 3:
            # Add alpha channel
            alpha = torch.ones((*tensor.shape[:-1], 1), device=tensor.device)
            tensor = torch.cat([tensor, alpha], dim=-1)
            
        return tensor

    def tensor_to_pil(self, tensor):
        """Convert ComfyUI tensor to PIL Image"""
        if len(tensor.shape) == 4:
            tensor = tensor[0]  # Remove batch dimension
        
        # Convert to numpy and scale to 0-255
        np_image = (tensor.cpu().numpy() * 255).astype(np.uint8)
        
        # Handle different channel formats
        if np_image.shape[2] == 4:  # RGBA
            return Image.fromarray(np_image, 'RGBA')
        elif np_image.shape[2] == 3:  # RGB
            return Image.fromarray(np_image, 'RGB')
        else:  # Grayscale
            return Image.fromarray(np_image[:,:,0], 'L')

    def pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI tensor format"""
        # Ensure RGBA format
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        
        # Convert to numpy array and normalize to 0-1
        np_image = np.array(pil_image).astype(np.float32) / 255.0
        
        # Convert to tensor with batch dimension
        tensor = torch.from_numpy(np_image)[None, ...]
        
        return self.ensure_compatible_format(tensor)

    def get_optimal_dimensions(self, input_image, mask_image, default_width, default_height):
        """Determine optimal wordcloud dimensions based on input image and mask"""
        target_width = default_width
        target_height = default_height
        
        # Check if we have input image
        if input_image is not None:
            if len(input_image.shape) == 4:
                # Batch dimension present
                img_height, img_width = input_image.shape[1:3]
            else:
                img_height, img_width = input_image.shape[:2]
            target_width = img_width
            target_height = img_height
            if self.debug:
                print(f"EricsWordCloudNode: Using input image dimensions: {target_width}x{target_height}")
        
        # Check if we have mask
        if mask_image is not None:
            if len(mask_image.shape) == 3:
                # Remove batch dimension
                mask_height, mask_width = mask_image.shape[1:3]
            else:
                mask_height, mask_width = mask_image.shape[:2]
            
            # If we have both input image and mask, use the larger dimensions
            if input_image is not None:
                target_width = max(target_width, mask_width)
                target_height = max(target_height, mask_height)
                if self.debug:
                    print(f"EricsWordCloudNode: Both image and mask present, using larger dimensions: {target_width}x{target_height}")
            else:
                target_width = mask_width
                target_height = mask_height
                if self.debug:
                    print(f"EricsWordCloudNode: Using mask dimensions: {target_width}x{target_height}")
        
        return target_width, target_height

    def create_mask_from_image(self, mask_image, target_size, mask_placement):
        """Create a mask array for WordCloud from the mask image"""
        # Handle ComfyUI mask format (mask tensor is typically single channel)
        if len(mask_image.shape) == 3:
            # Remove batch dimension if present
            mask_array = mask_image[0].cpu().numpy()
        elif len(mask_image.shape) == 2:
            # Already 2D array
            mask_array = mask_image.cpu().numpy()
        else:
            # Convert tensor to numpy
            mask_array = mask_image.cpu().numpy()
            if len(mask_array.shape) > 2:
                mask_array = mask_array[0] if len(mask_array.shape) == 3 else mask_array
        
        # Ensure it's 2D
        if len(mask_array.shape) > 2:
            mask_array = mask_array[:, :, 0]  # Take first channel
        
        # Scale to 0-255 range if needed
        if mask_array.max() <= 1.0:
            mask_array = (mask_array * 255).astype(np.uint8)
        else:
            mask_array = mask_array.astype(np.uint8)
        
        # Resize to target size
        mask_pil = Image.fromarray(mask_array, 'L')
        mask_pil = mask_pil.resize(target_size, Image.Resampling.LANCZOS)
        mask_array = np.array(mask_pil)
        
        # WordCloud expects white areas for text placement
        # If mask_placement is "outside_mask", invert the mask
        if mask_placement == "outside_mask":
            # Invert: black becomes white (text area), white becomes black (no text)
            mask_array = 255 - mask_array
        # If mask_placement is "inside_mask", use as-is (white areas for text)
        
        # WordCloud expects binary mask where 0 = no text, 255 = allow text
        # Threshold the mask
        mask_array = np.where(mask_array > 127, 255, 0).astype(np.uint8)
        
        return mask_array

    def process_background_image(self, input_image, target_width, target_height):
        """Process input image to be used as background"""
        # Convert tensor to PIL
        bg_image = self.tensor_to_pil(input_image)
        
        # Resize to target dimensions
        bg_image = bg_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Ensure RGB mode for WordCloud background
        if bg_image.mode == 'RGBA':
            # Create white background and composite
            white_bg = Image.new('RGB', bg_image.size, (255, 255, 255))
            bg_image = Image.alpha_composite(white_bg.convert('RGBA'), bg_image).convert('RGB')
        elif bg_image.mode != 'RGB':
            bg_image = bg_image.convert('RGB')
        
        return bg_image

    def overlay_wordcloud_on_image(self, wordcloud_img, background_img):
        """Overlay word cloud on background image"""
        # Ensure both images are the same size
        if wordcloud_img.size != background_img.size:
            wordcloud_img = wordcloud_img.resize(background_img.size, Image.Resampling.LANCZOS)
        
        # Convert background to RGBA
        if background_img.mode != 'RGBA':
            background_img = background_img.convert('RGBA')
        
        # Ensure wordcloud is RGBA
        if wordcloud_img.mode != 'RGBA':
            wordcloud_img = wordcloud_img.convert('RGBA')
        
        # Create composite image
        composite = Image.alpha_composite(background_img, wordcloud_img)
        
        return composite

    def generate_wordcloud(self, text, width, height, max_words, min_font_size, max_font_size,
                          background_mode, background_color, color_mode="random_colors", 
                          single_color_hex=None, single_color_name=None, cultural_color_set=None, emotional_color_set=None,
                          color_harmony_set=None, custom_color_range=None, matplotlib_colormap=None,
                          generation_mode="from_text", word_frequencies="",
                          font_mode="single_font", primary_font=None,
                          font_set=None, prefer_horizontal=0.5, allow_vertical=True,
                          margin=5, word_spacing=1.0,
                          include_numbers=False, normalize_plurals=True, text_case="as_input", collocations=True,
                          min_word_length=2, collocation_threshold=30, custom_stopwords="",
                          special_words="", special_words_example="",
                          preview_text="Font Preview Sample",
                          relative_scaling=0.8, repeat_words=False, random_seed=42, text_file_path="",
                          mask_placement="inside_mask", input_image=None, mask_image=None,
                          enable_svg_export=False, svg_embed_font=False):
        
        if not WORDCLOUD_AVAILABLE:
            # Create error image
            img = Image.new('RGBA', (width, height), (255, 0, 0, 255))
            draw = ImageDraw.Draw(img)
            error_text = "WordCloud library not installed.\nPlease run: pip install wordcloud"
            draw.text((width//2, height//2), error_text, fill=(255, 255, 255), anchor="mm")
            
            img_np = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np)[None, ...]
            img_tensor = self.ensure_compatible_format(img_tensor)
            return (img_tensor, img_tensor, img_tensor, "", "")
        
        # Load text from file if specified
        if text_file_path and text_file_path.strip():
            file_text = self.load_text_from_file(text_file_path.strip())
            if file_text:
                text = file_text
                if self.debug:
                    print(f"EricsWordCloudNode: Loaded text from file: {text_file_path} ({len(text)} characters)")
            else:
                if self.debug:
                    print(f"EricsWordCloudNode: Failed to load text from file: {text_file_path}")
        
        if not text.strip():
            text = "No text provided for word cloud generation"
        
        # Parse special words configuration
        special_config = self.parse_special_words(special_words)
        
        # Process special words if provided
        if special_config:
            text = self.apply_special_words(text, special_config)
            if self.debug:
                print(f"EricsWordCloudNode: Applied special words configuration with {len(special_config)} entries")
        
        # Apply text case transformation
        text = self.transform_text_case(text, text_case)
        if self.debug and text_case != "as_input":
            print(f"EricsWordCloudNode: Applied text case transformation: {text_case}")
        
        # Set random seed for reproducibility
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        # Determine optimal dimensions based on input image and mask
        actual_width, actual_height = self.get_optimal_dimensions(input_image, mask_image, width, height)
        if self.debug:
            print(f"EricsWordCloudNode: Final dimensions: {actual_width}x{actual_height} (requested: {width}x{height})")
        
        # Parse background color
        bg_color = None if background_mode == "transparent" else self.parse_color(background_color)
        
        # Create stopwords set
        stopwords = set(STOPWORDS)
        if custom_stopwords.strip():
            custom_stops = set(line.strip().lower() for line in custom_stopwords.strip().split('\n') if line.strip())
            stopwords.update(custom_stops)
        
        # Adjust collocation settings to reduce word pairing
        if not collocations:
            # Disable collocations entirely
            collocation_threshold = 999999  # Very high threshold to prevent collocations
        elif collocation_threshold < 50:
            # Increase threshold to reduce word pairing
            collocation_threshold = max(50, collocation_threshold)
        
        # Get color function
        color_func = self.get_color_function(
            color_mode, single_color_hex, single_color_name, cultural_color_set, 
            emotional_color_set, color_harmony_set, custom_color_range, matplotlib_colormap, random_seed
        )
        
        # Get font path
        font_path = self.get_font_function(font_mode, primary_font, font_set, random_seed)
        
        if self.debug:
            print(f"EricsWordCloudNode: Font configuration - Mode: {font_mode}, Primary: {primary_font}, Path: {font_path}")
            if font_path and not os.path.exists(font_path):
                print(f"EricsWordCloudNode: WARNING - Font path does not exist: {font_path}")
            elif not font_path:
                print(f"EricsWordCloudNode: Using system default font")
        
        # Initialize variables for error handling
        wordcloud = None
        prefer_horizontal_ratio = prefer_horizontal
        
        try:
            # Calculate prefer_horizontal based on allow_vertical option
            if not allow_vertical:
                prefer_horizontal_ratio = 1.0  # Force all horizontal
            else:
                prefer_horizontal_ratio = prefer_horizontal  # Use user setting
            
            if self.debug:
                print(f"EricsWordCloudNode: Horizontal preference ratio: {prefer_horizontal_ratio} (allow_vertical: {allow_vertical})")
            
            # Process mask if provided
            mask_array = None
            if mask_image is not None:
                mask_array = self.create_mask_from_image(mask_image, (actual_width, actual_height), mask_placement)
                if self.debug:
                    print(f"EricsWordCloudNode: Using mask with placement: {mask_placement}")
            
            # Process background image if provided (scale to match final dimensions)
            background_img = None
            if input_image is not None:
                background_img = self.process_background_image(input_image, actual_width, actual_height)
                if self.debug:
                    print(f"EricsWordCloudNode: Using background image of size: {background_img.size}")
            
            # Create WordCloud instance with actual dimensions
            wc = WordCloud(
                width=actual_width,
                height=actual_height,
                max_words=max_words,
                min_font_size=min_font_size,
                max_font_size=max_font_size,
                background_color=None if background_mode == "transparent" else f"rgb({bg_color[0]}, {bg_color[1]}, {bg_color[2]})" if bg_color else "black",
                mode="RGBA" if background_mode == "transparent" else "RGB",
                color_func=color_func,
                font_path=font_path,
                prefer_horizontal=prefer_horizontal_ratio,
                margin=margin,
                mask=mask_array,  # Add mask support
                stopwords=stopwords,
                include_numbers=include_numbers,
                normalize_plurals=normalize_plurals,
                collocations=collocations,
                min_word_length=min_word_length,
                collocation_threshold=collocation_threshold,
                relative_scaling=relative_scaling,
                repeat=repeat_words,
                random_state=random_seed,
                scale=word_spacing
            )
            
            # Generate word cloud based on generation mode
            if generation_mode == "from_frequencies" and word_frequencies.strip():
                # Parse frequencies and generate from them
                frequencies = self.parse_word_frequencies(word_frequencies)
                if frequencies:
                    if self.debug:
                        print(f"EricsWordCloudNode: Generating from {len(frequencies)} word frequencies")
                    wordcloud = wc.generate_from_frequencies(frequencies)
                else:
                    if self.debug:
                        print("EricsWordCloudNode: No valid frequencies found, falling back to text generation")
                    wordcloud = wc.generate(text)
            else:
                # Standard text generation
                wordcloud = wc.generate(text)
            
            # Convert to PIL Image
            img = wordcloud.to_image()
            
            # Extract words used in the wordcloud for keywords
            used_words_list = []
            try:
                # Method 1: Get words from the frequency dictionary (most reliable)
                if hasattr(wordcloud, 'words_') and wordcloud.words_:
                    # Sort by frequency (higher frequency first) and get just the words
                    sorted_words = sorted(wordcloud.words_.items(), key=lambda x: x[1], reverse=True)
                    used_words_list = [word for word, freq in sorted_words]
                    if self.debug:
                        print(f"EricsWordCloudNode: Extracted {len(used_words_list)} words from words_ dict")
                
                # Method 2: Fallback to layout data if words_ not available
                elif hasattr(wordcloud, 'layout_') and wordcloud.layout_:
                    # Extract just the word text from layout data (word, freq, position, orientation, font_size, color)
                    for word_info in wordcloud.layout_:
                        if word_info and len(word_info) > 0:
                            word_text = word_info[0][0] if isinstance(word_info[0], tuple) else str(word_info[0])
                            # Clean any potential SVG formatting
                            word_text = word_text.strip().replace('<', '').replace('>', '')
                            if word_text and not word_text.startswith('text') and not word_text.startswith('svg'):
                                used_words_list.append(word_text)
                    if self.debug:
                        print(f"EricsWordCloudNode: Extracted {len(used_words_list)} words from layout_")
                
                # Remove duplicates while preserving order
                seen = set()
                unique_words = []
                for word in used_words_list:
                    if word not in seen:
                        seen.add(word)
                        unique_words.append(word)
                used_words_list = unique_words
                
                if self.debug:
                    print(f"EricsWordCloudNode: Final word list: {used_words_list[:10]}..." if len(used_words_list) > 10 else f"EricsWordCloudNode: Final word list: {used_words_list}")
                    
            except Exception as e:
                if self.debug:
                    print(f"EricsWordCloudNode: Error extracting words: {str(e)}")
                used_words_list = []
            
            # Convert words list to comma-separated string for keywords
            used_words_string = ", ".join(used_words_list) if used_words_list else ""
            
            # Handle SVG export if requested
            svg_content = ""
            if enable_svg_export:
                try:
                    svg_content = wordcloud.to_svg()
                    if self.debug:
                        print(f"EricsWordCloudNode: Generated SVG content ({len(svg_content)} characters)")
                except Exception as e:
                    if self.debug:
                        print(f"EricsWordCloudNode: SVG export failed: {str(e)}")
                    svg_content = f"<!-- SVG export failed: {str(e)} -->"
            
            # Ensure RGBA format for transparency support
            if img.mode != 'RGBA':
                if background_mode == "transparent":
                    # Convert to RGBA with transparent background
                    img = img.convert('RGBA')
                    # Make background transparent
                    data = np.array(img)
                    if bg_color:
                        # Replace background color with transparency
                        bg_rgb = bg_color[:3]
                        mask = np.all(data[:,:,:3] == bg_rgb, axis=2)
                        data[mask] = [0, 0, 0, 0]
                    else:
                        # Replace black background with transparency
                        mask = np.all(data[:,:,:3] == [0, 0, 0], axis=2)
                        data[mask] = [0, 0, 0, 0]
                    img = Image.fromarray(data)
                else:
                    # Convert to RGBA but keep solid background
                    img = img.convert('RGBA')
            
            # Handle special words positioning (simplified implementation)
            if special_config:
                if self.debug:
                    print(f"EricsWordCloudNode: Processing {len(special_config)} special words")
                # This would require more complex implementation to position words specifically
                # For now, we'll note that special words were configured
            
            # Overlay word cloud on background image if provided
            if background_img is not None:
                img = self.overlay_wordcloud_on_image(img, background_img)
                if self.debug:
                    print(f"EricsWordCloudNode: Overlaid word cloud on background image")
            
            # Convert PIL image to tensor
            img_np = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np)[None, ...]
            img_tensor = self.ensure_compatible_format(img_tensor)
            
            # Debug output
            if self.debug:
                print(f"EricsWordCloudNode: Generated word cloud with shape: {img_tensor.shape}")
                print(f"EricsWordCloudNode: Final dimensions used: {actual_width}x{actual_height}")
                if wordcloud and hasattr(wordcloud, 'words_'):
                    print(f"EricsWordCloudNode: Words processed: {len(wordcloud.words_)}")
                print(f"EricsWordCloudNode: Color mode: {color_mode}, Font mode: {font_mode}")
                print(f"EricsWordCloudNode: Background: {background_mode}")
                print(f"EricsWordCloudNode: Font used: {font_path}")
                print(f"EricsWordCloudNode: Horizontal preference: {prefer_horizontal_ratio}")
                print(f"EricsWordCloudNode: Collocations enabled: {collocations}, threshold: {collocation_threshold}")
                if mask_array is not None:
                    print(f"EricsWordCloudNode: Mask placement: {mask_placement}")
                if background_img is not None:
                    print(f"EricsWordCloudNode: Background image used: {background_img.size}")
                
                # Save debug image
                try:
                    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_path = os.path.join(debug_dir, f"wordcloud_debug_{int(time.time())}.png")
                    img.save(debug_path)
                    print(f"EricsWordCloudNode: Saved debug image to {debug_path}")
                except Exception as e:
                    print(f"EricsWordCloudNode: Failed to save debug image: {str(e)}")
            
            # Create font preview for the second output
            try:
                font_preview_img, current_page, total_pages = self.generate_font_preview(
                    preview_text, width, height
                )
                
                font_preview_np = np.array(font_preview_img).astype(np.float32) / 255.0
                # Add alpha channel for RGBA format
                if len(font_preview_np.shape) == 3 and font_preview_np.shape[2] == 3:
                    alpha = np.ones((*font_preview_np.shape[:2], 1), dtype=np.float32)
                    font_preview_np = np.concatenate([font_preview_np, alpha], axis=2)
                
                font_preview_tensor = torch.from_numpy(font_preview_np)[None, ...]
                font_preview_tensor = self.ensure_compatible_format(font_preview_tensor)
                
                if self.debug:
                    print(f"EricsWordCloudNode: Generated font preview for second output page {current_page}/{total_pages}")
                    print(f"EricsWordCloudNode: Font preview dimensions: {font_preview_img.size}")
                
            except Exception as e:
                print(f"EricsWordCloudNode: Error generating font preview: {str(e)}")
                # Use the wordcloud as fallback for preview output
                font_preview_tensor = img_tensor
            
            # Create color preview for the third output
            try:
                color_preview_img = self.generate_color_preview(
                    color_mode, cultural_color_set, emotional_color_set, color_harmony_set, custom_color_range,
                    single_color_hex, single_color_name
                )
                
                color_preview_np = np.array(color_preview_img).astype(np.float32) / 255.0
                # Add alpha channel for RGBA format
                if len(color_preview_np.shape) == 3 and color_preview_np.shape[2] == 3:
                    alpha = np.ones((*color_preview_np.shape[:2], 1), dtype=np.float32)
                    color_preview_np = np.concatenate([color_preview_np, alpha], axis=2)
                
                color_preview_tensor = torch.from_numpy(color_preview_np)[None, ...]
                color_preview_tensor = self.ensure_compatible_format(color_preview_tensor)
                
                if self.debug:
                    print(f"EricsWordCloudNode: Generated color preview for third output")
                    print(f"EricsWordCloudNode: Color preview dimensions: {color_preview_img.size}")
                
            except Exception as e:
                print(f"EricsWordCloudNode: Error generating color preview: {str(e)}")
                # Use a minimal fallback color preview
                fallback_img = Image.new('RGB', (200, 100), (128, 128, 128))
                draw = ImageDraw.Draw(fallback_img)
                draw.text((100, 50), "Color Preview Error", fill=(255, 255, 255), anchor="mm")
                
                fallback_np = np.array(fallback_img).astype(np.float32) / 255.0
                alpha = np.ones((*fallback_np.shape[:2], 1), dtype=np.float32)
                fallback_np = np.concatenate([fallback_np, alpha], axis=2)
                color_preview_tensor = torch.from_numpy(fallback_np)[None, ...]
            
            return (img_tensor, font_preview_tensor, color_preview_tensor, svg_content, used_words_string)
            
        except Exception as e:
            print(f"EricsWordCloudNode: Error generating word cloud: {str(e)}")
            
            # Determine dimensions for error image
            error_width, error_height = self.get_optimal_dimensions(input_image, mask_image, width, height)
            
            # Create error image
            error_img = Image.new('RGBA', (error_width, error_height), (255, 0, 0, 128))
            draw = ImageDraw.Draw(error_img)
            error_text = f"Error generating word cloud:\n{str(e)}"
            draw.text((error_width//2, error_height//2), error_text, fill=(255, 255, 255), anchor="mm")
            
            error_np = np.array(error_img).astype(np.float32) / 255.0
            error_tensor = torch.from_numpy(error_np)[None, ...]
            error_tensor = self.ensure_compatible_format(error_tensor)
            
            return (error_tensor, error_tensor, error_tensor, "", "")

# Registration of the node for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EricsWordCloudNode": EricsWordCloudNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricsWordCloudNode": "Erics Word Cloud Generator (Advanced Image/Mask Support)"
}

# Print initialization info
if __name__ != "__main__":
    print(f"EricsWordCloud Node: Library available = {WORDCLOUD_AVAILABLE}")
    print(f"EricsWordCloud Node: Cultural data available = {CULTURAL_DATA_AVAILABLE}")
    print(f"EricsWordCloud Node: Color database size = {len(COLOR_NAMES)}")
    print(f"EricsWordCloud Node: Cultural color sets = {len(CULTURAL_COLOR_SETS)}")
    print(f"EricsWordCloud Node: Emotional color sets = {len(EMOTIONAL_COLOR_SETS)}")
    
    # Debug: Show first few color names for troubleshooting
    color_samples = list(COLOR_NAMES.items())[:10]
    print(f"EricsWordCloud Node: Sample colors from database:")
    for name, rgb in color_samples:
        print(f"  '{name}' -> {rgb}")
    
    if CULTURAL_DATA_AVAILABLE:
        print(f"EricsWordCloud Node: Cultural combinations loaded = {len(color_combinations)}")
        print(f"EricsWordCloud Node: Color significance data loaded = {len(color_significance)}")
    
    # List some available cultural sets
    if CULTURAL_COLOR_SETS:
        available_sets = list(CULTURAL_COLOR_SETS.keys())[:10]  # First 10
        print(f"EricsWordCloud Node: Sample cultural sets: {', '.join(available_sets)}")
        
    print("EricsWordCloud Node: Successfully initialized with enhanced color support!")
