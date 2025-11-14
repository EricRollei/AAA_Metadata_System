"""
ComfyUI Node: lora_tester_node_v03.py
Description: This node allows users to test LoRA models with flexible filtering options.
It supports searching by directory name, filtering by filename, and filtering by model architecture type (SD1.5, SDXL, Flux, etc.).       
It provides count statistics of available and filtered LoRAs, outputs a text list of selected LoRAs, and runs batch processing with sequential or random selection. The node can operate in two modes: direct loading (applies LoRA to model/CLIP) or info provider (outputs LoRA info for other nodes).
Author: Eric Hiss (GitHub: EricRollei) 
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.0.1

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

import os
import re
import json
import random
import glob
import hashlib
import requests  
import gc  
from datetime import datetime 
from pathlib import Path
from typing import List, Dict, Tuple, Union, Optional, Any
from PIL import Image, ImageOps
import numpy as np
import torch

import folder_paths
import comfy.utils
import comfy.model_management

from comfy.sd import load_lora_for_models
from comfy.utils import load_torch_file


class LoRATesterNode:
    """
    ComfyUI node for testing LoRA models with flexible filtering options.
    
    This node allows users to:
    1. Search for LoRAs by directory name
    2. Filter LoRAs by filename
    3. Filter by model architecture type (SD1.5, SDXL, Flux, etc.)
    4. Search by trigger words
    5. View count statistics of available and filtered LoRAs
    6. Output a text list of selected LoRAs
    7. Run batch processing with sequential or random selection
    8. Support two modes: direct loading or info provider
    9. Auto-discover and display associated images
    10. Store/load LoRA-specific parameters and trigger words
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the node."""
        return {
            "required": {
                "dir_search_terms": ("STRING", {"default": "", "multiline": False, 
                                    "tooltip": "Comma-separated terms to search in directory paths. Use -term to exclude."}),
                "file_search_terms": ("STRING", {"default": "", "multiline": False,
                                    "tooltip": "Comma-separated terms to search in LoRA filenames. Use -term to exclude (e.g., -pony,-inpaint)."}),
                "additional_path": ("STRING", {"default": "", "multiline": False,
                                "tooltip": "Additional directory to search for LoRAs"}),
                "architecture": (["Any", "SD1.5", "SDXL", "Flux", "Pony", "Illustrious", 
                                "Noobai", "SD3.5 Medium", "SD3.5 Large", "HiDream", 
                                "Stable Cascade", "PixArt Sigma", "Playground"], 
                                {"default": "Any", "tooltip": "Filter by model architecture"}),
                "category": (["Any", "unknown", "style", "character", "concept", "pose", 
                            "clothing", "background", "effect", "artistic", "photographic", 
                            "graphic", "treatment", "tool", "slider", 
                            "anime", "realism", "details", "lighting", "mood", "texture",
                            "fantasy", "scifi", "historical", "nsfw", "enhancement"],
                            {"default": "Any", "tooltip": "Filter by LoRA category"}),
                "trigger_search": ("STRING", {"default": "", "multiline": False,
                            "tooltip": "Search terms to match in trigger words. Use -term to exclude."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, 
                        "tooltip": "LoRA number to load (0 = random, 1 = first in list)"}),
                "mode": (["direct_load", "info_only"], {
                    "default": "direct_load",
                    "tooltip": "direct_load: Apply LoRA to model/CLIP, info_only: Just output LoRA info"
                }),
                "model_strength": ("FLOAT", {"default": 0.8, "min": -5.0, "max": 5.0, "step": 0.05,
                    "tooltip": "Strength multiplier for model (used if direct_load mode)"}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": -5.0, "max": 5.0, "step": 0.05,
                    "tooltip": "Strength multiplier for CLIP (used if direct_load mode)"}),
                "use_database_defaults": ("BOOLEAN", {"default": True,
                    "tooltip": "Use LoRA-specific defaults from database if available"}),
                "query_civitai": ("BOOLEAN", {"default": False,
                    "tooltip": "Automatically query Civitai for trigger words when LoRA has none"}),
                "force_civitai_fetch": ("BOOLEAN", {"default": False,
                    "tooltip": "Force fetch from Civitai even if tags already exist"}),
                "prompt_placement": (["auto", "beginning", "end", "none"], {"default": "auto",
                "tooltip": "Where to place trigger words: auto (use database setting), beginning, end, or none (no insertion)"
            }),
                # Add gallery options
                "max_gallery_images": ("INT", {"default": 50, "min": 1, "max": 200,
                    "tooltip": "Maximum number of images to include in gallery"}),
                "gallery_image_size": ("INT", {"default": 512, "min": 128, "max": 1024, "step": 64,
                    "tooltip": "Target size for gallery images (they will be resized to this)"}),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "Input model (required for direct_load mode)"}),
                "clip": ("CLIP", {"tooltip": "Input CLIP (required for direct_load mode)"}),
                "input_prompt": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "Input prompt text to combine with trigger words"}),
                "primary_trigger_override": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Override the primary trigger word selection"}),
            }
        }

    RETURN_TYPES = (
        "MODEL", "CLIP", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING",
        "INT", "INT", "IMAGE", "FLOAT", "FLOAT", "IMAGE"
    )
    RETURN_NAMES = (
        "model", "clip", "lora_name", "lora_path", "trigger_words_all",
        "trigger_words_selected", "combined_prompt", "lora_list", "total_loras", "selected_loras",
        "associated_images", "model_strength_used", "clip_strength_used", "gallery_images"
    )

    FUNCTION = "process_loras"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the LoRA tester node."""
        # Lists to store paths and filtered LoRAs
        self.lora_paths = []
        self.filtered_loras = []
        
        # Track current index for sequential processing
        self.current_index = 0
        
        # Track seed for determining selection mode
        self.last_seed = None
        
        # Database for storing LoRA metadata
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        
        # Import existing tags file if available
        self.tags_file_path = os.path.join(os.path.dirname(__file__), "loras_tags.json")
        if os.path.exists(self.tags_file_path) and not self.lora_db.get("tags_imported", False):
            self._import_existing_tags()
        
        # Load the current index from database if available
        if "current_index" in self.lora_db:
            self.current_index = self.lora_db["current_index"]
            print(f"[LoRATester] Loaded current_index from database: {self.current_index}")
        else:
            print("[LoRATester] No current_index in database, using default: 0")
        
        # Architecture identification patterns
        self.known_architectures = {
            "SD1.5": {
                "patterns": ["sd1.5", "sd15", "sd-1-5", "stable-diffusion-v1", "v1-5", "sd_v1", "sd1", "sd_1"],
                "defaults": {"model": 0.75, "clip": 1.0}
            },
            "SD2.1": {
                "patterns": ["sd2.1", "sd21", "sd-2-1", "stable-diffusion-v2", "v2-1", "sd2", "v2", "sd_2"],
                "defaults": {"model": 0.75, "clip": 1.0}
            },
            "SDXL": {
                "patterns": ["sdxl", "sd-xl", "stable-diffusion-xl", "sd_xl", "xl_base", "SDXL", "XL_"],
                "defaults": {"model": 0.7, "clip": 1.0}
            },
            "SD3.5 Medium": {
                "patterns": ["sd3.5", "sd35", "sd35medium", "medium", "sd3-medium"],
                "defaults": {"model": 0.66, "clip": 1.0}
            },
            "SD3.5 Large": {
                "patterns": ["sd3.5", "sd35", "sd35large", "large", "sd3-large"],
                "defaults": {"model": 0.66, "clip": 1.0}
            },
            "Flux": {
                "patterns": ["flux", "FLUX", "Flux1", "flux1d", "flux-1d", "flux_1d"],
                "defaults": {"model": 0.8, "clip": 1.0}
            },
            "Pony": {
                "patterns": ["pony", "PONY", "Pony", "ponyV1"],
                "defaults": {"model": 0.75, "clip": 1.0}
            },
            "Illustrious": {
                "patterns": ["illustrious", "illustrious-xl"],
                "defaults": {"model": 0.7, "clip": 1.0}
            },
            "Noobai": {
                "patterns": ["noobai", "noobai-xl"],
                "defaults": {"model": 0.7, "clip": 1.0}
            },
            "HiDream": {
                "patterns": ["hidream", "HiDream"],
                "defaults": {"model": 0.8, "clip": 1.0}
            },
            "Stable Cascade": {
                "patterns": ["cascade", "stable-cascade"],
                "defaults": {"model": 0.8, "clip": 1.0}
            },
            "PixArt Sigma": {
                "patterns": ["pixart", "pixart-sigma"],
                "defaults": {"model": 0.8, "clip": 1.0}
            },
            "Playground": {
                "patterns": ["playground", "playground-v2"],
                "defaults": {"model": 0.7, "clip": 1.0}
            }
        }
        
        # Initial scan of available LoRAs
        self.scan_loras()

        # Add Civitai integration settings
        self.civitai_cache_file = os.path.join(os.path.dirname(__file__), "civitai_cache.json")
        self.civitai_cache = self._load_civitai_cache()

    def _load_civitai_cache(self) -> Dict:
        """Load Civitai cache from disk."""
        if os.path.exists(self.civitai_cache_file):
            try:
                with open(self.civitai_cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_civitai_cache(self):
        """Save Civitai cache to disk."""
        try:
            with open(self.civitai_cache_file, 'w') as f:
                json.dump(self.civitai_cache, f, indent=2)
        except IOError as e:
            print(f"[LoRATester] Warning: Could not save Civitai cache: {e}")

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash for Civitai API lookup."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[LoRATester] Error calculating SHA256 for {file_path}: {e}")
            return ""

    def _get_civitai_model_info(self, sha256_hash: str) -> Optional[Dict]:
        """Query Civitai API for model information."""
        # Check cache first
        if sha256_hash in self.civitai_cache:
            print(f"[LoRATester] Using cached Civitai data for hash {sha256_hash[:8]}...")
            return self.civitai_cache[sha256_hash]
        
        try:
            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256_hash}"
            print(f"[LoRATester] Querying Civitai API for hash {sha256_hash[:8]}...")
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                model_info = response.json()
                # Cache the result
                self.civitai_cache[sha256_hash] = model_info
                self._save_civitai_cache()
                print(f"[LoRATester] Successfully retrieved Civitai data")
                return model_info
            elif response.status_code == 404:
                # Cache negative result to avoid repeated queries
                self.civitai_cache[sha256_hash] = None
                self._save_civitai_cache()
                print(f"[LoRATester] LoRA not found on Civitai")
                return None
            else:
                print(f"[LoRATester] Civitai API returned status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"[LoRATester] Error querying Civitai API: {e}")
            return None

    def _fetch_civitai_tags(self, lora_path: str, force_fetch: bool = False) -> List[str]:
        """Fetch trigger words from Civitai for a specific LoRA."""
        lora_hash = self._calculate_lora_hash(lora_path)
        
        # Check if we already have tags and don't need to force fetch
        if not force_fetch and lora_hash in self.lora_db["loras"]:
            existing_tags = self.lora_db["loras"][lora_hash].get("trigger_words", {}).get("full_list", [])
            if existing_tags:
                return existing_tags
        
        # Calculate SHA256 for Civitai lookup
        sha256_hash = self._calculate_sha256(lora_path)
        if not sha256_hash:
            return []
        
        # Query Civitai
        model_info = self._get_civitai_model_info(sha256_hash)
        if model_info and "trainedWords" in model_info:
            tags = model_info["trainedWords"]
            print(f"[LoRATester] Found {len(tags)} trigger words from Civitai")
            
            # Update database
            if lora_hash not in self.lora_db["loras"]:
                # Initialize entry if it doesn't exist
                self._update_lora_database()
            
            if lora_hash in self.lora_db["loras"]:
                self.lora_db["loras"][lora_hash]["trigger_words"]["full_list"] = tags
                self.lora_db["loras"][lora_hash]["trigger_words"]["imported_from"] = "civitai"
                self._save_lora_db()
            
            return tags
        else:
            print(f"[LoRATester] No trigger words found on Civitai")
            # Mark as queried to avoid repeated attempts
            if lora_hash in self.lora_db["loras"]:
                self.lora_db["loras"][lora_hash]["trigger_words"]["imported_from"] = "civitai_not_found"
                self._save_lora_db()
            return []

    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    db = json.load(f)
                    # Ensure required fields exist
                    if "current_index" not in db:
                        db["current_index"] = 0
                    if "loras" not in db:
                        db["loras"] = {}
                    if "version" not in db:
                        db["version"] = "1.0"
                    if "tags_imported" not in db:
                        db["tags_imported"] = False
                    
                    # Ensure all LoRAs have the necessary fields
                    for lora_hash, lora_data in db.get("loras", {}).items():
                        if "category" not in lora_data:
                            lora_data["category"] = "unknown"
                        if "notes" not in lora_data:
                            lora_data["notes"] = ""
                        if "trigger_words" not in lora_data:
                            lora_data["trigger_words"] = {
                                "full_list": [],
                                "selected": [],
                                "imported_from": ""
                            }
                        if "strengths" not in lora_data:
                            lora_data["strengths"] = {
                                "model_default": 0.8,
                                "clip_default": 1.0,
                                "architecture_specific": {}
                            }
                        if "compatible_checkpoints" not in lora_data:
                            lora_data["compatible_checkpoints"] = []
                        if "compatible_loras" not in lora_data:
                            lora_data["compatible_loras"] = []
                        
                    return db
            except (json.JSONDecodeError, IOError):
                print("Warning: LoRA database is corrupted. Creating a new one.")
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        else:
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}

    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            # Ensure current_index is in the database before saving
            self.lora_db["current_index"] = self.current_index
            
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
            print(f"[LoRATester] Database saved with current_index = {self.current_index}")
        except IOError as e:
            print(f"[LoRATester] Warning: Could not save LoRA database: {e}")


    def _create_lora_gallery(self, max_images: int = 50, target_size: int = 512) -> torch.Tensor:
        """
        Create a gallery of images from all filtered LoRAs.
        
        Args:
            max_images: Maximum number of images to include
            target_size: Target size for resizing images
            
        Returns:
            torch.Tensor: Batch tensor containing gallery images
        """
        gallery_images = []
        images_collected = 0
        
        print(f"[LoRATester] Creating gallery from {len(self.filtered_loras)} LoRAs...")
        
        for lora_path in self.filtered_loras:
            if images_collected >= max_images:
                break
                
            # Find associated images for this LoRA
            image_paths = self._find_associated_images(lora_path)
            
            if image_paths:
                # Take only the first image for each LoRA to avoid too many from one LoRA
                img_path = image_paths[0]
                try:
                    # Load and process the image
                    img = Image.open(img_path).convert('RGB')
                    
                    # Resize while maintaining aspect ratio
                    img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                    
                    # Pad to exact square size with dark gray background
                    img = ImageOps.pad(img, (target_size, target_size), color=(21, 21, 21))
                    
                    # Convert to numpy array and normalize
                    img_array = np.array(img).astype(np.float32) / 255.0
                    gallery_images.append(img_array)
                    images_collected += 1
                    
                except Exception as e:
                    print(f"[LoRATester] Error loading gallery image {img_path}: {e}")
                    continue
        
        if not gallery_images:
            # Create a dark gray placeholder if no images found
            placeholder = np.full((target_size, target_size, 3), 21/255.0, dtype=np.float32)
            gallery_images = [placeholder]
            print("[LoRATester] No gallery images found, using placeholder")
        else:
            print(f"[LoRATester] Created gallery with {len(gallery_images)} images")
        
        # Stack into batch tensor
        batch_tensor = np.stack(gallery_images, axis=0)
        return torch.from_numpy(batch_tensor)


    def _import_existing_tags(self):
        """Import trigger words from existing loras_tags.json file."""
        try:
            with open(self.tags_file_path, 'r') as f:
                tags_data = json.load(f)
            
            imported_count = 0
            for lora_path, trigger_words in tags_data.items():
                # Normalize path separators
                normalized_path = os.path.normpath(lora_path)
                
                # Find matching LoRA in database by comparing paths
                for lora_hash, lora_data in self.lora_db["loras"].items():
                    db_path = os.path.normpath(lora_data["path"])
                    if normalized_path in db_path or db_path.endswith(normalized_path):
                        # Import trigger words
                        if trigger_words:  # Only import if there are trigger words
                            lora_data["trigger_words"]["full_list"] = trigger_words
                            lora_data["trigger_words"]["imported_from"] = "loras_tags.json"
                            imported_count += 1
                        break
            
            # Mark as imported to avoid re-importing
            self.lora_db["tags_imported"] = True
            self._save_lora_db()
            
            print(f"[LoRATester] Imported trigger words for {imported_count} LoRAs from loras_tags.json")
            
        except Exception as e:
            print(f"[LoRATester] Error importing tags file: {e}")

    def _calculate_lora_hash(self, file_path: str) -> str:
        """
        Calculate a hash for the LoRA to use as a unique identifier.
        
        Uses file metadata for speed instead of hashing entire file.
        
        Args:
            file_path: Path to the LoRA file
            
        Returns:
            str: Hash string to uniquely identify this LoRA
        """
        try:
            hasher = hashlib.md5()
            
            # Add file metadata to the hash
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            
            # Read first 1MB of the file for a quick content hash
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
                
            return hasher.hexdigest()
        except:
            # If any error occurs, fall back to just using the path as an identifier
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()

    def scan_loras(self, additional_path: str = ""):
        """Scan for LoRA files in the filesystem."""
        self.lora_paths = []  # Reset
        
        # Get standard ComfyUI LoRA directories
        lora_dirs = folder_paths.get_folder_paths("loras")
        
        all_dirs_to_scan = list(lora_dirs)
        
        # Add additional path if specified
        if additional_path and os.path.isdir(additional_path):
            normalized_additional_path = os.path.normpath(additional_path)
            is_already_present = any(os.path.normpath(d) == normalized_additional_path for d in all_dirs_to_scan)
            if not is_already_present:
                all_dirs_to_scan.append(normalized_additional_path)
        
        # Supported extensions for LoRA files
        extensions = [".safetensors", ".pt", ".bin"]
        
        # Use a set to collect unique normalized paths
        unique_scan_dirs = set(os.path.normpath(d) for d in all_dirs_to_scan)
        
        temp_lora_paths = set()  # Use set to ensure uniqueness
        
        for directory in unique_scan_dirs:
            if not os.path.isdir(directory):
                continue
            for ext in extensions:
                pattern = os.path.join(directory, f"**/*{ext}")
                try:
                    found_files = glob.glob(pattern, recursive=True)
                    for file_path in found_files:
                        temp_lora_paths.add(os.path.normpath(file_path))
                except Exception as e:
                    print(f"[LoRATester] Error scanning directory {directory} with pattern {pattern}: {e}")
        
        self.lora_paths = sorted(list(temp_lora_paths))
        
        # Update database with discovered LoRAs
        self._update_lora_database()

    def _update_lora_database(self):
        """Update the LoRA database with newly discovered LoRAs."""
        updated = False
        
        for path in self.lora_paths:
            lora_hash = self._calculate_lora_hash(path)
            
            # Initialize new LoRA entry if not already in database
            if lora_hash not in self.lora_db["loras"]:
                lora_name = os.path.basename(path)
                
                # Detect architecture from filename and directory
                detected_arch = self._detect_architecture_from_path(path)
                
                self.lora_db["loras"][lora_hash] = {
                    "path": path,
                    "name": lora_name,
                    "architecture": detected_arch,
                    "category": self._guess_category_from_path(path),
                    "notes": "",
                    "trigger_words": {
                        "full_list": [],
                        "selected": [],
                        "imported_from": "",
                        "placement": "end",  # New field: "beginning", "end"
                        "placement_notes": ""  # Optional notes about placement
                    },
                    "strengths": {
                        "model_default": self.known_architectures.get(detected_arch, {}).get("defaults", {}).get("model", 0.8),
                        "clip_default": self.known_architectures.get(detected_arch, {}).get("defaults", {}).get("clip", 1.0),
                        "architecture_specific": {}
                    },
                    "compatible_checkpoints": [],
                    "compatible_loras": [],
                    "recommended_settings": {
                        "best_checkpoints": [],     # Names of checkpoints this works best with
                        "avoid_checkpoints": [],    # Checkpoints to avoid
                        "optimal_cfg_range": "",    # e.g., "7-12"
                        "resolution_preference": "", # e.g., "1024x1024", "portrait", "landscape"
                        "style_tags": [],           # Additional style descriptors
                    },
                    "user_feedback": {
                        "quality_rating": 0,        # 1-5 stars
                        "ease_of_use": 0,          # 1-5 stars
                        "versatility": 0,          # 1-5 stars
                        "last_tested": "",         # ISO date string
                        "quick_notes": "",         # Short feedback
                    }
                }
                updated = True
            
            # Update path if it has changed (e.g., file moved)
            elif self.lora_db["loras"][lora_hash]["path"] != path:
                self.lora_db["loras"][lora_hash]["path"] = path
                updated = True
        
        # Save if database was updated
        if updated:
            self._save_lora_db()

    def _detect_architecture_from_path(self, path: str) -> str:
        """
        Detect model architecture from file path and name.
        
        Args:
            path: Path to the LoRA file
            
        Returns:
            str: Detected architecture name or "Unknown"
        """
        path_lower = path.lower()
        filename_lower = os.path.basename(path).lower()
        
        # Check directory structure for architecture indicators
        for arch, arch_data in self.known_architectures.items():
            patterns = arch_data["patterns"]
            for pattern in patterns:
                if pattern.lower() in path_lower or pattern.lower() in filename_lower:
                    return arch
        
        return "Unknown"

    def _guess_category_from_path(self, path: str) -> str:
        """
        Guess LoRA category from path structure.
        
        Args:
            path: Path to the LoRA file
            
        Returns:
            str: Guessed category
        """
        path_lower = path.lower()
        
        # Updated category patterns to match UI categories
        category_patterns = {
            "style": ["style", "artistic", "art_style", "photostyle"],
            "character": ["character", "people", "person", "char"],
            "concept": ["concept", "conceptart"],
            "pose": ["pose", "body", "poses", "position"],
            "clothing": ["clothing", "clothes", "dress", "outfit", "fashion"],
            "background": ["background", "environment", "scene", "landscape"],
            "effect": ["effect", "treatment", "filter", "fx"],
            "graphic": ["graphic", "graphicdesign", "design"],
            "tool": ["tool", "helper", "enhancer", "utility"],
            "slider": ["slider", "sliders"],
            # New categories
            "anime": ["anime", "manga", "waifu", "animestyle"],
            "realism": ["realism", "realistic", "photorealistic", "real"],
            "details": ["details", "detail", "enhance", "enhancement", "quality"],
            "lighting": ["lighting", "light", "illuminate", "glow", "shadow"],
            "mood": ["mood", "atmosphere", "emotion", "feeling"],
            "texture": ["texture", "material", "surface", "fabric"],
            "fantasy": ["fantasy", "magic", "magical", "fairy", "dragon"],
            "scifi": ["scifi", "sci-fi", "science", "future", "cyber", "robot"],
            "historical": ["historical", "history", "vintage", "retro", "medieval"],
            "nsfw": ["nsfw", "nude", "adult", "sexy", "erotic"],
            "enhancement": ["enhancement", "upscale", "improve", "quality", "hd"]
        }
        
        for category, patterns in category_patterns.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return category
        
        return "unknown"

    def filter_loras(self, dir_search_terms: str, file_search_terms: str, 
                    architecture: str, category: str, trigger_search: str):
        """
        Apply filters to LoRA models with support for negated search terms.
        
        Args:
            dir_search_terms: Comma-separated terms to match in directory paths. Use -term to exclude.
            file_search_terms: Comma-separated terms to match in filenames. Use -term to exclude.
            architecture: Architecture to filter by, or "Any" for all
            category: Category to filter by, or "Any" for all
            trigger_search: Terms to search for in trigger words. Use -term to exclude.
            
        Returns:
            List[str]: Filtered list of LoRA paths
        """
        
        # Helper function to parse terms with negation
        def parse_search_terms(term_string: str) -> Tuple[List[str], List[str]]:
            """Parse search terms into include and exclude lists."""
            include_terms = []
            exclude_terms = []
            
            if not term_string.strip():
                return include_terms, exclude_terms
            
            for term in term_string.split(','):
                term = term.strip()
                if not term:
                    continue
                if term.startswith('-'):
                    # Exclude term (remove the minus sign)
                    exclude_terms.append(term[1:].lower())
                else:
                    # Include term
                    include_terms.append(term.lower())
            
            return include_terms, exclude_terms
        
        # Parse all search term types
        dir_include, dir_exclude = parse_search_terms(dir_search_terms)
        file_include, file_exclude = parse_search_terms(file_search_terms)
        trigger_include, trigger_exclude = parse_search_terms(trigger_search)
        
        # Debug output
        if file_include or file_exclude:
            print(f"[LoRATester] File search - Include: {file_include}, Exclude: {file_exclude}")
        if trigger_include or trigger_exclude:
            print(f"[LoRATester] Trigger search - Include: {trigger_include}, Exclude: {trigger_exclude}")
        
        # Start with all LoRAs
        filtered = self.lora_paths
        
        # Apply directory name filter
        if dir_include or dir_exclude:
            filtered_by_dir = []
            for lora_path in filtered:
                dir_path = os.path.dirname(lora_path).lower()
                # Check includes
                if dir_include and not any(term in dir_path for term in dir_include):
                    continue
                # Check excludes
                if dir_exclude and any(term in dir_path for term in dir_exclude):
                    continue
                filtered_by_dir.append(lora_path)
            filtered = filtered_by_dir
        
        # Apply filename filter
        if file_include or file_exclude:
            filtered_by_file = []
            for lora_path in filtered:
                filename = os.path.basename(lora_path).lower()
                # Check includes
                if file_include and not any(term in filename for term in file_include):
                    continue
                # Check excludes
                if file_exclude and any(term in filename for term in file_exclude):
                    continue
                filtered_by_file.append(lora_path)
            filtered = filtered_by_file
        
        # Apply architecture filter
        if architecture != "Any":
            arch_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db["loras"]:
                    lora_arch = self.lora_db["loras"][lora_hash]["architecture"]
                    if lora_arch == architecture:
                        arch_filtered.append(lora_path)
            filtered = arch_filtered
        
        # Apply category filter
        if category != "Any":
            category_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db["loras"]:
                    lora_category = self.lora_db["loras"][lora_hash].get("category", "unknown")
                    if lora_category.lower() == category.lower():
                        category_filtered.append(lora_path)
            filtered = category_filtered
        
        # Apply trigger word search with includes/excludes
        if trigger_include or trigger_exclude:
            trigger_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db["loras"]:
                    trigger_words = self.lora_db["loras"][lora_hash].get("trigger_words", {}).get("full_list", [])
                    trigger_text = " ".join(trigger_words).lower()
                    
                    # Check includes
                    if trigger_include and not any(term in trigger_text for term in trigger_include):
                        continue
                    # Check excludes
                    if trigger_exclude and any(term in trigger_text for term in trigger_exclude):
                        continue
                    
                    trigger_filtered.append(lora_path)
            filtered = trigger_filtered
        
        self.filtered_loras = filtered
        return filtered
        

    def get_lora_list(self) -> str:
        """
        Create a formatted list of LoRAs.
        
        Returns:
            str: Formatted text list of LoRAs with index numbers
        """
        if not self.filtered_loras:
            return "No LoRAs match the current filters."
        
        result = "Available LoRAs:\n"
        for idx, lora_path in enumerate(self.filtered_loras):
            lora_name = os.path.basename(lora_path)
            
            # Try to add metadata from database
            lora_hash = self._calculate_lora_hash(lora_path)
            if lora_hash in self.lora_db["loras"]:
                lora_data = self.lora_db["loras"][lora_hash]
                arch = lora_data["architecture"]
                category = lora_data["category"]
                
                if arch != "Unknown":
                    result += f"{idx+1}. {lora_name} [{arch}] ({category})\n"
                else:
                    result += f"{idx+1}. {lora_name} ({category})\n"
            else:
                result += f"{idx+1}. {lora_name}\n"
        
        return result

    def _combine_prompt_with_triggers(self, input_prompt: str, trigger_words: str, 
                                    placement: str, lora_data: Dict = None) -> str:
        """
        Combine input prompt with trigger words based on placement preference.
        
        Args:
            input_prompt: The original prompt text
            trigger_words: The trigger words to add
            placement: "auto", "beginning", "end", or "none"
            lora_data: LoRA database entry for auto placement detection
            
        Returns:
            str: Combined prompt text
        """
        if not trigger_words.strip() or placement == "none":
            return input_prompt
        
        # Determine actual placement
        actual_placement = "end"  # Default fallback
        
        if placement == "auto" and lora_data:
            # Use database setting if available
            actual_placement = lora_data.get("trigger_words", {}).get("placement", "end")
        elif placement in ["beginning", "end"]:
            actual_placement = placement
        
        # Clean up inputs
        prompt = input_prompt.strip()
        triggers = trigger_words.strip()
        
        if not triggers:
            return prompt
        
        # Combine based on placement
        if actual_placement == "beginning":
            if prompt:
                # Add triggers at beginning with proper spacing
                combined = f"{triggers}, {prompt}"
            else:
                combined = triggers
        else:  # "end"
            if prompt:
                # Add triggers at end with proper spacing
                # Check if prompt already ends with punctuation
                if prompt.endswith(('.', ',', '!', '?', ';', ':')):
                    combined = f"{prompt} {triggers}"
                else:
                    combined = f"{prompt}, {triggers}"
            else:
                combined = triggers
        
        return combined

    def _guess_trigger_placement(self, trigger_words: List[str]) -> str:
        """
        Guess optimal placement for trigger words based on content analysis.
        
        Args:
            trigger_words: List of trigger words
            
        Returns:
            str: "beginning" or "end"
        """
        if not trigger_words:
            return "end"
        
        # Analyze trigger words for placement hints
        beginning_indicators = [
            "style", "in the style of", "artwork", "painting", "illustration",
            "photograph", "photo", "drawing", "sketch", "render", "art by",
            "by ", "portrait", "landscape", "close-up", "wide shot"
        ]
        
        end_indicators = [
            "detailed", "high quality", "masterpiece", "best quality",
            "highly detailed", "sharp focus", "professional", "award winning",
            "trending", "popular", "viral", "featured"
        ]
        
        # Combine all trigger words into a single string for analysis
        trigger_text = " ".join(trigger_words).lower()
        
        beginning_score = sum(1 for indicator in beginning_indicators if indicator in trigger_text)
        end_score = sum(1 for indicator in end_indicators if indicator in trigger_text)
        
        # Check for specific style patterns
        style_patterns = ["style of", "in the style", "art style", "artistic style"]
        if any(pattern in trigger_text for pattern in style_patterns):
            beginning_score += 2
        
        # Default to end if scores are equal
        return "beginning" if beginning_score > end_score else "end"

    def _find_associated_images(self, lora_path: str) -> List[str]:
        """
        Find images associated with a LoRA file.
        
        Looks for files with same base name and image extensions.
        
        Args:
            lora_path: Path to the LoRA file
            
        Returns:
            List[str]: Paths to found image files
        """
        base_path = os.path.splitext(lora_path)[0]
        base_filename = os.path.basename(base_path)
        directory = os.path.dirname(lora_path)
        
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        associated_images = []
        
        # Check for exact match
        for ext in image_extensions:
            img_path = base_path + ext
            if os.path.exists(img_path):
                associated_images.append(img_path)
        
        # Check for numbered variants (e.g., lora-1.png, lora_1.jpg)
        for i in range(1, 10):  # Check variants 1-9
            for separator in ['-', '_']:
                for ext in image_extensions:
                    img_path = f"{base_path}{separator}{i}{ext}"
                    if os.path.exists(img_path):
                        associated_images.append(img_path)
        
        return associated_images

    def _load_images_as_batch(self, image_paths: List[str]) -> Optional[torch.Tensor]:
        """
        Load multiple images and combine them into a batch tensor.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            torch.Tensor: Batch tensor or None if no images
        """
        if not image_paths:
            return None
        
        images = []
        max_width = 0
        max_height = 0
        
        # First pass: load images and find max dimensions
        for img_path in image_paths:
            try:
                img = Image.open(img_path).convert('RGB')
                images.append(img)
                max_width = max(max_width, img.width)
                max_height = max(max_height, img.height)
            except Exception as e:
                print(f"[LoRATester] Error loading image {img_path}: {e}")
        
        if not images:
            return None
        
        # Second pass: resize images to max dimensions
        image_arrays = []
        for img in images:
            # Pad image to max dimensions with dark gray background
            img = ImageOps.pad(img, (max_width, max_height), color=(21, 21, 21))
            # Convert to numpy array and normalize to [0,1]
            img_array = np.array(img).astype(np.float32) / 255.0
            image_arrays.append(img_array)
        
        # Stack into batch tensor and convert to PyTorch tensor
        batch_tensor = np.stack(image_arrays, axis=0)
        return torch.from_numpy(batch_tensor)
        

    def load_lora(self, lora_path: str, model, clip, model_strength: float, clip_strength: float):
        """
        Load and apply a LoRA to the model and CLIP.
        
        Args:
            lora_path: Path to the LoRA file
            model: Input model
            clip: Input CLIP
            model_strength: Strength for model application
            clip_strength: Strength for CLIP application
        
        Returns:
            Tuple: (modified_model, modified_clip)
        """
        try:
            print(f"[LoRATester] Loading LoRA: {lora_path}")

            lora = load_torch_file(lora_path, safe_load=True)
            model_lora, clip_lora = model, clip

            # Only apply if not None
            if model is not None or clip is not None:
                model_lora, clip_lora = load_lora_for_models(model, clip, lora, model_strength, clip_strength)

            return model_lora, clip_lora

        except Exception as e:
            print(f"[LoRATester] Error loading LoRA {lora_path}: {e}")
            return model, clip

    def get_lora_info(self, lora_path: str, query_civitai: bool = False, 
                     force_fetch: bool = False, primary_override: str = "") -> Tuple[str, str, float, float]:
        """
        Get information about a LoRA from the database, optionally querying Civitai.
        
        Args:
            lora_path: Path to the LoRA file
            query_civitai: Whether to query Civitai for missing trigger words
            force_fetch: Force fetch from Civitai even if tags exist
            primary_override: Override for primary trigger word selection
            
        Returns:
            Tuple: (trigger_words_all, trigger_words_selected, model_strength, clip_strength)
        """
        lora_hash = self._calculate_lora_hash(lora_path)
        
        trigger_words_all = ""
        trigger_words_selected = ""
        model_strength = 0.8
        clip_strength = 1.0
        
        if lora_hash in self.lora_db["loras"]:
            lora_data = self.lora_db["loras"][lora_hash]
            
            # Get existing trigger words
            full_list = lora_data.get("trigger_words", {}).get("full_list", [])
            selected_list = lora_data.get("trigger_words", {}).get("selected", [])
            
            # Query Civitai if enabled and no tags exist, or if force fetch is enabled
            if query_civitai and (not full_list or force_fetch):
                civitai_tags = self._fetch_civitai_tags(lora_path, force_fetch)
                if civitai_tags:
                    full_list = civitai_tags
                    # If we got new tags and no selection exists, use first tag as selected
                    if not selected_list and civitai_tags:
                        selected_list = [civitai_tags[0]]
                        lora_data["trigger_words"]["selected"] = selected_list
                        self._save_lora_db()
            
            trigger_words_all = ", ".join(full_list) if full_list else ""
            
            # Handle primary trigger selection
            if primary_override.strip():
                # Use override if provided
                trigger_words_selected = primary_override.strip()
            elif selected_list:
                # Use selected from database
                trigger_words_selected = ", ".join(selected_list)
            elif full_list:
                # Fall back to first available trigger word
                trigger_words_selected = full_list[0]
            else:
                trigger_words_selected = ""
            
            # Get strengths
            strengths = lora_data.get("strengths", {})
            model_strength = strengths.get("model_default", 0.8)
            clip_strength = strengths.get("clip_default", 1.0)
            
            # Check for architecture-specific strengths
            architecture = lora_data.get("architecture", "Unknown")
            arch_specific = strengths.get("architecture_specific", {})
            if architecture in arch_specific:
                model_strength = arch_specific[architecture].get("model", model_strength)
                clip_strength = arch_specific[architecture].get("clip", clip_strength)
        
        return trigger_words_all, trigger_words_selected, model_strength, clip_strength

    def process_loras(self, dir_search_terms: str, file_search_terms: str, 
                    architecture: str, category: str, trigger_search: str,
                    seed: int, mode: str, model_strength: float, clip_strength: float,
                    use_database_defaults: bool, query_civitai: bool, force_civitai_fetch: bool,
                    prompt_placement: str, max_gallery_images: int, gallery_image_size: int,
                    additional_path: str = "", model=None, clip=None, 
                    input_prompt: str = "", primary_trigger_override: str = ""):
        
        """
        Main node processing function with Civitai integration, prompt combination, and gallery generation.
        """
        print(f"[LoRATester] Running with seed: {seed}, mode: {mode}, query_civitai: {query_civitai}")
        
        # Rescan LoRAs if additional path is provided
        if additional_path:
            self.scan_loras(additional_path)
        
        # Apply filters
        self.filter_loras(dir_search_terms, file_search_terms, architecture, 
                        category, trigger_search)
        
        # Generate list of LoRAs
        lora_list = self.get_lora_list()
        
        # Get count statistics
        total_loras = len(self.lora_paths)
        selected_loras = len(self.filtered_loras)
        
        combined_prompt = input_prompt  # Initialize with input prompt

        # Create gallery from all filtered LoRAs
        gallery_images = self._create_lora_gallery(max_gallery_images, gallery_image_size)

        # Default outputs
        output_model = model
        output_clip = clip
        lora_name = ""
        lora_path = ""
        trigger_words_all = ""
        trigger_words_selected = ""
        associated_images = None
        model_strength_used = model_strength
        clip_strength_used = clip_strength
        
        if self.filtered_loras:
            max_attempts = min(len(self.filtered_loras), 5)
            attempts = 0
            
            # Determine control mode (existing logic remains the same)
            if hasattr(self, 'last_seed') and self.last_seed is not None:
                if seed == self.last_seed:
                    control_mode = "fixed"
                    print(f"[LoRATester] Detected fixed mode (seed unchanged)")
                elif seed == (self.last_seed + 1) % 0xffffffffffffffff:
                    control_mode = "increment"
                    print(f"[LoRATester] Detected increment mode (seed incremented)")
                elif seed == (self.last_seed - 1) % 0xffffffffffffffff:
                    control_mode = "decrement"
                    print(f"[LoRATester] Detected decrement mode (seed decremented)")
                else:
                    control_mode = "random"
                    print(f"[LoRATester] Detected random mode (seed changed randomly)")
            else:
                if seed == 1:
                    control_mode = "increment"
                    print(f"[LoRATester] First run, using increment mode (seed = 1)")
                else:
                    control_mode = "fixed"
                    print(f"[LoRATester] First run, using fixed mode (seed = {seed})")
            
            while attempts < max_attempts:
                try:
                    if control_mode == "random" or seed == 0:
                        selected_lora_path = random.choice(self.filtered_loras)
                        print(f"[LoRATester] Random mode: selected LoRA {os.path.basename(selected_lora_path)}")
                    elif control_mode == "fixed":
                        list_index = seed - 1  # Convert from 1-based to 0-based indexing
                        list_index = max(0, min(len(self.filtered_loras)-1, list_index))
                        selected_lora_path = self.filtered_loras[list_index]
                    elif control_mode == "increment":
                        list_index = seed % len(self.filtered_loras)
                        selected_lora_path = self.filtered_loras[list_index]
                    else:  # decrement
                        list_index = (len(self.filtered_loras) - (seed % len(self.filtered_loras))) % len(self.filtered_loras)
                        selected_lora_path = self.filtered_loras[list_index]
                    
                    # Get LoRA information with Civitai integration
                    lora_name = os.path.basename(selected_lora_path)
                    lora_path = selected_lora_path
                    
                    # Get trigger words and default strengths with Civitai support
                    trigger_words_all, trigger_words_selected, default_model_strength, default_clip_strength = self.get_lora_info(
                        selected_lora_path, query_civitai, force_civitai_fetch, primary_trigger_override
                    )
                    
                    # Get LoRA data for placement information
                    lora_hash = self._calculate_lora_hash(selected_lora_path)
                    lora_data = self.lora_db["loras"].get(lora_hash, {})
                    
                    # Combine prompt with trigger words
                    combined_prompt = self._combine_prompt_with_triggers(
                        input_prompt, trigger_words_selected, prompt_placement, lora_data
                    )
                    
                    # Auto-guess placement if not set in database and we have new triggers
                    if (prompt_placement == "auto" and lora_data and 
                        not lora_data.get("trigger_words", {}).get("placement")):
                        
                        full_triggers = lora_data.get("trigger_words", {}).get("full_list", [])
                        if full_triggers:
                            guessed_placement = self._guess_trigger_placement(full_triggers)
                            lora_data["trigger_words"]["placement"] = guessed_placement
                            self._save_lora_db()
                            print(f"[LoRATester] Auto-guessed trigger placement: {guessed_placement}")
                    
                    
                    # Use database defaults if requested
                    if use_database_defaults:
                        final_model_strength = default_model_strength
                        final_clip_strength = default_clip_strength
                    else:
                        final_model_strength = model_strength
                        final_clip_strength = clip_strength
                    
                    # Track strengths used for output
                    model_strength_used = final_model_strength
                    clip_strength_used = final_clip_strength
                    
                    # Find associated images for the selected LoRA (keep existing functionality)
                    image_paths = self._find_associated_images(selected_lora_path)
                    if image_paths:
                        associated_images = self._load_images_as_batch(image_paths)
                        print(f"[LoRATester] Found {len(image_paths)} associated images")
                    
                    # Apply LoRA if in direct load mode
                    if mode == "direct_load":
                        if model is None:
                            print(f"[LoRATester] Warning: Model is required for direct_load mode")
                        else:
                            output_model, output_clip = self.load_lora(
                                selected_lora_path, model, clip, 
                                final_model_strength, final_clip_strength
                            )
                    
                    break  # Success, exit attempt loop
                    
                except Exception as e:
                    print(f"[LoRATester] Error processing LoRA: {e}")
                    attempts += 1
                    print(f"[LoRATester] Attempt {attempts}/{max_attempts} failed, trying next LoRA")
                    
                    # Clean up memory after failed attempt
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                    gc.collect()
        
        # Save current seed
        self.last_seed = seed
        
        # Create default empty image if no images found for selected LoRA
        if associated_images is None:
            # Create a 512x512 dark gray image as placeholder
            placeholder = torch.full((1, 512, 512, 3), 21/255.0, dtype=torch.float32)
            associated_images = placeholder
        
        return (
            output_model, output_clip, lora_name, lora_path, 
            trigger_words_all, trigger_words_selected, combined_prompt, lora_list, 
            total_loras, selected_loras, associated_images,
            model_strength_used, clip_strength_used, gallery_images
        )



class LoRAInfoSetterNode:
    """
    Companion node for LoRATesterNode that allows setting LoRA information
    such as architecture, category, trigger words, and default strengths.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the node."""
        return {
            "required": {
                "lora_path": ("STRING", {"default": "", "multiline": False, 
                            "tooltip": "Path to the LoRA file"}),
                "architecture": (["SD1.5", "SD2.1", "SDXL", "Pony", "Illustrious", 
                                "Noobai", "SD3.5 Medium", "SD3.5 Large", "Flux", "HiDream", 
                                "Stable Cascade", "PixArt Sigma", "Playground"], 
                                {"default": "SD1.5", "tooltip": "Model architecture"}),
                "category": (["unknown", "style", "character", "concept", "pose", 
                            "clothing", "background", "effect", "artistic", "photographic", 
                            "graphic", "treatment", "tool", "slider"],
                            {"default": "unknown", "tooltip": "LoRA category"}),
                "notes": ("STRING", {"default": "", "multiline": True, 
                        "tooltip": "Additional notes about this LoRA"}),
                "trigger_words_full": ("STRING", {"default": "", "multiline": True,
                        "tooltip": "All trigger words for this LoRA (comma-separated)"}),
                "trigger_words_selected": ("STRING", {"default": "", "multiline": True,
                        "tooltip": "Selected trigger words to use (comma-separated)"}),
                "model_strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Default model strength"}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Default CLIP strength"}),
                "trigger_placement": (["beginning", "end"], {
                    "default": "end",
                    "tooltip": "Where trigger words work best in prompts"
            }),
            },
            "optional": {
                "compatible_checkpoints": ("STRING", {"default": "", "multiline": True,
                        "tooltip": "Compatible checkpoint paths (one per line)"}),
                "compatible_loras": ("STRING", {"default": "", "multiline": True,
                        "tooltip": "Compatible LoRA paths (one per line)"}),
                "placement_notes": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "Notes about optimal trigger word placement"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "set_lora_info"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the LoRA info setter node."""
        # Get reference to the database
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Warning: LoRA database is corrupted. Creating a new one.")
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        else:
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
            
    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    


    
    def set_lora_info(self, lora_path: str, architecture: str, category: str = "unknown", 
                    notes: str = "", trigger_words_full: str = "", 
                    trigger_words_selected: str = "", model_strength: float = 0.8, 
                    clip_strength: float = 1.0, trigger_placement: str = "end",
                    compatible_checkpoints: str = "", compatible_loras: str = "",
                    placement_notes: str = "") -> Tuple[str]:
        """
        Set information for a specific LoRA including trigger placement.
        """
        # Validate the LoRA path
        if not os.path.exists(lora_path):
            return (f"Error: LoRA file not found at {lora_path}",)
        
        # Calculate LoRA hash
        lora_hash = self._calculate_lora_hash(lora_path)
        
        # Parse trigger words
        full_triggers = [t.strip() for t in trigger_words_full.split(',') if t.strip()]
        selected_triggers = [t.strip() for t in trigger_words_selected.split(',') if t.strip()]
        
        # Parse compatible lists
        compatible_checkpoints_list = [p.strip() for p in compatible_checkpoints.split('\n') if p.strip()]
        compatible_loras_list = [p.strip() for p in compatible_loras.split('\n') if p.strip()]
        
        # Get or create the LoRA entry
        if lora_hash not in self.lora_db["loras"]:
            self.lora_db["loras"][lora_hash] = {
                "path": lora_path,
                "name": os.path.basename(lora_path),
                "architecture": "Unknown",
                "category": "unknown",
                "notes": "",
                "trigger_words": {
                    "full_list": [],
                    "selected": [],
                    "imported_from": ""
                },
                "strengths": {
                    "model_default": 0.8,
                    "clip_default": 1.0,
                    "architecture_specific": {}
                },
                "compatible_checkpoints": [],
                "compatible_loras": [],
                "recommended_settings": {
                    "best_checkpoints": [],     # Names of checkpoints this works best with
                    "avoid_checkpoints": [],    # Checkpoints to avoid
                    "optimal_cfg_range": "",    # e.g., "7-12"
                    "resolution_preference": "", # e.g., "1024x1024", "portrait", "landscape"
                    "style_tags": [],           # Additional style descriptors
                },
                "user_feedback": {
                    "quality_rating": 0,        # 1-5 stars
                    "ease_of_use": 0,          # 1-5 stars
                    "versatility": 0,          # 1-5 stars
                    "last_tested": "",         # ISO date string
                    "quick_notes": "",         # Short feedback
                }
            }
        # Update LoRA information
        
        lora_data = self.lora_db["loras"][lora_hash]
        lora_data["architecture"] = architecture
        lora_data["category"] = category
        lora_data["notes"] = notes
        lora_data["trigger_words"]["full_list"] = full_triggers
        lora_data["trigger_words"]["selected"] = selected_triggers
        lora_data["strengths"]["model_default"] = model_strength
        lora_data["strengths"]["clip_default"] = clip_strength
        lora_data["compatible_checkpoints"] = compatible_checkpoints_list
        lora_data["compatible_loras"] = compatible_loras_list
        lora_data["trigger_words"]["full_list"] = full_triggers
        lora_data["trigger_words"]["selected"] = selected_triggers
        lora_data["trigger_words"]["placement"] = trigger_placement
        lora_data["trigger_words"]["placement_notes"] = placement_notes
        
        # Save the updated database
        self._save_lora_db()
        
        return (f"Successfully updated information for {os.path.basename(lora_path)}",)


class LoRABatchInfoSetterNode:
    """
    Node for batch setting information about multiple LoRAs.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the batch info setter node."""
        return {
            "required": {
                "dir_path": ("STRING", {"default": "", "multiline": False, 
                            "tooltip": "Directory containing LoRAs to update"}),
                "architecture": (["SD1.5", "SD2.1", "SDXL", "Pony", "Illustrious", 
                                "Noobai", "SD3.5 Medium", "SD3.5 Large", "Flux", "HiDream", 
                                "Stable Cascade", "PixArt Sigma", "Playground"], 
                                {"default": "SD1.5", "tooltip": "Model architecture"}),
                "category": (["unknown", "style", "character", "concept", "pose", 
                            "clothing", "background", "effect", "artistic", "photographic", 
                            "graphic", "treatment", "tool", "slider"],
                            {"default": "unknown", "tooltip": "LoRA category"}),
                "recursive": ("BOOLEAN", {"default": True,
                            "tooltip": "Scan subdirectories recursively"}),
                "file_pattern": ("STRING", {"default": "*.safetensors", "multiline": False,
                                "tooltip": "Pattern to match filenames (e.g., *.safetensors)"}),
                "model_strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Default model strength"}),
                "clip_strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Default CLIP strength"}),
                "overwrite_existing": ("BOOLEAN", {"default": False,
                        "tooltip": "Overwrite existing LoRA information"}),
            },
            "optional": {
                "notes": ("STRING", {"default": "", "multiline": True, 
                        "tooltip": "Additional notes for these LoRAs"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "batch_set_info"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the batch info setter node."""
        # Get reference to the database
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Warning: LoRA database is corrupted. Creating a new one.")
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        else:
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def batch_set_info(self, dir_path: str, architecture: str, category: str, 
                      recursive: bool, file_pattern: str, model_strength: float, 
                      clip_strength: float, overwrite_existing: bool, 
                      notes: str = "") -> Tuple[str]:
        """
        Set information for multiple LoRAs in a directory.
        """
        # Validate directory
        if not os.path.isdir(dir_path):
            return (f"Error: Directory not found at {dir_path}",)
        
        # Find matching LoRA files
        pattern = os.path.join(dir_path, "**" if recursive else "", file_pattern)
        lora_files = glob.glob(pattern, recursive=recursive)
        
        if not lora_files:
            return (f"Error: No files matching pattern '{file_pattern}' found in {dir_path}",)
        
        # Update information for each LoRA
        updated_count = 0
        skipped_count = 0
        
        for lora_path in lora_files:
            # Calculate LoRA hash
            lora_hash = self._calculate_lora_hash(lora_path)
            
            # Check if LoRA already exists and if we should skip it
            if lora_hash in self.lora_db["loras"] and not overwrite_existing:
                skipped_count += 1
                continue
            
            # Get or create the LoRA entry
            if lora_hash not in self.lora_db["loras"]:
                self.lora_db["loras"][lora_hash] = {
                    "path": lora_path,
                    "name": os.path.basename(lora_path),
                    "architecture": "Unknown",
                    "category": "unknown",
                    "notes": "",
                    "trigger_words": {
                        "full_list": [],
                        "selected": [],
                        "imported_from": ""
                    },
                    "strengths": {
                        "model_default": 0.8,
                        "clip_default": 1.0,
                        "architecture_specific": {}
                    },
                    "compatible_checkpoints": [],
                    "compatible_loras": [],
                    "recommended_settings": {
                        "best_checkpoints": [],     # Names of checkpoints this works best with
                        "avoid_checkpoints": [],    # Checkpoints to avoid
                        "optimal_cfg_range": "",    # e.g., "7-12"
                        "resolution_preference": "", # e.g., "1024x1024", "portrait", "landscape"
                        "style_tags": [],           # Additional style descriptors
                    },
                    "user_feedback": {
                        "quality_rating": 0,        # 1-5 stars
                        "ease_of_use": 0,          # 1-5 stars
                        "versatility": 0,          # 1-5 stars
                        "last_tested": "",         # ISO date string
                        "quick_notes": "",         # Short feedback
                    }
                }
            
            # Update LoRA information
            lora_data = self.lora_db["loras"][lora_hash]
            lora_data["architecture"] = architecture
            lora_data["category"] = category
            lora_data["notes"] = notes
            lora_data["strengths"]["model_default"] = model_strength
            lora_data["strengths"]["clip_default"] = clip_strength
            
            updated_count += 1
        
        # Save the updated database
        self._save_lora_db()
        
        return (f"Successfully updated {updated_count} LoRAs in {dir_path}. Skipped {skipped_count} existing LoRAs.",)


class LoRAParamsLoaderNode:
    """
    Node for loading saved LoRA parameters and trigger words.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the node."""
        return {
            "required": {
                "lora_path": ("STRING", {"default": "", "multiline": False, 
                            "tooltip": "Path to the LoRA file"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("trigger_words_all", "trigger_words_selected", "model_strength", 
                   "clip_strength", "architecture", "category")
    FUNCTION = "load_params"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the params loader node."""
        # Get reference to the database
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Warning: LoRA database is corrupted. Creating a new one.")
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        else:
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def load_params(self, lora_path: str) -> Tuple[str, str, float, float, str, str]:
        """
        Load saved parameters and information for a LoRA.
        """
        # Default values
        trigger_words_all = ""
        trigger_words_selected = ""
        model_strength = 0.8
        clip_strength = 1.0
        architecture = "Unknown"
        category = "unknown"
        
        # Check if file exists
        if not os.path.exists(lora_path):
            print(f"Warning: LoRA file not found at {lora_path}")
            return (trigger_words_all, trigger_words_selected, model_strength, 
                   clip_strength, architecture, category)
        
        # Calculate LoRA hash
        lora_hash = self._calculate_lora_hash(lora_path)
        
        # Get information from database if available
        if lora_hash in self.lora_db["loras"]:
            lora_data = self.lora_db["loras"][lora_hash]
            
            # Get trigger words
            trigger_data = lora_data.get("trigger_words", {})
            full_list = trigger_data.get("full_list", [])
            selected_list = trigger_data.get("selected", [])
            
            trigger_words_all = ", ".join(full_list) if full_list else ""
            trigger_words_selected = ", ".join(selected_list) if selected_list else trigger_words_all
            
            # Get strengths
            strengths = lora_data.get("strengths", {})
            model_strength = strengths.get("model_default", 0.8)
            clip_strength = strengths.get("clip_default", 1.0)
            
            # Get metadata
            architecture = lora_data.get("architecture", "Unknown")
            category = lora_data.get("category", "unknown")
        
        return (trigger_words_all, trigger_words_selected, model_strength, 
               clip_strength, architecture, category)


class LoRAInfoViewerNode:
    """
    Node for viewing detailed information about a LoRA.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the node."""
        return {
            "required": {
                "lora_path": ("STRING", {"default": "", "multiline": False, 
                            "tooltip": "Path to the LoRA file"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("lora_name", "architecture", "category", "trigger_words", 
                   "compatible_items", "notes", "associated_images")
    FUNCTION = "view_info"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the info viewer node."""
        # Get reference to the database
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Warning: LoRA database is corrupted. Creating a new one.")
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        else:
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}

    def _find_associated_images(self, lora_path: str) -> List[str]:
        """
        Find images associated with a LoRA file.
        
        Looks for files with same base name and image extensions.
        
        Args:
            lora_path: Path to the LoRA file
            
        Returns:
            List[str]: Paths to found image files
        """
        base_path = os.path.splitext(lora_path)[0]
        base_filename = os.path.basename(base_path)
        directory = os.path.dirname(lora_path)
        
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        associated_images = []
        
        # Check for exact match
        for ext in image_extensions:
            img_path = base_path + ext
            if os.path.exists(img_path):
                associated_images.append(img_path)
        
        # Check for numbered variants (e.g., lora-1.png, lora_1.jpg)
        for i in range(1, 10):  # Check variants 1-9
            for separator in ['-', '_']:
                for ext in image_extensions:
                    img_path = f"{base_path}{separator}{i}{ext}"
                    if os.path.exists(img_path):
                        associated_images.append(img_path)
        
        return associated_images

    def _load_images_as_batch(self, image_paths: List[str]) -> Optional[torch.Tensor]:
        """
        Load multiple images and combine them into a batch tensor.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            torch.Tensor: Batch tensor or None if no images
        """
        if not image_paths:
            return None
        
        images = []
        max_width = 0
        max_height = 0
        
        # First pass: load images and find max dimensions
        for img_path in image_paths:
            try:
                img = Image.open(img_path).convert('RGB')
                images.append(img)
                max_width = max(max_width, img.width)
                max_height = max(max_height, img.height)
            except Exception as e:
                print(f"[LoRATester] Error loading image {img_path}: {e}")
        
        if not images:
            return None
        
        # Second pass: resize images to max dimensions
        image_arrays = []
        for img in images:
            # Pad image to max dimensions with dark gray background
            img = ImageOps.pad(img, (max_width, max_height), color=(21, 21, 21))
            # Convert to numpy array and normalize to [0,1]
            img_array = np.array(img).astype(np.float32) / 255.0
            image_arrays.append(img_array)
        
        # Stack into batch tensor and convert to PyTorch tensor
        batch_tensor = np.stack(image_arrays, axis=0)
        return torch.from_numpy(batch_tensor)
        

    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8'))
            
    def view_info(self, lora_path: str) -> Tuple[str, str, str, str, str, str, torch.Tensor]:
        """
        View information about a LoRA.
        """
        # Default values
        lora_name = os.path.basename(lora_path) if lora_path else "Unknown"
        architecture = "Unknown"
        category = "unknown"
        trigger_words = "No trigger words set"
        compatible_items = "None listed"
        notes = "No notes"
        
        # Create default dark gray image
        placeholder = torch.full((1, 512, 512, 3), 21/255.0, dtype=torch.float32)
        associated_images = placeholder
        
        # Check if the LoRA path exists
        if lora_path and os.path.exists(lora_path):
            # Calculate LoRA hash
            lora_hash = self._calculate_lora_hash(lora_path)
            
            # Get information from database if available
            if lora_hash in self.lora_db["loras"]:
                lora_data = self.lora_db["loras"][lora_hash]
                
                lora_name = lora_data.get("name", lora_name)
                architecture = lora_data.get("architecture", architecture)
                category = lora_data.get("category", category)
                notes = lora_data.get("notes", notes)
                
                # Format trigger words
                trigger_data = lora_data.get("trigger_words", {})
                full_list = trigger_data.get("full_list", [])
                selected_list = trigger_data.get("selected", [])
                
                if full_list:
                    trigger_words = f"All: {', '.join(full_list)}\n"
                    if selected_list:
                        trigger_words += f"Selected: {', '.join(selected_list)}"
                    else:
                        trigger_words += "Selected: (using all)"
                
                # Format compatible items
                compatible_checkpoints = lora_data.get("compatible_checkpoints", [])
                compatible_loras = lora_data.get("compatible_loras", [])
                
                if compatible_checkpoints or compatible_loras:
                    compatible_items = "Compatible Items:\n"
                    if compatible_checkpoints:
                        compatible_items += f"Checkpoints:\n"
                        for cp in compatible_checkpoints:
                            compatible_items += f"  - {os.path.basename(cp)}\n"
                    if compatible_loras:
                        compatible_items += f"LoRAs:\n"
                        for lora in compatible_loras:
                            compatible_items += f"  - {os.path.basename(lora)}\n"
            
            # Load associated images
            image_paths = self._find_associated_images(lora_path)
            if image_paths:
                loaded_images = self._load_images_as_batch(image_paths)
                if loaded_images is not None:
                    associated_images = loaded_images
        
        return (lora_name, architecture, category, trigger_words, 
            compatible_items, notes, associated_images)

class TriggerWordManagerNode:
    """
    Node for managing trigger word selection for LoRAs with Civitai integration.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define the inputs for the node."""
        return {
            "required": {
                "lora_path": ("STRING", {"default": "", "multiline": False, 
                            "tooltip": "Path to the LoRA file"}),
                "fetch_from_civitai": ("BOOLEAN", {"default": False,
                    "tooltip": "Fetch trigger words from Civitai"}),
                "force_fetch": ("BOOLEAN", {"default": False,
                    "tooltip": "Force fetch even if tags already exist"}),
                "trigger_placement": (["auto-detect", "beginning", "end"], {"default": "auto-detect",
                    "tooltip": "Where trigger words work best in prompts"})
            },
            "optional": {
                "primary_trigger": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Select primary trigger word (leave empty to auto-select first)"}),
                "custom_triggers": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "Add custom trigger words (comma-separated)"}),
            },
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("all_triggers", "selected_trigger", "status")
    FUNCTION = "manage_triggers"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the trigger word manager node."""
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        self.civitai_cache_file = os.path.join(os.path.dirname(__file__), "civitai_cache.json")
        self.civitai_cache = self._load_civitai_cache()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _load_civitai_cache(self) -> Dict:
        """Load Civitai cache from disk."""
        if os.path.exists(self.civitai_cache_file):
            try:
                with open(self.civitai_cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _guess_trigger_placement(self, trigger_words: List[str]) -> str:
        """
        Guess optimal placement for trigger words based on content analysis.
        
        Args:
            trigger_words: List of trigger words
            
        Returns:
            str: "beginning" or "end"
        """
        if not trigger_words:
            return "end"
        
        # Analyze trigger words for placement hints
        beginning_indicators = [
            "style", "in the style of", "artwork", "painting", "illustration",
            "photograph", "photo", "drawing", "sketch", "render", "art by",
            "by ", "portrait", "landscape", "close-up", "wide shot"
        ]
        
        end_indicators = [
            "detailed", "high quality", "masterpiece", "best quality",
            "highly detailed", "sharp focus", "professional", "award winning",
            "trending", "popular", "viral", "featured"
        ]
        
        # Combine all trigger words into a single string for analysis
        trigger_text = " ".join(trigger_words).lower()
        
        beginning_score = sum(1 for indicator in beginning_indicators if indicator in trigger_text)
        end_score = sum(1 for indicator in end_indicators if indicator in trigger_text)
        
        # Check for specific style patterns
        style_patterns = ["style of", "in the style", "art style", "artistic style"]
        if any(pattern in trigger_text for pattern in style_patterns):
            beginning_score += 2
        
        # Default to end if scores are equal
        return "beginning" if beginning_score > end_score else "end"
    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash for Civitai API lookup."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[TriggerManager] Error calculating SHA256 for {file_path}: {e}")
            return ""
    
    def _get_civitai_model_info(self, sha256_hash: str) -> Optional[Dict]:
        """Query Civitai API for model information."""
        if sha256_hash in self.civitai_cache:
            return self.civitai_cache[sha256_hash]
        
        try:
            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256_hash}"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                model_info = response.json()
                self.civitai_cache[sha256_hash] = model_info
                return model_info
            else:
                self.civitai_cache[sha256_hash] = None
                return None
                
        except requests.RequestException as e:
            print(f"[TriggerManager] Error querying Civitai API: {e}")
            return None
    
    def manage_triggers(self, lora_path: str, fetch_from_civitai: bool, force_fetch: bool,
                       trigger_placement: str = "auto-detect", primary_trigger: str = "", 
                       custom_triggers: str = "") -> Tuple[str, str, str]:
        """
        Manage trigger words for a LoRA including placement.
        """
        if not os.path.exists(lora_path):
            return ("", "", f"Error: LoRA file not found at {lora_path}")
        
        lora_hash = self._calculate_lora_hash(lora_path)
        status_messages = []
        
        # Initialize LoRA entry if it doesn't exist
        if lora_hash not in self.lora_db["loras"]:
            self.lora_db["loras"][lora_hash] = {
                "path": lora_path,
                "name": os.path.basename(lora_path),
                "architecture": "Unknown",
                "category": "unknown",
                "notes": "",
                "trigger_words": {
                    "full_list": [],
                    "selected": [],
                    "imported_from": ""
                },
                "strengths": {
                    "model_default": 0.8,
                    "clip_default": 1.0,
                    "architecture_specific": {}
                },
                "compatible_checkpoints": [],
                "compatible_loras": [],
                "recommended_settings": {
                    "best_checkpoints": [],     # Names of checkpoints this works best with
                    "avoid_checkpoints": [],    # Checkpoints to avoid
                    "optimal_cfg_range": "",    # e.g., "7-12"
                    "resolution_preference": "", # e.g., "1024x1024", "portrait", "landscape"
                    "style_tags": [],           # Additional style descriptors
                },
                "user_feedback": {
                    "quality_rating": 0,        # 1-5 stars
                    "ease_of_use": 0,          # 1-5 stars
                    "versatility": 0,          # 1-5 stars
                    "last_tested": "",         # ISO date string
                    "quick_notes": "",         # Short feedback
                }
            }
        
        lora_data = self.lora_db["loras"][lora_hash]
        current_triggers = lora_data["trigger_words"]["full_list"]
        
        # Fetch from Civitai if requested
        if fetch_from_civitai and (not current_triggers or force_fetch):
            sha256_hash = self._calculate_sha256(lora_path)
            if sha256_hash:
                model_info = self._get_civitai_model_info(sha256_hash)
                if model_info and "trainedWords" in model_info:
                    civitai_triggers = model_info["trainedWords"]
                    lora_data["trigger_words"]["full_list"] = civitai_triggers
                    lora_data["trigger_words"]["imported_from"] = "civitai"
                    status_messages.append(f"Fetched {len(civitai_triggers)} triggers from Civitai")
                    current_triggers = civitai_triggers
                else:
                    status_messages.append("No triggers found on Civitai")
                    lora_data["trigger_words"]["imported_from"] = "civitai_not_found"
            else:
                status_messages.append("Error calculating hash for Civitai lookup")
        
        # Add custom triggers
        if custom_triggers.strip():
            custom_list = [t.strip() for t in custom_triggers.split(',') if t.strip()]
            # Merge with existing triggers, avoiding duplicates
            all_triggers = list(current_triggers)
            for trigger in custom_list:
                if trigger not in all_triggers:
                    all_triggers.append(trigger)
            lora_data["trigger_words"]["full_list"] = all_triggers
            status_messages.append(f"Added {len(custom_list)} custom triggers")
            current_triggers = all_triggers
        
        # Handle primary trigger selection
        if primary_trigger.strip():
            if primary_trigger in current_triggers:
                lora_data["trigger_words"]["selected"] = [primary_trigger]
                status_messages.append(f"Set primary trigger to: {primary_trigger}")
            else:
                status_messages.append(f"Warning: '{primary_trigger}' not found in trigger list")
        elif current_triggers and not lora_data["trigger_words"]["selected"]:
            # Auto-select first trigger if none selected
            lora_data["trigger_words"]["selected"] = [current_triggers[0]]
            status_messages.append(f"Auto-selected first trigger: {current_triggers[0]}")
        
        # Handle placement setting
        if trigger_placement == "auto-detect" and current_triggers:
            # Use the guess function to determine placement
            guessed_placement = self._guess_trigger_placement(current_triggers)
            lora_data["trigger_words"]["placement"] = guessed_placement
            status_messages.append(f"Auto-detected placement: {guessed_placement}")
        elif trigger_placement in ["beginning", "end"]:
            lora_data["trigger_words"]["placement"] = trigger_placement
            status_messages.append(f"Set placement to: {trigger_placement}")

        # Save database
        self._save_lora_db()
        
        # Prepare outputs
        all_triggers_str = ", ".join(current_triggers) if current_triggers else ""
        selected_triggers = lora_data["trigger_words"]["selected"]
        selected_trigger_str = ", ".join(selected_triggers) if selected_triggers else ""
        status_str = "; ".join(status_messages) if status_messages else "No changes made"
        
        return (all_triggers_str, selected_trigger_str, status_str)

class LoRAQuickFeedbackNode:
    """
    Node for quickly adding feedback and notes to LoRAs during testing.
    Shows existing feedback to prevent duplicate ratings.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_path": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Path to the LoRA file (can be piped from LoRA Tester)"}),
                "show_current_feedback": ("BOOLEAN", {"default": True,
                    "tooltip": "Display current feedback before updating"}),
                "quality_rating": (["Keep Current", "Not Rated", "1 Star", "2 Stars", "3 Stars", "4 Stars", "5 Stars"],
                    {"default": "Keep Current", "tooltip": "Quality rating (Keep Current = no change)"}),
                "ease_of_use": (["Keep Current", "Not Rated", "1 Star", "2 Stars", "3 Stars", "4 Stars", "5 Stars"],
                    {"default": "Keep Current", "tooltip": "Ease of use rating"}),
                "versatility": (["Keep Current", "Not Rated", "1 Star", "2 Stars", "3 Stars", "4 Stars", "5 Stars"],
                    {"default": "Keep Current", "tooltip": "Versatility rating"}),
                "update_mode": (["Add to Notes", "Replace Notes", "Keep Current Notes"],
                    {"default": "Add to Notes", "tooltip": "How to handle existing notes"}),
                "tested_with_checkpoint": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Name of checkpoint used for testing"}),
            },
            "optional": {
                "new_notes": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "New notes to add or replace"}),
                "style_tags": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Style tags (comma-separated)"}),
                "cfg_range": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Optimal CFG range (e.g., '7-12')"}),
                "resolution_pref": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Resolution preference (e.g., '1024x1024', 'portrait')"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("lora_path", "current_feedback", "feedback_status", "summary")
    FUNCTION = "manage_feedback"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        """Initialize the feedback node."""
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def _rating_to_stars(self, rating: int) -> str:
        """Convert numeric rating to star display."""
        if rating == 0:
            return "Not Rated"
        return "★" * rating + "☆" * (5 - rating)
    
    def _get_current_feedback(self, lora_data: Dict) -> str:
        """Format current feedback for display."""
        feedback = lora_data.get("user_feedback", {})
        settings = lora_data.get("recommended_settings", {})
        
        current_feedback = f"=== CURRENT FEEDBACK ===\n"
        current_feedback += f"Quality: {self._rating_to_stars(feedback.get('quality_rating', 0))}\n"
        current_feedback += f"Ease of Use: {self._rating_to_stars(feedback.get('ease_of_use', 0))}\n"
        current_feedback += f"Versatility: {self._rating_to_stars(feedback.get('versatility', 0))}\n"
        
        last_tested = feedback.get('last_tested', '')
        if last_tested:
            current_feedback += f"Last Tested: {last_tested}\n"
        
        current_notes = feedback.get('quick_notes', '')
        if current_notes:
            current_feedback += f"Notes: {current_notes}\n"
        
        # Show settings
        cfg_range = settings.get('optimal_cfg_range', '')
        if cfg_range:
            current_feedback += f"CFG Range: {cfg_range}\n"
        
        resolution = settings.get('resolution_preference', '')
        if resolution:
            current_feedback += f"Resolution: {resolution}\n"
        
        best_checkpoints = settings.get('best_checkpoints', [])
        if best_checkpoints:
            current_feedback += f"Best Checkpoints: {', '.join(best_checkpoints[:3])}\n"
        
        style_tags = settings.get('style_tags', [])
        if style_tags:
            current_feedback += f"Style Tags: {', '.join(style_tags)}\n"
        
        return current_feedback
    
    def manage_feedback(self, lora_path: str, show_current_feedback: bool, quality_rating: str,
                       ease_of_use: str, versatility: str, update_mode: str, 
                       tested_with_checkpoint: str, new_notes: str = "", style_tags: str = "",
                       cfg_range: str = "", resolution_pref: str = "") -> Tuple[str, str, str, str]:
        """Manage feedback for a LoRA with current state awareness."""
        
        if not os.path.exists(lora_path):
            return (lora_path, "", f"Error: LoRA not found", "")
        
        lora_hash = self._calculate_lora_hash(lora_path)
        lora_name = os.path.basename(lora_path)
        
        # Initialize LoRA entry if it doesn't exist
        if lora_hash not in self.lora_db["loras"]:
            self.lora_db["loras"][lora_hash] = {
                "path": lora_path,
                "name": lora_name,
                "architecture": "Unknown",
                "category": "unknown", 
                "notes": "",
                "trigger_words": {"full_list": [], "selected": [], "imported_from": ""},
                "strengths": {"model_default": 0.8, "clip_default": 1.0, "architecture_specific": {}},
                "compatible_checkpoints": [],
                "compatible_loras": [],
                "recommended_settings": {
                    "best_checkpoints": [],
                    "avoid_checkpoints": [],
                    "optimal_cfg_range": "",
                    "resolution_preference": "",
                    "style_tags": [],
                },
                "user_feedback": {
                    "quality_rating": 0,
                    "ease_of_use": 0,
                    "versatility": 0,
                    "last_tested": "",
                    "quick_notes": "",
                }
            }
        
        lora_data = self.lora_db["loras"][lora_hash]
        
        # Get current feedback for display
        current_feedback_display = ""
        if show_current_feedback:
            current_feedback_display = self._get_current_feedback(lora_data)
        
        # Process updates
        updates = []
        rating_map = {"Keep Current": -1, "Not Rated": 0, "1 Star": 1, "2 Stars": 2, 
                     "3 Stars": 3, "4 Stars": 4, "5 Stars": 5}
        
        # Update ratings
        if quality_rating != "Keep Current":
            new_rating = rating_map[quality_rating]
            old_rating = lora_data["user_feedback"]["quality_rating"]
            lora_data["user_feedback"]["quality_rating"] = new_rating
            updates.append(f"Quality: {self._rating_to_stars(old_rating)} → {self._rating_to_stars(new_rating)}")
        
        if ease_of_use != "Keep Current":
            new_rating = rating_map[ease_of_use]
            old_rating = lora_data["user_feedback"]["ease_of_use"]
            lora_data["user_feedback"]["ease_of_use"] = new_rating
            updates.append(f"Ease of Use: {self._rating_to_stars(old_rating)} → {self._rating_to_stars(new_rating)}")
        
        if versatility != "Keep Current":
            new_rating = rating_map[versatility]
            old_rating = lora_data["user_feedback"]["versatility"]
            lora_data["user_feedback"]["versatility"] = new_rating
            updates.append(f"Versatility: {self._rating_to_stars(old_rating)} → {self._rating_to_stars(new_rating)}")
        
        # Update notes
        if new_notes.strip() and update_mode != "Keep Current Notes":
            current_notes = lora_data["user_feedback"]["quick_notes"]
            if update_mode == "Add to Notes":
                if current_notes:
                    # Add timestamp and new notes
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    lora_data["user_feedback"]["quick_notes"] = f"{current_notes}\n[{timestamp}] {new_notes.strip()}"
                else:
                    lora_data["user_feedback"]["quick_notes"] = new_notes.strip()
                updates.append("Added to notes")
            elif update_mode == "Replace Notes":
                lora_data["user_feedback"]["quick_notes"] = new_notes.strip()
                updates.append("Replaced notes")
        
        # Update settings
        if cfg_range.strip():
            lora_data["recommended_settings"]["optimal_cfg_range"] = cfg_range.strip()
            updates.append(f"CFG range: {cfg_range.strip()}")
        
        if resolution_pref.strip():
            lora_data["recommended_settings"]["resolution_preference"] = resolution_pref.strip()
            updates.append(f"Resolution: {resolution_pref.strip()}")
        
        if style_tags.strip():
            tags_list = [t.strip() for t in style_tags.split(',') if t.strip()]
            lora_data["recommended_settings"]["style_tags"] = tags_list
            updates.append(f"Style tags: {', '.join(tags_list)}")
        
        # Update checkpoint info
        if tested_with_checkpoint.strip():
            best_checkpoints = lora_data["recommended_settings"]["best_checkpoints"]
            checkpoint_name = os.path.basename(tested_with_checkpoint.strip())
            if checkpoint_name not in best_checkpoints:
                best_checkpoints.append(checkpoint_name)
                updates.append(f"Added checkpoint: {checkpoint_name}")
        
        # Update last tested date
        if updates:  # Only update if something actually changed
            from datetime import datetime
            lora_data["user_feedback"]["last_tested"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Save database
            self._save_lora_db()
        
        # Create status and summary
        if updates:
            status = f"Updated {lora_name}: " + "; ".join(updates)
            summary = f"✓ {len(updates)} changes made"
        else:
            status = f"No changes made to {lora_name}"
            summary = "No updates"
        
        # Create quick summary for display
        feedback = lora_data["user_feedback"]
        quick_summary = f"{lora_name} - Q:{self._rating_to_stars(feedback['quality_rating'])} "
        quick_summary += f"E:{self._rating_to_stars(feedback['ease_of_use'])} "
        quick_summary += f"V:{self._rating_to_stars(feedback['versatility'])}"
        
        return (lora_path, current_feedback_display, status, quick_summary)

class LoRAGalleryDisplayNode:
    """Interactive gallery node for LoRA selection with JavaScript enhancement"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_list": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "LoRA list from LoRA Tester node"}),
                "selected_index": ("INT", {"default": 1, "min": 1, "max": 999,
                    "tooltip": "Currently selected LoRA index (1-based)"}),
                "refresh_gallery": ("BOOLEAN", {"default": False,
                    "tooltip": "Force refresh the gallery display"}),
                "gallery_size": (["small", "medium", "large"], {"default": "medium",
                    "tooltip": "Size of gallery cards"}),
                "show_architecture": ("BOOLEAN", {"default": True,
                    "tooltip": "Show architecture badges on cards"}),
                "show_category": ("BOOLEAN", {"default": True,
                    "tooltip": "Show category badges on cards"}),
            },
            "optional": {
                "filter_architecture": (["Any", "SD1.5", "SDXL", "Flux", "Pony", "Illustrious", 
                    "Noobai", "SD3.5 Medium", "SD3.5 Large", "HiDream", 
                    "Stable Cascade", "PixArt Sigma", "Playground"], 
                    {"default": "Any", "tooltip": "Filter gallery by architecture"}),
                "filter_category": (["Any", "unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "graphic", "treatment", "tool", "slider", 
                    "anime", "realism", "details", "lighting", "mood", "texture",
                    "fantasy", "scifi", "historical", "nsfw", "enhancement"],
                    {"default": "Any", "tooltip": "Filter gallery by category"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "STRING") 
    RETURN_NAMES = ("gallery_html", "selected_index", "selected_lora_info")
    FUNCTION = "display_gallery"
    CATEGORY = "loaders/lora tester"
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force refresh when inputs change
        return str(kwargs.get('lora_list', '')) + str(kwargs.get('refresh_gallery', False))
    
    def __init__(self):
        """Initialize the gallery display node."""
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        """Load the LoRA database from disk."""
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier."""
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def _find_associated_images(self, lora_path: str) -> List[str]:
        """Find images associated with a LoRA file."""
        base_path = os.path.splitext(lora_path)[0]
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        associated_images = []
        
        # Check for exact match
        for ext in image_extensions:
            img_path = base_path + ext
            if os.path.exists(img_path):
                associated_images.append(img_path)
                break  # Just get the first one for gallery
        
        return associated_images
    
    def _parse_lora_list(self, lora_list: str) -> List[Dict]:
        """Parse the LoRA list text into structured data."""
        lora_data = []
        if not lora_list or "No LoRAs match" in lora_list:
            return lora_data
        
        lines = lora_list.split('\n')
        for line in lines[1:]:  # Skip header line
            line = line.strip()
            if not line:
                continue
            
            # Parse line format: "1. filename.safetensors [SDXL] (style)"
            import re
            match = re.match(r'(\d+)\.\s+(.+?)(?:\s+\[([^\]]+)\])?\s*(?:\(([^)]+)\))?', line)
            if match:
                index, filename, architecture, category = match.groups()
                
                # Try to find full path
                lora_path = self._find_lora_path(filename)
                
                lora_info = {
                    'index': int(index),
                    'name': filename,
                    'path': lora_path,
                    'architecture': architecture or "Unknown",
                    'category': category or "unknown",
                    'image_path': None
                }
                
                # Get additional info from database if available
                if lora_path:
                    lora_hash = self._calculate_lora_hash(lora_path)
                    if lora_hash in self.lora_db["loras"]:
                        db_data = self.lora_db["loras"][lora_hash]
                        lora_info['architecture'] = db_data.get('architecture', lora_info['architecture'])
                        lora_info['category'] = db_data.get('category', lora_info['category'])
                        
                        # Get user ratings for display
                        feedback = db_data.get('user_feedback', {})
                        lora_info['quality_rating'] = feedback.get('quality_rating', 0)
                        lora_info['ease_of_use'] = feedback.get('ease_of_use', 0)
                        lora_info['versatility'] = feedback.get('versatility', 0)
                        
                        # Get trigger words
                        triggers = db_data.get('trigger_words', {}).get('selected', [])
                        lora_info['triggers'] = triggers[:3]  # Show first 3 triggers
                    
                    # Find associated image
                    image_paths = self._find_associated_images(lora_path)
                    if image_paths:
                        lora_info['image_path'] = image_paths[0]
                
                lora_data.append(lora_info)
        
        return lora_data
    
    def _find_lora_path(self, filename: str) -> str:
        """Find the full path for a LoRA filename."""
        # This is a simplified version - in practice you'd search through your LoRA directories
        import folder_paths
        lora_dirs = folder_paths.get_folder_paths("loras")
        
        for directory in lora_dirs:
            for root, dirs, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)
        return ""
    
    def _get_card_size_styles(self, size: str) -> Dict[str, str]:
        """Get CSS styles for different card sizes."""
        size_configs = {
            "small": {
                "card_width": "140px",
                "image_height": "100px",
                "font_size": "10px",
                "padding": "6px"
            },
            "medium": {
                "card_width": "180px", 
                "image_height": "140px",
                "font_size": "11px",
                "padding": "8px"
            },
            "large": {
                "card_width": "220px",
                "image_height": "180px", 
                "font_size": "12px",
                "padding": "10px"
            }
        }
        return size_configs.get(size, size_configs["medium"])
    
    def display_gallery(self, lora_list: str, selected_index: int, refresh_gallery: bool,
                       gallery_size: str = "medium", show_architecture: bool = True, 
                       show_category: bool = True, filter_architecture: str = "Any",
                       filter_category: str = "Any") -> Tuple[str, int, str]:
        """Create an enhanced interactive gallery display with JavaScript."""
        
        # Parse the LoRA list
        lora_data = self._parse_lora_list(lora_list)
        
        if not lora_data:
            return ("<div style='padding: 20px; text-align: center; color: #888;'>No LoRAs available for gallery</div>", 
                   selected_index, "No LoRAs available")
        
        # Apply filters
        filtered_data = lora_data
        if filter_architecture != "Any":
            filtered_data = [lora for lora in filtered_data if lora['architecture'] == filter_architecture]
        if filter_category != "Any":
            filtered_data = [lora for lora in filtered_data if lora['category'] == filter_category]
        
        # Get card size configuration
        size_config = self._get_card_size_styles(gallery_size)
        
        # Generate the gallery HTML with embedded JavaScript
        html = self._create_interactive_gallery(filtered_data, selected_index, size_config, 
                                               show_architecture, show_category)
        
        # Get info about selected LoRA
        selected_lora_info = "No selection"
        if 1 <= selected_index <= len(lora_data):
            selected_lora = lora_data[selected_index - 1]
            selected_lora_info = f"{selected_lora['name']} - {selected_lora['architecture']} ({selected_lora['category']})"
        
        return (html, selected_index, selected_lora_info)
    
    def _create_interactive_gallery(self, lora_data: List[Dict], selected_index: int, 
                                   size_config: Dict, show_architecture: bool, 
                                   show_category: bool) -> str:
        """Create HTML gallery with JavaScript enhancement."""
        
        html = f"""
        <div id="lora-gallery-container" style="max-height: 800px; overflow-y: auto; background: #1a1a1a; border-radius: 8px;">
            <style>
                .lora-gallery {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax({size_config['card_width']}, 1fr));
                    gap: 12px;
                    padding: 15px;
                    background: #1a1a1a;
                }}
                .lora-card {{
                    border: 2px solid #333;
                    border-radius: 8px;
                    padding: {size_config['padding']};
                    cursor: pointer;
                    transition: all 0.3s ease;
                    background: #2a2a2a;
                    position: relative;
                    overflow: hidden;
                }}
                .lora-card:hover {{
                    border-color: #666;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }}
                .lora-card.selected {{
                    border-color: #4a9eff;
                    background: #1a3a5a;
                    box-shadow: 0 0 15px rgba(74, 158, 255, 0.3);
                }}
                .lora-image {{
                    width: 100%;
                    height: {size_config['image_height']};
                    object-fit: cover;
                    border-radius: 6px;
                    background: #333;
                    display: block;
                }}
                .lora-name {{
                    font-size: {size_config['font_size']};
                    color: #fff;
                    margin-top: 6px;
                    text-align: center;
                    word-wrap: break-word;
                    line-height: 1.2;
                    max-height: 2.4em;
                    overflow: hidden;
                }}
                .lora-index {{
                    position: absolute;
                    top: 4px;
                    right: 4px;
                    background: rgba(0,0,0,0.8);
                    color: #fff;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }}
                .lora-badges {{
                    position: absolute;
                    top: 4px;
                    left: 4px;
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }}
                .badge {{
                    background: rgba(0,0,0,0.7);
                    color: #fff;
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-size: 8px;
                    font-weight: bold;
                }}
                .badge.architecture {{
                    background: rgba(74, 158, 255, 0.8);
                }}
                .badge.category {{
                    background: rgba(255, 140, 0, 0.8);
                }}
                .ratings {{
                    position: absolute;
                    bottom: 4px;
                    left: 4px;
                    font-size: 8px;
                    color: #ffd700;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                .gallery-header {{
                    padding: 10px 15px;
                    background: #333;
                    color: #fff;
                    font-size: 12px;
                    border-bottom: 1px solid #555;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .selection-info {{
                    background: #1a3a5a;
                    padding: 10px 15px;
                    color: #fff;
                    font-size: 12px;
                    border-top: 1px solid #555;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .copy-btn {{
                    margin-left: 10px;
                    padding: 4px 8px;
                    background: #4a9eff;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 10px;
                    transition: background 0.2s;
                }}
                .copy-btn:hover {{
                    background: #357abd;
                }}
                .copy-btn.copied {{
                    background: #28a745;
                }}
                .no-image {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #666;
                    font-size: 10px;
                    background: #333;
                }}
            </style>
            
            <div class="gallery-header">
                <span>Gallery: {len(lora_data)} LoRAs | Click to select</span>
                <span>Currently: #{selected_index}</span>
            </div>
            
            <div class="lora-gallery">
        """
        
        # Generate cards for each LoRA
        for lora in lora_data:
            is_selected = lora['index'] == selected_index
            selected_class = "selected" if is_selected else ""
            
            # Generate image HTML
            if lora.get('image_path') and os.path.exists(lora['image_path']):
                # Convert to file:// URL for browser display
                img_url = f"file:///{lora['image_path'].replace(os.sep, '/')}"
                image_html = f'<img src="{img_url}" class="lora-image" alt="{lora["name"]}" onerror="this.parentElement.innerHTML=\'<div class=\\"lora-image no-image\\">No Image</div>\'">'
            else:
                image_html = '<div class="lora-image no-image">No Image</div>'
            
            # Generate badges
            badges_html = '<div class="lora-badges">'
            if show_architecture and lora['architecture'] != "Unknown":
                badges_html += f'<span class="badge architecture">{lora["architecture"]}</span>'
            if show_category and lora['category'] != "unknown":
                badges_html += f'<span class="badge category">{lora["category"]}</span>'
            badges_html += '</div>'
            
            # Generate ratings if available
            ratings_html = ""
            if lora.get('quality_rating', 0) > 0:
                stars = "★" * lora['quality_rating']
                ratings_html = f'<div class="ratings">Q:{stars}</div>'
            
            # Generate trigger words tooltip
            trigger_tooltip = ""
            if lora.get('triggers'):
                trigger_tooltip = f'title="Triggers: {", ".join(lora["triggers"])}"'
            
            html += f"""
                <div class="lora-card {selected_class}" 
                     onclick="selectLoRA({lora['index']})" 
                     {trigger_tooltip}>
                    <div class="lora-index">{lora['index']}</div>
                    {badges_html}
                    {image_html}
                    <div class="lora-name">{lora['name']}</div>
                    {ratings_html}
                </div>
            """
        
        html += f"""
            </div>
            
            <div class="selection-info" id="selection-info">
                <span id="selected-info">
                    Selected: <span id="selected-name">{lora_data[selected_index-1]['name'] if selected_index <= len(lora_data) else 'None'}</span>
                </span>
                <span>
                    Use seed: <span id="selected-seed" style="font-weight: bold; color: #4a9eff;">{selected_index}</span>
                    <button onclick="copyToClipboard()" class="copy-btn" id="copy-btn">Copy Seed</button>
                </span>
            </div>
        </div>

        <script>
            // Store the current selection and data
            let currentSelection = {selected_index};
            let loraData = {json.dumps(lora_data, default=str)};
            
            function selectLoRA(index) {{
                // Update visual selection
                document.querySelectorAll('.lora-card').forEach((card, i) => {{
                    const cardIndex = parseInt(card.querySelector('.lora-index').textContent);
                    card.classList.toggle('selected', cardIndex === index);
                }});
                
                // Update info display
                currentSelection = index;
                const selectedLora = loraData.find(lora => lora.index === index);
                if (selectedLora) {{
                    document.getElementById('selected-name').textContent = selectedLora.name;
                    document.getElementById('selected-seed').textContent = index;
                }}
                
                // Log for debugging
                console.log('Selected LoRA:', selectedLora ? selectedLora.name : 'Unknown', 'Seed:', index);
                
                // Note: In ComfyUI, you can't directly update node inputs from JavaScript
                // The user needs to manually change the seed input to match
            }}
            
            function copyToClipboard() {{
                const seedText = document.getElementById('selected-seed').textContent;
                const button = document.getElementById('copy-btn');
                
                // Try modern clipboard API first
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(seedText).then(() => {{
                        showCopyFeedback(button);
                    }}).catch(err => {{
                        // Fallback to older method
                        fallbackCopyToClipboard(seedText, button);
                    }});
                }} else {{
                    fallbackCopyToClipboard(seedText, button);
                }}
            }}
            
            function fallbackCopyToClipboard(text, button) {{
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {{
                    document.execCommand('copy');
                    showCopyFeedback(button);
                }} catch (err) {{
                    console.error('Could not copy text: ', err);
                    alert('Copy failed. Seed number is: ' + text);
                }}
                
                document.body.removeChild(textArea);
            }}
            
            function showCopyFeedback(button) {{
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.classList.add('copied');
                
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.classList.remove('copied');
                }}, 1500);
            }}
            
            // Initialize gallery
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('LoRA Gallery initialized with', loraData.length, 'items');
                
                // Ensure selected item is visible
                const selectedCard = document.querySelector('.lora-card.selected');
                if (selectedCard) {{
                    selectedCard.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                }}
            }});
        </script>
        """
        
        return html

class LoRADatabaseStatsNode:
    """
    Node for viewing comprehensive database statistics and health metrics.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "refresh_stats": ("BOOLEAN", {"default": False,
                    "tooltip": "Force refresh of statistics"}),
                "show_detailed_breakdown": ("BOOLEAN", {"default": True,
                    "tooltip": "Show detailed category and architecture breakdowns"}),
                "show_missing_data": ("BOOLEAN", {"default": True,
                    "tooltip": "Show LoRAs missing metadata"}),
                "show_ratings_analysis": ("BOOLEAN", {"default": True,
                    "tooltip": "Show ratings and feedback analysis"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("stats_overview", "detailed_breakdown", "missing_data_report", "recommendations")
    FUNCTION = "generate_stats"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def generate_stats(self, refresh_stats: bool, show_detailed_breakdown: bool, 
                      show_missing_data: bool, show_ratings_analysis: bool) -> Tuple[str, str, str, str]:
        """Generate comprehensive database statistics."""
        
        loras = self.lora_db.get("loras", {})
        total_loras = len(loras)
        
        if total_loras == 0:
            return ("No LoRAs in database", "", "", "Scan for LoRAs to populate database")
        
        # Basic statistics
        architectures = {}
        categories = {}
        ratings_data = {"quality": [], "ease_of_use": [], "versatility": []}
        missing_data = {
            "no_architecture": 0,
            "no_category": 0,
            "no_triggers": 0,
            "no_images": 0,
            "no_ratings": 0,
            "no_notes": 0
        }
        
        recent_tests = []
        
        # Analyze each LoRA
        for lora_hash, lora_data in loras.items():
            # Architecture analysis
            arch = lora_data.get("architecture", "Unknown")
            architectures[arch] = architectures.get(arch, 0) + 1
            
            # Category analysis
            cat = lora_data.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            
            # Missing data analysis
            if arch == "Unknown":
                missing_data["no_architecture"] += 1
            if cat == "unknown":
                missing_data["no_category"] += 1
            
            triggers = lora_data.get("trigger_words", {}).get("full_list", [])
            if not triggers:
                missing_data["no_triggers"] += 1
            
            # Check for associated images
            lora_path = lora_data.get("path", "")
            if lora_path:
                image_paths = self._find_associated_images(lora_path)
                if not image_paths:
                    missing_data["no_images"] += 1
            
            # Ratings analysis
            feedback = lora_data.get("user_feedback", {})
            quality = feedback.get("quality_rating", 0)
            ease = feedback.get("ease_of_use", 0)
            versatility = feedback.get("versatility", 0)
            
            if quality > 0:
                ratings_data["quality"].append(quality)
            if ease > 0:
                ratings_data["ease_of_use"].append(ease)
            if versatility > 0:
                ratings_data["versatility"].append(versatility)
            
            if quality == 0 and ease == 0 and versatility == 0:
                missing_data["no_ratings"] += 1
            
            notes = feedback.get("quick_notes", "")
            if not notes:
                missing_data["no_notes"] += 1
            
            # Recent activity
            last_tested = feedback.get("last_tested", "")
            if last_tested:
                recent_tests.append((lora_data.get("name", "Unknown"), last_tested))
        
        # Generate overview
        overview = self._generate_overview(total_loras, architectures, categories, ratings_data)
        
        # Generate detailed breakdown
        breakdown = ""
        if show_detailed_breakdown:
            breakdown = self._generate_detailed_breakdown(architectures, categories, ratings_data)
        
        # Generate missing data report
        missing_report = ""
        if show_missing_data:
            missing_report = self._generate_missing_data_report(missing_data, total_loras)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(missing_data, total_loras, recent_tests)
        
        return (overview, breakdown, missing_report, recommendations)
    
    def _find_associated_images(self, lora_path: str) -> List[str]:
        """Find images associated with a LoRA file."""
        base_path = os.path.splitext(lora_path)[0]
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        associated_images = []
        
        for ext in image_extensions:
            img_path = base_path + ext
            if os.path.exists(img_path):
                associated_images.append(img_path)
                break
        return associated_images
    
    def _generate_overview(self, total: int, architectures: Dict, categories: Dict, ratings: Dict) -> str:
        """Generate overview statistics."""
        overview = f"=== LoRA DATABASE OVERVIEW ===\n"
        overview += f"Total LoRAs: {total}\n\n"
        
        # Top architectures
        sorted_archs = sorted(architectures.items(), key=lambda x: x[1], reverse=True)
        overview += "Top Architectures:\n"
        for arch, count in sorted_archs[:5]:
            percentage = (count / total) * 100
            overview += f"  {arch}: {count} ({percentage:.1f}%)\n"
        
        # Top categories
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        overview += "\nTop Categories:\n"
        for cat, count in sorted_cats[:5]:
            percentage = (count / total) * 100
            overview += f"  {cat}: {count} ({percentage:.1f}%)\n"
        
        # Ratings summary
        if ratings["quality"]:
            avg_quality = sum(ratings["quality"]) / len(ratings["quality"])
            overview += f"\nRatings Summary:\n"
            overview += f"  Average Quality: {avg_quality:.1f}/5 ({len(ratings['quality'])} rated)\n"
            
            if ratings["ease_of_use"]:
                avg_ease = sum(ratings["ease_of_use"]) / len(ratings["ease_of_use"])
                overview += f"  Average Ease of Use: {avg_ease:.1f}/5 ({len(ratings['ease_of_use'])} rated)\n"
            
            if ratings["versatility"]:
                avg_versatility = sum(ratings["versatility"]) / len(ratings["versatility"])
                overview += f"  Average Versatility: {avg_versatility:.1f}/5 ({len(ratings['versatility'])} rated)\n"
        
        return overview
    
    def _generate_detailed_breakdown(self, architectures: Dict, categories: Dict, ratings: Dict) -> str:
        """Generate detailed breakdown."""
        breakdown = "=== DETAILED BREAKDOWN ===\n\n"
        
        # All architectures
        breakdown += "Architecture Distribution:\n"
        sorted_archs = sorted(architectures.items(), key=lambda x: x[1], reverse=True)
        for arch, count in sorted_archs:
            breakdown += f"  {arch}: {count}\n"
        
        # All categories
        breakdown += "\nCategory Distribution:\n"
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_cats:
            breakdown += f"  {cat}: {count}\n"
        
        # Ratings distribution
        if ratings["quality"]:
            breakdown += "\nQuality Ratings Distribution:\n"
            for rating in range(1, 6):
                count = ratings["quality"].count(rating)
                if count > 0:
                    breakdown += f"  {rating} Stars: {count}\n"
        
        return breakdown
    
    def _generate_missing_data_report(self, missing: Dict, total: int) -> str:
        """Generate missing data report."""
        report = "=== MISSING DATA REPORT ===\n\n"
        
        if missing["no_architecture"] > 0:
            pct = (missing["no_architecture"] / total) * 100
            report += f"Unknown Architecture: {missing['no_architecture']} ({pct:.1f}%)\n"
        
        if missing["no_category"] > 0:
            pct = (missing["no_category"] / total) * 100
            report += f"Unknown Category: {missing['no_category']} ({pct:.1f}%)\n"
        
        if missing["no_triggers"] > 0:
            pct = (missing["no_triggers"] / total) * 100
            report += f"No Trigger Words: {missing['no_triggers']} ({pct:.1f}%)\n"
        
        if missing["no_images"] > 0:
            pct = (missing["no_images"] / total) * 100
            report += f"No Associated Images: {missing['no_images']} ({pct:.1f}%)\n"
        
        if missing["no_ratings"] > 0:
            pct = (missing["no_ratings"] / total) * 100
            report += f"No Ratings: {missing['no_ratings']} ({pct:.1f}%)\n"
        
        if missing["no_notes"] > 0:
            pct = (missing["no_notes"] / total) * 100
            report += f"No Notes: {missing['no_notes']} ({pct:.1f}%)\n"
        
        if not any(missing.values()):
            report += "✓ All LoRAs have complete metadata!\n"
        
        return report
    
    def _generate_recommendations(self, missing: Dict, total: int, recent_tests: List) -> str:
        """Generate recommendations for improving the database."""
        recommendations = "=== RECOMMENDATIONS ===\n\n"
        
        priority_issues = []
        
        # High priority recommendations
        if missing["no_architecture"] > total * 0.1:  # More than 10% unknown
            priority_issues.append("🔴 HIGH: Many LoRAs have unknown architecture - use Batch Info Setter")
        
        if missing["no_triggers"] > total * 0.2:  # More than 20% no triggers
            priority_issues.append("🔴 HIGH: Many LoRAs missing trigger words - enable Civitai fetching")
        
        # Medium priority recommendations
        if missing["no_category"] > total * 0.15:  # More than 15% unknown category
            priority_issues.append("🟡 MEDIUM: Many LoRAs need categorization")
        
        if missing["no_ratings"] > total * 0.5:  # More than 50% unrated
            priority_issues.append("🟡 MEDIUM: Consider rating your LoRAs for better organization")
        
        # Low priority recommendations
        if missing["no_images"] > total * 0.3:  # More than 30% no images
            priority_issues.append("🟢 LOW: Many LoRAs could benefit from preview images")
        
        if missing["no_notes"] > total * 0.8:  # More than 80% no notes
            priority_issues.append("🟢 LOW: Add notes to your favorite LoRAs for better recall")
        
        if priority_issues:
            for issue in priority_issues:
                recommendations += f"{issue}\n"
        else:
            recommendations += "✓ Your database is in excellent shape!\n"
        
        # Activity recommendations
        if len(recent_tests) < total * 0.1:  # Less than 10% recently tested
            recommendations += "\n💡 TIP: Regular testing helps keep your database current\n"
        
        recommendations += "\n--- Quick Actions ---\n"
        recommendations += "• Use Batch Info Setter for bulk architecture/category updates\n"
        recommendations += "• Enable Civitai fetching in LoRA Tester for automatic trigger words\n"
        recommendations += "• Use Quick Feedback node during testing sessions\n"
        recommendations += "• Use Gallery Display for visual database browsing\n"
        
        return recommendations

class LoRADatabaseMaintenanceNode:
    """
    Node for database maintenance, cleanup, and optimization operations.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "maintenance_action": (["Check Health", "Remove Dead Entries", "Fix Missing Paths", 
                                      "Optimize Database", "Backup Database", "Clean Duplicates"],
                    {"default": "Check Health", "tooltip": "Maintenance operation to perform"}),
                "confirm_action": ("BOOLEAN", {"default": False,
                    "tooltip": "Confirm destructive operations (required for Remove/Fix operations)"}),
                "backup_before_changes": ("BOOLEAN", {"default": True,
                    "tooltip": "Create backup before making changes"}),
            },
            "optional": {
                "custom_backup_name": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Custom backup filename (leave empty for auto-generated)"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("operation_result", "health_report", "backup_info")
    FUNCTION = "perform_maintenance"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        self.backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _load_lora_db(self) -> Dict:
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _save_lora_db(self):
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    
    def _create_backup(self, custom_name: str = "") -> str:
        """Create a backup of the current database."""
        from datetime import datetime
        
        if custom_name:
            backup_filename = f"{custom_name}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"lora_db_backup_{timestamp}.json"
        
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            with open(backup_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
            return f"Backup created: {backup_filename}"
        except IOError as e:
            return f"Backup failed: {e}"
    
    def perform_maintenance(self, maintenance_action: str, confirm_action: bool, 
                          backup_before_changes: bool, custom_backup_name: str = "") -> Tuple[str, str, str]:
        """Perform selected maintenance operation."""
        
        backup_info = ""
        
        # Create backup if requested and action is destructive
        destructive_actions = ["Remove Dead Entries", "Fix Missing Paths", "Clean Duplicates"]
        if backup_before_changes and maintenance_action in destructive_actions:
            backup_info = self._create_backup(custom_backup_name)
        elif maintenance_action == "Backup Database":
            backup_info = self._create_backup(custom_backup_name)
            return ("Backup completed", "", backup_info)
        
        # Perform the requested operation
        if maintenance_action == "Check Health":
            result, health_report = self._check_database_health()
        elif maintenance_action == "Remove Dead Entries":
            if not confirm_action:
                result = "Error: Confirmation required for destructive operation"
                health_report = "Operation cancelled - enable 'confirm_action'"
            else:
                result, health_report = self._remove_dead_entries()
        elif maintenance_action == "Fix Missing Paths":
            if not confirm_action:
                result = "Error: Confirmation required for path fixes"
                health_report = "Operation cancelled - enable 'confirm_action'"
            else:
                result, health_report = self._fix_missing_paths()
        elif maintenance_action == "Optimize Database":
            result, health_report = self._optimize_database()
        elif maintenance_action == "Clean Duplicates":
            if not confirm_action:
                result = "Error: Confirmation required for duplicate removal"
                health_report = "Operation cancelled - enable 'confirm_action'"
            else:
                result, health_report = self._clean_duplicates()
        else:
            result = f"Unknown maintenance action: {maintenance_action}"
            health_report = ""
        
        return (result, health_report, backup_info)
    
    def _check_database_health(self) -> Tuple[str, str]:
        """Check database health and integrity."""
        loras = self.lora_db.get("loras", {})
        issues = []
        
        dead_entries = 0
        missing_fields = 0
        corrupted_entries = 0
        
        for lora_hash, lora_data in loras.items():
            # Check if file exists
            lora_path = lora_data.get("path", "")
            if lora_path and not os.path.exists(lora_path):
                dead_entries += 1
                issues.append(f"Dead entry: {lora_data.get('name', 'Unknown')}")
            
            # Check for required fields
            required_fields = ["path", "name", "architecture", "category"]
            for field in required_fields:
                if field not in lora_data:
                    missing_fields += 1
                    issues.append(f"Missing {field}: {lora_data.get('name', lora_hash[:8])}")
                    break
            
            # Check data integrity
            try:
                # Ensure trigger_words structure is correct
                if "trigger_words" in lora_data:
                    triggers = lora_data["trigger_words"]
                    if not isinstance(triggers.get("full_list", []), list):
                        corrupted_entries += 1
                        issues.append(f"Corrupted triggers: {lora_data.get('name', 'Unknown')}")
            except Exception:
                corrupted_entries += 1
                issues.append(f"Corrupted data: {lora_data.get('name', 'Unknown')}")
        
        # Generate health report
        health_report = f"=== DATABASE HEALTH CHECK ===\n\n"
        health_report += f"Total Entries: {len(loras)}\n"
        health_report += f"Dead Entries: {dead_entries}\n"
        health_report += f"Missing Fields: {missing_fields}\n"
        health_report += f"Corrupted Entries: {corrupted_entries}\n\n"
        
        if issues:
            health_report += "Issues Found:\n"
            for issue in issues[:20]:  # Show first 20 issues
                health_report += f"  • {issue}\n"
            if len(issues) > 20:
                health_report += f"  ... and {len(issues) - 20} more\n"
        else:
            health_report += "✓ Database is healthy!\n"
        
        result = f"Health check completed. Found {len(issues)} issues."
        return result, health_report
    
    def _remove_dead_entries(self) -> Tuple[str, str]:
        """Remove entries for LoRAs that no longer exist."""
        loras = self.lora_db.get("loras", {})
        dead_hashes = []
        
        for lora_hash, lora_data in loras.items():
            lora_path = lora_data.get("path", "")
            if lora_path and not os.path.exists(lora_path):
                dead_hashes.append(lora_hash)
        
        # Remove dead entries
        for dead_hash in dead_hashes:
            del self.lora_db["loras"][dead_hash]
        
        if dead_hashes:
            self._save_lora_db()
        
        result = f"Removed {len(dead_hashes)} dead entries"
        health_report = f"Cleaned up {len(dead_hashes)} entries for missing LoRA files"
        
        return result, health_report
    
    def _fix_missing_paths(self) -> Tuple[str, str]:
        """Attempt to fix entries with missing or incorrect paths."""
        # This would implement path fixing logic
        # For now, return a placeholder
        result = "Path fixing not yet implemented"
        health_report = "This feature will attempt to relocate moved LoRA files"
        return result, health_report
    
    def _optimize_database(self) -> Tuple[str, str]:
        """Optimize database structure and remove redundant data."""
        optimizations = []
        
        # Remove empty fields
        loras = self.lora_db.get("loras", {})
        for lora_hash, lora_data in loras.items():
            # Remove empty lists and strings
            for key, value in list(lora_data.items()):
                if isinstance(value, list) and not value:
                    if key not in ["full_list", "selected"]:  # Keep these even if empty
                        del lora_data[key]
                        optimizations.append(f"Removed empty {key}")
                elif isinstance(value, str) and not value.strip():
                    if key not in ["notes", "quick_notes"]:  # Keep these even if empty
                        del lora_data[key]
                        optimizations.append(f"Removed empty {key}")
        
        # Ensure consistent structure
        for lora_hash, lora_data in loras.items():
            # Ensure all required fields exist
            if "recommended_settings" not in lora_data:
                lora_data["recommended_settings"] = {
                    "best_checkpoints": [],
                    "avoid_checkpoints": [],
                    "optimal_cfg_range": "",
                    "resolution_preference": "",
                    "style_tags": [],
                }
                optimizations.append("Added missing recommended_settings")
            
            if "user_feedback" not in lora_data:
                lora_data["user_feedback"] = {
                    "quality_rating": 0,
                    "ease_of_use": 0,
                    "versatility": 0,
                    "last_tested": "",
                    "quick_notes": "",
                }
                optimizations.append("Added missing user_feedback")
        
        if optimizations:
            self._save_lora_db()
        
        result = f"Database optimized. Made {len(optimizations)} improvements."
        health_report = f"Optimization completed:\n" + "\n".join(optimizations[:10])
        
        return result, health_report
    
    def _clean_duplicates(self) -> Tuple[str, str]:
        """Remove duplicate entries based on file paths."""
        loras = self.lora_db.get("loras", {})
        path_to_hash = {}
        duplicates = []
        
        # Find duplicates
        for lora_hash, lora_data in loras.items():
            path = lora_data.get("path", "")
            if path:
                normalized_path = os.path.normpath(path)
                if normalized_path in path_to_hash:
                    # This is a duplicate
                    duplicates.append(lora_hash)
                else:
                    path_to_hash[normalized_path] = lora_hash
        
        # Remove duplicates (keep the first one found)
        for dup_hash in duplicates:
            del self.lora_db["loras"][dup_hash]
        
        if duplicates:
            self._save_lora_db()
        
        result = f"Removed {len(duplicates)} duplicate entries"
        health_report = f"Cleaned up {len(duplicates)} duplicate database entries"
        
        return result, health_report

class LoRABulkOperationsNode:
    """
    Node for performing bulk operations on LoRA collections.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "operation_type": (["Auto-Detect Architecture", "Bulk Categorize", "Fetch All Triggers", 
                                  "Apply Ratings Filter", "Export Filtered Set", "Import Metadata"],
                    {"default": "Auto-Detect Architecture", "tooltip": "Type of bulk operation"}),
                "filter_architecture": (["Any", "Unknown", "SD1.5", "SDXL", "Flux", "Pony", "Illustrious", 
                    "Noobai", "SD3.5 Medium", "SD3.5 Large", "HiDream", 
                    "Stable Cascade", "PixArt Sigma", "Playground"], 
                    {"default": "Any", "tooltip": "Filter by architecture"}),
                "filter_category": (["Any", "unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "graphic", "treatment", "tool", "slider", 
                    "anime", "realism", "details", "lighting", "mood", "texture",
                    "fantasy", "scifi", "historical", "nsfw", "enhancement"],
                    {"default": "Any", "tooltip": "Filter by category"}),
                "confirm_operation": ("BOOLEAN", {"default": False,
                    "tooltip": "Confirm bulk operation (required for safety)"}),
            },
            "optional": {
                "new_architecture": (["SD1.5", "SD2.1", "SDXL", "Pony", "Illustrious", 
                    "Noobai", "SD3.5 Medium", "SD3.5 Large", "Flux", "HiDream", 
                    "Stable Cascade", "PixArt Sigma", "Playground"], 
                    {"default": "SD1.5", "tooltip": "New architecture for bulk update"}),
                "new_category": (["unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "graphic", "treatment", "tool", "slider",
                    "anime", "realism", "details", "lighting", "mood", "texture",
                    "fantasy", "scifi", "historical", "nsfw", "enhancement"],
                    {"default": "unknown", "tooltip": "New category for bulk update"}),
                "rating_threshold": ("INT", {"default": 3, "min": 1, "max": 5,
                    "tooltip": "Minimum rating for filtering"}),
                "export_filename": ("STRING", {"default": "lora_export", "multiline": False,
                    "tooltip": "Filename for export operations"}),
                "path_filter": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Filter by path substring (optional)"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("operation_result", "detailed_log", "items_processed")
    FUNCTION = "perform_bulk_operation"
    CATEGORY = "loaders/lora tester"
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        
        # Architecture detection patterns
        self.architecture_patterns = {
            "SD1.5": ["sd1.5", "sd15", "sd-1-5", "stable-diffusion-v1", "v1-5", "sd_v1", "sd1", "sd_1"],
            "SD2.1": ["sd2.1", "sd21", "sd-2-1", "stable-diffusion-v2", "v2-1", "sd2", "v2", "sd_2"],
            "SDXL": ["sdxl", "sd-xl", "stable-diffusion-xl", "sd_xl", "xl_base", "SDXL", "XL_"],
            "SD3.5 Medium": ["sd3.5", "sd35", "sd35medium", "medium", "sd3-medium"],
            "SD3.5 Large": ["sd3.5", "sd35", "sd35large", "large", "sd3-large"],
            "Flux": ["flux", "FLUX", "Flux1", "flux1d", "flux-1d", "flux_1d"],
            "Pony": ["pony", "PONY", "Pony", "ponyV1"],
            "Illustrious": ["illustrious", "illustrious-xl"],
            "Noobai": ["noobai", "noobai-xl"],
            "HiDream": ["hidream", "HiDream"],
            "Stable Cascade": ["cascade", "stable-cascade"],
            "PixArt Sigma": ["pixart", "pixart-sigma"],
            "Playground": ["playground", "playground-v2"]
        }
    
    def _load_lora_db(self) -> Dict:
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _save_lora_db(self):
        try:
            with open(self.lora_db_path, 'w') as f:
                json.dump(self.lora_db, f, indent=2)
        except IOError:
            print("Warning: Could not save LoRA database.")
    
    def _filter_loras(self, architecture_filter: str, category_filter: str, path_filter: str) -> List[Tuple[str, Dict]]:
        """Filter LoRAs based on criteria."""
        loras = self.lora_db.get("loras", {})
        filtered = []
        
        for lora_hash, lora_data in loras.items():
            # Architecture filter
            if architecture_filter != "Any":
                current_arch = lora_data.get("architecture", "Unknown")
                if current_arch != architecture_filter:
                    continue
            
            # Category filter
            if category_filter != "Any":
                current_cat = lora_data.get("category", "unknown")
                if current_cat != category_filter:
                    continue
            
            # Path filter
            if path_filter:
                lora_path = lora_data.get("path", "")
                if path_filter.lower() not in lora_path.lower():
                    continue
            
            filtered.append((lora_hash, lora_data))
        
        return filtered
    
    def _detect_architecture(self, lora_data: Dict) -> str:
        """Auto-detect architecture from path and filename."""
        path = lora_data.get("path", "").lower()
        
        for arch, patterns in self.architecture_patterns.items():
            for pattern in patterns:
                if pattern.lower() in path:
                    return arch
        
        return "Unknown"
    
    def perform_bulk_operation(self, operation_type: str, filter_architecture: str, filter_category: str,
                             confirm_operation: bool, new_architecture: str = "SD1.5", 
                             new_category: str = "unknown", rating_threshold: int = 3,
                             export_filename: str = "lora_export", path_filter: str = "") -> Tuple[str, str, int]:
        """Perform the selected bulk operation."""
        
        if not confirm_operation:
            return ("Error: Please confirm the operation", "Operation cancelled for safety", 0)
        
        # Get filtered LoRAs
        filtered_loras = self._filter_loras(filter_architecture, filter_category, path_filter)
        
        if not filtered_loras:
            return ("No LoRAs match the filter criteria", "", 0)
        
        # Perform the operation
        if operation_type == "Auto-Detect Architecture":
            return self._auto_detect_architecture(filtered_loras)
        elif operation_type == "Bulk Categorize":
            return self._bulk_categorize(filtered_loras, new_category)
        elif operation_type == "Fetch All Triggers":
            return self._fetch_all_triggers(filtered_loras)
        elif operation_type == "Apply Ratings Filter":
            return self._apply_ratings_filter(filtered_loras, rating_threshold)
        elif operation_type == "Export Filtered Set":
            return self._export_filtered_set(filtered_loras, export_filename)
        elif operation_type == "Import Metadata":
            return self._import_metadata(export_filename)
        else:
            return (f"Unknown operation: {operation_type}", "", 0)
    
    def _auto_detect_architecture(self, filtered_loras: List[Tuple[str, Dict]]) -> Tuple[str, str, int]:
        """Auto-detect and update architecture for filtered LoRAs."""
        updated_count = 0
        log_entries = []
        
        for lora_hash, lora_data in filtered_loras:
            current_arch = lora_data.get("architecture", "Unknown")
            detected_arch = self._detect_architecture(lora_data)
            
            if detected_arch != "Unknown" and detected_arch != current_arch:
                lora_data["architecture"] = detected_arch
                updated_count += 1
                log_entries.append(f"{lora_data.get('name', 'Unknown')}: {current_arch} → {detected_arch}")
        
        if updated_count > 0:
            self._save_lora_db()
        
        detailed_log = "Architecture Detection Results:\n\n" + "\n".join(log_entries[:20])
        if len(log_entries) > 20:
            detailed_log += f"\n... and {len(log_entries) - 20} more"
        
        result = f"Updated architecture for {updated_count}/{len(filtered_loras)} LoRAs"
        return result, detailed_log, updated_count
    
    def _bulk_categorize(self, filtered_loras: List[Tuple[str, Dict]], new_category: str) -> Tuple[str, str, int]:
        """Bulk update category for filtered LoRAs."""
        updated_count = 0
        log_entries = []
        
        for lora_hash, lora_data in filtered_loras:
            current_cat = lora_data.get("category", "unknown")
            if current_cat != new_category:
                lora_data["category"] = new_category
                updated_count += 1
                log_entries.append(f"{lora_data.get('name', 'Unknown')}: {current_cat} → {new_category}")
        
        if updated_count > 0:
            self._save_lora_db()
        
        detailed_log = "Category Update Results:\n\n" + "\n".join(log_entries[:20])
        if len(log_entries) > 20:
            detailed_log += f"\n... and {len(log_entries) - 20} more"
        
        result = f"Updated category for {updated_count}/{len(filtered_loras)} LoRAs to '{new_category}'"
        return result, detailed_log, updated_count
    
    def _fetch_all_triggers(self, filtered_loras: List[Tuple[str, Dict]]) -> Tuple[str, str, int]:
        """Fetch trigger words from Civitai for all filtered LoRAs."""
        # This would implement bulk Civitai fetching
        # For now, return a placeholder
        result = f"Trigger fetching for {len(filtered_loras)} LoRAs would be implemented here"
        detailed_log = "This feature will bulk fetch trigger words from Civitai"
        return result, detailed_log, 0
    
    def _apply_ratings_filter(self, filtered_loras: List[Tuple[str, Dict]], threshold: int) -> Tuple[str, str, int]:
        """Filter and report LoRAs above rating threshold."""
        high_rated = []
        
        for lora_hash, lora_data in filtered_loras:
            feedback = lora_data.get("user_feedback", {})
            quality = feedback.get("quality_rating", 0)
            if quality >= threshold:
                high_rated.append((lora_data.get("name", "Unknown"), quality))
        
        detailed_log = f"LoRAs with {threshold}+ star rating:\n\n"
        for name, rating in high_rated[:20]:
            stars = "★" * rating + "☆" * (5 - rating)
            detailed_log += f"{name}: {stars}\n"
        
        if len(high_rated) > 20:
            detailed_log += f"... and {len(high_rated) - 20} more"
        
        result = f"Found {len(high_rated)} LoRAs with {threshold}+ star rating"
        return result, detailed_log, len(high_rated)
    
    def _export_filtered_set(self, filtered_loras: List[Tuple[str, Dict]], filename: str) -> Tuple[str, str, int]:
        """Export filtered LoRA set to JSON file."""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_exported": len(filtered_loras),
            "loras": {}
        }
        
        for lora_hash, lora_data in filtered_loras:
            export_data["loras"][lora_hash] = lora_data
        
        export_path = os.path.join(os.path.dirname(__file__), f"{filename}.json")
        
        try:
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            result = f"Exported {len(filtered_loras)} LoRAs to {filename}.json"
            detailed_log = f"Export completed successfully.\nFile: {export_path}"
            return result, detailed_log, len(filtered_loras)
            
        except IOError as e:
            result = f"Export failed: {e}"
            detailed_log = f"Could not write to {export_path}"
            return result, detailed_log, 0
    
    def _import_metadata(self, filename: str) -> Tuple[str, str, int]:
        """Import metadata from exported JSON file."""
        import_path = os.path.join(os.path.dirname(__file__), f"{filename}.json")
        
        if not os.path.exists(import_path):
            return (f"Import file not found: {filename}.json", "", 0)
        
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            imported_loras = import_data.get("loras", {})
            merged_count = 0
            
            for lora_hash, lora_data in imported_loras.items():
                if lora_hash in self.lora_db["loras"]:
                    # Merge data, keeping existing data where conflicts occur
                    existing_data = self.lora_db["loras"][lora_hash]
                    for key, value in lora_data.items():
                        if key not in existing_data or not existing_data[key]:
                            existing_data[key] = value
                else:
                    # New entry
                    self.lora_db["loras"][lora_hash] = lora_data
                merged_count += 1
            
            self._save_lora_db()
            
            result = f"Imported metadata for {merged_count} LoRAs"
            detailed_log = f"Import completed from {import_path}\nProcessed {len(imported_loras)} entries"
            return result, detailed_log, merged_count
            
        except (IOError, json.JSONDecodeError) as e:
            result = f"Import failed: {e}"
            detailed_log = f"Could not read from {import_path}"
            return result, detailed_log, 0

class LoRAGalleryWithEditNode:
    """Enhanced gallery with quick edit capabilities and advanced filtering"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_list": ("STRING", {"default": "", "multiline": True,
                    "tooltip": "LoRA list from LoRA Tester node"}),
                "selected_index": ("INT", {"default": 1, "min": 1, "max": 999,
                    "tooltip": "Currently selected LoRA index (1-based)"}),
                "edit_mode": ("BOOLEAN", {"default": False,
                    "tooltip": "Enable quick edit mode for gallery cards"}),
                "gallery_size": (["small", "medium", "large"], {"default": "medium",
                    "tooltip": "Size of gallery cards"}),
                "show_architecture": ("BOOLEAN", {"default": True,
                    "tooltip": "Show architecture badges on cards"}),
                "show_category": ("BOOLEAN", {"default": True,
                    "tooltip": "Show category badges on cards"}),
                "show_ratings": ("BOOLEAN", {"default": True,
                    "tooltip": "Show rating stars on cards"}),
                "show_triggers": ("BOOLEAN", {"default": True,
                    "tooltip": "Show trigger words in tooltips"}),
            },
            "optional": {
                "filter_architecture": (["Any", "Unknown", "SD1.5", "SDXL", "Flux", "Pony", "Illustrious", 
                    "Noobai", "SD3.5 Medium", "SD3.5 Large", "HiDream", 
                    "Stable Cascade", "PixArt Sigma", "Playground"], 
                    {"default": "Any", "tooltip": "Filter gallery by architecture"}),
                "filter_category": (["Any", "unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "graphic", "treatment", "tool", "slider", 
                    "anime", "realism", "details", "lighting", "mood", "texture",
                    "fantasy", "scifi", "historical", "nsfw", "enhancement"],
                    {"default": "Any", "tooltip": "Filter gallery by category"}),
                "min_rating": ("INT", {"default": 0, "min": 0, "max": 5,
                    "tooltip": "Minimum quality rating filter (0 = show all)"}),
                "has_images_only": ("BOOLEAN", {"default": False,
                    "tooltip": "Show only LoRAs with associated images"}),
                "has_triggers_only": ("BOOLEAN", {"default": False,
                    "tooltip": "Show only LoRAs with trigger words"}),
                "search_text": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in LoRA names and trigger words"}),
            }
        }
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # This ensures the web extension gets triggered when inputs change
        return str(kwargs.get('lora_list', '')) + str(kwargs.get('edit_mode', False)) + str(kwargs.get('selected_index', 1))
    

    RETURN_TYPES = ("STRING", "INT", "STRING", "STRING") 
    RETURN_NAMES = ("gallery_html", "selected_index", "selected_lora_info", "edit_feedback")
    FUNCTION = "display_enhanced_gallery"
    CATEGORY = "loaders/lora tester"
    

    # Add this to make outputs visible to web extension
    OUTPUT_NODE = True
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
    
    def _load_lora_db(self) -> Dict:
        if os.path.exists(self.lora_db_path):
            try:
                with open(self.lora_db_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        try:
            hasher = hashlib.md5()
            file_stat = os.stat(file_path)
            metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            hasher.update(metadata.encode('utf-8'))
            with open(file_path, 'rb') as f:
                hasher.update(f.read(1024 * 1024))
            return hasher.hexdigest()
        except:
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def _find_associated_images(self, lora_path: str) -> List[str]:
        base_path = os.path.splitext(lora_path)[0]
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
        associated_images = []
        
        for ext in image_extensions:
            img_path = base_path + ext
            if os.path.exists(img_path):
                associated_images.append(img_path)
                break
        return associated_images
    
    def _parse_lora_list(self, lora_list: str) -> List[Dict]:
        lora_data = []
        if not lora_list or "No LoRAs match" in lora_list:
            return lora_data
        
        lines = lora_list.split('\n')
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            import re
            match = re.match(r'(\d+)\.\s+(.+?)(?:\s+\[([^\]]+)\])?\s*(?:\(([^)]+)\))?', line)
            if match:
                index, filename, architecture, category = match.groups()
                lora_path = self._find_lora_path(filename)
                
                lora_info = {
                    'index': int(index),
                    'name': filename,
                    'path': lora_path,
                    'architecture': architecture or "Unknown",
                    'category': category or "unknown",
                    'image_path': None,
                    'hash': ""
                }
                
                if lora_path:
                    lora_hash = self._calculate_lora_hash(lora_path)
                    lora_info['hash'] = lora_hash
                    
                    if lora_hash in self.lora_db["loras"]:
                        db_data = self.lora_db["loras"][lora_hash]
                        lora_info['architecture'] = db_data.get('architecture', lora_info['architecture'])
                        lora_info['category'] = db_data.get('category', lora_info['category'])
                        
                        feedback = db_data.get('user_feedback', {})
                        lora_info['quality_rating'] = feedback.get('quality_rating', 0)
                        lora_info['ease_of_use'] = feedback.get('ease_of_use', 0)
                        lora_info['versatility'] = feedback.get('versatility', 0)
                        lora_info['notes'] = feedback.get('quick_notes', '')
                        
                        triggers = db_data.get('trigger_words', {}).get('full_list', [])
                        lora_info['triggers'] = triggers
                        lora_info['selected_triggers'] = db_data.get('trigger_words', {}).get('selected', [])
                    
                    image_paths = self._find_associated_images(lora_path)
                    if image_paths:
                        lora_info['image_path'] = image_paths[0]
                
                lora_data.append(lora_info)
        
        return lora_data
    
    def _find_lora_path(self, filename: str) -> str:
        import folder_paths
        lora_dirs = folder_paths.get_folder_paths("loras")
        
        for directory in lora_dirs:
            for root, dirs, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)
        return ""
    
    def _apply_advanced_filters(self, lora_data: List[Dict], filters: Dict) -> List[Dict]:
        """Apply advanced filtering to LoRA data"""
        filtered = lora_data
        
        # Architecture filter
        if filters.get('filter_architecture') != "Any":
            filtered = [lora for lora in filtered if lora['architecture'] == filters['filter_architecture']]
        
        # Category filter
        if filters.get('filter_category') != "Any":
            filtered = [lora for lora in filtered if lora['category'] == filters['filter_category']]
        
        # Rating filter
        min_rating = filters.get('min_rating', 0)
        if min_rating > 0:
            filtered = [lora for lora in filtered if lora.get('quality_rating', 0) >= min_rating]
        
        # Images filter
        if filters.get('has_images_only', False):
            filtered = [lora for lora in filtered if lora.get('image_path')]
        
        # Triggers filter
        if filters.get('has_triggers_only', False):
            filtered = [lora for lora in filtered if lora.get('triggers')]
        
        # Text search
        search_text = filters.get('search_text', '').lower().strip()
        if search_text:
            search_filtered = []
            for lora in filtered:
                # Search in name
                if search_text in lora['name'].lower():
                    search_filtered.append(lora)
                    continue
                
                # Search in triggers
                if lora.get('triggers'):
                    trigger_text = ' '.join(lora['triggers']).lower()
                    if search_text in trigger_text:
                        search_filtered.append(lora)
                        continue
                
                # Search in notes
                if lora.get('notes') and search_text in lora['notes'].lower():
                    search_filtered.append(lora)
                    continue
            
            filtered = search_filtered
        
        return filtered
    
    def display_enhanced_gallery(self, lora_list: str, selected_index: int, edit_mode: bool,
                                gallery_size: str = "medium", show_architecture: bool = True, 
                                show_category: bool = True, show_ratings: bool = True, 
                                show_triggers: bool = True, **filters) -> Tuple[str, int, str, str]:
        """Display enhanced gallery with quick edit capabilities"""
        
        lora_data = self._parse_lora_list(lora_list)
        
        if not lora_data:
            return ("<div style='padding: 20px; text-align: center; color: #888;'>No LoRAs available</div>", 
                selected_index, "No LoRAs available", "")
        
        # Apply advanced filters
        filtered_data = self._apply_advanced_filters(lora_data, filters)
        
        if not filtered_data:
            return ("<div style='padding: 20px; text-align: center; color: #888;'>No LoRAs match current filters</div>", 
                selected_index, "No matches", "")
        
        size_config = self._get_card_size_styles(gallery_size)
        
        # This returns just HTML
        html = self._create_enhanced_gallery(filtered_data, selected_index, size_config, 
                                        show_architecture, show_category, show_ratings, 
                                        show_triggers, edit_mode)
        
        selected_lora_info = "No selection"
        if 1 <= selected_index <= len(lora_data):
            selected_lora = lora_data[selected_index - 1]
            selected_lora_info = f"{selected_lora['name']} - {selected_lora['architecture']} ({selected_lora['category']})"
        
        edit_feedback = f"Edit mode: {'Enabled' if edit_mode else 'Disabled'} | Showing {len(filtered_data)}/{len(lora_data)} LoRAs"
        
        return {
            "ui": {
                "gallery_html": [html],
                "lora_data": [json.dumps(filtered_data, default=str)],  # <-- filtered_data exists here
                "edit_mode": [edit_mode]
            },
            "result": (html, selected_index, selected_lora_info, edit_feedback)
        }
    
    def _get_card_size_styles(self, size: str) -> Dict[str, str]:
        size_configs = {
            "small": {"card_width": "140px", "image_height": "100px", "font_size": "10px", "padding": "6px"},
            "medium": {"card_width": "180px", "image_height": "140px", "font_size": "11px", "padding": "8px"},
            "large": {"card_width": "220px", "image_height": "180px", "font_size": "12px", "padding": "10px"}
        }
        return size_configs.get(size, size_configs["medium"])
    
    def _create_enhanced_gallery(self, lora_data: List[Dict], selected_index: int, size_config: Dict,
                               show_architecture: bool, show_category: bool, show_ratings: bool,
                               show_triggers: bool, edit_mode: bool) -> str:
        """Create enhanced gallery with edit capabilities"""
        
        html = f"""
        <div id="enhanced-lora-gallery" style="max-height: 900px; overflow-y: auto; background: #1a1a1a; border-radius: 8px;">
            <style>
                .enhanced-gallery {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax({size_config['card_width']}, 1fr));
                    gap: 12px;
                    padding: 15px;
                    background: #1a1a1a;
                }}
                .enhanced-card {{
                    border: 2px solid #333;
                    border-radius: 8px;
                    padding: {size_config['padding']};
                    cursor: pointer;
                    transition: all 0.3s ease;
                    background: #2a2a2a;
                    position: relative;
                    overflow: hidden;
                }}
                .enhanced-card:hover {{
                    border-color: #666;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }}
                .enhanced-card.selected {{
                    border-color: #4a9eff;
                    background: #1a3a5a;
                    box-shadow: 0 0 15px rgba(74, 158, 255, 0.3);
                }}
                .enhanced-card.edit-mode {{
                    border-color: #ff6b35;
                    background: #3d2a1a;
                }}
                .lora-image {{
                    width: 100%;
                    height: {size_config['image_height']};
                    object-fit: cover;
                    border-radius: 6px;
                    background: #333;
                    display: block;
                }}
                .lora-name {{
                    font-size: {size_config['font_size']};
                    color: #fff;
                    margin-top: 6px;
                    text-align: center;
                    word-wrap: break-word;
                    line-height: 1.2;
                    max-height: 2.4em;
                    overflow: hidden;
                }}
                .lora-index {{
                    position: absolute;
                    top: 4px;
                    right: 4px;
                    background: rgba(0,0,0,0.8);
                    color: #fff;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }}
                .lora-badges {{
                    position: absolute;
                    top: 4px;
                    left: 4px;
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }}
                .badge {{
                    background: rgba(0,0,0,0.7);
                    color: #fff;
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-size: 8px;
                    font-weight: bold;
                }}
                .badge.architecture {{ background: rgba(74, 158, 255, 0.8); }}
                .badge.category {{ background: rgba(255, 140, 0, 0.8); }}
                .badge.editable {{
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                .badge.editable:hover {{ background: rgba(255, 255, 255, 0.2); }}
                .ratings {{
                    position: absolute;
                    bottom: 4px;
                    left: 4px;
                    font-size: 8px;
                    color: #ffd700;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                    cursor: {('pointer' if edit_mode else 'default')};
                }}
                .edit-controls {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(0,0,0,0.9);
                    padding: 8px;
                    border-radius: 6px;
                    display: none;
                    flex-direction: column;
                    gap: 4px;
                    z-index: 10;
                }}
                .edit-btn {{
                    background: #4a9eff;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 10px;
                    transition: background 0.2s;
                }}
                .edit-btn:hover {{ background: #357abd; }}
                .edit-btn.danger {{ background: #ff4757; }}
                .edit-btn.danger:hover {{ background: #ff3742; }}
                .edit-btn.success {{ background: #2ed573; }}
                .edit-btn.success:hover {{ background: #26d069; }}
                .gallery-header {{
                    padding: 10px 15px;
                    background: #333;
                    color: #fff;
                    font-size: 12px;
                    border-bottom: 1px solid #555;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .filter-info {{
                    font-size: 10px;
                    color: #888;
                    font-style: italic;
                }}
                .selection-info {{
                    background: #1a3a5a;
                    padding: 10px 15px;
                    color: #fff;
                    font-size: 12px;
                    border-top: 1px solid #555;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .copy-btn {{
                    margin-left: 10px;
                    padding: 4px 8px;
                    background: #4a9eff;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 10px;
                    transition: background 0.2s;
                }}
                .copy-btn:hover {{ background: #357abd; }}
                .copy-btn.copied {{ background: #28a745; }}
                .no-image {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #666;
                    font-size: 10px;
                    background: #333;
                }}
                .quick-edit-panel {{
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #2a2a2a;
                    border: 2px solid #4a9eff;
                    border-radius: 8px;
                    padding: 20px;
                    z-index: 1000;
                    display: none;
                    min-width: 300px;
                    max-width: 500px;
                }}
                .edit-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.7);
                    z-index: 999;
                    display: none;
                }}
                .edit-form {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .edit-form label {{
                    color: #fff;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .edit-form select, .edit-form input, .edit-form textarea {{
                    padding: 6px;
                    border: 1px solid #555;
                    border-radius: 4px;
                    background: #333;
                    color: #fff;
                    font-size: 11px;
                }}
                .edit-form-buttons {{
                    display: flex;
                    gap: 10px;
                    justify-content: flex-end;
                }}
            </style>
            
            <div class="gallery-header">
                <div>
                    <span>Enhanced Gallery: {len(lora_data)} LoRAs</span>
                    <div class="filter-info">Edit Mode: {'ON' if edit_mode else 'OFF'} | Click cards to select, double-click to edit</div>
                </div>
                <span>Selected: #{selected_index}</span>
            </div>
            
            <div class="enhanced-gallery">
        """
        
        # Generate enhanced cards
        for lora in lora_data:
            is_selected = lora['index'] == selected_index
            selected_class = "selected" if is_selected else ""
            edit_class = "edit-mode" if edit_mode else ""
            
            # Generate image HTML
            if lora.get('image_path') and os.path.exists(lora['image_path']):
                img_url = f"file:///{lora['image_path'].replace(os.sep, '/')}"
                image_html = f'<img src="{img_url}" class="lora-image" alt="{lora["name"]}" onerror="this.parentElement.innerHTML=\'<div class=\\"lora-image no-image\\">No Image</div>\'">'
            else:
                image_html = '<div class="lora-image no-image">No Image</div>'
            
            # Generate badges
            badges_html = '<div class="lora-badges">'
            if show_architecture and lora['architecture'] != "Unknown":
                edit_attr = 'onclick="editArchitecture(event)" class="badge architecture editable"' if edit_mode else 'class="badge architecture"'
                badges_html += f'<span {edit_attr} data-hash="{lora["hash"]}" data-current="{lora["architecture"]}">{lora["architecture"]}</span>'
            if show_category and lora['category'] != "unknown":
                edit_attr = 'onclick="editCategory(event)" class="badge category editable"' if edit_mode else 'class="badge category"'
                badges_html += f'<span {edit_attr} data-hash="{lora["hash"]}" data-current="{lora["category"]}">{lora["category"]}</span>'
            badges_html += '</div>'
            
            # Generate ratings
            ratings_html = ""
            if show_ratings and lora.get('quality_rating', 0) > 0:
                stars = "★" * lora['quality_rating']
                edit_attr = 'onclick="editRating(event)"' if edit_mode else ''
                ratings_html = f'<div class="ratings" {edit_attr} data-hash="{lora["hash"]}" data-current="{lora["quality_rating"]}" title="Quality: {lora["quality_rating"]}/5">Q:{stars}</div>'
            
            # Generate trigger tooltip
            trigger_tooltip = ""
            if show_triggers and lora.get('triggers'):
                triggers_text = ", ".join(lora['triggers'][:5])  # Show first 5
                if len(lora['triggers']) > 5:
                    triggers_text += f" ... (+{len(lora['triggers']) - 5} more)"
                trigger_tooltip = f'title="Triggers: {triggers_text}"'
            
            # Edit controls for edit mode
            edit_controls = ""
            if edit_mode:
                edit_controls = f"""
                <div class="edit-controls" id="edit-controls-{lora['index']}">
                    <button class="edit-btn" onclick="quickEdit('{lora['hash']}', '{lora['name']}')">Quick Edit</button>
                    <button class="edit-btn success" onclick="rateQuick('{lora['hash']}', 5)">5★</button>
                    <button class="edit-btn success" onclick="rateQuick('{lora['hash']}', 4)">4★</button>
                    <button class="edit-btn" onclick="rateQuick('{lora['hash']}', 3)">3★</button>
                    <button class="edit-btn danger" onclick="rateQuick('{lora['hash']}', 1)">1★</button>
                </div>
                """
            
            card_events = f'onclick="selectLoRA({lora["index"]})"'
            if edit_mode:
                card_events += f' ondblclick="quickEdit(\'{lora["hash"]}\', \'{lora["name"]}\') \" onmouseenter="showEditControls({lora["index"]})" onmouseleave="hideEditControls({lora["index"]})"'
            
            html += f"""
                <div class="enhanced-card {selected_class} {edit_class}" {card_events} {trigger_tooltip}>
                    <div class="lora-index">{lora['index']}</div>
                    {badges_html}
                    {image_html}
                    <div class="lora-name">{lora['name']}</div>
                    {ratings_html}
                    {edit_controls}
                </div>
            """
        
        # Add edit panel and JavaScript
        html += f"""
            </div>
            
            <div class="selection-info">
                <span>Selected: <span id="selected-name">{lora_data[selected_index-1]['name'] if selected_index <= len(lora_data) else 'None'}</span></span>
                <span>
                    Use seed: <span id="selected-seed" style="font-weight: bold; color: #4a9eff;">{selected_index}</span>
                    <button onclick="copyToClipboard()" class="copy-btn" id="copy-btn">Copy Seed</button>
                </span>
            </div>
        </div>

        <!-- Edit Overlay and Panel -->
        <div class="edit-overlay" id="editOverlay" onclick="closeEditPanel()"></div>
        <div class="quick-edit-panel" id="editPanel">
            <h3 style="color: #fff; margin-top: 0;">Quick Edit LoRA</h3>
            <div class="edit-form" id="editForm">
                <label for="editArchitecture">Architecture:</label>
                <select id="editArchitecture">
                    <option value="SD1.5">SD1.5</option>
                    <option value="SDXL">SDXL</option>
                    <option value="Flux">Flux</option>
                    <option value="Pony">Pony</option>
                    <option value="Illustrious">Illustrious</option>
                    <option value="Noobai">Noobai</option>
                    <option value="SD3.5 Medium">SD3.5 Medium</option>
                    <option value="SD3.5 Large">SD3.5 Large</option>
                    <option value="Unknown">Unknown</option>
                </select>
                
                <label for="editCategory">Category:</label>
                <select id="editCategory">
                    <option value="style">Style</option>
                    <option value="character">Character</option>
                    <option value="concept">Concept</option>
                    <option value="pose">Pose</option>
                    <option value="clothing">Clothing</option>
                    <option value="background">Background</option>
                    <option value="effect">Effect</option>
                    <option value="tool">Tool</option>
                    <option value="unknown">Unknown</option>
                </select>
                
                <label for="editQuality">Quality Rating:</label>
                <select id="editQuality">
                    <option value="0">Not Rated</option>
                    <option value="1">1 Star</option>
                    <option value="2">2 Stars</option>
                    <option value="3">3 Stars</option>
                    <option value="4">4 Stars</option>
                    <option value="5">5 Stars</option>
                </select>
                
                <label for="editNotes">Quick Notes:</label>
                <textarea id="editNotes" rows="3" placeholder="Add your notes..."></textarea>
                
                <div class="edit-form-buttons">
                    <button class="edit-btn danger" onclick="closeEditPanel()">Cancel</button>
                    <button class="edit-btn success" onclick="saveEdit()">Save Changes</button>
                </div>
            </div>
        </div>

        <script>
            let currentSelection = {selected_index};
            let loraData = {json.dumps(lora_data, default=str)};
            let currentEditHash = null;
            let editMode = {str(edit_mode).lower()};
            
            function selectLoRA(index) {{
                document.querySelectorAll('.enhanced-card').forEach((card, i) => {{
                    const cardIndex = parseInt(card.querySelector('.lora-index').textContent);
                    card.classList.toggle('selected', cardIndex === index);
                }});
                
                currentSelection = index;
                const selectedLora = loraData.find(lora => lora.index === index);
                if (selectedLora) {{
                    document.getElementById('selected-name').textContent = selectedLora.name;
                    document.getElementById('selected-seed').textContent = index;
                }}
                
                console.log('Selected LoRA:', selectedLora ? selectedLora.name : 'Unknown', 'Seed:', index);
            }}
            
            function showEditControls(index) {{
                if (editMode) {{
                    const controls = document.getElementById('edit-controls-' + index);
                    if (controls) {{
                        controls.style.display = 'flex';
                    }}
                }}
            }}
            
            function hideEditControls(index) {{
                if (editMode) {{
                    const controls = document.getElementById('edit-controls-' + index);
                    if (controls) {{
                        controls.style.display = 'none';
                    }}
                }}
            }}
            
            function quickEdit(hash, name) {{
                currentEditHash = hash;
                const lora = loraData.find(l => l.hash === hash);
                if (!lora) return;
                
                // Populate form
                document.getElementById('editArchitecture').value = lora.architecture || 'Unknown';
                document.getElementById('editCategory').value = lora.category || 'unknown';
                document.getElementById('editQuality').value = lora.quality_rating || 0;
                document.getElementById('editNotes').value = lora.notes || '';
                
                // Show panel
                document.getElementById('editOverlay').style.display = 'block';
                document.getElementById('editPanel').style.display = 'block';
            }}
            
            function closeEditPanel() {{
                document.getElementById('editOverlay').style.display = 'none';
                document.getElementById('editPanel').style.display = 'none';
                currentEditHash = null;
            }}
            
            function saveEdit() {{
                if (!currentEditHash) return;
                
                // Note: In a real implementation, this would send the data to ComfyUI backend
                // For now, we'll just show a confirmation
                const changes = {{
                    hash: currentEditHash,
                    architecture: document.getElementById('editArchitecture').value,
                    category: document.getElementById('editCategory').value,
                    quality: parseInt(document.getElementById('editQuality').value),
                    notes: document.getElementById('editNotes').value
                }};
                
                console.log('Would save changes:', changes);
                alert('Edit functionality requires backend integration. Changes logged to console.');
                closeEditPanel();
            }}
            
            function rateQuick(hash, rating) {{
                console.log('Quick rate:', hash, rating, 'stars');
                // Update visual feedback
                const lora = loraData.find(l => l.hash === hash);
                if (lora) {{
                    lora.quality_rating = rating;
                    // Update display
                    const ratingElement = document.querySelector(`[data-hash="${{hash}}"].ratings`);
                    if (ratingElement) {{
                        const stars = '★'.repeat(rating);
                        ratingElement.innerHTML = `Q:${{stars}}`;
                    }}
                }}
                alert(`Rated LoRA ${{rating}} stars. Requires backend integration to save.`);
            }}
            
            function editArchitecture(event) {{
                event.stopPropagation();
                const current = event.target.dataset.current;
                const hash = event.target.dataset.hash;
                const newArch = prompt('Change architecture from ' + current + ' to:', current);
                if (newArch && newArch !== current) {{
                    console.log('Would change architecture:', hash, current, '->', newArch);
                    event.target.textContent = newArch;
                    alert('Architecture change requires backend integration to save.');
                }}
            }}
            
            function editCategory(event) {{
                event.stopPropagation();
                const current = event.target.dataset.current;
                const hash = event.target.dataset.hash;
                const newCat = prompt('Change category from ' + current + ' to:', current);
                if (newCat && newCat !== current) {{
                    console.log('Would change category:', hash, current, '->', newCat);
                    event.target.textContent = newCat;
                    alert('Category change requires backend integration to save.');
                }}
            }}
            
            function editRating(event) {{
                event.stopPropagation();
                const current = parseInt(event.target.dataset.current);
                const hash = event.target.dataset.hash;
                const newRating = prompt('Change rating (1-5):', current);
                if (newRating && !isNaN(newRating) && newRating >= 1 && newRating <= 5) {{
                    rateQuick(hash, parseInt(newRating));
                }}
            }}
            
            function copyToClipboard() {{
                const seedText = document.getElementById('selected-seed').textContent;
                const button = document.getElementById('copy-btn');
                
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    navigator.clipboard.writeText(seedText).then(() => {{
                        showCopyFeedback(button);
                    }}).catch(err => {{
                        fallbackCopyToClipboard(seedText, button);
                    }});
                }} else {{
                    fallbackCopyToClipboard(seedText, button);
                }}
            }}
            
            function fallbackCopyToClipboard(text, button) {{
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {{
                    document.execCommand('copy');
                    showCopyFeedback(button);
                }} catch (err) {{
                    console.error('Could not copy text: ', err);
                    alert('Copy failed. Seed number is: ' + text);
                }}
                
                document.body.removeChild(textArea);
            }}
            
            function showCopyFeedback(button) {{
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.classList.add('copied');
                
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.classList.remove('copied');
                }}, 1500);
            }}
            
            // Initialize
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('Enhanced LoRA Gallery initialized with', loraData.length, 'items');
                console.log('Edit mode:', editMode ? 'ENABLED' : 'DISABLED');
                
                const selectedCard = document.querySelector('.enhanced-card.selected');
                if (selectedCard) {{
                    selectedCard.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
                }}
            }});
        </script>
        """
        
        return html


# Node registration - this is how ComfyUI finds the nodes

NODE_CLASS_MAPPINGS = {
    "LoRATester_v03": LoRATesterNode,
    "LoRAInfoSetter_v03": LoRAInfoSetterNode,
    "LoRABatchInfoSetter_v03": LoRABatchInfoSetterNode,
    "LoRAParamsLoader_v03": LoRAParamsLoaderNode,
    "LoRAInfoViewer_v03": LoRAInfoViewerNode,
    "TriggerWordManager_v03": TriggerWordManagerNode,
    "LoRAQuickFeedback_v03": LoRAQuickFeedbackNode,
    "LoRAGalleryDisplay_v03": LoRAGalleryDisplayNode,
    "LoRAGalleryWithEdit_v03": LoRAGalleryWithEditNode,
    "LoRADatabaseStats_v03": LoRADatabaseStatsNode,
    "LoRADatabaseMaintenance_v03": LoRADatabaseMaintenanceNode,
    "LoRABulkOperations_v03": LoRABulkOperationsNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRATester_v03": "LoRA Tester v03",
    "LoRAInfoSetter_v03": "LoRA Info Setter v03",
    "LoRABatchInfoSetter_v03": "LoRA Batch Info Setter v03",
    "LoRAParamsLoader_v03": "LoRA Params Loader v03",
    "LoRAInfoViewer_v03": "LoRA Info Viewer v03",
    "TriggerWordManager_v03": "Trigger Word Manager v03",
    "LoRAQuickFeedback_v03": "LoRA Quick Feedback v03",
    "LoRAGalleryDisplay_v03": "LoRA Gallery Display v03",
    "LoRAGalleryWithEdit_v03": "LoRA Gallery with Edit v03",
    "LoRADatabaseStats_v03": "LoRA Database Stats v03",
    "LoRADatabaseMaintenance_v03": "LoRA Database Maintenance v03",
    "LoRABulkOperations_v03": "LoRA Bulk Operations v03"
}