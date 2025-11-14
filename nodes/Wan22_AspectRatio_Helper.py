"""
Wan 2.2 Aspect Ratio Helper Node v2.2

Analyzes input image aspect ratio and dynamically generates optimized width/height pairs
for Wan 2.2 video generation at multiple scales (tiny, small, medium, large, extra-large, gigantic).

Based on official Wan 2.2 specifications:
- Divisibility by 8 pixels
- Ratio range: 1:3 to 3:1 (0.333 to 3.0)
- Smart hybrid: uses documented training sizes when available, calculates optimal otherwise

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
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

v2.2 Updates:
- Added "tiny" preset (~200K pixels) for ultra-fast previews
- Added "gigantic" preset (~2M pixels) for maximum quality renders

v2.1 UX Improvement:
- Simplified to 3 outputs (width, height, info_text)
- Change size preset without rewiring workflow
- Enhanced info_text with formatted display

Author: Eric
Version: 2.2
Date: 2025-10-23
"""

import torch
import numpy as np
from typing import Tuple, Dict, List
import math


class Wan22AspectRatioHelper:
    """
    Analyzes input image aspect ratio and provides optimized resolution suggestions
    for Wan 2.2 video generation across 6 size scales.
    
    v2.0 Features:
    - Dynamic size calculation matching exact input aspect ratio
    - Supports any ratio from 1:3 to 3:1 (ultra-portrait to ultra-wide)
    - All resolutions divisible by 8 (official Wan 2.2 requirement)
    - Smart hybrid algorithm: uses known Wan 2.2 training sizes when close, calculates optimal otherwise
    - Better ratio detection and labeling
    - 6 size presets: tiny (~200K pixels), small (~400K), medium (~650K), large (~900K), extra-large (~1.4M), gigantic (~2M)
    """
    
    # Wan 2.2 requirements:
    # - Divisible by 8
    # - Ratio range: 1:3 to 3:1 (0.333 to 3.0)
    # - Typical ranges: width 320-1280, height 320-1280
    
    # Target pixel counts for each size preset (approximate total pixels)
    TARGET_PIXELS = {
        "tiny": 200_000,       # ~200K pixels (e.g., 368x544 = 200K)
        "small": 400_000,      # ~400K pixels (e.g., 520x768 = 399K)
        "medium": 650_000,     # ~650K pixels (e.g., 720x912 = 657K)
        "large": 900_000,      # ~900K pixels (e.g., 848x1088 = 923K)
        "extra-large": 1_400_000,  # ~1.4M pixels (e.g., 1056x1344 = 1.42M)
        "gigantic": 2_000_000  # ~2M pixels (e.g., 1264x1600 = 2.02M)
    }
    
    # Wan 2.2 documented training sizes (used as preferred options when close)
    WAN22_KNOWN_SIZES = [
        # 1:1 Square
        (720, 720), (848, 848), (1008, 1008), (1264, 1264),
        # 3:4 Portrait
        (416, 544), (560, 720), (720, 912), (848, 1088),
        # 4:3 Landscape
        (544, 416), (720, 560), (912, 720), (1088, 848),
        # 2:3 Portrait
        (384, 576), (528, 768), (656, 960), (784, 1136),
        # 3:2 Landscape
        (576, 384), (768, 528), (960, 656), (1136, 784),
        # 9:16 Vertical
        (368, 624), (480, 848), (608, 1072), (720, 1264),
        # 16:9 Horizontal
        (624, 368), (848, 480), (1072, 608), (1264, 720),
    ]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),  # ComfyUI image tensor
                "size_preset": (["tiny", "small", "medium", "large", "extra-large", "gigantic"], {
                    "default": "medium"
                }),
            },
        }
    
    RETURN_TYPES = (
        "INT",      # width (based on dropdown selection)
        "INT",      # height (based on dropdown selection)
        "STRING",   # info_text (shows all 6 size options)
    )
    
    RETURN_NAMES = (
        "width",
        "height",
        "info_text",
    )
    
    FUNCTION = "calculate_wan22_sizes"
    CATEGORY = "loaders/multi-lora/wan"
    
    def calculate_wan22_sizes(self, image: torch.Tensor, size_preset: str):
        """
        Calculate optimized Wan 2.2 resolutions based on input image aspect ratio.
        
        Args:
            image: ComfyUI IMAGE tensor [B, H, W, C]
            size_preset: One of "tiny", "small", "medium", "large", "extra-large", "gigantic"
            
        Returns:
            Tuple of width/height pairs for all 6 scales, plus selected scale and info text
        """
        # Get input image dimensions from tensor
        # ComfyUI images are [batch, height, width, channels]
        if len(image.shape) == 4:
            _, height, width, _ = image.shape
        elif len(image.shape) == 3:
            height, width, _ = image.shape
        else:
            raise ValueError(f"Unexpected image tensor shape: {image.shape}")
        
        # Calculate aspect ratio
        aspect_ratio = width / height
        
        # Clamp ratio to Wan 2.2 supported range (1:3 to 3:1)
        if aspect_ratio < 0.333:
            print(f"[Wan 2.2 AR Helper] WARNING: Input ratio {aspect_ratio:.3f} too narrow, clamping to 1:3")
            aspect_ratio = 0.333
        elif aspect_ratio > 3.0:
            print(f"[Wan 2.2 AR Helper] WARNING: Input ratio {aspect_ratio:.3f} too wide, clamping to 3:1")
            aspect_ratio = 3.0
        
        # Console logging for debugging
        print(f"[Wan 2.2 AR Helper] Input image: {width}x{height} (ratio: {aspect_ratio:.3f})")
        
        # Generate 4 optimized sizes matching the input aspect ratio
        sizes = self._generate_optimal_sizes(aspect_ratio)
        
        # Extract the 6 size scales
        width_tiny, height_tiny = sizes[0]
        width_small, height_small = sizes[1]
        width_medium, height_medium = sizes[2]
        width_large, height_large = sizes[3]
        width_xlarge, height_xlarge = sizes[4]
        width_gigantic, height_gigantic = sizes[5]
        
        print(f"[Wan 2.2 AR Helper] Generated sizes:")
        print(f"  Tiny: {width_tiny}x{height_tiny}")
        print(f"  Small: {width_small}x{height_small}")
        print(f"  Medium: {width_medium}x{height_medium}")
        print(f"  Large: {width_large}x{height_large}")
        print(f"  Extra-Large: {width_xlarge}x{height_xlarge}")
        print(f"  Gigantic: {width_gigantic}x{height_gigantic}")
        
        # Get selected size based on dropdown
        preset_index = {
            "tiny": 0,
            "small": 1,
            "medium": 2,
            "large": 3,
            "extra-large": 4,
            "gigantic": 5
        }[size_preset]
        
        selected_width, selected_height = sizes[preset_index]
        
        print(f"[Wan 2.2 AR Helper] Size preset '{size_preset}' selected: {selected_width}x{selected_height}")
        
        # Create descriptive text output showing all options
        ratio_name = self._get_ratio_name(aspect_ratio)
        
        info_text = (
            f"Wan 2.2 Aspect Ratio Helper\n"
            f"═══════════════════════════\n"
            f"Input: {width}x{height}\n"
            f"Detected Ratio: {ratio_name} ({aspect_ratio:.3f})\n"
            f"\n"
            f"Available Sizes:\n"
            f"  Tiny:        {width_tiny:4d}×{height_tiny:<4d} ({width_tiny*height_tiny:>9,} pixels)\n"
            f"  Small:       {width_small:4d}×{height_small:<4d} ({width_small*height_small:>9,} pixels)\n"
            f"  Medium:      {width_medium:4d}×{height_medium:<4d} ({width_medium*height_medium:>9,} pixels)\n"
            f"  Large:       {width_large:4d}×{height_large:<4d} ({width_large*height_large:>9,} pixels)\n"
            f"  Extra-Large: {width_xlarge:4d}×{height_xlarge:<4d} ({width_xlarge*height_xlarge:>9,} pixels)\n"
            f"  Gigantic:    {width_gigantic:4d}×{height_gigantic:<4d} ({width_gigantic*height_gigantic:>9,} pixels)\n"
            f"\n"
            f"✓ Selected ({size_preset}): {selected_width}×{selected_height}\n"
            f"  All dimensions divisible by 8"
        )
        
        return (
            selected_width,
            selected_height,
            info_text
        )
    
    def _generate_optimal_sizes(self, aspect_ratio: float) -> List[Tuple[int, int]]:
        """
        Generate 6 optimized size pairs matching the aspect ratio.
        Tries to use Wan 2.2 known training sizes when close, otherwise calculates optimal sizes.
        
        Args:
            aspect_ratio: Target aspect ratio (width/height)
            
        Returns:
            List of 6 (width, height) tuples for tiny, small, medium, large, extra-large, gigantic
        """
        sizes = []
        
        for preset in ["small", "medium", "large", "extra-large"]:
            target_pixels = self.TARGET_PIXELS[preset]
            
            # First, check if any known Wan 2.2 sizes match well
            best_known = None
            best_known_diff = float('inf')
            
            for w, h in self.WAN22_KNOWN_SIZES:
                size_ratio = w / h
                pixels = w * h
                
                # Check if ratio matches (within 5%) and pixel count is close (within 30%)
                ratio_diff = abs(size_ratio - aspect_ratio)
                pixel_diff_pct = abs(pixels - target_pixels) / target_pixels
                
                if ratio_diff < 0.05 and pixel_diff_pct < 0.3:
                    combined_diff = ratio_diff + pixel_diff_pct * 0.1
                    if combined_diff < best_known_diff:
                        best_known = (w, h)
                        best_known_diff = combined_diff
            
            # Use known size if found, otherwise calculate
            if best_known:
                sizes.append(best_known)
            else:
                # Calculate optimal size based on target pixels and aspect ratio
                # pixels = width * height
                # aspect_ratio = width / height
                # width = aspect_ratio * height
                # pixels = aspect_ratio * height^2
                # height = sqrt(pixels / aspect_ratio)
                
                height = int(math.sqrt(target_pixels / aspect_ratio))
                width = int(aspect_ratio * height)
                
                # Round to nearest 8
                width = ((width + 4) // 8) * 8
                height = ((height + 4) // 8) * 8
                
                # Ensure within valid range (320-1280)
                width = max(320, min(1280, width))
                height = max(320, min(1280, height))
                
                # Re-verify aspect ratio and adjust if needed
                actual_ratio = width / height
                if abs(actual_ratio - aspect_ratio) > 0.1:
                    # Adjust width to match aspect ratio better
                    width = int(aspect_ratio * height)
                    width = ((width + 4) // 8) * 8
                    width = max(320, min(1280, width))
                
                sizes.append((width, height))
        
        return sizes
    
    def _get_ratio_name(self, aspect_ratio: float) -> str:
        """
        Get descriptive name for aspect ratio.
        
        Args:
            aspect_ratio: Aspect ratio value (width/height)
            
        Returns:
            Descriptive string like "3:4 Portrait" or "Custom 1.25:1"
        """
        # Known ratios
        known_ratios = {
            1.0: "1:1 Square",
            0.75: "3:4 Portrait",
            1.333: "4:3 Landscape",
            0.667: "2:3 Portrait",
            1.5: "3:2 Landscape",
            0.5625: "9:16 Vertical",
            1.778: "16:9 Widescreen",
        }
        
        # Find closest known ratio (within 3%)
        for ratio_val, ratio_name in known_ratios.items():
            if abs(aspect_ratio - ratio_val) < 0.03:
                return ratio_name
        
        # Custom ratio
        if aspect_ratio < 1.0:
            # Portrait - express as X:Y where Y > X
            simplified = self._simplify_ratio(aspect_ratio)
            return f"{simplified} Portrait"
        elif aspect_ratio > 1.0:
            # Landscape - express as X:Y where X > Y
            simplified = self._simplify_ratio(aspect_ratio)
            return f"{simplified} Landscape"
        else:
            return "1:1 Square"
    
    def _simplify_ratio(self, ratio: float) -> str:
        """
        Convert decimal ratio to simplified fraction string.
        
        Args:
            ratio: Aspect ratio (width/height)
            
        Returns:
            String like "16:10" or "1.25:1"
        """
        # Try common fractions
        for num in range(1, 20):
            for denom in range(1, 20):
                if abs(ratio - (num / denom)) < 0.02:
                    return f"{num}:{denom}"
        
        # Fall back to decimal
        if ratio < 1.0:
            return f"1:{1/ratio:.2f}"
        else:
            return f"{ratio:.2f}:1"


# ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "Wan22AspectRatioHelper": Wan22AspectRatioHelper
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22AspectRatioHelper": "Wan 2.2 Aspect Ratio Helper"
}
