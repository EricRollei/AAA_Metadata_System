"""
Multi-LoRA Loader for Z-Image
Platform-specific loader for Z-Image LoRAs.
Simple 4-slot loader - set LoRA to "None" to skip that slot.

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
from typing import Tuple
from .Multi_LoRA_Loader_Base import MultiLoRALoaderBase


class MultiLoRALoaderZImage(MultiLoRALoaderBase):
    """
    Multi-LoRA loader specifically for Z-Image LoRAs.
    Only shows LoRAs from the Z_Image directory.
    4 LoRA slots - set to "None" to skip.
    """
    
    # Platform-specific configuration
    PLATFORM_NAME = "zimage"
    PLATFORM_DIRECTORY_FILTER = "Z_Image"
    REQUIRES_CLIP = True
    DEFAULT_ARCHITECTURE = "Z-Image"
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get platform-filtered LoRAs
        try:
            lora_options = ["None"] + cls._get_platform_filtered_loras()
        except Exception as e:
            lora_options = ["None"]
        
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                
                # LoRA 1
                "lora_1": (lora_options, {"default": "None", "tooltip": "First LoRA to load"}),
                "strength_1": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength_1": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA 2
                "lora_2": (lora_options, {"default": "None", "tooltip": "Second LoRA to load"}),
                "strength_2": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength_2": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA 3
                "lora_3": (lora_options, {"default": "None", "tooltip": "Third LoRA to load"}),
                "strength_3": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength_3": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # LoRA 4
                "lora_4": (lora_options, {"default": "None", "tooltip": "Fourth LoRA to load"}),
                "strength_4": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                "clip_strength_4": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                
                # Trigger word settings
                "trigger_position": (["front", "back"], {"default": "front"}),
                "trigger_separator": ("STRING", {"default": ", "}),
                
                # Civitai integration
                "query_civitai": ("BOOLEAN", {"default": False,
                    "tooltip": "Automatically query Civitai for trigger words"}),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("model", "clip", "prompt", "prompt_with_triggers", "loaded_loras_info")
    FUNCTION = "load_loras"
    CATEGORY = "loaders/multi-lora/zimage"
    
    def load_loras(self, model, clip, prompt: str,
                   lora_1: str, strength_1: float, clip_strength_1: float,
                   lora_2: str, strength_2: float, clip_strength_2: float,
                   lora_3: str, strength_3: float, clip_strength_3: float,
                   lora_4: str, strength_4: float, clip_strength_4: float,
                   trigger_position: str, trigger_separator: str,
                   query_civitai: bool) -> Tuple:
        """Load up to 4 LoRAs for Z-Image"""
        
        import comfy.utils
        import comfy.sd
        
        current_model = model
        current_clip = clip
        loaded_loras = []
        all_triggers = []
        
        # Process each LoRA slot
        lora_configs = [
            (1, lora_1, strength_1, clip_strength_1),
            (2, lora_2, strength_2, clip_strength_2),
            (3, lora_3, strength_3, clip_strength_3),
            (4, lora_4, strength_4, clip_strength_4),
        ]
        
        for slot, name, strength, clip_str in lora_configs:
            if name == "None" or not name:
                continue
            
            lora_path = self._find_lora_path(name)
            if not lora_path:
                print(f"[{self.PLATFORM_NAME}] Warning: LoRA '{name}' not found, skipping slot {slot}")
                continue
            
            try:
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                current_model, current_clip = comfy.sd.load_lora_for_models(
                    current_model, current_clip, lora, strength, clip_str
                )
                
                # Get info
                lora_info = self._get_lora_info(name, query_civitai, False)
                
                loaded_loras.append(f"Slot {slot}: {name} (str: {strength:.2f}, clip: {clip_str:.2f})")
                
                # Collect triggers
                triggers = lora_info.get("selected_triggers", []) or lora_info.get("triggers", [])
                all_triggers.extend(triggers)
                
                print(f"[{self.PLATFORM_NAME}] Loaded LoRA {slot}: {name}")
                
            except Exception as e:
                print(f"[{self.PLATFORM_NAME}] Error loading LoRA '{name}': {str(e)}")
                continue
        
        # Build outputs
        loaded_loras_info = "\n".join(loaded_loras) if loaded_loras else "No LoRAs loaded"
        
        # Unique triggers
        unique_triggers = list(dict.fromkeys(all_triggers))
        all_trigger_words = trigger_separator.join(unique_triggers)
        
        # Prompt with triggers
        prompt_with_triggers = prompt
        if unique_triggers:
            if trigger_position == "front":
                prompt_with_triggers = all_trigger_words + trigger_separator + prompt
            else:
                prompt_with_triggers = prompt + trigger_separator + all_trigger_words
        
        return (current_model, current_clip, prompt, prompt_with_triggers, loaded_loras_info)


# Node registration
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader Z-Image": MultiLoRALoaderZImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Multi-LoRA Loader Z-Image": "Multi-LoRA Loader (Z-Image)",
}
