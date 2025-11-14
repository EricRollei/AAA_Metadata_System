"""
Multi-LoRA Loader Node - Model Only Version
A model-only multi-LoRA loader for use with diffusion models like Wan Video that don't use CLIP
This version removes CLIP input/output and clip_strength parameters

Based on Multi_LoRA_Loader_v02.py
"""

import os
import json
import re
import hashlib
import glob
import requests
from typing import Dict, List, Tuple, Optional, Any
import folder_paths
import comfy.sd
import comfy.utils

class MultiLoRALoaderModelOnly:
    """
    Multi-LoRA loader node (MODEL ONLY) that can load up to 8 LoRAs with search/filter capabilities.
    Integrates with LoRA Tester database for metadata and trigger words.
    No CLIP input/output - designed for diffusion models and video models like Wan Video.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available LoRAs - this will be the full list since we can't dynamically filter dropdowns
        # The filtering will happen at execution time and be displayed in the filter_info output
        try:
            instance = cls()
            all_loras = instance._get_available_loras()
            lora_options = ["None"] + all_loras
        except Exception as e:
            print(f"Error getting LoRA options: {e}")
            lora_options = ["None"]
        
        return {
            "required": {
                "model": ("MODEL",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                
                # Master search and filter controls
                "search_directory": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in directory/path names. Use commas to separate multiple terms."}),
                "search_filename": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in LoRA filenames. Use commas to separate multiple terms."}),
                "search_category": (["Any", "unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "graphic", "treatment", "tool", "slider", "anime", "realism", 
                    "details", "lighting", "mood", "texture", "fantasy", "scifi", 
                    "historical", "nsfw", "enhancement"], {"default": "Any"}),
                "search_trigger_word": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in trigger words from database. Use commas to separate multiple terms."}),
                "filter_architecture": (["Any", "Unknown", "SD1.5", "SDXL", "Flux", "Pony", 
                    "Illustrious", "Noobai", "SD3.5 Medium", "SD3.5 Large", "HiDream", 
                    "Stable Cascade", "PixArt Sigma", "Playground"], {"default": "Any"}),
                "min_rating": ("INT", {"default": 0, "min": 0, "max": 5,
                    "tooltip": "Minimum quality rating from database (0 = show all)"}),
                
                # Refresh control
                "refresh_lists": ("BOOLEAN", {"default": False,
                    "tooltip": "Toggle to refresh. Filters are applied during execution - check filter_info output to see results."}),
                
                # Civitai integration
                "query_civitai": ("BOOLEAN", {"default": False,
                    "tooltip": "Automatically query Civitai for trigger words when LoRA has none"}),
                "force_civitai_fetch": ("BOOLEAN", {"default": False,
                    "tooltip": "Force fetch from Civitai even if tags already exist"}),
                
                # Trigger word settings
                "trigger_position": (["front", "back"], {"default": "front"}),
                "trigger_separator": ("STRING", {"default": ", "}),
                
                # LoRA slot 1 - MODEL ONLY
                "lora_1_enable": ("BOOLEAN", {"default": False}),
                "lora_1_name": (lora_options, {"default": "None"}),
                "lora_1_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 2 - MODEL ONLY
                "lora_2_enable": ("BOOLEAN", {"default": False}),
                "lora_2_name": (lora_options, {"default": "None"}),
                "lora_2_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 3 - MODEL ONLY
                "lora_3_enable": ("BOOLEAN", {"default": False}),
                "lora_3_name": (lora_options, {"default": "None"}),
                "lora_3_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 4 - MODEL ONLY
                "lora_4_enable": ("BOOLEAN", {"default": False}),
                "lora_4_name": (lora_options, {"default": "None"}),
                "lora_4_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 5 - MODEL ONLY
                "lora_5_enable": ("BOOLEAN", {"default": False}),
                "lora_5_name": (lora_options, {"default": "None"}),
                "lora_5_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 6 - MODEL ONLY
                "lora_6_enable": ("BOOLEAN", {"default": False}),
                "lora_6_name": (lora_options, {"default": "None"}),
                "lora_6_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 7 - MODEL ONLY
                "lora_7_enable": ("BOOLEAN", {"default": False}),
                "lora_7_name": (lora_options, {"default": "None"}),
                "lora_7_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA slot 8 - MODEL ONLY
                "lora_8_enable": ("BOOLEAN", {"default": False}),
                "lora_8_name": (lora_options, {"default": "None"}),
                "lora_8_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            }
        }
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Trigger update when search parameters or refresh toggle changes
        search_params = [
            kwargs.get('search_directory', ''),
            kwargs.get('search_filename', ''),
            kwargs.get('search_category', 'Any'),
            kwargs.get('search_trigger_word', ''),
            kwargs.get('filter_architecture', 'Any'),
            kwargs.get('min_rating', 0),
            kwargs.get('refresh_lists', False),
            kwargs.get('query_civitai', False),
            kwargs.get('force_civitai_fetch', False)
        ]
        return str(search_params) + str(hash(str(search_params)))
    
    RETURN_TYPES = ("MODEL", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model", "prompt", "prompt_with_triggers", "loaded_loras_info", "all_trigger_words", "filter_info", "filtered_loras_list")
    FUNCTION = "load_multi_loras"
    CATEGORY = "loaders/multi-lora"
    
    def __init__(self):
        self.lora_db_path = os.path.join(os.path.dirname(__file__), "lora_tester_db.json")
        self.lora_db = self._load_lora_db()
        
        # Add Civitai integration settings
        self.civitai_cache_file = os.path.join(os.path.dirname(__file__), "civitai_cache.json")
        self.civitai_cache = self._load_civitai_cache()
        
        # Lists to store paths and filtered LoRAs (like LoRA Tester)
        self.lora_paths = []
        self.filtered_loras = []
        
        # Architecture detection patterns (from LoRA Tester)
        self.known_architectures = {
            "SD1.5": {
                "patterns": ["sd1.5", "sd15", "sd-1-5", "stable-diffusion-v1", "v1-5", "sd_v1", "sd1", "sd_1"],
                "defaults": {"model": 0.75}
            },
            "SD2.1": {
                "patterns": ["sd2.1", "sd21", "sd-2-1", "stable-diffusion-v2", "v2-1", "sd2", "v2", "sd_2"],
                "defaults": {"model": 0.75}
            },
            "SDXL": {
                "patterns": ["sdxl", "sd-xl", "stable-diffusion-xl", "sd_xl", "xl_base", "SDXL", "XL_"],
                "defaults": {"model": 0.7}
            },
            "SD3.5 Medium": {
                "patterns": ["sd3.5", "sd35", "sd35medium", "medium", "sd3-medium"],
                "defaults": {"model": 0.66}
            },
            "SD3.5 Large": {
                "patterns": ["sd3.5", "sd35", "sd35large", "large", "sd3-large"],
                "defaults": {"model": 0.66}
            },
            "Flux": {
                "patterns": ["flux", "FLUX", "Flux1", "flux1d", "flux-1d", "flux_1d"],
                "defaults": {"model": 0.8}
            },
            "Pony": {
                "patterns": ["pony", "PONY", "Pony", "ponyV1"],
                "defaults": {"model": 0.75}
            },
            "Illustrious": {
                "patterns": ["illustrious", "illustrious-xl"],
                "defaults": {"model": 0.7}
            },
            "Noobai": {
                "patterns": ["noobai", "noobai-xl"],
                "defaults": {"model": 0.7}
            },
            "HiDream": {
                "patterns": ["hidream", "HiDream"],
                "defaults": {"model": 0.8}
            },
            "Stable Cascade": {
                "patterns": ["cascade", "stable-cascade"],
                "defaults": {"model": 0.8}
            },
            "PixArt Sigma": {
                "patterns": ["pixart", "pixart-sigma"],
                "defaults": {"model": 0.8}
            },
            "Playground": {
                "patterns": ["playground", "playground-v2"],
                "defaults": {"model": 0.7}
            }
        }
        
        # Initial scan of available LoRAs (like LoRA Tester)
        self.scan_loras()
    
    def _load_lora_db(self) -> Dict:
        """Load LoRA database from JSON file"""
        try:
            if os.path.exists(self.lora_db_path):
                with open(self.lora_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
        except Exception as e:
            print(f"Error loading LoRA database: {e}")
            return {"loras": {}, "version": "1.0", "current_index": 0, "tags_imported": False}
    
    def scan_loras(self, additional_path: str = ""):
        """Scan for LoRA files in the filesystem (from LoRA Tester)."""
        import glob
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
                    print(f"[MultiLoRA-ModelOnly] Error scanning directory {directory} with pattern {pattern}: {e}")
        
        self.lora_paths = sorted(list(temp_lora_paths))
    
    def _calculate_lora_hash(self, file_path: str) -> str:
        """Calculate a hash for the LoRA to use as a unique identifier (from LoRA Tester)."""
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
        """Detect LoRA architecture from path and filename (from LoRA Tester)."""
        path_lower = lora_path.lower()
        
        for arch, arch_data in self.known_architectures.items():
            for pattern in arch_data["patterns"]:
                if pattern in path_lower:
                    return arch
        
        return "Unknown"
    
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
    
    def _filter_loras(self, search_directory: str, search_filename: str, search_category: str,
                     search_trigger_word: str, filter_architecture: str, min_rating: int) -> List[str]:
        """Filter LoRAs based on search criteria (adapted from LoRA Tester)"""
        
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
        dir_include, dir_exclude = parse_search_terms(search_directory)
        file_include, file_exclude = parse_search_terms(search_filename)
        trigger_include, trigger_exclude = parse_search_terms(search_trigger_word)
        
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
        if filter_architecture != "Any":
            arch_filtered = []
            for lora_path in filtered:
                lora_hash = self._calculate_lora_hash(lora_path)
                if lora_hash in self.lora_db.get("loras", {}):
                    lora_arch = self.lora_db["loras"][lora_hash]["architecture"]
                    if lora_arch == filter_architecture:
                        arch_filtered.append(lora_path)
                else:
                    # Try to detect architecture from path if not in database
                    detected_arch = self._detect_architecture_from_path(lora_path)
                    if detected_arch == filter_architecture:
                        arch_filtered.append(lora_path)
            filtered = arch_filtered
        
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
        
        # Apply rating filter (simplified for now)
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
    
    def _update_lora_usage(self, lora_hash: str, lora_name: str, strength: float):
        """Update LoRA usage statistics in database (model-only version)"""
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
                
                # Save updated database
                with open(self.lora_db_path, 'w', encoding='utf-8') as f:
                    json.dump(self.lora_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error updating LoRA usage: {e}")
    
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
            print(f"[MultiLoRA-ModelOnly] Warning: Could not save Civitai cache: {e}")

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash for Civitai API lookup."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[MultiLoRA-ModelOnly] Error calculating SHA256 for {file_path}: {e}")
            return ""

    def _get_civitai_model_info(self, sha256_hash: str) -> Optional[Dict]:
        """Query Civitai API for model information."""
        # Check cache first
        if sha256_hash in self.civitai_cache:
            print(f"[MultiLoRA-ModelOnly] Using cached Civitai data for hash {sha256_hash[:8]}...")
            return self.civitai_cache[sha256_hash]
        
        try:
            api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256_hash}"
            print(f"[MultiLoRA-ModelOnly] Querying Civitai API for hash {sha256_hash[:8]}...")
            
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                model_info = response.json()
                # Cache the result
                self.civitai_cache[sha256_hash] = model_info
                self._save_civitai_cache()
                print(f"[MultiLoRA-ModelOnly] Successfully retrieved Civitai data")
                return model_info
            elif response.status_code == 404:
                # Cache negative result to avoid repeated queries
                self.civitai_cache[sha256_hash] = None
                self._save_civitai_cache()
                print(f"[MultiLoRA-ModelOnly] LoRA not found on Civitai")
                return None
            else:
                print(f"[MultiLoRA-ModelOnly] Civitai API returned status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"[MultiLoRA-ModelOnly] Error querying Civitai API: {e}")
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
            print(f"[MultiLoRA-ModelOnly] Found {len(tags)} trigger words from Civitai")
            
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
            print(f"[MultiLoRA-ModelOnly] No trigger words found on Civitai")
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
            print(f"[MultiLoRA-ModelOnly] Warning: Could not save LoRA database: {e}")

    def load_multi_loras(self, model, prompt: str, 
                        search_directory: str, search_filename: str, search_category: str,
                        search_trigger_word: str, filter_architecture: str, min_rating: int,
                        refresh_lists: bool, query_civitai: bool, force_civitai_fetch: bool,
                        trigger_position: str, trigger_separator: str,
                        # LoRA parameters (MODEL ONLY - no clip_strength)
                        lora_1_enable: bool, lora_1_name: str, lora_1_strength: float,
                        lora_2_enable: bool, lora_2_name: str, lora_2_strength: float,
                        lora_3_enable: bool, lora_3_name: str, lora_3_strength: float,
                        lora_4_enable: bool, lora_4_name: str, lora_4_strength: float,
                        lora_5_enable: bool, lora_5_name: str, lora_5_strength: float,
                        lora_6_enable: bool, lora_6_name: str, lora_6_strength: float,
                        lora_7_enable: bool, lora_7_name: str, lora_7_strength: float,
                        lora_8_enable: bool, lora_8_name: str, lora_8_strength: float
                        ) -> Tuple[Any, str, str, str, str, str, str]:
        """Load multiple LoRAs for model only (no CLIP)"""
        
        # Get filtered LoRAs info for display
        filtered_lora_paths = self._filter_loras(
            search_directory, search_filename, search_category,
            search_trigger_word, filter_architecture, min_rating
        )
        
        # Convert paths to filenames for comparison
        filtered_lora_names = [os.path.basename(path) for path in filtered_lora_paths]
        
        # Create filtered LoRA list for user reference
        filtered_loras_list = self._create_filtered_lora_list(
            search_directory, search_filename, search_category,
            search_trigger_word, filter_architecture, min_rating, query_civitai, force_civitai_fetch
        )
        
        # Create detailed filter info
        active_filters = []
        if search_directory.strip():
            active_filters.append(f"Directory: '{search_directory}'")
        if search_filename.strip():
            active_filters.append(f"Filename: '{search_filename}'")
        if search_category != "Any":
            active_filters.append(f"Category: {search_category}")
        if filter_architecture != "Any":
            active_filters.append(f"Architecture: {filter_architecture}")
        if min_rating > 0:
            active_filters.append(f"Min Rating: {min_rating}")
        if search_trigger_word.strip():
            active_filters.append(f"Trigger: '{search_trigger_word}'")
        
        if active_filters:
            filter_info = f"ACTIVE FILTERS: {' | '.join(active_filters)} | Found {len(filtered_lora_paths)} of {len(self.lora_paths)} LoRAs"
        else:
            filter_info = f"NO FILTERS ACTIVE | All {len(self.lora_paths)} LoRAs available"
        
        # Collect all LoRA configurations (MODEL ONLY)
        lora_configs = [
            (lora_1_enable, lora_1_name, lora_1_strength),
            (lora_2_enable, lora_2_name, lora_2_strength),
            (lora_3_enable, lora_3_name, lora_3_strength),
            (lora_4_enable, lora_4_name, lora_4_strength),
            (lora_5_enable, lora_5_name, lora_5_strength),
            (lora_6_enable, lora_6_name, lora_6_strength),
            (lora_7_enable, lora_7_name, lora_7_strength),
            (lora_8_enable, lora_8_name, lora_8_strength)
        ]
        
        # Validate selected LoRAs against filters
        warnings = []
        for i, (enabled, name, strength) in enumerate(lora_configs, 1):
            if enabled and name != "None":
                if name not in filtered_lora_names and active_filters:
                    warnings.append(f"LoRA {i} '{name}' doesn't match current filters")
        
        if warnings:
            filter_info += f" | WARNINGS: {'; '.join(warnings)}"
        
        # Process each enabled LoRA (MODEL ONLY)
        current_model = model
        loaded_loras = []
        all_triggers = []
        
        for i, (enabled, name, strength) in enumerate(lora_configs, 1):
            if not enabled or name == "None":
                continue
            
            # Find and load the LoRA
            lora_path = self._find_lora_path(name)
            if not lora_path:
                print(f"Warning: LoRA '{name}' not found, skipping slot {i}")
                continue
            
            try:
                # Load the LoRA for model only
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                
                # Create a dummy clip for the load_lora_for_models function
                # We'll discard it after loading
                dummy_clip = None  # We pass None for clip
                current_model, _ = comfy.sd.load_lora_for_models(
                    current_model, dummy_clip, lora, strength, 0.0
                )
                
                # Get LoRA info and update database
                lora_info = self._get_lora_info(name, query_civitai, force_civitai_fetch)
                self._update_lora_usage(lora_info["hash"], name, strength)
                
                # Collect loaded LoRA info
                loaded_loras.append({
                    "slot": i,
                    "name": name,
                    "strength": strength,
                    "architecture": lora_info.get("architecture", "Unknown"),
                    "category": lora_info.get("category", "unknown"),
                    "triggers": lora_info.get("triggers", [])
                })
                
                # Collect trigger words
                triggers = lora_info.get("selected_triggers", [])
                if not triggers:
                    triggers = lora_info.get("triggers", [])
                all_triggers.extend(triggers)
                
                print(f"Loaded LoRA {i}: {name} (model strength: {strength})")
                
            except Exception as e:
                print(f"Error loading LoRA '{name}' in slot {i}: {str(e)}")
                continue
        
        # Create loaded LoRAs info string
        loaded_info_lines = []
        for lora in loaded_loras:
            loaded_info_lines.append(
                f"Slot {lora['slot']}: {lora['name']} "
                f"[{lora['architecture']}] ({lora['category']}) "
                f"- Model Strength: {lora['strength']:.2f}"
            )
        
        loaded_loras_info = "\n".join(loaded_info_lines) if loaded_info_lines else "No LoRAs loaded"
        
        # Create combined trigger words string
        unique_triggers = []
        for trigger in all_triggers:
            if trigger not in unique_triggers:
                unique_triggers.append(trigger)
        
        all_trigger_words = trigger_separator.join(unique_triggers)
        
        # Create prompt with triggers
        prompt_with_triggers = prompt
        if unique_triggers:
            if trigger_position == "front":
                prompt_with_triggers = all_trigger_words + trigger_separator + prompt
            else:
                prompt_with_triggers = prompt + trigger_separator + all_trigger_words
        
        return (current_model, prompt, prompt_with_triggers, loaded_loras_info, all_trigger_words, filter_info, filtered_loras_list)
    
    def _create_filtered_lora_list(self, search_directory: str, search_filename: str, search_category: str,
                                  search_trigger_word: str, filter_architecture: str, min_rating: int,
                                  query_civitai: bool = False, force_civitai_fetch: bool = False) -> str:
        """Create a formatted list of filtered LoRAs for user reference"""
        filtered_lora_paths = self._filter_loras(
            search_directory, search_filename, search_category,
            search_trigger_word, filter_architecture, min_rating
        )
        
        if not filtered_lora_paths:
            return "No LoRAs match the current filters"
        
        # Create a formatted list with basic info
        lora_list = []
        civitai_queries = 0
        
        for lora_path in filtered_lora_paths[:50]:  # Limit to first 50 to avoid overwhelming output
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
            
            # Show relative path for context (handle cross-drive paths on Windows)
            try:
                if folder_paths.get_folder_paths("loras"):
                    base_path = folder_paths.get_folder_paths("loras")[0]
                    # Check if paths are on the same drive on Windows
                    if os.name == 'nt':  # Windows
                        lora_drive = os.path.splitdrive(lora_path)[0]
                        base_drive = os.path.splitdrive(base_path)[0]
                        if lora_drive.lower() == base_drive.lower():
                            rel_path = os.path.relpath(lora_path, base_path)
                        else:
                            # Different drives, just show the path from the drive root
                            rel_path = lora_path
                    else:
                        # Non-Windows, should work normally
                        rel_path = os.path.relpath(lora_path, base_path)
                else:
                    rel_path = lora_path
            except (ValueError, OSError):
                # Fallback to full path if relative path calculation fails
                rel_path = lora_path
            
            lora_list.append(f"• {lora_name}")
            lora_list.append(f"  Path: {rel_path}")
            lora_list.append(f"  Info: [{arch}] ({category}) - Triggers: {trigger_preview}")
            lora_list.append("")  # Empty line for readability
        
        if len(filtered_lora_paths) > 50:
            lora_list.append(f"... and {len(filtered_lora_paths) - 50} more LoRAs")
        
        # Add Civitai query info if enabled
        if query_civitai and civitai_queries > 0:
            lora_list.append("")
            lora_list.append(f"🌐 Civitai queries performed: {civitai_queries}")
            if force_civitai_fetch:
                lora_list.append("🔄 Force fetch enabled - existing triggers may have been updated")
        
        return "\n".join(lora_list)


# Node registration
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader Model-Only": MultiLoRALoaderModelOnly,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Multi-LoRA Loader Model-Only": "Multi-LoRA Loader (Model Only)",
}
