"""
ComfyUI Node: Eric's Color Palette Analyzer v3
Description: Analyzes dominant colors, color harmonies, and palette characteristics in images.
    Integrates with the metadata system to store color analysis results.
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
- opencv-python (cv2): Apache 2.0
- [colorthief]: MIT License
- [scikit-learn]: BSD 3-Clause

Eric's Color Palette Analyzer v3 with more cultural data, data moved to separate folder structure

Analyzes dominant colors, color harmonies, and palette characteristics in images.
Integrates with the metadata system to store color analysis results.
"""

import os
import sys  # Add this import since you use sys.path.append
import math
import numpy as np
import torch
from typing import Dict, Any, List, Tuple
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from colorthief import ColorThief
from PIL import Image, ImageDraw, ImageFont
import io
from matplotlib.colors import rgb2hex
import colorsys
import cv2

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService

# Add data directory to path if needed
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))

# Import data
from color_data.color_names_v2 import COLOR_NAMES
from color_data.color_culture_table import COLOR_CULTURE_DATA as RGB_CULTURE_CONCEPTS

class Eric_Color_Palette_Analyzer:
    """Node for analyzing color palettes in images"""
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=False)
        
        # Use imported color names
        self.color_names = COLOR_NAMES
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "num_colors": ("INT", {
                    "default": 5,
                    "min": 3,
                    "max": 10,
                    "step": 1,
                    "display": "slider"
                }),
                "input_filepath": ("STRING", {"default": ""}),
                "extraction_method": (["colorthief", "histogram", "kmeans"], {"default": "kmeans"}),
            },
            "optional": {
                "color_space": (["RGB", "HSV", "LAB"], {"default": "RGB"}),
                "palette_analysis": ("BOOLEAN", {"default": True}),
                "harmony_analysis": ("BOOLEAN", {"default": True}),
                # Metadata options
                "write_to_xmp": ("BOOLEAN", {"default": True}),
                "embed_metadata": ("BOOLEAN", {"default": True}),
                "write_text_file": ("BOOLEAN", {"default": False}),
                "write_to_database": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": False}),
                # New options for saving visualization images
                "save_color_swatch": ("BOOLEAN", {"default": False}),
                "save_color_spectrum": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING", 
                "STRING", "STRING", "STRING", "STRING", "DICT", "IMAGE")
    RETURN_NAMES = ("image", "color_swatch", "dominant_colors", "harmony_info", "characteristics", 
                "emotional_quality", "age_appeal", "cultural_significance", "cultural_meanings", "color_data", "color_histogram")

    FUNCTION = "analyze_colors"
    CATEGORY = "Eric's Nodes/Analysis"
    
    def analyze_colors(self, image, num_colors=5, input_filepath="", 
                    extraction_method="kmeans", 
                    color_space="RGB", palette_analysis=True, harmony_analysis=True,
                    write_to_xmp=True, embed_metadata=True, 
                    write_text_file=False, write_to_database=False,
                    debug_logging=False,
                    save_color_swatch=False, save_color_spectrum=False) -> tuple:
        """Analyze colors in image and generate color palette analysis"""
        try:
            # Enable debug logging if requested
            if (debug_logging):
                self.metadata_service.debug = True
                print(f"[ColorPalette] Starting color analysis for image")
            
            # Convert image tensor to numpy array
            if isinstance(image, torch.Tensor):
                # Convert tensor [B, H, W, C] to numpy [H, W, C]
                if len(image.shape) == 4:
                    np_image = image[0].cpu().numpy()
                else:
                    np_image = image.cpu().numpy()
                
                # Ensure values are in 0-255 range for PIL
                if np_image.max() <= 1.0:
                    np_image = (np_image * 255).astype(np.uint8)
            else:
                np_image = image
            
            # Convert to PIL Image for ColorThief
            pil_image = self._tensor_to_pil(np_image)
            
            # Extract dominant colors using selected method
            dominant_colors = self._extract_dominant_colors(pil_image, num_colors, extraction_method)
            
            # Get named colors
            named_colors = self._name_colors(dominant_colors)
            
            # Extract color palette characteristics
            if palette_analysis:
                characteristics = self._analyze_palette_characteristics(dominant_colors)
                emotion_quality = self._analyze_emotional_quality(dominant_colors)
            else:
                characteristics = {"temperature": "unknown", "saturation": "unknown"}
                emotion_quality = {"quality": "unknown", "emotions": []}
                
            # Analyze color harmonies
            if harmony_analysis:
                harmony_info = self._analyze_color_harmony(dominant_colors)
            else:
                harmony_info = {"type": "unknown", "is_harmonious": False}

            # Analyze age appeal
            age_appeal = self._analyze_age_appeal(dominant_colors)

            # Analyze cultural significance
            cultural_significance = self._analyze_cultural_significance(named_colors)

            # Format emotional quality text
            emotional_text = self._format_emotional_text(emotion_quality)

            # Format text outputs
            age_appeal_text = self._format_age_appeal_text(age_appeal)
            cultural_text = self._format_cultural_text(cultural_significance)

            # Create color swatch visualization
            color_swatch = self._create_color_swatch(dominant_colors, named_colors)
            
            # Create color histogram 
            color_histogram = self._create_color_histogram(np_image, named_colors=named_colors)

            # Prepare formatted output strings
            colors_text = self._format_colors_text(named_colors)
            harmony_text = self._format_harmony_text(harmony_info)
            characteristics_text = self._format_characteristics_text(characteristics)

            # Add this before the return statement
            cultural_meanings_text = self._format_cultural_meanings_text(self._analyze_cultural_color_meanings(named_colors))
            
            # Structure complete color data
            color_data = {
                "dominant_colors": named_colors,
                "harmony": harmony_info,
                "characteristics": characteristics,
                "emotional_quality": emotion_quality,
                "age_appeal": age_appeal,
                "cultural_significance": cultural_significance
            }
            
            # Build metadata structure
            metadata = {
                'analysis': {
                    'eiqa': {
                        'color': color_data
                    }
                }
            }
            
            # Write metadata if filepath provided
            if input_filepath:
                # Set targets based on user preferences
                targets = []
                if write_to_xmp: targets.append('xmp')
                if embed_metadata: targets.append('embedded')
                if write_text_file: targets.append('txt')
                if write_to_database: targets.append('db')
                
                if targets:
                    # Set resource identifier
                    filename = os.path.basename(input_filepath)
                    resource_uri = f"file:///{filename}"
                    self.metadata_service.set_resource_identifier(resource_uri)
                    
                    # Write metadata
                    write_results = self.metadata_service.write_metadata(input_filepath, metadata, targets=targets)
                    
                    # Log results
                    if debug_logging:
                        success_targets = [t for t, success in write_results.items() if success]
                        if success_targets:
                            print(f"[ColorPalette] Successfully wrote metadata to: {', '.join(success_targets)}")
                        else:
                            print("[ColorPalette] Failed to write metadata to any target")
            
            # Save visualization images if requested
            if input_filepath and (save_color_swatch or save_color_spectrum):
                try:
                    # Get base directory and filename without extension
                    base_dir = os.path.dirname(input_filepath)
                    base_name, _ = os.path.splitext(os.path.basename(input_filepath))
                    
                    # Save color swatch
                    if save_color_swatch:
                        swatch_path = os.path.join(base_dir, f"{base_name}_color_swatch.jpg")
                        if self._save_tensor_as_jpg(color_swatch, swatch_path):
                            if debug_logging:
                                print(f"[ColorPalette] Saved color swatch to {swatch_path}")
                    
                    # Save color spectrum (histogram)
                    if save_color_spectrum:
                        spectrum_path = os.path.join(base_dir, f"{base_name}_color_spectrum.jpg")
                        if self._save_tensor_as_jpg(color_histogram, spectrum_path):
                            if debug_logging:
                                print(f"[ColorPalette] Saved color spectrum to {spectrum_path}")
                
                except Exception as e:
                    print(f"[ColorPalette] Error saving visualization images: {str(e)}")
            
            # Return results
            return (image, color_swatch, colors_text, harmony_text, characteristics_text, 
            emotional_text, age_appeal_text, cultural_text, cultural_meanings_text, color_data, color_histogram)
            
        except Exception as e:
            import traceback
            print(f"[ColorPalette] Error in color analysis: {str(e)}")
            traceback.print_exc()
            return (image, image, f"Error: {str(e)}", "Error", "Error", "Error", "Error", "Error", "Error", {}, image)
            
        finally:
            # Ensure cleanup
            self.cleanup()

    def _extract_dominant_colors(self, pil_image, num_colors=5, method="colorthief") -> List[Tuple]:
        """Extract dominant colors using the specified method"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        if (method == "colorthief"):
            return self._extract_colors_colorthief(pil_image, num_colors)
        elif (method == "histogram"):
            return self._extract_colors_histogram(pil_image, num_colors)
        elif (method == "kmeans"):
            return self._extract_colors_kmeans(pil_image, num_colors)
        else:
            # Default to ColorThief if unknown method
            return self._extract_colors_colorthief(pil_image, num_colors)

    def _extract_colors_colorthief(self, pil_image, num_colors=5) -> List[Tuple]:
        """Extract dominant colors using ColorThief without real percentages"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Create in-memory file to work with ColorThief
        img_bytes = io.BytesIO()
        pil_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Use ColorThief to extract palette
        color_thief = ColorThief(img_bytes)
        palette = color_thief.get_palette(color_count=num_colors, quality=10)
        
        # For colorthief, we'll need to calculate percentages using K-means
        img_array = np.array(pil_image)
        pixels = img_array.reshape(-1, 3)
        
        # Use k-means to get the cluster sizes
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=len(palette), random_state=0, n_init=10)
        kmeans.fit(pixels)
        
        # Count pixels in each cluster
        counts = np.bincount(kmeans.labels_, minlength=len(palette))
        total_pixels = len(kmeans.labels_)
        percentages = counts / total_pixels
        
        # Match palette colors with percentages by finding closest colors
        result = []
        for color in palette:
            distances = [np.sum((np.array(color) - centroid)**2) for centroid in kmeans.cluster_centers_]
            closest_idx = np.argmin(distances)
            result.append((color[0], color[1], color[2], float(percentages[closest_idx])))
        
        # Sort by percentage
        result.sort(key=lambda x: x[3], reverse=True)
        
        return result

    def _extract_colors_kmeans(self, pil_image, num_colors=5) -> List[Tuple]:
        """Extract dominant colors using K-means clustering"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Convert to numpy array
        img_array = np.array(pil_image)
        pixels = img_array.reshape(-1, 3)
        
        # Use k-means to find dominant colors
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init=10)
        kmeans.fit(pixels)
        
        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(int)
        
        # Count pixels in each cluster
        counts = np.bincount(kmeans.labels_, minlength=num_colors)
        total_pixels = len(kmeans.labels_)
        percentages = counts / total_pixels
        
        # Create result tuples with percentages
        result = [(int(color[0]), int(color[1]), int(color[2]), float(pct)) 
                for color, pct in zip(colors, percentages)]
        
        # Sort by percentage
        result.sort(key=lambda x: x[3], reverse=True)
        
        return result

    def _extract_colors_histogram(self, pil_image, num_colors=5) -> List[Tuple]:
        """Extract dominant colors using color histogram clustering"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Convert to numpy array
        img_array = np.array(pil_image)
        pixels = img_array.reshape(-1, 3)
        
        # Calculate total pixels
        total_pixels = pixels.shape[0]
        
        # Bin sizes for the histogram (reduce resolution to group similar colors)
        bin_size = 16  # Larger bin size to find broader color regions
        bins = np.arange(0, 256 + bin_size, bin_size)
        
        # Create 3D histogram
        hist, edges = np.histogramdd(
            pixels, 
            bins=(bins, bins, bins),
            density=False
        )
        
        # Find peaks (local maxima) in the histogram
        from scipy import ndimage
        neighborhood_size = 2
        local_max = ndimage.maximum_filter(hist, size=neighborhood_size)
        peaks = (hist == local_max) & (hist > 0)
        
        # Get coordinates and counts of peaks
        peak_coords = np.argwhere(peaks)
        peak_values = hist[peaks]
        
        # Convert bin indices to RGB values
        bin_centers = bins[:-1] + bin_size/2
        peak_colors = [(bin_centers[coord[0]], bin_centers[coord[1]], bin_centers[coord[2]]) 
                    for coord in peak_coords]
        
        # Calculate percentages
        percentages = peak_values / total_pixels
        
        # Create color tuples with percentages
        color_tuples = [(int(color[0]), int(color[1]), int(color[2]), float(pct)) 
                        for color, pct in zip(peak_colors, percentages)]
        
        # Sort by percentage
        color_tuples.sort(key=lambda x: x[3], reverse=True)
        
        # Return top N colors
        return color_tuples[:num_colors]    

    def _name_colors(self, colors_with_pct: List[Tuple]) -> List[Dict[str, Any]]:
        """Match colors to named colors using actual percentages"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        named_colors = []
        used_names = {}  # Track used color names and their RGB values
        
        for color_data in colors_with_pct:
            if len(color_data) >= 4:
                rgb = color_data[:3]
                percentage = color_data[3]
            else:
                rgb = color_data
                percentage = 0.2
            
            # Find closest color name
            color_name = self._get_closest_color_name(rgb)
            
            # Format RGB as a string
            rgb_str = f"{rgb[0]},{rgb[1]},{rgb[2]}"
            
            # Create hex color
            try:
                rgb_normalized = tuple(max(0.0, min(1.0, c/255.0)) for c in rgb)
                hex_color = rgb2hex(rgb_normalized)
            except (ValueError, TypeError) as e:
                hex_color = f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"
            
            # Handle duplicate color names
            if color_name in used_names:
                prev_rgb = [int(c) for c in used_names[color_name].split(',')]
                
                # Calculate brightness (0-1 scale)
                current_brightness = sum(rgb) / 765.0
                previous_brightness = sum(prev_rgb) / 765.0
                
                # Add appropriate qualifier based on brightness difference
                brightness_diff = current_brightness - previous_brightness
                
                if abs(brightness_diff) > 0.15:
                    # Significant brightness difference
                    prefix = "Light" if brightness_diff > 0 else "Deep" 
                    color_name = f"{prefix} {color_name}"
                else:
                    # Similar brightness, use hue comparison
                    r1, g1, b1 = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
                    r2, g2, b2 = prev_rgb[0]/255.0, prev_rgb[1]/255.0, prev_rgb[2]/255.0
                    
                    h1, s1, v1 = colorsys.rgb_to_hsv(r1, g1, b1)
                    h2, s2, v2 = colorsys.rgb_to_hsv(r2, g2, b2)
                    
                    if abs(s1 - s2) > 0.2:
                        # Different saturation
                        color_name = f"{'Vivid' if s1 > s2 else 'Muted'} {color_name}"
                    elif min(abs(h1 - h2), 1 - abs(h1 - h2)) > 0.05:
                        # Different hue - determine if warmer/cooler
                        warm_hues = h1 < 0.1 or h1 > 0.8 or (h1 > 0.5 and h1 < 0.65)
                        prev_warm_hues = h2 < 0.1 or h2 > 0.8 or (h2 > 0.5 and h2 < 0.65)
                        
                        if warm_hues != prev_warm_hues:
                            color_name = f"{'Warm' if warm_hues else 'Cool'} {color_name}" 
                        else:
                            color_name = f"Variant {color_name}"
                    else:
                        # Very similar - use numerical suffix
                        color_name = f"{color_name} (2)"
                
                # Ensure new name isn't also a duplicate
                while color_name in used_names:
                    if '(' in color_name and ')' in color_name:
                        base, num = color_name.rsplit("(", 1)
                        num = int(num.rstrip(")")) + 1
                        color_name = f"{base}({num})"
                    else:
                        color_name = f"{color_name} (2)"
            
            # Create color info
            color_info = {
                "name": color_name,
                "rgb": rgb_str,
                "hex": hex_color,
                "percentage": round(percentage, 3)
            }
            
            # Record this name as used
            used_names[color_name] = rgb_str
            named_colors.append(color_info)
        
        return named_colors
    
    def _analyze_palette_characteristics(self, colors: List[Tuple[int, int, int]]) -> Dict[str, str]:
        """Analyze palette characteristics like temperature, saturation, etc."""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        characteristics = {}
        
        # Extract just RGB values from colors (ignoring percentage if present)
        rgb_colors = []
        for color in colors:
            if len(color) >= 3:  # Make sure we have at least RGB
                rgb_colors.append(color[:3])  # Take just the first 3 values (RGB)
        
        # Calculate average HSV values
        hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in rgb_colors]
        avg_hue = np.mean([h for h, _, _ in hsv_colors])
        avg_sat = np.mean([s for _, s, _ in hsv_colors])
        avg_val = np.mean([v for _, _, v in hsv_colors])
        
        # Calculate hue variance
        hue_values = [h for h, _, _ in hsv_colors]
        hue_variance = np.var(hue_values)
        
        # Temperature (warm vs. cool)
        if 0.95 <= avg_hue < 0.1 or 0.5 <= avg_hue < 0.65:  # Red, orange, purple
            characteristics["temperature"] = "warm"
        elif 0.1 <= avg_hue < 0.5:  # Yellow, green
            characteristics["temperature"] = "neutral"
        else:  # Blue, cyan
            characteristics["temperature"] = "cool"
            
        # Saturation (vibrant, muted, pastel)
        if avg_sat < 0.3:
            if avg_val > 0.7:
                characteristics["saturation"] = "pastel"
            else:
                characteristics["saturation"] = "muted"
        elif avg_sat > 0.6:
            characteristics["saturation"] = "vibrant"
        else:
            characteristics["saturation"] = "balanced"
            
        # Contrast
        if avg_val > 0.8:
            characteristics["brightness"] = "bright"
        elif avg_val < 0.4:
            characteristics["brightness"] = "dark"
        else:
            characteristics["brightness"] = "balanced"
            
        # Hue Range (diversity of colors)
        if hue_variance < 0.01:
            characteristics["diversity"] = "monochromatic"
        elif hue_variance < 0.05:
            characteristics["diversity"] = "limited"
        elif hue_variance < 0.10:
            characteristics["diversity"] = "moderate"
        else:
            characteristics["diversity"] = "diverse"
            
        return characteristics
    
    def _analyze_color_harmony(self, colors: List[Tuple]) -> Dict[str, Any]:
        """Analyze color harmony relationships with improved accuracy"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        harmony_info = {}
        
        # Extract just RGB values
        rgb_colors = [color[:3] for color in colors if len(color) >= 3]
        
        # Skip analysis if fewer than 2 colors
        if len(rgb_colors) < 2:
            return {
                "type": "insufficient_colors",
                "score": 0.0,
                "is_harmonious": False,
                "details": {"harmony_scores": {}}
            }
        
        # Convert RGB to HSV for harmony analysis
        hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in rgb_colors]
        
        # Extract sorted hues and saturations (ignore very low saturation colors)
        # Low saturation colors (near gray) shouldn't strongly influence harmony
        hue_sat_pairs = [(h, s) for h, s, _ in hsv_colors if s > 0.1]
        
        # If no sufficiently saturated colors, return neutral result
        if len(hue_sat_pairs) < 2:
            return {
                "type": "low_saturation",
                "score": 0.5,  # Neutral score for low saturation
                "is_harmonious": True,  # Monochromatic/neutral is harmonious
                "details": {"harmony_scores": {"monochromatic": 0.5}}
            }
        
        # Sort by hue
        hue_sat_pairs.sort()
        hues = [h for h, _ in hue_sat_pairs]
        
        # Calculate hue differences (on color wheel, 0-1 scale) between adjacent hues
        adjacent_diffs = []
        for i in range(len(hues)-1):
            # Calculate difference accounting for circular nature of hue
            diff = min(abs(hues[i] - hues[i+1]), 1 - abs(hues[i] - hues[i+1]))
            adjacent_diffs.append(diff)
        
        # Calculate all pairwise differences (for complementary, etc.)
        all_diffs = []
        for i in range(len(hues)):
            for j in range(i+1, len(hues)):
                diff = min(abs(hues[i] - hues[j]), 1 - abs(hues[i] - hues[j]))
                all_diffs.append(diff)
        
        # Detect common harmony patterns with improved scoring
        
        # Monochromatic: Same hue, different saturations/values
        hue_variance = np.var(hues)
        mono_score = max(0, 1 - hue_variance * 30)  # Scale factor to normalize
        
        # Analogous: Adjacent hues (within ~30° or 0.083 in 0-1 scale)
        analogous_count = sum(1 for d in adjacent_diffs if d < 0.083)
        analogous_score = analogous_count / max(1, len(adjacent_diffs))
        
        # Complementary: Opposite hues (around 180° or 0.5 in 0-1 scale)
        complementary_scores = [1 - min(abs(d - 0.5) * 5, 1) for d in all_diffs]
        # Average of top 2 scores, or just the highest if only one score
        complementary_score = (sum(sorted(complementary_scores, reverse=True)[:min(2, len(complementary_scores))]) / 
                            min(2, len(complementary_scores)))
        
        # Triadic: Three colors equally spaced (around 120° or 0.33 in 0-1 scale)
        # Need at least 3 colors for true triadic
        triadic_score = 0
        if len(hues) >= 3:
            # Check for spacing around 120°
            triadic_matches = [1 - min(abs(d - 0.33) * 7, 1) for d in all_diffs]
            # Need at least 2 good matches for triadic (three colors = two adjacent differences)
            if len(triadic_matches) >= 2:
                top_matches = sorted(triadic_matches, reverse=True)[:2]
                triadic_score = sum(top_matches) / 2 if all(m > 0.3 for m in top_matches) else 0
        
        # Split complementary: One base color plus two colors adjacent to its complement
        split_comp_score = 0
        if len(hues) >= 3:
            # For each potential base color
            for base_hue in hues:
                # Its complement
                complement_hue = (base_hue + 0.5) % 1
                # Check if we have colors on both sides of the complement
                left_score = max([1 - min(abs(h - ((complement_hue - 0.083) % 1)) * 12, 1) for h in hues])
                right_score = max([1 - min(abs(h - ((complement_hue + 0.083) % 1)) * 12, 1) for h in hues])
                # Score is good if we have matches on both sides
                if left_score > 0.4 and right_score > 0.4:
                    split_comp_score = max(split_comp_score, (left_score + right_score) / 2)
        
        # Tetradic (Double Complementary): Two complementary pairs
        tetradic_score = 0
        if len(hues) >= 4:
            # Check all possible complementary pairs
            for i, h1 in enumerate(hues):
                for j, h2 in enumerate(hues[i+1:], i+1):
                    # If these are not complementary, skip
                    if abs(h1 - h2) % 1 < 0.4 or abs(h1 - h2) % 1 > 0.6:
                        continue
                        
                    # Look for a second complementary pair
                    for k, h3 in enumerate(hues):
                        if k == i or k == j:  # Skip the first pair
                            continue
                            
                        # Find a fourth color that would complement h3
                        h4_target = (h3 + 0.5) % 1
                        best_match = max([1 - min(abs(h - h4_target) * 12, 1) for h in hues 
                                    if hues.index(h) not in [i, j, k]])
                        
                        if best_match > 0.4:
                            pair_score = (best_match + 0.8) / 2  # Weight toward success
                            tetradic_score = max(tetradic_score, pair_score)
        
        # Square: Special case of tetradic where hues are evenly spaced (90° or 0.25)
        square_score = 0
        if len(hues) >= 4:
            # Check if we have approximately 4 evenly spaced hues
            quarter_matches = [1 - min(abs(d - 0.25) * 8, 1) for d in all_diffs]
            top_quarter_matches = sorted(quarter_matches, reverse=True)[:min(4, len(quarter_matches))]
            if len(top_quarter_matches) >= 3 and all(m > 0.3 for m in top_quarter_matches[:3]):
                square_score = sum(top_quarter_matches[:3]) / 3
        
        # Determine the dominant harmony type
        harmony_scores = {
            "monochromatic": mono_score,
            "analogous": analogous_score,
            "complementary": complementary_score,
            "triadic": triadic_score,
            "split_complementary": split_comp_score,
            "tetradic": tetradic_score,
            "square": square_score
        }
        
        # Find the strongest harmony pattern
        harmony_type = max(harmony_scores.items(), key=lambda x: x[1])
        
        # More strict threshold for determining a strong harmony (0.6 instead of 0.4)
        max_score = harmony_type[1]
        is_strong_harmony = max_score > 0.6
        
        # If no strong harmony, check for monochromatic/neutral as fallback
        if not is_strong_harmony and mono_score > 0.5:
            harmony_type = ("monochromatic", mono_score)
            is_strong_harmony = True
        
        # If still no strong harmony, label as unclassified
        if not is_strong_harmony:
            harmony_type = ("unclassified", max_score)
        
        harmony_info = {
            "type": harmony_type[0],
            "score": round(harmony_type[1], 2),
            "is_harmonious": is_strong_harmony,
            "details": {
                "harmony_scores": {
                    type_name: round(score, 2) for type_name, score in harmony_scores.items()
                }
            }
        }
        
        return harmony_info
    def _create_color_swatch(self, colors: List[Tuple[int, int, int]], 
                        named_colors: List[Dict[str, Any]]) -> torch.Tensor:
        """Create a color swatch visualization with proportional heights"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Define dimensions
        height, width = 900, 500 
        
        # Create a blank RGB image
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Sort colors by percentage (descending)
        sorted_colors = sorted(named_colors, key=lambda x: x["percentage"], reverse=True)
        
        # Calculate total height used so far
        y_position = 0
        
        # Add color blocks with height proportional to percentage
        for color_info in sorted_colors:
            rgb = self._parse_rgb(color_info["rgb"])
            name = color_info["name"]
            percentage = color_info["percentage"]
            hex_code = color_info["hex"]
            
            # Calculate block height based on percentage (minimum 10% of height for visibility)
            block_height = max(int(height * percentage), int(height * 0.10))
            
            # Ensure we don't exceed the image height
            if y_position + block_height > height:
                block_height = height - y_position
            
            # Fill color block
            y_start = y_position
            y_end = y_position + block_height
            img[y_start:y_end, :] = rgb
            
            # Add text if block is large enough
            if block_height >= 50:  # Only add text if block is tall enough
                text = f"{name} ({hex_code})"
                rgb_text = f"RGB: {rgb[0]},{rgb[1]},{rgb[2]}"
                text_color = (0, 0, 0) if sum(rgb) > 380 else (255, 255, 255)
                
                # Calculate text position
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                x_center = width // 2 - text_size[0] // 2
                y_center = y_start + (block_height // 2)
                
                # Add main text and RGB below it
                cv2.putText(img, text, (x_center, y_center), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
                
                rgb_text_size = cv2.getTextSize(rgb_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
                rgb_x_center = width // 2 - rgb_text_size[0] // 2
                cv2.putText(img, rgb_text, (rgb_x_center, y_center + 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 1)
            elif block_height >= 40:
                # Compact version for smaller blocks
                text = f"{name} ({hex_code})"
                text_color = (0, 0, 0) if sum(rgb) > 380 else (255, 255, 255)
                
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
                x_center = width // 2 - text_size[0] // 2
                y_center = y_start + (block_height // 2)
                
                cv2.putText(img, text, (x_center, y_center), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 1)
            
            # Update y position for next block
            y_position += block_height
            
            # Break if we've filled the image
            if y_position >= height:
                break
        
        # Convert to ComfyUI tensor format (BHWC)
        tensor = torch.from_numpy(img).float() / 255.0
        tensor = tensor.unsqueeze(0)
        
        return tensor
    def _analyze_age_appeal(self, dominant_colors):
        """Analyze color palette for appeal to different age groups"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Extract just RGB values
        rgb_colors = [color[:3] for color in dominant_colors if len(color) >= 3]
        
        # Convert to HSV
        hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in rgb_colors]
        
        # 1. Analyze primary color preference
        primary_hues = [0, 1/3, 2/3]  # Red, Green, Blue in HSV
        primary_score = 0
        for h, _, _ in hsv_colors:
            # Check if close to primary hues
            primary_score += min(min(abs(h - hue), 1 - abs(h - hue)) for hue in primary_hues)
        primary_score = 1 - (primary_score / len(hsv_colors) / 0.167)  # Normalize
        
        # 2. Analyze saturation (children prefer high saturation)
        saturation_score = sum(s for _, s, _ in hsv_colors) / len(hsv_colors)
        
        # 3. Analyze brightness (children prefer brighter colors)
        brightness_score = sum(v for _, _, v in hsv_colors) / len(hsv_colors)
        
        # 4. Analyze contrast between colors
        hue_variance = np.var([h for h, _, _ in hsv_colors])
        contrast_score = min(1.0, hue_variance * 10)  # Scale up, cap at 1.0
        
        # Calculate child appeal score (0-1)
        child_appeal = (primary_score * 0.4 + saturation_score * 0.3 + 
                    brightness_score * 0.2 + contrast_score * 0.1)
        
        # Calculate adult appeal score
        adult_appeal = 1 - (primary_score * 0.3 + saturation_score * 0.3 + 
                        brightness_score * 0.1 + contrast_score * 0.3)
        
        # Determine primary appeal and strength
        if child_appeal > adult_appeal:
            primary_appeal = "children"
            strength = child_appeal
        else:
            primary_appeal = "adults"
            strength = adult_appeal
        
        # Create age ranges with confidence
        age_ranges = {
            "children_under_10": child_appeal * (1.2 if child_appeal > 0.7 else 1.0),
            "teens": (child_appeal + adult_appeal) / 2,
            "adults": adult_appeal * (1.2 if adult_appeal > 0.7 else 1.0)
        }
        
        # Normalize to percentages
        total = sum(age_ranges.values())
        age_ranges = {k: round(v/total*100) for k, v in age_ranges.items()}
        
        return {
            "primary_appeal": primary_appeal,
            "strength": round(strength, 2),
            "age_distributions": age_ranges,
            "factors": {
                "primary_color_score": round(primary_score, 2),
                "saturation_score": round(saturation_score, 2),
                "brightness_score": round(brightness_score, 2),
                "contrast_score": round(contrast_score, 2)
            }
        } 

    def _analyze_cultural_significance(self, named_colors):
        """Analyze cultural significance of the color palette"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Dictionary of cultural color meanings
        cultural_meanings = {
            "red": {
                "western": ["passion", "love", "danger", "power", "excitement"],
                "chinese": ["luck", "joy", "prosperity", "celebration", "happiness"],
                "japanese": ["life", "anger", "danger", "strength"],
                "indian": ["purity", "sensuality", "spirituality", "marriage"],
                "middle_eastern": ["danger", "evil", "good luck"],
                "african": ["death", "high status", "mourning"]
            },
            "orange": {
                "western": ["energy", "warmth", "enthusiasm", "creativity"],
                "chinese": ["happiness", "love", "humility"],
                "japanese": ["happiness", "love", "courage"],
                "indian": ["courage", "sacrifice"],
                "middle_eastern": ["mourning"],
                "african": ["hospitality", "endurance"]
            },
            "yellow": {
                "western": ["happiness", "optimism", "caution", "cowardice"],
                "chinese": ["royalty", "power", "prosperity"],
                "japanese": ["courage", "cheerfulness"],
                "indian": ["learning", "knowledge", "sanctity"],
                "middle_eastern": ["happiness", "prosperity"],
                "african": ["wealth", "fertility", "royalty"]
            },
            "green": {
                "western": ["nature", "growth", "harmony", "freshness", "environmental"],
                "chinese": ["health", "prosperity", "harmony", "new life"],
                "japanese": ["life", "youth", "energy", "eternal life"],
                "indian": ["harvest", "new beginnings"],
                "middle_eastern": ["fertility", "strength", "paradise"],
                "african": ["fertility", "growth"]
            },
            "blue": {
                "western": ["trust", "calm", "stability", "peace", "loyalty"],
                "chinese": ["immortality", "healing", "heavens"],
                "japanese": ["everyday life", "purity", "passivity"],
                "indian": ["divinity", "religious observance", "truthfulness"],
                "middle_eastern": ["protection", "spirituality", "heaven", "mourning"],
                "african": ["love", "protection", "harmony"]
            },
            "purple": {
                "western": ["royalty", "luxury", "wisdom", "dignity", "mystery"],
                "chinese": ["spirituality", "divinity"],
                "japanese": ["privilege", "nobility", "wealth"],
                "indian": ["sorrow", "comfort"],
                "middle_eastern": ["wealth", "power"],
                "african": ["royalty", "wealth", "nobility"]
            },
            "pink": {
                "western": ["femininity", "romance", "compassion", "playfulness"],
                "chinese": ["love", "marriage"],
                "japanese": ["youth", "good health"],
                "indian": ["hospitality", "honor", "femininity"],
                "middle_eastern": ["joy", "femininity"],
                "african": ["gentleness", "femininity"]
            },
            "brown": {
                "western": ["earthiness", "reliability", "stability", "warmth"],
                "chinese": ["earth", "industry"],
                "japanese": ["earth", "simplicity"],
                "indian": ["mourning"],
                "middle_eastern": ["earth", "comfort"],
                "african": ["earth", "solidity"]
            },
            "white": {
                "western": ["purity", "innocence", "cleanliness", "simplicity"],
                "chinese": ["mourning", "death", "purity"],
                "japanese": ["purity", "innocence", "divinity"],
                "indian": ["peace", "purity", "knowledge"],
                "middle_eastern": ["purity", "peace", "mourning"],
                "african": ["purity", "spirituality", "peace"]
            },
            "black": {
                "western": ["power", "elegance", "sophistication", "death", "evil"],
                "chinese": ["power", "authority", "stability"],
                "japanese": ["mystery", "elegance", "formality"],
                "indian": ["evil", "darkness"],
                "middle_eastern": ["mystery", "death"],
                "african": ["maturity", "masculinity", "power"]
            },
            "gold": {
                "western": ["wealth", "success", "achievement", "luxury"],
                "chinese": ["wealth", "fortune", "prestige", "royalty"],
                "japanese": ["wealth", "prosperity"],
                "indian": ["prosperity", "wealth", "auspiciousness"],
                "middle_eastern": ["wealth", "prosperity", "prestige"],
                "african": ["wealth", "high status", "royalty"]
            },
            "silver": {
                "western": ["modernity", "sleekness", "high-tech"],
                "chinese": ["purity", "divination"],
                "japanese": ["modernity", "cleanliness"],
                "indian": ["riches", "purity"],
                "middle_eastern": ["wealth", "purity"],
                "african": ["serenity", "purity", "age"]
            }
        }
        
        # Map color names to base colors
        base_color_mapping = {
            # Reds
            'red': 'red', 'crimson': 'red', 'firebrick': 'red', 'darkred': 'red', 'maroon': 'red',
            'indian_red': 'red', 'salmon': 'red', 'light_coral': 'red', 'dark_salmon': 'red',
            'light_salmon': 'red', 'tomato': 'red',
            
            # Oranges
            'orange': 'orange', 'dark_orange': 'orange', 'coral': 'orange', 'orange_red': 'orange',
            
            # Yellows
            'yellow': 'yellow', 'light_yellow': 'yellow', 'lemon_chiffon': 'yellow', 'gold': 'gold',
            'khaki': 'yellow',
            
            # Greens
            'green': 'green', 'lime': 'green', 'lime_green': 'green', 'forest_green': 'green',
            'dark_green': 'green', 'olive': 'green', 'olive_drab': 'green', 'sea_green': 'green',
            'medium_sea_green': 'green', 'spring_green': 'green',
            
            # Blues
            'blue': 'blue', 'navy': 'blue', 'royal_blue': 'blue', 'steel_blue': 'blue',
            'dark_blue': 'blue', 'medium_blue': 'blue', 'sky_blue': 'blue', 'light_sky_blue': 'blue',
            'deep_sky_blue': 'blue', 'dodger_blue': 'blue', 'cornflower_blue': 'blue',
            'cadet_blue': 'blue',
            
            # Purples
            'purple': 'purple', 'indigo': 'purple', 'dark_magenta': 'purple', 'dark_violet': 'purple',
            'dark_orchid': 'purple', 'medium_purple': 'purple', 'medium_orchid': 'purple',
            'magenta': 'purple', 'orchid': 'purple', 'violet': 'purple', 'plum': 'purple',
            
            # Pinks
            'pink': 'pink', 'light_pink': 'pink', 'hot_pink': 'pink', 'deep_pink': 'pink',
            'pale_violet_red': 'pink', 'medium_violet_red': 'pink',
            
            # Browns
            'brown': 'brown', 'saddle_brown': 'brown', 'sienna': 'brown', 'chocolate': 'brown',
            'peru': 'brown', 'sandy_brown': 'brown', 'burly_wood': 'brown', 'tan': 'brown',
            
            # Whites
            'white': 'white', 'snow': 'white', 'honeydew': 'white', 'mint_cream': 'white',
            'azure': 'white', 'alice_blue': 'white', 'ghost_white': 'white', 'white_smoke': 'white',
            'seashell': 'white', 'beige': 'white',
            
            # Grays/Silvers
            'gainsboro': 'silver', 'light_gray': 'silver', 'silver': 'silver', 'dark_gray': 'silver',
            'gray': 'silver', 'dim_gray': 'silver', 'light_slate_gray': 'silver',
            'slate_gray': 'silver',
            
            # Blacks
            'black': 'black', 'dark_slate_gray': 'black'
        }
        
        # Analyze each color in the palette
        cultural_analysis = {}
        color_counts = {}
        
        for color_info in named_colors:
            color_name = color_info["name"].lower().replace('-', '_')
            base_color = base_color_mapping.get(color_name)
            
            # Skip colors we can't map
            if not base_color or base_color not in cultural_meanings:
                continue
                
            # Count color frequencies
            if base_color not in color_counts:
                color_counts[base_color] = 0
            color_counts[base_color] += 1
            
            # Map cultural meanings
            for culture, meanings in cultural_meanings[base_color].items():
                if culture not in cultural_analysis:
                    cultural_analysis[culture] = {"meanings": [], "colors": [], "count": 0}
                
                cultural_analysis[culture]["meanings"].extend(meanings)
                if base_color not in cultural_analysis[culture]["colors"]:
                    cultural_analysis[culture]["colors"].append(base_color)
                cultural_analysis[culture]["count"] += 1
        
        # Calculate cultural significance scores
        results = {}
        total_colors = sum(color_counts.values())
        
        if total_colors > 0:
            for culture, data in cultural_analysis.items():
                # Calculate score based on color coverage and meaning diversity
                color_coverage = len(data["colors"]) / len(color_counts)
                meaning_diversity = len(set(data["meanings"])) / 10  # Normalize
                
                significance_score = (color_coverage * 0.7 + meaning_diversity * 0.3)
                
                # Format final results
                results[culture] = {
                    "score": round(significance_score, 2),
                    "meanings": list(set(data["meanings"])),
                    "colors": data["colors"]
                }
        
        # Sort cultures by significance score
        sorted_cultures = sorted(results.items(), key=lambda x: x[1]["score"], reverse=True)
        
        # Return formatted results
        if sorted_cultures:
            return {
                "primary_culture": sorted_cultures[0][0],
                "primary_score": sorted_cultures[0][1]["score"],
                "cultures": {culture: data for culture, data in sorted_cultures}
            }
        else:
            return {
                "primary_culture": "unknown",
                "primary_score": 0,
                "cultures": {}
            }          

    def _format_age_appeal_text(self, age_info: Dict[str, Any]) -> str:
        """Format age appeal information as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        primary_appeal = age_info["primary_appeal"].title()
        strength = age_info["strength"]
        distributions = age_info["age_distributions"]
        
        lines = [
            "Age Appeal Analysis:",
            f"Primary Appeal: {primary_appeal}",
            f"Appeal Strength: {strength:.2f}/1.0",
            "Age Distributions:",
        ]
        
        for age_group, percentage in distributions.items():
            lines.append(f"  • {age_group.replace('_', ' ').title()}: {percentage}%")
        
        return "\n".join(lines)

    def _format_cultural_text(self, cultural_info: Dict[str, Any]) -> str:
        """Format cultural significance information as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        primary_culture = cultural_info["primary_culture"].title()
        primary_score = cultural_info["primary_score"]
        
        lines = [
            "Cultural Color Significance:",
            f"Primary Cultural Resonance: {primary_culture}",
            f"Significance Score: {primary_score:.2f}/1.0",
            "Cultural Meanings:"
        ]
        
        # Add top 2 cultures and their meanings
        cultures = list(cultural_info["cultures"].items())[:2]
        for culture_name, culture_data in cultures:
            meanings = culture_data["meanings"][:5]  # Limit to top 5 meanings
            lines.append(f"  • {culture_name.title()}: {', '.join(meanings)}")
        
        return "\n".join(lines)
    def _tensor_to_pil(self, np_image) -> Image.Image:
        """Convert numpy array to PIL Image"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Ensure proper format and data type
        if np_image.dtype != np.uint8:
            np_image = np.clip(np_image * 255, 0, 255).astype(np.uint8)
            
        # Convert to PIL
        pil_image = Image.fromarray(np_image)
        return pil_image
    

    def _analyze_emotional_quality(self, dominant_colors):
        """Analyze the emotional quality of the color palette"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Extract just RGB values
        rgb_colors = [color[:3] for color in dominant_colors if len(color) >= 3]
        
        # Convert to HSV
        hsv_colors = [colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in rgb_colors]
        
        # Calculate overall warmth (reds/oranges/yellows are warm)
        warmth = sum(1 if (h < 0.2 or h > 0.8) else 0 for h, s, v in hsv_colors) / len(hsv_colors)
        
        # Calculate overall saturation and value
        avg_saturation = sum(s for _, s, _ in hsv_colors) / len(hsv_colors)
        avg_value = sum(v for _, _, v in hsv_colors) / len(hsv_colors)
        
        # More saturated, warm colors with high value tend to feel "major"
        # Less saturated, cool colors or colors with low value tend to feel "minor"
        major_score = warmth * 0.4 + avg_saturation * 0.3 + avg_value * 0.3
        
        emotion_info = {
            "quality": "major" if major_score > 0.6 else "minor" if major_score < 0.4 else "neutral",
            "score": round(major_score if major_score > 0.5 else 1 - major_score, 2),
            "major_score": round(major_score, 2),
            "details": {
                "warmth": round(warmth, 2),
                "avg_saturation": round(avg_saturation, 2),
                "avg_value": round(avg_value, 2)
            }
        }
        
        # Add emotional descriptions
        emotion_mapping = {
            "major": ["cheerful", "energetic", "optimistic"] if major_score > 0.8 else 
                    ["positive", "pleasant", "uplifting"],
            "minor": ["melancholic", "serious", "mysterious"] if major_score < 0.2 else 
                    ["calm", "subdued", "introspective"],
            "neutral": ["balanced", "moderate", "versatile"]
        }
        
        emotion_info["emotions"] = emotion_mapping[emotion_info["quality"]]
        
        return emotion_info

    def _get_closest_color_name(self, rgb: Tuple[int, int, int]) -> str:
        """Find the closest named color using HSV color space for better perceptual matching"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        min_distance = float('inf')
        closest_name = "unknown"
        
        # Convert RGB to HSV
        r, g, b = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
        target_hsv = colorsys.rgb_to_hsv(r, g, b)
        
        # Give more weight to hue differences than saturation or value
        h_weight, s_weight, v_weight = 5.0, 1.0, 1.0
        
        for name, name_rgb in self.color_names.items():
            # Convert named color to HSV
            r, g, b = name_rgb[0]/255.0, name_rgb[1]/255.0, name_rgb[2]/255.0
            name_hsv = colorsys.rgb_to_hsv(r, g, b)
            
            # Calculate distance in HSV space with special handling for hue's circular nature
            h_diff = min(abs(target_hsv[0] - name_hsv[0]), 1 - abs(target_hsv[0] - name_hsv[0]))
            s_diff = abs(target_hsv[1] - name_hsv[1])
            v_diff = abs(target_hsv[2] - name_hsv[2])
            
            # Weighted distance
            distance = h_weight * h_diff + s_weight * s_diff + v_weight * v_diff
            
            if distance < min_distance:
                min_distance = distance
                closest_name = name
        
        return closest_name
        
    def _analyze_cultural_color_meanings(self, named_colors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cultural meanings of colors in the palette"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        # Initialize results
        result = {
            "cultures": {},
            "concepts": {},
            "dominant_concepts": []
        }
        
        # Initialize match count to fix the undefined variable error
        match_count = 0
        
        # Debug check for RGB_CULTURE_CONCEPTS
        if not RGB_CULTURE_CONCEPTS:
            print("[ColorPalette] Warning: RGB_CULTURE_CONCEPTS dictionary or list is empty")
            return result

        # Only print the debug info when debug_logging is enabled
        if debug_output:
            print(f"[ColorPalette] Debug: RGB_CULTURE_CONCEPTS data type: {type(RGB_CULTURE_CONCEPTS)}")
            # Rest of the debug prints...
        if isinstance(RGB_CULTURE_CONCEPTS, list) and len(RGB_CULTURE_CONCEPTS) > 0:
            print(f"[ColorPalette] Debug: First item type: {type(RGB_CULTURE_CONCEPTS[0])}")
            # Print a sample item or its keys if it's a dictionary
            if hasattr(RGB_CULTURE_CONCEPTS[0], 'keys'):
                print(f"[ColorPalette] Debug: Sample keys: {list(RGB_CULTURE_CONCEPTS[0].keys())[:3]}")
        
        # Initialize culture scores
        cultures = ["western american", "japanese", "hindu", "native american", 
                    "chinese", "asian", "eastern european", "arab", 
                    "african", "south american"]
        
        for culture in cultures:
            result["cultures"][culture] = {
                "concepts": {},
                "score": 0.0
            }
        
        # Process each detected color
        for color_info in named_colors:
            rgb = self._parse_rgb(color_info["rgb"])
            percentage = color_info["percentage"]
            
            # Extract RGB values from the culture data structure
            if isinstance(RGB_CULTURE_CONCEPTS, dict):
                # If it's a dictionary, we use the keys (assuming keys are RGB tuples)
                rgb_tuples = list(RGB_CULTURE_CONCEPTS.keys())
                
                # Find closest match
                closest_rgb = self._find_closest_rgb_match(rgb, rgb_tuples)
                
                if closest_rgb and closest_rgb in RGB_CULTURE_CONCEPTS:
                    color_data = RGB_CULTURE_CONCEPTS[closest_rgb]
                    match_count += 1
                    
                    # Process color meanings
                    self._process_color_cultural_meanings(color_data, percentage, result)
            
            elif isinstance(RGB_CULTURE_CONCEPTS, list):
                # For list, we need to extract RGB values from each item
                # This is a workaround - we don't know the exact structure
                # Common patterns would be: [{rgb: (r,g,b), data:...}, ...] or [((r,g,b), data), ...]
                
                # Let's try to handle both dictionary and tuple formats
                closest_item = None
                min_distance = float('inf')
                
                for item in RGB_CULTURE_CONCEPTS:
                    # Try to extract RGB values based on common formats
                    item_rgb = None
                    
                    if isinstance(item, dict) and 'rgb' in item:
                        # Format {rgb: (r,g,b), ...}
                        item_rgb = item['rgb']
                    elif isinstance(item, tuple) and len(item) >= 1:
                        # Format ((r,g,b), ...)
                        if isinstance(item[0], tuple) and len(item[0]) == 3:
                            item_rgb = item[0]
                    
                    # Skip if we couldn't extract RGB
                    if not item_rgb:
                        continue
                    
                    # Calculate distance
                    try:
                        converted_rgb = tuple(int(val) if isinstance(val, (int, float)) else 0 for val in rgb[:3])
                        distance = sum((t - r) ** 2 for t, r in zip(converted_rgb, item_rgb))
                        if distance < min_distance:
                            min_distance = distance
                            closest_item = item
                    except TypeError:
                        # If there's a type error, skip this item
                        print(f"[ColorPalette] Warning: Invalid RGB format in culture data: {item_rgb}")
                        continue
                
                # Process the closest item if found
                if closest_item:
                    match_count += 1
                    
                    # Extract color data based on structure
                    color_data = None
                    if isinstance(closest_item, dict):
                        # The whole item is the data
                        color_data = closest_item
                    elif isinstance(closest_item, tuple) and len(closest_item) > 1:
                        # Second element is the data
                        color_data = closest_item[1]
                    
                    if color_data:
                        self._process_color_cultural_meanings(color_data, percentage, result)
        
        # Rest of the method remains the same...
        return result

    def _process_color_cultural_meanings(self, color_data, percentage, result):
        """Helper to process color cultural meanings"""
        # Only process if color_data is a dictionary with culture keys
        if not isinstance(color_data, dict):
            return
            
        # Process each culture and its concepts
        for culture, concepts in color_data.items():
            if culture not in result["cultures"]:
                continue
                
            # Skip if concepts isn't a list or iterable
            if not hasattr(concepts, '__iter__'):
                continue
                
            for concept in concepts:
                # Add concept with weight
                if concept not in result["cultures"][culture]["concepts"]:
                    result["cultures"][culture]["concepts"][concept] = 0
                    
                result["cultures"][culture]["concepts"][concept] += percentage
                
                # Also track concepts globally
                if concept not in result["concepts"]:
                    result["concepts"][concept] = 0
                result["concepts"][concept] += percentage

    def _find_closest_rgb_match(self, target_rgb: Tuple[int, int, int], 
                            rgb_values: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
        """Find the closest RGB match from a list of RGB values"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        if not rgb_values:
            return None
            
        min_distance = float('inf')
        closest_match = None
        
        for rgb in rgb_values:
            if rgb is None:
                continue
                
            # Skip if rgb isn't the right type or length
            if not hasattr(rgb, '__len__') or len(rgb) < 3:
                continue
                
            # Ensure all elements are integers
            try:
                converted_rgb = tuple(int(val) if isinstance(val, (int, float)) else 0 for val in rgb[:3])
                
                # Calculate Euclidean distance
                distance = sum((t - r) ** 2 for t, r in zip(target_rgb, converted_rgb))
                
                if distance < min_distance:
                    min_distance = distance
                    closest_match = rgb
            except (TypeError, ValueError):
                # Skip values that can't be converted to int
                continue
        
        return closest_match    
    def _format_colors_text(self, named_colors: List[Dict[str, Any]]) -> str:
        """Format color information as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        lines = ["Dominant Colors:"]
        
        for i, color_info in enumerate(named_colors):  # Changed from "for i, color_info in named_colors:"
            name = color_info["name"]
            hex_code = color_info["hex"]
            percentage = color_info["percentage"] * 100
            
            lines.append(f"{i+1}. {name.title()} ({hex_code}) - {percentage:.0f}%")
            
        return "\n".join(lines)
    
    def _format_harmony_text(self, harmony_info: Dict[str, Any]) -> str:
        """Format harmony information as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        harmony_type = harmony_info["type"].title()
        score = harmony_info["score"]
        is_harmonious = harmony_info["is_harmonious"]
        
        harmony_descriptions = {
            "Complementary": "Colors from opposite sides of the color wheel",
            "Analogous": "Colors that are adjacent to each other on the color wheel",
            "Triadic": "Three colors that are evenly spaced around the color wheel",
            "Tetradic": "Four colors arranged into two complementary pairs",
            "Monochromatic": "Different tones, tints and shades of a single color",
            "Unclassified": "No strong color harmony pattern detected"
        }
        
        harmony_description = harmony_descriptions.get(harmony_type, "")
        
        lines = [
            "Color Harmony:",
            f"Type: {harmony_type} ({harmony_description})",
            f"Harmony Score: {score:.2f}/1.0",
            f"Assessment: {'Harmonious' if is_harmonious else 'Not strongly harmonious'}"
        ]
        
        return "\n".join(lines)
    
    def _format_characteristics_text(self, characteristics: Dict[str, str]) -> str:
        """Format palette characteristics as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        lines = ["Color Palette Characteristics:"]
        
        for characteristic, value in characteristics.items():
            lines.append(f"{characteristic.title()}: {value.title()}")
            
        return "\n".join(lines)
    
    def _format_emotional_text(self, emotion_info: Dict[str, Any]) -> str:
        """Format emotional quality information as text"""
        debug_output = self.metadata_service.debug if hasattr(self, 'metadata_service') else False
        if debug_output:
            print("Debug information...")
        quality = emotion_info["quality"].title()
        score = emotion_info["score"]
        emotions = ", ".join(emotion_info["emotions"])
        
        emotion_descriptions = {
            "Major": "Bright, cheerful palette similar to a major chord in music",
            "Minor": "Subdued, serious palette similar to a minor chord in music",
            "Neutral": "Balanced palette without strong emotional direction"
        }
        
        description = emotion_descriptions.get(quality, "")
        
        lines = [
            "Emotional Quality:",
            f"Type: {quality} ({description})",
            f"Strength: {score:.2f}/1.0",
            f"Associated Emotions: {emotions}"
        ]
        
        return "\n".join(lines)
    def _create_color_histogram(self, np_image, num_bins=100, named_colors=None) -> torch.Tensor:
        """Create a color histogram visualization across the visible spectrum"""
        # Downsample image if it's too large (>1/4 megapixel)
        height, width = np_image.shape[:2]
        pixel_count = height * width
        
        if pixel_count > 250000:  # 1/4 megapixel
            scale_factor = np.sqrt(250000 / pixel_count)
            new_height = int(height * scale_factor)
            new_width = int(width * scale_factor)
            np_image = cv2.resize(np_image, (new_width, new_height))
        
        # Create figure for histogram with explicit dimensions and higher DPI
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        
        # Reshape image for processing
        pixels = np_image.reshape(-1, 3)
        
        # Create bins for the hue spectrum (0 to 1)
        hue_bins = np.linspace(0, 1, num_bins + 1)
        
        # Initialize histogram counts
        hist_values = np.zeros(num_bins)
        
        # Track total saturation and value for each bin to calculate averages
        sat_sum = np.zeros(num_bins)
        val_sum = np.zeros(num_bins)
        counts = np.zeros(num_bins)
        
        # Process each pixel
        for pixel in pixels:
            # Convert RGB (0-255) to HSV (0-1)
            r, g, b = pixel[0]/255.0, pixel[1]/255.0, pixel[2]/255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            
            # Only consider pixels with sufficient saturation and value
            if s > 0.1 and v > 0.15:
                # Find the bin for this hue
                bin_idx = min(int(h * num_bins), num_bins - 1)
                
                # Increment count and accumulate S and V values
                hist_values[bin_idx] += 1
                sat_sum[bin_idx] += s
                val_sum[bin_idx] += v
                counts[bin_idx] += 1

        # If we have no data at all (might happen with fully grayscale images)
        if np.sum(counts) == 0:
            # Create a neutral distribution
            hist_values = np.ones(num_bins) * 0.1
            avg_sat = np.ones(num_bins) * 0.2
            avg_val = np.ones(num_bins) * 0.5
        
        # Calculate average saturation and value for each bin
        avg_sat = np.zeros(num_bins)
        avg_val = np.zeros(num_bins)
        
        for i in range(num_bins):
            if counts[i] > 0:
                avg_sat[i] = sat_sum[i] / counts[i]
                avg_val[i] = val_sum[i] / counts[i]
            else:
                # Default values for empty bins
                avg_sat[i] = 0.7
                avg_val[i] = 0.7
        
        # Normalize histogram for better visibility - make tallest column 95% of height
        if np.max(hist_values) > 0:
            hist_values = hist_values / np.max(hist_values) * 0.95
        
        # Create the histogram with bars colored by their position in the spectrum
        for i in range(num_bins):
            # Use the center of each bin for the hue
            hue = (hue_bins[i] + hue_bins[i+1]) / 2
            
            # Use the average saturation and value, but ensure minimum visibility
            sat = min(max(avg_sat[i], 0.4), 0.9)
            val = min(max(avg_val[i], 0.5), 0.9)
            
            # Convert HSV to RGB for matplotlib
            r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
            
            # Plot the bar
            ax.bar(i, hist_values[i], width=1.0, color=(r, g, b), edgecolor=None, alpha=0.9)
        
        # Add markers for the dominant colors if provided
        if named_colors:
            marker_height = 1.03  # Above the top of the plot
            for color_info in named_colors:
                rgb = self._parse_rgb(color_info["rgb"])
                
                # Convert RGB to HSV
                r, g, b = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                
                # Find bin index
                bin_idx = min(int(h * num_bins), num_bins - 1)
                
                # Draw triangle marker
                marker_size = 10
                ax.plot(bin_idx, marker_height, 'v', color=(r, g, b), 
                       markersize=marker_size, markeredgecolor='white')
        
        # Setup the plot
        ax.set_xlim(0, num_bins)
        ax.set_ylim(0, 1.10)  # Increase slightly for markers
        ax.set_title('Color Spectrum Distribution', fontsize=14)
        ax.set_xticks([])  # Hide x-axis ticks
        ax.set_yticks([])  # Hide y-axis ticks
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Add color spectrum along x-axis
        spectrum_height = 0.05
        for i in range(num_bins):
            hue = i / num_bins
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            ax.add_patch(plt.Rectangle((i, -spectrum_height), 1, spectrum_height, 
                                    color=(r, g, b), alpha=0.8))
        
        plt.subplots_adjust(bottom=0.1)
        
        # Convert to PIL Image first (more reliable)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        
        # Open as PIL Image and convert to numpy array
        pil_img = Image.open(buf).convert('RGB')
        img_array = np.array(pil_img)
        
        # Convert to tensor with proper normalization
        tensor = torch.from_numpy(img_array).float() / 255.0
        
        # Ensure batch dimension for ComfyUI (BHWC format)
        if len(tensor.shape) == 3:  # HWC format
            tensor = tensor.unsqueeze(0)  # Add batch dimension -> BHWC
        
        plt.close(fig)
        buf.close()
        return tensor
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
        
        # Close any matplotlib figures
        plt.close('all')
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

    def _save_tensor_as_jpg(self, tensor, filepath):
        """Save a tensor as a JPG image"""
        try:
            # Convert tensor to numpy array
            if tensor.shape[0] == 1:
                # Remove batch dimension if present
                np_image = tensor[0].cpu().numpy()
            else:
                np_image = tensor.cpu().numpy()
            
            # Ensure values are in 0-255 range
            if np_image.max() <= 1.0:
                np_image = (np_image * 255).astype(np.uint8)
            else:
                np_image = np.clip(np_image, 0, 255).astype(np.uint8)
            
            # Convert to PIL and save
            Image.fromarray(np_image).save(filepath, 'JPEG', quality=95)
            return True
        except Exception as e:
            print(f"[ColorPalette] Error saving image to {filepath}: {str(e)}")
            return False

    def _format_cultural_meanings_text(self, cultural_meanings: Dict[str, Any]) -> str:
        """Format cultural meanings information as text"""
        lines = ["Cultural Color Meanings:"]
        
        # Check if we have culture data
        if not cultural_meanings or "cultures" not in cultural_meanings:
            lines.append("  No cultural meanings found")
            return "\n".join(lines)
        
        # Add top concepts
        if "concepts" in cultural_meanings and cultural_meanings["concepts"]:
            lines.append("Global Concepts:")
            sorted_concepts = sorted(cultural_meanings["concepts"].items(), 
                                    key=lambda x: x[1], reverse=True)[:5]
            for concept, score in sorted_concepts:
                lines.append(f"  • {concept.title()}: {score:.2f}")
        
        # Add per-culture concepts
        lines.append("Cultural Associations:")
        for culture_name, culture_data in cultural_meanings["cultures"].items():
            # Skip cultures with no concepts or zero score
            if not culture_data["concepts"] or culture_data["score"] == 0:
                continue
                
            lines.append(f"  {culture_name.title()} (Score: {culture_data['score']:.2f}):")
            
            # Get top concepts
            sorted_concepts = sorted(culture_data["concepts"].items(), 
                                  key=lambda x: x[1], reverse=True)[:3]
            for concept, score in sorted_concepts:
                lines.append(f"    - {concept.title()}: {score:.2f}")
        
        return "\n".join(lines)

    def _parse_rgb(self, rgb_value):
        """Convert various RGB formats to a tuple of integers"""
        if isinstance(rgb_value, str):
            return tuple(int(c) for c in rgb_value.split(','))
        elif hasattr(rgb_value, '__len__') and len(rgb_value) >= 3:
            return tuple(int(c) for c in rgb_value[:3])
        else:
            return (0, 0, 0)  # Default fallback

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Color_Palette_Analyzer_v3": Eric_Color_Palette_Analyzer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Color_Palette_Analyzer_v3": "Eric's Color Palette Analyzer_v3"
}