"""
ComfyUI Node: File Organizer Node v0.1
Description: 
This node organizes files by type into subfolders (movies, images, text, other) and 
can filter images based on minimum pixel dimensions. Supports both flat organization
and maintaining subfolder structure. Handles sidecar files appropriately.

Features:
- Sort files by type into organized subfolders
- Filter images by minimum pixel dimensions (shortest/longest/both sides)
- Handle sidecar files (.xmp, .json, .txt) appropriately
- Training mode for caption handling
- Maintain existing subfolder structure while organizing within each folder
- Detailed statistics and logging

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.1.0
Date: [September 2025]
License: Dual License (Non-Commercial and Commercial Use)
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import time
from datetime import datetime
import json
from PIL import Image

class FileOrganizer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "min_pixel_size": ("INT", {"default": 512, "min": 1, "max": 4096, "step": 1, 
                                         "tooltip": "Minimum pixel size for image dimension check"}),
                "dimension_check": (["shortest_side", "longest_side", "both_dimensions"], 
                                  {"default": "shortest_side", 
                                   "tooltip": "Which dimension(s) to check against minimum"}),
                "subfolder_handling": (["flatten_all", "organize_each_subfolder", "ignore_subfolders"], 
                                     {"default": "organize_each_subfolder",
                                      "tooltip": "flatten_all: Move all files from subfolders to main type folders | organize_each_subfolder: Create type folders within each existing subfolder | ignore_subfolders: Only organize files in the main directory"}),
                "sidecar_handling": (["keep_txt_with_images", "keep_all_sidecars_with_images", "separate_sidecars"], 
                                   {"default": "keep_all_sidecars_with_images",
                                    "tooltip": "keep_txt_with_images: Keep only .txt files with images (for captions), move .xmp/.json to sidecars folder | keep_all_sidecars_with_images: Keep all .txt/.xmp/.json files with images | separate_sidecars: Move all sidecars to separate sidecars folder"}),
            },
            "optional": {
                "folder_paths_input": ("STRING", {"default": "", 
                                                "tooltip": "Optional: Folder paths from another node (like web scraper output)"}),
                "folder_paths_manual": ("STRING", {"default": "", "multiline": True, 
                                                 "tooltip": "Manual input: One folder path per line to organize"}),
                "handle_small_images": (["move_to_below_min", "delete"], {"default": "move_to_below_min",
                                       "tooltip": "What to do with images below minimum size"}),
                "create_subfolders": ("BOOLEAN", {"default": True, 
                                                "tooltip": "Create type subfolders (images, movies, text, other, sidecars, below_min)"}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING")
    RETURN_NAMES = ("status_message", "files_processed", "stats_json", "log_output")
    FUNCTION = "organize_files"
    CATEGORY = "Eric/Images"

    def __init__(self):
        # File type mappings
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif'}
        self.movie_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
        self.text_extensions = {'.txt', '.md', '.doc', '.docx', '.pdf', '.rtf'}
        self.sidecar_extensions = {'.xmp', '.json', '.txt'}

    def organize_files(self, min_pixel_size=512, dimension_check="shortest_side",
                      subfolder_handling="organize_each_subfolder", sidecar_handling="keep_all_sidecars_with_images",
                      folder_paths_input="", folder_paths_manual="", 
                      handle_small_images="move_to_below_min", create_subfolders=True):
        """
        Main function to organize files by type and filter by image dimensions
        """
        start_time = time.time()
        
        # Initialize stats
        stats = {
            "start_time": datetime.now().isoformat(),
            "folders_processed": 0,
            "files_processed": 0,
            "images_analyzed": 0,
            "images_moved": 0,
            "movies_moved": 0,
            "text_files_moved": 0,
            "other_files_moved": 0,
            "sidecars_moved": 0,
            "small_images_found": 0,
            "small_images_deleted": 0,
            "small_images_moved": 0,
            "subfolders_created": 0,
            "errors": [],
            "organized_folders": [],
            "small_images": [],
            "error": None
        }
        
        log_messages = []
        
        try:
            # Parse folder paths - combine input from node connection and manual input
            folder_list = []
            
            # Add paths from connected node input
            if folder_paths_input:
                # Handle both newline and semicolon separated paths
                input_text = folder_paths_input.replace(';', '\n')  # Convert semicolons to newlines
                folder_list.extend([f.strip() for f in input_text.splitlines() if f.strip()])
            
            # Add paths from manual input
            if folder_paths_manual:
                # Handle both newline and semicolon separated paths
                manual_text = folder_paths_manual.replace(';', '\n')  # Convert semicolons to newlines
                folder_list.extend([f.strip() for f in manual_text.splitlines() if f.strip()])
            
            if not folder_list:
                error_msg = "No folder paths provided in either input"
                stats["error"] = error_msg
                return error_msg, 0, json.dumps(stats, indent=2), "\n".join(log_messages)
            
            # Validate folder paths
            valid_folders = []
            for folder_path in folder_list:
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    valid_folders.append(folder_path)
                    log_messages.append(f"Added folder: {folder_path}")
                else:
                    error_msg = f"Invalid folder path: {folder_path}"
                    stats["errors"].append(error_msg)
                    log_messages.append(f"WARNING: {error_msg}")
            
            if not valid_folders:
                error_msg = "No valid folder paths found"
                stats["error"] = error_msg
                return error_msg, 0, json.dumps(stats, indent=2), "\n".join(log_messages)
            
            log_messages.append(f"Starting file organization with {len(valid_folders)} folders")
            log_messages.append(f"Min pixel size: {min_pixel_size} ({dimension_check})")
            log_messages.append(f"Subfolder handling: {subfolder_handling}")
            log_messages.append(f"Sidecar handling: {sidecar_handling}")
            log_messages.append(f"Small images action: {handle_small_images}")
            
            # Process each folder
            total_files_processed = 0
            for folder_path in valid_folders:
                try:
                    folder_stats = self._organize_folder(
                        folder_path, min_pixel_size, dimension_check,
                        subfolder_handling, sidecar_handling, handle_small_images,
                        create_subfolders, log_messages
                    )
                    
                    # Accumulate stats
                    for key in folder_stats:
                        if key in stats and isinstance(stats[key], int):
                            stats[key] += folder_stats[key]
                        elif key == "errors":
                            stats["errors"].extend(folder_stats["errors"])
                        elif key == "organized_folders":
                            stats["organized_folders"].extend(folder_stats["organized_folders"])
                        elif key == "small_images":
                            stats["small_images"].extend(folder_stats["small_images"])
                    
                    stats["folders_processed"] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing folder {folder_path}: {str(e)}"
                    stats["errors"].append(error_msg)
                    log_messages.append(f"ERROR: {error_msg}")
            
            # Generate final status
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            total_files_processed = stats["files_processed"]
            
            status_message = f"Organized {total_files_processed} files"
            status_message += f" ({stats['images_moved']} images, {stats['movies_moved']} movies, "
            status_message += f"{stats['text_files_moved']} text, {stats['other_files_moved']} other, "
            status_message += f"{stats['sidecars_moved']} sidecars)"
            
            if stats["small_images_found"] > 0:
                if handle_small_images == "delete":
                    status_message += f", deleted {stats['small_images_deleted']} small images"
                else:
                    status_message += f", moved {stats['small_images_moved']} small images"
            
            if stats["errors"]:
                status_message += f" ({len(stats['errors'])} errors occurred)"
            
            log_messages.append(f"Operation completed: {status_message}")
            
            return status_message, total_files_processed, json.dumps(stats, indent=2), "\n".join(log_messages)
            
        except Exception as e:
            error_msg = f"Fatal error in file organization: {str(e)}"
            stats["error"] = error_msg
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            log_messages.append(f"FATAL ERROR: {error_msg}")
            
            return error_msg, 0, json.dumps(stats, indent=2), "\n".join(log_messages)

    def _organize_folder(self, folder_path, min_pixel_size, dimension_check, subfolder_handling,
                        sidecar_handling, handle_small_images, create_subfolders, log_messages):
        """Organize files in a single folder"""
        folder_stats = {
            "files_processed": 0,
            "images_analyzed": 0,
            "images_moved": 0,
            "movies_moved": 0,
            "text_files_moved": 0,
            "other_files_moved": 0,
            "sidecars_moved": 0,
            "small_images_found": 0,
            "small_images_deleted": 0,
            "small_images_moved": 0,
            "subfolders_created": 0,
            "errors": [],
            "organized_folders": [],
            "small_images": []
        }
        
        folder_path = Path(folder_path)
        
        if subfolder_handling == "organize_each_subfolder":
            # Check if top-level type folders already exist
            type_folder_names = {'images', 'movies', 'text', 'other', 'sidecars', 'below_min'}
            existing_type_folders = {d.name.lower() for d in folder_path.iterdir() if d.is_dir() and d.name.lower() in type_folder_names}
            
            if existing_type_folders:
                # If type folders already exist at root level, only organize within them and process root files
                folders_to_organize = [folder_path]  # Only process root folder
                log_messages.append(f"Found existing type folders: {existing_type_folders}. Organizing into existing structure.")
            else:
                # No type folders exist, create them and organize all subdirectories
                folders_to_organize = [folder_path]  # Include root folder
                # Only include subdirectories that are NOT named like type folders
                for d in folder_path.iterdir():
                    if d.is_dir() and d.name.lower() not in type_folder_names:
                        folders_to_organize.append(d)
                        log_messages.append(f"Will organize subfolder: {d.name}")
        elif subfolder_handling == "flatten_all":
            # Only process root folder but collect files from all subfolders
            folders_to_organize = [folder_path]
        elif subfolder_handling == "ignore_subfolders":
            # Only organize the root folder
            folders_to_organize = [folder_path]
        
        log_messages.append(f"Organizing {len(folders_to_organize)} folders")
        
        for current_folder in folders_to_organize:
            try:
                self._organize_single_directory(
                    current_folder, min_pixel_size, dimension_check,
                    subfolder_handling, sidecar_handling, handle_small_images,
                    create_subfolders, folder_stats, log_messages
                )
                folder_stats["organized_folders"].append(str(current_folder))
                
            except Exception as e:
                error_msg = f"Error organizing directory {current_folder}: {str(e)}"
                folder_stats["errors"].append(error_msg)
                log_messages.append(f"ERROR: {error_msg}")
        
        return folder_stats

    def _organize_single_directory(self, directory, min_pixel_size, dimension_check,
                                  subfolder_handling, sidecar_handling, handle_small_images,
                                  create_subfolders, stats, log_messages):
        """Organize files within a single directory"""
        directory = Path(directory)
        
        # Get files based on subfolder handling mode
        if subfolder_handling == "flatten_all":
            # Get all files from this directory and all subdirectories
            files_in_dir = []
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    files_in_dir.append(file_path)
        else:
            # Get only files in this directory (not subdirectories)
            files_in_dir = [f for f in directory.iterdir() if f.is_file()]
        
        if not files_in_dir:
            return
        
        log_messages.append(f"Processing {len(files_in_dir)} files in {directory}")
        
        # Create type subfolders if requested
        type_folders = {}
        if create_subfolders:
            for folder_type in ['images', 'movies', 'text', 'other', 'sidecars', 'below_min']:
                type_folder = directory / folder_type
                type_folders[folder_type] = type_folder
                if not type_folder.exists():
                    type_folder.mkdir(exist_ok=True)
                    stats["subfolders_created"] += 1
                    log_messages.append(f"Created subfolder: {type_folder}")
                else:
                    log_messages.append(f"Using existing subfolder: {type_folder}")
        
        # Group files by type and handle sidecars
        file_groups = {
            'images': [],
            'movies': [],
            'text': [],
            'other': [],
            'sidecars': []
        }
        
        # First pass: categorize files
        for file_path in files_in_dir:
            file_type = self._get_file_type(file_path)
            if file_type in file_groups:
                file_groups[file_type].append(file_path)
            stats["files_processed"] += 1
        
        # Handle images and check dimensions
        for image_file in file_groups['images']:
            try:
                is_small = self._check_image_dimensions(image_file, min_pixel_size, dimension_check)
                stats["images_analyzed"] += 1
                
                if is_small:
                    stats["small_images_found"] += 1
                    stats["small_images"].append({
                        "path": str(image_file),
                        "action": handle_small_images
                    })
                    
                    if handle_small_images == "delete":
                        image_file.unlink()
                        stats["small_images_deleted"] += 1
                        log_messages.append(f"Deleted small image: {image_file.name}")
                    else:  # move_to_below_min
                        if create_subfolders:
                            target_path = type_folders['below_min'] / image_file.name
                            shutil.move(str(image_file), str(target_path))
                            stats["small_images_moved"] += 1
                            log_messages.append(f"Moved small image to below_min: {image_file.name}")
                else:
                    # Move normal-sized image
                    if create_subfolders:
                        target_path = type_folders['images'] / image_file.name
                        shutil.move(str(image_file), str(target_path))
                        stats["images_moved"] += 1
                        log_messages.append(f"Moved image: {image_file.name}")
                        
                        # Handle associated sidecars
                        self._move_sidecars(image_file, type_folders, sidecar_handling, stats, log_messages)
                
            except Exception as e:
                error_msg = f"Error processing image {image_file}: {str(e)}"
                stats["errors"].append(error_msg)
                log_messages.append(f"ERROR: {error_msg}")
        
        # Handle other file types
        for movie_file in file_groups['movies']:
            if create_subfolders:
                target_path = type_folders['movies'] / movie_file.name
                shutil.move(str(movie_file), str(target_path))
                stats["movies_moved"] += 1
                log_messages.append(f"Moved movie: {movie_file.name}")
        
        # Handle text files (those not associated with images as sidecars)
        for text_file in file_groups['text']:
            # Check if this text file is associated with an image (only in certain sidecar modes)
            is_sidecar = False
            if sidecar_handling in ["keep_txt_with_images", "keep_all_sidecars_with_images"]:
                # Check if there's a matching image file
                base_name = text_file.stem
                for img_ext in self.image_extensions:
                    potential_image = text_file.parent / f"{base_name}{img_ext}"
                    if potential_image.exists():
                        is_sidecar = True
                        break
            
            if not is_sidecar and create_subfolders:
                target_path = type_folders['text'] / text_file.name
                shutil.move(str(text_file), str(target_path))
                stats["text_files_moved"] += 1
                log_messages.append(f"Moved text file: {text_file.name}")
        
        # Handle other files
        for other_file in file_groups['other']:
            if create_subfolders:
                target_path = type_folders['other'] / other_file.name
                shutil.move(str(other_file), str(target_path))
                stats["other_files_moved"] += 1
                log_messages.append(f"Moved other file: {other_file.name}")

    def _get_file_type(self, file_path):
        """Determine file type based on extension"""
        ext = file_path.suffix.lower()
        
        if ext in self.image_extensions:
            return 'images'
        elif ext in self.movie_extensions:
            return 'movies'
        elif ext in self.text_extensions:
            return 'text'
        elif ext in self.sidecar_extensions:
            return 'sidecars'
        else:
            return 'other'

    def _check_image_dimensions(self, image_path, min_pixel_size, dimension_check):
        """Check if image meets minimum dimension requirements"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                if dimension_check == "shortest_side":
                    return min(width, height) < min_pixel_size
                elif dimension_check == "longest_side":
                    return max(width, height) < min_pixel_size
                elif dimension_check == "both_dimensions":
                    return width < min_pixel_size or height < min_pixel_size
                
        except Exception as e:
            # If we can't read the image, consider it problematic (small)
            return True
        
        return False

    def _move_sidecars(self, image_file, type_folders, sidecar_handling, stats, log_messages):
        """Move sidecar files associated with an image based on sidecar handling mode"""
        base_name = image_file.stem
        image_dir = image_file.parent
        
        # Look for matching sidecar files
        for sidecar_ext in self.sidecar_extensions:
            sidecar_file = image_dir / f"{base_name}{sidecar_ext}"
            if sidecar_file.exists():
                if sidecar_handling == "keep_txt_with_images":
                    if sidecar_ext == '.txt':
                        # Keep .txt files with images (as captions)
                        target_path = type_folders['images'] / sidecar_file.name
                        shutil.move(str(sidecar_file), str(target_path))
                        stats["sidecars_moved"] += 1
                        log_messages.append(f"Moved caption file with image: {sidecar_file.name}")
                    else:
                        # Move .xmp and .json to sidecars folder
                        target_path = type_folders['sidecars'] / sidecar_file.name
                        shutil.move(str(sidecar_file), str(target_path))
                        stats["sidecars_moved"] += 1
                        log_messages.append(f"Moved sidecar to sidecars folder: {sidecar_file.name}")
                        
                elif sidecar_handling == "keep_all_sidecars_with_images":
                    # Keep all sidecars with images
                    target_path = type_folders['images'] / sidecar_file.name
                    shutil.move(str(sidecar_file), str(target_path))
                    stats["sidecars_moved"] += 1
                    log_messages.append(f"Moved sidecar with image: {sidecar_file.name}")
                    
                elif sidecar_handling == "separate_sidecars":
                    # Move all sidecars to separate sidecars folder
                    target_path = type_folders['sidecars'] / sidecar_file.name
                    shutil.move(str(sidecar_file), str(target_path))
                    stats["sidecars_moved"] += 1
                    log_messages.append(f"Moved sidecar to sidecars folder: {sidecar_file.name}")

# Required for ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "FileOrganizer": FileOrganizer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FileOrganizer": "File Organizer"
}
