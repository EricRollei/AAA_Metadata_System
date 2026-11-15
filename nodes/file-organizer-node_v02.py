"""
ComfyUI Node: File Organizer Node v0.2
Description: 
Intelligent file organizer that sorts files by type into subfolders and filters images
by dimensions. Features improved GUI organization, empty folder cleanup, and detailed reporting.

Improvements in v0.2:
- Better organized GUI with logical sections
- Automatically removes empty subfolders after organization
- Clearer option descriptions and grouping
- Enhanced status reporting
- Preview mode to see what would be organized
- Better handling of edge cases

Features:
- Sort files by type (images, movies, documents, audio, archives, other)
- Filter images by minimum dimensions (width, height, or both)
- Smart sidecar file handling (.xmp, .json, .txt captions)
- Multiple subfolder handling modes
- Removes empty folders automatically
- Detailed statistics and logging
- Preview mode (dry run)

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.2.0
Date: 2026-01-07
License: Dual License (Non-Commercial and Commercial Use)
Copyright (c) 2025-2026 Eric Hiss. All rights reserved.

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
import shutil
from pathlib import Path
from collections import defaultdict
import time
from datetime import datetime
import json
from PIL import Image

class FileOrganizerV2:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # === FOLDER PATHS ===
                "folder_paths": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "tooltip": "Folder paths to organize (one per line, or semicolon-separated)"
                }),
                
                # === ORGANIZATION MODE ===
                "organization_mode": (["Organize by Type", "Filter Small Images Only", "Full Organization + Filter"], {
                    "default": "Full Organization + Filter",
                    "tooltip": "Organize by Type: Sort files into type folders | Filter Small: Only remove/move small images | Full: Do both"
                }),
                
                # === IMAGE FILTERING ===
                "enable_image_filter": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Enable filtering of images by dimensions"
                }),
                "min_width": ("INT", {
                    "default": 512, 
                    "min": 1, 
                    "max": 8192, 
                    "step": 1,
                    "tooltip": "Minimum image width in pixels"
                }),
                "min_height": ("INT", {
                    "default": 512, 
                    "min": 1, 
                    "max": 8192, 
                    "step": 1,
                    "tooltip": "Minimum image height in pixels"
                }),
                "dimension_rule": (["Both must meet minimum", "Either can meet minimum", "Shortest side only", "Longest side only"], {
                    "default": "Shortest side only",
                    "tooltip": "Both: width AND height >= min | Either: width OR height >= min | Shortest: min(w,h) >= min | Longest: max(w,h) >= min"
                }),
                "small_image_action": (["Move to 'below_min'", "Move to 'rejected'", "Delete permanently"], {
                    "default": "Move to 'below_min'",
                    "tooltip": "What to do with images below minimum dimensions"
                }),
                
                # === SUBFOLDER HANDLING ===
                "subfolder_mode": (["Flatten everything to root", "Organize within each subfolder", "Root folder only"], {
                    "default": "Organize within each subfolder",
                    "tooltip": "Flatten: Move all to root type folders | Within each: Create type folders in each subfolder | Root only: Ignore subfolders"
                }),
                
                # === SIDECAR FILES ===
                "sidecar_mode": (["Keep .txt captions with images", "Keep all sidecars with images", "Move sidecars to separate folder"], {
                    "default": "Keep all sidecars with images",
                    "tooltip": ".txt captions: Keep .txt files with images, separate .xmp/.json | All: Keep all metadata with images | Separate: Move all to sidecars folder"
                }),
                
                # === CLEANUP ===
                "remove_empty_folders": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Remove empty subfolders after organization"
                }),
                
                # === SAFETY ===
                "preview_mode": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Dry run - show what would be done without actually moving files"
                }),
            },
            "optional": {
                "folder_paths_from_node": ("STRING", {
                    "default": "",
                    "tooltip": "Folder paths from another node (e.g., web scraper)"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING", "INT")
    RETURN_NAMES = ("status", "files_processed", "stats_json", "detailed_log", "empty_folders_removed")
    FUNCTION = "organize_files"
    CATEGORY = "Eric/Files"
    OUTPUT_NODE = True

    def __init__(self):
        # File type mappings - expanded categories
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.ico', '.svg'}
        self.movie_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'}
        self.audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus'}
        self.document_extensions = {'.txt', '.md', '.doc', '.docx', '.pdf', '.rtf', '.odt', '.tex'}
        self.archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}
        self.sidecar_extensions = {'.xmp', '.json', '.txt'}  # txt can be both doc and sidecar

    def organize_files(self, folder_paths, organization_mode, enable_image_filter,
                      min_width, min_height, dimension_rule, small_image_action,
                      subfolder_mode, sidecar_mode, remove_empty_folders, preview_mode,
                      folder_paths_from_node=""):
        """
        Main function to organize files
        """
        start_time = time.time()
        
        # Initialize stats
        stats = {
            "start_time": datetime.now().isoformat(),
            "preview_mode": preview_mode,
            "folders_processed": 0,
            "files_processed": 0,
            "files_moved": 0,
            "images": {"total": 0, "kept": 0, "filtered": 0, "deleted": 0},
            "movies": 0,
            "audio": 0,
            "documents": 0,
            "archives": 0,
            "other": 0,
            "sidecars": 0,
            "type_folders_created": 0,
            "empty_folders_removed": 0,
            "errors": [],
            "processed_folders": []
        }
        
        log_messages = []
        log_messages.append(f"{'='*60}")
        log_messages.append(f"File Organizer v0.2 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_messages.append(f"{'='*60}")
        
        if preview_mode:
            log_messages.append("⚠️  PREVIEW MODE - No files will be moved")
        
        try:
            # Parse and validate folder paths
            folder_list = self._parse_folder_paths(folder_paths, folder_paths_from_node)
            
            if not folder_list:
                return self._error_return("No folder paths provided", stats, log_messages)
            
            valid_folders = self._validate_folders(folder_list, log_messages, stats)
            
            if not valid_folders:
                return self._error_return("No valid folder paths found", stats, log_messages)
            
            # Log configuration
            log_messages.append(f"\nConfiguration:")
            log_messages.append(f"  Mode: {organization_mode}")
            log_messages.append(f"  Subfolder handling: {subfolder_mode}")
            log_messages.append(f"  Sidecar handling: {sidecar_mode}")
            
            if enable_image_filter:
                log_messages.append(f"  Image filter: {min_width}×{min_height} ({dimension_rule})")
                log_messages.append(f"  Small images: {small_image_action}")
            else:
                log_messages.append(f"  Image filter: Disabled")
            
            log_messages.append(f"  Remove empty folders: {remove_empty_folders}")
            log_messages.append(f"\nProcessing {len(valid_folders)} folder(s)...")
            log_messages.append("")
            
            # Process each folder
            for folder_path in valid_folders:
                try:
                    folder_stats = self._organize_folder(
                        folder_path, organization_mode, enable_image_filter,
                        min_width, min_height, dimension_rule, small_image_action,
                        subfolder_mode, sidecar_mode, preview_mode, log_messages
                    )
                    
                    # Accumulate stats
                    self._accumulate_stats(stats, folder_stats)
                    stats["folders_processed"] += 1
                    stats["processed_folders"].append(str(folder_path))
                    
                except Exception as e:
                    error_msg = f"Error processing folder {folder_path}: {str(e)}"
                    stats["errors"].append(error_msg)
                    log_messages.append(f"❌ ERROR: {error_msg}")
            
            # Remove empty folders if requested
            if remove_empty_folders and not preview_mode:
                for folder_path in valid_folders:
                    removed = self._remove_empty_folders(folder_path, log_messages)
                    stats["empty_folders_removed"] += removed
            elif remove_empty_folders and preview_mode:
                log_messages.append("\n📋 Preview: Would remove empty folders (skipped in preview mode)")
            
            # Generate final status
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            status_message = self._generate_status_message(stats, preview_mode)
            
            log_messages.append(f"\n{'='*60}")
            log_messages.append(f"SUMMARY: {status_message}")
            log_messages.append(f"Duration: {stats['duration_seconds']} seconds")
            log_messages.append(f"{'='*60}")
            
            return (
                status_message, 
                stats["files_processed"],
                json.dumps(stats, indent=2),
                "\n".join(log_messages),
                stats["empty_folders_removed"]
            )
            
        except Exception as e:
            return self._error_return(f"Fatal error: {str(e)}", stats, log_messages)

    def _parse_folder_paths(self, manual_input, node_input):
        """Parse folder paths from both inputs"""
        folder_list = []
        
        # Combine inputs
        combined = []
        if node_input:
            combined.append(node_input)
        if manual_input:
            combined.append(manual_input)
        
        for text in combined:
            # Handle both newline and semicolon separated paths
            text = text.replace(';', '\n')
            paths = [p.strip() for p in text.splitlines() if p.strip()]
            folder_list.extend(paths)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_list = []
        for path in folder_list:
            if path not in seen:
                seen.add(path)
                unique_list.append(path)
        
        return unique_list

    def _validate_folders(self, folder_list, log_messages, stats):
        """Validate folder paths"""
        valid_folders = []
        
        for folder_path in folder_list:
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                valid_folders.append(Path(folder_path))
                log_messages.append(f"✓ Valid folder: {folder_path}")
            else:
                error_msg = f"Invalid or missing folder: {folder_path}"
                stats["errors"].append(error_msg)
                log_messages.append(f"⚠️  {error_msg}")
        
        return valid_folders

    def _organize_folder(self, folder_path, organization_mode, enable_image_filter,
                        min_width, min_height, dimension_rule, small_image_action,
                        subfolder_mode, sidecar_mode, preview_mode, log_messages):
        """Organize files in a single folder"""
        
        folder_stats = {
            "files_processed": 0,
            "files_moved": 0,
            "images": {"total": 0, "kept": 0, "filtered": 0, "deleted": 0},
            "movies": 0,
            "audio": 0,
            "documents": 0,
            "archives": 0,
            "other": 0,
            "sidecars": 0,
            "type_folders_created": 0,
            "errors": []
        }
        
        log_messages.append(f"\n📁 Processing: {folder_path}")
        
        # Determine which folders to process
        folders_to_process = self._get_folders_to_process(folder_path, subfolder_mode, log_messages)
        
        # Process each directory
        for current_dir in folders_to_process:
            self._organize_directory(
                current_dir, folder_path, organization_mode, enable_image_filter,
                min_width, min_height, dimension_rule, small_image_action,
                subfolder_mode, sidecar_mode, preview_mode, folder_stats, log_messages
            )
        
        return folder_stats

    def _get_folders_to_process(self, root_folder, subfolder_mode, log_messages):
        """Determine which folders to process based on mode"""
        
        type_folder_names = {'images', 'movies', 'audio', 'documents', 'archives', 'other', 'sidecars', 'below_min', 'rejected'}
        
        if subfolder_mode == "Root folder only":
            return [root_folder]
        
        elif subfolder_mode == "Organize within each subfolder":
            # Check if type folders already exist at root
            existing_type_folders = {d.name.lower() for d in root_folder.iterdir() 
                                    if d.is_dir() and d.name.lower() in type_folder_names}
            
            if existing_type_folders:
                log_messages.append(f"  Found existing type folders, will organize within them")
                return [root_folder]
            else:
                # Include root and all non-type subdirectories
                folders = [root_folder]
                for d in root_folder.iterdir():
                    if d.is_dir() and d.name.lower() not in type_folder_names:
                        folders.append(d)
                return folders
        
        elif subfolder_mode == "Flatten everything to root":
            return [root_folder]
        
        return [root_folder]

    def _organize_directory(self, directory, root_folder, organization_mode, enable_image_filter,
                          min_width, min_height, dimension_rule, small_image_action,
                          subfolder_mode, sidecar_mode, preview_mode, stats, log_messages):
        """Organize files within a single directory"""
        
        directory = Path(directory)
        
        # Get files based on subfolder mode
        if subfolder_mode == "Flatten everything to root":
            files = list(directory.rglob('*'))
            files = [f for f in files if f.is_file()]
        else:
            files = [f for f in directory.iterdir() if f.is_file()]
        
        if not files:
            return
        
        log_messages.append(f"  Processing {len(files)} files in {directory.name}")
        
        # Create type folders
        type_folders = self._create_type_folders(directory, organization_mode, small_image_action, 
                                                preview_mode, stats, log_messages)
        
        # Categorize and process files
        self._process_files(files, directory, type_folders, organization_mode, enable_image_filter,
                          min_width, min_height, dimension_rule, small_image_action,
                          sidecar_mode, preview_mode, stats, log_messages)

    def _create_type_folders(self, directory, organization_mode, small_image_action, 
                           preview_mode, stats, log_messages):
        """Create organizational folders"""
        type_folders = {}
        
        if organization_mode == "Filter Small Images Only":
            # Only create folders for small images
            folders_needed = ['below_min' if 'below_min' in small_image_action.lower() else 'rejected']
        else:
            # Create all type folders
            folders_needed = ['images', 'movies', 'audio', 'documents', 'archives', 'other', 'sidecars']
            if 'below_min' in small_image_action.lower():
                folders_needed.append('below_min')
            if 'rejected' in small_image_action.lower():
                folders_needed.append('rejected')
        
        for folder_type in folders_needed:
            folder_path = directory / folder_type
            type_folders[folder_type] = folder_path
            
            if not folder_path.exists():
                if not preview_mode:
                    folder_path.mkdir(exist_ok=True)
                    stats["type_folders_created"] += 1
                log_messages.append(f"  {'[Preview]' if preview_mode else '✓'} Created folder: {folder_type}/")
        
        return type_folders

    def _process_files(self, files, directory, type_folders, organization_mode, enable_image_filter,
                      min_width, min_height, dimension_rule, small_image_action,
                      sidecar_mode, preview_mode, stats, log_messages):
        """Process and organize files"""
        
        # Categorize files
        categorized = self._categorize_files(files)
        
        # Process images with filtering
        for image_file in categorized['images']:
            self._process_image(image_file, type_folders, enable_image_filter,
                              min_width, min_height, dimension_rule, small_image_action,
                              sidecar_mode, preview_mode, stats, log_messages)
        
        # Process other file types
        if organization_mode != "Filter Small Images Only":
            for file_type, file_list in categorized.items():
                if file_type != 'images':
                    for file_path in file_list:
                        self._move_file(file_path, type_folders.get(file_type), preview_mode, stats, log_messages, file_type)

    def _categorize_files(self, files):
        """Categorize files by type"""
        categorized = {
            'images': [],
            'movies': [],
            'audio': [],
            'documents': [],
            'archives': [],
            'other': [],
            'sidecars': []
        }
        
        for file_path in files:
            ext = file_path.suffix.lower()
            
            if ext in self.image_extensions:
                categorized['images'].append(file_path)
            elif ext in self.movie_extensions:
                categorized['movies'].append(file_path)
            elif ext in self.audio_extensions:
                categorized['audio'].append(file_path)
            elif ext in self.document_extensions and ext != '.txt':  # .txt handled as sidecar
                categorized['documents'].append(file_path)
            elif ext in self.archive_extensions:
                categorized['archives'].append(file_path)
            elif ext in self.sidecar_extensions:
                categorized['sidecars'].append(file_path)
            else:
                categorized['other'].append(file_path)
        
        return categorized

    def _process_image(self, image_file, type_folders, enable_image_filter,
                      min_width, min_height, dimension_rule, small_image_action,
                      sidecar_mode, preview_mode, stats, log_messages):
        """Process a single image file"""
        
        stats["images"]["total"] += 1
        stats["files_processed"] += 1
        
        try:
            # Check dimensions if filtering enabled
            if enable_image_filter:
                is_small = self._check_image_dimensions(image_file, min_width, min_height, dimension_rule)
            else:
                is_small = False
            
            if is_small:
                stats["images"]["filtered"] += 1
                
                if "Delete" in small_image_action:
                    if not preview_mode:
                        image_file.unlink()
                    stats["images"]["deleted"] += 1
                    log_messages.append(f"  {'[Preview]' if preview_mode else '🗑️ '} Deleted small image: {image_file.name}")
                else:
                    folder_key = 'below_min' if 'below_min' in small_image_action.lower() else 'rejected'
                    self._move_file(image_file, type_folders.get(folder_key), preview_mode, stats, log_messages, "small_image")
            else:
                # Move normal-sized image
                stats["images"]["kept"] += 1
                self._move_file(image_file, type_folders.get('images'), preview_mode, stats, log_messages, "image")
                
                # Handle sidecars
                if type_folders.get('images'):
                    self._handle_sidecars(image_file, type_folders, sidecar_mode, preview_mode, stats, log_messages)
        
        except Exception as e:
            error_msg = f"Error processing image {image_file.name}: {str(e)}"
            stats["errors"].append(error_msg)
            log_messages.append(f"  ❌ {error_msg}")

    def _check_image_dimensions(self, image_path, min_width, min_height, dimension_rule):
        """Check if image meets dimension requirements"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                if dimension_rule == "Both must meet minimum":
                    return width < min_width or height < min_height
                elif dimension_rule == "Either can meet minimum":
                    return width < min_width and height < min_height
                elif dimension_rule == "Shortest side only":
                    return min(width, height) < min(min_width, min_height)
                elif dimension_rule == "Longest side only":
                    return max(width, height) < max(min_width, min_height)
        except Exception:
            return True  # Treat unreadable images as small
        
        return False

    def _move_file(self, file_path, target_folder, preview_mode, stats, log_messages, file_type):
        """Move a file to target folder"""
        if not target_folder:
            return
        
        try:
            target_path = target_folder / file_path.name
            
            # Handle name conflicts
            if target_path.exists() and target_path != file_path:
                base = target_path.stem
                ext = target_path.suffix
                counter = 1
                while target_path.exists():
                    target_path = target_folder / f"{base}_{counter}{ext}"
                    counter += 1
            
            if not preview_mode and target_path != file_path:
                shutil.move(str(file_path), str(target_path))
                stats["files_moved"] += 1
            
            # Update category stats
            if file_type in ["image", "small_image"]:
                pass  # Already counted in images
            else:
                stats[file_type] = stats.get(file_type, 0) + 1
        
        except Exception as e:
            error_msg = f"Error moving {file_path.name}: {str(e)}"
            stats["errors"].append(error_msg)
            log_messages.append(f"  ❌ {error_msg}")

    def _handle_sidecars(self, image_file, type_folders, sidecar_mode, preview_mode, stats, log_messages):
        """Handle sidecar files associated with an image"""
        base_name = image_file.stem
        image_dir = image_file.parent
        
        for ext in self.sidecar_extensions:
            sidecar_file = image_dir / f"{base_name}{ext}"
            if sidecar_file.exists():
                if "Keep .txt captions" in sidecar_mode:
                    target = type_folders['images'] if ext == '.txt' else type_folders.get('sidecars')
                elif "Keep all sidecars" in sidecar_mode:
                    target = type_folders['images']
                else:  # Separate
                    target = type_folders.get('sidecars')
                
                if target:
                    self._move_file(sidecar_file, target, preview_mode, stats, log_messages, "sidecars")
                    stats["sidecars"] += 1

    def _remove_empty_folders(self, root_folder, log_messages):
        """Remove empty subfolders recursively"""
        removed_count = 0
        
        log_messages.append(f"\n🧹 Cleaning up empty folders in {root_folder}")
        
        # Walk bottom-up to remove nested empty folders first
        for dirpath, dirnames, filenames in os.walk(root_folder, topdown=False):
            for dirname in dirnames:
                folder_path = Path(dirpath) / dirname
                try:
                    if not any(folder_path.iterdir()):  # Check if empty
                        folder_path.rmdir()
                        removed_count += 1
                        log_messages.append(f"  🗑️  Removed empty folder: {folder_path.relative_to(root_folder)}")
                except Exception as e:
                    log_messages.append(f"  ⚠️  Could not remove {dirname}: {str(e)}")
        
        return removed_count

    def _accumulate_stats(self, total_stats, folder_stats):
        """Accumulate folder stats into total stats"""
        for key in folder_stats:
            if key == "images":
                for subkey in folder_stats["images"]:
                    total_stats["images"][subkey] += folder_stats["images"][subkey]
            elif key in total_stats and isinstance(total_stats[key], int):
                total_stats[key] += folder_stats[key]
            elif key == "errors":
                total_stats["errors"].extend(folder_stats["errors"])

    def _generate_status_message(self, stats, preview_mode):
        """Generate human-readable status message"""
        prefix = "[PREVIEW] Would process" if preview_mode else "Processed"
        
        msg = f"{prefix} {stats['files_processed']} files"
        
        details = []
        if stats["images"]["total"] > 0:
            details.append(f"{stats['images']['kept']} images kept")
            if stats["images"]["filtered"] > 0:
                details.append(f"{stats['images']['filtered']} filtered")
            if stats["images"]["deleted"] > 0:
                details.append(f"{stats['images']['deleted']} deleted")
        
        for ftype in ["movies", "audio", "documents", "archives", "other", "sidecars"]:
            if stats[ftype] > 0:
                details.append(f"{stats[ftype]} {ftype}")
        
        if details:
            msg += " (" + ", ".join(details) + ")"
        
        if stats["empty_folders_removed"] > 0:
            msg += f" | Removed {stats['empty_folders_removed']} empty folders"
        
        if stats["errors"]:
            msg += f" | {len(stats['errors'])} errors"
        
        return msg

    def _error_return(self, error_msg, stats, log_messages):
        """Return error result"""
        stats["error"] = error_msg
        log_messages.append(f"\n❌ FATAL ERROR: {error_msg}")
        return (
            f"ERROR: {error_msg}",
            0,
            json.dumps(stats, indent=2),
            "\n".join(log_messages),
            0
        )


# Required for ComfyUI node registration
NODE_CLASS_MAPPINGS = {
    "FileOrganizerV2": FileOrganizerV2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FileOrganizerV2": "File Organizer v2"
}
