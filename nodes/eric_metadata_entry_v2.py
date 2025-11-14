"""
ComfyUI Node: Eric's Metadata Entry V2
Description: Add metadata to images including basic fields and AI generation information.
Uses the new MetadataService for improved handling.
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 1.0.0
Date: [March 2025]
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

Dependencies:
This code depends on several third-party libraries, each with its own license:
- torch: BSD 3-Clause

Eric's Metadata Entry Node V2 - Updated March 2025

Add metadata to images including basic fields and AI generation information.
Uses the new MetadataService for improved handling.

Features:
- Standard Adobe/XMP metadata fields (title, description, keywords, etc.)
- AI generation metadata fields
- Database support
- Multiple storage options (embedded, XMP, text, database)
"""

import os
import torch
from typing import Dict, List, Optional, Union
import datetime

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService

class EricMetadataEntryNodeV2:
    """Node for adding metadata to images from ComfyUI"""
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "input_filepath": ("STRING", {"default": ""}),
            },
            "optional": {
                # Basic metadata fields
                "title": ("STRING", {"default": ""}),
                "description": ("STRING", {"default": ""}),
                "keywords": ("STRING", {"default": ""}),
                "rating": (["", "1", "2", "3", "4", "5"], {"default": ""}),
                "author": ("STRING", {"default": ""}),
                "copyright": ("STRING", {"default": ""}),
                "copyright_url": ("STRING", {"default": ""}),
                "category": ("STRING", {"default": ""}),
                
                # AI generation fields
                "prompt": ("STRING", {"default": ""}),
                "negative_prompt": ("STRING", {"default": ""}),
                "model": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": 0}),
                "steps": ("INT", {"default": 0}),
                "cfg_scale": ("FLOAT", {"default": 0.0}),
                "sampler": ("STRING", {"default": ""}),
                "scheduler": ("STRING", {"default": ""}),
                
                # Storage options
                "write_to_xmp": ("BOOLEAN", {"default": True}),
                "embed_metadata": ("BOOLEAN", {"default": True}),
                "write_text_file": ("BOOLEAN", {"default": False}),
                "write_to_database": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": True})
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "BOOLEAN")
    RETURN_NAMES = ("image", "status", "success")
    FUNCTION = "add_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def add_metadata(self, image, input_filepath, 
                   # Basic metadata optional parameters
                   title="", description="", keywords="",
                   rating="", author="", copyright="",
                   copyright_url="", category="",
                   # AI generation optional parameters
                   prompt="", negative_prompt="", model="",
                   seed=0, steps=0, cfg_scale=0.0,
                   sampler="", scheduler="",
                   # Storage options
                   write_to_xmp=True, embed_metadata=True,
                   write_text_file=False, write_to_database=False,
                   debug_logging=True):
        """Add metadata to image file"""
        try:
            # Enable debug logging if requested
            self.metadata_service.debug = debug_logging
            
            if debug_logging:
                print(f"[MetadataEntry] Processing metadata for {input_filepath}")
                
            # Skip metadata operations if no filepath provided
            if not input_filepath:
                return image, "No filepath provided, skipping metadata operations", False
                
            # Process keywords into proper format
            processed_keywords = []
            if keywords:
                for keyword in keywords.split(','):
                    keyword = keyword.strip()
                    if keyword:  # Only add non-empty keywords
                        processed_keywords.append(keyword)
                if debug_logging:
                    print(f"[MetadataEntry] Processed keywords: {processed_keywords}")
                
            # Structure metadata
            metadata = {
                'basic': {},
                'ai_info': {}
            }
            
            # Add basic metadata fields if provided
            if title:
                metadata['basic']['title'] = title
            if description:
                metadata['basic']['description'] = description
            if processed_keywords:
                metadata['basic']['keywords'] = processed_keywords
            if rating:
                metadata['basic']['rating'] = int(rating)
            if author:
                metadata['basic']['creator'] = author
            if copyright:
                metadata['basic']['rights'] = copyright
            if category:
                metadata['basic']['category'] = category
            if copyright_url:
                if 'rights_info' not in metadata['basic']:
                    metadata['basic']['rights_info'] = {}
                metadata['basic']['rights_info']['web_statement'] = copyright_url
                metadata['basic']['rights_info']['marked'] = True
                
            # Add AI generation information if provided
            has_ai_info = False
            
            if any([prompt, negative_prompt, model, seed > 0, steps > 0, 
                    cfg_scale > 0, sampler, scheduler]):
                generation_data = {}
                
                if prompt:
                    generation_data['prompt'] = prompt
                if negative_prompt:
                    generation_data['negative_prompt'] = negative_prompt
                if model:
                    generation_data['model'] = model
                if seed > 0:
                    generation_data['seed'] = seed
                if steps > 0:
                    generation_data['steps'] = steps
                if cfg_scale > 0:
                    generation_data['cfg_scale'] = cfg_scale
                if sampler:
                    generation_data['sampler'] = sampler
                if scheduler:
                    generation_data['scheduler'] = scheduler
                    
                # Add timestamp
                generation_data['timestamp'] = self.metadata_service.get_timestamp()
                
                # Add generation data to ai_info
                metadata['ai_info']['generation'] = generation_data
                has_ai_info = True
            
            # Skip if no metadata provided
            if not metadata['basic'] and not has_ai_info:
                return image, "No metadata provided", False
                
            # Set targets based on user preferences
            targets = []
            if write_to_xmp: targets.append('xmp')
            if embed_metadata: targets.append('embedded')
            if write_text_file: targets.append('txt')
            if write_to_database: targets.append('db')
            
            # Skip metadata writing if no targets selected
            if not targets:
                return image, "No metadata targets selected", False
                
            # Set resource identifier (important for proper XMP handling)
            filename = os.path.basename(input_filepath)
            resource_uri = f"file:///{filename}"
            self.metadata_service.set_resource_identifier(resource_uri)
            
            # Write metadata to all requested targets
            write_results = self.metadata_service.write_metadata(
                input_filepath, 
                metadata, 
                targets=targets
            )
            
            # Prepare status message
            success_targets = [t for t, success in write_results.items() if success]
            fail_targets = [t for t, success in write_results.items() if not success]
            
            if all(write_results.values()):
                message = f"Successfully wrote metadata to all targets: {', '.join(targets)}"
                success = True
            elif any(write_results.values()):
                message = f"Partially wrote metadata. Success: {', '.join(success_targets)}. Failed: {', '.join(fail_targets)}"
                success = True  # Still consider successful if at least one target worked
            else:
                message = "Failed to write metadata to any target"
                success = False
                
            return image, message, success
            
        except Exception as e:
            print(f"[MetadataEntry] ERROR: Metadata entry failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return image, f"Error: {str(e)}", False
        finally:
            # Always ensure cleanup happens
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

NODE_CLASS_MAPPINGS = {
    "Eric_Metadata_Entry_V2": EricMetadataEntryNodeV2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Metadata_Entry_V2": "Eric's Metadata Entry V2"
}