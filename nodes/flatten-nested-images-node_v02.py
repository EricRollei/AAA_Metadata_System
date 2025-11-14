"""
ComfyUI Node: Flatten Nested Files Node v0.2
Description: 
This node intelligently flattens nested directory structures while respecting file 
organization and paired files (sidecars). Can organize by file type, recognize paired 
files (image.jpg + image.xmp/txt/json), and respect organized subdirectories.

Features:
- Flatten to configurable depth levels
- Organize by file type (images, movies, text, sidecars, other)
- Recognize and keep paired files together (image + metadata sidecars)
- Respect organized subdirectories (skip folders that already have structure)
- Handle filename conflicts with multiple strategies
- Detailed statistics and logging

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.2.0
Date: [October 2025]
License: Dual License (Non-Commercial and Commercial Use)
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import time
from datetime import datetime
import json

class FlattenNestedFiles:
    def __init__(self):
        # File type mappings - consistent with file-organizer node
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.heic', '.heif'}
        self.movie_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
        self.text_extensions = {'.txt', '.md', '.doc', '.docx', '.pdf', '.rtf'}
        self.sidecar_extensions = {'.xmp', '.json', '.txt'}
        # Paired file tracking
        self.paired_files = defaultdict(list)  # Maps base filename to list of associated files
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "main_directory": ("STRING", {"default": "", "tooltip": "Main directory where all files will be moved to"}),
                "operation_mode": (["flatten_only", "flatten_and_organize", "organize_only"], 
                                  {"default": "flatten_only",
                                   "tooltip": "Choose operation mode:\n• flatten_only: Move all files directly into main_directory (NO type subfolders)\n• flatten_and_organize: Move files AND create type subfolders (images/, movies/, etc.)\n• organize_only: Don't move files up, just organize them in their current locations\nNote: organize_by_type parameter can override flatten_only to add type folders"}),
            },
            "optional": {
                "file_types": (["images_only", "all_media", "all_files"], {"default": "images_only", 
                              "tooltip": "Which files to process:\n• images_only: .jpg, .png, .webp, .gif, etc.\n• all_media: Images + videos (.mp4, .mov, etc.)\n• all_files: Everything including .txt, .pdf, etc."}),
                "flatten_depth": ("INT", {"default": 0, "min": 0, "max": 10, "step": 1,
                                  "tooltip": "Flatten nested folders to this depth:\n• 0 = Move ALL files to main directory\n• 1 = Keep 1st level subfolders, flatten everything inside them\n• 2 = Keep 2 levels, flatten below that\nExample: If main=instagram and depth=1, processes each profile folder (alisha.maghi/, 777luckyfish/) independently"}),
                "respect_paired_files": ("BOOLEAN", {"default": True, 
                                         "tooltip": "Keep paired files together (e.g., photo.jpg + photo.xmp + photo.txt).\nPaired files share the same base filename and are moved as a group."}),
                "skip_organized_folders": ("BOOLEAN", {"default": True,
                                           "tooltip": "Skip folders that already have type organization (contain images/, movies/, text/ subfolders).\nUseful to avoid re-organizing already processed directories."}),
                "organize_by_type": ("BOOLEAN", {"default": False,
                                     "tooltip": "Create type-based subfolders:\n• images/ for .jpg, .png, etc.\n• movies/ for .mp4, .mov, etc.\n• text/ for .txt, .pdf, .md\n• sidecars/ for .xmp, .json (unless kept with images)\n• other/ for unrecognized types\nWhen True: Always creates type folders (even with flatten_only mode)\nWhen False with flatten_only: All files go directly into main_directory"}),

                "sidecar_handling": (["keep_with_images", "separate_folder", "keep_txt_only"], 
                                    {"default": "keep_with_images",
                                     "tooltip": "Where to put sidecar/metadata files:\n• keep_with_images: Put .xmp/.json/.txt in images/ folder\n• separate_folder: Put all sidecars in sidecars/ folder\n• keep_txt_only: Only .txt with images, others to sidecars/"}),
                "remove_empty_folders": ("BOOLEAN", {"default": True, "tooltip": "Delete empty subdirectories after moving files.\nLeaves a clean directory structure with no leftover empty folders."}),
                "dry_run": ("BOOLEAN", {"default": False, "tooltip": "Preview mode - show what WOULD be moved without actually moving anything.\nGreat for testing settings before committing changes."}),
                "handle_conflicts": (["rename", "skip", "overwrite"], {"default": "rename", 
                                   "tooltip": "How to handle duplicate filenames:\n• rename: Add (1), (2), etc. to filename\n• skip: Leave original, don't move duplicate\n• overwrite: Replace existing file with new one"}),
                "max_scan_depth": ("INT", {"default": 100, "min": 1, "max": 200, "step": 1, 
                             "tooltip": "Maximum folder nesting depth to scan.\nIncrease if you have very deeply nested folders (46+ levels).\nPrevents infinite loops and excessive scanning."}),
                "custom_type_mappings": ("STRING", {"default": "", "multiline": True,
                                        "tooltip": "JSON mapping file extensions to custom folder names.\nExample:\n{\n  \".pdf\": \"documents\",\n  \".cr2\": \"raw_photos\",\n  \".psd\": \"photoshop\"\n}\nFiles with these extensions go to specified folders instead of default type folders."}),
                "custom_folder_mappings": ("STRING", {"default": "", "multiline": True,
                                          "tooltip": "JSON mapping file TYPES to custom folder names.\nExample:\n{\n  \"movies\": \"videos\",\n  \"images\": \"photos\",\n  \"text\": \"documents\"\n}\nRenames the default type folders (images→photos, movies→videos, etc.)."}),
                "preserve_source_folder": (["none", "prefix", "suffix"], {"default": "none",
                                           "tooltip": "Add original folder name to filename to preserve context:\n• none: photo.jpg (no change)\n• prefix: alisha.maghi_photo.jpg\n• suffix: photo_alisha.maghi.jpg\nUseful when flattening to avoid name conflicts and maintain source info."}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("status_message", "files_moved", "paired_files_moved", "stats_json", "log_output")
    FUNCTION = "flatten_files"
    CATEGORY = "Eric/Images"

    def flatten_files(self, main_directory, operation_mode="flatten_only", file_types="images_only", 
                      flatten_depth=0, respect_paired_files=True, skip_organized_folders=True,
                      organize_by_type=False, sidecar_handling="keep_with_images",
                      remove_empty_folders=True, dry_run=False, 
                      handle_conflicts="rename", max_scan_depth=10,
                      custom_type_mappings="", custom_folder_mappings="", preserve_source_folder="none"):
        """
        Main function to flatten and/or organize nested files
        """
        start_time = time.time()
        
        # Initialize stats
        stats = {
            "start_time": datetime.now().isoformat(),
            "main_directory": main_directory,
            "operation_mode": operation_mode,
            "file_types": file_types,
            "flatten_depth": flatten_depth,
            "dry_run": dry_run,
            "files_found": 0,
            "files_moved": 0,
            "files_skipped": 0,
            "files_renamed": 0,
            "conflicts_resolved": 0,
            "paired_files_moved": 0,
            "folders_scanned": 0,
            "folders_skipped": 0,
            "folders_removed": 0,
            "images_moved": 0,
            "movies_moved": 0,
            "text_moved": 0,
            "sidecars_moved": 0,
            "other_moved": 0,
            "errors": [],
            "moved_files": [],
            "renamed_files": [],
            "excluded_files": [],
            "skipped_folders": [],
            "error": None
        }
        
        log_messages = []
        
        # Parse custom mappings
        custom_ext_to_folder = {}
        custom_type_to_folder = {}
        
        if custom_type_mappings:
            try:
                custom_ext_to_folder = json.loads(custom_type_mappings)
                log_messages.append(f"Loaded custom extension mappings: {len(custom_ext_to_folder)} entries")
            except json.JSONDecodeError as e:
                log_messages.append(f"WARNING: Invalid JSON in custom_type_mappings: {e}")
        
        if custom_folder_mappings:
            try:
                custom_type_to_folder = json.loads(custom_folder_mappings)
                log_messages.append(f"Loaded custom folder mappings: {len(custom_type_to_folder)} entries")
            except json.JSONDecodeError as e:
                log_messages.append(f"WARNING: Invalid JSON in custom_folder_mappings: {e}")
        
        try:
            # Validate inputs
            if not main_directory or not os.path.exists(main_directory):
                error_msg = f"Main directory does not exist: {main_directory}"
                stats["error"] = error_msg
                return error_msg, 0, 0, json.dumps(stats, indent=2), "\n".join(log_messages)
            
            main_path = Path(main_directory)
            
            # Set instance variable for preserve_source_folder (used by helper method)
            self._preserve_source_folder = preserve_source_folder
            
            log_messages.append(f"=== Enhanced Flatten/Organize Operation ===")
            log_messages.append(f"Main directory: {main_directory}")
            log_messages.append(f"Operation mode: {operation_mode}")
            log_messages.append(f"File types: {file_types}")
            log_messages.append(f"Flatten depth: {flatten_depth} (0=flatten all)")
            log_messages.append(f"Preserve source folder: {preserve_source_folder}")
            log_messages.append(f"Respect paired files: {respect_paired_files}")
            log_messages.append(f"Skip organized folders: {skip_organized_folders}")
            log_messages.append(f"Organize by type: {organize_by_type}")
            log_messages.append(f"Sidecar handling: {sidecar_handling}")
            log_messages.append(f"Dry run mode: {dry_run}")
            
            # Step 1: Scan and categorize all files, identifying paired files
            log_messages.append(f"\n--- Step 1: Scanning directory structure ---")
            log_messages.append(f"Looking for file types: {file_types}")
            if file_types == "images_only":
                log_messages.append(f"Image extensions: {', '.join(sorted(self.image_extensions))}")
            elif file_types == "all_media":
                log_messages.append(f"Media extensions: {', '.join(sorted(self.image_extensions | self.movie_extensions))}")
            
            all_files_by_folder = self._scan_directory_structure(
                main_path, file_types, respect_paired_files, skip_organized_folders,
                max_scan_depth, stats, log_messages
            )
            
            stats["files_found"] = sum(len(files) for files in all_files_by_folder.values())
            
            if stats["files_found"] == 0:
                message = f"No files found to process"
                log_messages.append(message)
                return message, 0, 0, json.dumps(stats, indent=2), "\n".join(log_messages)
            
            log_messages.append(f"Found {stats['files_found']} files in {len(all_files_by_folder)} folders")
            log_messages.append(f"Identified {len(self.paired_files)} base files with paired sidecars")
            
            # Step 2: Process files based on operation mode
            log_messages.append(f"\n--- Step 2: Processing files ---")
            
            if operation_mode == "organize_only":
                # Organize files within their current folders
                self._organize_in_place(all_files_by_folder, organize_by_type, sidecar_handling,
                                       handle_conflicts, dry_run, stats, log_messages,
                                       custom_ext_to_folder, custom_type_to_folder, preserve_source_folder)
            elif operation_mode in ["flatten_only", "flatten_and_organize"]:
                # Flatten files to specified depth and optionally organize
                # For flatten_and_organize: always organize by type (force True)
                # For flatten_only: respect the organize_by_type parameter (user's choice)
                should_organize = True if operation_mode == "flatten_and_organize" else organize_by_type
                self._flatten_and_organize(all_files_by_folder, main_path, flatten_depth,
                                          should_organize,
                                          sidecar_handling, handle_conflicts, dry_run, stats, log_messages,
                                          custom_ext_to_folder, custom_type_to_folder, preserve_source_folder)
            
            # Step 3: Remove empty directories if requested
            if remove_empty_folders and not dry_run:
                log_messages.append(f"\n--- Step 3: Cleaning up empty directories ---")
                removed_count = self._remove_empty_directories(main_directory, log_messages)
                stats["folders_removed"] = removed_count
            elif remove_empty_folders and dry_run:
                empty_dirs = self._find_empty_directories(main_directory)
                log_messages.append(f"Would remove {len(empty_dirs)} empty directories")
                stats["folders_removed"] = len(empty_dirs)
            
            # Generate final status
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            
            # Build status message
            if dry_run:
                status_message = f"DRY RUN: Would process {stats['files_moved']} files"
            else:
                status_message = f"Successfully processed {stats['files_moved']} files"
            
            if stats["paired_files_moved"] > 0:
                status_message += f" ({stats['paired_files_moved']} with paired sidecars)"
            
            if stats["images_moved"] > 0 or stats["movies_moved"] > 0:
                status_message += f" [{stats['images_moved']} images, {stats['movies_moved']} movies"
                if stats["text_moved"] > 0 or stats["sidecars_moved"] > 0:
                    status_message += f", {stats['text_moved']} text, {stats['sidecars_moved']} sidecars"
                status_message += "]"
            
            if stats["folders_skipped"] > 0:
                status_message += f" ({stats['folders_skipped']} organized folders skipped)"
            
            if stats["errors"]:
                status_message += f" ({len(stats['errors'])} errors occurred)"
            
            log_messages.append(f"\n=== Operation completed: {status_message} ===")
            
            return status_message, stats["files_moved"], stats["paired_files_moved"], json.dumps(stats, indent=2), "\n".join(log_messages)
            
        except Exception as e:
            error_msg = f"Fatal error in flatten operation: {str(e)}"
            stats["error"] = error_msg
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            log_messages.append(f"FATAL ERROR: {error_msg}")
            import traceback
            log_messages.append(traceback.format_exc())
            
            return error_msg, 0, 0, json.dumps(stats, indent=2), "\n".join(log_messages)

    def _scan_directory_structure(self, main_path, file_types, respect_paired_files, 
                                  skip_organized_folders, max_depth, stats, log_messages):
        """Scan directory and categorize files, identifying paired files"""
        all_files_by_folder = defaultdict(list)
        self.paired_files.clear()
        
        def is_organized_folder(folder_path):
            """Check if a folder already has type organization with actual files"""
            if not skip_organized_folders:
                return False
                
            type_folder_names = {'images', 'movies', 'text', 'other', 'sidecars', 'below_min'}
            try:
                subfolders = {d.name.lower() for d in folder_path.iterdir() if d.is_dir()}
                type_folders_found = subfolders & type_folder_names
                
                # Need at least 2 type folders to be considered organized
                if len(type_folders_found) < 2:
                    return False
                
                # Check if these type folders actually contain files (not just more nested folders)
                has_actual_organization = False
                for type_folder_name in type_folders_found:
                    type_folder_path = folder_path / type_folder_name
                    # Check if this type folder has files directly in it
                    try:
                        has_files = any(item.is_file() for item in type_folder_path.iterdir())
                        if has_files:
                            has_actual_organization = True
                            break
                    except:
                        continue
                
                return has_actual_organization
            except:
                return False
        
        def scan_folder(folder_path, current_depth=0):
            if current_depth >= max_depth:
                log_messages.append(f"  Max depth reached at: {folder_path}")
                return
            
            stats["folders_scanned"] += 1
            log_messages.append(f"  Scanning folder (depth {current_depth}): {folder_path}")
            
            # Check if this folder is already organized (but NEVER skip the main/root directory)
            if current_depth > 0 and is_organized_folder(folder_path):
                stats["folders_skipped"] += 1
                stats["skipped_folders"].append(str(folder_path))
                log_messages.append(f"  ⏭️  Skipping organized folder: {folder_path.name}")
                return
            
            try:
                items = list(folder_path.iterdir())
                log_messages.append(f"    Found {len(items)} items in folder")
                
                files_found = 0
                dirs_found = 0
                
                for item in items:
                    if item.is_file():
                        files_found += 1
                        # Check if file matches our filter
                        if self._should_include_file(item, file_types):
                            all_files_by_folder[folder_path].append(item)
                            
                            # Track paired files if enabled
                            if respect_paired_files:
                                self._track_paired_file(item, folder_path)
                    
                    elif item.is_dir():
                        dirs_found += 1
                        # Recursively scan subdirectories
                        scan_folder(item, current_depth + 1)
                
                log_messages.append(f"    Processed {files_found} files, {dirs_found} subdirectories")
            
            except PermissionError:
                log_messages.append(f"  Permission denied: {folder_path}")
                stats["errors"].append(f"Permission denied: {folder_path}")
            except Exception as e:
                log_messages.append(f"  Error scanning {folder_path}: {e}")
                stats["errors"].append(f"Error scanning {folder_path}: {e}")
        
        scan_folder(main_path)
        return all_files_by_folder

    def _should_include_file(self, file_path, file_types):
        """Determine if file should be included based on file type filter"""
        ext = file_path.suffix.lower()
        
        if file_types == "images_only":
            included = ext in self.image_extensions
        elif file_types == "all_media":
            included = ext in (self.image_extensions | self.movie_extensions)
        elif file_types == "all_files":
            # Exclude system/temp files but include files with no extension
            exclude_extensions = {'.tmp', '.log', '.cache', '.DS_Store', '.thumbs.db'}
            # Include files with no extension or extensions not in exclude list
            included = (not ext) or (ext not in exclude_extensions)
        else:
            included = False
        
        # Debug: Print first few rejections to help diagnose
        if not included and not hasattr(self, '_debug_reject_count'):
            self._debug_reject_count = 0
        if not included and self._debug_reject_count < 5:
            print(f"      Rejected file: {file_path.name} (ext={ext}, filter={file_types})")
            self._debug_reject_count += 1
        
        return included

    def _track_paired_file(self, file_path, folder_path):
        """Track files that might be paired (image + sidecar)"""
        base_name = file_path.stem
        ext = file_path.suffix.lower()
        
        # Create a key for this base filename in this folder
        folder_key = (folder_path, base_name)
        
        # Add this file to the list for this base name
        self.paired_files[folder_key].append(file_path)

    def _get_file_type(self, file_path, custom_ext_to_folder=None):
        """Determine file type category, checking custom mappings first"""
        ext = file_path.suffix.lower()
        
        # Check custom extension mappings first (these map directly to folder names, not types)
        # We return 'custom' and handle folder name separately
        if custom_ext_to_folder and ext in custom_ext_to_folder:
            return 'custom'  # Will be handled by _get_destination_folder
        
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
    
    def _get_destination_folder(self, file_type, custom_type_to_folder):
        """Get destination folder name, checking custom mappings"""
        # Check if there's a custom folder mapping for this type
        if custom_type_to_folder and file_type in custom_type_to_folder:
            return custom_type_to_folder[file_type]
        # Otherwise use the default type name
        return file_type
    
    def _get_custom_folder_for_extension(self, file_path, custom_ext_to_folder):
        """Get custom folder name for a file extension"""
        ext = file_path.suffix.lower()
        return custom_ext_to_folder.get(ext, None)

    def _flatten_and_organize(self, all_files_by_folder, main_path, flatten_depth,
                             organize_by_type, sidecar_handling, handle_conflicts, 
                             dry_run, stats, log_messages,
                             custom_ext_to_folder, custom_type_to_folder, preserve_source_folder):
        """Flatten files to specified depth and optionally organize by type"""
        
        for folder_path, files in all_files_by_folder.items():
            # Calculate relative path and depth
            rel_path = folder_path.relative_to(main_path)
            current_depth = len(rel_path.parts)
            
            # Determine target folder based on flatten_depth
            if flatten_depth == 0:
                # Flatten everything to main directory
                target_base = main_path
            elif current_depth <= flatten_depth:
                # Files at or above target depth - they're at the "preservation level"
                # Example: depth=1, we're in "instagram/alisha.maghi/" (depth 1)
                # Files here should be organized within this folder, not moved up
                target_base = folder_path
            else:
                # Files below target depth move up to the depth-level ancestor
                # Example: depth=1, we're in "instagram/alisha.maghi/images/images/images/"
                # Files here should move to "instagram/alisha.maghi/" (the depth-1 ancestor)
                keep_parts = rel_path.parts[:flatten_depth]
                target_base = main_path.joinpath(*keep_parts) if keep_parts else main_path
            
            # Skip if files are in a type folder and would stay in same location
            # This prevents unnecessary processing when target_base == folder_path
            # and the folder is already a type folder (images/, movies/, etc.)
            type_folder_names = {'images', 'movies', 'text', 'other', 'sidecars', 'below_min'}
            if target_base == folder_path and not organize_by_type:
                # Files staying in place and no organization requested - skip
                continue
            
            # Process each file
            processed_bases = set()
            
            for file_path in files:
                base_name = file_path.stem
                folder_key = (folder_path, base_name)
                
                # Skip if we already processed this base (for paired files)
                if folder_key in processed_bases:
                    continue
                
                # Get all paired files for this base
                paired_group = self.paired_files.get(folder_key, [file_path])
                
                # Move the file(s)
                self._move_file_group(paired_group, target_base, organize_by_type,
                                     sidecar_handling, handle_conflicts, dry_run, stats, log_messages,
                                     custom_ext_to_folder, custom_type_to_folder, folder_path)
                
                processed_bases.add(folder_key)
                
                if len(paired_group) > 1:
                    stats["paired_files_moved"] += 1

    def _organize_in_place(self, all_files_by_folder, organize_by_type, sidecar_handling,
                          handle_conflicts, dry_run, stats, log_messages,
                          custom_ext_to_folder, custom_type_to_folder, preserve_source_folder):
        """Organize files within their current folders"""
        
        for folder_path, files in all_files_by_folder.items():
            if not files:
                continue
            
            log_messages.append(f"  Organizing {len(files)} files in: {folder_path}")
            
            # Process each file
            processed_bases = set()
            
            for file_path in files:
                base_name = file_path.stem
                folder_key = (folder_path, base_name)
                
                # Skip if already processed this base
                if folder_key in processed_bases:
                    continue
                
                # Get all paired files
                paired_group = self.paired_files.get(folder_key, [file_path])
                
                # Organize within the same folder
                self._move_file_group(paired_group, folder_path, organize_by_type,
                                     sidecar_handling, handle_conflicts, dry_run, stats, log_messages,
                                     custom_ext_to_folder, custom_type_to_folder, preserve_source_folder, folder_path)
                
                processed_bases.add(folder_key)
                
                if len(paired_group) > 1:
                    stats["paired_files_moved"] += 1

    def _move_file_group(self, file_group, target_base_path, organize_by_type,
                        sidecar_handling, handle_conflicts, dry_run, stats, log_messages,
                        custom_ext_to_folder, custom_type_to_folder, source_folder_path):
        """Move a group of paired files together"""
        
        # Separate files by type
        images = [f for f in file_group if self._get_file_type(f, custom_ext_to_folder) == 'images']
        movies = [f for f in file_group if self._get_file_type(f, custom_ext_to_folder) == 'movies']
        texts = [f for f in file_group if self._get_file_type(f, custom_ext_to_folder) == 'text']
        sidecars = [f for f in file_group if self._get_file_type(f, custom_ext_to_folder) == 'sidecars']
        others = [f for f in file_group if self._get_file_type(f, custom_ext_to_folder) == 'other']
        
        # Check if target_base_path already IS a type folder to avoid nesting
        type_folder_names = {'images', 'movies', 'text', 'other', 'sidecars', 'below_min'}
        base_folder_name = target_base_path.name.lower()
        already_in_type_folder = base_folder_name in type_folder_names
        
        # Determine where each type should go
        for file_path in file_group:
            # Check for custom extension mapping first (direct extension -> folder mapping)
            custom_folder = self._get_custom_folder_for_extension(file_path, custom_ext_to_folder)
            
            if custom_folder and organize_by_type and not already_in_type_folder:
                # Custom extension mapping takes priority
                target_dir = target_base_path / custom_folder
            elif organize_by_type and not already_in_type_folder:
                # Standard type-based organization
                file_type = self._get_file_type(file_path, custom_ext_to_folder)
                
                # Sidecars might go with images or to separate folder
                if file_type == 'sidecars':
                    if sidecar_handling == "keep_with_images" and images:
                        target_dir = target_base_path / self._get_destination_folder('images', custom_type_to_folder)
                    elif sidecar_handling == "keep_txt_only" and file_path.suffix.lower() == '.txt' and images:
                        target_dir = target_base_path / self._get_destination_folder('images', custom_type_to_folder)
                    else:
                        target_dir = target_base_path / self._get_destination_folder('sidecars', custom_type_to_folder)
                else:
                    # Check for custom folder mapping for this file type (type -> custom folder name)
                    dest_folder = self._get_destination_folder(file_type, custom_type_to_folder)
                    target_dir = target_base_path / dest_folder
            else:
                target_dir = target_base_path
            
            # Create directory if needed
            if not dry_run and not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move the file
            self._move_single_file(file_path, target_dir, handle_conflicts, dry_run, stats, log_messages,
                                  source_folder_path)

    def _move_single_file(self, file_path, target_dir, handle_conflicts, dry_run, stats, log_messages,
                         source_folder_path=None):
        """Move a single file to target directory"""
        # Get the new filename (may include source folder name)
        new_filename = self._apply_source_folder_preservation(file_path, source_folder_path)
        target_path = target_dir / new_filename
        
        # Handle conflicts
        if target_path.exists() and target_path != file_path:
            if handle_conflicts == "skip":
                stats["files_skipped"] += 1
                return False
            elif handle_conflicts == "overwrite":
                if not dry_run:
                    target_path.unlink()
            elif handle_conflicts == "rename":
                target_path = self._get_unique_filename(target_path)
                stats["files_renamed"] += 1
                stats["conflicts_resolved"] += 1
        
        # Perform move
        if dry_run:
            log_messages.append(f"    Would move: {file_path.name} -> {target_dir}")
        else:
            if file_path != target_path:  # Only move if source != target
                shutil.move(str(file_path), str(target_path))
                log_messages.append(f"    Moved: {file_path.name} -> {target_dir.name}/")
        
        # Update stats
        stats["files_moved"] += 1
        file_type = self._get_file_type(file_path)  # Use without custom mappings for stats
        if file_type == 'images':
            stats["images_moved"] += 1
        elif file_type == 'movies':
            stats["movies_moved"] += 1
        elif file_type == 'text':
            stats["text_moved"] += 1
        elif file_type == 'sidecars':
            stats["sidecars_moved"] += 1
        else:
            stats["other_moved"] += 1
        
        stats["moved_files"].append({
            "source": str(file_path),
            "target": str(target_path)
        })
        
        return True

    def _apply_source_folder_preservation(self, file_path, source_folder_path):
        """Apply source folder name to filename based on preserve_source_folder setting"""
        # This will be set as an instance variable when processing
        preserve_mode = getattr(self, '_preserve_source_folder', 'none')
        
        if preserve_mode == 'none' or not source_folder_path:
            return file_path.name
        
        # Get just the source folder name (not full path)
        source_folder_name = source_folder_path.name
        
        # Don't add folder name if it's a type folder (images, movies, etc.)
        type_folder_names = {'images', 'movies', 'text', 'other', 'sidecars', 'below_min'}
        if source_folder_name.lower() in type_folder_names:
            return file_path.name
        
        # Apply prefix or suffix
        stem = file_path.stem
        ext = file_path.suffix
        
        if preserve_mode == 'prefix':
            return f"{source_folder_name}_{stem}{ext}"
        elif preserve_mode == 'suffix':
            return f"{stem}_{source_folder_name}{ext}"
        
        return file_path.name
    
    def _get_unique_filename(self, target_path):
        """Generate unique filename with (1), (2), etc."""
        base = target_path.stem
        ext = target_path.suffix
        parent = target_path.parent
        counter = 1
        
        while target_path.exists():
            new_name = f"{base} ({counter}){ext}"
            target_path = parent / new_name
            counter += 1
        
        return target_path

    def _remove_empty_directories(self, main_directory, log_messages):
        """Remove empty directories recursively"""
        removed_count = 0
        main_path = Path(main_directory)
        
        # Get all directories sorted by depth (deepest first)
        all_dirs = []
        for root, dirs, files in os.walk(main_directory):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                all_dirs.append(dir_path)
        
        all_dirs.sort(key=lambda x: len(x.parts), reverse=True)
        
        for dir_path in all_dirs:
            try:
                if dir_path == main_path:
                    continue
                
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    removed_count += 1
                    log_messages.append(f"  Removed empty: {dir_path.name}")
            except:
                pass
        
        return removed_count

    def _find_empty_directories(self, main_directory):
        """Find empty directories for dry run"""
        empty_dirs = []
        main_path = Path(main_directory)
        
        for root, dirs, files in os.walk(main_directory):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                if dir_path != main_path:
                    try:
                        if not any(dir_path.iterdir()):
                            empty_dirs.append(dir_path)
                    except:
                        pass
        
        return empty_dirs

# Required for ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "FlattenNestedFiles_v2": FlattenNestedFiles
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FlattenNestedFiles_v2": "Flatten Nested Files v0.2"
}
