"""
TEMPLATE: Multi-LoRA Loader for [PLATFORM_NAME]
Platform-specific loader for [PLATFORM_NAME] LoRAs

INSTRUCTIONS:
1. Copy this file and rename to: Multi_LoRA_Loader_[YourPlatform].py
2. Search and replace the following:
   - [PLATFORM_NAME] → Your platform name (e.g., "Flux", "SDXL")
   - [PLATFORM_SHORT] → Short name (e.g., "flux", "sdxl")
   - [DIRECTORY_FILTER] → Directory path (e.g., "Flux" or os.path.join("Flux", "subfolder"))
   - [REQUIRES_CLIP] → True or False
   - [DEFAULT_ARCH] → Default architecture name
3. Adjust category list if needed
4. Delete these instructions
5. Save and restart ComfyUI
"""

import os
from typing import Tuple, Any
from .Multi_LoRA_Loader_Base import MultiLoRALoaderBase


class MultiLoRALoader[PLATFORM_NAME](MultiLoRALoaderBase):
    """
    Multi-LoRA loader specifically for [PLATFORM_NAME] LoRAs.
    Only shows LoRAs from the [DIRECTORY_FILTER] directory.
    
    Configure REQUIRES_CLIP based on your platform:
    - True: For platforms that use CLIP (SD1.5, SDXL, Flux, etc.)
    - False: For platforms without CLIP (Wan Video, pure diffusion models, etc.)
    """
    
    # Platform-specific configuration - CHANGE THESE VALUES
    PLATFORM_NAME = "[PLATFORM_SHORT]"
    PLATFORM_DIRECTORY_FILTER = "[DIRECTORY_FILTER]"  # e.g., "Flux" or os.path.join("Flux", "loras")
    REQUIRES_CLIP = [REQUIRES_CLIP]  # True or False
    DEFAULT_ARCHITECTURE = "[DEFAULT_ARCH]"
    MAX_LORA_SLOTS = 8
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get platform-filtered LoRAs
        try:
            lora_options = ["None"] + cls._get_platform_filtered_loras()
            if len(lora_options) == 1:  # Only "None" means no LoRAs found
                print(f"[{cls.PLATFORM_NAME}] Warning: No LoRAs found in {cls.PLATFORM_DIRECTORY_FILTER} directory")
        except Exception as e:
            print(f"[{cls.PLATFORM_NAME}] Error getting LoRA options: {e}")
            lora_options = ["None"]
        
        # Base input structure (CLIP handling added below if needed)
        base_inputs = {
            "required": {
                "model": ("MODEL",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                
                # Simplified filters (directory filter already applied by platform)
                "search_filename": ("STRING", {"default": "", "multiline": False,
                    "tooltip": "Search in LoRA filenames. Use commas to separate multiple terms."}),
                "search_category": (["Any", "unknown", "lightning", "tools", "artstyle", "photostyle", 
                    "character", "body", "effect", "mood", "treatment", "style", "concept", 
                    "pose", "clothing", "background"], {"default": "Any",
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
            }
        }
        
        # Add CLIP input if required
        if cls.REQUIRES_CLIP:
            base_inputs["required"]["clip"] = ("CLIP",)
        
        # Add 8 LoRA slots
        for i in range(1, 9):
            base_inputs["required"][f"lora_{i}_enable"] = ("BOOLEAN", {"default": False})
            base_inputs["required"][f"lora_{i}_name"] = (lora_options, {"default": "None"})
            base_inputs["required"][f"lora_{i}_strength"] = ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01})
            
            # Add clip_strength only if CLIP is required
            if cls.REQUIRES_CLIP:
                base_inputs["required"][f"lora_{i}_clip_strength"] = ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01})
        
        return base_inputs
    
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
    
    # Return types depend on whether CLIP is used
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING") if REQUIRES_CLIP else \
                   ("MODEL", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "prompt", "prompt_with_triggers", "loaded_loras_info", "all_trigger_words", "filter_info", "filtered_loras_list") if REQUIRES_CLIP else \
                   ("model", "prompt", "prompt_with_triggers", "loaded_loras_info", "all_trigger_words", "filter_info", "filtered_loras_list")
    FUNCTION = "load_multi_loras"
    CATEGORY = "loaders/multi-lora/[PLATFORM_SHORT]"  # Change category as needed
    
    def load_multi_loras(self, model, prompt: str,
                        search_filename: str, search_category: str,
                        search_trigger_word: str, min_rating: int,
                        refresh_lists: bool, query_civitai: bool, force_civitai_fetch: bool,
                        trigger_position: str, trigger_separator: str,
                        clip=None,  # Optional, used only if REQUIRES_CLIP=True
                        # LoRA parameters - dynamically handled
                        **lora_kwargs
                        ) -> Tuple:
        """Load multiple LoRAs for [PLATFORM_NAME]"""
        
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
        active_filters.append(f"Platform: [PLATFORM_NAME]")
        if search_filename.strip():
            active_filters.append(f"Filename: '{search_filename}'")
        if search_category != "Any":
            active_filters.append(f"Category: {search_category}")
        if min_rating > 0:
            active_filters.append(f"Min Rating: {min_rating}")
        if search_trigger_word.strip():
            active_filters.append(f"Trigger: '{search_trigger_word}'")
        
        filter_info = f"FILTERS: {' | '.join(active_filters)} | Found {len(filtered_lora_paths)} of {len(self.lora_paths)} [PLATFORM_NAME] LoRAs"
        
        # Collect LoRA configurations
        lora_configs = []
        for i in range(1, 9):
            enabled = lora_kwargs.get(f'lora_{i}_enable', False)
            name = lora_kwargs.get(f'lora_{i}_name', 'None')
            strength = lora_kwargs.get(f'lora_{i}_strength', 1.0)
            clip_strength = lora_kwargs.get(f'lora_{i}_clip_strength', 1.0) if self.REQUIRES_CLIP else 0.0
            lora_configs.append((enabled, name, strength, clip_strength))
        
        # Validate selections
        warnings = []
        for i, (enabled, name, strength, clip_strength) in enumerate(lora_configs, 1):
            if enabled and name != "None":
                if name not in filtered_lora_names and active_filters:
                    warnings.append(f"LoRA {i} '{name}' doesn't match filters")
        
        if warnings:
            filter_info += f" | WARNINGS: {'; '.join(warnings)}"
        
        # Load LoRAs
        import comfy.utils
        import comfy.sd
        
        current_model = model
        current_clip = clip if self.REQUIRES_CLIP else None
        loaded_loras = []
        all_triggers = []
        
        for i, (enabled, name, strength, clip_strength) in enumerate(lora_configs, 1):
            if not enabled or name == "None":
                continue
            
            lora_path = self._find_lora_path(name)
            if not lora_path:
                print(f"[{self.PLATFORM_NAME}] Warning: LoRA '{name}' not found, skipping slot {i}")
                continue
            
            try:
                # Load LoRA
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                
                if self.REQUIRES_CLIP:
                    # Load with CLIP
                    current_model, current_clip = comfy.sd.load_lora_for_models(
                        current_model, current_clip, lora, strength, clip_strength
                    )
                else:
                    # Load model only
                    current_model, _ = comfy.sd.load_lora_for_models(
                        current_model, None, lora, strength, 0.0
                    )
                
                # Get info and update usage
                lora_info = self._get_lora_info(name, query_civitai, force_civitai_fetch)
                self._update_lora_usage(lora_info["hash"], name, strength, clip_strength)
                
                loaded_loras.append({
                    "slot": i,
                    "name": name,
                    "strength": strength,
                    "clip_strength": clip_strength if self.REQUIRES_CLIP else None,
                    "architecture": lora_info.get("architecture", self.DEFAULT_ARCHITECTURE),
                    "category": lora_info.get("category", "unknown"),
                    "triggers": lora_info.get("triggers", [])
                })
                
                # Collect triggers
                triggers = lora_info.get("selected_triggers", [])
                if not triggers:
                    triggers = lora_info.get("triggers", [])
                all_triggers.extend(triggers)
                
                if self.REQUIRES_CLIP:
                    print(f"[{self.PLATFORM_NAME}] Loaded LoRA {i}: {name} (strength: {strength}, clip: {clip_strength})")
                else:
                    print(f"[{self.PLATFORM_NAME}] Loaded LoRA {i}: {name} (strength: {strength})")
                
            except Exception as e:
                print(f"[{self.PLATFORM_NAME}] Error loading LoRA '{name}' in slot {i}: {str(e)}")
                continue
        
        # Create loaded info
        loaded_info_lines = []
        for lora in loaded_loras:
            if self.REQUIRES_CLIP:
                loaded_info_lines.append(
                    f"Slot {lora['slot']}: {lora['name']} "
                    f"[{lora['architecture']}] ({lora['category']}) "
                    f"- Strength: {lora['strength']:.2f}, Clip: {lora['clip_strength']:.2f}"
                )
            else:
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
        
        # Return appropriate outputs based on CLIP requirement
        if self.REQUIRES_CLIP:
            return (current_model, current_clip, prompt, prompt_with_triggers, loaded_loras_info, all_trigger_words, filter_info, filtered_loras_list)
        else:
            return (current_model, prompt, prompt_with_triggers, loaded_loras_info, all_trigger_words, filter_info, filtered_loras_list)


# Node registration - CHANGE THESE
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader [PLATFORM_NAME]": MultiLoRALoader[PLATFORM_NAME],
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Multi-LoRA Loader [PLATFORM_NAME]": "Multi-LoRA Loader ([PLATFORM_NAME])",
}
