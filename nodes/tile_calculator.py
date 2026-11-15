"""
Tile Calculator Node
Accepts an input image, calculates dimensions and determines how many 1024 tiles fit.

Author: Eric Hiss (GitHub: EricRollei)
Copyright (c) 2025 Eric Hiss. All rights reserved.
"""

import math
from typing import Tuple


class TileCalculator:
    """
    Calculate how many 1024x1024 tiles fit in an image.
    Outputs the closest integer number of tiles for width and height.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Input image to calculate tiles for"}),
            },
            "optional": {
                "tile_size": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 64,
                    "tooltip": "Size of each tile (default 1024)"}),
            }
        }
    
    RETURN_TYPES = ("INT", "INT", "INT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("width_tiles", "height_tiles", "image_width", "image_height", "aspect_ratio", "info")
    FUNCTION = "calculate_tiles"
    CATEGORY = "image/preprocessing"
    
    DESCRIPTION = "Calculate how many tiles of a given size fit in an image (rounded to nearest integer)"
    
    def calculate_tiles(self, image, tile_size: int = 1024) -> Tuple[int, int, int, int, float, str]:
        """
        Calculate tile counts for an image.
        
        Args:
            image: Input image tensor [batch, height, width, channels]
            tile_size: Size of each square tile (default 1024)
            
        Returns:
            Tuple of (width_tiles, height_tiles, image_width, image_height, aspect_ratio, info_string)
        """
        # Get image dimensions from tensor
        # Image tensor shape is typically [batch, height, width, channels]
        if len(image.shape) == 4:
            height = image.shape[1]
            width = image.shape[2]
        elif len(image.shape) == 3:
            height = image.shape[0]
            width = image.shape[1]
        else:
            raise ValueError(f"Unexpected image shape: {image.shape}")
        
        # Calculate number of tiles (rounded to nearest integer)
        width_tiles = round(width / tile_size)
        height_tiles = round(height / tile_size)
        
        # Ensure at least 1 tile in each dimension
        width_tiles = max(1, width_tiles)
        height_tiles = max(1, height_tiles)
        
        # Calculate aspect ratio (width / height)
        aspect_ratio = width / height if height > 0 else 1.0
        
        # Create info string
        info = (
            f"Image: {width}x{height} pixels\n"
            f"Tile size: {tile_size}x{tile_size}\n"
            f"Tiles needed: {width_tiles}W x {height_tiles}H\n"
            f"Total tiles: {width_tiles * height_tiles}\n"
            f"Aspect ratio: {aspect_ratio:.3f}\n"
            f"Coverage: {width_tiles * tile_size}x{height_tiles * tile_size} "
            f"({(width_tiles * tile_size * height_tiles * tile_size) / (width * height) * 100:.1f}% of original area)"
        )
        
        return (width_tiles, height_tiles, int(width), int(height), aspect_ratio, info)


# Node registration
NODE_CLASS_MAPPINGS = {
    "TileCalculator": TileCalculator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TileCalculator": "Tile Calculator",
}
