"""
Eric's Load Image with Layers Node
Loads images with full layer support for PSD files
Complements eric_metadata_save_image_v099d
"""

import os
import hashlib
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence

import folder_paths
import node_helpers

# Try to import psd-tools for layer support
try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer, Group
    PSD_TOOLS_AVAILABLE = True
except ImportError:
    PSD_TOOLS_AVAILABLE = False
    print("[EricLoadImageWithLayers] Warning: psd-tools not installed. PSD layer support disabled.")
    print("  Install with: pip install psd-tools")


class EricLoadImageWithLayers:
    """
    Advanced Load Image node that supports:
    - File picker dialog for easy image selection
    - Additional formats: TIFF, WebP, SVG, PSD
    - Full PSD layer support (load individual layers or all layers)
    - Outputs: IMAGE, MASK, filename, full path, and layer info
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
        
        load_modes = [
            "composite",      # Default: flattened composite image
            "all_layers",     # Load all layers as separate images (batch)
            "layer_by_name",  # Load specific layer by name
            "layer_by_index", # Load specific layer by index
            "visible_only"    # Load only visible layers
        ]
        
        return {
            "required": {
                "image": (sorted(filtered_files), {"image_upload": True}),
                "load_mode": (load_modes, {
                    "default": "composite",
                    "tooltip": "How to load layers from PSD files"
                })
            },
            "optional": {
                "layer_name": ("STRING", {
                    "default": "",
                    "tooltip": "Layer name to load (for layer_by_name mode)"
                }),
                "layer_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100,
                    "tooltip": "Layer index to load (for layer_by_index mode, 0 = first layer)"
                }),
            }
        }
    
    CATEGORY = "image"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "filename", "full_path", "layer_info")
    FUNCTION = "load_image"
    
    def load_image(self, image, load_mode="composite", layer_name="", layer_index=0):
        """
        Load an image with optional layer support
        
        Args:
            image: The filename of the image to load
            load_mode: How to handle layers (composite, all_layers, etc.)
            layer_name: Name of specific layer to load
            layer_index: Index of specific layer to load
            
        Returns:
            tuple: (image_tensor, mask_tensor, filename, full_path, layer_info)
        """
        # Get the full path to the image
        image_path = folder_paths.get_annotated_filepath(image)
        
        # Extract just the filename without path
        filename = os.path.basename(image_path)
        
        # Get file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Handle PSD files with layer support
        if file_ext == '.psd' and PSD_TOOLS_AVAILABLE and load_mode != "composite":
            return self._load_psd_with_layers(image_path, filename, load_mode, layer_name, layer_index)
        
        # Handle SVG files (convert to PNG first)
        elif file_ext == '.svg':
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
        
        # Layer info for non-PSD files
        layer_info = f"Format: {file_ext}, Mode: {load_mode}, Frames: {len(output_images)}"
        
        return (output_image, output_mask, filename, image_path, layer_info)
    
    def _load_psd_with_layers(self, psd_path, filename, load_mode, layer_name, layer_index):
        """
        Load PSD file with layer support using psd-tools
        
        Args:
            psd_path: Path to PSD file
            filename: Filename for output
            load_mode: How to load layers
            layer_name: Specific layer name to load
            layer_index: Specific layer index to load
            
        Returns:
            tuple: (image_tensor, mask_tensor, filename, full_path, layer_info)
        """
        try:
            psd = PSDImage.open(psd_path)
            
            # Get all layers (excluding groups)
            all_layers = []
            for layer in psd:
                if isinstance(layer, PixelLayer):
                    all_layers.append(layer)
                elif isinstance(layer, Group):
                    # Recursively get layers from groups
                    for sublayer in layer.descendants():
                        if isinstance(sublayer, PixelLayer):
                            all_layers.append(sublayer)
            
            # Build layer info string
            layer_names = [layer.name for layer in all_layers]
            layer_info_parts = [
                f"Format: PSD",
                f"Mode: {load_mode}",
                f"Total Layers: {len(all_layers)}",
                f"Layer Names: {', '.join(layer_names[:5])}" + ("..." if len(layer_names) > 5 else "")
            ]
            layer_info = " | ".join(layer_info_parts)
            
            # Process based on load mode
            if load_mode == "all_layers":
                return self._load_all_psd_layers(psd, all_layers, filename, psd_path, layer_info)
            
            elif load_mode == "visible_only":
                visible_layers = [layer for layer in all_layers if layer.visible]
                if not visible_layers:
                    visible_layers = all_layers  # Fallback to all if none visible
                return self._load_all_psd_layers(psd, visible_layers, filename, psd_path, 
                                                 layer_info + f" | Visible: {len(visible_layers)}")
            
            elif load_mode == "layer_by_name":
                for layer in all_layers:
                    if layer.name == layer_name:
                        return self._load_single_psd_layer(layer, filename, psd_path, 
                                                          layer_info + f" | Selected: {layer_name}")
                # Fallback: layer not found, load composite
                print(f"[EricLoadImageWithLayers] Layer '{layer_name}' not found. Loading composite instead.")
                return self._load_psd_composite(psd, filename, psd_path, layer_info + " | Layer not found")
            
            elif load_mode == "layer_by_index":
                if 0 <= layer_index < len(all_layers):
                    layer = all_layers[layer_index]
                    return self._load_single_psd_layer(layer, filename, psd_path,
                                                       layer_info + f" | Selected: {layer.name} (index {layer_index})")
                # Fallback: invalid index, load composite
                print(f"[EricLoadImageWithLayers] Layer index {layer_index} out of range (0-{len(all_layers)-1}). Loading composite.")
                return self._load_psd_composite(psd, filename, psd_path, layer_info + " | Invalid index")
            
            else:  # composite (default)
                return self._load_psd_composite(psd, filename, psd_path, layer_info)
        
        except Exception as e:
            print(f"[EricLoadImageWithLayers] Error loading PSD with layers: {str(e)}")
            print("[EricLoadImageWithLayers] Falling back to PIL composite loading...")
            # Fallback to PIL for basic composite
            img = Image.open(psd_path)
            return self._convert_pil_to_tensors(img, filename, psd_path, f"PSD (fallback): {str(e)}")
    
    def _load_psd_composite(self, psd, filename, psd_path, layer_info):
        """Load flattened composite image from PSD"""
        composite = psd.composite()
        return self._convert_pil_to_tensors(composite, filename, psd_path, layer_info)
    
    def _load_single_psd_layer(self, layer, filename, psd_path, layer_info):
        """Load a single layer from PSD"""
        layer_img = layer.topil()
        if layer_img is None:
            # Empty layer, create blank image
            layer_img = Image.new('RGBA', (layer.width, layer.height), (0, 0, 0, 0))
        return self._convert_pil_to_tensors(layer_img, filename, psd_path, layer_info)
    
    def _load_all_psd_layers(self, psd, layers, filename, psd_path, layer_info):
        """Load all specified layers as a batch"""
        output_images = []
        output_masks = []
        
        for layer in layers:
            layer_img = layer.topil()
            if layer_img is None:
                continue
            
            # Convert to RGB for image
            img_rgb = layer_img.convert("RGB")
            img_np = np.array(img_rgb).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_np)[None,]
            output_images.append(img_tensor)
            
            # Extract alpha for mask
            if 'A' in layer_img.getbands():
                mask_np = np.array(layer_img.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask_np)
            else:
                mask = torch.zeros((layer_img.height, layer_img.width), dtype=torch.float32)
            
            output_masks.append(mask.unsqueeze(0))
        
        # If no valid layers, return empty image
        if not output_images:
            empty_img = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            empty_mask = torch.zeros((1, 512, 512), dtype=torch.float32)
            return (empty_img, empty_mask, filename, psd_path, layer_info + " | No valid layers")
        
        # Combine all layers into batch
        output_image = torch.cat(output_images, dim=0)
        output_mask = torch.cat(output_masks, dim=0)
        
        return (output_image, output_mask, filename, psd_path, layer_info)
    
    def _convert_pil_to_tensors(self, pil_img, filename, full_path, layer_info):
        """Convert PIL image to tensor format"""
        # Convert to RGB
        img_rgb = pil_img.convert("RGB")
        img_np = np.array(img_rgb).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np)[None,]
        
        # Extract mask if alpha present
        if 'A' in pil_img.getbands():
            mask_np = np.array(pil_img.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask_np)
        else:
            mask = torch.zeros((pil_img.height, pil_img.width), dtype=torch.float32)
        
        mask = mask.unsqueeze(0)
        
        return (img_tensor, mask, filename, full_path, layer_info)
    
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
    def IS_CHANGED(s, image, **kwargs):
        """
        Check if the image file has changed
        """
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()
    
    @classmethod
    def VALIDATE_INPUTS(s, image, **kwargs):
        """
        Validate that the image file exists
        """
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True


# Node registration
NODE_CLASS_MAPPINGS = {
    "EricLoadImageWithLayers": EricLoadImageWithLayers
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricLoadImageWithLayers": "🎨 Eric Load Image with Layers"
}
