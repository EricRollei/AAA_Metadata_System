"""
Multi-LoRA Loader Base Class
Provides common functionality for platform-specific LoRA loader nodes

This base class handles all the core LoRA loading logic, filtering, and database integration.
Platform-specific nodes inherit from this and specify their directory filters and requirements.

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
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
import json
import hashlib
import glob
import requests
from typing import Dict, List, Tuple, Optional, Any
import folder_paths
import comfy.sd
import comfy.utils

from custom_nodes.AAA_Metadata_System.eric_metadata.utils.hash_utils import hash_file_sha256


class MultiLoRALoaderBase:
    """
    Base class for multi-LoRA loader nodes with search and filtering capabilities.
    Platform-specific nodes should inherit from this class.
    """
    
    # Platform-specific configuration (override in subclasses)
    PLATFORM_NAME = "Generic"
    PLATFORM_DIRECTORY_FILTER = ""  # Subdirectory to filter (e.g., "Wan\\i2v")
    REQUIRES_CLIP = True  # Set to False for video/diffusion models
    DEFAULT_ARCHITECTURE = "Unknown"
    MAX_LORA_SLOTS = 8
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        
        # Civitai integration settings
        self.civitai_cache_file = os.path.join(os.path.dirname(__file__), "civitai_cache.json")
        self.civitai_cache = self._load_civitai_cache()
        
        # Lists to store paths and filtered LoRAs
        self.lora_paths = []
        self.filtered_loras = []
        
        # Architecture detection patterns
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
            },
            "Wan": {
                "patterns": ["wan", "wanvideo", "wan2", "wan-2"],
                "defaults": {"model": 1.0, "clip": 0.0}
            }
        }
        
        # Initial scan of available LoRAs with platform filter
        self.scan_loras()
    
    # Class-level cache for platform-filtered LoRAs - shared across all subclasses
    _lora_cache = {}
    _lora_cache_logged = set()
    _startup_complete = False
    
    @classmethod
    def _get_platform_filtered_loras(cls):
        """Get LoRAs filtered by platform directory - uses ComfyUI's built-in caching when possible"""
        cache_key = cls.PLATFORM_DIRECTORY_FILTER or "all"
        
        # Use ComfyUI's built-in lora list for faster startup
        if cache_key not in cls._lora_cache:
            try:
                # Get ComfyUI's cached lora list (much faster than scanning ourselves)
                all_loras = folder_paths.get_filename_list("loras")
                
                if cls.PLATFORM_DIRECTORY_FILTER:
                    # Filter to only include LoRAs from the platform directory
                    filter_path = cls.PLATFORM_DIRECTORY_FILTER.replace("\\", "/").lower()
                    filtered = [
                        lora for lora in all_loras 
                        if filter_path in lora.replace("\\", "/").lower()
                    ]
                    cls._lora_cache[cache_key] = filtered
                else:
                    cls._lora_cache[cache_key] = list(all_loras)
                
                # Only log once per platform, and only after startup
                if cache_key not in cls._lora_cache_logged:
                    count = len(cls._lora_cache[cache_key])
                    if count == 0 and cls.PLATFORM_DIRECTORY_FILTER:
                        print(f"[{cls.PLATFORM_NAME}] No LoRAs found in {cls.PLATFORM_DIRECTORY_FILTER} directory")
                    cls._lora_cache_logged.add(cache_key)
                    
            except Exception as e:
                print(f"[{cls.PLATFORM_NAME}] Error getting LoRA list: {e}")
                cls._lora_cache[cache_key] = []
        
        return cls._lora_cache[cache_key]
    
    @classmethod
    def clear_lora_cache(cls):
        """Clear the LoRA cache to force a rescan"""
        cls._lora_cache.clear()
        cls._lora_cache_logged.clear()
    
    def _load_lora_db(self) -> Dict:
        """Load LoRA database from JSON file"""
        try:
            if os.path.exists(self.lora_db_path):
                with open(self.lora_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        except Exception as e:
            print(f"[{self.PLATFORM_NAME}] Error loading LoRA database: {e}")
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def scan_loras(self, additional_path: str = ""):
        """Scan for LoRA files with platform-specific filtering"""
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
        
        temp_lora_paths = set()
        
        for directory in unique_scan_dirs:
            if not os.path.isdir(directory):
                continue
            
            # Apply platform directory filter if specified
            if self.PLATFORM_DIRECTORY_FILTER:
                # Check if this directory or any subdirectory matches the platform filter
                platform_path = os.path.join(directory, self.PLATFORM_DIRECTORY_FILTER)
                if os.path.isdir(platform_path):
                    scan_dir = platform_path
                else:
                    # Skip this directory if platform subdirectory doesn't exist
                    continue
            else:
                scan_dir = directory
            
            for ext in extensions:
                pattern = os.path.join(scan_dir, f"**/*{ext}")
                try:
                    found_files = glob.glob(pattern, recursive=True)
                    for file_path in found_files:
                        temp_lora_paths.add(os.path.normpath(file_path))
                except Exception as e:
                    print(f"[{self.PLATFORM_NAME}] Error scanning directory {scan_dir} with pattern {pattern}: {e}")
        
        self.lora_paths = sorted(list(temp_lora_paths))
        # Note: Logging is handled by _get_platform_filtered_loras to avoid spam
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier"""
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
    
    def _detect_architecture_from_path(self, lora_path: str) -> str:
        """Detect LoRA architecture from path and filename"""
        path_lower = lora_path.lower()
        
        for arch, arch_data in self.known_architectures.items():
            for pattern in arch_data["patterns"]:
                if pattern in path_lower:
                    return arch
        
        return self.DEFAULT_ARCHITECTURE
    
    def _get_available_loras(self) -> List[str]:
        """Get list of available LoRA filenames for dropdowns"""
        return [os.path.basename(path) for path in self.lora_paths]
    
    def _get_lora_info(self, lora_name: str, query_civitai: bool = False, force_fetch: bool = False) -> Dict:
        """Get LoRA information from database with optional Civitai querying"""
        # Find the full path for this LoRA name
        lora_path = self._find_lora_path(lora_name)
        if not lora_path:
            return {"hash": "", "architecture": "Unknown", "category": "unknown", "triggers": []}
        
        # Calculate hash and get database info
        lora_hash = self._calculate_lora_hash(lora_path)
        
        # Look up in database
        if lora_hash in self.lora_db.get("loras", {}):
            db_info = self.lora_db["loras"][lora_hash]
            
            # Get existing trigger words
            full_list = db_info.get("trigger_words", {}).get("full_list", [])
            selected_list = db_info.get("trigger_words", {}).get("selected", [])
            
            # Query Civitai if enabled and no tags exist, or if force fetch is enabled
            if query_civitai and (not full_list or force_fetch):
                civitai_tags = self._fetch_civitai_tags(lora_path, force_fetch)
                if civitai_tags:
                    full_list = civitai_tags
                    # If we got new tags and no selection exists, use first tag as selected
                    if not selected_list and civitai_tags:
                        selected_list = [civitai_tags[0]]
            
            return {
                "hash": lora_hash,
                "architecture": db_info.get("architecture", "Unknown"),
                "category": db_info.get("category", "unknown"),
                "triggers": full_list,
                "selected_triggers": selected_list
            }
        
        # If not found in database, create new entry and optionally query Civitai
        architecture = self._detect_architecture_from_path(lora_path)
        triggers = []
        
        if query_civitai:
            triggers = self._fetch_civitai_tags(lora_path, force_fetch)
        
        return {
            "hash": lora_hash,
            "architecture": architecture,
            "category": "unknown",
            "triggers": triggers,
            "selected_triggers": triggers[:1] if triggers else []
        }
    
    def _find_lora_path(self, lora_name: str) -> Optional[str]:
        """Find full path to LoRA file by filename"""
        for path in self.lora_paths:
            if os.path.basename(path) == lora_name:
                return path
        return None
    
    def _filter_loras(self, search_filename: str, search_category: str,
                     search_trigger_word: str, min_rating: int) -> List[str]:
        """Filter LoRAs based on search criteria (directory filter already applied by platform)"""
        
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
        file_include, file_exclude = parse_search_terms(search_filename)
        trigger_include, trigger_exclude = parse_search_terms(search_trigger_word)
        
        # Start with platform-filtered LoRAs
        filtered = self.lora_paths
        
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
        
        # Apply category filter
        if search_category != "Any":
            category_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db.get("loras", {}):
                    lora_category = self.lora_db["loras"][lora_hash].get("category", "unknown")
                    if lora_category.lower() == search_category.lower():
                        category_filtered.append(lora_path)
            filtered = category_filtered
        
        # Apply trigger word search with includes/excludes
        if trigger_include or trigger_exclude:
            trigger_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db.get("loras", {}):
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
        
        # Apply rating filter
        if min_rating > 0:
            temp_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db.get("loras", {}):
                    rating = self.lora_db["loras"][lora_hash].get("user_feedback", {}).get("quality_rating", 0)
                    if rating >= min_rating:
                        temp_filtered.append(lora_path)
            filtered = temp_filtered
        
        self.filtered_loras = filtered
        return filtered
    
    def _update_lora_usage(self, lora_hash: str, lora_name: str, strength: float, clip_strength: float = 0.0):
        """Update LoRA usage statistics in database"""
        try:
            if lora_hash in self.lora_db.get("loras", {}):
                lora_entry = self.lora_db["loras"][lora_hash]
                
                # Initialize usage statistics if not present
                if "user_feedback" not in lora_entry:
                    lora_entry["user_feedback"] = {}
                
                # Update usage count
                if "usage_count" not in lora_entry["user_feedback"]:
                    lora_entry["user_feedback"]["usage_count"] = 0
                lora_entry["user_feedback"]["usage_count"] += 1
                
                # Update last used info
                lora_entry["user_feedback"]["last_used"] = str(int(os.path.getmtime(__file__)))
                lora_entry["user_feedback"]["last_strength"] = strength
                if self.REQUIRES_CLIP:
                    lora_entry["user_feedback"]["last_clip_strength"] = clip_strength
                
                # Save updated database
                with open(self.lora_db_path, 'w', encoding='utf-8') as f:
                    json.dump(self.lora_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[{self.PLATFORM_NAME}] Error updating LoRA usage: {e}")
    
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
            print(f"[{self.PLATFORM_NAME}] Warning: Could not save Civitai cache: {e}")

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash for Civitai API lookup using cached helper."""
        digest = hash_file_sha256(file_path)
        if digest is None:
            print(f"[{self.PLATFORM_NAME}] Error calculating SHA256 for {file_path}: unable to read file")
            return ""
        return digest

    def _get_civitai_model_info(self, sha256_hash: str) -> Optional[Dict]:
        """Query Civitai API for model information."""
        # Check cache first
        if sha256_hash in self.civitai_cache:
            print(f"[{self.PLATFORM_NAME}] Using cached Civitai data for hash {sha256_hash[:8]}...")
            return self.civitai_cache[sha256_hash]
        
        try:
            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256_hash}"
            print(f"[{self.PLATFORM_NAME}] Querying Civitai API for hash {sha256_hash[:8]}...")
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                model_info = response.json()
                # Cache the result
                self.civitai_cache[sha256_hash] = model_info
                self._save_civitai_cache()
                print(f"[{self.PLATFORM_NAME}] Successfully retrieved Civitai data")
                return model_info
            elif response.status_code == 404:
                # Cache negative result to avoid repeated queries
                self.civitai_cache[sha256_hash] = None
                self._save_civitai_cache()
                print(f"[{self.PLATFORM_NAME}] LoRA not found on Civitai")
                return None
            else:
                print(f"[{self.PLATFORM_NAME}] Civitai API returned status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"[{self.PLATFORM_NAME}] Error querying Civitai API: {e}")
            return None

    def _fetch_civitai_tags(self, lora_path: str, force_fetch: bool = False) -> List[str]:
        """Fetch trigger words from Civitai for a specific LoRA."""
        lora_hash = self._calculate_lora_hash(lora_path)
        
        # Check if we already have tags and don't need to force fetch
        if not force_fetch and lora_hash in self.lora_db.get("loras", {}):
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
            print(f"[{self.PLATFORM_NAME}] Found {len(tags)} trigger words from Civitai")
            
            # Update database
            if lora_hash not in self.lora_db.get("loras", {}):
                # Initialize entry if it doesn't exist
                self.lora_db["loras"][lora_hash] = {
                    "path": lora_path,
                    "name": os.path.basename(lora_path),
                    "architecture": self._detect_architecture_from_path(lora_path),
                    "category": "unknown",
                    "notes": "",
                    "trigger_words": {
                        "full_list": [],
                        "selected": [],
                        "imported_from": ""
                    }
                }
            
            if lora_hash in self.lora_db["loras"]:
                self.lora_db["loras"][lora_hash]["trigger_words"]["full_list"] = tags
                self.lora_db["loras"][lora_hash]["trigger_words"]["imported_from"] = "civitai"
                # If no selected triggers, use first one
                if not self.lora_db["loras"][lora_hash]["trigger_words"]["selected"] and tags:
                    self.lora_db["loras"][lora_hash]["trigger_words"]["selected"] = [tags[0]]
                self._save_lora_db()
            
            return tags
        else:
            print(f"[{self.PLATFORM_NAME}] No trigger words found on Civitai")
            # Mark as queried to avoid repeated attempts
            if lora_hash in self.lora_db.get("loras", {}):
                self.lora_db["loras"][lora_hash]["trigger_words"]["imported_from"] = "civitai_not_found"
                self._save_lora_db()
            
            return []

    def _save_lora_db(self):
        """Save the LoRA database to disk."""
        try:
            with open(self.lora_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.lora_db, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[{self.PLATFORM_NAME}] Warning: Could not save LoRA database: {e}")

    def _create_filtered_lora_list(self, search_filename: str, search_category: str,
                                  search_trigger_word: str, min_rating: int,
                                  query_civitai: bool = False, force_civitai_fetch: bool = False) -> str:
        """Create a formatted list of filtered LoRAs for user reference"""
        filtered_lora_paths = self._filter_loras(
            search_filename, search_category,
            search_trigger_word, min_rating
        )
        
        if not filtered_lora_paths:
            return f"No LoRAs match the current filters in {self.PLATFORM_NAME}"
        
        # Create a formatted list with basic info
        lora_list = []
        civitai_queries = 0
        
        for lora_path in filtered_lora_paths[:50]:  # Limit to first 50
            lora_name = os.path.basename(lora_path)
            lora_info = self._get_lora_info(lora_name, query_civitai, force_civitai_fetch)
            
            # Track Civitai queries
            if query_civitai and not lora_info.get("triggers"):
                civitai_queries += 1
                
            arch = lora_info.get("architecture", "Unknown")
            category = lora_info.get("category", "unknown")
            triggers = lora_info.get("triggers", [])
            trigger_preview = ", ".join(triggers[:3]) if triggers else "No triggers"
            if len(triggers) > 3:
                trigger_preview += f" (+ {len(triggers) - 3} more)"
            
            # Show relative path
            try:
                if self.PLATFORM_DIRECTORY_FILTER:
                    # Show path relative to platform directory
                    platform_idx = lora_path.lower().find(self.PLATFORM_DIRECTORY_FILTER.lower())
                    if platform_idx >= 0:
                        rel_path = lora_path[platform_idx:]
                    else:
                        rel_path = os.path.basename(lora_path)
                else:
                    rel_path = lora_path
            except:
                rel_path = os.path.basename(lora_path)
            
            lora_list.append(f"• {lora_name}")
            lora_list.append(f"  Path: {rel_path}")
            lora_list.append(f"  Info: [{arch}] ({category}) - Triggers: {trigger_preview}")
            lora_list.append("")
        
        if len(filtered_lora_paths) > 50:
            lora_list.append(f"... and {len(filtered_lora_paths) - 50} more LoRAs")
        
        # Add Civitai query info
        if query_civitai and civitai_queries > 0:
            lora_list.append("")
            lora_list.append(f"🌐 Civitai queries performed: {civitai_queries}")
            if force_civitai_fetch:
                lora_list.append("🔄 Force fetch enabled - existing triggers may have been updated")
        
        return "\n".join(lora_list)
