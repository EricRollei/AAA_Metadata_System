"""
ComfyUI Node: Image Duplicate Finder Node v0.4
Description: 
This node scans folders of images, identifies duplicates and similar images using perceptual hashing,
and provides various options for handling them. Integration with the metadata system allows for
storing and retrieving hash data.

Features:
- Multiple hash algorithm support (phash, dhash, average_hash, whash-haar)
- Multi-level similarity detection (exact, similar, variant)
- Filename and metadata-based similarity enhancement
- Integrated with metadata system using the 'image.similarity' namespace
- Options for moving, copying, or organizing duplicate files
- Detailed reporting and statistics

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.4.0

Date: [March 2025]
License: Dual License (Non-Commercial and Commercial Use)
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import hashlib
from tqdm import tqdm
import numpy as np
from PIL import Image
import folder_paths

# Check for imagehash library
try:
    import imagehash
except ImportError:
    print("Warning: imagehash library not installed. Please install it with:")
    print("pip install imagehash")
    imagehash = None

# Import metadata service if available
try:
    from eric_metadata.service import MetadataService
    METADATA_SYSTEM_AVAILABLE = True
except ImportError:
    print("Note: Eric's metadata system not found. Will use basic metadata handling.")
    METADATA_SYSTEM_AVAILABLE = False

class ImageDuplicateFinder:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "folder_path": ("STRING", {"default": "", "tooltip": "Main folder to scan for images."}),
                "primary_hash": (["phash", "average_hash", "dhash", "whash-haar"], {"default": "phash", "tooltip": "Primary hash algorithm to use."}),
                "exact_duplicate_threshold": ("FLOAT", {"default": 0.985, "min": 0.5, "max": 1.0, "step": 0.01, "tooltip": "Threshold values will depend on hash, but between .96 and .99 works well."}),
                "similar_image_threshold": ("FLOAT", {"default": 0.93, "min": 0.3, "max": 1.0, "step": 0.01, "tooltip": "Threshold values depend on hash and images, experiment in the  .85 and .95 range"}),
                "variant_threshold": ("FLOAT", {"default": 0.8, "min": 0.3, "max": 1.0, "step": 0.01, "tooltip": "Small changes can have big effects depending on image content - experiment between .75 and .85"}),
            },
            "optional": {
                "recursive": ("BOOLEAN", {"default": True, "tooltip": "Set True to scan subfolders recursively."}),
                "additional_folders": ("STRING", {"default": "", "multiline": True, 
                                     "placeholder": "Scan extra folders. Put only one folder path per line"}),
                "secondary_hash": (["none", "phash", "average_hash", "dhash", "whash-haar"], {"default": "dhash", "tooltip": "A second hash improves accuracy but is slower."}),
                "min_dimensions": ("STRING", {"default": "0x0", "placeholder": "WIDTHxHEIGHT", "tooltip": "Minimum dimensions to include ie 100x100. Can speed up runs, but don't change unless you know what you are doing."}),
                "analyze_filename": ("BOOLEAN", {"default": True, "tooltip": "Adds info from file names into the similarity score."}),
                "analyze_metadata": ("BOOLEAN", {"default": True, "tooltip": "Adds info from image metadata into the similarity score."}),
                "metadata_weight": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "Can help if your images have good metadata otherwise might give false positives."}),
                "save_hashes": ("BOOLEAN", {"default": True, "tooltip": "Save hashes to metadata for future use."}),
                "duplicate_action": (["move", "copy", "none"], {"default": "none"}),
                "output_folder": ("STRING", {"default": "duplicates", "tooltip": "Folder to save duplicates, similar, and variant images to. Will be created if it doesn't exist."}),
                "output_folder_location": (["comfyui_output", "original_folder"], {"default": "comfyui_output","tooltip": "Where to save duplicates: ComfyUI output folder or inside each original image's folder."}),
                "group_by_similarity": ("BOOLEAN", {"default": True}),
                "keep_largest": ("BOOLEAN", {"default": True}),
                "update_metadata": ("BOOLEAN", {"default": True}),
                "save_results": ("BOOLEAN", {"default": True}),
                "results_format": (["json", "csv", "both"], {"default": "json"}),
                "display_top_n": ("INT", {"default": 20, "min": 0, "max": 100, "step": 5}),
            }
        }
        return inputs

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("duplicate_groups", "total_duplicates", "stats_json", "results_path") 
    FUNCTION = "find_duplicates"
    CATEGORY = "Eric/Images"

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.results_dir = os.path.join(self.output_dir, "duplicate_finder")
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize metadata service if available
        self.metadata_service = None
        if METADATA_SYSTEM_AVAILABLE:
            try:
                self.metadata_service = MetadataService(debug=False)
                print("Metadata service initialized")
            except Exception as e:
                print(f"Error initializing metadata service: {e}")

    def find_duplicates(self, folder_path, primary_hash="phash", exact_duplicate_threshold=0.95, 
                       similar_image_threshold=0.85, variant_threshold=0.7, recursive=True,
                       additional_folders="", secondary_hash="none", min_dimensions="0x0",
                       analyze_filename=True, analyze_metadata=True, metadata_weight=0.3,
                       save_hashes=True, 
                       duplicate_action="none", 
                       output_folder="duplicates", output_folder_location="comfyui_output", group_by_similarity=True, keep_largest=True,
                       update_metadata=True, save_results=True, results_format="json",
                       display_top_n=20):
        """
        Main function to find and handle duplicate images
        """
        start_time = time.time()
        
        # Configure database handler if using metadata system
        if update_metadata and self.metadata_service:
            try:
                self.metadata_service.configure_handler(
                    'database',
                    auto_index_hashes=True  # Enable indexing for faster hash lookups
                )
            except Exception as e:
                print(f"Note: Database configuration failed: {e}. Continuing without database optimization.")
                
        # Parse and validate inputs
        additional_folder_list = [f.strip() for f in additional_folders.splitlines() if f.strip()]
        min_width, min_height = self._parse_dimensions(min_dimensions)
        
        print(f"Starting duplicate analysis on folder: {folder_path}")
        print(f"Using primary hash algorithm: {primary_hash}")
        print(f"Additional folders: {len(additional_folder_list)}")
        
        # Create stats dictionary
        stats = {
            "start_time": datetime.now().isoformat(),
            "folders_scanned": 1 + len(additional_folder_list),
            "files_scanned": 0,
            "images_processed": 0,
            "skipped_non_images": 0,
            "skipped_small": 0,
            "skipped_errors": 0,
            "exact_duplicates": 0,
            "similar_images": 0,
            "variant_images": 0,
            "files_moved": 0,
            "files_copied": 0,
            "hashes_saved": 0,
            "metadata_updated": 0,
            "total_savings_bytes": 0,
            "error": None
        }
        
        # Initialize output folder if needed
        duplicates_path = None
        if duplicate_action in ["move", "copy"]:
            duplicates_path = self._create_duplicates_folder(output_folder, output_folder_location)
            print(f"Duplicate files will be {duplicate_action}d to: {duplicates_path}")
        
        try:
            # 1. Scan folders and collect image paths
            image_paths = self._collect_image_paths(folder_path, recursive, additional_folder_list)
            stats["files_scanned"] = len(image_paths)
            print(f"Found {len(image_paths)} total files")
            
            # After collecting image_paths
            root_folder = folder_path
            
            if not image_paths:
                stats["error"] = "No files found in specified folders"
                return "No files found", 0, json.dumps(stats), ""
            
            # 2. Process images and calculate hashes
            image_data = self._process_images(
                image_paths, 
                primary_hash, 
                secondary_hash,
                min_width, 
                min_height, 
                save_hashes,
                analyze_metadata,
                stats
            )
            
            # 3. Calculate similarity and group images
            groups = self._group_similar_images(
                image_data,
                exact_duplicate_threshold,
                similar_image_threshold,
                variant_threshold,
                analyze_filename,
                metadata_weight,
                stats
            )
            
            # 4. Handle duplicates (move/copy if requested)
            if duplicate_action in ["move", "copy"] and duplicates_path:
                self._handle_duplicates(
                    groups, 
                    duplicates_path, 
                    duplicate_action, 
                    keep_largest,
                    group_by_similarity,
                    stats,
                    output_folder,
                    output_folder_location,
                    root_folder  # <-- pass it here
                )
            
            # 5. Update metadata if requested
            if update_metadata and self.metadata_service:
                self._update_similarity_metadata(groups, stats)
            
            # 6. Save results if requested
            results_path = ""
            if save_results:
                results_path = self._save_results(groups, stats, results_format)
            
            # 7. Format output for return
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            total_duplicates = stats["exact_duplicates"] + stats["similar_images"] + stats["variant_images"]
            
            # Format duplicate groups for display (limiting to top N)
            formatted_groups = self._format_groups_for_display(groups, display_top_n)
            
            return formatted_groups, total_duplicates, json.dumps(stats, indent=2), results_path
            
        except Exception as e:
            print(f"Error in duplicate finder: {e}")
            import traceback
            traceback.print_exc()
            stats["error"] = str(e)
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            return f"Error: {e}", 0, json.dumps(stats), ""

    def _parse_dimensions(self, dimensions_str):
        """Parse dimensions string in format WIDTHxHEIGHT"""
        try:
            if 'x' in dimensions_str:
                width, height = dimensions_str.lower().split('x')
                return int(width), int(height)
            return 0, 0
        except Exception:
            print(f"Invalid dimensions format: {dimensions_str}, using 0x0")
            return 0, 0

    def _collect_image_paths(self, main_folder, recursive, additional_folders):
        """Collect image file paths from all specified folders"""
        image_paths = []
        
        # Image extensions to look for
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif', '.gif']
        
        # Function to scan a single folder
        def scan_folder(folder):
            folder_paths = []
            if not os.path.exists(folder):
                print(f"Warning: Folder does not exist: {folder}")
                return folder_paths
                
            print(f"Scanning folder: {folder}")
            if recursive:
                # Walk through all subdirectories
                for root, _, files in os.walk(folder):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in valid_extensions):
                            folder_paths.append(os.path.join(root, file))
            else:
                # Only scan top-level directory
                for file in os.listdir(folder):
                    if os.path.isfile(os.path.join(folder, file)) and any(file.lower().endswith(ext) for ext in valid_extensions):
                        folder_paths.append(os.path.join(folder, file))
            
            return folder_paths
        
        # Scan main folder
        if main_folder:
            image_paths.extend(scan_folder(main_folder))
            
        # Scan additional folders
        for folder in additional_folders:
            image_paths.extend(scan_folder(folder))
            
        return image_paths

    def _process_images(self, image_paths, primary_hash, secondary_hash, min_width, min_height, 
                    save_hashes, analyze_metadata, stats):
        """Process images and calculate their hashes and metadata"""
        image_data = []
        
        # Check if imagehash is available
        if imagehash is None:
            raise ImportError("imagehash library is required for duplicate finding")
        
        print(f"Processing {len(image_paths)} images...")
        
        # Create a progress indicator
        for idx, img_path in enumerate(tqdm(image_paths)):
            try:
                # Check if we already have hash data in metadata/database
                has_existing_hash = False
                if analyze_metadata and self.metadata_service:
                    try:
                        metadata = self.metadata_service.read_metadata(
                            img_path, 
                            source='database',  # Try database first for speed
                            fallback=True       # Fall back to other sources if needed
                        )
                        
                        # Check if we have the hash we need in the eiqa namespace
                        if (metadata and 'eiqa' in metadata and 'technical' in metadata['eiqa'] 
                            and 'hashes' in metadata['eiqa']['technical'] 
                            and primary_hash in metadata['eiqa']['technical']['hashes']):
                            
                            # We found an existing hash! Get basic info without opening the image
                            file_size = os.path.getsize(img_path)
                            file_info = {
                                'path': img_path,
                                'filename': os.path.basename(img_path),
                                'size': file_size,
                                'modified_time': os.path.getmtime(img_path),
                                'primary_hash': metadata['eiqa']['technical']['hashes'][primary_hash],
                                'has_metadata': True
                            }
                            
                            # Also get secondary hash if available and requested
                            if (secondary_hash != "none" and 
                                secondary_hash in metadata['eiqa']['technical']['hashes']):
                                file_info['secondary_hash'] = metadata['eiqa']['technical']['hashes'][secondary_hash]
                            
                            # Try to get dimensions if available in metadata
                            if ('dimensions' in metadata.get('basic', {}) and 
                                'x' in metadata['basic']['dimensions']):
                                try:
                                    width, height = metadata['basic']['dimensions'].split('x')
                                    file_info['dimensions'] = f"{width}x{height}"
                                    file_info['width'] = int(width)
                                    file_info['height'] = int(height)
                                    file_info['pixel_count'] = int(width) * int(height)
                                except:
                                    # If dimensions parsing fails, we'll get them by opening the image
                                    pass
                            
                            # If we have all the info we need, add to image_data and continue
                            if 'width' in file_info and 'height' in file_info:
                                has_existing_hash = True
                                
                                # Check dimensions against minimum if specified
                                if ((min_width > 0 and file_info['width'] < min_width) or 
                                    (min_height > 0 and file_info['height'] < min_height)):
                                    stats["skipped_small"] += 1
                                    continue
                                
                                # Add to image data and skip to next file
                                image_data.append(file_info)
                                stats["images_processed"] += 1
                                continue
                            
                    except Exception as e:
                        print(f"Error checking metadata for {img_path}: {e}")
                
                # If we didn't get hash from metadata or need more info, open the image
                if not has_existing_hash:
                    # Try to open the image
                    img = Image.open(img_path)
                    
                    # Check dimensions
                    width, height = img.size
                    if (min_width > 0 and width < min_width) or (min_height > 0 and height < min_height):
                        stats["skipped_small"] += 1
                        continue
                    
                    # Get file info
                    file_size = os.path.getsize(img_path)
                    file_info = {
                        'path': img_path,
                        'filename': os.path.basename(img_path),
                        'size': file_size,
                        'dimensions': f"{width}x{height}",
                        'width': width,
                        'height': height,
                        'pixel_count': width * height,
                        'modified_time': os.path.getmtime(img_path),
                        'format': img.format
                    }
                    
                    # Calculate primary hash
                    if primary_hash == "phash":
                        hash_value = imagehash.phash(img)
                    elif primary_hash == "dhash":
                        hash_value = imagehash.dhash(img)
                    elif primary_hash == "whash-haar":
                        hash_value = imagehash.whash(img)
                    else:  # default to average_hash
                        hash_value = imagehash.average_hash(img)
                    
                    file_info['primary_hash'] = str(hash_value)
                    
                    # Calculate secondary hash if requested
                    if secondary_hash != "none":
                        if secondary_hash == "phash":
                            secondary_hash_value = imagehash.phash(img)
                        elif secondary_hash == "dhash":
                            secondary_hash_value = imagehash.dhash(img)
                        elif secondary_hash == "whash-haar":
                            secondary_hash_value = imagehash.whash(img)
                        else:  # average_hash
                            secondary_hash_value = imagehash.average_hash(img)
                        
                        file_info['secondary_hash'] = str(secondary_hash_value)
                    
                    # Get existing metadata if available and requested
                    if analyze_metadata and self.metadata_service:
                        try:
                            metadata = self.metadata_service.read_metadata(img_path, fallback=True)
                            # Extract relevant metadata
                            if metadata:
                                # Store any other relevant metadata
                                file_info['has_metadata'] = True
                                
                                # Extract creation date if available
                                if 'basic' in metadata and 'creation_date' in metadata['basic']:
                                    file_info['creation_date'] = metadata['basic']['creation_date']
                                
                                # Extract AI generation info if available
                                if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
                                    gen_info = metadata['ai_info']['generation']
                                    if 'seed' in gen_info:
                                        file_info['seed'] = gen_info['seed']
                                    if 'model' in gen_info:
                                        file_info['model'] = gen_info['model']
                        except Exception as e:
                            print(f"Error reading metadata for {img_path}: {e}")
                    
                    # Save hash to metadata if requested
                    if save_hashes and self.metadata_service:
                        try:
                            self._save_hash_to_metadata(img_path, primary_hash, str(hash_value), 
                                                    secondary_hash, file_info.get('secondary_hash'))
                            stats["hashes_saved"] += 1
                        except Exception as e:
                            print(f"Error saving hash to metadata for {img_path}: {e}")
                    
                    image_data.append(file_info)
                    stats["images_processed"] += 1
            
            except (IOError, OSError) as e:
                stats["skipped_errors"] += 1
                print(f"Error processing image {img_path}: {e}")
                continue
                
            except Exception as e:
                stats["skipped_errors"] += 1
                print(f"Unexpected error with {img_path}: {e}")
                continue
                
        print(f"Successfully processed {stats['images_processed']} images")
        return image_data

    def _save_hash_to_metadata(self, image_path, primary_hash_type, primary_hash_value, 
                              secondary_hash_type=None, secondary_hash_value=None):
        """Save hash values to image metadata"""
        if not self.metadata_service:
            return
            
        # Create metadata structure for hash values
        hash_metadata = {
            'eiqa': {
                'technical': {
                    'hashes': {
                        primary_hash_type: primary_hash_value,
                        'hash_time': datetime.now().isoformat()
                    }
                }
            }
        }
        
        # Add secondary hash if available
        if secondary_hash_type and secondary_hash_type != "none" and secondary_hash_value:
            hash_metadata['eiqa']['technical']['hashes'][secondary_hash_type] = secondary_hash_value
            
        # Set resource identifier (important for XMP)
        filename = os.path.basename(image_path)
        resource_uri = f"file:///{filename}"
        self.metadata_service.set_resource_identifier(resource_uri)
        
        # Write hash metadata
        try:
            self.metadata_service.write_metadata(
                image_path, 
                hash_metadata,
                targets=['embedded', 'xmp', 'database']  # Save to both embedded and XMP if available
            )
            return True
        except Exception as e:
            print(f"Error writing hash metadata: {e}")
            return False

    def _hamming_distance(self, hash1, hash2):
        """Calculate normalized Hamming distance between two hash strings"""
        if not hash1 or not hash2:
            return 0
            
        # Convert string hashes to imagehash objects if needed
        if isinstance(hash1, str):
            hash1 = self._str_to_imagehash(hash1)
        if isinstance(hash2, str):
            hash2 = self._str_to_imagehash(hash2)
            
        # If conversion failed, return 0 (no similarity)
        if hash1 is None or hash2 is None:
            return 0
            
        # Calculate bit difference and normalize to 0-1 range where 1 is identical
        bit_size = len(hash1.hash.flatten())
        hamming_distance = hash1 - hash2
        similarity = 1 - (hamming_distance / bit_size)
        
        return similarity

    def _str_to_imagehash(self, hash_str):
        """Convert a string hash to an imagehash object"""
        try:
            # Remove 0x prefix if present
            if hash_str.startswith('0x'):
                hash_str = hash_str[2:]
                
            # Convert to imagehash object (this is an approximation, depends on hash type)
            hash_int = int(hash_str, 16)
            hash_bits = bin(hash_int)[2:].zfill(64)  # Convert to binary and pad to 64 bits
            hash_array = np.array([int(bit) for bit in hash_bits]).reshape(8, 8)
            
            return imagehash.ImageHash(hash_array)
        except Exception as e:
            print(f"Error converting hash string to imagehash: {e}")
            return None

    def _filename_similarity(self, filename1, filename2):
        """Calculate filename similarity score based on common patterns"""
        # Get base names without extensions
        base1 = os.path.splitext(filename1)[0]
        base2 = os.path.splitext(filename2)[0]
        
        # Simple case: one is a substring of the other
        if base1 in base2 or base2 in base1:
            # Calculate how much of the longer name is matched
            longer = max(len(base1), len(base2))
            shorter = min(len(base1), len(base2))
            if longer > 0:
                return shorter / longer
            return 0
            
        # Check for common patterns like "image (1)" and "image (2)"
        # or "image_upscaled" and "image"
        
        # Remove trailing numbers and common suffixes
        def clean_name(name):
            # Remove trailing "(n)" pattern
            import re
            name = re.sub(r'\s*\(\d+\)$', '', name)
            
            # Remove common suffixes
            suffixes = ["_upscaled", "_enhanced", "_fixed", "_edited", "_copy", 
                       "-upscaled", "-enhanced", "-fixed", "-edited", "-copy"]
            for suffix in suffixes:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
                    break
            return name
            
        clean1 = clean_name(base1)
        clean2 = clean_name(base2)
        
        # Check for exact match after cleaning
        if clean1 == clean2:
            return 0.9  # High but not perfect match
            
        # Check for substring match after cleaning
        if clean1 in clean2 or clean2 in clean1:
            longer = max(len(clean1), len(clean2))
            shorter = min(len(clean1), len(clean2))
            if longer > 0:
                return 0.7 * (shorter / longer)  # Scale down a bit
            
        # Fallback: Calculate Levenshtein distance (string edit distance)
        distance = self._levenshtein_distance(clean1, clean2)
        max_len = max(len(clean1), len(clean2))
        if max_len > 0:
            return 1 - (distance / max_len)
        return 0

    def _levenshtein_distance(self, s1, s2):
        """Calculate Levenshtein (edit) distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
            
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]

    def _format_file_size(self, size_in_bytes):
        """Format file size in bytes to human-readable format"""
        # Define size units
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_in_bytes)
        unit_index = 0
        
        # Find appropriate unit
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        # Format with appropriate precision
        if size < 10:
            return f"{size:.2f} {units[unit_index]}"
        elif size < 100:
            return f"{size:.1f} {units[unit_index]}"
        else:
            return f"{int(size)} {units[unit_index]}"
            
    def _metadata_similarity(self, info1, info2):
        """Calculate similarity score based on metadata"""
        score = 0
        weight_sum = 0
        
        # Check for exact same dimensions
        if info1.get('dimensions') == info2.get('dimensions'):
            score += 0.5
            weight_sum += 0.5
            
        # Check for similar dimensions (resized versions)
        elif 'width' in info1 and 'height' in info1 and 'width' in info2 and 'height' in info2:
            # Calculate aspect ratio similarity
            ratio1 = info1['width'] / info1['height'] if info1['height'] > 0 else 0
            ratio2 = info2['width'] / info2['height'] if info2['height'] > 0 else 0
            
            if ratio1 > 0 and ratio2 > 0:
                ratio_sim = 1 - min(abs(ratio1 - ratio2) / max(ratio1, ratio2), 1.0)
                score += 0.3 * ratio_sim
                weight_sum += 0.3
                
            # Check if one is approximately a scaled version of the other
            area1 = info1['width'] * info1['height']
            area2 = info2['width'] * info2['height']
            
            if area1 > 0 and area2 > 0:
                scale_ratio = max(area1, area2) / min(area1, area2)
                
                # Check if it's close to a common scaling factor (1.5x, 2x, 4x)
                if abs(scale_ratio - 1.5) < 0.1 or abs(scale_ratio - 2) < 0.1 or abs(scale_ratio - 4) < 0.1:
                    score += 0.4
                    weight_sum += 0.4
                # Or if it's any reasonable scaling factor
                elif scale_ratio < 8:  # Not too extreme scaling
                    score += 0.2
                    weight_sum += 0.2
                    
        # Check creation date if available
        if 'creation_date' in info1 and 'creation_date' in info2:
            try:
                # Parse dates (format depends on your metadata)
                from dateutil.parser import parse
                date1 = parse(info1['creation_date'])
                date2 = parse(info2['creation_date'])
                
                # Check if dates are close (within 1 minute)
                diff = abs((date1 - date2).total_seconds())
                if diff < 60:
                    score += 0.3
                    weight_sum += 0.3
                # Within 1 hour
                elif diff < 3600:
                    score += 0.1
                    weight_sum += 0.1
            except:
                pass  # Skip date comparison if parsing fails
                
        # Check if images share same AI generation seed
        if 'seed' in info1 and 'seed' in info2 and info1['seed'] == info2['seed']:
            score += 0.6
            weight_sum += 0.6
            
        # Check if images are from the same model
        if 'model' in info1 and 'model' in info2 and info1['model'] == info2['model']:
            score += 0.2
            weight_sum += 0.2
            
        # Normalize score
        if weight_sum > 0:
            return score / weight_sum
        return 0

    def _group_similar_images(self, image_data, exact_threshold, similar_threshold, variant_threshold,
                             analyze_filename, metadata_weight, stats):
        """Group images based on similarity scores"""
        # Print thresholds
        print(f"Grouping with thresholds: Exact={exact_threshold}, Similar={similar_threshold}, Variant={variant_threshold}")
        
        # Create a list to store groups
        groups = {
            'exact': [],
            'similar': [],
            'variant': []
        }
        
        # Skip if no images to process
        if len(image_data) <= 1:
            return groups
            
        # Calculate similarity scores between all pairs
        print("Calculating similarity scores...")
        pairs = []
        
        for i in range(len(image_data)):
            for j in range(i+1, len(image_data)):
                info1 = image_data[i]
                info2 = image_data[j]
                
                # Calculate primary hash similarity
                hash_similarity = self._hamming_distance(info1['primary_hash'], info2['primary_hash'])
                
                # Calculate secondary hash similarity if available
                secondary_similarity = 0
                if 'secondary_hash' in info1 and 'secondary_hash' in info2:
                    secondary_similarity = self._hamming_distance(info1['secondary_hash'], info2['secondary_hash'])
                    
                # Combine hash similarities (if secondary hash exists)
                if secondary_similarity > 0:
                    hash_similarity = 0.7 * hash_similarity + 0.3 * secondary_similarity
                
                # Initialize overall similarity with hash similarity
                similarity = hash_similarity
                
                # Factor in filename similarity if requested
                if analyze_filename:
                    filename_sim = self._filename_similarity(info1['filename'], info2['filename'])
                    # Adjust overall similarity with filename similarity
                    if filename_sim > 0.5:  # Only consider strong filename matches
                        similarity = (1 - metadata_weight) * similarity + metadata_weight * filename_sim
                
                # Factor in metadata similarity if available
                meta_similarity = self._metadata_similarity(info1, info2)
                if meta_similarity > 0:
                    similarity = (1 - metadata_weight) * similarity + metadata_weight * meta_similarity
                
                # Store the pair with its similarity score
                pairs.append((i, j, similarity))
        
        # Sort pairs by similarity (highest first)
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Helper function to create Union-Find data structure for grouping
        def make_union_find(n):
            parent = list(range(n))
            rank = [0] * n
            
            def find(x):
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]
                
            def union(x, y):
                root_x = find(x)
                root_y = find(y)
                if root_x == root_y:
                    return
                if rank[root_x] < rank[root_y]:
                    parent[root_x] = root_y
                else:
                    parent[root_y] = root_x
                    if rank[root_x] == rank[root_y]:
                        rank[root_x] += 1
                        
            return find, union
        
        # Create Union-Find structures for each threshold
        n = len(image_data)
        find_exact, union_exact = make_union_find(n)
        find_similar, union_similar = make_union_find(n)
        find_variant, union_variant = make_union_find(n)
        
        # Group images using the Union-Find data structure
        print("Grouping similar images...")
        
        # First pass: connect components
        for i, j, similarity in pairs:
            if similarity >= exact_threshold:
                union_exact(i, j)
                union_similar(i, j)
                union_variant(i, j)
            elif similarity >= similar_threshold:
                union_similar(i, j)
                union_variant(i, j)
            elif similarity >= variant_threshold:
                union_variant(i, j)
        
        # Second pass: collect groups
        groups_exact = defaultdict(list)
        groups_similar = defaultdict(list)
        groups_variant = defaultdict(list)
        
        for i in range(n):
            groups_exact[find_exact(i)].append(i)
            groups_similar[find_similar(i)].append(i)
            groups_variant[find_variant(i)].append(i)
        
        # Convert to list of groups and filter out singletons (non-duplicates)
        exact_groups = [indices for indices in groups_exact.values() if len(indices) > 1]
        similar_groups = [indices for indices in groups_similar.values() if len(indices) > 1]
        variant_groups = [indices for indices in groups_variant.values() if len(indices) > 1]
        
        # Sort groups by size (largest first)
        exact_groups.sort(key=len, reverse=True)
        similar_groups.sort(key=len, reverse=True)
        variant_groups.sort(key=len, reverse=True)
        
        # Create final structured groups
        # Format: [{group_type, images: [{path, filename, size, dimensions, similarity}, ...]}]
        
        # Helper function to format a group
        def format_group(indices, group_type, base_similarity):
            group_data = []
            base_index = indices[0]  # Use first image as reference
            base_image = image_data[base_index]
            
            for idx in indices:
                img = image_data[idx]
                # Calculate similarity to base image for display
                if idx == base_index:
                    similarity = 1.0  # Base image is 100% similar to itself
                else:
                    # Use pre-calculated similarity if available, or estimate based on threshold
                    similarity = next((s for i, j, s in pairs if (i == base_index and j == idx) or (i == idx and j == base_index)), base_similarity)
                
                group_data.append({
                    'path': img['path'],
                    'filename': img['filename'],
                    'size': img['size'],
                    'dimensions': img['dimensions'],
                    'size_readable': self._format_file_size(img['size']),
                    'similarity': round(similarity, 4),
                    'primary_hash': img['primary_hash'],
                    'secondary_hash': img.get('secondary_hash', ''),
                    'is_base': idx == base_index
                })
            
            return {
                'group_type': group_type,
                'base_image': base_image['path'],
                'image_count': len(indices),
                'total_size': sum(image_data[idx]['size'] for idx in indices),
                'duplicated_size': sum(image_data[idx]['size'] for idx in indices[1:]),  # Excluding base image
                'images': group_data
            }
        
        # Format all groups
        for group_indices in exact_groups:
            groups['exact'].append(format_group(group_indices, 'exact', exact_threshold))
            
        # Only include similar groups that aren't already covered by exact groups
        exact_indices_flat = {idx for group in exact_groups for idx in group}
        for group_indices in similar_groups:
            # Skip if all indices are already in exact groups
            if all(idx in exact_indices_flat for idx in group_indices):
                continue
            # Skip if only one image is not in exact groups
            non_exact_indices = [idx for idx in group_indices if idx not in exact_indices_flat]
            if len(non_exact_indices) <= 1:
                continue
            groups['similar'].append(format_group(group_indices, 'similar', similar_threshold))
            
        # Similarly filter variant groups
        # Create a set of all paths from similar groups
        similar_paths = {img['path'] for group in groups['similar'] for img in group['images']}
        
        # Find indices in image_data that correspond to these paths
        similar_indices_flat = exact_indices_flat.union({
            i for i, img_data in enumerate(image_data) if img_data['path'] in similar_paths
        })
        for group_indices in variant_groups:
            non_similar_indices = [idx for idx in group_indices if idx not in similar_indices_flat]
            if len(non_similar_indices) <= 1:
                continue
            groups['variant'].append(format_group(group_indices, 'variant', variant_threshold))
        
        # Update stats
        stats["exact_duplicates"] = sum(group['image_count'] - 1 for group in groups['exact'])
        stats["similar_images"] = sum(group['image_count'] - 1 for group in groups['similar'])
        stats["variant_images"] = sum(group['image_count'] - 1 for group in groups['variant'])
        stats["total_savings_bytes"] = sum(group['duplicated_size'] for group in groups['exact'])
        
        print(f"Found {stats['exact_duplicates']} exact duplicates in {len(groups['exact'])} groups")
        print(f"Found {stats['similar_images']} similar images in {len(groups['similar'])} groups")
        print(f"Found {stats['variant_images']} variant images in {len(groups['variant'])} groups")
        
        return groups

    def _create_duplicates_folder(self, output_folder, output_folder_location, base_image_path=None):
        """Create folder for duplicate files"""
        if output_folder_location == "original_folder" and base_image_path:
            # Place duplicates folder inside the original image's folder
            base_dir = os.path.dirname(base_image_path)
            duplicates_path = os.path.join(base_dir, output_folder)
        else:
            # Default: ComfyUI output directory
            if os.path.isabs(output_folder):
                duplicates_path = output_folder
            else:
                duplicates_path = os.path.join(self.output_dir, output_folder)
        os.makedirs(duplicates_path, exist_ok=True)
        return duplicates_path

    def _handle_duplicates(
        self,
        groups,
        duplicates_path,
        duplicate_action,
        keep_largest,
        group_by_similarity,
        stats,
        output_folder,
        output_folder_location,
        root_folder  
    ):

        """
        Move or copy duplicate images into organized output folders.

        Args:
            root_folder: The original root directory scanned. Used to ensure output folders
                        are always created relative to the original source, not the current
                        location of the images.
        """

        files_handled = 0
        handled_files = set()

        for group_type in ['exact', 'similar', 'variant']:
            for group_idx, group in enumerate(groups[group_type]):
                if keep_largest:
                    base_image = max(group['images'], key=lambda x: x['size'])['path']
                else:
                    base_image = group['base_image']

                if output_folder_location == "original_folder":
                    # Output folder is always relative to the original root folder
                    rel_path = os.path.relpath(os.path.dirname(base_image), root_folder)
                    group_folder = os.path.join(root_folder, rel_path, output_folder, group_type)
                else:
                    group_folder = os.path.join(duplicates_path, group_type)

                subgroup_folder = os.path.join(group_folder, f"group_{group_idx+1}")
                os.makedirs(subgroup_folder, exist_ok=True)

                for img in group['images']:
                    if group_type == 'exact' and img['path'] == base_image:
                        continue
                    if img['path'] in handled_files:
                        continue

                    dest_filename = os.path.basename(img['path'])
                    dest_path = os.path.join(subgroup_folder, dest_filename)

                    if os.path.exists(dest_path):
                        base_name, ext = os.path.splitext(dest_filename)
                        dest_path = os.path.join(subgroup_folder, f"{base_name}_dup{ext}")
                        if os.path.exists(dest_path):
                            timestamp = int(time.time())
                            dest_path = os.path.join(subgroup_folder, f"{base_name}_{timestamp}{ext}")

                    try:
                        if duplicate_action == "move":
                            shutil.move(img['path'], dest_path)
                            stats["files_moved"] += 1
                        else:
                            shutil.copy2(img['path'], dest_path)
                            stats["files_copied"] += 1

                        files_handled += 1
                        handled_files.add(img['path'])
                    except Exception as e:
                        print(f"Error {duplicate_action}ing file {img['path']}: {e}")

        print(f"Total files {duplicate_action}d: {files_handled}")
        return files_handled

    def _save_results(self, groups, stats, results_format):
        """Save duplicate finder results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_filename = f"duplicate_results_{timestamp}"
        results_path = ""
        
        try:
            # Create results directory if it doesn't exist
            os.makedirs(self.results_dir, exist_ok=True)
            
            # Save as JSON
            if results_format in ["json", "both"]:
                json_path = os.path.join(self.results_dir, f"{results_filename}.json")
                
                # Prepare data for JSON serialization
                json_data = {
                    "stats": stats,
                    "groups": groups
                }
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                results_path = json_path
                print(f"Results saved to: {json_path}")
            
            # Save as CSV
            if results_format in ["csv", "both"]:
                csv_path = os.path.join(self.results_dir, f"{results_filename}.csv")
                
                with open(csv_path, 'w', encoding='utf-8') as f:
                    # Write header
                    f.write("Group Type,Base Image,File Path,Filename,Size,Dimensions,Similarity\n")
                    
                    # Write data for each group
                    for group_type in ['exact', 'similar', 'variant']:
                        for group in groups[group_type]:
                            base_image = group['base_image']
                            
                            for img in group['images']:
                                f.write(f"{group_type},{base_image},{img['path']},{img['filename']},")
                                f.write(f"{img['size']},{img.get('dimensions', '')},{img['similarity']}\n")
                
                if results_format == "csv":
                    results_path = csv_path
                    print(f"Results saved to: {csv_path}")
            
            return results_path
        
        except Exception as e:
            print(f"Error saving results: {e}")
            return ""

    def _format_groups_for_display(self, groups, display_top_n):
        """Format groups for display in the UI"""
        summary = []
        total_groups = 0
        total_duplicates = 0
        
        # Add header
        summary.append("=== Duplicate Image Analysis Results ===")
        
        # Process each group type
        for group_type in ['exact', 'similar', 'variant']:
            groups_count = len(groups[group_type])
            if groups_count == 0:
                continue
                
            duplicates_count = sum(group['image_count'] - 1 for group in groups[group_type])
            total_groups += groups_count
            total_duplicates += duplicates_count
            
            summary.append(f"\n--- {group_type.capitalize()} Duplicates: {duplicates_count} images in {groups_count} groups ---")
            
            # Show top N groups
            for i, group in enumerate(groups[group_type][:display_top_n]):
                base_image = os.path.basename(group['base_image'])
                dup_count = group['image_count'] - 1
                dup_size = self._format_file_size(group['duplicated_size'])
                
                summary.append(f"\nGroup {i+1}: {dup_count} duplicates of '{base_image}' ({dup_size})")
                
                # List first few duplicates
                shown = 0
                for img in group['images'][1:]:  # Skip base image
                    if shown >= 5:  # Show max 5 examples per group
                        summary.append(f"  ... and {dup_count - shown} more")
                        break
                        
                    filename = os.path.basename(img['path'])
                    similarity = f"{img['similarity'] * 100:.1f}%"
                    summary.append(f"  - {filename} (Similarity: {similarity})")
                    shown += 1
            
            # If there are more groups than we displayed
            if groups_count > display_top_n:
                summary.append(f"\n... and {groups_count - display_top_n} more groups")
        
        # Add overall summary
        if total_groups > 0:
            summary.append(f"\n=== Total: {total_duplicates} duplicate images in {total_groups} groups ===")
        else:
            summary.append("\n=== No duplicate images found ===")
        
        return "\n".join(summary)

    def _update_similarity_metadata(self, groups, stats):
        """Update image metadata with similarity information"""
        if not self.metadata_service:
            return
            
        total_updated = 0
        
        # Process all groups
        for group_type in ['exact', 'similar', 'variant']:
            for group in groups[group_type]:
                base_path = group['base_image']
                base_name = os.path.basename(base_path)
                
                # Update each image in the group
                for img_data in group['images']:
                    img_path = img_data['path']
                    
                    # Skip if it's the same file (redundant metadata)
                    if img_path == base_path and len(group['images']) > 1:
                        continue
                        
                    try:
                        # Create similarity metadata
                        similarity_metadata = {
                            'eiqa': {
                                'technical': {
                                    'matches': [{
                                        'path': base_name,  # Store just filename, not full path
                                        'similarity_score': img_data['similarity'],
                                        'match_type': group_type,
                                        'primary_hash': img_data['primary_hash']
                                    }]
                                }
                            }
                        }
                        
                        # Set resource identifier
                        filename = os.path.basename(img_path)
                        resource_uri = f"file:///{filename}"
                        self.metadata_service.set_resource_identifier(resource_uri)
                        
                        # Write metadata
                        self.metadata_service.write_metadata(
                            img_path,
                            similarity_metadata,
                            targets=['embedded', 'xmp', 'database']
                        )
                        
                        total_updated += 1
                        
                    except Exception as e:
                        print(f"Error updating similarity metadata for {img_path}: {e}")
        
        stats["metadata_updated"] = total_updated
        print(f"Updated similarity metadata for {total_updated} images")
        return total_updated

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Duplicate_Image_Finder_v04": ImageDuplicateFinder,  
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Duplicate_Image_Finder_v04": "Eric Duplicate Image Finder v04",
}