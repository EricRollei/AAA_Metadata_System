"""
Eric's Extended Load Image Node
Loads images with file picker dialog and extended format support

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
"""

import os
import hashlib
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

import folder_paths
import node_helpers


class EricLoadImageExtended:
    """
    Extended Load Image node that supports:
    - File picker dialog for easy image selection
    - Additional formats: TIFF, WebP, SVG, PSD
    - Outputs: IMAGE, MASK, filename, and full path
    """
    
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        
        # Extended file type support
        supported_extensions = [
            '.jpg', '.jpeg', '.png', '.bmp', '.gif',  # Standard formats
            '.tiff', '.tif',                           # TIFF
            '.webp',                                   # WebP
            '.psd',                                    # Photoshop
            '.svg'                                     # SVG (will be rasterized)
        ]
        
        # Filter files by supported extensions
        filtered_files = []
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_extensions:
                filtered_files.append(f)
        
        return {
            "required": {
                "image": (sorted(filtered_files), {"image_upload": True})
            },
        }
    
    CATEGORY = "image"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "filename", "full_path")
    FUNCTION = "load_image"
    
    def load_image(self, image):
        """
        Load an image and return the image tensor, mask, filename, and full path
        
        Args:
            image: The filename of the image to load
            
        Returns:
            tuple: (image_tensor, mask_tensor, filename, full_path)
        """
        # Get the full path to the image
        image_path = folder_paths.get_annotated_filepath(image)
        
        # Extract just the filename without path
        filename = os.path.basename(image_path)
        
        # Get file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Handle SVG files (convert to PNG first)
        if file_ext == '.svg':
            img = self._load_svg(image_path)
        else:
            # Open image with PIL
            img = node_helpers.pillow(Image.open, image_path)
        
        output_images = []
        output_masks = []
        w, h = None, None
        excluded_formats = ['MPO']
        
        # Handle multi-frame images (like GIFs, TIFFs with multiple pages)
        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)
            
            # Handle 16-bit images
            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            
            # Convert to RGB
            image_tensor = i.convert("RGB")
            
            if len(output_images) == 0:
                w = image_tensor.size[0]
                h = image_tensor.size[1]
            
            # Ensure consistent dimensions
            if image_tensor.size[0] != w or image_tensor.size[1] != h:
                continue
            
            # Convert to numpy then to torch tensor
            image_np = np.array(image_tensor).astype(np.float32) / 255.0
            image_tensor = torch.from_numpy(image_np)[None,]
            
            # Extract or create mask
            if 'A' in i.getbands():
                mask_np = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask_np)
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
            
            output_images.append(image_tensor)
            output_masks.append(mask.unsqueeze(0))
        
        # Combine multiple frames if present
        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]
        
        return (output_image, output_mask, filename, image_path)
    
    def _load_svg(self, svg_path, width=1024, height=1024):
        """
        Load and rasterize an SVG file
        
        Args:
            svg_path: Path to the SVG file
            width: Width to rasterize to (default: 1024)
            height: Height to rasterize to (default: 1024)
            
        Returns:
            PIL Image
        """
        try:
            # Try using cairosvg if available
            import cairosvg
            from io import BytesIO
            
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=width,
                output_height=height
            )
            img = Image.open(BytesIO(png_data))
            return img
        except ImportError:
            # Fallback: try svglib + reportlab
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                from io import BytesIO
                
                drawing = svg2rlg(svg_path)
                png_data = BytesIO()
                renderPM.drawToFile(drawing, png_data, fmt="PNG")
                png_data.seek(0)
                img = Image.open(png_data)
                return img
            except ImportError:
                # Final fallback: create a placeholder image with text
                img = Image.new('RGB', (width, height), color=(128, 128, 128))
                return img
    
    @classmethod
    def IS_CHANGED(s, image):
        """
        Check if the image file has changed
        """
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()
    
    @classmethod
    def VALIDATE_INPUTS(s, image):
        """
        Validate that the image file exists
        """
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True


# Node registration
NODE_CLASS_MAPPINGS = {
    "EricLoadImageExtended": EricLoadImageExtended
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricLoadImageExtended": "📁 Eric Load Image Extended"
}
