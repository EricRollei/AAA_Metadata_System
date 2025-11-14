"""
Version: 0.2.0

Date: [May 2025]
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

import torch
import numpy as np
import cv2
from PIL import Image
from typing import Tuple, List, Optional, Dict

class SmartImageCropper:
    """
    ComfyUI Node for intelligent image cropping using adaptive detection methods.
    Automatically analyzes images and applies optimal cropping strategies.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "crop_mode": ([
                    "auto",           # Smart adaptive detection
                    "conservative",   # When auto is too aggressive
                    "aggressive"      # When auto is too conservative
                ], {
                    "default": "auto",
                    "tooltip": "Auto uses intelligent detection, others are manual overrides when needed"
                }),
                "multi_image_handling": ([
                    "largest_only",   # Return only the largest detected image
                    "best_quality",   # Return the highest quality image based on content analysis
                    "first_found"     # Return the first valid image found
                ], {
                    "default": "largest_only",
                    "tooltip": "How to handle multiple images: largest_only picks biggest area, best_quality analyzes content"
                }),
                "min_crop_ratio": ("FLOAT", {
                    "default": 0.05,
                    "min": 0.01,
                    "max": 0.5,
                    "step": 0.01,
                    "tooltip": "Minimum crop size as ratio of original (prevents over-cropping)"
                }),
            },
            "optional": {
                "debug_mode": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Print detailed analysis and decision information"
                }),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("cropped_image",)
    FUNCTION = "smart_crop"
    CATEGORY = "Eric/Image Processing"
    
    DESCRIPTION = """
    Smart Image Cropper - Intelligent content detection and cropping
    
    Automatically detects and crops rectangular images from:
    • Scanned documents and book pages
    • Magazine layouts with embedded photos
    • Museum photos with framed artwork
    • Composite images with borders
    
    Features:
    • Adaptive parameter selection based on image analysis
    • Automatic text caption exclusion
    • Multiple detection strategies with intelligent scoring
    • Handles various background types and lighting conditions
    • Multi-image detection with intelligent selection
    
    Modes:
    • Auto: Analyzes image characteristics and applies optimal strategy
    • Conservative: Manual override when auto crops too aggressively
    • Aggressive: Manual override when auto is too cautious
    
    Multi-Image Handling:
    • Largest Only: Returns the biggest detected image (good for main content)
    • Best Quality: Analyzes content quality and returns the richest image
    • First Found: Returns the first valid image (fastest processing)
    """
    
    def __init__(self):
        self.debug_mode = False
        self.min_crop_ratio = 0.05
        self.multi_image_handling = "largest_only"
    
    def smart_crop(self, image, crop_mode="auto", multi_image_handling="largest_only", 
                   min_crop_ratio=0.05, debug_mode=False):
        """Main cropping function with intelligent adaptive detection and multi-image support"""
        self.debug_mode = debug_mode
        self.min_crop_ratio = min_crop_ratio
        self.multi_image_handling = multi_image_handling
        
        # Convert ComfyUI tensor to PIL Image
        pil_image = self._tensor_to_pil(image)
        
        if self.debug_mode:
            print(f"\n{'='*60}")
            print(f"SMART IMAGE CROPPER - {crop_mode.upper()} MODE")
            print(f"Multi-image handling: {multi_image_handling.upper()}")
            print(f"{'='*60}")
            print(f"Input: {pil_image.width}x{pil_image.height}")
        
        # Convert to numpy for processing
        img_array = np.array(pil_image)
        
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Intelligent cropping pipeline with multi-image detection
        if crop_mode == "auto":
            cropped_pil = self._intelligent_auto_crop_multi(pil_image, gray)
        elif crop_mode == "conservative":
            cropped_pil = self._conservative_crop_multi(pil_image, gray)
        elif crop_mode == "aggressive":
            cropped_pil = self._aggressive_crop_multi(pil_image, gray)
        else:
            cropped_pil = pil_image
        
        if self.debug_mode:
            original_area = pil_image.width * pil_image.height
            cropped_area = cropped_pil.width * cropped_pil.height
            reduction = ((original_area - cropped_area) / original_area) * 100
            print(f"Output: {cropped_pil.width}x{cropped_pil.height}")
            print(f"Reduction: {reduction:.1f}%")
            print(f"{'='*60}")
        
        # Convert back to ComfyUI tensor
        return (self._pil_to_tensor(cropped_pil),)
    
    def _intelligent_auto_crop_multi(self, image: Image.Image, gray: np.ndarray) -> Image.Image:
        """Intelligent adaptive cropping with multi-image detection and selection"""
        
        # Step 1: Analyze image characteristics
        image_type, characteristics = self._analyze_image_characteristics(gray)
        
        if self.debug_mode:
            print(f"Image type detected: {image_type}")
            print(f"Characteristics: {characteristics}")
        
        # NEW: Check if image needs cropping at all
        needs_cropping = self._assess_cropping_necessity(image, gray, characteristics)
        
        if not needs_cropping:
            if self.debug_mode:
                print("✅ Image appears to be already well-cropped - no processing needed")
            return image
        
        # Step 2: Get adaptive parameters based on analysis
        params = self._get_adaptive_parameters(image_type, characteristics)
        
        if self.debug_mode:
            print(f"Using adaptive parameters for {image_type}")
        
        # Step 3: Detect ALL potential image regions
        all_image_regions = self._detect_all_image_regions(image, gray, params)
        
        if self.debug_mode:
            print(f"Found {len(all_image_regions)} potential image regions")
            for i, (method, region_image, score, area) in enumerate(all_image_regions):
                print(f"  Region {i+1}: {region_image.width}x{region_image.height} "
                    f"(method: {method}, score: {score:.3f}, area: {area})")
        
        # Step 4: Select the best region, but validate it's actually better
        if not all_image_regions:
            if self.debug_mode:
                print("No valid image regions found, returning original")
            return image
        
        best_region = self._select_best_region(all_image_regions, characteristics)
        
        # NEW: Validate that the crop is actually beneficial
        is_beneficial = self._validate_crop_benefit(image, best_region[1], characteristics)
        
        if not is_beneficial:
            if self.debug_mode:
                print("❌ Proposed crop doesn't improve the image - keeping original")
            return image
        
        if self.debug_mode:
            method, selected_image, score, area = best_region
            print(f"✅ Selected beneficial crop: {selected_image.width}x{selected_image.height} "
                f"(method: {method}, score: {score:.3f})")
        
        return best_region[1]

    def _assess_cropping_necessity(self, image: Image.Image, gray: np.ndarray, characteristics: Dict) -> bool:
        """Assess whether the image actually needs cropping"""
        
        # Check 1: Image content distribution
        content_is_centered = self._check_content_distribution(gray)
        
        # Check 2: Border analysis - look for significant empty borders
        has_significant_borders = self._check_border_significance(gray)
        
        # Check 3: Check for obvious cropping markers (like frames, borders, text areas)
        has_cropping_markers = self._check_cropping_markers(gray, characteristics)
        
        if self.debug_mode:
            print(f"  Cropping assessment:")
            print(f"    Content centered: {'No' if content_is_centered else 'Yes'}")
            print(f"    Significant borders: {'Yes' if has_significant_borders else 'No'}")
            print(f"    Cropping markers: {'Yes' if has_cropping_markers else 'No'}")
        
        # Decision: Need cropping if ANY indicator suggests it
        needs_cropping = (not content_is_centered or 
                        has_significant_borders or 
                        has_cropping_markers)
        
        return needs_cropping

    def _check_content_distribution(self, gray: np.ndarray) -> bool:
        """Check if content is well-distributed (not needing crop)"""
        h, w = gray.shape
        
        # Divide image into 9 regions (3x3 grid)
        regions = []
        for i in range(3):
            for j in range(3):
                y1, y2 = i * h // 3, (i + 1) * h // 3
                x1, x2 = j * w // 3, (j + 1) * w // 3
                region = gray[y1:y2, x1:x2]
                
                # Calculate content density (variance as proxy for content)
                content_density = np.var(region)
                regions.append(content_density)
        
        # Check if content is reasonably distributed
        # Center region (index 4) should have content, but so should others
        center_content = regions[4]
        edge_content = np.mean([regions[0], regions[2], regions[6], regions[8]])  # corners
        border_content = np.mean([regions[1], regions[3], regions[5], regions[7]])  # edges
        
        # If center has much more content than edges, might need cropping
        center_dominance = center_content / (edge_content + 1)
        
        # Well-distributed if center doesn't dominate too much
        is_well_distributed = center_dominance < 5.0  # Threshold for "centered" content
        
        if self.debug_mode:
            print(f"    Content distribution - Center dominance: {center_dominance:.2f}")
        
        return is_well_distributed

    def _check_border_significance(self, gray: np.ndarray) -> bool:
        """Check for significant empty/uniform borders that suggest cropping needed"""
        h, w = gray.shape
        
        # Check border thickness and uniformity
        border_thickness = min(50, min(h, w) // 10)  # Up to 10% of image
        
        # Analyze each border
        borders = {
            'top': gray[:border_thickness, :],
            'bottom': gray[-border_thickness:, :],
            'left': gray[:, :border_thickness],
            'right': gray[:, -border_thickness:]
        }
        
        significant_borders = 0
        for border_name, border in borders.items():
            # Calculate uniformity (low variance = uniform)
            uniformity = 1.0 - (np.std(border) / 255.0)
            
            # Calculate relative size
            border_area = border.size
            total_area = gray.size
            border_ratio = border_area / total_area
            
            # Significant if uniform and substantial
            if uniformity > 0.8 and border_ratio > 0.05:  # 80% uniform, >5% of image
                significant_borders += 1
                
                if self.debug_mode:
                    print(f"    Significant {border_name} border: uniformity={uniformity:.2f}, size={border_ratio:.2f}")
        
        return significant_borders >= 2  # At least 2 significant borders

    def _check_cropping_markers(self, gray: np.ndarray, characteristics: Dict) -> bool:
        """Check for obvious markers that cropping is needed"""
        
        # Marker 1: Text regions (captions, titles) that should be excluded
        has_text_to_exclude = characteristics['text_likelihood'] > 0.2
        
        # Marker 2: Very high background uniformity with content islands
        has_content_islands = (characteristics['background_uniformity'] > 0.85 and 
                            characteristics['texture_score'] > 0.3)
        
        # Marker 3: Edge density suggests framed content
        has_frame_indicators = characteristics['edge_density'] > 0.12
        
        # Marker 4: High contrast suggests clear subject/background separation
        has_clear_separation = characteristics['contrast_level'] > 80
        
        markers_found = sum([
            has_text_to_exclude,
            has_content_islands, 
            has_frame_indicators,
            has_clear_separation
        ])
        
        if self.debug_mode:
            print(f"    Cropping markers found: {markers_found}/4")
            if has_text_to_exclude:
                print(f"      - Text to exclude (likelihood: {characteristics['text_likelihood']:.2f})")
            if has_content_islands:
                print(f"      - Content islands (uniformity: {characteristics['background_uniformity']:.2f})")
            if has_frame_indicators:
                print(f"      - Frame indicators (edge density: {characteristics['edge_density']:.2f})")
            if has_clear_separation:
                print(f"      - Clear separation (contrast: {characteristics['contrast_level']:.1f})")
        
        return markers_found >= 2  # Need at least 2 markers to suggest cropping

    def _validate_crop_benefit(self, original: Image.Image, cropped: Image.Image, characteristics: Dict) -> bool:
        """Validate that the proposed crop actually improves the image"""
        
        # Check 1: Size reduction should be meaningful
        original_area = original.width * original.height
        cropped_area = cropped.width * cropped.height
        reduction_ratio = (original_area - cropped_area) / original_area
        
        # Check 2: Don't crop too little (probably noise) or too much (probably wrong)
        if reduction_ratio < 0.05:  # Less than 5% reduction
            if self.debug_mode:
                print(f"    Crop too small: {reduction_ratio:.1%} reduction")
            return False
        
        if reduction_ratio > 0.8:  # More than 80% reduction
            if self.debug_mode:
                print(f"    Crop too aggressive: {reduction_ratio:.1%} reduction")
            return False
        
        # Check 3: Ensure we're above minimum crop ratio
        min_area_ratio = max(self.min_crop_ratio, 0.05)  # At least 5% of original
        actual_ratio = cropped_area / original_area
        
        if actual_ratio < min_area_ratio:
            if self.debug_mode:
                print(f"    Below minimum ratio: {actual_ratio:.1%} < {min_area_ratio:.1%}")
            return False
        
        # Check 4: Content quality should be preserved or improved
        original_gray = cv2.cvtColor(np.array(original), cv2.COLOR_RGB2GRAY)
        cropped_gray = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2GRAY)
        
        original_quality = self._score_content_quality(original_gray)
        cropped_quality = self._score_content_quality(cropped_gray)
        
        quality_improvement = cropped_quality / (original_quality + 0.01)  # Avoid division by zero
        
        if quality_improvement < 0.8:  # Quality dropped significantly
            if self.debug_mode:
                print(f"    Quality degraded: {quality_improvement:.2f}x")
            return False
        
        if self.debug_mode:
            print(f"    ✅ Beneficial crop: {reduction_ratio:.1%} reduction, {quality_improvement:.2f}x quality")
        
        return True
    
    def _detect_all_image_regions(self, image: Image.Image, gray: np.ndarray, params: Dict) -> List[Tuple[str, Image.Image, float, int]]:
        """Detect all potential image regions in the input image"""
        all_regions = []
        
        # Method 1: Advanced rectangular detection with multiple candidates
        rect_regions = self._find_all_rectangular_regions(image, gray, params)
        for region_img, score, area in rect_regions:
            all_regions.append(("adaptive_rectangular", region_img, score, area))
        
        # Method 2: Content-aware edge detection regions
        edge_regions = self._find_all_edge_regions(image, gray, params)
        for region_img, score, area in edge_regions:
            all_regions.append(("content_edge", region_img, score, area))
        
        # Method 3: Multi-threshold analysis regions
        threshold_regions = self._find_all_threshold_regions(image, gray, params)
        for region_img, score, area in threshold_regions:
            all_regions.append(("multi_threshold", region_img, score, area))
        
        # Step 4: Apply text exclusion to all regions
        refined_regions = []
        for method, region_img, score, area in all_regions:
            refined_img = self._exclude_text_and_refine(region_img, gray, params)
            if refined_img != region_img:  # If text exclusion changed the image
                # Recalculate area and score for refined image
                refined_area = refined_img.width * refined_img.height
                refined_score = score * (refined_area / area) if area > 0 else score
                refined_regions.append((method, refined_img, refined_score, refined_area))
            else:
                refined_regions.append((method, region_img, score, area))
        
        # Filter out duplicates and very similar regions
        unique_regions = self._filter_duplicate_regions(refined_regions)
        
        return unique_regions
    
    def _find_all_rectangular_regions(self, image: Image.Image, gray: np.ndarray, params: Dict) -> List[Tuple[Image.Image, float, int]]:
        """Find all rectangular regions that could be images"""
        regions = []
        
        try:
            # Use adaptive thresholds
            low_thresh, high_thresh = self._calculate_adaptive_thresholds(gray)
            
            # Create mask with adaptive thresholds
            mask = cv2.inRange(gray, low_thresh, high_thresh)
            
            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, params['morph_kernel_size'])
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Edge detection with adaptive parameters
            edges = cv2.Canny(gray, params['canny_low'], params['canny_high'])
            edges = cv2.dilate(edges, kernel, iterations=params['morph_iterations'])
            
            # Combine mask and edges
            combined_mask = cv2.bitwise_or(mask, edges)
            
            # Find all contours
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return regions
            
            # Process all valid contours
            valid_contours = self._filter_contours_advanced(contours, image, params)
            
            for x, y, w, h, quality_score, area_ratio in valid_contours:
                # Create cropped image for this region
                region_img = image.crop((x, y, x + w, y + h))
                area = w * h
                
                # Calculate content quality for this specific region
                roi = gray[y:y+h, x:x+w]
                content_score = self._score_content_quality(roi)
                
                # Combined score for this region
                total_score = quality_score + content_score * 0.3
                
                regions.append((region_img, total_score, area))
                
                if self.debug_mode:
                    print(f"    Found rectangular region: {w}x{h} at ({x},{y}), "
                          f"score: {total_score:.3f}, area: {area}")
            
        except Exception as e:
            if self.debug_mode:
                print(f"  Error in rectangular detection: {e}")
        
        return regions
    
    def _find_all_edge_regions(self, image: Image.Image, gray: np.ndarray, params: Dict) -> List[Tuple[Image.Image, float, int]]:
        """Find all edge-based regions that could be images"""
        regions = []
        
        try:
            # Multi-scale edge detection
            edges_fine = cv2.Canny(gray, params['canny_low'], params['canny_high'])
            edges_coarse = cv2.Canny(gray, params['canny_low']//2, params['canny_high']//2)
            
            # Combine edges
            combined_edges = cv2.bitwise_or(edges_fine, edges_coarse)
            
            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, params['morph_kernel_size'])
            combined_edges = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel)
            combined_edges = cv2.dilate(combined_edges, kernel, iterations=params['morph_iterations'])
            
            # Find contours
            contours, _ = cv2.findContours(combined_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return regions
            
            # Process all content-rich contours
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area_ratio = (w * h) / (image.width * image.height)
                
                if area_ratio >= params['min_area_ratio'] and area_ratio >= self.min_crop_ratio:
                    # Check content richness
                    roi = gray[y:y+h, x:x+w]
                    texture_score = self._calculate_texture_complexity(roi)
                    
                    if texture_score > 0.15:  # Lower threshold to catch more candidates
                        # Add margin and ensure validity
                        margin = 5
                        x_crop = max(0, x - margin)
                        y_crop = max(0, y - margin)
                        x2_crop = min(image.width, x + w + 2 * margin)
                        y2_crop = min(image.height, y + h + 2 * margin)
                        
                        region_img = image.crop((x_crop, y_crop, x2_crop, y2_crop))
                        area = (x2_crop - x_crop) * (y2_crop - y_crop)
                        
                        # Score based on texture and area
                        score = texture_score + area_ratio * 0.5
                        
                        regions.append((region_img, score, area))
                        
                        if self.debug_mode:
                            print(f"    Found edge region: {x2_crop-x_crop}x{y2_crop-y_crop} "
                                  f"at ({x_crop},{y_crop}), score: {score:.3f}")
            
        except Exception as e:
            if self.debug_mode:
                print(f"  Error in edge detection: {e}")
        
        return regions
    
    def _find_all_threshold_regions(self, image: Image.Image, gray: np.ndarray, params: Dict) -> List[Tuple[Image.Image, float, int]]:
        """Find all threshold-based regions that could be images"""
        regions = []
        
        try:
            # Try multiple threshold combinations
            threshold_combinations = [
                (params['threshold_low'], params['threshold_high']),
                (params['threshold_low'] - 10, params['threshold_high'] + 10),
                (params['threshold_low'] + 15, params['threshold_high'] - 15),
                (params['threshold_low'] - 20, params['threshold_high'] + 20),  # More aggressive
            ]
            
            for low, high in threshold_combinations:
                low = max(0, low)
                high = min(255, high)
                
                # Create mask with current thresholds
                mask = cv2.inRange(gray, low, high)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if not contours:
                    continue
                
                # Process all valid contours from this threshold
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    area_ratio = (w * h) / (image.width * image.height)
                    
                    if (area_ratio >= params['min_area_ratio'] and 
                        area_ratio <= params['max_area_ratio'] and
                        area_ratio >= self.min_crop_ratio):
                        
                        # Calculate content quality score
                        roi = gray[y:y+h, x:x+w]
                        content_score = self._score_content_quality(roi)
                        
                        if content_score > 0.1:  # Lower threshold for more candidates
                            region_img = image.crop((x, y, x + w, y + h))
                            area = w * h
                            total_score = area_ratio * content_score
                            
                            regions.append((region_img, total_score, area))
                            
                            if self.debug_mode:
                                print(f"    Found threshold region: {w}x{h} at ({x},{y}), "
                                      f"thresholds: ({low},{high}), score: {total_score:.3f}")
            
        except Exception as e:
            if self.debug_mode:
                print(f"  Error in threshold analysis: {e}")
        
        return regions
    
    def _filter_duplicate_regions(self, regions: List[Tuple[str, Image.Image, float, int]]) -> List[Tuple[str, Image.Image, float, int]]:
        """Filter out duplicate and very similar regions"""
        if len(regions) <= 1:
            return regions
        
        unique_regions = []
        
        for i, (method1, img1, score1, area1) in enumerate(regions):
            is_duplicate = False
            
            # Check against already accepted regions
            for method2, img2, score2, area2 in unique_regions:
                # Calculate similarity based on size and position
                size_diff = abs(area1 - area2) / max(area1, area2)
                
                # If sizes are very similar, check for overlap
                if size_diff < 0.1:  # Less than 10% size difference
                    # Convert images to arrays for comparison
                    arr1 = np.array(img1)
                    arr2 = np.array(img2)
                    
                    # If dimensions are very similar, likely duplicates
                    if (abs(arr1.shape[0] - arr2.shape[0]) < 20 and 
                        abs(arr1.shape[1] - arr2.shape[1]) < 20):
                        is_duplicate = True
                        
                        # Keep the one with higher score
                        if score1 > score2:
                            # Remove the lower scoring one and add this one
                            unique_regions = [(m, i, s, a) for m, i, s, a in unique_regions 
                                            if not (m == method2 and s == score2)]
                            break
                        else:
                            # Skip this one, keep the existing higher scoring one
                            break
            
            if not is_duplicate:
                unique_regions.append((method1, img1, score1, area1))
        
        if self.debug_mode and len(unique_regions) < len(regions):
            print(f"    Filtered duplicates: {len(regions)} -> {len(unique_regions)} regions")
        
        return unique_regions
    
    def _select_best_region(self, regions: List[Tuple[str, Image.Image, float, int]], 
                           characteristics: Dict) -> Tuple[str, Image.Image, float, int]:
        """Select the best region based on user preference"""
        
        if len(regions) == 1:
            return regions[0]
        
        if self.multi_image_handling == "largest_only":
            # Return the region with the largest area
            best_region = max(regions, key=lambda x: x[3])
            
            if self.debug_mode:
                print(f"Selected largest region: {best_region[3]} pixels")
            
            return best_region
            
        elif self.multi_image_handling == "best_quality":
            # Return the region with the highest quality score
            # Combine area and content quality for a comprehensive score
            scored_regions = []
            
            for method, img, score, area in regions:
                # Normalize area score (larger images get bonus, but not linearly)
                area_bonus = np.log(area + 1) / 15.0  # Logarithmic area bonus
                
                # Method-specific bonuses
                method_bonuses = {
                    'adaptive_rectangular': 0.2,
                    'content_edge': 0.15,
                    'multi_threshold': 0.1
                }
                method_bonus = method_bonuses.get(method, 0.05)
                
                # Characteristic-based adjustments
                char_bonus = 0
                if characteristics['text_likelihood'] > 0.3 and method == 'adaptive_rectangular':
                    char_bonus += 0.1
                if characteristics['background_uniformity'] > 0.8 and method == 'adaptive_rectangular':
                    char_bonus += 0.1
                
                final_score = score + area_bonus + method_bonus + char_bonus
                scored_regions.append((final_score, method, img, score, area))
            
            # Return highest scoring region
            best_score, method, img, orig_score, area = max(scored_regions, key=lambda x: x[0])
            
            if self.debug_mode:
                print(f"Selected best quality region: score {best_score:.3f} (original: {orig_score:.3f})")
            
            return (method, img, orig_score, area)
            
        elif self.multi_image_handling == "first_found":
            # Return the first region (fastest processing)
            if self.debug_mode:
                print("Selected first found region")
            
            return regions[0]
        
        else:
            # Default to largest
            return max(regions, key=lambda x: x[3])
    
    def _conservative_crop_multi(self, image: Image.Image, gray: np.ndarray) -> Image.Image:
        """Conservative cropping with multi-image support"""
        conservative_params = {
            'canny_low': 60,
            'canny_high': 180,
            'morph_kernel_size': (3, 3),
            'morph_iterations': 1,
            'threshold_low': 20,
            'threshold_high': 235,
            'min_area_ratio': 0.2,
            'max_area_ratio': 0.95,
            'text_exclusion_strength': 0.3
        }
        
        if self.debug_mode:
            print("Using conservative parameters with multi-image detection")
        
        # Use the same multi-image detection with conservative parameters
        image_type, characteristics = self._analyze_image_characteristics(gray)
        all_regions = self._detect_all_image_regions(image, gray, conservative_params)
        
        if not all_regions:
            return image
        
        best_region = self._select_best_region(all_regions, characteristics)
        return best_region[1]
    
    def _aggressive_crop_multi(self, image: Image.Image, gray: np.ndarray) -> Image.Image:
        """Aggressive cropping with multi-image support"""
        aggressive_params = {
            'canny_low': 25,
            'canny_high': 75,
            'morph_kernel_size': (7, 7),
            'morph_iterations': 3,
            'threshold_low': 5,
            'threshold_high': 250,
            'min_area_ratio': 0.01,
            'max_area_ratio': 0.8,
            'text_exclusion_strength': 0.8
        }
        
        if self.debug_mode:
            print("Using aggressive parameters with multi-image detection")
        
        # Use the same multi-image detection with aggressive parameters
        image_type, characteristics = self._analyze_image_characteristics(gray)
        all_regions = self._detect_all_image_regions(image, gray, aggressive_params)
        
        if not all_regions:
            return image
        
        best_region = self._select_best_region(all_regions, characteristics)
        return best_region[1]
    
    def _analyze_image_characteristics(self, gray: np.ndarray) -> Tuple[str, Dict]:
        """Analyze image to determine type and characteristics - IMPROVED for sky/studio backgrounds"""
        h, w = gray.shape
        
        # Calculate various image metrics
        noise_level = np.std(cv2.Laplacian(gray, cv2.CV_64F))
        contrast_level = np.std(gray)
        brightness_mean = np.mean(gray)
        
        # Edge analysis
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges) / 255.0
        
        # Background uniformity analysis
        border_size = min(20, min(h, w) // 20)
        borders = np.concatenate([
            gray[:border_size, :].flatten(),
            gray[-border_size:, :].flatten(),
            gray[:, :border_size].flatten(),
            gray[:, -border_size:].flatten()
        ])
        background_uniformity = 1.0 - (np.std(borders) / 255.0)
        
        # Texture analysis
        texture_score = self._calculate_texture_complexity(gray)
        
        # Text pattern detection
        text_likelihood = self._detect_text_patterns(gray)
        
        # NEW: Additional check for photo content with uniform backgrounds
        # Check center region for photographic content
        center_h, center_w = h // 4, w // 4
        center_region = gray[center_h:3*center_h, center_w:3*center_w]
        center_texture = self._calculate_texture_complexity(center_region) if center_region.size > 0 else 0
        
        characteristics = {
            'noise_level': noise_level,
            'contrast_level': contrast_level,
            'brightness_mean': brightness_mean,
            'edge_density': edge_density,
            'background_uniformity': background_uniformity,
            'texture_score': texture_score,
            'text_likelihood': text_likelihood,
            'aspect_ratio': w / h,
            'center_texture': center_texture  # NEW metric
        }
        
        # IMPROVED classification with sky/studio background detection
        if background_uniformity > 0.8 and contrast_level > 60:
            # Check if this is actually a photo with uniform background (sky/studio)
            if (center_texture > 0.3 and edge_density > 0.08 and texture_score > 0.2):
                image_type = "photograph"  # Reclassify as photo, not clean_document
            else:
                image_type = "clean_document"
        elif noise_level > 30 and contrast_level < 80:
            image_type = "scanned_document"
        elif edge_density > 0.15 and texture_score > 0.4:
            image_type = "photograph"
        elif text_likelihood > 0.3:
            image_type = "text_heavy"
        elif background_uniformity < 0.4:
            image_type = "complex_background"
        else:
            image_type = "mixed_content"
        
        return image_type, characteristics

    def _get_adaptive_parameters(self, image_type: str, characteristics: Dict) -> Dict:
        """Get optimal parameters - UPDATED with conservative sky/studio handling"""
        
        base_params = {
            'canny_low': 50,
            'canny_high': 150,
            'morph_kernel_size': (5, 5),
            'morph_iterations': 1,
            'threshold_low': 10,
            'threshold_high': 245,
            'min_area_ratio': 0.08,  # INCREASED - less aggressive cropping
            'max_area_ratio': 0.95,
            'text_exclusion_strength': 0.4  # REDUCED - less text exclusion
        }
        
        # Adaptive adjustments based on image type
        if image_type == "clean_document":
            base_params.update({
                'canny_low': 30,
                'canny_high': 100,
                'threshold_low': 15,
                'threshold_high': 240,
                'min_area_ratio': 0.15,  # INCREASED - keep more of clean documents
                'text_exclusion_strength': 0.6
            })
        elif image_type == "scanned_document":
            base_params.update({
                'canny_low': 40,
                'canny_high': 120,
                'morph_iterations': 2,
                'threshold_low': 5,
                'threshold_high': 250,
                'min_area_ratio': 0.08,  # INCREASED from 0.03
                'text_exclusion_strength': 0.5  # REDUCED from 0.7
            })
        elif image_type == "photograph":
            # SPECIAL handling for uniform background photos (sky/studio)
            if characteristics['background_uniformity'] > 0.8:
                # Very conservative parameters for sky/studio backgrounds
                base_params.update({
                    'canny_low': 25,           # LOWER - catch subtle edges
                    'canny_high': 80,          # LOWER - less aggressive  
                    'morph_kernel_size': (3, 3),  # SMALLER - preserve fine boundaries
                    'threshold_low': 30,       # HIGHER - avoid background noise
                    'threshold_high': 220,     # LOWER - be more inclusive
                    'min_area_ratio': 0.20,    # MUCH HIGHER - very conservative cropping
                    'text_exclusion_strength': 0.1  # VERY LOW - don't exclude sky/background
                })
            else:
                # Normal photo parameters
                base_params.update({
                    'canny_low': 60,
                    'canny_high': 180,
                    'morph_kernel_size': (3, 3),
                    'threshold_low': 20,
                    'threshold_high': 235,
                    'min_area_ratio': 0.12,  # INCREASED from 0.08
                    'text_exclusion_strength': 0.2  # Keep low for photos
                })
        elif image_type == "text_heavy":
            base_params.update({
                'canny_low': 35,
                'canny_high': 105,
                'morph_iterations': 1,
                'min_area_ratio': 0.15,
                'text_exclusion_strength': 0.7  # REDUCED from 0.9
            })
        elif image_type == "complex_background":
            base_params.update({
                'canny_low': 70,
                'canny_high': 200,
                'morph_kernel_size': (7, 7),
                'morph_iterations': 3,
                'min_area_ratio': 0.06,  # INCREASED from original
                'text_exclusion_strength': 0.6
            })
        elif image_type == "mixed_content":  # ADD missing case
            base_params.update({
                'canny_low': 45,
                'canny_high': 135,
                'morph_kernel_size': (5, 5),
                'morph_iterations': 2,
                'min_area_ratio': 0.10,
                'text_exclusion_strength': 0.5
            })
        
        # Fine-tune based on specific characteristics
        if characteristics['contrast_level'] < 40:
            base_params['canny_low'] = max(20, base_params['canny_low'] - 15)
            base_params['canny_high'] = max(60, base_params['canny_high'] - 30)
        
        if characteristics['noise_level'] > 40:
            base_params['morph_iterations'] += 1
            base_params['morph_kernel_size'] = (7, 7)
        
        # NEW: Additional adjustments for edge density and background uniformity
        if characteristics['edge_density'] > 0.2:  # High edge density
            base_params['min_area_ratio'] = max(0.05, base_params['min_area_ratio'] - 0.02)
        elif characteristics['edge_density'] < 0.05:  # Low edge density
            base_params['min_area_ratio'] += 0.03
        
        # Background uniformity adjustments
        if characteristics['background_uniformity'] > 0.9:  # Very uniform background
            base_params['text_exclusion_strength'] += 0.1
        elif characteristics['background_uniformity'] < 0.3:  # Very non-uniform background
            base_params['text_exclusion_strength'] = max(0.2, base_params['text_exclusion_strength'] - 0.2)
        
        return base_params
        
    
    def _calculate_adaptive_thresholds(self, gray: np.ndarray) -> Tuple[int, int]:
        """Calculate optimal thresholds based on histogram analysis"""
        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        # Smooth histogram
        hist_smooth = cv2.GaussianBlur(hist.reshape(-1, 1), (5, 1), 0).flatten()
        
        # Find peaks and valleys
        peaks = []
        valleys = []
        
        for i in range(1, len(hist_smooth) - 1):
            if hist_smooth[i] > hist_smooth[i-1] and hist_smooth[i] > hist_smooth[i+1]:
                if hist_smooth[i] > np.max(hist_smooth) * 0.1:  # Significant peaks only
                    peaks.append(i)
            elif hist_smooth[i] < hist_smooth[i-1] and hist_smooth[i] < hist_smooth[i+1]:
                valleys.append(i)
        
        # Determine thresholds
        if len(valleys) >= 1:
            # Use the most significant valley
            valley_scores = [(v, hist_smooth[v]) for v in valleys]
            best_valley = min(valley_scores, key=lambda x: x[1])[0]
            
            low_thresh = max(5, best_valley - 20)
            high_thresh = min(250, best_valley + 20)
        else:
            # Fallback to Otsu's method
            otsu_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            low_thresh = max(5, otsu_thresh - 25)
            high_thresh = min(250, otsu_thresh + 25)
        
        return low_thresh, high_thresh
    
    def _filter_contours_advanced(self, contours: List, image: Image.Image, params: Dict) -> List:
        """Advanced contour filtering with multiple criteria"""
        total_area = image.width * image.height
        valid_contours = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            area_ratio = area / total_area
            aspect_ratio = w / h if h > 0 else 0
            
            # Basic size filtering
            if not (params['min_area_ratio'] <= area_ratio <= params['max_area_ratio']):
                continue
            
            if area_ratio < self.min_crop_ratio:
                continue
            
            # Aspect ratio filtering (reasonable rectangles)
            if not (0.1 <= aspect_ratio <= 10.0):
                continue
            
            # Contour quality assessment
            contour_area = cv2.contourArea(contour)
            bbox_area = w * h
            fill_ratio = contour_area / bbox_area if bbox_area > 0 else 0
            
            # Prefer more rectangular shapes
            if fill_ratio > 0.6:
                quality_score = area_ratio * fill_ratio
                valid_contours.append((x, y, w, h, quality_score, area_ratio))
        
        return valid_contours
    
    def _exclude_text_and_refine(self, image: Image.Image, gray: np.ndarray, params: Dict) -> Image.Image:
        """Exclude text regions and refine boundaries"""
        try:
            # Convert cropped image back to array for analysis
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                crop_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                crop_gray = img_array
            
            # Detect text regions
            text_strength = params['text_exclusion_strength']
            if text_strength > 0.5:
                text_regions = self._detect_text_regions_advanced(crop_gray)
                
                if text_regions:
                    # Create mask excluding text
                    h, w = crop_gray.shape
                    text_mask = np.zeros((h, w), dtype=np.uint8)
                    
                    for x, y, tw, th in text_regions:
                        padding = int(max(tw, th) * 0.1)  # Adaptive padding
                        x1 = max(0, x - padding)
                        y1 = max(0, y - padding)
                        x2 = min(w, x + tw + padding)
                        y2 = min(h, y + th + padding)
                        cv2.rectangle(text_mask, (x1, y1), (x2, y2), 255, -1)
                    
                    # Find largest text-free region
                    text_free = cv2.bitwise_not(text_mask)
                    contours, _ = cv2.findContours(text_free, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        largest_contour = max(contours, key=cv2.contourArea)
                        x, y, tw, th = cv2.boundingRect(largest_contour)
                        
                        # Check if remaining region is substantial
                        remaining_ratio = (tw * th) / (w * h)
                        if remaining_ratio > 0.3:
                            if self.debug_mode:
                                print(f"  Text exclusion: Kept {remaining_ratio:.2f} of region")
                            return image.crop((x, y, x + tw, y + th))
            
            return image
            
        except Exception as e:
            if self.debug_mode:
                print(f"  Text exclusion failed: {e}")
            return image
    
    def _detect_text_regions_advanced(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Advanced text region detection"""
        # Multiple text detection approaches
        text_regions = []
        
        # Method 1: Horizontal morphology
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (12, 1))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        
        # Method 2: Connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(horizontal, connectivity=8)
        
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            aspect_ratio = w / h if h > 0 else 0
            
            # Text-like characteristics
            if (aspect_ratio > 3.0 and  # Wide regions
                20 < area < 5000 and     # Reasonable size
                h > 8 and w > 30):       # Minimum dimensions
                text_regions.append((x, y, w, h))
        
        return text_regions
    
    def _calculate_texture_complexity(self, roi: np.ndarray) -> float:
        """Calculate texture complexity score"""
        if roi.size == 0:
            return 0.0
        
        # Local Binary Pattern-like analysis
        laplacian_var = cv2.Laplacian(roi, cv2.CV_64F).var()
        gradient_x = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
        
        texture_score = (laplacian_var / 1000.0) + (np.mean(gradient_magnitude) / 255.0)
        return min(1.0, texture_score)
    
    def _detect_text_patterns(self, gray: np.ndarray) -> float:
        """Detect likelihood of text patterns in image"""
        # Horizontal line detection
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        
        text_pixels = np.sum(horizontal_lines > 0)
        total_pixels = horizontal_lines.size
        
        return text_pixels / total_pixels if total_pixels > 0 else 0.0
    
    def _score_content_quality(self, roi: np.ndarray) -> float:
        """Score the quality/richness of content in a region"""
        if roi.size == 0:
            return 0.0
        
        # Multiple quality metrics
        variance_score = np.var(roi) / 1000.0
        edge_score = np.mean(cv2.Canny(roi, 50, 150)) / 255.0
        texture_score = self._calculate_texture_complexity(roi)
        
        # Combine scores
        quality_score = (variance_score + edge_score + texture_score) / 3.0
        return min(1.0, quality_score)
    
    def _tensor_to_pil(self, tensor):
        """Convert ComfyUI tensor to PIL Image"""
        # Handle batch dimension
        if len(tensor.shape) == 4:
            tensor = tensor[0]
        
        # Convert from torch tensor to numpy
        image_np = tensor.cpu().numpy()
        
        # Scale from 0-1 to 0-255 and convert to uint8
        image_np = (image_np * 255).astype(np.uint8)
        
        # Convert to PIL Image
        return Image.fromarray(image_np)
    
    def _pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI tensor"""
        # Convert to numpy array
        image_np = np.array(pil_image)
        
        # Ensure RGB format
        if len(image_np.shape) == 2:
            image_np = np.stack([image_np] * 3, axis=-1)
        elif image_np.shape[2] == 4:  # RGBA
            image_np = image_np[:, :, :3]  # Remove alpha
        
        # Convert to float and normalize to 0-1
        image_np = image_np.astype(np.float32) / 255.0
        
        # Convert to torch tensor and add batch dimension
        tensor = torch.from_numpy(image_np).unsqueeze(0)
        
        return tensor


# Node registration
NODE_CLASS_MAPPINGS = {
    "SmartImageCropper": SmartImageCropper
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SmartImageCropper": "Smart Image Cropper"
}