"""
Workflow Extractor Node
Node to extract workflow metadata from existing images

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

class WorkflowExtractorNode:
    """Node to extract workflow metadata from existing images"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "debug_logging": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("metadata_json",)
    FUNCTION = "extract_workflow"
    CATEGORY = "Eric's Nodes/Metadata"
    
    def extract_workflow(self, image_path, debug_logging=False):
        from custom_nodes.AAA_Metadata_System.eric_metadata.workflow_metadata import WorkflowMetadataProcessor
        
        # Create processor
        processor = WorkflowMetadataProcessor(debug=debug_logging)
        
        # Process embedded data
        metadata = processor.process_embedded_data(image_path)
        
        # Convert to JSON string
        metadata_json = json.dumps(metadata, indent=2)
        
        return (metadata_json,)