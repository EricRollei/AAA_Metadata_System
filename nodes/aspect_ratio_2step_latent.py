"""
Aspect Ratio for 2step Latent Sample Node
Provides width and height outputs for common aspect ratios, scaled to a base resolution.
Optionally detects aspect ratio from an input image.
"""

import math
from typing import Optional, Tuple

class AspectRatio2StepLatent:
    """
    Calculate width and height for various aspect ratios at different base resolutions.
    All outputs are divisible by 16 for optimal latent compatibility.
    """
    
    # Base resolutions from 256 to 1024 in 64-step increments
    BASE_RESOLUTIONS = [str(i) for i in range(256, 1025, 64)]
    
    # Aspect ratios from 1:2 to 2:1 with common values
    # Format: "display_name": (width_ratio, height_ratio)
    ASPECT_RATIOS = {
        # Portrait ratios (height > width)
        "1:2 Portrait": (1, 2),
        "9:16 Portrait": (9, 16),
        "2:3 Portrait": (2, 3),
        "3:4 Portrait": (3, 4),
        "4:5 Portrait": (4, 5),
        # Square
        "1:1 Square": (1, 1),
        # Landscape ratios (width > height)
        "5:4 Landscape": (5, 4),
        "4:3 Landscape": (4, 3),
        "3:2 Landscape": (3, 2),
        "16:9 Landscape": (16, 9),
        "2:1 Landscape": (2, 1),
        # Additional common ratios
        "9:21 Portrait (Ultrawide)": (9, 21),
        "21:9 Landscape (Ultrawide)": (21, 9),
        "1:1.414 Portrait (A4)": (1000, 1414),  # sqrt(2) approximation
        "1.414:1 Landscape (A4)": (1414, 1000),
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_resolution": (cls.BASE_RESOLUTIONS, {
                    "default": "512",
                    "tooltip": "Base resolution for the shorter side (256-1024 in 64-step increments)"
                }),
                "aspect_ratio": (list(cls.ASPECT_RATIOS.keys()), {
                    "default": "1:1 Square",
                    "tooltip": "Select aspect ratio. Ignored if image is connected."
                }),
            },
            "optional": {
                "image": ("IMAGE", {
                    "tooltip": "Optional input image. If provided, its aspect ratio will be used instead of the dropdown selection."
                }),
            }
        }
    
    RETURN_TYPES = ("INT", "INT", "STRING", "FLOAT")
    RETURN_NAMES = ("width", "height", "ratio_string", "ratio_float")
    FUNCTION = "calculate_dimensions"
    CATEGORY = "image/preprocessing"
    
    DESCRIPTION = "Calculate width and height for 2-step latent sampling based on aspect ratio and base resolution. All outputs are divisible by 16."
    
    def _round_to_multiple(self, value: float, multiple: int = 16) -> int:
        """Round a value to the nearest multiple of the specified number."""
        return int(round(value / multiple) * multiple)
    
    def _get_ratio_from_image(self, image) -> Tuple[int, int]:
        """Extract width and height from an image tensor and return as ratio."""
        # Image tensor shape is typically [batch, height, width, channels]
        if len(image.shape) == 4:
            height = image.shape[1]
            width = image.shape[2]
        elif len(image.shape) == 3:
            height = image.shape[0]
            width = image.shape[1]
        else:
            raise ValueError(f"Unexpected image shape: {image.shape}")
        
        return width, height
    
    def _simplify_ratio(self, width: int, height: int) -> Tuple[int, int]:
        """Simplify a ratio to its smallest form using GCD."""
        gcd = math.gcd(width, height)
        return width // gcd, height // gcd
    
    def _ratio_to_string(self, width_ratio: int, height_ratio: int) -> str:
        """Convert ratio to a display string."""
        simplified_w, simplified_h = self._simplify_ratio(width_ratio, height_ratio)
        return f"{simplified_w}:{simplified_h}"
    
    def calculate_dimensions(self, base_resolution: str, aspect_ratio: str, image=None):
        """
        Calculate width and height based on aspect ratio and base resolution.
        
        Args:
            base_resolution: Base resolution as string (256-1024)
            aspect_ratio: Selected aspect ratio from dropdown
            image: Optional input image tensor
            
        Returns:
            Tuple of (width, height, ratio_string, ratio_float)
        """
        base_res = int(base_resolution)
        
        # Determine aspect ratio - from image if provided, otherwise from dropdown
        if image is not None:
            img_width, img_height = self._get_ratio_from_image(image)
            width_ratio, height_ratio = img_width, img_height
            ratio_source = "image"
        else:
            width_ratio, height_ratio = self.ASPECT_RATIOS[aspect_ratio]
            ratio_source = "dropdown"
        
        # Calculate the ratio as a float (width/height)
        ratio_float = width_ratio / height_ratio
        
        # Calculate dimensions using geometric mean approach
        # This keeps the total pixel area roughly equal to base_res^2
        # For a 4:5 ratio at 512 base: width = 512 * sqrt(4/5), height = 512 * sqrt(5/4)
        # So width < 512 and height > 512 by proportional amounts
        
        aspect = width_ratio / height_ratio
        # width = base_res * sqrt(aspect), height = base_res / sqrt(aspect)
        # This ensures width * height ≈ base_res^2
        sqrt_aspect = math.sqrt(aspect)
        
        width = self._round_to_multiple(base_res * sqrt_aspect)
        height = self._round_to_multiple(base_res / sqrt_aspect)
        
        # Ensure minimum dimensions
        width = max(width, 16)
        height = max(height, 16)
        
        # Create ratio string
        ratio_string = self._ratio_to_string(width_ratio, height_ratio)
        if ratio_source == "image":
            ratio_string = f"{ratio_string} (from image)"
        
        return (width, height, ratio_string, ratio_float)


# Node registration
NODE_CLASS_MAPPINGS = {
    "AspectRatio2StepLatent": AspectRatio2StepLatent
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AspectRatio2StepLatent": "Aspect Ratio for 2step Latent Sample"
}
