"""
Qwen Image Aspect Ratio Helper Node v1.0

Provides optimized width/height pairs for Qwen-Image (text-to-image) and 
Qwen-Image-Edit (image editing) based on aspect ratio and megapixel size selection.

Key Requirements:
- Qwen-Image (T2I): Dimensions divisible by 16
- Qwen-Image-Edit: Dimensions divisible by 112 (Qwen2.5-VL patch size 14 × VAE compression 8)

Aspect ratios span from ultra-tall portrait (9:21) to ultra-wide landscape (21:9).

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
License: Dual License (Non-Commercial and Commercial Use)
Copyright (c) 2025-2026 Eric Hiss. All rights reserved.

Dual License:
1. Non-Commercial Use: This software is licensed under the terms of the
   Creative Commons Attribution-NonCommercial 4.0 International License.
   To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/4.0/
   
2. Commercial Use: For commercial use, a separate license is required.
   Please contact Eric Hiss at [eric@historic.camera, eric@rollei.us] for licensing options.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT.

Version: 1.0
Date: 2026-01-05
"""

# Console output goes through one switch (see aaa_meta/console.py): problems are always shown,
# everything else only with the node's debug option on or AAA_META_VERBOSE=1.
try:
    from ..aaa_meta.console import quiet_print as print, note_error as _note_error
except Exception:                                    # used outside the pack
    def _note_error(error, where=""):
        pass

import math
from typing import Tuple, Dict, List, Optional


class QwenAspectRatioHelper:
    """
    Aspect Ratio Helper for Qwen-Image and Qwen-Image-Edit models.
    
    Provides optimized width/height pairs based on:
    - Model type (T2I uses divisible by 16, Edit uses divisible by 112)
    - Aspect ratio selection from ultra-portrait to ultra-landscape
    - Megapixel size selection (0.5MP to 2.5MP)
    
    Displays selected W×H directly in the node UI.
    """
    
    # Aspect ratios from very tall portrait to very wide landscape
    # Format: "display_name": (width_ratio, height_ratio)
    ASPECT_RATIOS = {
        "9:21 Ultra-Tall Portrait": (9, 21),
        "9:16 Tall Portrait": (9, 16),
        "2:3 Portrait": (2, 3),
        "3:4 Portrait": (3, 4),
        "4:5 Portrait": (4, 5),
        "1:1 Square": (1, 1),
        "5:4 Landscape": (5, 4),
        "4:3 Landscape": (4, 3),
        "3:2 Landscape": (3, 2),
        "16:9 Wide Landscape": (16, 9),
        "21:9 Ultra-Wide Landscape": (21, 9),
    }
    
    # Megapixel targets - fine-grained control
    MP_SIZES = {
        "0.4 MP (~400K pixels)": 400_000,
        "0.5 MP (~500K pixels)": 500_000,
        "0.6 MP (~600K pixels)": 600_000,
        "0.8 MP (~800K pixels)": 800_000,
        "1.0 MP (~1M pixels)": 1_000_000,
        "1.2 MP (~1.2M pixels)": 1_200_000,
        "1.4 MP (~1.4M pixels)": 1_400_000,
        "1.6 MP (~1.6M pixels)": 1_600_000,
        "1.8 MP (~1.8M pixels)": 1_800_000,
        "2.0 MP (~2M pixels)": 2_000_000,
        "3.0 MP (~3M pixels)": 3_000_000,
        "4.0 MP (~4M pixels)": 4_000_000,
    }
    
    # Model divisibility requirements
    MODEL_DIVISIBILITY = {
        "Qwen-Image (T2I - div 16)": 16,
        "Qwen-Image-Edit (div 112)": 112,
    }
    
    # Pre-computed reference sizes from official Qwen documentation
    # These are the officially documented sizes for Qwen-Image
    QWEN_OFFICIAL_SIZES = {
        "1:1": (1328, 1328),
        "16:9": (1664, 928),
        "9:16": (928, 1664),
        "4:3": (1472, 1104),
        "3:4": (1104, 1472),
        "3:2": (1584, 1056),
        "2:3": (1056, 1584),
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (list(cls.MODEL_DIVISIBILITY.keys()), {
                    "default": "Qwen-Image-Edit (div 112)"
                }),
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {
                    "default": "1:1 Square"
                }),
                "megapixels": (list(cls.MP_SIZES.keys()), {
                    "default": "1.0 MP (~1M pixels)"
                }),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            },
        }
    
    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "info_text")
    
    FUNCTION = "calculate_dimensions"
    CATEGORY = "loaders/multi-lora/qwen"
    
    # Enable dynamic display in the node
    OUTPUT_NODE = False
    
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True
    
    def calculate_dimensions(
        self, 
        model_type: str, 
        aspect_ratio: str, 
        megapixels: str,
        reference_image=None
    ) -> Tuple[int, int, str]:
        """
        Calculate optimized dimensions for Qwen models.
        
        Args:
            model_type: Which Qwen model to optimize for
            aspect_ratio: Selected aspect ratio
            megapixels: Target megapixel size
            reference_image: Optional reference image to derive aspect ratio from
            
        Returns:
            Tuple of (width, height, info_text)
        """
        divisibility = self.MODEL_DIVISIBILITY[model_type]
        target_pixels = self.MP_SIZES[megapixels]
        
        # Determine aspect ratio
        if reference_image is not None:
            # Use reference image aspect ratio
            if len(reference_image.shape) == 4:
                _, h, w, _ = reference_image.shape
            elif len(reference_image.shape) == 3:
                h, w, _ = reference_image.shape
            else:
                h, w = 1, 1
            
            width_ratio = w
            height_ratio = h
            ratio_name = f"From Image ({w}×{h})"
            ar_decimal = w / h
        else:
            # Use selected aspect ratio
            width_ratio, height_ratio = self.ASPECT_RATIOS[aspect_ratio]
            ratio_name = aspect_ratio
            ar_decimal = width_ratio / height_ratio
        
        # Calculate optimal dimensions
        width, height = self._calculate_optimal_size(
            ar_decimal, target_pixels, divisibility
        )
        
        actual_pixels = width * height
        actual_mp = actual_pixels / 1_000_000
        
        # Generate size table for help info
        size_table = self._generate_size_table(divisibility)
        
        # Create info text with selected dimensions and full table
        info_text = self._format_info_text(
            model_type=model_type,
            ratio_name=ratio_name,
            ar_decimal=ar_decimal,
            megapixels=megapixels,
            width=width,
            height=height,
            actual_mp=actual_mp,
            divisibility=divisibility,
            size_table=size_table
        )
        
        # Console output
        print(f"[Qwen AR Helper] {model_type}")
        print(f"[Qwen AR Helper] Ratio: {ratio_name} ({ar_decimal:.3f})")
        print(f"[Qwen AR Helper] Target: {megapixels}")
        print(f"[Qwen AR Helper] Output: {width}×{height} ({actual_mp:.2f} MP)")
        print(f"[Qwen AR Helper] Divisibility: {divisibility}")
        
        return (width, height, info_text)
    
    def _calculate_optimal_size(
        self, 
        aspect_ratio: float, 
        target_pixels: int, 
        divisibility: int
    ) -> Tuple[int, int]:
        """
        Calculate optimal width and height for given constraints.
        
        Args:
            aspect_ratio: Width/height ratio
            target_pixels: Target total pixel count
            divisibility: Required divisibility (16 or 112)
            
        Returns:
            Tuple of (width, height)
        """
        # Calculate base dimensions from aspect ratio and target pixels
        # pixels = width × height
        # aspect_ratio = width / height
        # width = aspect_ratio × height
        # pixels = aspect_ratio × height²
        # height = sqrt(pixels / aspect_ratio)
        
        height = math.sqrt(target_pixels / aspect_ratio)
        width = aspect_ratio * height
        
        # Round to nearest divisibility value
        width = round(width / divisibility) * divisibility
        height = round(height / divisibility) * divisibility
        
        # Ensure minimum dimensions
        min_dim = divisibility * 2  # At least 2 blocks
        width = max(min_dim, width)
        height = max(min_dim, height)
        
        # Apply reasonable maximums to prevent memory issues
        max_dim = 4096
        if width > max_dim:
            width = (max_dim // divisibility) * divisibility
        if height > max_dim:
            height = (max_dim // divisibility) * divisibility
        
        return (int(width), int(height))
    
    def _generate_size_table(self, divisibility: int) -> str:
        """
        Generate a complete size table for all ratios and MP sizes.
        
        Args:
            divisibility: The divisibility requirement (16 or 112)
            
        Returns:
            Formatted table string
        """
        lines = []
        
        # Split into two tables for readability (6 sizes each)
        mp_items = list(self.MP_SIZES.items())
        mp_group1 = mp_items[:6]  # 0.4 to 1.0
        mp_group2 = mp_items[6:]  # 1.2 to 4.0
        
        # Table 1: Small to medium sizes
        header1 = f"{'Aspect Ratio':<24}"
        for mp_name, _ in mp_group1:
            short_name = mp_name.split()[0]  # Extract "0.4" from "0.4 MP (~400K pixels)"
            header1 += f" {short_name:>10}"
        lines.append(header1)
        lines.append("─" * 90)
        
        for ratio_name, (w_ratio, h_ratio) in self.ASPECT_RATIOS.items():
            ar_decimal = w_ratio / h_ratio
            row = f"{ratio_name[:23]:<24}"
            for mp_name, target_pixels in mp_group1:
                w, h = self._calculate_optimal_size(ar_decimal, target_pixels, divisibility)
                row += f" {w}×{h:>10}"[:11].rjust(11)
            lines.append(row)
        
        lines.append("")
        
        # Table 2: Medium to large sizes
        header2 = f"{'Aspect Ratio':<24}"
        for mp_name, _ in mp_group2:
            short_name = mp_name.split()[0]
            header2 += f" {short_name:>10}"
        lines.append(header2)
        lines.append("─" * 90)
        
        for ratio_name, (w_ratio, h_ratio) in self.ASPECT_RATIOS.items():
            ar_decimal = w_ratio / h_ratio
            row = f"{ratio_name[:23]:<24}"
            for mp_name, target_pixels in mp_group2:
                w, h = self._calculate_optimal_size(ar_decimal, target_pixels, divisibility)
                row += f" {w}×{h:>10}"[:11].rjust(11)
            lines.append(row)
        
        return "\n".join(lines)
    
    def _format_info_text(
        self,
        model_type: str,
        ratio_name: str,
        ar_decimal: float,
        megapixels: str,
        width: int,
        height: int,
        actual_mp: float,
        divisibility: int,
        size_table: str
    ) -> str:
        """Format the info text output with all details."""
        
        div_explanation = ""
        if divisibility == 112:
            div_explanation = "(Qwen2.5-VL patch size 14 × VAE compression 8 = 112)"
        elif divisibility == 16:
            div_explanation = "(Standard diffusion model requirement)"
        
        return (
            f"Qwen Aspect Ratio Helper\n"
            f"════════════════════════════════════════\n"
            f"\n"
            f"Model: {model_type}\n"
            f"Divisibility: {divisibility} {div_explanation}\n"
            f"\n"
            f"Selected Settings:\n"
            f"  Aspect Ratio: {ratio_name}\n"
            f"  Decimal Ratio: {ar_decimal:.4f}\n"
            f"  Target Size: {megapixels}\n"
            f"\n"
            f"════════════════════════════════════════\n"
            f"  ✓ OUTPUT: {width} × {height}\n"
            f"  ✓ Actual: {actual_mp:.2f} MP ({width * height:,} pixels)\n"
            f"════════════════════════════════════════\n"
            f"\n"
            f"Complete Size Reference Table (div by {divisibility}):\n"
            f"────────────────────────────────────────────────────────────────────────────────────────\n"
            f"{size_table}\n"
            f"────────────────────────────────────────────────────────────────────────────────────────\n"
            f"\n"
            f"Notes:\n"
            f"• Qwen-Image (T2I): Use divisibility of 16\n"
            f"• Qwen-Image-Edit: Use divisibility of 112 for best results\n"
            f"  (Qwen2.5-VL uses 14×14 patches, VAE uses 8× compression → 14×8=112)\n"
            f"• Official Qwen-Image sizes: 1:1=1328×1328, 16:9=1664×928, 4:3=1472×1104\n"
        )


class QwenAspectRatioHelperAdvanced:
    """
    Advanced version with custom ratio input and more control.
    """
    
    # Same base ratios as the standard helper
    ASPECT_RATIOS = QwenAspectRatioHelper.ASPECT_RATIOS.copy()
    ASPECT_RATIOS["Custom (use inputs below)"] = (1, 1)  # Placeholder
    
    MP_SIZES = QwenAspectRatioHelper.MP_SIZES.copy()
    MODEL_DIVISIBILITY = QwenAspectRatioHelper.MODEL_DIVISIBILITY.copy()
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (list(cls.MODEL_DIVISIBILITY.keys()), {
                    "default": "Qwen-Image-Edit (div 112)"
                }),
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {
                    "default": "1:1 Square"
                }),
                "megapixels": (list(cls.MP_SIZES.keys()), {
                    "default": "1.0 MP (~1M pixels)"
                }),
            },
            "optional": {
                "custom_width_ratio": ("INT", {
                    "default": 16,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "Custom width ratio (e.g., 16 for 16:9)"
                }),
                "custom_height_ratio": ("INT", {
                    "default": 9,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "Custom height ratio (e.g., 9 for 16:9)"
                }),
                "custom_divisibility": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 256,
                    "step": 1,
                    "tooltip": "Override divisibility (0 = use model default)"
                }),
                "reference_image": ("IMAGE",),
            },
        }
    
    RETURN_TYPES = ("INT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("width", "height", "aspect_ratio_decimal", "info_text")
    
    FUNCTION = "calculate_dimensions"
    CATEGORY = "loaders/multi-lora/qwen"
    
    def calculate_dimensions(
        self,
        model_type: str,
        aspect_ratio: str,
        megapixels: str,
        custom_width_ratio: int = 16,
        custom_height_ratio: int = 9,
        custom_divisibility: int = 0,
        reference_image=None
    ) -> Tuple[int, int, float, str]:
        """
        Calculate optimized dimensions with advanced options.
        """
        # Determine divisibility
        if custom_divisibility > 0:
            divisibility = custom_divisibility
        else:
            divisibility = self.MODEL_DIVISIBILITY[model_type]
        
        target_pixels = self.MP_SIZES[megapixels]
        
        # Determine aspect ratio
        if reference_image is not None:
            # Use reference image aspect ratio
            if len(reference_image.shape) == 4:
                _, h, w, _ = reference_image.shape
            elif len(reference_image.shape) == 3:
                h, w, _ = reference_image.shape
            else:
                h, w = 1, 1
            
            width_ratio = w
            height_ratio = h
            ratio_name = f"From Image ({w}×{h})"
        elif aspect_ratio == "Custom (use inputs below)":
            width_ratio = custom_width_ratio
            height_ratio = custom_height_ratio
            ratio_name = f"Custom {custom_width_ratio}:{custom_height_ratio}"
        else:
            width_ratio, height_ratio = self.ASPECT_RATIOS[aspect_ratio]
            ratio_name = aspect_ratio
        
        ar_decimal = width_ratio / height_ratio
        
        # Calculate optimal dimensions
        width, height = self._calculate_optimal_size(
            ar_decimal, target_pixels, divisibility
        )
        
        actual_pixels = width * height
        actual_mp = actual_pixels / 1_000_000
        
        # Generate info text
        info_text = (
            f"Qwen AR Helper (Advanced)\n"
            f"══════════════════════════\n"
            f"Model: {model_type}\n"
            f"Divisibility: {divisibility}\n"
            f"Ratio: {ratio_name} ({ar_decimal:.4f})\n"
            f"Target: {megapixels}\n"
            f"\n"
            f"✓ OUTPUT: {width} × {height}\n"
            f"✓ Actual: {actual_mp:.2f} MP\n"
        )
        
        return (width, height, ar_decimal, info_text)
    
    def _calculate_optimal_size(
        self,
        aspect_ratio: float,
        target_pixels: int,
        divisibility: int
    ) -> Tuple[int, int]:
        """Calculate optimal width and height."""
        height = math.sqrt(target_pixels / aspect_ratio)
        width = aspect_ratio * height
        
        width = round(width / divisibility) * divisibility
        height = round(height / divisibility) * divisibility
        
        min_dim = divisibility * 2
        width = max(min_dim, width)
        height = max(min_dim, height)
        
        max_dim = 4096
        if width > max_dim:
            width = (max_dim // divisibility) * divisibility
        if height > max_dim:
            height = (max_dim // divisibility) * divisibility
        
        return (int(width), int(height))


# ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "QwenAspectRatioHelper": QwenAspectRatioHelper,
    "QwenAspectRatioHelperAdvanced": QwenAspectRatioHelperAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QwenAspectRatioHelper": "Qwen Aspect Ratio Helper",
    "QwenAspectRatioHelperAdvanced": "Qwen Aspect Ratio Helper (Advanced)",
}
