"""
Wan 2.2 Size Preset Node v1.1

Generates optimized width/height pairs for Wan 2.2 video generation without requiring
an input image. User selects aspect ratio and size preset from dropdown menus.

Based on official Wan 2.2 specifications:
- Divisibility by 8 pixels
- Ratio range: 1:3 to 3:1 (0.333 to 3.0)
- Smart hybrid: uses documented training sizes when available, calculates optimal otherwise

Companion to Wan22_AspectRatio_Helper - same logic, no image input required.

v1.1 Updates:
- Added "tiny" preset (~200K pixels) for ultra-fast previews
- Added "gigantic" preset (~2M pixels) for maximum quality renders

Author: Eric
Version: 1.1
Date: 2025-10-23
"""

import math

class Wan22_Size_Preset:
    """
    Generates Wan 2.2 optimized dimensions based on user-selected aspect ratio and size preset.
    No input image required - perfect for starting workflows from scratch.
    """
    
    # Target pixel counts for each size preset
    TARGET_PIXELS = {
        "tiny": 200_000,       # ~200K pixels
        "small": 400_000,      # ~400K pixels
        "medium": 650_000,     # ~650K pixels
        "large": 900_000,      # ~900K pixels
        "extra-large": 1_400_000,  # ~1.4M pixels
        "gigantic": 2_000_000  # ~2M pixels
    }
    
    # Documented Wan 2.2 training sizes (width, height)
    # These are preferred when they match the selected ratio
    WAN22_KNOWN_SIZES = [
        # Square (1:1)
        (720, 720),
        # Portrait ratios
        (560, 720), (560, 896), (560, 1088), (560, 1280),
        (688, 880), (688, 1072),
        (848, 1088),
        # Landscape ratios
        (720, 560), (896, 560), (1088, 560), (1280, 560),
        (880, 688), (1072, 688),
        (1088, 848),
        # Wide landscape
        (1280, 720), (1280, 800),
        # Ultra-wide
        (1280, 544), (1600, 640),
        # Additional documented sizes
        (1088, 672), (672, 1088),
        (1088, 704), (704, 1088),
        (1072, 672), (672, 1072),
        (1280, 768), (768, 1280)
    ]
    
    # Predefined aspect ratios with descriptive names
    ASPECT_RATIOS = {
        # Portrait
        "1:3 Ultra-Tall Portrait": 1/3,
        "9:21 Tall Portrait": 9/21,
        "9:19.5 Tall Portrait": 9/19.5,
        "9:16 Tall Portrait": 9/16,
        "3:4 Portrait": 3/4,
        "5:6 Portrait": 5/6,
        
        # Square
        "1:1 Square": 1.0,
        
        # Landscape
        "6:5 Landscape": 6/5,
        "4:3 Standard": 4/3,
        "16:10 Widescreen": 16/10,
        "16:9 Widescreen": 16/9,
        "19.5:9 Widescreen": 19.5/9,
        "21:9 Ultra-Wide": 21/9,
        "3:1 Ultra-Wide Landscape": 3/1,
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {
                    "default": "16:9 Widescreen"
                }),
                "size_preset": (["tiny", "small", "medium", "large", "extra-large", "gigantic"], {
                    "default": "medium"
                }),
            }
        }
    
    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("width", "height", "info_text")
    FUNCTION = "generate_wan22_sizes"
    CATEGORY = "Wan 2.2"
    OUTPUT_NODE = False
    
    def generate_wan22_sizes(self, aspect_ratio, size_preset):
        """
        Generate optimized Wan 2.2 dimensions for the selected aspect ratio and size.
        
        Args:
            aspect_ratio: String key from ASPECT_RATIOS dict
            size_preset: "tiny", "small", "medium", "large", "extra-large", or "gigantic"
            
        Returns:
            tuple: (width, height, info_text)
        """
        # Get numeric ratio value
        ratio_value = self.ASPECT_RATIOS[aspect_ratio]
        
        # Generate all 6 size options for this ratio
        all_sizes = self._generate_optimal_sizes(ratio_value)
        
        # Select the requested size
        size_map = {
            "tiny": all_sizes["tiny"],
            "small": all_sizes["small"],
            "medium": all_sizes["medium"],
            "large": all_sizes["large"],
            "extra-large": all_sizes["extra-large"],
            "gigantic": all_sizes["gigantic"]
        }
        
        selected_width, selected_height = size_map[size_preset]
        
        # Create formatted info text
        info_lines = [
            "Wan 2.2 Size Preset",
            "═══════════════════════════",
            f"Selected Ratio: {aspect_ratio}",
            f"Ratio Value: {ratio_value:.3f}",
            "",
            "Available Sizes:",
        ]
        
        for preset_name, (w, h) in all_sizes.items():
            pixels = w * h
            checkmark = "✓ " if preset_name == size_preset else "  "
            info_lines.append(f"{checkmark}{preset_name.capitalize()}: {w}×{h} (~{pixels//1000}K pixels)")
        
        info_lines.append("")
        info_lines.append("All dimensions divisible by 8")
        
        info_text = "\n".join(info_lines)
        
        # Console logging for debugging
        print(f"\n{'='*50}")
        print(f"Wan 2.2 Size Preset Generated")
        print(f"{'='*50}")
        print(f"Aspect Ratio: {aspect_ratio} ({ratio_value:.3f})")
        print(f"Size Preset: {size_preset}")
        print(f"\nAll Available Sizes:")
        for preset_name, (w, h) in all_sizes.items():
            mark = "→" if preset_name == size_preset else " "
            print(f"  {mark} {preset_name}: {w}×{h} ({w*h} pixels)")
        print(f"\nSelected Output: {selected_width}×{selected_height}")
        print(f"{'='*50}\n")
        
        return (selected_width, selected_height, info_text)
    
    def _generate_optimal_sizes(self, aspect_ratio):
        """
        Generate 4 optimized size pairs (small, medium, large, extra-large) for given aspect ratio.
        Uses documented Wan 2.2 training sizes when available, calculates optimal otherwise.
        
        Args:
            aspect_ratio: Numeric aspect ratio (width/height)
            
        Returns:
            dict: {"small": (w,h), "medium": (w,h), "large": (w,h), "extra-large": (w,h)}
        """
        sizes = {}
        
        for preset_name, target_pixels in self.TARGET_PIXELS.items():
            # First, try to find a matching known Wan 2.2 size
            best_known = self._find_closest_known_size(aspect_ratio, target_pixels)
            
            if best_known:
                sizes[preset_name] = best_known
            else:
                # Calculate optimal size for this pixel target
                sizes[preset_name] = self._calculate_optimal_size(aspect_ratio, target_pixels)
        
        return sizes
    
    def _find_closest_known_size(self, target_ratio, target_pixels):
        """
        Find a documented Wan 2.2 training size that matches the target ratio and pixel count.
        
        Args:
            target_ratio: Target aspect ratio
            target_pixels: Target pixel count
            
        Returns:
            tuple: (width, height) if match found, None otherwise
        """
        RATIO_TOLERANCE = 0.05  # 5% ratio difference allowed
        PIXEL_TOLERANCE = 0.30  # 30% pixel count difference allowed
        
        best_match = None
        best_score = float('inf')
        
        for width, height in self.WAN22_KNOWN_SIZES:
            size_ratio = width / height
            size_pixels = width * height
            
            # Calculate how close this size is to our targets
            ratio_diff = abs(size_ratio - target_ratio) / target_ratio
            pixel_diff = abs(size_pixels - target_pixels) / target_pixels
            
            # Check if within tolerances
            if ratio_diff <= RATIO_TOLERANCE and pixel_diff <= PIXEL_TOLERANCE:
                # Combined score (lower is better)
                score = ratio_diff + pixel_diff
                if score < best_score:
                    best_score = score
                    best_match = (width, height)
        
        return best_match
    
    def _calculate_optimal_size(self, aspect_ratio, target_pixels):
        """
        Calculate optimal width/height for given aspect ratio and target pixel count.
        Ensures divisibility by 8.
        
        Args:
            aspect_ratio: Target aspect ratio (width/height)
            target_pixels: Target total pixel count
            
        Returns:
            tuple: (width, height) both divisible by 8
        """
        # Calculate ideal dimensions
        # aspect_ratio = width / height
        # target_pixels = width * height
        # Solving: height = sqrt(target_pixels / aspect_ratio)
        ideal_height = math.sqrt(target_pixels / aspect_ratio)
        ideal_width = aspect_ratio * ideal_height
        
        # Round to nearest multiple of 8
        height = self._round_to_multiple(ideal_height, 8)
        width = self._round_to_multiple(ideal_width, 8)
        
        return (width, height)
    
    def _round_to_multiple(self, value, multiple):
        """Round value to nearest multiple."""
        return int((value + multiple/2) // multiple) * multiple


# Node registration
NODE_CLASS_MAPPINGS = {
    "Wan22_Size_Preset": Wan22_Size_Preset
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22_Size_Preset": "Wan 2.2 Size Preset"
}
