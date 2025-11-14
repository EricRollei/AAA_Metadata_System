"""
Multi-LoRA Loader for Wan Video (t2v)
Platform-specific loader for Wan Video Text-to-Video LoRAs
Filters to show only LoRAs in L:\stable-diffusion-webui\models\Lora\Wan\t2v

This is a model-only loader (no CLIP) optimized for Wan Video workflows.
"""

import os
from typing import Tuple, Any
from .Multi_LoRA_Loader_Base import MultiLoRALoaderBase


class MultiLoRALoaderWanT2V(MultiLoRALoaderBase):
    """
    Multi-LoRA loader specifically for Wan Video (Text-to-Video) LoRAs.
    Only shows LoRAs from the Wan\t2v directory.
    Model-only (no CLIP).
    """
    
    # Platform-specific configuration
    PLATFORM_NAME = "Wan-t2v"
    PLATFORM_DIRECTORY_FILTER = os.path.join("Wan", "t2v")  # Will scan Lora\Wan\t2v
    REQUIRES_CLIP = False  # Wan Video doesn't use CLIP
    DEFAULT_ARCHITECTURE = "Wan"
    MAX_LORA_SLOTS = 8
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get platform-filtered LoRAs (only from Wan\t2v directory)
        try:
            lora_options = ["None"] + cls._get_platform_filtered_loras()
            if len(lora_options) == 1:  # Only "None" means no LoRAs found
                print(f"[Wan-t2v] Warning: No LoRAs found in Wan\\t2v directory")
        except Exception as e:
            print(f"[Wan-t2v] Error getting LoRA options: {e}")
            lora_options = ["None"]
        
        return {
            "required": {
                "model": ("MODEL",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                
                # Simplified filters (directory filter is already applied by platform)
                "search_filename": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in LoRA filenames. Use commas to separate multiple terms."}),
                "search_category": (["Any", "unknown", "lightning", "tools", "artstyle", "photostyle", 
                    "character", "body", "effect", "mood", "treatment"], {"default": "Any",
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
                
                # LoRA slots (MODEL ONLY - no clip_strength)
                "lora_1_enable": ("BOOLEAN", {"default": False}),
                "lora_1_name": (lora_options, {"default": "None"}),
                "lora_1_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_2_enable": ("BOOLEAN", {"default": False}),
                "lora_2_name": (lora_options, {"default": "None"}),
                "lora_2_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_3_enable": ("BOOLEAN", {"default": False}),
                "lora_3_name": (lora_options, {"default": "None"}),
                "lora_3_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_4_enable": ("BOOLEAN", {"default": False}),
                "lora_4_name": (lora_options, {"default": "None"}),
                "lora_4_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_5_enable": ("BOOLEAN", {"default": False}),
                "lora_5_name": (lora_options, {"default": "None"}),
                "lora_5_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_6_enable": ("BOOLEAN", {"default": False}),
                "lora_6_name": (lora_options, {"default": "None"}),
                "lora_6_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_7_enable": ("BOOLEAN", {"default": False}),
                "lora_7_name": (lora_options, {"default": "None"}),
                "lora_7_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                "lora_8_enable": ("BOOLEAN", {"default": False}),
                "lora_8_name": (lora_options, {"default": "None"}),
                "lora_8_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
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
    
    RETURN_TYPES = ("MODEL", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model", "prompt", "prompt_with_triggers", "loaded_loras_info", "all_trigger_words", "filter_info", "filtered_loras_list")
    FUNCTION = "load_multi_loras"
    CATEGORY = "loaders/multi-lora/wan"
    
    def load_multi_loras(self, model, prompt: str,
                        search_filename: str, search_category: str,
                        search_trigger_word: str, min_rating: int,
                        refresh_lists: bool, query_civitai: bool, force_civitai_fetch: bool,
                        trigger_position: str, trigger_separator: str,
                        # LoRA parameters (MODEL ONLY)
                        lora_1_enable: bool, lora_1_name: str, lora_1_strength: float,
                        lora_2_enable: bool, lora_2_name: str, lora_2_strength: float,
                        lora_3_enable: bool, lora_3_name: str, lora_3_strength: float,
                        lora_4_enable: bool, lora_4_name: str, lora_4_strength: float,
                        lora_5_enable: bool, lora_5_name: str, lora_5_strength: float,
                        lora_6_enable: bool, lora_6_name: str, lora_6_strength: float,
                        lora_7_enable: bool, lora_7_name: str, lora_7_strength: float,
                        lora_8_enable: bool, lora_8_name: str, lora_8_strength: float
                        ) -> Tuple[Any, str, str, str, str, str, str]:
        """Load multiple LoRAs for Wan t2v (model only)"""
        
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
        active_filters.append(f"Platform: Wan t2v")
        if search_filename.strip():
            active_filters.append(f"Filename: '{search_filename}'")
        if search_category != "Any":
            active_filters.append(f"Category: {search_category}")
        if min_rating > 0:
            active_filters.append(f"Min Rating: {min_rating}")
        if search_trigger_word.strip():
            active_filters.append(f"Trigger: '{search_trigger_word}'")
        
        filter_info = f"FILTERS: {' | '.join(active_filters)} | Found {len(filtered_lora_paths)} of {len(self.lora_paths)} Wan t2v LoRAs"
        
        # Collect LoRA configurations
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
        
        # Validate selections
        warnings = []
        for i, (enabled, name, strength) in enumerate(lora_configs, 1):
            if enabled and name != "None":
                if name not in filtered_lora_names and active_filters:
                    warnings.append(f"LoRA {i} '{name}' doesn't match filters")
        
        if warnings:
            filter_info += f" | WARNINGS: {'; '.join(warnings)}"
        
        # Load LoRAs (model only)
        import comfy.utils
        import comfy.sd
        
        current_model = model
        loaded_loras = []
        all_triggers = []
        
        for i, (enabled, name, strength) in enumerate(lora_configs, 1):
            if not enabled or name == "None":
                continue
            
            lora_path = self._find_lora_path(name)
            if not lora_path:
                print(f"[Wan-t2v] Warning: LoRA '{name}' not found, skipping slot {i}")
                continue
            
            try:
                # Load LoRA for model only
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                current_model, _ = comfy.sd.load_lora_for_models(
                    current_model, None, lora, strength, 0.0
                )
                
                # Get info and update usage
                lora_info = self._get_lora_info(name, query_civitai, force_civitai_fetch)
                self._update_lora_usage(lora_info["hash"], name, strength, 0.0)
                
                loaded_loras.append({
                    "slot": i,
                    "name": name,
                    "strength": strength,
                    "architecture": lora_info.get("architecture", "Wan"),
                    "category": lora_info.get("category", "unknown"),
                    "triggers": lora_info.get("triggers", [])
                })
                
                # Collect triggers
                triggers = lora_info.get("selected_triggers", [])
                if not triggers:
                    triggers = lora_info.get("triggers", [])
                all_triggers.extend(triggers)
                
                print(f"[Wan-t2v] Loaded LoRA {i}: {name} (strength: {strength})")
                
            except Exception as e:
                print(f"[Wan-t2v] Error loading LoRA '{name}' in slot {i}: {str(e)}")
                continue
        
        # Create loaded info
        loaded_info_lines = []
        for lora in loaded_loras:
            loaded_info_lines.append(
                f"Slot {lora['slot']}: {lora['name']} "
                f"[{lora['architecture']}] ({lora['category']}) "
                f"- Strength: {lora['strength']:.2f}"
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
        
        return (current_model, prompt, prompt_with_triggers, loaded_loras_info, all_trigger_words, filter_info, filtered_loras_list)


# Node registration
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader Wan-t2v": MultiLoRALoaderWanT2V,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Multi-LoRA Loader Wan-t2v": "Multi-LoRA Loader (Wan t2v)",
}
