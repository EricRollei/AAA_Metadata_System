"""
Split Workflow Extractor Node V2 - Updated March 6, 2025

Extracts and merges workflow data from PNG files that may have split information
across multiple metadata fields, and stores it using the new MetadataService system.
"""

import os
import json
import torch
import numpy as np
from PIL import Image

# Import the metadata service from the package
from custom_nodes.AAA_Metadata_System import MetadataService

class SplitWorkflowExtractorNode_V2:
    """Extracts and merges split workflow data (prompt+workflow fields) from PNG files"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "input_filepath": ("STRING", {"default": ""}),
            },
            "optional": {
                # Metadata options
                "write_to_xmp": ("BOOLEAN", {"default": True}),
                "embed_metadata": ("BOOLEAN", {"default": True}),
                "write_text_file": ("BOOLEAN", {"default": False}),
                "write_to_database": ("BOOLEAN", {"default": False}),
                "overwrite_existing": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "JSON")
    RETURN_NAMES = ("image", "workflow_summary", "workflow_json")
    FUNCTION = "extract_workflow"
    CATEGORY = "Eric's Nodes/Metadata"

    def __init__(self):
        """Initialize metadata service"""
        self.metadata_service = MetadataService(debug=True)
        
    def extract_workflow(self, image, input_filepath, 
                         write_to_xmp=True, embed_metadata=True, 
                         write_text_file=False, write_to_database=False,
                         overwrite_existing=False, debug_logging=False):
        """Extract workflow data from PNG files"""
        try:
            # Enable debug logging if requested
            if debug_logging:
                self.metadata_service.debug = True
                print("[WorkflowExtractor] Starting workflow extraction")
            
            if not input_filepath:
                return (image, "No filepath provided", {})
                
            if not input_filepath.lower().endswith('.png'):
                return (image, "Not a PNG file - workflows only exist in PNG files", {})
                
            # Check if file exists
            if not os.path.exists(input_filepath):
                return (image, f"File does not exist: {input_filepath}", {})
                
            # Extract available metadata fields from PNG
            prompt_data = None
            workflow_data = None
            
            # Read metadata directly from PNG
            with Image.open(input_filepath) as img:
                if not hasattr(img, 'info') or not img.info:
                    return (image, "No metadata found in PNG", {})
                
                available_fields = list(img.info.keys())
                if debug_logging:
                    print(f"[WorkflowExtractor] Available fields: {', '.join(available_fields)}")
                
                # Extract both prompt and workflow fields if they exist
                if 'prompt' in img.info:
                    try:
                        prompt_data = json.loads(img.info['prompt'])
                        if debug_logging:
                            print("[WorkflowExtractor] Successfully loaded 'prompt' field as JSON")
                    except json.JSONDecodeError:
                        print("[WorkflowExtractor] 'prompt' field is not valid JSON")
                        
                if 'workflow' in img.info:
                    try:
                        workflow_data = json.loads(img.info['workflow'])
                        if debug_logging:
                            print("[WorkflowExtractor] Successfully loaded 'workflow' field as JSON")
                    except json.JSONDecodeError:
                        print("[WorkflowExtractor] 'workflow' field is not valid JSON")
                
                # Try parameters field for some tools
                if 'parameters' in img.info:
                    try:
                        parameters = img.info['parameters']
                        if debug_logging:
                            print("[WorkflowExtractor] Found 'parameters' field")
                    except:
                        parameters = None
            
            # Handle the case where we don't have both parts
            if not prompt_data and not workflow_data:
                return (image, "No valid JSON data found in 'prompt' or 'workflow' fields", {})
            
            # Merge data - reconstruct complete workflow
            merged_workflow = {}
            
            # Process prompt field (contains node data)
            if prompt_data and isinstance(prompt_data, dict):
                merged_workflow["nodes"] = []
                
                for node_id, node_data in prompt_data.items():
                    if isinstance(node_data, dict):
                        # Convert node ID from string to int if needed
                        try:
                            node_id_int = int(node_id)
                        except ValueError:
                            node_id_int = node_id
                            
                        # Create node structure
                        node = {
                            "id": node_id_int,
                            "type": node_data.get("class_type", ""),
                            "inputs": node_data.get("inputs", {}),
                            "_meta": node_data.get("_meta", {"title": node_data.get("class_type", "")})
                        }
                        
                        if "is_changed" in node_data:
                            node["is_changed"] = node_data["is_changed"]
                            
                        merged_workflow["nodes"].append(node)
            
            # Process workflow field (contains structure, links, etc)
            if workflow_data and isinstance(workflow_data, dict):
                # Add workflow structure info
                for key in ["last_node_id", "last_link_id", "links", "groups", "config", "extra", "version"]:
                    if key in workflow_data:
                        merged_workflow[key] = workflow_data[key]
                        
                # If workflow also has nodes, use those instead as they might be more complete
                if "nodes" in workflow_data:
                    merged_workflow["nodes"] = workflow_data["nodes"]
            
            # Extract generation data from the nodes
            ai_metadata = self._extract_generation_data(merged_workflow)
            
            # Add raw workflow data
            ai_metadata["ai_info"]["workflow"] = merged_workflow
            
            # Write metadata if filepath provided and targets selected
            write_result = {}
            if ai_metadata and input_filepath:
                # Set targets based on user preferences
                targets = []
                if write_to_xmp: targets.append('xmp')
                if embed_metadata: targets.append('embedded')
                if write_text_file: targets.append('txt')
                if write_to_database: targets.append('db')
                
                if targets:
                    # Check if we should overwrite existing metadata
                    if not overwrite_existing:
                        # Read existing metadata to check if we should proceed
                        existing = self.metadata_service.read_metadata(input_filepath, source='xmp', fallback=True)
                        if existing and 'ai_info' in existing and 'workflow' in existing['ai_info']:
                            if debug_logging:
                                print("[WorkflowExtractor] Existing workflow found, skipping write due to overwrite_existing=False")
                            write_result = {target: False for target in targets}
                        else:
                            # No existing workflow, proceed with write
                            # Set resource identifier (important for proper XMP handling)
                            filename = os.path.basename(input_filepath)
                            resource_uri = f"file:///{filename}"
                            self.metadata_service.set_resource_identifier(resource_uri)
                            
                            # Write metadata
                            write_result = self.metadata_service.write_metadata(input_filepath, ai_metadata, targets=targets)
                    else:
                        # Always overwrite
                        # Set resource identifier (important for proper XMP handling)
                        filename = os.path.basename(input_filepath)
                        resource_uri = f"file:///{filename}"
                        self.metadata_service.set_resource_identifier(resource_uri)
                        
                        # Write metadata
                        write_result = self.metadata_service.write_metadata(input_filepath, ai_metadata, targets=targets)
                    
                    # Log results
                    if debug_logging:
                        success_targets = [t for t, success in write_result.items() if success]
                        if success_targets:
                            print(f"[WorkflowExtractor] Successfully wrote metadata to: {', '.join(success_targets)}")
                        else:
                            print("[WorkflowExtractor] Failed to write metadata to any target")
            
            # Build summary text
            summary = "Split Workflow Extractor Results:\n"
            summary += f"Found fields: {', '.join(available_fields)}\n"
            
            if prompt_data:
                summary += f"Prompt data: {len(json.dumps(prompt_data))} bytes\n"
            if workflow_data:
                summary += f"Workflow data: {len(json.dumps(workflow_data))} bytes\n"
            
            # Add generation details
            if ai_metadata and "ai_info" in ai_metadata and "generation" in ai_metadata["ai_info"]:
                gen = ai_metadata["ai_info"]["generation"]
                if "model" in gen:
                    summary += f"Model: {gen['model']}\n"
                if "prompt" in gen:
                    prompt = gen["prompt"]
                    if len(prompt) > 100:
                        prompt = prompt[:100] + "..."
                    summary += f"Prompt: {prompt}\n"
                if "seed" in gen:
                    summary += f"Seed: {gen['seed']}\n"
                if "sampler_name" in gen:
                    summary += f"Sampler: {gen['sampler_name']}\n"
                if "loras" in gen and gen["loras"]:
                    loras = [lora.get("name", "Unknown") for lora in gen["loras"]]
                    summary += f"LoRAs: {', '.join(loras)}\n"
            
            # Add metadata write results
            if write_result:
                success_targets = [t for t, success in write_result.items() if success]
                if success_targets:
                    summary += f"\nMetadata written to: {', '.join(success_targets)}\n"
                else:
                    summary += "\nMetadata was not written to any targets\n"
                    if not overwrite_existing:
                        summary += "(Tip: set overwrite_existing=True to replace existing metadata)\n"
            
            return (image, summary, merged_workflow)
            
        except Exception as e:
            import traceback
            error_msg = f"Split workflow extraction failed: {str(e)}"
            print(f"[WorkflowExtractor] ERROR: {error_msg}")
            traceback.print_exc()
            return (image, error_msg, {})
        finally:
            # Ensure cleanup always happens
            self.cleanup()
    
    def _extract_generation_data(self, workflow):
        """Extract generation parameters from workflow data"""
        result = {"ai_info": {"generation": {}}}
        generation = result["ai_info"]["generation"]
        prompt_texts = {"positive": [], "negative": []}
        
        try:
            # Process nodes if available
            if "nodes" in workflow:
                for node in workflow["nodes"]:
                    # Handle standard nodes by type
                    node_type = node.get("type", node.get("class_type", ""))
                    node_inputs = node.get("inputs", {})
                    
                    # Extract model info
                    if node_type in ["CheckpointLoaderSimple", "CheckpointLoader"]:
                        if "ckpt_name" in node_inputs:
                            generation["model"] = node_inputs["ckpt_name"]
                    
                    # Extract sampler info
                    elif node_type in ["KSampler", "KSamplerAdvanced"]:
                        for key in ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"]:
                            if key in node_inputs:
                                generation[key] = node_inputs[key]
                    
                    # Extract VAE info
                    elif node_type == "VAELoader":
                        if "vae_name" in node_inputs:
                            generation["vae"] = node_inputs["vae_name"]
                    
                    # Extract prompt info - handle different prompt node types
                    elif node_type in ["CLIPTextEncode", "CLIPTextEncodeSDXL", "CLIPTextEncodeSD3"]:
                        # Get prompt text
                        if "text" in node_inputs:
                            text = node_inputs["text"]
                            
                            # Determine if positive or negative
                            is_negative = False
                            if "is_negative" in node:
                                is_negative = bool(node["is_negative"])
                            elif "_meta" in node and "title" in node["_meta"] and "negative" in node["_meta"]["title"].lower():
                                is_negative = True
                            
                            if is_negative:
                                prompt_texts["negative"].append(text)
                            else:
                                prompt_texts["positive"].append(text)
                    
                    # Extract LoRA info
                    elif node_type in ["LoraLoader", "LoraLoaderTagsQuery"]:
                        if "lora_name" in node_inputs:
                            if "loras" not in generation:
                                generation["loras"] = []
                            
                            lora = {
                                "name": node_inputs["lora_name"],
                                "strength_model": node_inputs.get("strength_model", 1.0),
                                "strength_clip": node_inputs.get("strength_clip", 1.0)
                            }
                            generation["loras"].append(lora)
            
            # Add combined prompt texts
            generation["prompt"] = "\n".join(prompt_texts["positive"]) if prompt_texts["positive"] else ""
            generation["negative_prompt"] = "\n".join(prompt_texts["negative"]) if prompt_texts["negative"] else ""
            
            # Add timestamp
            generation["timestamp"] = self.metadata_service.get_timestamp()
            
            return result
            
        except Exception as e:
            print(f"[WorkflowExtractor] Error extracting generation data: {str(e)}")
            return result
            
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "SplitWorkflowExtractorNode_V2": SplitWorkflowExtractorNode_V2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SplitWorkflowExtractorNode_V2": "Split Workflow Extractor V2"
}