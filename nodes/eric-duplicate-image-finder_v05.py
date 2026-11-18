"""
ComfyUI Node: Image Duplicate Finder Node v0.5
Description: 
This node scans folders of images, identifies duplicates and similar images using perceptual hashing,
and provides various options for handling them. Integration with the metadata system allows for
storing and retrieving hash data.

Features:
- Multiple hash algorithm support (phash, dhash, average_hash, whash-haar, colorhash)
- Multi-level similarity detection (exact, similar, variant)
- Scale-invariant detection for upscaled/downscaled images
- Parallel processing for faster comparison on multi-core systems
- Calibration mode to analyze similarity distribution and suggest thresholds
- Filename and metadata-based similarity enhancement
- Integrated with metadata system using the 'eiqa.technical' namespace
- Options for moving, copying, or deleting duplicate files
- Detailed progress reporting during comparison phase
- Detailed reporting and statistics

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.5.0

Date: [February 2026]
License: Dual License (Non-Commercial and Commercial Use)
"""

# Console output goes through one switch (see aaa_meta/console.py): problems are always shown,
# everything else only with the node's debug option on or AAA_META_VERBOSE=1.
try:
    from ..aaa_meta.console import quiet_print as print, note_error as _note_error
except Exception:                                    # used outside the pack
    def _note_error(error, where=""):
        pass

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
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing
import math

# Check for imagehash library
try:
    import imagehash
except ImportError:
    print("Warning: imagehash library not installed. Please install it with:")
    print("pip install imagehash")
    imagehash = None

# Import metadata service if available
try:
    from ..eric_metadata.service import MetadataService
    METADATA_SYSTEM_AVAILABLE = True
except ImportError:
    print("Note: Eric's metadata system not found. Will use basic metadata handling.")
    METADATA_SYSTEM_AVAILABLE = False

class ImageDuplicateFinder:
    @classmethod
    def INPUT_TYPES(cls):
        # Get CPU count for parallel processing default
        cpu_count = multiprocessing.cpu_count()
        
        inputs = {
            "required": {
                "folder_path": ("STRING", {"default": "", "tooltip": "Main folder to scan for images."}),
                "primary_hash": (["phash", "average_hash", "dhash", "whash-haar", "colorhash"], {"default": "phash", "tooltip": "Primary hash algorithm. phash is best all-around, colorhash helps with color-similar variants."}),
                "exact_duplicate_threshold": ("FLOAT", {"default": 0.975, "min": 0.5, "max": 1.0, "step": 0.005, "tooltip": "Threshold for exact duplicates. 0.97-0.99 recommended. Higher = stricter matching."}),
                "similar_image_threshold": ("FLOAT", {"default": 0.945, "min": 0.3, "max": 1.0, "step": 0.005, "tooltip": "Threshold for similar images (resized, minor edits). 0.90-0.96 range."}),
                "variant_threshold": ("FLOAT", {"default": 0.86, "min": 0.3, "max": 1.0, "step": 0.005, "tooltip": "Threshold for variants (related but different). 0.80-0.90 range."}),
            },
            "optional": {
                "recursive": ("BOOLEAN", {"default": True, "tooltip": "Set True to scan subfolders recursively."}),
                "additional_folders": ("STRING", {"default": "", "multiline": True, 
                                     "placeholder": "Scan extra folders. Put only one folder path per line"}),
                "secondary_hash": (["none", "phash", "average_hash", "dhash", "whash-haar", "colorhash"], {"default": "dhash", "tooltip": "A second hash improves accuracy. dhash recommended with phash primary."}),
                "min_dimensions": ("STRING", {"default": "0x0", "placeholder": "WIDTHxHEIGHT", "tooltip": "Minimum dimensions to include ie 100x100. Can speed up runs."}),
                "analyze_filename": ("BOOLEAN", {"default": True, "tooltip": "Factor filename patterns into similarity (detects '_upscaled', '(1)' copies, etc)."}),
                "analyze_metadata": ("BOOLEAN", {"default": True, "tooltip": "Use metadata (dimensions, dates, AI seeds) to improve matching."}),
                "metadata_weight": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "Weight of metadata/filename analysis. 0.2-0.4 recommended."}),
                "scale_invariant": ("BOOLEAN", {"default": True, "tooltip": "Boost similarity for images that appear to be scaled versions of each other."}),
                "save_hashes": ("BOOLEAN", {"default": True, "tooltip": "Save hashes to metadata for faster future runs."}),
                "calibration_mode": ("BOOLEAN", {"default": False, "tooltip": "Run calibration to analyze similarity distribution and suggest optimal thresholds."}),
                "parallel_workers": ("INT", {"default": 0, "min": 0, "max": 64, "step": 1, "tooltip": "Number of parallel workers for comparison. 0 = auto-detect (uses CPU cores)."}),
                "duplicate_action": (["move", "copy", "delete", "none"], {"default": "none", "tooltip": "Action for duplicates. 'delete' requires confirmation and keeps largest file."}),
                "output_folder_location": (["comfyui_output", "original_folder"], {"default": "comfyui_output","tooltip": "Where to save: ComfyUI output creates duplicates/, similar/, variants/ folders there; original_folder creates them next to source images."}),
                "group_by_similarity": ("BOOLEAN", {"default": True}),
                "keep_largest": ("BOOLEAN", {"default": True, "tooltip": "Keep the largest file in each group, move/copy/delete the smaller ones."}),
                "update_metadata": ("BOOLEAN", {"default": True}),
                "save_results": ("BOOLEAN", {"default": True, "tooltip": "Save detailed results to file."}),
                "results_format": (["json", "csv", "both"], {"default": "json"}),
                "display_top_n": ("INT", {"default": 20, "min": 0, "max": 100, "step": 5, "tooltip": "Number of duplicate groups to show in output."}),
                "confirm_delete": ("BOOLEAN", {"default": False, "tooltip": "REQUIRED for delete action. Set True to confirm deletion of duplicate files."}),
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
                       scale_invariant=True, save_hashes=True, calibration_mode=False,
                       parallel_workers=0,
                       duplicate_action="none", 
                       output_folder_location="comfyui_output", 
                       group_by_similarity=True, keep_largest=True,
                       update_metadata=True, save_results=True, results_format="json",
                       display_top_n=20, confirm_delete=False):
        """
        Main function to find and handle duplicate images
        """
        start_time = time.time()
        
        # Safety check for delete action
        if duplicate_action == "delete" and not confirm_delete:
            return "ERROR: Delete action requires confirm_delete=True for safety. Please enable confirm_delete to proceed.", 0, json.dumps({"error": "Delete not confirmed"}), ""
        
        # Configure parallel workers
        if parallel_workers == 0:
            parallel_workers = max(1, multiprocessing.cpu_count() - 2)  # Leave 2 cores free
        print(f"Using {parallel_workers} parallel workers for comparison")
        
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
        if secondary_hash != "none":
            print(f"Using secondary hash algorithm: {secondary_hash}")
        print(f"Scale-invariant mode: {scale_invariant}")
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
            "files_deleted": 0,
            "hashes_saved": 0,
            "metadata_updated": 0,
            "total_savings_bytes": 0,
            "parallel_workers": parallel_workers,
            "calibration_mode": calibration_mode,
            "error": None
        }
        
        # Print output location info
        if duplicate_action in ["move", "copy"]:
            if output_folder_location == "comfyui_output":
                print(f"Duplicate files will be {duplicate_action}d to: {self.output_dir}/[duplicates|similar|variants]/")
            else:
                print(f"Duplicate files will be {duplicate_action}d to folders next to original images")
        
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
            groups, calibration_data = self._group_similar_images(
                image_data,
                exact_duplicate_threshold,
                similar_image_threshold,
                variant_threshold,
                analyze_filename,
                metadata_weight,
                scale_invariant,
                parallel_workers,
                calibration_mode,
                stats
            )
            
            # If calibration mode, return calibration results instead
            if calibration_mode:
                calibration_report = self._format_calibration_report(calibration_data, stats)
                stats["duration_seconds"] = round(time.time() - start_time, 2)
                return calibration_report, 0, json.dumps(stats, indent=2), ""
            
            # 4. Handle duplicates (move/copy/delete if requested)
            if duplicate_action in ["move", "copy", "delete"]:
                self._handle_duplicates(
                    groups, 
                    duplicate_action, 
                    keep_largest,
                    group_by_similarity,
                    stats,
                    output_folder_location,
                    root_folder
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
                                except Exception as _caught:
                                    # If dimensions parsing fails, we'll get them by opening the image
                                    _note_error(_caught, "eric-duplicate-image-finder_v05.py:383")
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
                    
                    # Detect if image is color or grayscale/B&W
                    # This is important: B&W version of color image should NOT be exact duplicate
                    try:
                        if img.mode == 'L' or img.mode == '1':
                            file_info['is_grayscale'] = True
                        elif img.mode in ('RGB', 'RGBA', 'P'):
                            # Check if it's actually grayscale stored as RGB
                            # Sample some pixels to check if R=G=B
                            img_rgb = img.convert('RGB')
                            pixels = list(img_rgb.getdata())
                            sample_size = min(100, len(pixels))
                            sample = pixels[::max(1, len(pixels)//sample_size)][:sample_size]
                            grayscale_count = sum(1 for r, g, b in sample if abs(r-g) < 10 and abs(g-b) < 10 and abs(r-b) < 10)
                            file_info['is_grayscale'] = grayscale_count > sample_size * 0.95
                        else:
                            file_info['is_grayscale'] = False
                    except Exception as _caught:
                        _note_error(_caught, "eric-duplicate-image-finder_v05.py:446")
                        file_info['is_grayscale'] = False
                    
                    # Calculate primary hash
                    if primary_hash == "phash":
                        hash_value = imagehash.phash(img)
                    elif primary_hash == "dhash":
                        hash_value = imagehash.dhash(img)
                    elif primary_hash == "whash-haar":
                        hash_value = imagehash.whash(img)
                    elif primary_hash == "colorhash":
                        hash_value = imagehash.colorhash(img)
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
                        elif secondary_hash == "colorhash":
                            secondary_hash_value = imagehash.colorhash(img)
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
        """
        Calculate filename similarity score based on sequence patterns.
        
        This function is designed to identify images that are part of the same set/sequence,
        NOT just images with similar prefixes.
        
        High similarity (0.8+): 
            - "photo-001.jpg" and "photo-002.jpg" (same base, sequential numbers)
            - "image_v1.jpg" and "image_v2.jpg" (version variants)
            - "test (1).jpg" and "test (2).jpg" (copy patterns)
            
        Low similarity (0.0-0.3):
            - "EXCLUSIVE_Paris.jpg" and "EXCLUSIVE_London.jpg" (different subjects)
            - "comfyui_test.jpg" and "comfyui_portrait.jpg" (different content)
        """
        import re
        
        # Get base names without extensions
        base1 = os.path.splitext(filename1)[0]
        base2 = os.path.splitext(filename2)[0]
        
        # Exact match
        if base1 == base2:
            return 1.0
        
        # Pattern 1: Sequential numbering at the end
        # Matches: name-001, name_001, name001, name (1), name[1]
        seq_pattern = r'^(.+?)[-_\s]?[\(\[]?(\d{1,4})[\)\]]?$'
        
        match1 = re.match(seq_pattern, base1)
        match2 = re.match(seq_pattern, base2)
        
        if match1 and match2:
            prefix1, num1 = match1.groups()
            prefix2, num2 = match2.groups()
            
            # If the prefixes match exactly (ignoring trailing separators), they're a sequence
            prefix1_clean = re.sub(r'[-_\s]+$', '', prefix1)
            prefix2_clean = re.sub(r'[-_\s]+$', '', prefix2)
            
            if prefix1_clean.lower() == prefix2_clean.lower():
                # Same sequence - high similarity
                return 0.9
        
        # Pattern 2: Version suffixes (v1, v2, _v1, -v2, etc.)
        version_pattern = r'^(.+?)[-_]?v(\d+)$'
        
        vmatch1 = re.match(version_pattern, base1, re.IGNORECASE)
        vmatch2 = re.match(version_pattern, base2, re.IGNORECASE)
        
        if vmatch1 and vmatch2:
            vprefix1 = vmatch1.group(1)
            vprefix2 = vmatch2.group(1)
            
            if vprefix1.lower() == vprefix2.lower():
                return 0.85
        
        # Pattern 3: Common modification suffixes (upscaled, enhanced, etc.)
        # These indicate the SAME image was modified
        mod_suffixes = [
            '_upscaled', '-upscaled', '_enhanced', '-enhanced',
            '_fixed', '-fixed', '_edited', '-edited', 
            '_copy', '-copy', '_2x', '-2x', '_4x', '-4x',
            '_hires', '-hires', '_lowres', '-lowres'
        ]
        
        def strip_mod_suffix(name):
            name_lower = name.lower()
            for suffix in mod_suffixes:
                if name_lower.endswith(suffix):
                    return name[:-len(suffix)]
            return name
        
        stripped1 = strip_mod_suffix(base1)
        stripped2 = strip_mod_suffix(base2)
        
        # If stripping suffixes makes them match, they're variants of same image
        if stripped1.lower() == stripped2.lower():
            return 0.9
        
        # Pattern 4: One is base, other has suffix
        if base1.lower() == stripped2.lower() or base2.lower() == stripped1.lower():
            return 0.85
        
        # Pattern 5: Copy pattern "(n)" anywhere
        copy_pattern = r'^(.+?)\s*\(\d+\)(.*)$'
        
        cmatch1 = re.match(copy_pattern, base1)
        cmatch2 = re.match(copy_pattern, base2)
        
        # Get the base without copy numbers
        def get_copy_base(name, match):
            if match:
                return match.group(1) + match.group(2)
            return name
        
        copy_base1 = get_copy_base(base1, cmatch1)
        copy_base2 = get_copy_base(base2, cmatch2)
        
        if copy_base1.lower() == copy_base2.lower():
            return 0.9
        
        # If one is the copy base of the other
        if base1.lower() == copy_base2.lower() or base2.lower() == copy_base1.lower():
            return 0.85
        
        # NO MATCH on sequence patterns - these are likely different images
        # that just happen to share a prefix
        
        # Only give low similarity for Levenshtein closeness, and only if
        # the names are quite similar (>80% character match)
        distance = self._levenshtein_distance(base1.lower(), base2.lower())
        max_len = max(len(base1), len(base2))
        
        if max_len > 0:
            similarity = 1 - (distance / max_len)
            # Only return meaningful similarity if very close (likely typos or minor diffs)
            # Otherwise return 0 - they're just different files with similar prefixes
            if similarity > 0.85:
                return similarity * 0.5  # Scale down since it's not a confirmed pattern
        
        # Default: not similar enough to matter
        return 0.0

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
            except Exception as _caught:
                _note_error(_caught, "eric-duplicate-image-finder_v05.py:823")
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

    def _is_scaled_version(self, info1, info2):
        """Check if two images appear to be scaled versions of each other"""
        if 'width' not in info1 or 'width' not in info2:
            return False, 1.0
            
        w1, h1 = info1['width'], info1['height']
        w2, h2 = info2['width'], info2['height']
        
        if w1 == 0 or h1 == 0 or w2 == 0 or h2 == 0:
            return False, 1.0
            
        # Calculate aspect ratios
        ratio1 = w1 / h1
        ratio2 = w2 / h2
        
        # Check if aspect ratios are very similar (within 2%)
        ratio_diff = abs(ratio1 - ratio2) / max(ratio1, ratio2)
        if ratio_diff > 0.02:
            return False, 1.0
            
        # Calculate scale factor
        scale_w = max(w1, w2) / min(w1, w2)
        scale_h = max(h1, h2) / min(h1, h2)
        
        # If width and height scale similarly, it's likely a scaled version
        if abs(scale_w - scale_h) < 0.05:  # Within 5% of same scale
            # Return boost factor based on how clean the scale is
            # Common scales like 2x, 1.5x, 4x get higher boost
            avg_scale = (scale_w + scale_h) / 2
            
            # Check for common upscale factors
            common_scales = [1.5, 2.0, 2.5, 3.0, 4.0, 8.0]
            for cs in common_scales:
                if abs(avg_scale - cs) < 0.1:
                    return True, 0.08  # Strong boost for common scale factors
                    
            # Any other clean scale
            if avg_scale > 1.1:  # At least 10% size difference
                return True, 0.05  # Moderate boost
                
        return False, 0.0

    def _compute_pair_similarity(self, args):
        """Compute similarity for a single pair - designed for parallel execution"""
        i, j, info1, info2, analyze_filename, metadata_weight, scale_invariant = args
        
        # Calculate primary hash similarity
        hash_similarity = self._hamming_distance(info1['primary_hash'], info2['primary_hash'])
        
        # Early exit for very dissimilar hashes (optimization)
        if hash_similarity < 0.5:
            return (i, j, hash_similarity)
        
        # Calculate secondary hash similarity if available
        secondary_similarity = 0
        if 'secondary_hash' in info1 and 'secondary_hash' in info2:
            secondary_similarity = self._hamming_distance(info1['secondary_hash'], info2['secondary_hash'])
            
        # Combine hash similarities (if secondary hash exists)
        if secondary_similarity > 0:
            hash_similarity = 0.7 * hash_similarity + 0.3 * secondary_similarity
        
        # Initialize overall similarity with hash similarity
        similarity = hash_similarity
        
        # CRITICAL CHECK: Color vs Grayscale mismatch
        # A B&W version of a color image should NOT be an exact duplicate!
        # This catches cases where perceptual hash sees them as identical
        is_grayscale1 = info1.get('is_grayscale', False)
        is_grayscale2 = info2.get('is_grayscale', False)
        
        if is_grayscale1 != is_grayscale2:
            # One is color, one is grayscale - cap similarity at "similar" level, not "exact"
            # This prevents a B&W conversion from being marked as an exact duplicate
            similarity = min(similarity, 0.94)  # Below typical exact threshold
        
        # Apply scale-invariant boost if images appear to be scaled versions
        if scale_invariant:
            is_scaled, boost = self._is_scaled_version(info1, info2)
            if is_scaled:
                similarity = min(1.0, similarity + boost)
        
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
        
        return (i, j, similarity)

    def _group_similar_images(self, image_data, exact_threshold, similar_threshold, variant_threshold,
                             analyze_filename, metadata_weight, scale_invariant, parallel_workers,
                             calibration_mode, stats):
        """Group images based on similarity scores with parallel processing"""
        # Print thresholds
        print(f"Grouping with thresholds: Exact={exact_threshold}, Similar={similar_threshold}, Variant={variant_threshold}")
        
        # Create a list to store groups
        groups = {
            'exact': [],
            'similar': [],
            'variant': []
        }
        
        # Calibration data for analyzing similarity distribution
        calibration_data = {
            'all_scores': [],
            'high_scores': [],  # > 0.7
            'score_histogram': {},
            'suggested_thresholds': {}
        }
        
        # Skip if no images to process
        if len(image_data) <= 1:
            return groups, calibration_data
            
        n = len(image_data)
        total_pairs = n * (n - 1) // 2
        print(f"Calculating similarity for {total_pairs:,} image pairs...")
        
        start_compare_time = time.time()
        
        # FAST PATH: Pre-convert all hashes to numpy arrays for vectorized comparison
        print("  Converting hashes to binary arrays...")
        
        # Convert hash strings to binary arrays (64 bits each for standard hashes)
        hash_arrays = []
        for img in image_data:
            hash_str = img['primary_hash']
            # Remove 0x prefix if present
            if hash_str.startswith('0x'):
                hash_str = hash_str[2:]
            try:
                hash_int = int(hash_str, 16)
                # Convert to binary array (64 bits)
                bits = np.array([(hash_int >> i) & 1 for i in range(63, -1, -1)], dtype=np.uint8)
                hash_arrays.append(bits)
            except Exception as _caught:
                # Fallback for unusual hash formats
                _note_error(_caught, "eric-duplicate-image-finder_v05.py:984")
                hash_arrays.append(np.zeros(64, dtype=np.uint8))
        
        hash_matrix = np.array(hash_arrays, dtype=np.uint8)  # Shape: (n, 64)
        
        # Also prepare secondary hashes if available
        has_secondary = all('secondary_hash' in img for img in image_data)
        if has_secondary:
            sec_hash_arrays = []
            for img in image_data:
                hash_str = img.get('secondary_hash', '0')
                if hash_str.startswith('0x'):
                    hash_str = hash_str[2:]
                try:
                    hash_int = int(hash_str, 16)
                    bits = np.array([(hash_int >> i) & 1 for i in range(63, -1, -1)], dtype=np.uint8)
                    sec_hash_arrays.append(bits)
                except Exception as _caught:
                    _note_error(_caught, "eric-duplicate-image-finder_v05.py:1002")
                    sec_hash_arrays.append(np.zeros(64, dtype=np.uint8))
            sec_hash_matrix = np.array(sec_hash_arrays, dtype=np.uint8)
        
        # Pre-extract grayscale flags
        grayscale_flags = np.array([img.get('is_grayscale', False) for img in image_data], dtype=bool)
        
        # Pre-extract dimensions for scale detection
        widths = np.array([img.get('width', 0) for img in image_data], dtype=np.float32)
        heights = np.array([img.get('height', 0) for img in image_data], dtype=np.float32)
        
        print("  Computing pairwise similarities (vectorized)...")
        
        # Process in batches for memory efficiency and progress reporting
        pairs = []
        batch_size = min(500, n)  # Process 500 images at a time against all others
        
        for batch_start in range(0, n, batch_size):
            batch_end = min(batch_start + batch_size, n)
            
            # For each image in batch, compare against all images with higher index
            for i in range(batch_start, batch_end):
                if i >= n - 1:
                    continue
                    
                # Compare image i against all images j > i using vectorized XOR
                j_indices = np.arange(i + 1, n)
                
                # Hamming distance: count differing bits
                # XOR gives 1 where bits differ, sum counts differences
                xor_result = np.bitwise_xor(hash_matrix[i], hash_matrix[j_indices])
                hamming_distances = np.sum(xor_result, axis=1)
                
                # Convert to similarity (1.0 = identical, 0.0 = completely different)
                primary_similarities = 1.0 - (hamming_distances / 64.0)
                
                # Add secondary hash if available
                if has_secondary:
                    sec_xor = np.bitwise_xor(sec_hash_matrix[i], sec_hash_matrix[j_indices])
                    sec_hamming = np.sum(sec_xor, axis=1)
                    sec_similarities = 1.0 - (sec_hamming / 64.0)
                    # Combine: 70% primary, 30% secondary
                    similarities = 0.7 * primary_similarities + 0.3 * sec_similarities
                else:
                    similarities = primary_similarities
                
                # Apply color/grayscale penalty
                # If one is grayscale and other is color, cap at 0.94
                color_mismatch = grayscale_flags[i] != grayscale_flags[j_indices]
                similarities = np.where(color_mismatch, np.minimum(similarities, 0.94), similarities)
                
                # Apply scale detection boost
                if scale_invariant:
                    # Check aspect ratio similarity
                    ratio_i = widths[i] / heights[i] if heights[i] > 0 else 0
                    ratios_j = np.divide(widths[j_indices], heights[j_indices], 
                                        out=np.zeros_like(widths[j_indices]), 
                                        where=heights[j_indices] > 0)
                    
                    # Aspect ratios within 2% are potential scale matches
                    ratio_diff = np.abs(ratio_i - ratios_j) / np.maximum(ratio_i, ratios_j + 1e-10)
                    potential_scales = ratio_diff < 0.02
                    
                    # For potential scales, add small boost
                    similarities = np.where(potential_scales, np.minimum(similarities + 0.05, 1.0), similarities)
                
                # Store pairs that meet minimum threshold (optimization: skip very low scores)
                for idx, j in enumerate(j_indices):
                    sim = float(similarities[idx])
                    if sim >= variant_threshold * 0.9:  # Keep anything close to variant threshold
                        pairs.append((i, int(j), sim))
                    elif calibration_mode:
                        # In calibration mode, track all scores for histogram
                        calibration_data['all_scores'].append(sim)
                        if sim > 0.7:
                            calibration_data['high_scores'].append(sim)
                        bucket = int(sim * 10) / 10
                        calibration_data['score_histogram'][bucket] = calibration_data['score_histogram'].get(bucket, 0) + 1
            
            # Progress report
            progress_pct = batch_end / n * 100
            elapsed = time.time() - start_compare_time
            if batch_end < n:
                eta = elapsed / (batch_end / n) - elapsed
                print(f"  Progress: {progress_pct:.0f}% - ETA: {eta:.0f}s")
        
        # Apply filename similarity boost for high-scoring pairs only (expensive operation)
        if analyze_filename:
            print("  Applying filename analysis to candidate pairs...")
            enhanced_pairs = []
            for i, j, sim in pairs:
                if sim >= variant_threshold * 0.95:  # Only for viable candidates
                    filename_sim = self._filename_similarity(image_data[i]['filename'], image_data[j]['filename'])
                    if filename_sim > 0.5:
                        sim = (1 - metadata_weight) * sim + metadata_weight * filename_sim
                enhanced_pairs.append((i, j, sim))
            pairs = enhanced_pairs
        
        # Calibration data collection for pairs we kept
        if calibration_mode:
            for _, _, sim in pairs:
                calibration_data['all_scores'].append(sim)
                if sim > 0.7:
                    calibration_data['high_scores'].append(sim)
                bucket = int(sim * 10) / 10
                calibration_data['score_histogram'][bucket] = calibration_data['score_histogram'].get(bucket, 0) + 1
        
        compare_time = time.time() - start_compare_time
        print(f"Comparison complete in {compare_time:.1f}s ({total_pairs/compare_time:,.0f} pairs/sec)")
        
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
        
        # Generate calibration suggestions if in calibration mode
        if calibration_mode and calibration_data['all_scores']:
            scores = sorted(calibration_data['all_scores'], reverse=True)
            
            # Find natural breaks in the data
            # Look for the top percentiles
            if len(scores) > 0:
                p999 = scores[int(len(scores) * 0.001)] if len(scores) > 1000 else scores[0]
                p99 = scores[int(len(scores) * 0.01)] if len(scores) > 100 else scores[0]
                p95 = scores[int(len(scores) * 0.05)] if len(scores) > 20 else scores[0]
                p90 = scores[int(len(scores) * 0.10)] if len(scores) > 10 else scores[0]
                
                calibration_data['suggested_thresholds'] = {
                    'exact': round(max(0.95, p999 - 0.01), 3),
                    'similar': round(max(0.85, p99 - 0.02), 3),
                    'variant': round(max(0.70, p95 - 0.03), 3),
                    'percentiles': {
                        'p0.1': round(p999, 4),
                        'p1': round(p99, 4),
                        'p5': round(p95, 4),
                        'p10': round(p90, 4)
                    }
                }
        
        return groups, calibration_data

    def _handle_duplicates(
        self,
        groups,
        duplicate_action,
        keep_largest,
        group_by_similarity,
        stats,
        output_folder_location,
        root_folder  
    ):

        """
        Move, copy, or delete duplicate images.
        
        IMPORTANT: Each category is handled differently!
        
        - exact_dups_found/: Only the DUPLICATES are moved (original stays in place)
          These are safe to delete - they're redundant copies.
          
        - similar_to_compare/: ALL images in the group are moved together
          User needs to compare them side-by-side to pick the best one(s).
          
        - variant_sets/: ALL images in the group are moved together  
          These are a series/set that belong together for organization.

        Args:
            root_folder: The original root directory scanned.
            duplicate_action: 'move', 'copy', or 'delete'
            output_folder_location: 'comfyui_output' or 'original_folder'
        """

        files_handled = 0
        handled_files = set()
        deleted_files_log = []  # Track deleted files for potential recovery
        
        # Map group types to folder names - clearer naming
        folder_names = {
            'exact': 'exact_dups_found',
            'similar': 'similar_to_compare', 
            'variant': 'variant_sets'
        }

        for group_type in ['exact', 'similar', 'variant']:
            for group_idx, group in enumerate(groups[group_type]):
                # Determine the "best" image (largest) for reference
                if keep_largest:
                    best_image = max(group['images'], key=lambda x: x['size'])['path']
                else:
                    best_image = group['base_image']
                
                # Get base image filename for folder naming
                best_image_name = os.path.splitext(os.path.basename(best_image))[0]
                # Clean the name for use as folder (remove problematic chars, limit length)
                safe_base_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in best_image_name)
                safe_base_name = safe_base_name[:50]  # Limit length for filesystem compatibility

                # For delete action, we only delete exact duplicates
                # (similar/variant should be reviewed by user)
                if duplicate_action == "delete" and group_type != 'exact':
                    continue

                if duplicate_action in ["move", "copy"]:
                    # Get the appropriate folder name for this group type
                    type_folder = folder_names[group_type]
                    
                    if output_folder_location == "original_folder":
                        rel_path = os.path.relpath(os.path.dirname(best_image), root_folder)
                        group_folder = os.path.join(root_folder, rel_path, type_folder)
                    else:
                        group_folder = os.path.join(self.output_dir, type_folder)

                    # Name subfolder with base image name for context
                    subgroup_folder = os.path.join(group_folder, f"{group_idx+1:03d}_{safe_base_name}")
                    os.makedirs(subgroup_folder, exist_ok=True)
                    
                    # For EXACT duplicates: copy the reference/kept image into the folder
                    # so user can easily compare and verify the duplicates are correct
                    if group_type == 'exact':
                        try:
                            ref_filename = os.path.basename(best_image)
                            ref_base, ref_ext = os.path.splitext(ref_filename)
                            ref_dest = os.path.join(subgroup_folder, f"_KEPT_{ref_base}{ref_ext}")
                            if not os.path.exists(ref_dest):
                                shutil.copy2(best_image, ref_dest)
                        except Exception as e:
                            print(f"Note: Could not copy reference image: {e}")

                # Process each image in the group
                for img in group['images']:
                    # Skip already handled files
                    if img['path'] in handled_files:
                        continue
                    
                    # DIFFERENT LOGIC PER CATEGORY:
                    # - Exact: Skip the best/largest image (keep original in place, move dups)
                    # - Similar: Move ALL including best (need to compare side-by-side)
                    # - Variant: Move ALL including best (keep series together)
                    
                    if group_type == 'exact' and img['path'] == best_image:
                        # For exact duplicates, keep the best one in original location
                        continue

                    try:
                        if duplicate_action == "delete":
                            # Only for exact duplicates (checked above)
                            deleted_files_log.append({
                                'path': img['path'],
                                'size': img['size'],
                                'similarity': img['similarity'],
                                'kept_file': best_image
                            })
                            os.remove(img['path'])
                            stats["files_deleted"] += 1
                            files_handled += 1
                            handled_files.add(img['path'])
                            
                        elif duplicate_action == "move":
                            dest_filename = os.path.basename(img['path'])
                            dest_path = os.path.join(subgroup_folder, dest_filename)
                            
                            # Handle filename conflicts
                            if os.path.exists(dest_path):
                                base_name, ext = os.path.splitext(dest_filename)
                                dest_path = os.path.join(subgroup_folder, f"{base_name}_dup{ext}")
                                if os.path.exists(dest_path):
                                    timestamp = int(time.time())
                                    dest_path = os.path.join(subgroup_folder, f"{base_name}_{timestamp}{ext}")
                            
                            shutil.move(img['path'], dest_path)
                            stats["files_moved"] += 1
                            files_handled += 1
                            handled_files.add(img['path'])
                            
                        else:  # copy
                            dest_filename = os.path.basename(img['path'])
                            dest_path = os.path.join(subgroup_folder, dest_filename)
                            
                            # Handle filename conflicts
                            if os.path.exists(dest_path):
                                base_name, ext = os.path.splitext(dest_filename)
                                dest_path = os.path.join(subgroup_folder, f"{base_name}_dup{ext}")
                                if os.path.exists(dest_path):
                                    timestamp = int(time.time())
                                    dest_path = os.path.join(subgroup_folder, f"{base_name}_{timestamp}{ext}")
                            
                            shutil.copy2(img['path'], dest_path)
                            stats["files_copied"] += 1
                            files_handled += 1
                            handled_files.add(img['path'])
                            
                    except Exception as e:
                        print(f"Error {duplicate_action}ing file {img['path']}: {e}")

        # Save deletion log for potential recovery
        if duplicate_action == "delete" and deleted_files_log:
            log_path = os.path.join(self.results_dir, f"deleted_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(deleted_files_log, f, indent=2)
                print(f"Deletion log saved to: {log_path}")
            except Exception as e:
                print(f"Warning: Could not save deletion log: {e}")

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

    def _format_calibration_report(self, calibration_data, stats):
        """Format calibration results for display"""
        report = []
        report.append("=" * 60)
        report.append("   CALIBRATION MODE - Similarity Distribution Analysis")
        report.append("=" * 60)
        
        total_pairs = len(calibration_data.get('all_scores', []))
        high_score_pairs = len(calibration_data.get('high_scores', []))
        
        report.append(f"\nTotal image pairs analyzed: {total_pairs:,}")
        report.append(f"Images processed: {stats.get('images_processed', 0):,}")
        report.append(f"Pairs with similarity > 70%: {high_score_pairs:,}")
        
        # Histogram
        histogram = calibration_data.get('score_histogram', {})
        if histogram:
            report.append("\n--- Similarity Score Distribution ---")
            report.append("(Shows how many pairs fall into each similarity range)")
            report.append("")
            
            # Sort buckets and display
            for bucket in sorted(histogram.keys(), reverse=True):
                count = histogram[bucket]
                pct = count / total_pairs * 100 if total_pairs > 0 else 0
                bar_len = int(pct * 2)  # Scale for display
                bar = "█" * min(bar_len, 50)
                
                bucket_label = f"{bucket*100:.0f}%-{(bucket+0.1)*100:.0f}%"
                report.append(f"  {bucket_label:12} | {count:8,} ({pct:5.2f}%) {bar}")
        
        # Suggested thresholds
        suggested = calibration_data.get('suggested_thresholds', {})
        if suggested:
            report.append("\n" + "=" * 60)
            report.append("   SUGGESTED THRESHOLDS")
            report.append("=" * 60)
            report.append("")
            report.append(f"  Exact duplicates:  {suggested.get('exact', 'N/A')}")
            report.append(f"  Similar images:    {suggested.get('similar', 'N/A')}")
            report.append(f"  Variant images:    {suggested.get('variant', 'N/A')}")
            
            percentiles = suggested.get('percentiles', {})
            if percentiles:
                report.append("\n--- Score Percentiles (top similarity scores) ---")
                report.append(f"  Top 0.1% of pairs have similarity >= {percentiles.get('p0.1', 'N/A')}")
                report.append(f"  Top 1% of pairs have similarity >= {percentiles.get('p1', 'N/A')}")
                report.append(f"  Top 5% of pairs have similarity >= {percentiles.get('p5', 'N/A')}")
                report.append(f"  Top 10% of pairs have similarity >= {percentiles.get('p10', 'N/A')}")
        
        report.append("\n" + "=" * 60)
        report.append("   RECOMMENDATIONS")
        report.append("=" * 60)
        report.append("")
        report.append("• If finding too many false positives: RAISE thresholds")
        report.append("• If missing obvious duplicates: LOWER thresholds")
        report.append("• For scaled/resized images: Enable scale_invariant mode")
        report.append("• Run again with suggested thresholds to find duplicates")
        report.append("")
        
        return "\n".join(report)

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
    "Eric_Duplicate_Image_Finder_v05": ImageDuplicateFinder,  
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Duplicate_Image_Finder_v05": "Eric Duplicate Image Finder v05",
}