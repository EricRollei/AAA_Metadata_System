"""
ComfyUI Node: checkpoint_tester_node_v074.py
Description: This node allows users to test multiple checkpoint models with flexible filtering options.
It supports searching by directory name, filtering by filename, and filtering by model architecture type (SD1.5, SDXL, etc.).
It also provides count statistics of available and filtered checkpoints, outputs a text list of selected checkpoints, and runs batch processing with sequential or random selection. The node can output model, CLIP, and VAE components, and supports various model formats (.safetensor, .pt, .gguf, unet). It also allows for storing/loading generation parameters per checkpoint.
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 0.0.7.4 (Refactored)

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

    Credits:
    - GGUF loading functionality adapted from City96/ComfyUI-GGUF
    - Architecture detection inspired by X-T-E-R/ComfyUI-EasyCivitai-XTNodes
    - ComfyUI! Uses ComfyUI's built-in model detection where available

"""

import os
import re
import json
import random
import glob
import hashlib
import importlib
import traceback
import gc
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Union, Optional, Any
from collections import OrderedDict


import torch
import folder_paths
import comfy.sd
import comfy.utils
import comfy.model_management
import comfy.model_detection
import comfy.samplers
# Import the model detection utilities if available
try:
    import comfy.supported_models
    import comfy.supported_models_base
    from comfy.model_detection import detect_unet_config  # <-- Fixed import
    HAS_ADVANCED_MODEL_DETECTION = True
except ImportError:
    HAS_ADVANCED_MODEL_DETECTION = False

# Import GGUF if available
try:
    import gguf
    HAS_GGUF_SUPPORT = True
except ImportError:
    HAS_GGUF_SUPPORT = False
    print("[CheckpointTester] Native GGUF support requires gguf package.")
    print("[CheckpointTester] Install with: pip install gguf")

# Add error handling for these imports:
try:
    import yaml
    HAS_YAML_SUPPORT = True
except ImportError:
    HAS_YAML_SUPPORT = False
    print("[CheckpointTester] YAML support not available. Install with: pip install pyyaml")

# At the top, add proper safetensors import handling:
try:
    from safetensors.torch import safe_open
    HAS_SAFETENSORS = True
except ImportError:
    HAS_SAFETENSORS = False
    print("[CheckpointTester] Safetensors support not available.")

# --- Constants ---
DB_FILENAME = "checkpoint_tester_db.json"
DB_VERSION = "1.1" # Increment version if schema changes significantly

KNOWN_ARCHITECTURES = {
    "SD1.5": ["sd1.5", "sd15", "sd-1-5", "stable-diffusion-v1", "v1-5", "sd_v1", "sd1", "sd_1"],
    "SD2.1": ["sd2.1", "sd21", "sd-2-1", "stable-diffusion-v2", "v2-1", "sd2", "v2", "sd2", "SD2.0", "sd2.0", "sd-2", "sd_2"],
    "SDXL": ["sdxl", "sd-xl", "stable-diffusion-xl", "sd_xl", "xl_base", "SDXL", "XL_"],
    "SD3": ["sd3", "stable-diffusion-3", "sd-3"],
    "SD3.5 Large": ["sd3.5", "sd35", "stable-diffusion-3.5", "sd35large", "large", "sd3-large"],
    "SD3.5 Medium": ["sd3.5", "sd35", "stable-diffusion-3.5", "sd35medium", "medium", "sd3-medium"],
    "Flux 1D": ["flux", "FLUX", "Flux1", "F1D", "f1d", "flux1d", "flux-1d", "flex", "flux_1d"],
    "Flux 1S": ["flux", "flux1s", "flux-1s", "flux 1s"],
    "Playground": ["playground", "playground-v2"],
    "Illustrious": ["illustrious", "illustrious-xl"],
    "Pony": ["pony", "PONY", "Pony", "ponyV1"],
    "PixArt Sigma": ["pixart", "pixart-sigma"],
    "PixArt Alpha": ["pixart", "pixart-alpha"],
    "Noobai": ["noobai", "noobai-xl"],
    "HiDream": ["hidream", "HiDream"],
    "StableAudio": ["stableaudio", "audio"],
    "FluxInpaint": ["flux-inpaint", "flux_inpaint"],
    "HunyuanVideo": ["hunyuan-video", "hunyuan_video"],
    "Cosmos": ["cosmos", "cosmos-t2v", "cosmos-i2v"],
    "Lumina2": ["lumina2"],
    "WAN21": ["wan2.1", "wan21"],
    "Chroma": ["chroma"],
    "ACEStep": ["ace", "acestep"],
}

DEFAULT_GENERATION_PARAMS = {
    "sampler": "euler_ancestral", "scheduler": "normal", "steps": 30, "cfg": 7.0,
    "clip_skip": 1, "batch_size": 1, "width": 1024, "height": 1024
}

DEFAULT_CLIP_PREFERENCES = {
    "clip1": "", "clip2": "", "clip3": "", "clip4": "",
    "clip_type": "auto", "device": "default", "t5_bit_depth": "fp16"
}

# --- Helper Functions ---

def calculate_checkpoint_hash(file_path: str) -> str:
    """Calculate a hash for the checkpoint using metadata and first 1MB."""
    try:
        hasher = hashlib.md5()
        file_stat = os.stat(file_path)
        metadata = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
        hasher.update(metadata.encode('utf-8'))
        with open(file_path, 'rb') as f:
            hasher.update(f.read(1024 * 1024))
        return hasher.hexdigest()
    except Exception as e:
        print(f"[CheckpointTester] Error calculating hash for {file_path}: {e}. Falling back to path hash.")
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()

def get_clean_clip_list() -> List[str]:
    """Get a sorted, deduplicated list of available CLIP models."""
    clip_list = []
    for folder_type in ["clip", "clip_vision", "text_encoders"]:
        try:
            clip_list.extend(folder_paths.get_filename_list(folder_type))
        except Exception as e:
            print(f"[CheckpointTester] Warning: Could not list files in '{folder_type}': {e}")
    return ["None"] + sorted(list(set(clip_list)))

def get_clean_vae_list() -> List[str]:
    """Get a sorted list of available VAE models, including 'None'."""
    return ["None"] + folder_paths.get_filename_list("vae")

def safe_torch_file_load(path: str, device: str = "cpu") -> Optional[Dict]:
    """Safely load a torch file, returning None on error."""
    try:
        # Convert string device to torch.device object if needed
        if isinstance(device, str):
            device_obj = torch.device(device)
        else:
            device_obj = device
        
        # Use the device object with ComfyUI's load function
        return comfy.utils.load_torch_file(path, device=device_obj)
    except Exception as e:
        print(f"[CheckpointTester] Error loading torch file {path}: {e}")
        return None

def clear_gpu_memory():
    """Attempt to clear GPU memory."""
    gc.collect()
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as e:
        print(f"[CheckpointTester] Warning: Error clearing GPU memory: {e}")

# --- Checkpoint Database Manager ---

class CheckpointDBManager:
    """Handles loading, saving, and accessing the checkpoint database."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = self._load()

    def _load(self) -> Dict:
        """Load the checkpoint database from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    db_data = json.load(f)
                # Basic validation and migration if needed
                if not isinstance(db_data, dict) or "checkpoints" not in db_data:
                    raise ValueError("Invalid database format.")
                if db_data.get("version") != DB_VERSION:
                    print(f"[CheckpointTester] Database version mismatch (found {db_data.get('version')}, expected {DB_VERSION}). Attempting migration or reset.")
                    # Add migration logic here if needed in the future
                    db_data = self._initialize_db() # Reset if migration fails or isn't implemented
                self._ensure_db_structure(db_data)
                return db_data
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"[CheckpointTester] Warning: Checkpoint database error ({e}). Creating a new one.")
                return self._initialize_db()
        else:
            return self._initialize_db()

    def _initialize_db(self) -> Dict:
        """Return an empty database structure."""
        return {"checkpoints": {}, "version": DB_VERSION, "current_index": 0}

    def _ensure_db_structure(self, db_data: Dict):
        """Ensure all necessary keys exist in the database entries."""
        if "current_index" not in db_data:
            db_data["current_index"] = 0
        for cp_hash, cp_data in db_data.get("checkpoints", {}).items():
            if not isinstance(cp_data, dict): continue # Skip invalid entries
            cp_data.setdefault("architecture", "Unknown")
            cp_data.setdefault("model_type", "checkpoint")
            cp_data.setdefault("has_vae", None)
            cp_data.setdefault("has_clip", None)
            cp_data.setdefault("clip_type", "none") # Type detected from keys
            cp_data.setdefault("category", "unknown")
            cp_data.setdefault("notes", "")
            cp_data.setdefault("preferred_vae", "")
            cp_data.setdefault("clip_preferences", {}).update({k: v for k, v in DEFAULT_CLIP_PREFERENCES.items() if k not in cp_data["clip_preferences"]})
            cp_data.setdefault("generation_params", {}).update({k: v for k, v in DEFAULT_GENERATION_PARAMS.items() if k not in cp_data["generation_params"]})

    def save(self):
        """Save the checkpoint database to disk."""
        try:
            # Ensure current_index is up-to-date before saving
            # self.db["current_index"] = current_index # This should be set by the caller
            with open(self.db_path, 'w') as f:
                json.dump(self.db, f, indent=2)
            # print(f"[CheckpointTester] Database saved.")
        except IOError as e:
            print(f"[CheckpointTester] Warning: Could not save checkpoint database: {e}")

    def get_checkpoint_data(self, checkpoint_hash: str) -> Optional[Dict]:
        """Get data for a specific checkpoint hash."""
        return self.db["checkpoints"].get(checkpoint_hash)

    def update_checkpoint_data(self, checkpoint_hash: str, data: Dict):
        """Update data for a specific checkpoint hash."""
        if checkpoint_hash in self.db["checkpoints"]:
            self.db["checkpoints"][checkpoint_hash].update(data)
        else:
            # Ensure basic structure if creating new
            self.db["checkpoints"][checkpoint_hash] = data
            self._ensure_db_structure(self.db) # Ensure new entry has all fields

    def get_all_checkpoints(self) -> Dict:
        """Get the entire checkpoints dictionary."""
        return self.db.get("checkpoints", {})

    def get_current_index(self) -> int:
        """Get the last saved current index."""
        return self.db.get("current_index", 0)

    def set_current_index(self, index: int):
        """Set the current index in the database (for saving)."""
        self.db["current_index"] = index

# --- Base Node Class ---

class BaseCheckpointNode:
    """Base class for nodes interacting with the checkpoint database."""
    def __init__(self):
        db_path = os.path.join(os.path.dirname(__file__), DB_FILENAME)
        self.db_manager = CheckpointDBManager(db_path)

# --- Checkpoint Tester Node ---

class CheckpointTesterNode(BaseCheckpointNode):
    """ComfyUI node for testing multiple checkpoint models."""

    @classmethod
    def INPUT_TYPES(cls):
        clip_list = get_clean_clip_list()
        vae_list = get_clean_vae_list()
        return {
            "required": {
                "dir_search_terms": ("STRING", {"default": "", "multiline": False, "tooltip": "Comma-separated terms to search in directory paths. Use -term to exclude."}),
                "file_search_terms": ("STRING", {"default": "", "multiline": False, "tooltip": "Comma-separated terms to search in checkpoint filenames. Use -term to exclude (e.g., -inpaint,-refiner)."}),
                "additional_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Additional directory to search for checkpoints"}),
                "architecture": (["Any"] + list(KNOWN_ARCHITECTURES.keys()), {"default": "Any", "tooltip": "Filter by model architecture"}),
                "category": (["Any", "unknown", "art", "illustration", "painting", "realistic", "cinema", "anime", "3d", "concept art", "portrait", "landscape", "photographic", "dreamlike", "character", "sci-fi", "fantasy", "abstract", "other"], {"default": "Any", "tooltip": "Filter by model category"}),
                "notes_search": ("STRING", {"default": "", "multiline": False, "tooltip": "Search terms to match in model notes. Use -term to exclude."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Checkpoint number (1-based index) or random seed"}),
                "vae_mode": (["auto", "embedded_only", "specific_vae", "none"], {"default": "auto", "tooltip": "How to select the VAE"}),
                "vae_name": (vae_list, {"default": "None", "tooltip": "Specific VAE to use"}),
                "clip_mode": (["auto", "embedded_only", "specific_clip", "none"], {"default": "auto", "tooltip": "How to select CLIP"}),
                "clip1_name": (clip_list, {"default": "None", "tooltip": "Primary CLIP model"}),
                "clip2_name": (clip_list, {"default": "None", "tooltip": "Secondary CLIP model"}),
                "clip3_name": (clip_list, {"default": "None", "tooltip": "Tertiary CLIP model"}),
                "clip4_name": (clip_list, {"default": "None", "tooltip": "Quaternary CLIP model"}),
                "clip_type": (["auto"] + list(KNOWN_ARCHITECTURES.keys()) + ["single", "dual", "triple", "quad"], {"default": "auto", "tooltip": "Specific CLIP combiner type (auto=detect)"}),
                "clip_device": (["default", "CPU", "GPU"], {"default": "default", "tooltip": "Device for CLIP models"}),
                "t5_bit_depth": (["auto", "fp16", "bf16", "fp32", "fp8", "fp8_e4m3fn"], {"default": "auto", "tooltip": "Bit depth for T5 models (auto=detect)"}),
            },
            "optional": {
                # "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional prompt to encode with loaded CLIP"}), # Example optional input
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING", "STRING", "STRING", "INT", "INT", "STRING", "EMBEDDING")
    RETURN_NAMES = ("model", "clip", "vae", "latent_format", "model_name", "model_path", "checkpoint_list", "total_checkpoints", "selected_checkpoints", "missing_info_list", "prompt_embedding")
    FUNCTION = "process_checkpoints"
    CATEGORY = "loaders/checkpoint tester"

    def __init__(self):
        super().__init__()
        self.checkpoint_paths = []
        self.filtered_checkpoints = []
        self.current_index = self.db_manager.get_current_index()
        self.last_seed = None
        self._vae_cache = OrderedDict()
        self._clip_cache = OrderedDict()
        self._vae_cache_max_size = 5
        self._clip_cache_max_size = 3
        self.scan_checkpoints() # Initial scan

    # --- Caching ---
    def _manage_cache(self, cache: OrderedDict, max_size: int, item_type: str):
        """Generic cache management."""
        while len(cache) >= max_size:
            oldest_key, _ = cache.popitem(last=False) # Pop oldest item
            print(f"[CheckpointTester] Removing least recently used {item_type} from cache: {oldest_key}")
            clear_gpu_memory()

    def _add_to_cache(self, cache: OrderedDict, key: str, value: Any, max_size: int, item_type: str):
        """Add item to cache, managing size."""
        if key in cache: # Move to end if already exists
            cache.move_to_end(key)
        self._manage_cache(cache, max_size, item_type)
        cache[key] = value
        cache.move_to_end(key) # Mark as recently used

    # --- Checkpoint Scanning and Database Update ---
    def scan_checkpoints(self, additional_path: str = ""):
        """Scan standard checkpoint directories and the additional path."""
        self.checkpoint_paths = []
        dirs_to_scan = set()
        for folder_type in ["checkpoints", "unet", "diffusion_models"]:
            try:
                dirs_to_scan.update(os.path.normpath(p) for p in folder_paths.get_folder_paths(folder_type))
            except Exception as e:
                 print(f"[CheckpointTester] Warning: Could not get paths for '{folder_type}': {e}")

        if additional_path and os.path.isdir(additional_path):
            dirs_to_scan.add(os.path.normpath(additional_path))

        extensions = [".safetensors", ".pt", ".ckpt", ".bin", ".gguf"]
        found_paths = set()

        for directory in dirs_to_scan:
            if not os.path.isdir(directory): continue
            for ext in extensions:
                pattern = os.path.join(directory, f"**/*{ext}")
                try:
                    found_paths.update(os.path.normpath(p) for p in glob.glob(pattern, recursive=True))
                except Exception as e:
                    print(f"[CheckpointTester] Error scanning directory {directory} with pattern {pattern}: {e}")

        self.checkpoint_paths = sorted(list(found_paths))
        self._update_checkpoint_database()

    def _update_checkpoint_database(self):
        """Update the database with found checkpoints and detect architecture."""
        updated = False
        for path in self.checkpoint_paths:
            cp_hash = calculate_checkpoint_hash(path)
            cp_data = self.db_manager.get_checkpoint_data(cp_hash)

            if cp_data is None:
                model_name = os.path.basename(path)
                model_type = self._determine_model_type(path)
                detected_arch = self._detect_architecture(path, model_name)
                inspect_result = self._inspect_checkpoint_contents(path)

                new_data = {
                    "path": path, "name": model_name, "architecture": detected_arch,
                    "model_type": model_type, "has_vae": inspect_result["has_vae"],
                    "has_clip": inspect_result["has_clip"], "clip_type": inspect_result["clip_type"],
                    # Defaults will be filled by _ensure_db_structure
                }
                self.db_manager.update_checkpoint_data(cp_hash, new_data)
                updated = True
            elif cp_data.get("path") != path: # Update path if moved
                self.db_manager.update_checkpoint_data(cp_hash, {"path": path})
                updated = True
            elif cp_data.get("architecture") == "Unknown": # Try re-detecting if unknown
                 detected_arch = self._detect_architecture(path, cp_data.get("name"))
                 if detected_arch != "Unknown":
                     self.db_manager.update_checkpoint_data(cp_hash, {"architecture": detected_arch})
                     updated = True

        if updated:
            self.db_manager.save()

    def _determine_model_type(self, path: str) -> str:
        """Determine model type (checkpoint, unet, diffusion, gguf) based on path."""
        norm_path = path.replace("\\", "/")
        if norm_path.endswith(".gguf"): return "gguf"
        if "/unet/" in norm_path: return "unet"
        if "/diffusion_models/" in norm_path: return "diffusion"
        return "checkpoint"

    # --- Architecture Detection ---
    def _detect_architecture(self, path: str, name: str) -> str:
        """Enhanced architecture detection with better Flux format support."""
        # First try model inspection for more accurate detection
        arch_from_inspection = self._detect_arch_from_model_inspection(path)
        if arch_from_inspection and arch_from_inspection != "Unknown":
            return arch_from_inspection
        
        # Enhanced name-based detection with better Flux patterns
        arch_from_name = self._detect_arch_from_name_enhanced(name)
        if arch_from_name and arch_from_name != "Unknown":
            return arch_from_name
        
        return "Unknown"

    def _detect_arch_from_name_enhanced(self, filename: str) -> str:
        """Enhanced name-based detection with format-specific patterns."""
        filename_lower = filename.lower()
        
        # Enhanced Flux detection with format variants
        flux_patterns = [
            "flux", "flux-1d", "flux1d", "flux-1s", "flux1s", 
            "f1d", "f1s", "schnell", "dev"
        ]
        
        if any(p in filename_lower for p in flux_patterns):
            # Detect specific Flux variants
            if any(p in filename_lower for p in ["1s", "1-s", "schnell"]):
                return "Flux 1S"
            elif any(p in filename_lower for p in ["inpaint"]):
                return "FluxInpaint"
            else:
                return "Flux 1D"  # Default to Dev version
        
        # Check for quantization indicators
        quant_patterns = ["q8", "nf4", "int8", "int4", "gguf", "quantized"]
        if any(p in filename_lower for p in quant_patterns):
            # Still try to detect base architecture
            for arch, patterns in KNOWN_ARCHITECTURES.items():
                if any(pattern.lower() in filename_lower for pattern in patterns):
                    return arch
        
        # General pattern matching
        return self._detect_arch_from_list([filename_lower], match_exact=False)
        

    def _detect_arch_from_model_inspection(self, model_path: str) -> str:
        """Detect architecture using ComfyUI core detection, GGUF, and key patterns."""
        try:
            file_ext = os.path.splitext(model_path)[1].lower()

            # --- GGUF detection ---
            if file_ext == ".gguf" and HAS_GGUF_SUPPORT:
                try:
                    import gguf
                    reader = gguf.GGUFReader(model_path)
                    arch_field = reader.get_field("general.architecture")
                    if arch_field:
                        arch_str = str(arch_field.parts[arch_field.data[-1]], encoding="utf-8")
                        # Map GGUF arch to our naming
                        gguf_arch_map = {
                            "flux": "Flux 1D",
                            "sd1": "SD1.5",
                            "sdxl": "SDXL",
                            "sd3": "SD3"
                        }
                        return gguf_arch_map.get(arch_str, arch_str)
                except Exception as e:
                    print(f"[CheckpointTester] GGUF detection failed: {e}")

            # --- ComfyUI model_detection for .pt/.ckpt/.safetensors ---
            if file_ext in [".safetensors", ".pt", ".ckpt", ".pth"] and HAS_ADVANCED_MODEL_DETECTION:
                try:
                    # Try to load just the header for safetensors
                    if file_ext == ".safetensors" and HAS_SAFETENSORS:
                        # FIXED: Don't use device="meta" - use CPU instead
                        with safe_open(model_path, framework="pt", device="cpu") as f:
                            keys = list(f.keys())[:100]  # Limit to first 100 keys for speed
                    else:
                        # For .pt/.ckpt, load state dict keys (minimally) - FIXED: Use CPU
                        state_dict = comfy.utils.load_torch_file(model_path, safe_load=True, device="cpu")
                        if state_dict:
                            keys = list(state_dict.keys())[:100]  # Limit keys for speed
                            del state_dict  # Free memory immediately
                        else:
                            keys = []
                    
                    if not keys:
                        print(f"[CheckpointTester] No keys found in {model_path}")
                        return "Unknown"
                    
                    # Use Comfy's unet_prefix_from_state_dict
                    unet_prefix = comfy.model_detection.unet_prefix_from_state_dict(keys)
                    if unet_prefix is not None:
                        # Try to get model config - FIXED: Pass dummy state dict
                        dummy_state_dict = {k: None for k in keys}
                        model_config = comfy.model_detection.model_config_from_unet(
                            dummy_state_dict, unet_prefix, use_base_if_no_match=True
                        )
                        if model_config:
                            # Map config class name to our arch
                            return self._model_config_to_arch(model_config)
                    
                    # Fallback: try to detect Flux by key patterns
                    if self._is_flux_model(set(keys)):
                        return self._detect_flux_variant(set(keys), model_path)
                        
                except Exception as e:
                    print(f"[CheckpointTester] ComfyUI detection failed: {e}")

            # --- Fallback: key pattern matching ---
            if file_ext in [".safetensors", ".pt", ".ckpt", ".pth"]:
                try:
                    # Try to load keys if not already done
                    if 'keys' not in locals() or not keys:
                        if file_ext == ".safetensors" and HAS_SAFETENSORS:
                            # FIXED: Use CPU instead of meta
                            with safe_open(model_path, framework="pt", device="cpu") as f:
                                keys = list(f.keys())[:100]
                        else:
                            # FIXED: Use CPU instead of meta
                            state_dict = comfy.utils.load_torch_file(model_path, safe_load=True, device="cpu")
                            if state_dict:
                                keys = list(state_dict.keys())[:100]
                                del state_dict  # Free memory
                            else:
                                keys = []
                                
                    if keys and self._is_flux_model(set(keys)):
                        return self._detect_flux_variant(set(keys), model_path)
                        
                except Exception as e:
                    print(f"[CheckpointTester] Fallback key detection failed: {e}")

        except Exception as e:
            print(f"[CheckpointTester] Model inspection failed: {e}")

        return "Unknown"
        
        

    def _is_flux_model(self, state_dict_keys: set) -> bool:
        """Check if model is Flux based on key patterns."""
        flux_patterns = [
            "double_blocks.0.img_attn.norm.key_norm.scale",
            "img_in.weight",
            "time_in.in_layer.weight",
            "guidance_in.in_layer.weight",
            "txt_in.weight",
            "vector_in.in_layer.weight"
        ]
        return any(key in state_dict_keys for key in flux_patterns)

    def _detect_flux_variant(self, state_dict_keys: set, model_path: str) -> str:
        """Detect specific Flux variant."""
        # Check for inpainting version
        if any("inpaint" in key.lower() for key in state_dict_keys):
            return "FluxInpaint"
        
        # Check model size/complexity for schnell vs dev
        if "double_blocks.18" in state_dict_keys or any("double_blocks.1" in key for key in state_dict_keys if "double_blocks.1" in key and len(key.split('.')) > 3):
            return "Flux 1D"  # Dev version (larger)
        else:
            return "Flux 1S"  # Schnell version (smaller)

    def _detect_arch_from_list(self, items: List[str], match_exact: bool = False) -> str:
        """Helper to detect architecture from a list of strings (dirs or filename parts)."""
        for item in items:
            item_lower = item.lower()
            for arch, patterns in KNOWN_ARCHITECTURES.items():
                for pattern in patterns:
                    pattern_lower = pattern.lower()
                    if match_exact:
                        if item_lower == pattern_lower: return arch
                    else:
                        if pattern_lower in item_lower: return arch
        return "Unknown"

    def _detect_arch_from_name(self, filename: str) -> str:
        """Detect architecture from filename patterns."""
        filename_lower = filename.lower()
        # Handle specific cases first (like Flux variants)
        if any(p in filename_lower for p in ["flux", "flux-1d", "flux1d", "flux1s", "flux-1s"]):
            return "Flux 1S" if any(p in filename_lower for p in ["1s", "1-s"]) else "Flux 1D"
        # General pattern matching
        return self._detect_arch_from_list([filename_lower], match_exact=False)

    def _detect_arch_from_yaml(self, yaml_path: str) -> str:
        """Detect architecture from associated YAML config file."""
        if not HAS_YAML_SUPPORT:
            return "Unknown"
        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
            if isinstance(config, dict) and "model" in config:
                model_config = config["model"]
                if isinstance(model_config, dict):
                    target = model_config.get("target", "").lower()
                    if "sdxl" in target: return "SDXL"
                    if "sd3" in target: return "SD3"
                    if "v2" in target: return "SD2.1"
                    if "v1" in target: return "SD1.5" # Be careful with this one
                    # Add more specific checks if needed
        except Exception as e:
            print(f"[CheckpointTester] Error parsing YAML {yaml_path}: {e}")
        return "Unknown"

    def _detect_arch_from_gguf(self, model_path: str) -> str:
        """Enhanced GGUF detection."""
        if not HAS_GGUF_SUPPORT:
            # Fallback to name-based detection
            name = os.path.basename(model_path).lower()
            if "flux" in name:
                return "Flux 1D"
            return "Unknown"
        
        try:
            import gguf
            reader = gguf.GGUFReader(model_path)
            
            # Get architecture field
            arch_field = reader.get_field("general.architecture")
            if arch_field:
                arch_str = str(arch_field.parts[arch_field.data[-1]], encoding="utf-8")
                
                # Map GGUF architecture to our naming
                gguf_arch_map = {
                    "flux": "Flux 1D",
                    "sd1": "SD1.5", 
                    "sdxl": "SDXL",
                    "sd3": "SD3"
                }
                return gguf_arch_map.get(arch_str, "Unknown")
            
        except Exception as e:
            print(f"[CheckpointTester] GGUF detection failed: {e}")
        
        return "Unknown"

    def _model_config_to_arch(self, model_config) -> str:
        """Convert ComfyUI model config to our architecture naming."""
        config_class_name = model_config.__class__.__name__
        
        config_map = {
            "SD15": "SD1.5",
            "SD20": "SD2.1", 
            "SDXL": "SDXL",
            "SD3": "SD3",
            "Flux": "Flux 1D",
            "FluxSchnell": "Flux 1S",
            "FluxInpaint": "FluxInpaint"
        }
        
        return config_map.get(config_class_name, "Unknown")


    def _detect_arch_from_pt_st(self, model_path: str) -> str:
        """Detect architecture from PyTorch/Safetensors files using ComfyUI methods."""
        if not HAS_ADVANCED_MODEL_DETECTION: return "Unknown"
        try:
            # Use ComfyUI's detection logic
            # Note: This might load parts of the model, could be slow/memory intensive
            # Consider loading only metadata first if possible
            state_dict_metadata = {}
            if model_path.endswith('.safetensors'):
                 try:
                     with comfy.utils.safetensors_load_block(model_path, device="meta") as state_dict_iter:
                         # Try to get enough info from first few tensors for detection
                         # This is complex as detect_unet_config needs actual tensors
                         # A full load might be unavoidable for reliable detection here
                         pass # Placeholder - reliable detection without full load is hard
                 except Exception:
                     pass # Fallback if meta load fails or isn't enough

            # If metadata didn't work, try loading a sample (expensive)
            # This part needs careful implementation to avoid loading huge models entirely
            # For now, rely on other detection methods or assume Unknown if metadata fails
            # Example using guess_config (loads the whole model):
            # _, _, _, latent_format = comfy.sd.load_checkpoint_guess_config(model_path, output_vae=False, output_clip=False)
            # if latent_format: return latent_format.__class__.__name__ # Map class name back

        except Exception as e:
            print(f"[CheckpointTester] Error during advanced model detection for {model_path}: {e}")
        return "Unknown" # Fallback if advanced detection fails

    def _inspect_checkpoint_contents(self, model_path: str) -> Dict[str, Any]:
        """Inspect keys to determine embedded VAE/CLIP presence and CLIP type."""
        result = {"has_vae": None, "has_clip": None, "clip_type": "none"}
        keys = []
        try:
            if model_path.endswith(".safetensors") and HAS_SAFETENSORS:
                # Use metadata loading for speed if possible
                try:
                    with safe_open(model_path, framework="pt", device="meta") as f:
                        keys = list(f.keys())
                except Exception:
                    print(f"[CheckpointTester] Meta load failed for {model_path}, trying cpu load for inspection.")
                    if HAS_SAFETENSORS:
                        with safe_open(model_path, framework="pt", device="cpu") as f:
                            keys = list(f.keys())
            elif model_path.endswith((".pt", ".ckpt")):
                # Loading state_dict can be memory intensive
                state_dict = safe_torch_file_load(model_path, device="cpu")
                if state_dict:
                    keys = list(state_dict.keys())
            elif model_path.endswith(".gguf") and HAS_GGUF_SUPPORT:
                 # GGUF inspection logic (check for specific tensor names)
                 try:
                     reader = gguf.GGUFReader(model_path)
                     keys = [tensor.name for tensor in reader.tensors]
                 except Exception as e_gguf:
                     print(f"[CheckpointTester] Failed to read GGUF keys {model_path}: {e_gguf}")

            if not keys: return result # No keys found or loaded

            # Check for VAE keys (adjust patterns as needed)
            result["has_vae"] = any(k.startswith(("first_stage_model.", "vae.")) for k in keys)

            # Check for CLIP keys and determine type
            clip_key_prefixes = ["cond_stage_model.", "clip.", "text_model."] # Add more prefixes if needed
            clip_keys = [k for k in keys if any(k.startswith(p) for p in clip_key_prefixes)]

            if clip_keys:
                result["has_clip"] = True
                # More sophisticated type detection based on specific key patterns
                has_clip_l = any("clip_l." in k or ".text_model." in k for k in clip_keys) # Example patterns
                has_clip_g = any("clip_g." in k for k in clip_keys)
                has_t5 = any("t5." in k for k in clip_keys)
                # Add checks for other encoders (e.g., specific names in HiDream)

                if has_t5 and has_clip_g and has_clip_l: result["clip_type"] = "triple" # SD3-like
                elif has_clip_g and has_clip_l: result["clip_type"] = "dual" # SDXL-like
                elif has_clip_l or has_clip_g or has_t5: result["clip_type"] = "single" # Basic CLIP or T5 only
                # Add logic for quad, etc.
            else:
                 result["has_clip"] = False


        except Exception as e:
            print(f"[CheckpointTester] Failed to inspect {model_path}: {e}")
            # Keep results as None to indicate inspection failure

        return result

    def _ensure_checkpoint_inspected(self, checkpoint_hash: str, checkpoint_path: str):
        """Ensure VAE/CLIP info is in the DB, inspecting if needed."""
        entry = self.db_manager.get_checkpoint_data(checkpoint_hash)
        if not entry: return

        needs_inspect = entry.get("has_vae") is None or entry.get("has_clip") is None
        if needs_inspect:
            print(f"[CheckpointTester] Inspecting {os.path.basename(checkpoint_path)} for missing VAE/CLIP info")
            result = self._inspect_checkpoint_contents(checkpoint_path)
            update_data = {"has_vae": result["has_vae"], "has_clip": result["has_clip"]}
            # Only update clip_type if inspection succeeded and found CLIP
            if result["has_clip"] is not None and result["has_clip"]:
                 update_data["clip_type"] = result["clip_type"]
            self.db_manager.update_checkpoint_data(checkpoint_hash, update_data)
            self.db_manager.save() # Save immediately after inspection

        # Auto-detect t5_bit_depth if set to auto (moved from inspect to ensure it runs)
        # This is expensive, maybe only run if needed?
        # if entry.get("clip_preferences", {}).get("t5_bit_depth", "auto") == "auto":
        #     detected_precision = self._detect_checkpoint_precision(checkpoint_path, entry.get("architecture"))
        #     prefs = entry.setdefault("clip_preferences", {})
        #     prefs["t5_bit_depth"] = detected_precision
        #     self.db_manager.update_checkpoint_data(checkpoint_hash, {"clip_preferences": prefs})
        #     self.db_manager.save()


    # --- Filtering and Listing ---
    def filter_checkpoints(self, dir_search_terms: str, file_search_terms: str,
                        architecture: str, category: str, notes_search: str):
        """Apply filters to the list of scanned checkpoints."""
        
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
        notes_include, notes_exclude = parse_search_terms(notes_search)
        
        # Debug output
        if file_include or file_exclude:
            print(f"[CheckpointTester] File search - Include: {file_include}, Exclude: {file_exclude}")
        
        self.filtered_checkpoints = []
        for cp_path in self.checkpoint_paths:
            cp_hash = calculate_checkpoint_hash(cp_path)
            cp_data = self.db_manager.get_checkpoint_data(cp_hash)
            if not cp_data: continue # Skip if not in DB (shouldn't happen after scan)
            
            # Directory Filter
            if dir_include or dir_exclude:
                dir_path = os.path.dirname(cp_path).lower()
                # Check includes
                if dir_include and not any(term in dir_path for term in dir_include):
                    continue
                # Check excludes
                if dir_exclude and any(term in dir_path for term in dir_exclude):
                    continue
            
            # Filename Filter
            if file_include or file_exclude:
                filename = os.path.basename(cp_path).lower()
                # Check includes
                if file_include and not any(term in filename for term in file_include):
                    continue
                # Check excludes
                if file_exclude and any(term in filename for term in file_exclude):
                    continue
            
            # Architecture Filter
            if architecture != "Any" and cp_data.get("architecture") != architecture:
                continue
            
            # Category Filter
            if category != "Any" and cp_data.get("category", "unknown").lower() != category.lower():
                continue
            
            # Notes Filter
            if notes_include or notes_exclude:
                notes = cp_data.get("notes", "").lower()
                # Check includes
                if notes_include and not any(term in notes for term in notes_include):
                    continue
                # Check excludes
                if notes_exclude and any(term in notes for term in notes_exclude):
                    continue
            
            self.filtered_checkpoints.append(cp_path)
            

    def get_checkpoint_list_text(self) -> str:
        """Create a formatted text list of filtered checkpoints."""
        if not self.filtered_checkpoints:
            return "No checkpoints match the current filters."

        lines = ["Filtered Checkpoints:"]
        for idx, cp_path in enumerate(self.filtered_checkpoints):
            model_name = os.path.basename(cp_path)
            cp_hash = calculate_checkpoint_hash(cp_path)
            cp_data = self.db_manager.get_checkpoint_data(cp_hash)
            arch = cp_data.get("architecture", "Unknown") if cp_data else "Unknown"
            lines.append(f"{idx+1}. {model_name} [{arch}]")
        return "\n".join(lines)

    def get_missing_info_list_text(self) -> str:
        """Generate a list of models with missing information."""
        missing_info = []
        for cp_hash, cp_data in self.db_manager.get_all_checkpoints().items():
            missing = []
            if cp_data.get("architecture") == "Unknown": missing.append("architecture")
            if cp_data.get("has_vae") is None: missing.append("VAE status")
            if cp_data.get("has_clip") is None: missing.append("CLIP status")
            if missing:
                missing_info.append((cp_data.get("name", "N/A"), cp_data.get("path", "N/A"), missing))

        if not missing_info: return "All models have complete information."
        lines = ["Models with Missing Information:"]
        for idx, (name, path, missing_items) in enumerate(missing_info):
            lines.append(f"{idx+1}. {name} (Missing: {', '.join(missing_items)})")
        return "\n".join(lines)

    # --- VAE Loading and Selection ---
    def _load_vae_by_name(self, vae_name: str) -> Optional[comfy.sd.VAE]:
        """Load a VAE by name, checking cache first."""
        if not vae_name or vae_name == "None": return None

        if vae_name in self._vae_cache:
            print(f"[CheckpointTester] Using cached VAE: {vae_name}")
            self._vae_cache.move_to_end(vae_name)
            return self._vae_cache[vae_name]

        try:
            # Handle TAESD variants if necessary
            if vae_name.startswith("taesd"):
                sd = self._load_taesd(vae_name)
                if sd is None: return None
            else:
                vae_path = folder_paths.get_full_path("vae", vae_name)
                if not vae_path:
                    raise FileNotFoundError(f"VAE not found: {vae_name}")
                print(f"[CheckpointTester] Loading VAE: {vae_name} from {vae_path}")
                
                # Use proper device handling - remove the problematic device parameter
                sd = comfy.utils.load_torch_file(vae_path, safe_load=True)
                
                if sd is None: return None

            vae = comfy.sd.VAE(sd=sd)
            if not self._check_vae_health(vae):
                print(f"[CheckpointTester] Loaded VAE '{vae_name}' failed health check.")
                return None

            self._add_to_cache(self._vae_cache, vae_name, vae, self._vae_cache_max_size, "VAE")
            return vae
        except Exception as e:
            print(f"[CheckpointTester] ERROR loading VAE '{vae_name}': {e}\n{traceback.format_exc()}")
            return None

    def _load_taesd(self, name):
        """Load TAESD VAE components."""
        # Assuming this logic is correct from the original code
        sd = {}
        try:
            approx_vaes = folder_paths.get_filename_list("vae_approx")
            encoder_name = next((f for f in approx_vaes if f.startswith(f"{name}_encoder.")), None)
            decoder_name = next((f for f in approx_vaes if f.startswith(f"{name}_decoder.")), None)

            if not encoder_name or not decoder_name:
                raise RuntimeError(f"Missing TAESD components for {name}")

            encoder_path = folder_paths.get_full_path("vae_approx", encoder_name)
            decoder_path = folder_paths.get_full_path("vae_approx", decoder_name)

            enc = safe_torch_file_load(encoder_path)
            dec = safe_torch_file_load(decoder_path)

            if enc is None or dec is None: return None

            for k, v in enc.items(): sd[f"{name}_encoder.{k}"] = v
            for k, v in dec.items(): sd[f"{name}_decoder.{k}"] = v

            # Add scale/shift if needed (from original code)
            scales = {"taesd": 0.18215, "taesdxl": 0.13025, "taesd3": 1.5305, "taef1": 0.3611}
            shifts = {"taesd": 0.0, "taesdxl": 0.0, "taesd3": 0.0609, "taef1": 0.1159}
            sd["vae_scale"] = torch.tensor(scales.get(name, 1.0))
            sd["vae_shift"] = torch.tensor(shifts.get(name, 0.0))
            return sd
        except Exception as e:
            print(f"[CheckpointTester] Error loading TAESD '{name}': {e}")
            return None

    def _check_vae_health(self, vae: Optional[comfy.sd.VAE]) -> bool:
        """Basic check if VAE object seems valid."""
        return vae is not None and hasattr(vae, 'encode') and hasattr(vae, 'decode')

    def _detect_appropriate_vae(self, architecture: str) -> str:
        """Suggest an appropriate VAE based on architecture."""
        # Simplified suggestions - expand as needed
        vae_suggestions = {
            "SD1.5": ["vae-ft-mse-840000-ema-pruned.safetensors"],
            "SD2.1": ["vae-ft-mse-840000-ema-pruned.safetensors"],
            "SDXL": ["sdxl_vae.safetensors"],
            "SD3": ["sd3_vae.safetensors"],
            "SD3.5 Large": ["sd3_vae.safetensors"],
            "SD3.5 Medium": ["sd3_vae.safetensors"],
            "Flux 1D": ["flux_vae.safetensors", "ae.sft"],
            "Flux 1S": ["flux_vae.safetensors", "ae.sft"],
            # Add more...
        }
        universal_fallbacks = [
            "vae-ft-mse-840000-ema-pruned.safetensors",
            "sdxl_vae.safetensors",
            "sd3_vae.safetensors",
            "ae.sft",
        ]
        available_vaes = get_clean_vae_list() # Get current list

        for suggestion in vae_suggestions.get(architecture, []):
            if suggestion in available_vaes: return suggestion
        for fallback in universal_fallbacks:
            if fallback in available_vaes:
                 print(f"[CheckpointTester] No specific VAE found for {architecture}, using fallback: {fallback}")
                 return fallback
        return "" # Return empty string if none found

    def _handle_vae_selection(self, embedded_vae: Optional[comfy.sd.VAE], vae_mode: str, vae_name: str, cp_hash: str, arch: str) -> Optional[comfy.sd.VAE]:
        """Consolidated VAE selection logic."""
        final_vae = None
        cp_data = self.db_manager.get_checkpoint_data(cp_hash)
        preferred_vae = cp_data.get("preferred_vae", "") if cp_data else ""

        if vae_mode == "none":
            print("[CheckpointTester] VAE disabled ('none' mode)")
            return None
        elif vae_mode == "embedded_only":
            if embedded_vae:
                print("[CheckpointTester] Using embedded VAE (embedded_only mode)")
                final_vae = embedded_vae
            else:
                print("[CheckpointTester] No embedded VAE found (embedded_only mode)")
                return None # Explicitly return None
        elif vae_mode == "specific_vae" and vae_name != "None":
            print(f"[CheckpointTester] Attempting to load specific VAE: {vae_name}")
            final_vae = self._load_vae_by_name(vae_name)
        elif vae_mode == "auto":
            if embedded_vae:
                print("[CheckpointTester] Using embedded VAE (auto mode)")
                final_vae = embedded_vae
            elif preferred_vae:
                print(f"[CheckpointTester] Attempting to load preferred VAE from DB: {preferred_vae}")
                final_vae = self._load_vae_by_name(preferred_vae)
            # If still no VAE, try architecture default
            if final_vae is None:
                suggested_vae = self._detect_appropriate_vae(arch)
                if suggested_vae:
                    print(f"[CheckpointTester] Attempting to load suggested VAE for {arch}: {suggested_vae}")
                    final_vae = self._load_vae_by_name(suggested_vae)
            # Last resort: use vae_name if provided in auto mode
            if final_vae is None and vae_name != "None":
                 print(f"[CheckpointTester] Attempting to load specified VAE as auto fallback: {vae_name}")
                 final_vae = self._load_vae_by_name(vae_name)

        # Final check and emergency fallback
        if final_vae is None:
            print("[CheckpointTester] WARNING: No VAE loaded through primary methods. Trying emergency fallbacks.")
            emergency_fallbacks = ["sdxl_vae.safetensors", "vae-ft-mse-840000-ema-pruned.safetensors", "sd3_vae.safetensors", "ae.sft"]
            for fallback_name in emergency_fallbacks:
                emergency_vae = self._load_vae_by_name(fallback_name)
                if emergency_vae:
                    print(f"[CheckpointTester] Successfully loaded emergency fallback VAE: {fallback_name}")
                    final_vae = emergency_vae
                    break
            if final_vae is None:
                 print("[CheckpointTester] CRITICAL WARNING: All VAE loading attempts failed!")

        return final_vae

    # --- CLIP Loading and Selection ---
    def _load_clip_by_name(self, clip_name: str, architecture: str, clip_type: str, device_str: str, t5_bit_depth: str) -> Optional[Any]:
        """Load a single CLIP model by name, checking cache and using the correct loader for each architecture."""
        if not clip_name or clip_name == "None":
            fallback_clip = "clip_l.safetensors"
            print(f"[CheckpointTester] No CLIP specified, trying fallback: {fallback_clip}")
            clip_name = fallback_clip

        # Simple cache key without unsupported parameters
        cache_key = f"{clip_name}_{architecture}_{clip_type}"
        if cache_key in self._clip_cache:
            print(f"[CheckpointTester] Using cached CLIP: {clip_name}")
            self._clip_cache.move_to_end(cache_key)
            return self._clip_cache[cache_key]

        clip_path = None
        for folder_type in ["clip", "clip_vision", "text_encoders"]:
            try:
                clip_path = folder_paths.get_full_path(folder_type, clip_name)
                if clip_path:
                    break
            except:
                continue

        if not clip_path:
            print(f"[CheckpointTester] Cannot find CLIP file: {clip_name}")
            if clip_name != "clip_l.safetensors":
                return self._load_clip_by_name("clip_l.safetensors", architecture, clip_type, device_str, t5_bit_depth)
            return None

        print(f"[CheckpointTester] Loading CLIP: {clip_name} from {clip_path}")

        try:
            # Get the embedding directory
            embedding_directory = folder_paths.get_folder_paths("embeddings")
            
            # Determine the CLIP type based on architecture
            clip_type_enum = self._get_clip_type_enum(architecture, clip_type)
            
            # Use ComfyUI's load_clip with correct parameters
            clip_model = comfy.sd.load_clip(
                ckpt_paths=[clip_path],  # Note: expects a list!
                embedding_directory=embedding_directory,
                clip_type=clip_type_enum,
                model_options={}
            )
            
            if clip_model:
                self._add_to_cache(self._clip_cache, cache_key, clip_model, self._clip_cache_max_size, "CLIP")
            return clip_model

        except Exception as e:
            print(f"[CheckpointTester] Error loading CLIP '{clip_name}': {e}\n{traceback.format_exc()}")
            if clip_name != "clip_l.safetensors":
                return self._load_clip_by_name("clip_l.safetensors", architecture, clip_type, device_str, t5_bit_depth)
            return None

    def _get_clip_type_enum(self, architecture: str, clip_type: str):
        """Convert architecture and clip_type to ComfyUI's CLIPType enum."""
        try:
            from comfy.sd import CLIPType
            
            # Map architecture to appropriate CLIP type
            arch_upper = architecture.upper() if architecture else ""
            
            # Check if we have specific CLIP type mappings
            if any(x in arch_upper for x in ["FLUX"]):
                return CLIPType.FLUX
            elif any(x in arch_upper for x in ["SD3.5", "SD3"]):
                return CLIPType.SD3
            elif any(x in arch_upper for x in ["SDXL", "ILLUSTRIOUS", "PLAYGROUND", "PONY"]):
                return CLIPType.SDXL
            elif any(x in arch_upper for x in ["SD1.5", "SD2.1"]):
                return CLIPType.STABLE_DIFFUSION
            else:
                # Default fallback
                return CLIPType.STABLE_DIFFUSION
                
        except (ImportError, AttributeError) as e:
            print(f"[CheckpointTester] Could not determine CLIPType enum: {e}")
            # Fallback to default if enum not available
            try:
                from comfy.sd import CLIPType
                return CLIPType.STABLE_DIFFUSION
            except:
                return 1  # Fallback to the integer value we saw

    def _load_t5_clip(self, clip_path: str, architecture: str, t5_bit_depth: str) -> Optional[Any]:
        """Load a T5/Flux/SD3 CLIP - use ComfyUI's standard approach."""
        try:
            # For T5 models, use the standard CLIP loader
            # ComfyUI handles the dtype internally based on model requirements
            return comfy.sd.load_clip(clip_path)
        except Exception as e:
            print(f"[CheckpointTester] Error using T5 loader for '{clip_path}': {e}")
            return None


    def _load_sdxl_clipg(self, clip_path: str) -> Optional[Any]:
        """Load an SDXL CLIP-G model."""
        try:
            if hasattr(comfy.sd, "load_clip_g"):
                return comfy.sd.load_clip_g(clip_path)
            else:
                return comfy.sd.load_clip(clip_path)
        except Exception as e:
            print(f"[CheckpointTester] Error loading SDXL CLIP-G '{clip_path}': {e}")
            return None

    def _combine_clips(self, clips: List[Any], architecture: Optional[str], clip_type: str, device_str: str, t5_bit_depth: str) -> Optional[Any]:
        """Simplified CLIP combination for non-Flux architectures."""
        print(f"[DEBUG COMBINE] _combine_clips called:")
        print(f"[DEBUG COMBINE]   clips: {len(clips)} clips provided")
        print(f"[DEBUG COMBINE]   architecture: {architecture}")
        print(f"[DEBUG COMBINE]   clip_type: {clip_type}")
        
        if not clips: 
            print(f"[DEBUG COMBINE] No clips provided")
            return None
        if len(clips) == 1: 
            print(f"[DEBUG COMBINE] Only one clip, returning it")
            return clips[0]

        # For Flux, this method shouldn't be called (handled by _load_flux_clips_properly)
        if "FLUX" in architecture.upper():
            print(f"[DEBUG COMBINE] Warning: Flux CLIPs should be loaded together, not combined separately")
            return clips[0]

        # Determine effective clip_type if auto
        effective_clip_type = clip_type
        if effective_clip_type == "auto":
            print(f"[DEBUG COMBINE] Auto-detecting clip_type for architecture: {architecture}")
            arch_upper = architecture.upper() if architecture else ""
            if any(x in arch_upper for x in ["SDXL", "ILLUSTRIOUS", "PLAYGROUND", "PONY"]):
                effective_clip_type = "SDXL"
            elif any(x in arch_upper for x in ["SD3.5", "SD3"]):
                effective_clip_type = "SD3"
            else:
                print(f"[DEBUG COMBINE] Unknown arch '{architecture}', defaulting to single")
                effective_clip_type = "single"
            print(f"[DEBUG COMBINE] Detected effective_clip_type: {effective_clip_type}")
        
        print(f"[DEBUG COMBINE] Using first CLIP of {len(clips)} loaded CLIPs for {effective_clip_type}")
        
        # For most cases, just return the first CLIP
        # ComfyUI handles multi-CLIP combinations internally when loaded properly
        return clips[0]



    def _load_flux_clips_properly(self, clip_names: List[str]) -> Optional[Any]:
        """Load Flux CLIPs using ComfyUI's DualCLIPLoader approach."""
        try:
            # Filter valid clip names and get first 2 for Flux
            valid_clips = [name for name in clip_names if name and name != "None"]
            if len(valid_clips) < 2:
                print("[CheckpointTester] Flux needs at least 2 CLIPs")
                return None
            
            # Get full paths for the first two CLIPs
            clip_paths = []
            for clip_name in valid_clips[:2]:
                try:
                    # Try different folder types
                    clip_path = None
                    for folder_type in ["clip", "text_encoders"]:
                        try:
                            clip_path = folder_paths.get_full_path_or_raise(folder_type, clip_name)
                            break
                        except:
                            continue
                    
                    if clip_path:
                        clip_paths.append(clip_path)
                    else:
                        print(f"[CheckpointTester] Could not find CLIP: {clip_name}")
                        return None
                except Exception as e:
                    print(f"[CheckpointTester] Error finding CLIP {clip_name}: {e}")
                    return None
            
            if len(clip_paths) < 2:
                print("[CheckpointTester] Could not resolve paths for 2 Flux CLIPs")
                return None
            
            print(f"[CheckpointTester] Loading Flux CLIPs: {clip_paths}")
            
            # Use ComfyUI's standard dual CLIP loading for Flux (like DualCLIPLoader)
            from comfy.sd import CLIPType
            
            clip_model = comfy.sd.load_clip(
                ckpt_paths=clip_paths,
                embedding_directory=folder_paths.get_folder_paths("embeddings"),
                clip_type=CLIPType.FLUX
            )
            
            return clip_model
            
        except Exception as e:
            print(f"[CheckpointTester] Flux CLIP loading failed: {e}")
            print(f"[CheckpointTester] Traceback: {traceback.format_exc()}")
            return None

    def _handle_clip_selection(self, embedded_clip: Optional[Any], clip_mode: str, architecture: str,
                            clip_names: List[str], cp_hash: str, cp_path: str,
                            clip_type: str, clip_device: str, t5_bit_depth: str) -> Optional[Any]:
        """Consolidated CLIP selection logic using ComfyUI standards."""

        print(f"[DEBUG CLIP] _handle_clip_selection called:")
        print(f"[DEBUG CLIP]   clip_mode: {clip_mode}")
        print(f"[DEBUG CLIP]   architecture: {architecture}")
        print(f"[DEBUG CLIP]   clip_names: {clip_names}")
        print(f"[DEBUG CLIP]   clip_type: {clip_type}")
        print(f"[DEBUG CLIP]   embedded_clip: {embedded_clip}")

        final_clip = None
        clips_to_combine = []

        # Helper to load a single clip with current settings
        def load_single_clip(name):
            return self._load_clip_by_name(name, architecture, clip_type, clip_device, t5_bit_depth)

        if clip_mode == "none":
            print("[CheckpointTester] CLIP disabled ('none' mode)")
            return None
        elif clip_mode == "embedded_only":
            if embedded_clip:
                print("[CheckpointTester] Using embedded CLIP (embedded_only mode)")
                final_clip = embedded_clip
            else:
                print("[CheckpointTester] No embedded CLIP found (embedded_only mode)")
                return None
        elif clip_mode == "specific_clip":
            print(f"[CheckpointTester] Using specific CLIPs: {', '.join(n for n in clip_names if n != 'None')}")
            
            # Special handling for Flux - use dual CLIP loading
            if "FLUX" in architecture.upper():
                return self._load_flux_clips_properly(clip_names)
            
            # For other architectures, use individual loading
            for name in clip_names:
                if name and name != "None":
                    clip = load_single_clip(name)
                    if clip:
                        clips_to_combine.append(clip)
            
            if not clips_to_combine:
                print("[CheckpointTester] No specific CLIPs loaded successfully")
                return None
                
        elif clip_mode == "auto":
            if embedded_clip:
                print("[CheckpointTester] Using embedded CLIP (auto mode)")
                final_clip = embedded_clip
            else:
                # Try preferred CLIPs from DB
                print(f"[DEBUG CLIP] No embedded CLIP, checking DB preferences")
                db_clips = []
                db_clip_type = clip_type
                db_clip_device = clip_device
                db_t5_bit_depth = t5_bit_depth
                cp_data = self.db_manager.get_checkpoint_data(cp_hash)
                if cp_data:
                    prefs = cp_data.get("clip_preferences", {})
                    print(f"[DEBUG CLIP] DB preferences: {prefs}")
                    db_clip_type = prefs.get("clip_type", clip_type)
                    db_clip_device = prefs.get("device", clip_device)
                    db_t5_bit_depth = prefs.get("t5_bit_depth", t5_bit_depth)
                    db_clip_names = [prefs.get(f"clip{i+1}", "") for i in range(4)]
                    
                    # Special handling for Flux in auto mode
                    if "FLUX" in architecture.upper() and any(db_clip_names):
                        flux_clip = self._load_flux_clips_properly(db_clip_names)
                        if flux_clip:
                            print("[CheckpointTester] Using preferred Flux CLIPs from database")
                            return flux_clip
                    
                    # Regular CLIP loading for non-Flux
                    for name in db_clip_names:
                        if name:
                            clip = self._load_clip_by_name(name, architecture, db_clip_type, db_clip_device, db_t5_bit_depth)
                            if clip:
                                db_clips.append(clip)
                
                if db_clips:
                    print("[CheckpointTester] Using preferred CLIPs from database")
                    clips_to_combine = db_clips
                    clip_type = db_clip_type
                    clip_device = db_clip_device
                    t5_bit_depth = db_t5_bit_depth
                else:
                    # Try architecture defaults
                    arch_defaults = self._get_default_clips_for_architecture(architecture)
                    if arch_defaults and "clips" in arch_defaults:
                        # Special handling for Flux defaults
                        if "FLUX" in architecture.upper():
                            flux_clip = self._load_flux_clips_properly(arch_defaults["clips"])
                            if flux_clip:
                                print(f"[CheckpointTester] Using architecture default Flux CLIPs for {architecture}")
                                return flux_clip
                        
                        # Regular default loading for non-Flux
                        arch_clips = []
                        arch_clip_type = arch_defaults.get("clip_type", clip_type)
                        for name in arch_defaults["clips"]:
                            clip = load_single_clip(name)
                            if clip:
                                arch_clips.append(clip)
                        if arch_clips:
                            print(f"[CheckpointTester] Using architecture default CLIPs for {architecture}")
                            clips_to_combine = arch_clips
                            clip_type = arch_clip_type

            if not final_clip and not clips_to_combine:
                print("[CheckpointTester] No CLIP could be loaded in auto mode")
                return None

        # Combine clips if needed (for non-Flux architectures)
        if not final_clip and clips_to_combine:
            final_clip = self._combine_clips(clips_to_combine, architecture, clip_type, clip_device, t5_bit_depth)

        # Debugging outputs
        print(f"[CheckpointTester] CLIP selection mode: {clip_mode}")
        print(f"[CheckpointTester] CLIP names requested: {clip_names}")
        print(f"[CheckpointTester] CLIPs loaded: {[str(c) for c in clips_to_combine]}")
        print(f"[CheckpointTester] Final combined CLIP: {final_clip}")

        if final_clip is None:
            print("[CheckpointTester] WARNING: CLIP selection/combination resulted in None.")

        return final_clip
        

    def _get_default_clips_for_architecture(self, arch: str) -> Dict:
        """Get recommended CLIP configurations based on architecture."""
        architecture_clip_map = {
            "SD1.5": {"clip_type": "single", "clips": ["clip_l.safetensors"]},
            "SD2.1": {"clip_type": "single", "clips": ["clip_l.safetensors"]},
            "SDXL": {"clip_type": "dual", "clips": ["clip_l.safetensors", "clip_g.safetensors"]},
            "SD3": {"clip_type": "triple", "clips": ["clip_l.safetensors", "clip_g.safetensors", "t5xxl_fp16.safetensors"]},
            "SD3.5 Large": {"clip_type": "triple", "clips": ["clip_l.safetensors", "clip_g.safetensors", "t5xxl_fp16.safetensors"]},
            "SD3.5 Medium": {"clip_type": "triple", "clips": ["clip_l.safetensors", "clip_g.safetensors", "t5xxl_fp16.safetensors"]},
            "Flux 1D": {"clip_type": "dual", "clips": ["clip_l.safetensors", "t5xxl_fp16.safetensors"]},
            "Flux 1S": {"clip_type": "dual", "clips": ["clip_l.safetensors", "t5xxl_fp16.safetensors"]},
            "FluxInpaint": {"clip_type": "dual", "clips": ["clip_l.safetensors", "t5xxl_fp16.safetensors"]},
            "Playground": {"clip_type": "dual", "clips": ["clip_l.safetensors", "clip_g.safetensors"]},
            "Illustrious": {"clip_type": "dual", "clips": ["clip_l.safetensors", "clip_g.safetensors"]},
            "Pony": {"clip_type": "dual", "clips": ["clip_l.safetensors", "clip_g.safetensors"]},
            "HiDream": {"clip_type": "dual", "clips": ["t5xxl_fp16.safetensors", "llama_text_encoder.safetensors"]},
        }
        return architecture_clip_map.get(arch, {"clip_type": "single", "clips": ["clip_l.safetensors"]})
        

    # --- Checkpoint Loading ---
    def _load_checkpoint_internal(self, checkpoint_path: str, vae_mode: str, vae_name: str,
                                clip_mode: str, clip_names: List[str], clip_type: str,
                                clip_device: str, t5_bit_depth: str) -> Tuple[Optional[Any], Optional[Any], Optional[Any], Optional[str]]:
        """
        Loads a checkpoint and its components, handling GGUF, Flux, SD3.5, SD3, and standard models.
        Returns: (model, clip, vae, latent_format_info)
        """
        model, clip, vae, latent_format = None, None, None, None
        model_name = os.path.basename(checkpoint_path)
        cp_hash = calculate_checkpoint_hash(checkpoint_path)
        cp_data = self.db_manager.get_checkpoint_data(cp_hash)

        if not cp_data:
            print(f"[CheckpointTester] No DB entry for {checkpoint_path}")
            return None, None, None, None

        model_type = cp_data.get("model_type", "checkpoint")
        arch = cp_data.get("architecture", "Unknown")
        self._ensure_checkpoint_inspected(cp_hash, checkpoint_path)

        print(f"[CheckpointTester] Loading {model_type}: {model_name} (Arch: {arch})")

        embedded_clip = None
        embedded_vae = None

        try:
            # --- GGUF (City96/ComfyUI-GGUF) ---
            if model_type == "gguf":
                if HAS_GGUF_SUPPORT:
                    try:
                        # Try ComfyUI's loader first
                        model, embedded_clip, embedded_vae, latent_format = comfy.sd.load_gguf(checkpoint_path)
                    except Exception as e:
                        print(f"[CheckpointTester] ComfyUI GGUF loader failed: {e}")
                        # Try fallback loader if you have one (e.g., gguf_sd_loader)
                        try:
                            from gguf_city96_loader import gguf_sd_loader
                            model, arch_str = gguf_sd_loader(checkpoint_path, return_arch=True)
                            latent_format = self._infer_latent_format_from_arch(arch_str)
                            embedded_clip = None
                            embedded_vae = None
                        except Exception as e2:
                            print(f"[CheckpointTester] Fallback GGUF loader failed: {e2}")
                            model = None
                else:
                    print("[CheckpointTester] ERROR: GGUF support not available.")
                    raise ImportError("GGUF support missing")

            # --- Flux (unet/diffusion) ---
            elif model_type in ["unet", "diffusion"]:
                if "Flux" in arch:
                    model = self._load_flux_model(os.path.basename(checkpoint_path), "unet")
                    if model is None:
                        print(f"[CheckpointTester] Flux unet loading failed, trying as regular checkpoint")
                        try:
                            model, embedded_clip, embedded_vae, latent_format = comfy.sd.load_checkpoint_guess_config(checkpoint_path)
                            print(f"[CheckpointTester] Successfully loaded Flux model as checkpoint")
                        except Exception as e:
                            print(f"[CheckpointTester] Checkpoint loading also failed: {e}")
                elif arch in ["SD3.5 Large", "SD3.5 Medium"]:
                    try:
                        sd3_module = importlib.import_module("comfy.sd3")
                        if hasattr(sd3_module, "load_model"):
                            model = sd3_module.load_model(checkpoint_path)
                        else:
                            model = comfy.sd.load_model(checkpoint_path)
                    except Exception as e:
                        print(f"[CheckpointTester] SD3.5 loader failed: {e}")
                        model = comfy.sd.load_model(checkpoint_path)
                else:
                    model = comfy.sd.load_model(checkpoint_path)
                latent_format = None  # No standard latent format object for these yet

            # --- Standard checkpoint (safetensors/pt/ckpt) ---
            else:
                # Use guess_config, potentially with arch-specific overrides
                load_func = comfy.sd.load_checkpoint_guess_config
                if arch in ["SD3", "SD3.5 Large", "SD3.5 Medium"]:
                    try:
                        sd3_module = importlib.import_module("comfy.sd3")
                        if hasattr(sd3_module, "load_checkpoint"):
                            print(f"[CheckpointTester] Using SD3-specific loader for {arch}")
                            load_func = sd3_module.load_checkpoint
                    except ImportError:
                        pass  # Use default if SD3 module not found

                model, embedded_clip, embedded_vae, latent_format = load_func(checkpoint_path)
                print(f"[DEBUG] load_func returned latent_format: {latent_format}")
                print(f"[DEBUG] latent_format type: {type(latent_format)}")

                # If latent_format is None, try to get it from the model
                if latent_format is None and model is not None:
                    print(f"[DEBUG] Attempting to extract latent format from model")
                    try:
                        if hasattr(model, 'latent_format'):
                            latent_format = model.latent_format
                            print(f"[DEBUG] Found latent_format on model: {latent_format}")
                        elif hasattr(model, 'model') and hasattr(model.model, 'latent_format'):
                            latent_format = model.model.latent_format
                            print(f"[DEBUG] Found latent_format on model.model: {latent_format}")
                        elif arch != "Unknown":
                            latent_format = self._infer_latent_format_from_arch(arch)
                            print(f"[DEBUG] Inferred latent_format from arch: {latent_format}")
                    except Exception as e:
                        print(f"[DEBUG] Error extracting latent format: {e}")

            if model is None:
                raise ValueError("Model loading failed.")

            # --- VAE Selection ---
            vae = self._handle_vae_selection(embedded_vae, vae_mode, vae_name, cp_hash, arch)

            # --- CLIP Selection ---
            clip = self._handle_clip_selection(embedded_clip, clip_mode, arch, clip_names, cp_hash, checkpoint_path, clip_type, clip_device, t5_bit_depth)

            # --- Latent Format Info ---
            latent_format_info = self._get_latent_format_info(latent_format)
            print(f"[DEBUG] _get_latent_format_info returned: {latent_format_info}")
            print(f"[CheckpointTester] Successfully loaded: {model_name}")
            return model, clip, vae, latent_format_info

        except Exception as e:
            print(f"[CheckpointTester] ERROR loading checkpoint {model_name}: {e}\n{traceback.format_exc()}")
            clear_gpu_memory()
            return None, None, None, None

    def _load_gguf_checkpoint(self, checkpoint_path: str, checkpoint_data: dict) -> Tuple:
        """Load GGUF format checkpoint."""
        try:
            # Use ComfyUI's GGUF loader if available
            if hasattr(comfy.sd, 'load_checkpoint_guess_config'):
                return comfy.sd.load_checkpoint_guess_config(
                    checkpoint_path,
                    output_vae=True,
                    output_clip=True,
                    embedding_directory=folder_paths.get_folder_paths("embeddings")
                )
            else:
                # Fallback method
                print(f"[CheckpointTester] GGUF loading not supported, using fallback")
                return None, None, None
                
        except Exception as e:
            print(f"[CheckpointTester] GGUF loading failed: {e}")
            return None, None, None

    def _load_standard_checkpoint(self, checkpoint_path: str, checkpoint_data: dict) -> Tuple:
        """Load standard checkpoint formats (.safetensors, .pt, .ckpt)."""
        try:
            # Use ComfyUI's standard loader
            return comfy.sd.load_checkpoint_guess_config(
                checkpoint_path,
                output_vae=True,
                output_clip=True,
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )
            
        except Exception as e:
            print(f"[CheckpointTester] Standard checkpoint loading failed: {e}")
            return None, None, None

    def _try_load_separate_clip(self, checkpoint_path: str, checkpoint_data: dict) -> Optional:
        """Try to load CLIP separately if embedded loading failed."""
        try:
            # Get CLIP preferences
            clip_prefs = checkpoint_data.get("clip_preferences", {})
            preferred_clips = [
                clip_prefs.get("clip1", ""),
                clip_prefs.get("clip2", ""), 
                clip_prefs.get("clip3", ""),
                clip_prefs.get("clip4", "")
            ]
            
            # Try to load preferred CLIPs
            for clip_name in preferred_clips:
                if clip_name and clip_name != "None":
                    try:
                        clip_path = folder_paths.get_full_path("clip", clip_name)
                        if clip_path:
                            clip = comfy.sd.load_clip(clip_path)
                            if clip:
                                return clip
                    except Exception:
                        continue
            
            # Fallback to default CLIP based on architecture
            arch = checkpoint_data.get("architecture", "Unknown")
            arch_defaults = self._get_default_clips_for_architecture(arch)  # Use your existing method
            if arch_defaults and "clips" in arch_defaults:
                for clip_name in arch_defaults["clips"]:
                    try:
                        clip_path = folder_paths.get_full_path("clip", clip_name)
                        if clip_path:
                            return comfy.sd.load_clip(clip_path)
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"[CheckpointTester] Separate CLIP loading failed: {e}")
        
        return None

    def _infer_latent_format_from_arch(self, arch: str) -> str:
        """Infer latent format info from architecture when not available directly."""
        # Create a simple string representation based on known architectures
        format_map = {
            "SD1.5": "SD VAE (scale: 0.18215)",
            "SD2.1": "SD VAE (scale: 0.18215)", 
            "SDXL": "SDXL VAE (scale: 0.13025)",
            "SD3": "SD3 VAE (scale: 1.5305)",
            "SD3.5 Large": "SD3 VAE (scale: 1.5305)",
            "SD3.5 Medium": "SD3 VAE (scale: 1.5305)",
            "Flux 1D": "Flux VAE (scale: 0.3611)",
            "Flux 1S": "Flux VAE (scale: 0.3611)",
            "Pony": "SDXL VAE (scale: 0.13025)",  # Pony uses SDXL format
        }
        
        # Check for exact match first
        if arch in format_map:
            return format_map[arch]
        
        # Check for partial matches
        for key, value in format_map.items():
            if key in arch or arch in key:
                return value
        
        return f"Unknown ({arch})"


    def _load_flux_model(self, model_name: str, model_dir_type: str) -> Optional[Any]:
        """Enhanced Flux model loading with format detection."""
        try:
            # Get the model path
            model_path = self._resolve_flux_model_path(model_name, model_dir_type)
            if not model_path:
                return None
            
            print(f"[CheckpointTester] Loading Flux model from: {model_path}")
            
            # Detect Flux model format and load accordingly
            flux_format = self._detect_flux_format(model_path, model_name)
            print(f"[CheckpointTester] Detected Flux format: {flux_format}")
            
            return self._load_flux_by_format(model_path, flux_format)
            
        except Exception as e:
            print(f"[CheckpointTester] Error in _load_flux_model: {e}")
            print(f"[CheckpointTester] Traceback: {traceback.format_exc()}")
            return None

    def _resolve_flux_model_path(self, model_name: str, model_dir_type: str) -> Optional[str]:
        """Resolve the full path for a Flux model across different locations."""
        model_path = None
        
        # Try unet/flux subfolder first for unet type
        if model_dir_type == "unet":
            flux_subfolder_path = os.path.join(folder_paths.models_dir, "unet", "flux", model_name)
            if os.path.exists(flux_subfolder_path):
                model_path = flux_subfolder_path
                print(f"[CheckpointTester] Found Flux model in unet/flux subfolder: {model_path}")
                return model_path
        
        # Try the specified folder type
        try:
            model_path = folder_paths.get_full_path(model_dir_type, model_name)
            print(f"[CheckpointTester] Found Flux model in {model_dir_type}: {model_path}")
            return model_path
        except:
            pass
        
        # Try common fallback locations
        fallback_types = ["diffusion_models", "checkpoints", "unet", "transformers"]
        for fallback_type in fallback_types:
            if fallback_type != model_dir_type:
                try:
                    model_path = folder_paths.get_full_path(fallback_type, model_name)
                    print(f"[CheckpointTester] Found Flux model in {fallback_type}: {model_path}")
                    return model_path
                except:
                    continue
        
        print(f"[CheckpointTester] ERROR: Could not resolve path for Flux model {model_name}")
        return None

    def _detect_flux_format(self, model_path: str, model_name: str) -> str:
        """Detect the format/type of Flux model from filename and file inspection."""
        filename = model_name.lower()
        file_ext = os.path.splitext(model_path)[1].lower()
        
        # 1. GGUF format detection
        if file_ext == ".gguf" or "gguf" in filename:
            return "gguf"
        
        # 2. Quantized format detection from filename
        quantization_indicators = ["q8", "nf4", "int8", "int4", "q4", "q6", "fp8", "bnb"]
        if any(indicator in filename for indicator in quantization_indicators):
            return "quantized"
        
        # 3. Transformer format detection
        transformer_indicators = ["transformer", "transformers", "hf", "huggingface"]
        if any(indicator in filename for indicator in transformer_indicators):
            return "transformer"
        
        # 4. File inspection for deeper detection
        try:
            if file_ext in [".safetensors", ".pt", ".ckpt"]:
                # Quick inspection of model structure
                if file_ext == ".safetensors" and HAS_SAFETENSORS:
                    with safe_open(model_path, framework="pt", device="meta") as f:
                        keys = list(f.keys())[:50]  # Sample first 50 keys
                else:
                    # For .pt/.ckpt, load minimal state dict info
                    state_dict = comfy.utils.load_torch_file(model_path, safe_load=True, device="meta")
                    keys = list(state_dict.keys())[:50] if state_dict else []
                
                # Check for format indicators in keys
                if any("quantized" in key.lower() or "int8" in key.lower() or "nf4" in key.lower() for key in keys):
                    return "quantized"
                
                # Check for transformer-style keys
                transformer_key_patterns = ["transformer.", "blocks.", "norm.", "mlp."]
                if any(pattern in key for key in keys for pattern in transformer_key_patterns):
                    if self._is_flux_transformer_format(keys):
                        return "transformer"
                
                # Check if it's a standard diffusion model
                diffusion_patterns = ["diffusion_model.", "model.diffusion_model.", "unet."]
                if any(pattern in key for key in keys for pattern in diffusion_patterns):
                    return "diffusion"
                
                # Check for standard checkpoint format
                checkpoint_patterns = ["cond_stage_model.", "first_stage_model.", "model."]
                if any(pattern in key for key in keys for pattern in checkpoint_patterns):
                    return "checkpoint"
                
                # If it has Flux-specific keys but no other format, assume unet
                if self._is_flux_model(set(keys)):
                    return "unet"
                    
        except Exception as e:
            print(f"[CheckpointTester] Error inspecting model format: {e}")
        
        # 5. Fallback based on file extension and location
        if file_ext in [".safetensors", ".pt", ".ckpt"]:
            # Check path for hints
            path_lower = model_path.lower()
            if "unet" in path_lower or "diffusion" in path_lower:
                return "unet"
            elif "checkpoint" in path_lower:
                return "checkpoint"
        
        # Default assumption
        return "unet"

    def _is_flux_transformer_format(self, keys: List[str]) -> bool:
        """Check if the keys indicate a transformer-format Flux model."""
        # Look for transformer-specific Flux patterns
        transformer_flux_patterns = [
            "transformer.h.",
            "transformer.ln_f.",
            "transformer.wte.",
            "lm_head.",
            "blocks.0.attn.",
            "blocks.0.mlp."
        ]
        return any(pattern in key for key in keys for pattern in transformer_flux_patterns)

    def _load_flux_by_format(self, model_path: str, flux_format: str) -> Optional[Any]:
        """Load Flux model based on detected format."""
        print(f"[CheckpointTester] Loading Flux model using {flux_format} method")
        
        try:
            if flux_format == "gguf":
                return self._load_flux_gguf(model_path)
            elif flux_format == "quantized":
                return self._load_flux_quantized(model_path)
            elif flux_format == "transformer":
                return self._load_flux_transformer(model_path)
            elif flux_format == "checkpoint":
                return self._load_flux_checkpoint(model_path)
            elif flux_format == "diffusion":
                return self._load_flux_diffusion(model_path)
            elif flux_format == "unet":
                return self._load_flux_unet(model_path)
            else:
                # Unknown format, try multiple methods
                return self._load_flux_fallback(model_path)
                
        except Exception as e:
            print(f"[CheckpointTester] {flux_format} loading failed: {e}")
            # Try fallback methods
            return self._load_flux_fallback(model_path)

    def _load_flux_gguf(self, model_path: str) -> Optional[Any]:
        """Load GGUF format Flux model."""
        try:
            # Try ComfyUI's GGUF loader
            if hasattr(comfy.sd, 'load_gguf'):
                model, _, _, _ = comfy.sd.load_gguf(model_path)
                return model
            else:
                print("[CheckpointTester] ComfyUI GGUF loader not available")
                return None
        except Exception as e:
            print(f"[CheckpointTester] GGUF loading failed: {e}")
            return None

    def _load_flux_quantized(self, model_path: str) -> Optional[Any]:
        """Load quantized Flux model (NF4, Q8, etc.)."""
        try:
            # Check if we have quantization support
            try:
                import bitsandbytes as bnb
                has_bnb = True
            except ImportError:
                has_bnb = False
            
            if has_bnb:
                # Try loading with quantization support
                # This would require specific quantized model loaders
                # For now, try standard loading and let ComfyUI handle it
                pass
            
            # Try ComfyUI's standard loaders (they might handle quantization)
            return self._load_flux_unet(model_path)
            
        except Exception as e:
            print(f"[CheckpointTester] Quantized loading failed: {e}")
            return None

    def _load_flux_transformer(self, model_path: str) -> Optional[Any]:
        """Load transformer-format Flux model."""
        try:
            # Try using transformers library approach if available
            try:
                from transformers import AutoModel
                # This would need specific Flux transformer implementation
                # For now, fallback to standard methods
            except ImportError:
                pass
            
            # Try ComfyUI's transformer model loader if available
            if hasattr(comfy.sd, 'load_transformer'):
                return comfy.sd.load_transformer(model_path)
            else:
                # Fallback to standard loading
                return self._load_flux_unet(model_path)
                
        except Exception as e:
            print(f"[CheckpointTester] Transformer loading failed: {e}")
            return None

    def _load_flux_checkpoint(self, model_path: str) -> Optional[Any]:
        """Load checkpoint-format Flux model."""
        try:
            model, _, _, _ = comfy.sd.load_checkpoint_guess_config(model_path)
            return model
        except Exception as e:
            print(f"[CheckpointTester] Checkpoint loading failed: {e}")
            return None

    def _load_flux_diffusion(self, model_path: str) -> Optional[Any]:
        """Load diffusion-format Flux model."""
        try:
            if hasattr(comfy.sd, 'load_diffusion_model'):
                return comfy.sd.load_diffusion_model(model_path)
            else:
                return self._load_flux_unet(model_path)
        except Exception as e:
            print(f"[CheckpointTester] Diffusion loading failed: {e}")
            return None

    def _load_flux_unet(self, model_path: str) -> Optional[Any]:
        """Load UNet-format Flux model."""
        try:
            # Method 1: Try ComfyUI's UNet loader
            if hasattr(comfy.sd, 'load_unet'):
                return comfy.sd.load_unet(model_path)
            
            # Method 2: Manual loading with proper config detection
            unet_state_dict = comfy.utils.load_torch_file(model_path, safe_load=True)
            
            # Get model configuration
            model_config = comfy.model_detection.model_config_from_unet(
                unet_state_dict, 
                "", 
                use_base_if_no_match=True
            )
            
            if model_config is None:
                print(f"[CheckpointTester] Could not detect model config")
                return None
            
            # Use ComfyUI's model management for proper loading
            load_device = comfy.model_management.get_torch_device()
            manual_cast_dtype = comfy.model_management.unet_manual_cast(
                load_device, 
                comfy.model_management.unet_dtype(load_device)
            )
            model_config.set_inference_dtype(
                comfy.model_management.unet_dtype(load_device), 
                manual_cast_dtype
            )
            
            # Create the model properly
            model = model_config.get_model(unet_state_dict, "")
            model.load_model_weights(unet_state_dict, "")
            
            return model
            
        except Exception as e:
            print(f"[CheckpointTester] UNet loading failed: {e}")
            return None

    def _load_flux_fallback(self, model_path: str) -> Optional[Any]:
        """Try multiple loading methods as fallback."""
        loading_methods = [
            ("UNet loader", self._load_flux_unet),
            ("Diffusion loader", self._load_flux_diffusion),
            ("Checkpoint loader", self._load_flux_checkpoint),
        ]
        
        for method_name, method_func in loading_methods:
            try:
                print(f"[CheckpointTester] Trying {method_name}")
                result = method_func(model_path)
                if result is not None:
                    print(f"[CheckpointTester] Successfully loaded with {method_name}")
                    return result
            except Exception as e:
                print(f"[CheckpointTester] {method_name} failed: {e}")
                continue
        
        print(f"[CheckpointTester] All loading methods failed for {model_path}")
        return None
        
            


    def _get_latent_format_info(self, latent_format: Optional[Any]) -> str:
        """Get readable string from latent format object."""
        print(f"[DEBUG] _get_latent_format_info called with: {latent_format}")
        print(f"[DEBUG] latent_format type: {type(latent_format)}")
        
        if latent_format is None: 
            print(f"[DEBUG] latent_format is None, returning 'None'")
            return "No Latent Format"
        
        try:
            # Get the class name
            class_name = latent_format.__class__.__name__
            info = [class_name]

            print(f"[DEBUG] class name: {class_name}")
            
            # Check for various scale attributes
            scale_attrs = ["scale_factor", "scale", "scaling_factor"]
            for attr in scale_attrs:
                if hasattr(latent_format, attr):
                    value = getattr(latent_format, attr)
                    info.append(f"{attr}:{value:.4f}")
                    print(f"[DEBUG] {attr}: {value}")
            
            # Check for other common attributes
            if hasattr(latent_format, "channels"):
                info.append(f"channels:{latent_format.channels}")
            
            result = ", ".join(info)
            print(f"[DEBUG] returning latent format info: {result}")
            return result
        except Exception as e:
            print(f"[DEBUG] Error in _get_latent_format_info: {e}")
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    # --- Main Processing ---
    def process_checkpoints(self, dir_search_terms: str, file_search_terms: str,
                        additional_path: str, architecture: str, category: str, notes_search: str,
                        seed: int, vae_mode: str, vae_name: str, clip_mode: str,
                        clip1_name: str, clip2_name: str, clip3_name: str, clip4_name: str,
                        clip_type: str, clip_device: str, t5_bit_depth: str, **kwargs) -> Tuple:
        """Enhanced checkpoint processing with better CLIP handling."""
        
        print(f"[CheckpointTester] Processing request with seed: {seed}")
        if additional_path:
            self.scan_checkpoints(additional_path)
        
        self.filter_checkpoints(dir_search_terms, file_search_terms, architecture, category, notes_search)
        
        checkpoint_list_text = self.get_checkpoint_list_text()
        missing_info_list_text = self.get_missing_info_list_text()
        total_checkpoints = len(self.checkpoint_paths)
        selected_checkpoints_count = len(self.filtered_checkpoints)
        
        model, clip, vae, latent_format_info = None, None, None, "None"
        model_name, model_path = "None", ""
        prompt_embed = None
        
        if not self.filtered_checkpoints:
            print("[CheckpointTester] No checkpoints match filters.")
        else:
            # Determine control mode and target index
            control_mode, target_index = self._determine_selection(seed, len(self.filtered_checkpoints))
            print(f"[CheckpointTester] Control mode: {control_mode}, Target index: {target_index}")
            
            # Attempt to load the selected checkpoint
            checkpoint_path = self.filtered_checkpoints[target_index]
            model_name = os.path.basename(checkpoint_path)
            model_path = checkpoint_path
            
            clip_names = [clip1_name, clip2_name, clip3_name, clip4_name]
            model, clip, vae, latent_format_info = self._load_checkpoint_internal(
                checkpoint_path, vae_mode, vae_name, clip_mode, clip_names,
                clip_type, clip_device, t5_bit_depth
            )
            
            # FIXED: Only change to error values if model failed to load
            if model is None:
                model_name = "Load Failed"
                model_path = ""
                latent_format_info = "None"
            
            
            # TODO: PROMPT ENCODING - Commented out for now
            # Will implement architecture-specific prompt encoding later
            # This requires different handling for SD1.5, SDXL, SD3, Flux, etc.
            """
            # Handle prompt encoding if model and clip loaded successfully
            if model and clip and prompt and prompt.strip():
                try:
                    print(f"[CheckpointTester] Encoding prompt: '{prompt[:50]}...' with CLIP type: {type(clip)}")
                    
                    # Try different encoding methods based on CLIP type
                    if hasattr(clip, 'encode'):
                        # Most ComfyUI clips use this method
                        conditioning = clip.encode(prompt)
                    elif hasattr(clip, 'encode_from_tokens'):
                        # Some clips use tokenize + encode_from_tokens
                        if hasattr(clip, 'tokenize'):
                            tokens = clip.tokenize(prompt)
                            conditioning = clip.encode_from_tokens(tokens)
                        else:
                            print(f"[CheckpointTester] CLIP has encode_from_tokens but no tokenize method")
                            conditioning = None
                    else:
                        print(f"[CheckpointTester] CLIP object has no known encoding method")
                        conditioning = None
                    
                    if conditioning is not None:
                        # Handle different conditioning formats
                        if isinstance(conditioning, list) and len(conditioning) > 0:
                            if isinstance(conditioning[0], list) and len(conditioning[0]) > 0:
                                prompt_embed = conditioning[0][0]  # Extract tensor from [[tensor, dict]]
                            else:
                                prompt_embed = conditioning[0]  # Extract from [tensor]
                        else:
                            prompt_embed = conditioning  # Direct tensor
                        
                        print(f"[CheckpointTester] Successfully encoded prompt")
                        if hasattr(prompt_embed, 'shape'):
                            print(f"[CheckpointTester] Embedding shape: {prompt_embed.shape}")
                    else:
                        print(f"[CheckpointTester] Warning: Prompt encoding returned None")
                        
                except Exception as e_encode:
                    print(f"[CheckpointTester] Failed to encode prompt: {e_encode}")
                    print(f"[CheckpointTester] Traceback: {traceback.format_exc()}")
            elif prompt and prompt.strip() and not clip:
                print(f"[CheckpointTester] Cannot encode prompt - no CLIP model loaded")
            elif prompt and prompt.strip() and not model:
                print(f"[CheckpointTester] Cannot encode prompt - no model loaded")
            """

        # Debugging outputs
        print(f"[DEBUG] Pre-return type check:")
        print(f"[DEBUG]   model: {type(model)} = {model}")
        print(f"[DEBUG]   clip: {type(clip)} = {clip}")
        print(f"[DEBUG]   vae: {type(vae)} = {vae}")
        print(f"[DEBUG]   latent_format_info: {type(latent_format_info)} = {latent_format_info}")
        print(f"[DEBUG]   model_name: {type(model_name)} = {model_name}")
        print(f"[DEBUG]   model_path: {type(model_path)} = {model_path}")
        print(f"[DEBUG]   prompt_embed: {type(prompt_embed)} = {prompt_embed}")
        
        # Save state for next run
        self.last_seed = seed
        self.current_index = target_index if 'target_index' in locals() else self.current_index
        self.db_manager.set_current_index(self.current_index)
        self.db_manager.save()
        
        # REMOVED: The problematic reassignment lines
        # Don't overwrite the values if they were set correctly above
        
        if clip is None and clip_mode != "none":
            print("[CheckpointTester] WARNING: No CLIP model available! Text encoding will fail!")
        
        # Ensure string types
        latent_format_info = str(latent_format_info) if latent_format_info is not None else "None"
        model_name = str(model_name) if model_name is not None else "None"
        model_path = str(model_path) if model_path is not None else ""
        checkpoint_list_text = str(checkpoint_list_text)
        missing_info_list_text = str(missing_info_list_text)
        
        # Final debug before return
        print(f"[DEBUG FINAL] Returning values:")
        print(f"[DEBUG FINAL]   model_name: '{model_name}'")
        print(f"[DEBUG FINAL]   model_path: '{model_path}'")
        print(f"[DEBUG FINAL]   latent_format_info: '{latent_format_info}'")
        
        return (model, clip, vae, latent_format_info, model_name, model_path,
                checkpoint_list_text, total_checkpoints, selected_checkpoints_count,
                missing_info_list_text, prompt_embed)


    def _determine_selection(self, seed: int, num_filtered: int) -> Tuple[str, int]:
        """Determine control mode and target index based on seed."""
        if num_filtered == 0:
            return "fixed", 0

        control_mode = "fixed"
        if self.last_seed is not None and seed != self.last_seed:
            if seed == -1:
                control_mode = "random"
            elif seed > 0:
                control_mode = "fixed"
            elif seed < 0:
                control_mode = "increment"
        else:
            control_mode = "fixed"

        target_index = 0
        if control_mode == "fixed":
            # Support 1-based selection for in-range seeds and wrap large seeds via modulo
            if seed > 0:
                if seed <= num_filtered:
                    target_index = seed - 1
                else:
                    target_index = seed % num_filtered
            else:
                target_index = 0
        elif control_mode == "increment":
            target_index = (self.current_index + 1) % num_filtered
        elif control_mode == "decrement":
            target_index = (self.current_index - 1) % num_filtered
        elif control_mode == "random":
            import random
            target_index = random.randint(0, num_filtered - 1)
            self.current_index = target_index  # <-- update current_index after random selection

        # Ensure index is valid
        target_index = max(0, min(num_filtered - 1, target_index))
        self.current_index = target_index  # <-- always update current_index
        return control_mode, target_index

# --- Info Setter Node ---

class CheckpointInfoSetterNode(BaseCheckpointNode):
    """Node for setting metadata for a single checkpoint."""
    @classmethod
    def INPUT_TYPES(cls):
        clip_list = get_clean_clip_list()
        vae_list = get_clean_vae_list() # Use clean list here too
        return {
            "required": {
                "checkpoint_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Path to the checkpoint file"}),
                "architecture": (["Unknown"] + list(KNOWN_ARCHITECTURES.keys()), {"default": "Unknown", "tooltip": "Model architecture"}),
                "has_embedded_vae": ("BOOLEAN", {"default": True, "tooltip": "Whether the checkpoint has an embedded VAE"}),
                "has_embedded_clip": ("BOOLEAN", {"default": True, "tooltip": "Whether the checkpoint has an embedded CLIP"}),
                "clip_type": (["auto", "single", "dual", "triple", "quad"] + list(KNOWN_ARCHITECTURES.keys()), {"default": "auto", "tooltip": "CLIP structure type or specific combiner"}),
                "category": (["unknown", "art", "illustration", "painting", "realistic", "cinema", "anime", "3d", "concept art", "portrait", "landscape", "photographic", "dreamlike", "character", "sci-fi", "fantasy", "abstract", "other"], {"default": "unknown", "tooltip": "Model category"}),
                "preferred_vae": (vae_list, {"default": "None", "tooltip": "Preferred VAE"}),
                "preferred_clip1": (clip_list, {"default": "None", "tooltip": "Preferred primary CLIP"}),
                "preferred_clip2": (clip_list, {"default": "None", "tooltip": "Preferred secondary CLIP"}),
                "preferred_clip3": (clip_list, {"default": "None", "tooltip": "Preferred tertiary CLIP"}),
                "preferred_clip4": (clip_list, {"default": "None", "tooltip": "Preferred quaternary CLIP"}),
                "clip_device": (["default", "CPU", "GPU"], {"default": "default", "tooltip": "Preferred device for CLIPs"}),
                "t5_bit_depth": (["auto", "fp16", "bf16", "fp32", "fp8", "fp8_e4m3fn"], {"default": "auto", "tooltip": "Preferred T5 bit depth"}),
                "notes": ("STRING", {"default": "", "multiline": True, "tooltip": "Additional notes"}),
            },
            "optional": {
                # Add generation params as optional inputs
                "sampler": (comfy.samplers.KSampler.SAMPLERS, {"default": DEFAULT_GENERATION_PARAMS["sampler"]}),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": DEFAULT_GENERATION_PARAMS["scheduler"]}),
                "steps": ("INT", {"default": DEFAULT_GENERATION_PARAMS["steps"], "min": 1, "max": 1000}),
                "cfg": ("FLOAT", {"default": DEFAULT_GENERATION_PARAMS["cfg"], "min": 0.0, "max": 100.0, "step": 0.1}),
                "clip_skip": ("INT", {"default": DEFAULT_GENERATION_PARAMS["clip_skip"], "min": 1, "max": 12}),
                "width": ("INT", {"default": DEFAULT_GENERATION_PARAMS["width"], "min": 64, "max": 8192, "step": 8}),
                "height": ("INT", {"default": DEFAULT_GENERATION_PARAMS["height"], "min": 64, "max": 8192, "step": 8}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "set_checkpoint_info"
    CATEGORY = "loaders/checkpoint tester"

    def set_checkpoint_info(self, checkpoint_path: str, architecture: str, has_embedded_vae: bool,
                            has_embedded_clip: bool, clip_type: str, category: str,
                            preferred_vae: str, preferred_clip1: str, preferred_clip2: str,
                            preferred_clip3: str, preferred_clip4: str, clip_device: str,
                            t5_bit_depth: str, notes: str, **kwargs) -> Tuple[str]:
        """Set metadata for a specific checkpoint."""
        if not checkpoint_path or not os.path.exists(checkpoint_path):
            return (f"Error: Checkpoint file not found or path empty.",)

        cp_hash = calculate_checkpoint_hash(checkpoint_path)
        cp_data = self.db_manager.get_checkpoint_data(cp_hash)

        if cp_data is None: # Add if not exists
             cp_data = {"path": checkpoint_path, "name": os.path.basename(checkpoint_path)}
             self.db_manager.update_checkpoint_data(cp_hash, cp_data) # Add basic info first
             cp_data = self.db_manager.get_checkpoint_data(cp_hash) # Re-fetch to ensure structure

        update_data = {
            "architecture": architecture,
            "has_vae": has_embedded_vae,
            "has_clip": has_embedded_clip,
            "clip_type": clip_type, # Store the detected/set type
            "category": category,
            "notes": notes,
            "preferred_vae": "" if preferred_vae == "None" else preferred_vae,
            "clip_preferences": {
                "clip1": "" if preferred_clip1 == "None" else preferred_clip1,
                "clip2": "" if preferred_clip2 == "None" else preferred_clip2,
                "clip3": "" if preferred_clip3 == "None" else preferred_clip3,
                "clip4": "" if preferred_clip4 == "None" else preferred_clip4,
                "clip_type": clip_type, # Store preference too
                "device": clip_device,
                "t5_bit_depth": t5_bit_depth,
            },
            "generation_params": {
                "sampler": kwargs.get("sampler", DEFAULT_GENERATION_PARAMS["sampler"]),
                "scheduler": kwargs.get("scheduler", DEFAULT_GENERATION_PARAMS["scheduler"]),
                "steps": kwargs.get("steps", DEFAULT_GENERATION_PARAMS["steps"]),
                "cfg": kwargs.get("cfg", DEFAULT_GENERATION_PARAMS["cfg"]),
                "clip_skip": kwargs.get("clip_skip", DEFAULT_GENERATION_PARAMS["clip_skip"]),
                "batch_size": 1, # Batch size usually not set per checkpoint
                "width": kwargs.get("width", DEFAULT_GENERATION_PARAMS["width"]),
                "height": kwargs.get("height", DEFAULT_GENERATION_PARAMS["height"]),
            }
        }
        self.db_manager.update_checkpoint_data(cp_hash, update_data)
        self.db_manager.save()
        return (f"Successfully updated info for {os.path.basename(checkpoint_path)}",)

# --- Batch Info Setter Node ---

class CheckpointBatchInfoSetterNode(BaseCheckpointNode):
    """Node for batch setting metadata for multiple checkpoints."""
    @classmethod
    def INPUT_TYPES(cls):
        # Reuse inputs from single setter where applicable
        single_inputs = CheckpointInfoSetterNode.INPUT_TYPES()["required"]
        single_optional = CheckpointInfoSetterNode.INPUT_TYPES()["optional"]
        return {
            "required": {
                "dir_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Directory containing checkpoints"}),
                "recursive": ("BOOLEAN", {"default": True, "tooltip": "Scan subdirectories recursively"}),
                "file_pattern": ("STRING", {"default": "*.safetensors", "multiline": False, "tooltip": "Pattern to match filenames"}),
                **{k: v for k, v in single_inputs.items() if k != 'checkpoint_path'} # Copy relevant inputs
            },
            "optional": {
                 **single_optional # Copy optional generation params
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "batch_set_info"
    CATEGORY = "loaders/checkpoint tester"

    def batch_set_info(self, dir_path: str, recursive: bool, file_pattern: str, **kwargs) -> Tuple[str]:
        """Set metadata for multiple checkpoints in a directory."""
        if not dir_path or not os.path.isdir(dir_path):
            return (f"Error: Directory not found or path empty.",)

        pattern = os.path.join(dir_path, "**" if recursive else "", file_pattern)
        checkpoint_files = glob.glob(pattern, recursive=recursive)

        if not checkpoint_files:
            return (f"Error: No files matching pattern '{file_pattern}' found in {dir_path}",)

        updated_count = 0
        setter_node = CheckpointInfoSetterNode() # Use instance for setting logic

        for cp_path in checkpoint_files:
            try:
                # Call the single setter's logic for each file
                status = setter_node.set_checkpoint_info(checkpoint_path=cp_path, **kwargs)
                if status[0].startswith("Success"):
                    updated_count += 1
            except Exception as e:
                 print(f"[CheckpointTester] Error batch setting info for {cp_path}: {e}")

        # Save DB once after all updates (handled by single setter's save)
        return (f"Attempted update for {len(checkpoint_files)} files. Successfully updated info for {updated_count} checkpoints.",)


# --- Params Loader Node ---

class CheckpointParamsLoaderNode(BaseCheckpointNode):
    """Node for loading saved generation parameters for a checkpoint."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"checkpoint_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Path to the checkpoint file"})}}

    RETURN_TYPES = ("STRING", "STRING", "INT", "FLOAT", "INT", "INT", "INT", # Gen Params
                    "STRING", "STRING", # VAE Pref, CLIP Type Pref
                    "STRING", "STRING", "STRING", "STRING", # CLIP Prefs 1-4
                    "STRING", "STRING") # CLIP Device, T5 Depth Prefs
    RETURN_NAMES = ("sampler", "scheduler", "steps", "cfg", "clip_skip", "width", "height",
                    "preferred_vae", "clip_type_pref",
                    "preferred_clip1", "preferred_clip2", "preferred_clip3", "preferred_clip4",
                    "clip_device_pref", "t5_bit_depth_pref")
    FUNCTION = "load_params"
    CATEGORY = "loaders/checkpoint tester"

    def load_params(self, checkpoint_path: str) -> Tuple:
        """Load saved parameters and preferences for a checkpoint."""
        gen_params = DEFAULT_GENERATION_PARAMS.copy()
        clip_prefs = DEFAULT_CLIP_PREFERENCES.copy()
        preferred_vae = "None"

        if checkpoint_path and os.path.exists(checkpoint_path):
            cp_hash = calculate_checkpoint_hash(checkpoint_path)
            cp_data = self.db_manager.get_checkpoint_data(cp_hash)
            if cp_data:
                gen_params.update(cp_data.get("generation_params", {}))
                clip_prefs.update(cp_data.get("clip_preferences", {}))
                preferred_vae = cp_data.get("preferred_vae", "") or "None"

        return (gen_params["sampler"], gen_params["scheduler"], gen_params["steps"], gen_params["cfg"],
                gen_params["clip_skip"], gen_params["width"], gen_params["height"],
                preferred_vae, clip_prefs["clip_type"],
                clip_prefs["clip1"] or "None", clip_prefs["clip2"] or "None",
                clip_prefs["clip3"] or "None", clip_prefs["clip4"] or "None",
                clip_prefs["device"], clip_prefs["t5_bit_depth"])

# --- Info Viewer Node ---

class CheckpointInfoViewerNode(BaseCheckpointNode):
    """Node for viewing detailed information about a checkpoint."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"checkpoint_path": ("STRING", {"default": "", "multiline": False, "tooltip": "Path to the checkpoint file"})}}

    RETURN_TYPES = ("STRING", "STRING", "STRING", "BOOLEAN", "BOOLEAN", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model_name", "architecture", "model_type", "has_vae", "has_clip",
                    "clip_type", "category", "notes", "preferences", "generation_params")
    FUNCTION = "view_info"
    CATEGORY = "loaders/checkpoint tester"

    def view_info(self, checkpoint_path: str) -> Tuple:
        """View information about a checkpoint."""
        # Defaults
        info = {
            "model_name": os.path.basename(checkpoint_path) if checkpoint_path else "N/A",
            "architecture": "Unknown", "model_type": "Unknown", "has_vae": False, "has_clip": False,
            "clip_type": "none", "category": "unknown", "notes": "",
            "preferences": "None set", "generation_params": "Defaults"
        }

        if checkpoint_path and os.path.exists(checkpoint_path):
            cp_hash = calculate_checkpoint_hash(checkpoint_path)
            cp_data = self.db_manager.get_checkpoint_data(cp_hash)
            if cp_data:
                info["model_name"] = cp_data.get("name", info["model_name"])
                info["architecture"] = cp_data.get("architecture", info["architecture"])
                info["model_type"] = cp_data.get("model_type", info["model_type"])
                info["has_vae"] = cp_data.get("has_vae", info["has_vae"])
                info["has_clip"] = cp_data.get("has_clip", info["has_clip"])
                info["clip_type"] = cp_data.get("clip_type", info["clip_type"])
                info["category"] = cp_data.get("category", info["category"])
                info["notes"] = cp_data.get("notes", info["notes"])

                # Format preferences
                prefs_lines = []
                pref_vae = cp_data.get("preferred_vae")
                if pref_vae: prefs_lines.append(f"VAE: {pref_vae}")
                clip_prefs = cp_data.get("clip_preferences", {})
                clip_lines = [f"{i+1}: {clip_prefs[f'clip{i+1}']}" for i in range(4) if clip_prefs.get(f'clip{i+1}')]
                if clip_lines: prefs_lines.append("CLIPs:\n  " + "\n  ".join(clip_lines))
                if clip_prefs.get("clip_type", "auto") != "auto": prefs_lines.append(f"CLIP Type: {clip_prefs['clip_type']}")
                if clip_prefs.get("device", "default") != "default": prefs_lines.append(f"CLIP Device: {clip_prefs['device']}")
                if clip_prefs.get("t5_bit_depth", "auto") != "auto": prefs_lines.append(f"T5 Depth: {clip_prefs['t5_bit_depth']}")
                info["preferences"] = "\n".join(prefs_lines) if prefs_lines else "None set"

                # Format generation params
                gen_params = cp_data.get("generation_params", {})
                if gen_params and gen_params != DEFAULT_GENERATION_PARAMS:
                     info["generation_params"] = "\n".join(f"{k}: {v}" for k, v in gen_params.items())
                else: info["generation_params"] = "Defaults"

        return (info["model_name"], info["architecture"], info["model_type"], info["has_vae"], info["has_clip"],
                info["clip_type"], info["category"], info["notes"], info["preferences"], info["generation_params"])

# --- Node Registration ---

NODE_CLASS_MAPPINGS = {
    "CheckpointTester_v074": CheckpointTesterNode,
    "CheckpointInfoSetter_v074": CheckpointInfoSetterNode,
    "CheckpointBatchInfoSetter_v074": CheckpointBatchInfoSetterNode,
    "CheckpointParamsLoader_v074": CheckpointParamsLoaderNode,
    "CheckpointInfoViewer_v074": CheckpointInfoViewerNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CheckpointTester_v074": "Checkpoint Tester v074",
    "CheckpointInfoSetter_v074": "Checkpoint Info Setter v074",
    "CheckpointBatchInfoSetter_v074": "Checkpoint Batch Info Setter v074",
    "CheckpointParamsLoader_v074": "Checkpoint Params Loader v074",
    "CheckpointInfoViewer_v074": "Checkpoint Info Viewer v074"
}