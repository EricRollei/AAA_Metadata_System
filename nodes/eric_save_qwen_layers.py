"""
ComfyUI Node: EricSaveQwenLayers
Description: Saves Qwen-style layered images (from Qwen-Image-Layered or similar)
             as PSD, TIFF, or PNG sequence with full layer support.
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 1.0.0
Date: December 2025
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
- torch: BSD 3-Clause
- numpy: BSD 3-Clause
- psd-tools: MIT License
- pillow: PIL Software License

Designed for use with:
- Qwen-Image-Layered (image decomposition into semantic layers)
- Any workflow that produces multiple RGBA layers from a single image
"""

# Console output goes through one switch (see aaa_meta/console.py): problems are always shown,
# everything else only with the node's debug option on or AAA_META_VERBOSE=1.
try:
    from ..aaa_meta.console import quiet_print as print, note_error as _note_error
except Exception:                                    # used outside the pack
    def _note_error(error, where=""):
        pass

import os
import json
import datetime
import zipfile
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageCms
from typing import Dict, Any, List, Optional, Tuple
import folder_paths

# psd-tools for PSD support
try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    from psd_tools.constants import BlendMode, Resource
    from psd_tools.psd.image_resources import ImageResource, ImageResources
    HAS_PSD_TOOLS = True
except ImportError:
    HAS_PSD_TOOLS = False
    print("[EricSaveQwenLayers] psd-tools not installed. PSD export will be disabled.")

# ICC Profile paths (shared with main save node)
ICC_PROFILES = {
    'sRGB v4 Appearance': None,
    'sRGB v4 Preference': None,
    'sRGB v4 Display Class': None,
    'Adobe RGB': None,
    'ProPhoto RGB': None,
    'None': None
}

PROFILE_FILENAMES = {
    'sRGB v4 Appearance': 'sRGB_ICC_v4_Appearance.icc',
    'sRGB v4 Preference': 'sRGB_v4_ICC_preference.icc',
    'sRGB v4 Display Class': 'sRGB_v4_ICC_preference_displayclass.icc',
    'Adobe RGB': 'AdobeRGB1998.icc',
    'ProPhoto RGB': 'ProPhoto.icm',
}

# Blend mode mapping from string to psd-tools BlendMode
BLEND_MODE_MAP = {
    "normal": BlendMode.NORMAL if HAS_PSD_TOOLS else None,
    "multiply": BlendMode.MULTIPLY if HAS_PSD_TOOLS else None,
    "screen": BlendMode.SCREEN if HAS_PSD_TOOLS else None,
    "overlay": BlendMode.OVERLAY if HAS_PSD_TOOLS else None,
    "darken": BlendMode.DARKEN if HAS_PSD_TOOLS else None,
    "lighten": BlendMode.LIGHTEN if HAS_PSD_TOOLS else None,
    "color_dodge": BlendMode.COLOR_DODGE if HAS_PSD_TOOLS else None,
    "color_burn": BlendMode.COLOR_BURN if HAS_PSD_TOOLS else None,
    "hard_light": BlendMode.HARD_LIGHT if HAS_PSD_TOOLS else None,
    "soft_light": BlendMode.SOFT_LIGHT if HAS_PSD_TOOLS else None,
    "difference": BlendMode.DIFFERENCE if HAS_PSD_TOOLS else None,
    "exclusion": BlendMode.EXCLUSION if HAS_PSD_TOOLS else None,
    "hue": BlendMode.HUE if HAS_PSD_TOOLS else None,
    "saturation": BlendMode.SATURATION if HAS_PSD_TOOLS else None,
    "color": BlendMode.COLOR if HAS_PSD_TOOLS else None,
    "luminosity": BlendMode.LUMINOSITY if HAS_PSD_TOOLS else None,
}


class EricSaveQwenLayers:
    """
    Save Qwen-style layered images to PSD, TIFF, or PNG sequence.
    
    Designed for:
    - Qwen-Image-Layered output (semantic layer decomposition)
    - Any multi-layer RGBA image batch
    - Round-trip workflows with EricLoadQwenLayers
    
    Features:
    - Supports up to 10 layers (8 from Qwen + 2 extra)
    - Preserves layer names, blend modes, opacity, visibility
    - PSD format with full Photoshop compatibility
    - TIFF multi-page format
    - PNG sequence with manifest
    - Optional composite layer generation
    - ICC color profile embedding
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # Build available formats based on installed libraries
        file_formats = ["png_sequence"]
        if HAS_PSD_TOOLS:
            file_formats.insert(0, "psd")  # PSD is preferred
        file_formats.extend(["tiff", "zip"])
        
        blend_modes = list(BLEND_MODE_MAP.keys())
        
        return {
            "required": {
                "layers": ("IMAGE", {
                    "tooltip": "Batch of layer images [B, H, W, C]. Can be RGB or RGBA."
                }),
                "filename_prefix": ("STRING", {
                    "default": "qwen_layers",
                    "tooltip": "Base filename for output. Can include %date:yyyy-MM-dd% formatting."
                }),
                "file_format": (file_formats, {
                    "default": file_formats[0],
                    "tooltip": "Output format: PSD (best for Photoshop), TIFF (multi-page), PNG sequence, or ZIP archive."
                }),
            },
            "optional": {
                # Layer naming
                "layer_names": ("STRING", {
                    "default": "",
                    "tooltip": "Comma-separated layer names (e.g., 'Background,Subject,Text'). Empty = auto-name Layer_1, Layer_2, etc."
                }),
                
                # Alpha/mask handling
                "masks": ("MASK", {
                    "tooltip": "Optional mask batch to use as alpha channels. If not provided, uses alpha from layers if RGBA, or full opacity if RGB."
                }),
                
                # Blend modes and opacity (comma-separated for all layers)
                "blend_modes": ("STRING", {
                    "default": "normal",
                    "tooltip": "Comma-separated blend modes per layer. Single value applies to all. Options: normal, multiply, screen, overlay, etc."
                }),
                "opacities": ("STRING", {
                    "default": "255",
                    "tooltip": "Comma-separated opacity values (0-255) per layer. Single value applies to all."
                }),
                "visibility": ("STRING", {
                    "default": "true",
                    "tooltip": "Comma-separated visibility flags (true/false) per layer. Single value applies to all."
                }),
                
                # Composite options
                "include_composite": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Include a flattened composite layer at the top of the stack."
                }),
                "composite_name": ("STRING", {
                    "default": "Composite",
                    "tooltip": "Name for the composite layer."
                }),
                
                # Color management
                "color_profile": (list(ICC_PROFILES.keys()), {
                    "default": "sRGB v4 Appearance",
                    "tooltip": "ICC color profile to embed in the output file."
                }),
                
                # Alpha handling
                "alpha_mode": (["straight", "premultiplied", "auto"], {
                    "default": "auto",
                    "tooltip": "Alpha handling: straight (standard), premultiplied (for compositing), auto (format-appropriate)."
                }),
                
                # Output options
                "custom_output_directory": ("STRING", {
                    "default": "",
                    "tooltip": "Custom output directory. Empty = default output folder."
                }),
                "include_datetime": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Add date/time to filename."
                }),
                
                # Metadata
                "save_manifest": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Save a JSON manifest with layer info (names, blend modes, order)."
                }),
                
                # Layer order
                "layer_order": (["bottom_to_top", "top_to_bottom"], {
                    "default": "bottom_to_top",
                    "tooltip": "Layer stacking order. bottom_to_top = first layer is background. top_to_bottom = first layer is foreground."
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "IMAGE")
    RETURN_NAMES = ("filepath", "layer_count", "layer_preview")
    FUNCTION = "save_layers"
    CATEGORY = "Eric's Nodes/Layers"
    OUTPUT_NODE = True
    
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
    
    def save_layers(
        self,
        layers: torch.Tensor,
        filename_prefix: str,
        file_format: str,
        layer_names: str = "",
        masks: Optional[torch.Tensor] = None,
        blend_modes: str = "normal",
        opacities: str = "255",
        visibility: str = "true",
        include_composite: bool = True,
        composite_name: str = "Composite",
        color_profile: str = "sRGB v4 Appearance",
        alpha_mode: str = "auto",
        custom_output_directory: str = "",
        include_datetime: bool = True,
        save_manifest: bool = True,
        layer_order: str = "bottom_to_top",
    ) -> Tuple[str, int, torch.Tensor]:
        """
        Save layered images to the specified format.
        
        Args:
            layers: Batch tensor of layer images [B, H, W, C]
            filename_prefix: Base filename
            file_format: Output format (psd, tiff, png_sequence, zip)
            layer_names: Comma-separated layer names
            masks: Optional mask batch for alpha channels
            blend_modes: Comma-separated blend modes
            opacities: Comma-separated opacity values
            visibility: Comma-separated visibility flags
            include_composite: Whether to add composite layer
            composite_name: Name for composite layer
            color_profile: ICC profile to embed
            alpha_mode: Alpha handling mode
            custom_output_directory: Custom output path
            include_datetime: Add datetime to filename
            save_manifest: Save JSON manifest
            layer_order: Layer stacking order
            
        Returns:
            Tuple of (filepath, layer_count, layer_preview_image)
        """
        
        # Get batch info
        batch_size = layers.shape[0]
        height = layers.shape[1]
        width = layers.shape[2]
        channels = layers.shape[3]
        
        print(f"[EricSaveQwenLayers] Processing {batch_size} layers, {width}x{height}, {channels} channels")
        
        # Parse layer properties
        names_list = self._parse_layer_names(layer_names, batch_size)
        blend_modes_list = self._parse_comma_list(blend_modes, batch_size, "normal")
        opacities_list = self._parse_int_list(opacities, batch_size, 255)
        visibility_list = self._parse_bool_list(visibility, batch_size, True)
        
        # Determine output path
        output_path = self._get_output_path(
            filename_prefix, 
            file_format, 
            custom_output_directory,
            include_datetime
        )
        
        # Convert layers to PIL images with proper alpha
        pil_layers = self._convert_layers_to_pil(layers, masks, channels)
        
        # Reverse order if needed
        if layer_order == "top_to_bottom":
            pil_layers = list(reversed(pil_layers))
            names_list = list(reversed(names_list))
            blend_modes_list = list(reversed(blend_modes_list))
            opacities_list = list(reversed(opacities_list))
            visibility_list = list(reversed(visibility_list))
        
        # Generate composite if requested
        composite_pil = None
        if include_composite:
            composite_pil = self._generate_composite(pil_layers, blend_modes_list, opacities_list)
        
        # Build layer info for manifest
        layer_info = {
            "layer_count": batch_size,
            "width": width,
            "height": height,
            "layers": []
        }
        
        for i, name in enumerate(names_list):
            layer_info["layers"].append({
                "index": i,
                "name": name,
                "blend_mode": blend_modes_list[i],
                "opacity": opacities_list[i],
                "visible": visibility_list[i]
            })
        
        if include_composite:
            layer_info["composite"] = {
                "name": composite_name,
                "included": True
            }
        
        # Save based on format
        if file_format == "psd":
            self._save_as_psd(
                output_path, pil_layers, names_list, blend_modes_list,
                opacities_list, visibility_list, composite_pil, composite_name,
                color_profile, width, height
            )
        elif file_format == "tiff":
            self._save_as_tiff(
                output_path, pil_layers, names_list,
                composite_pil, color_profile
            )
        elif file_format == "png_sequence":
            self._save_as_png_sequence(
                output_path, pil_layers, names_list, composite_pil, composite_name
            )
        elif file_format == "zip":
            self._save_as_zip(
                output_path, pil_layers, names_list, layer_info, composite_pil, composite_name
            )
        
        # Save manifest
        if save_manifest and file_format != "zip":  # ZIP includes manifest internally
            manifest_path = output_path.rsplit('.', 1)[0] + "_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(layer_info, f, indent=2)
            print(f"[EricSaveQwenLayers] Saved manifest: {manifest_path}")
        
        # Generate layer preview visualization
        preview_image = self._generate_layer_preview(
            pil_layers, names_list, blend_modes_list, opacities_list, visibility_list,
            width, height
        )
        
        print(f"[EricSaveQwenLayers] Saved {batch_size} layers to: {output_path}")
        
        return (output_path, batch_size, preview_image)
    
    def _parse_layer_names(self, names_str: str, count: int) -> List[str]:
        """Parse layer names from comma-separated string."""
        if not names_str.strip():
            return [f"Layer_{i+1}" for i in range(count)]
        
        names = [n.strip() for n in names_str.split(',')]
        
        # Extend if not enough names provided
        while len(names) < count:
            names.append(f"Layer_{len(names)+1}")
        
        return names[:count]
    
    def _parse_comma_list(self, value_str: str, count: int, default: str) -> List[str]:
        """Parse comma-separated string list, extending to count."""
        if not value_str.strip():
            return [default] * count
        
        values = [v.strip().lower() for v in value_str.split(',')]
        
        # If single value, apply to all
        if len(values) == 1:
            return values * count
        
        # Extend with last value if not enough
        while len(values) < count:
            values.append(values[-1] if values else default)
        
        return values[:count]
    
    def _parse_int_list(self, value_str: str, count: int, default: int) -> List[int]:
        """Parse comma-separated int list."""
        if not value_str.strip():
            return [default] * count
        
        try:
            values = [int(v.strip()) for v in value_str.split(',')]
        except ValueError:
            return [default] * count
        
        if len(values) == 1:
            return values * count
        
        while len(values) < count:
            values.append(values[-1] if values else default)
        
        return [max(0, min(255, v)) for v in values[:count]]
    
    def _parse_bool_list(self, value_str: str, count: int, default: bool) -> List[bool]:
        """Parse comma-separated bool list."""
        if not value_str.strip():
            return [default] * count
        
        values = []
        for v in value_str.split(','):
            v = v.strip().lower()
            values.append(v in ('true', '1', 'yes', 'on', 'visible'))
        
        if len(values) == 1:
            return values * count
        
        while len(values) < count:
            values.append(values[-1] if values else default)
        
        return values[:count]
    
    def _get_output_path(
        self, 
        prefix: str, 
        file_format: str, 
        custom_dir: str,
        include_datetime: bool
    ) -> str:
        """Generate output file path."""
        
        # Determine base directory
        if custom_dir.strip():
            if os.path.isabs(custom_dir):
                base_dir = custom_dir
            else:
                base_dir = os.path.join(self.output_dir, custom_dir)
        else:
            base_dir = self.output_dir
        
        os.makedirs(base_dir, exist_ok=True)
        
        # Build filename
        filename = prefix
        
        if include_datetime:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}"
        
        # Add extension
        ext_map = {
            "psd": ".psd",
            "tiff": ".tiff",
            "png_sequence": "",  # Directory
            "zip": ".zip"
        }
        ext = ext_map.get(file_format, ".psd")
        
        if file_format == "png_sequence":
            # Create a directory for the sequence
            output_path = os.path.join(base_dir, filename)
            os.makedirs(output_path, exist_ok=True)
        else:
            output_path = os.path.join(base_dir, filename + ext)
        
        return output_path
    
    def _convert_layers_to_pil(
        self, 
        layers: torch.Tensor, 
        masks: Optional[torch.Tensor],
        channels: int
    ) -> List[Image.Image]:
        """Convert tensor layers to PIL RGBA images."""
        pil_layers = []
        batch_size = layers.shape[0]
        
        for i in range(batch_size):
            layer_np = layers[i].cpu().numpy()
            
            # Normalize to 0-255
            if layer_np.max() <= 1.0:
                layer_np = (layer_np * 255).astype(np.uint8)
            else:
                layer_np = np.clip(layer_np, 0, 255).astype(np.uint8)
            
            # Handle RGB vs RGBA
            if channels == 4:
                # Already RGBA
                pil_img = Image.fromarray(layer_np, mode='RGBA')
            elif channels == 3:
                # RGB - need to add alpha
                if masks is not None and i < masks.shape[0]:
                    # Use provided mask as alpha
                    mask_np = masks[i].cpu().numpy()
                    if mask_np.max() <= 1.0:
                        mask_np = (mask_np * 255).astype(np.uint8)
                    else:
                        mask_np = np.clip(mask_np, 0, 255).astype(np.uint8)
                    
                    # Create RGBA
                    rgba = np.zeros((layer_np.shape[0], layer_np.shape[1], 4), dtype=np.uint8)
                    rgba[:, :, :3] = layer_np
                    rgba[:, :, 3] = mask_np
                    pil_img = Image.fromarray(rgba, mode='RGBA')
                else:
                    # Full opacity
                    pil_img = Image.fromarray(layer_np, mode='RGB').convert('RGBA')
            else:
                # Grayscale or other - convert to RGBA
                pil_img = Image.fromarray(layer_np).convert('RGBA')
            
            pil_layers.append(pil_img)
        
        return pil_layers
    
    def _generate_composite(
        self,
        layers: List[Image.Image],
        blend_modes: List[str],
        opacities: List[int]
    ) -> Image.Image:
        """Generate a flattened composite of all layers."""
        if not layers:
            return None
        
        # Start with the first layer as base
        composite = layers[0].copy()
        
        # Simple alpha compositing for now (normal blend mode)
        for i, layer in enumerate(layers[1:], 1):
            # Apply opacity
            if opacities[i] < 255:
                layer = layer.copy()
                # Reduce alpha by opacity factor
                alpha = layer.split()[3]
                alpha = alpha.point(lambda x: int(x * opacities[i] / 255))
                layer.putalpha(alpha)
            
            # Composite using alpha
            composite = Image.alpha_composite(composite, layer)
        
        return composite
    
    def _save_as_psd(
        self,
        output_path: str,
        layers: List[Image.Image],
        names: List[str],
        blend_modes: List[str],
        opacities: List[int],
        visibility: List[bool],
        composite: Optional[Image.Image],
        composite_name: str,
        color_profile: str,
        width: int,
        height: int
    ):
        """Save layers as PSD file."""
        if not HAS_PSD_TOOLS:
            print("[EricSaveQwenLayers] Error: psd-tools not installed")
            return
        
        # Create new PSD
        psd = PSDImage.new(mode='RGBA', size=(width, height))
        
        # Add layers (bottom to top)
        for i, (layer_img, name) in enumerate(zip(layers, names)):
            pixel_layer = PixelLayer.frompil(layer_img, psd)
            pixel_layer.name = name
            
            # Set blend mode
            blend_mode_str = blend_modes[i] if i < len(blend_modes) else "normal"
            psd_blend = BLEND_MODE_MAP.get(blend_mode_str, BlendMode.NORMAL)
            if psd_blend:
                pixel_layer.blend_mode = psd_blend
            
            # Set opacity
            pixel_layer.opacity = opacities[i] if i < len(opacities) else 255
            
            # Set visibility
            pixel_layer.visible = visibility[i] if i < len(visibility) else True
            
            psd.append(pixel_layer)
        
        # Add composite layer on top if requested
        if composite is not None:
            composite_layer = PixelLayer.frompil(composite, psd)
            composite_layer.name = composite_name
            composite_layer.blend_mode = BlendMode.NORMAL
            composite_layer.opacity = 255
            composite_layer.visible = False  # Hidden by default
            psd.append(composite_layer)
        
        # Add ICC profile
        profile_data = self._get_color_profile(color_profile)
        if profile_data:
            if not hasattr(psd._record, 'image_resources'):
                psd._record.image_resources = ImageResources()
            icc_res = ImageResource(
                signature=b'8BIM',
                key=Resource.ICC_PROFILE.value,
                name='',
                data=profile_data
            )
            psd._record.image_resources[Resource.ICC_PROFILE.value] = icc_res
        
        # Save
        psd.save(output_path)
        print(f"[EricSaveQwenLayers] Saved PSD with {len(layers)} layers: {output_path}")
    
    def _save_as_tiff(
        self,
        output_path: str,
        layers: List[Image.Image],
        names: List[str],
        composite: Optional[Image.Image],
        color_profile: str
    ):
        """Save layers as multi-page TIFF."""
        all_images = []
        
        # Add composite first if available
        if composite is not None:
            all_images.append(composite)
        
        all_images.extend(layers)
        
        # Save as multi-page TIFF
        if all_images:
            # First image
            first = all_images[0]
            
            # Prepare append images
            append_images = all_images[1:] if len(all_images) > 1 else []
            
            # Save with all pages
            first.save(
                output_path,
                format='TIFF',
                save_all=True,
                append_images=append_images,
                compression='lzw'
            )
        
        print(f"[EricSaveQwenLayers] Saved TIFF with {len(all_images)} pages: {output_path}")
    
    def _save_as_png_sequence(
        self,
        output_dir: str,
        layers: List[Image.Image],
        names: List[str],
        composite: Optional[Image.Image],
        composite_name: str
    ):
        """Save layers as PNG sequence in a directory."""
        # Save each layer
        for i, (layer, name) in enumerate(zip(layers, names)):
            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
            filename = f"{i:02d}_{safe_name}.png"
            filepath = os.path.join(output_dir, filename)
            layer.save(filepath, format='PNG')
        
        # Save composite
        if composite is not None:
            composite_filename = f"composite_{composite_name}.png"
            composite.save(os.path.join(output_dir, composite_filename), format='PNG')
        
        print(f"[EricSaveQwenLayers] Saved PNG sequence to: {output_dir}")
    
    def _save_as_zip(
        self,
        output_path: str,
        layers: List[Image.Image],
        names: List[str],
        layer_info: Dict,
        composite: Optional[Image.Image],
        composite_name: str
    ):
        """Save layers as ZIP archive with manifest."""
        import io
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Save each layer
            for i, (layer, name) in enumerate(zip(layers, names)):
                safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
                filename = f"layers/{i:02d}_{safe_name}.png"
                
                # Save to bytes buffer
                buffer = io.BytesIO()
                layer.save(buffer, format='PNG')
                buffer.seek(0)
                
                zf.writestr(filename, buffer.getvalue())
            
            # Save composite
            if composite is not None:
                buffer = io.BytesIO()
                composite.save(buffer, format='PNG')
                buffer.seek(0)
                zf.writestr(f"composite/{composite_name}.png", buffer.getvalue())
            
            # Save manifest
            zf.writestr("manifest.json", json.dumps(layer_info, indent=2))
        
        print(f"[EricSaveQwenLayers] Saved ZIP archive: {output_path}")
    
    def _get_color_profile(self, profile_name: str) -> Optional[bytes]:
        """Load ICC color profile data."""
        if profile_name == 'None':
            return None
        
        # Check cache
        if ICC_PROFILES.get(profile_name):
            return ICC_PROFILES[profile_name]
        
        # Find profile file
        filename = PROFILE_FILENAMES.get(profile_name)
        if not filename:
            return None
        
        # Look in resources directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        profile_path = os.path.join(script_dir, 'resources', 'icc_profiles', filename)
        
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'rb') as f:
                    profile_data = f.read()
                ICC_PROFILES[profile_name] = profile_data
                return profile_data
            except Exception as e:
                print(f"[EricSaveQwenLayers] Error loading ICC profile: {e}")
        
        return None
    
    def _generate_layer_preview(
        self,
        layers: List[Image.Image],
        names: List[str],
        blend_modes: List[str],
        opacities: List[int],
        visibility: List[bool],
        width: int,
        height: int
    ) -> torch.Tensor:
        """
        Generate a visual preview showing the layer stack.
        Like a mini Photoshop layers panel.
        """
        # Calculate preview dimensions
        thumb_size = 64
        row_height = 80
        panel_width = 300
        panel_height = max(200, len(layers) * row_height + 40)
        
        # Create preview image
        preview = Image.new('RGBA', (panel_width, panel_height), (40, 40, 40, 255))
        draw = ImageDraw.Draw(preview)
        
        # Try to get a font
        try:
            font = ImageFont.truetype("arial.ttf", 12)
            font_small = ImageFont.truetype("arial.ttf", 10)
        except Exception as _caught:
            _note_error(_caught, "eric_save_qwen_layers.py:772")
            font = ImageFont.load_default()
            font_small = font
        
        # Header
        draw.text((10, 10), "Layer Stack Preview", fill=(255, 255, 255), font=font)
        draw.line([(10, 30), (panel_width - 10, 30)], fill=(100, 100, 100))
        
        # Draw each layer (top to bottom in preview)
        y_offset = 40
        for i in range(len(layers) - 1, -1, -1):  # Reverse order for visual representation
            layer = layers[i]
            name = names[i] if i < len(names) else f"Layer_{i+1}"
            blend = blend_modes[i] if i < len(blend_modes) else "normal"
            opacity = opacities[i] if i < len(opacities) else 255
            visible = visibility[i] if i < len(visibility) else True
            
            # Background for this row
            row_color = (60, 60, 60) if i % 2 == 0 else (50, 50, 50)
            draw.rectangle(
                [(5, y_offset), (panel_width - 5, y_offset + row_height - 5)],
                fill=row_color
            )
            
            # Visibility indicator
            vis_color = (0, 200, 0) if visible else (100, 100, 100)
            draw.ellipse(
                [(10, y_offset + 25), (25, y_offset + 40)],
                fill=vis_color
            )
            
            # Thumbnail
            thumb = layer.copy()
            thumb.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
            
            # Add checkerboard background for transparency
            checker = self._create_checkerboard(thumb_size, thumb_size)
            checker.paste(thumb, (0, 0), thumb if thumb.mode == 'RGBA' else None)
            
            preview.paste(checker, (35, y_offset + 8))
            
            # Layer name
            draw.text((105, y_offset + 10), name[:20], fill=(255, 255, 255), font=font)
            
            # Blend mode and opacity
            info_text = f"{blend} | {opacity}/255"
            draw.text((105, y_offset + 30), info_text, fill=(180, 180, 180), font=font_small)
            
            # Index
            draw.text((105, y_offset + 50), f"Index: {i}", fill=(120, 120, 120), font=font_small)
            
            y_offset += row_height
        
        # Convert to tensor
        preview_rgb = preview.convert('RGB')
        preview_np = np.array(preview_rgb).astype(np.float32) / 255.0
        preview_tensor = torch.from_numpy(preview_np).unsqueeze(0)
        
        return preview_tensor
    
    def _create_checkerboard(self, width: int, height: int, square_size: int = 8) -> Image.Image:
        """Create a checkerboard pattern for transparency visualization."""
        checker = Image.new('RGB', (width, height))
        pixels = checker.load()
        
        for y in range(height):
            for x in range(width):
                if (x // square_size + y // square_size) % 2 == 0:
                    pixels[x, y] = (200, 200, 200)
                else:
                    pixels[x, y] = (150, 150, 150)
        
        return checker


# Node registration
NODE_CLASS_MAPPINGS = {
    "EricSaveQwenLayers": EricSaveQwenLayers
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricSaveQwenLayers": "🎨 Save Qwen Layers"
}
