"""
ComfyUI Node: Metadata Consolidator Node V2
Description: Consolidates metadata from workflow and existing sources using MetadataService
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

Metadata Consolidator Node V2 - Updated March 6, 2025

This node consolidates metadata from different sources including workflow data embedded in PNG files
and existing XMP sidecar files, merges them intelligently using the new MetadataService,
and ensures proper resource identifier consistency.
"""

import os
from ..eric_metadata.utils.workflow_parser import WorkflowParser

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService

class MetadataConsolidatorNode_V2:
    """Consolidates metadata from workflow and existing sources using MetadataService"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "input_filepath": ("STRING", {"default": ""}),
                "extract_workflow": ("BOOLEAN", {"default": True}),
                "overwrite_existing": ("BOOLEAN", {"default": False})
            },
            "optional": {
                # Metadata targets
                "write_to_xmp": ("BOOLEAN", {"default": True}),
                "embed_metadata": ("BOOLEAN", {"default": True}),
                "write_text_file": ("BOOLEAN", {"default": True}),
                "write_to_database": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": True})
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "summary")
    FUNCTION = "consolidate_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def __init__(self):
        """Initialize with metadata service and workflow parser"""
        self.metadata_service = MetadataService(debug=True)
        self.workflow_parser = WorkflowParser()
        
    def consolidate_metadata(self, image, input_filepath, extract_workflow=True, overwrite_existing=False,
                           write_to_xmp=True, embed_metadata=True, write_text_file=True, 
                           write_to_database=False, debug_logging=True):
        """
        Consolidate metadata from different sources and write using MetadataService
        
        Args:
            image: ComfyUI image tensor
            input_filepath: Path to the image file
            extract_workflow: Whether to extract workflow metadata from PNG
            overwrite_existing: Whether to overwrite existing values in metadata
            write_to_xmp: Whether to write to XMP sidecar
            embed_metadata: Whether to embed metadata in image
            write_text_file: Whether to write text file
            write_to_database: Whether to write to database
            debug_logging: Whether to enable debug logging
            
        Returns:
            Tuple of (image, summary)
        """
        try:
            # Enable debug logging if requested
            if debug_logging:
                self.metadata_service.debug = True
                print("[MetadataConsolidator] Starting metadata consolidation")
            
            if not input_filepath:
                return (image, "No filepath provided")
                
            # First verify file exists and is accessible
            if not os.path.exists(input_filepath):
                return (image, f"File does not exist: {input_filepath}")
            
            # Set resource identifier based on the filename
            filename = os.path.basename(input_filepath)
            resource_uri = f"file:///{filename}"
            self.metadata_service.set_resource_identifier(resource_uri)
                
            # Read existing metadata - try embedded first with fallback to XMP
            existing_metadata = self.metadata_service.read_metadata(input_filepath, fallback=True)
            consolidated_metadata = existing_metadata.copy() if existing_metadata else {}
            
            if debug_logging:
                print(f"[MetadataConsolidator] Starting consolidation with existing metadata keys: {list(consolidated_metadata.keys())}")
            
            # Extract workflow if requested
            if extract_workflow and input_filepath.lower().endswith('.png'):
                if debug_logging:
                    print(f"[MetadataConsolidator] Extracting workflow from: {input_filepath}")
                
                # Extract the workflow metadata
                workflow_metadata = self.workflow_parser.extract_and_convert_to_ai_metadata(input_filepath)
                
                if workflow_metadata:
                    if debug_logging:
                        print(f"[MetadataConsolidator] Extracted workflow metadata keys: {list(workflow_metadata.keys())}")
                    
                    # Handle workflow metadata integration
                    if overwrite_existing:
                        # Simple update - overwrite any existing values
                        self._update_metadata_with_overwrite(consolidated_metadata, workflow_metadata)
                    else:
                        # Smart merge - keep existing values, add missing ones
                        self._update_metadata_without_overwrite(consolidated_metadata, workflow_metadata)
            
            # Write the consolidated metadata
            if debug_logging:
                print(f"[MetadataConsolidator] Final consolidated metadata keys: {list(consolidated_metadata.keys())}")
            
            if consolidated_metadata:
                # Set targets based on user preferences
                targets = []
                if write_to_xmp: targets.append('xmp')
                if embed_metadata: targets.append('embedded')
                if write_text_file: targets.append('txt')
                if write_to_database: targets.append('db')
                
                # Write metadata to all selected targets
                if targets:
                    write_results = self.metadata_service.write_metadata(
                        input_filepath, consolidated_metadata, targets=targets
                    )
                    
                    # Log results
                    if debug_logging:
                        success_targets = [t for t, success in write_results.items() if success]
                        fail_targets = [t for t, success in write_results.items() if not success]
                        
                        if success_targets:
                            print(f"[MetadataConsolidator] Successfully wrote metadata to: {', '.join(success_targets)}")
                        if fail_targets:
                            print(f"[MetadataConsolidator] Failed to write metadata to: {', '.join(fail_targets)}")
                
            # Create summary text for the node output
            gen_data = consolidated_metadata.get('ai_info', {}).get('generation', {})
            model = gen_data.get('model', 'Unknown')
            prompt_preview = gen_data.get('prompt', '')
            if prompt_preview and len(prompt_preview) > 50:
                prompt_preview = prompt_preview[:50] + '...'
            
            # Create comprehensive summary
            consolidated_keys = list(consolidated_metadata.keys())
            successful_targets = [t for t, success in write_results.items() if success] if 'write_results' in locals() else []
            
            summary_text = (
                f"Metadata Consolidation Summary:\n"
                f"Model: {model}\n"
                f"Prompt: {prompt_preview}\n\n"
                f"Consolidated sections: {', '.join(consolidated_keys)}\n"
                f"Successfully written to: {', '.join(successful_targets)}"
            )
            
            return (image, summary_text)
                    
        except Exception as e:
            import traceback
            error_msg = f"Metadata consolidation failed: {str(e)}"
            print(f"[MetadataConsolidator] ERROR: {error_msg}")
            traceback.print_exc()
            return (image, error_msg)
        finally:
            # Ensure cleanup always happens
            self.cleanup()
            
    def _update_metadata_with_overwrite(self, consolidated_metadata: dict, workflow_metadata: dict) -> None:
        """
        Update metadata with workflow data, overwriting existing values
        
        Args:
            consolidated_metadata: Metadata to update (modified in place)
            workflow_metadata: Workflow metadata to incorporate
        """
        # Handle AI info section
        if 'ai_info' in workflow_metadata:
            if 'ai_info' not in consolidated_metadata:
                consolidated_metadata['ai_info'] = {}
                
            # Update the generation info
            if 'generation' in workflow_metadata['ai_info']:
                consolidated_metadata['ai_info']['generation'] = workflow_metadata['ai_info']['generation']
                
            # Update any other AI info sections
            for key, value in workflow_metadata['ai_info'].items():
                if key != 'generation':
                    consolidated_metadata['ai_info'][key] = value
        
        # Handle regions section
        if 'regions' in workflow_metadata:
            consolidated_metadata['regions'] = workflow_metadata['regions']
    
    def _update_metadata_without_overwrite(self, consolidated_metadata: dict, workflow_metadata: dict) -> None:
        """
        Update metadata with workflow data, preserving existing values
        
        Args:
            consolidated_metadata: Metadata to update (modified in place)
            workflow_metadata: Workflow metadata to incorporate
        """
        # Handle AI info section
        if 'ai_info' in workflow_metadata:
            if 'ai_info' not in consolidated_metadata:
                consolidated_metadata['ai_info'] = {}
                
            # Smart merge of generation data
            if 'generation' in workflow_metadata['ai_info']:
                if 'generation' not in consolidated_metadata['ai_info']:
                    consolidated_metadata['ai_info']['generation'] = {}
                    
                # Add missing fields, don't overwrite existing ones
                for key, value in workflow_metadata['ai_info']['generation'].items():
                    if key not in consolidated_metadata['ai_info']['generation'] or not consolidated_metadata['ai_info']['generation'][key]:
                        consolidated_metadata['ai_info']['generation'][key] = value
                        
            # Handle other AI info sections
            for key, value in workflow_metadata['ai_info'].items():
                if key != 'generation' and key not in consolidated_metadata['ai_info']:
                    consolidated_metadata['ai_info'][key] = value
        
        # Handle regions section
        if 'regions' in workflow_metadata and 'regions' not in consolidated_metadata:
            consolidated_metadata['regions'] = workflow_metadata['regions']
        elif 'regions' in workflow_metadata:
            # Use the metadata service's merge logic
            merged = self.metadata_service._merge_metadata(
                consolidated_metadata, {'regions': workflow_metadata['regions']}
            )
            if 'regions' in merged:
                consolidated_metadata['regions'] = merged['regions']

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "MetadataConsolidatorNode_V2": MetadataConsolidatorNode_V2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MetadataConsolidatorNode_V2": "Metadata Consolidator V2"
}