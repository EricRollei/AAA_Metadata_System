"""
Multi-LoRA Loader for Flux
Platform-specific loader for Flux LoRAs
Filters to show only LoRAs in L:\stable-diffusion-webui\models\Lora\Flux

This loader includes CLIP support for Flux image generation workflows.

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
from typing import Tuple, Any
from .Multi_LoRA_Loader_Base import MultiLoRALoaderBase


class MultiLoRALoaderFlux(MultiLoRALoaderBase):
    """
    Multi-LoRA loader specifically for Flux LoRAs.
    Only shows LoRAs from the Flux directory.
    Includes CLIP support.
    """
    
    # Platform-specific configuration
    PLATFORM_NAME = "Flux"
    PLATFORM_DIRECTORY_FILTER = "Flux"  # Will scan Lora\Flux
    REQUIRES_CLIP = True  # Flux uses CLIP
    DEFAULT_ARCHITECTURE = "Flux"
    MAX_LORA_SLOTS = 8
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get platform-filtered LoRAs (only from Flux directory)
        try:
            lora_options = ["None"] + cls._get_platform_filtered_loras()
        except Exception as e:
            lora_options = ["None"]
        
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                
                # Simplified filters (directory filter is already applied by platform)
                "search_filename": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in LoRA filenames. Use commas to separate multiple terms."}),
                "search_category": (["Any", "unknown", "style", "character", "concept", "pose", 
                    "clothing", "background", "effect", "artistic", "photographic", 
                    "lighting", "mood", "texture", "enhancement"], {"default": "Any",
                    "tooltip": "Filter by LoRA category"}),
                "search_trigger_word": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in trigger words from database."}),
                "min_rating": ("INT", {"default": 0, "min": 0, "max": 5,
                    "tooltip": "Minimum quality rating from database (0 = show all)"}),
                
                # Refresh control
                "refresh_lists": ("BOOLEAN", {"default": False,
                    "tooltip": "Toggle to refresh LoRA list"}),
                
                # Civitai integration
                "query_civitai": ("BOOLEAN", {"default": False,
                    "tooltip": "Automatically query Civitai for trigger words"}),
                "force_civitai_fetch": ("BOOLEAN", {"default": False,
                    "tooltip": "Force fetch from Civitai even if tags exist"}),
                
                # Trigger word settings
                "trigger_position": (["front", "back"], {"default": "front"}),
                "trigger_separator": ("STRING", {"default": ", "}),
                
                # LoRA slots (WITH CLIP)
                "lora_1_enable": ("BOOLEAN", {"default": False}),
                "lora_1_name": (lora_options, {"default": "None"}),
                "lora_1_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_1_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_2_enable": ("BOOLEAN", {"default": False}),
                "lora_2_name": (lora_options, {"default": "None"}),
                "lora_2_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_2_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_3_enable": ("BOOLEAN", {"default": False}),
                "lora_3_name": (lora_options, {"default": "None"}),
                "lora_3_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_3_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_4_enable": ("BOOLEAN", {"default": False}),
                "lora_4_name": (lora_options, {"default": "None"}),
                "lora_4_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_4_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_5_enable": ("BOOLEAN", {"default": False}),
                "lora_5_name": (lora_options, {"default": "None"}),
                "lora_5_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_5_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_6_enable": ("BOOLEAN", {"default": False}),
                "lora_6_name": (lora_options, {"default": "None"}),
                "lora_6_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_6_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_7_enable": ("BOOLEAN", {"default": False}),
                "lora_7_name": (lora_options, {"default": "None"}),
                "lora_7_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_7_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_8_enable": ("BOOLEAN", {"default": False}),
                "lora_8_name": (lora_options, {"default": "None"}),
                "lora_8_strength": ("FLOAT", {"default": 0.8, "min": -10.0, "max": 10.0, "step": 0.01}),
                "lora_8_clip_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            }
        }
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Trigger update when search parameters or refresh toggle changes
        search_params = [
            kwargs.get('search_filename', ''),
            kwargs.get('search_category', 'Any'),
            kwargs.get('search_trigger_word', ''),
            kwargs.get('min_rating', 0),
            kwargs.get('refresh_lists', False),
            kwargs.get('query_civitai', False),
            kwargs.get('force_civitai_fetch', False)
        ]
        return str(search_params) + str(hash(str(search_params)))
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "prompt", "prompt_with_triggers", "loaded_loras_info", "all_trigger_words", "filter_info", "filtered_loras_list")
    FUNCTION = "load_multi_loras"
    CATEGORY = "loaders/multi-lora/flux"
    
    def load_multi_loras(self, model, clip, prompt: str,
                        search_filename: str, search_category: str,
                        search_trigger_word: str, min_rating: int,
                        refresh_lists: bool, query_civitai: bool, force_civitai_fetch: bool,
                        trigger_position: str, trigger_separator: str,
                        # LoRA parameters (WITH CLIP)
                        lora_1_enable: bool, lora_1_name: str, lora_1_strength: float, lora_1_clip_strength: float,
                        lora_2_enable: bool, lora_2_name: str, lora_2_strength: float, lora_2_clip_strength: float,
                        lora_3_enable: bool, lora_3_name: str, lora_3_strength: float, lora_3_clip_strength: float,
                        lora_4_enable: bool, lora_4_name: str, lora_4_strength: float, lora_4_clip_strength: float,
                        lora_5_enable: bool, lora_5_name: str, lora_5_strength: float, lora_5_clip_strength: float,
                        lora_6_enable: bool, lora_6_name: str, lora_6_strength: float, lora_6_clip_strength: float,
                        lora_7_enable: bool, lora_7_name: str, lora_7_strength: float, lora_7_clip_strength: float,
                        lora_8_enable: bool, lora_8_name: str, lora_8_strength: float, lora_8_clip_strength: float
                        ) -> Tuple[Any, Any, str, str, str, str, str, str]:
        """Load multiple LoRAs for Flux (with CLIP)"""
        
        # Get filtered LoRAs info for display
        filtered_lora_paths = self._filter_loras(
            search_filename, search_category,
            search_trigger_word, min_rating
        )
        
        # Convert paths to filenames
        filtered_lora_names = [os.path.basename(path) for path in filtered_lora_paths]
        
        # Create filtered LoRA list
        filtered_loras_list = self._create_filtered_lora_list(
            search_filename, search_category,
            search_trigger_word, min_rating, query_civitai, force_civitai_fetch
        )
        
        # Create filter info
        active_filters = []
        active_filters.append(f"Platform: Flux")
        if search_filename.strip():
            active_filters.append(f"Filename: '{search_filename}'")
        if search_category != "Any":
            active_filters.append(f"Category: {search_category}")
        if min_rating > 0:
            active_filters.append(f"Min Rating: {min_rating}")
        if search_trigger_word.strip():
            active_filters.append(f"Trigger: '{search_trigger_word}'")
        
        filter_info = f"FILTERS: {' | '.join(active_filters)} | Found {len(filtered_lora_paths)} of {len(self.lora_paths)} Flux LoRAs"
        
        # Collect LoRA configurations
        lora_configs = [
            (lora_1_enable, lora_1_name, lora_1_strength, lora_1_clip_strength),
            (lora_2_enable, lora_2_name, lora_2_strength, lora_2_clip_strength),
            (lora_3_enable, lora_3_name, lora_3_strength, lora_3_clip_strength),
            (lora_4_enable, lora_4_name, lora_4_strength, lora_4_clip_strength),
            (lora_5_enable, lora_5_name, lora_5_strength, lora_5_clip_strength),
            (lora_6_enable, lora_6_name, lora_6_strength, lora_6_clip_strength),
            (lora_7_enable, lora_7_name, lora_7_strength, lora_7_clip_strength),
            (lora_8_enable, lora_8_name, lora_8_strength, lora_8_clip_strength)
        ]
        
        # Validate selections
        warnings = []
        for i, (enabled, name, strength, clip_strength) in enumerate(lora_configs, 1):
            if enabled and name != "None":
                if name not in filtered_lora_names and active_filters:
                    warnings.append(f"LoRA {i} '{name}' doesn't match filters")
        
        if warnings:
            filter_info += f" | WARNINGS: {'; '.join(warnings)}"
        
        # Load LoRAs (with CLIP)
        import comfy.utils
        import comfy.sd
        
        current_model = model
        current_clip = clip
        loaded_loras = []
        all_triggers = []
        
        for i, (enabled, name, strength, clip_strength) in enumerate(lora_configs, 1):
            if not enabled or name == "None":
                continue
            
            lora_path = self._find_lora_path(name)
            if not lora_path:
                print(f"[Flux] Warning: LoRA '{name}' not found, skipping slot {i}")
                continue
            
            try:
                # Load LoRA with CLIP
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                current_model, current_clip = comfy.sd.load_lora_for_models(
                    current_model, current_clip, lora, strength, clip_strength
                )
                
                # Get info and update usage
                lora_info = self._get_lora_info(name, query_civitai, force_civitai_fetch)
                self._update_lora_usage(lora_info["hash"], name, strength, clip_strength)
                
                loaded_loras.append({
                    "slot": i,
                    "name": name,
                    "strength": strength,
                    "clip_strength": clip_strength,
                    "architecture": lora_info.get("architecture", "Flux"),
                    "category": lora_info.get("category", "unknown"),
                    "triggers": lora_info.get("triggers", [])
                })
                
                # Collect triggers
                triggers = lora_info.get("selected_triggers", [])
                if not triggers:
                    triggers = lora_info.get("triggers", [])
                all_triggers.extend(triggers)
                
                print(f"[Flux] Loaded LoRA {i}: {name} (strength: {strength}, clip: {clip_strength})")
                
            except Exception as e:
                print(f"[Flux] Error loading LoRA '{name}' in slot {i}: {str(e)}")
                continue
        
        # Create loaded info
        loaded_info_lines = []
        for lora in loaded_loras:
            loaded_info_lines.append(
                f"Slot {lora['slot']}: {lora['name']} "
                f"[{lora['architecture']}] ({lora['category']}) "
                f"- Strength: {lora['strength']:.2f}, Clip: {lora['clip_strength']:.2f}"
            )
        
        loaded_loras_info = "\n".join(loaded_info_lines) if loaded_info_lines else "No LoRAs loaded"
        
        # Create trigger words string
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
        
        return (current_model, current_clip, prompt, prompt_with_triggers, loaded_loras_info, all_trigger_words, filter_info, filtered_loras_list)


# Node registration
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader Flux": MultiLoRALoaderFlux,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Multi-LoRA Loader Flux": "Multi-LoRA Loader (Flux)",
}
