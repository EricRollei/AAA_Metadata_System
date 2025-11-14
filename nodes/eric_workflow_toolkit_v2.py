"""
ComfyUI Node: eric's Workflow Toolkit V1
Description: A comprehensive workflow management tool that extracts, analyzes, and visualizes
    workflows from AI-generated images with multiple output formats.
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
- numpy: BSD 3-Clause
- base64: BSD 3-Clause
- re: BSD 3-Clause
- json: BSD 3-Clause

Eric's Workflow Toolkit V1 - Updated March 2025

A comprehensive workflow management tool that extracts, analyzes, and visualizes
workflows from AI-generated images with multiple output formats.

Features:
- Workflow extraction from PNG metadata
- Multiple visualization formats (graph, text, JSON)
- Detailed workflow analysis and component identification
- Support for ComfyUI and other AI generators
- Integration with the metadata system for proper storage
"""

import os
import json
import torch
import datetime
import base64
import re
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union
from PIL import Image

# Import the metadata service from the package
from custom_nodes.AAA_Metadata_System import MetadataService
# Import the new version of the workflow metadata processor
from custom_nodes.AAA_Metadata_System.eric_metadata.utils.workflow_metadata_processor import WorkflowMetadataProcessor

class WorkflowToolkitNode:
    """Unified workflow extraction, analysis and visualization"""
    
    def __init__(self):
        """Initialize with metadata service"""
        # Set debug flag first
        self.debug = False # Default to False
        
        self.metadata_service = MetadataService(debug=self.debug)
        
        # Initialize workflow metadata processor
        self.workflow_processor = WorkflowMetadataProcessor(debug=self.debug, discovery_mode=True)
        
        # Cache for optimization
        self.workflow_cache = {}
        # Flag for graphviz availability
        self.has_graphviz = self._check_graphviz()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_filepath": ("STRING", {"default": ""}),
                "operation_mode": (["extract", "analyze", "visualize"], {"default": "extract"}),
            },
            "optional": {
                "image": ("IMAGE", ),
                # Mode-specific options
                "visualization_type": (["graph", "text", "json"], {"default": "graph"}),
                "detailed_output": ("BOOLEAN", {"default": True}),
                "extract_from_tensor": ("BOOLEAN", {"default": True}),
                # Output options
                "output_directory": ("STRING", {"default": "workflow_output"}),
                # Metadata options
                "write_to_xmp": ("BOOLEAN", {"default": True}),
                "embed_metadata": ("BOOLEAN", {"default": False}),
                "write_text_file": ("BOOLEAN", {"default": False}),
                "write_to_database": ("BOOLEAN", {"default": False}),
                "overwrite_existing": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": True})
            }
        }

    RETURN_TYPES = ("STRING", "DICT", "DICT", "IMAGE")
    RETURN_NAMES = ("result", "workflow_data", "structured_analysis", "image")
    FUNCTION = "process_workflow"
    CATEGORY = "Eric's Nodes/Workflow"

    def process_workflow(self, 
                        input_filepath: str,
                        operation_mode: str,
                        image: Optional[torch.Tensor] = None,
                        visualization_type: str = "graph",
                        detailed_output: bool = True,
                        extract_from_tensor: bool = True,
                        output_directory: str = "workflow_output",
                        write_to_xmp: bool = True,
                        embed_metadata: bool = False,
                        write_text_file: bool = False,
                        write_to_database: bool = False,
                        overwrite_existing: bool = False,
                        debug_logging: bool = True) -> Tuple[str, Dict[str, Any], Dict[str, Any], torch.Tensor]:
        """
        Process workflow based on selected operation mode
        
        Args:
            input_filepath: Path to the image file to extract workflow from
            operation_mode: Processing mode to apply:
                - 'extract': Extract and store workflow data from image
                - 'analyze': Generate detailed analysis of workflow data
                - 'visualize': Create visual representation of workflow
            image: Optional image tensor to extract workflow from instead of file
            visualization_type: Type of visualization to create (for 'visualize' mode):
                - 'graph': Create visual graph diagram of workflow nodes
                - 'text': Create human-readable text description
                - 'json': Create structured JSON representation
            detailed_output: Whether to include detailed information in analysis
            extract_from_tensor: Whether to try extracting workflow from image tensor
            output_directory: Directory for saving output files
            write_to_xmp: Whether to write extracted metadata to XMP sidecar
            embed_metadata: Whether to embed metadata in the image file itself
            write_text_file: Whether to write metadata to text file
            write_to_database: Whether to write metadata to database (if configured)
            overwrite_existing: Whether to overwrite existing metadata
            debug_logging: Whether to enable detailed debug logging
            
        Returns:
            Tuple containing:
            - result (str): Text result or path to output file
            - workflow_data (Dict): Raw workflow data dictionary
            - structured_analysis (Dict): Structured analysis data
            - image (torch.Tensor): Original or placeholder image tensor
        """

        try:
            # Enable debug logging if requested
            self.debug = debug_logging
            self.metadata_service.debug = debug_logging
            self.workflow_processor.debug = debug_logging
            
            if debug_logging:
                print(f"[WorkflowToolkit] Starting workflow processing in {operation_mode} mode")
                print(f"[WorkflowToolkit] Input filepath: {input_filepath}")
            
            # Create placeholder for structured data
            structured_data = {}
            
            # Check input validity
            if not input_filepath and image is None:
                return "No input provided (need filepath or image)", {}, structured_data, image if image is not None else torch.zeros((1, 1, 3))
                
            # Extract workflow data based on inputs
            workflow_data, workflow_source = self._extract_workflow_data(
                input_filepath, image, extract_from_tensor, debug_logging)
                
            if not workflow_data:
                return "No workflow data found in the provided input", {}, structured_data, image if image is not None else torch.zeros((1, 1, 3))
                
            # Process based on selected mode
            if operation_mode == "extract":
                # Extract and store workflow
                result = self._handle_extraction(
                    input_filepath, workflow_data, workflow_source,
                    write_to_xmp, embed_metadata, write_text_file, 
                    write_to_database, overwrite_existing)
                    
            elif operation_mode == "analyze":
                # Generate analysis of workflow and structured data
                result = self._analyze_workflow(
                    workflow_data, workflow_source, detailed_output)
                
                # Set structured data from last analysis if available
                structured_data = self.last_analysis_summary if hasattr(self, 'last_analysis_summary') else {}
                
                # If we don't have a proper structured data, generate one using _process_workflow_data
                if not structured_data:
                    processed_data = self._process_workflow_data(workflow_data, workflow_source, detailed_output)
                    structured_data = processed_data.get('summary', {})
                    self.last_analysis_summary = structured_data
                    
            elif operation_mode == "visualize":
                # Create visualization
                result = self._visualize_workflow(
                    input_filepath, workflow_data, workflow_source,
                    visualization_type, output_directory, detailed_output)
            else:
                result = f"Unknown operation mode: {operation_mode}"
                
            return result, workflow_data, structured_data, image if image is not None else torch.zeros((1, 1, 3))
            
        except Exception as e:
            import traceback
            error_msg = f"Workflow processing failed: {str(e)}"
            print(f"[WorkflowToolkit] ERROR: {error_msg}")
            if debug_logging:
                traceback.print_exc()
            structured_data = {'error': str(e)}
            return error_msg, {}, structured_data, image if image is not None else torch.zeros((1, 1, 3))
        finally:
            # Always ensure cleanup happens
            self.cleanup()
            
    def _extract_workflow_data(self, 
                            input_filepath: str, 
                            image: Optional[torch.Tensor],
                            extract_from_tensor: bool,
                            debug_logging: bool) -> Tuple[Dict, str]:
        """
        Extract workflow data from file or tensor
        
        Returns:
            Tuple of (workflow_data, source_type)
        """
        workflow_data = {}
        workflow_source = "unknown"
        
        # First try tensor if provided and option enabled
        if image is not None and extract_from_tensor:
            if debug_logging:
                print("[WorkflowToolkit] Attempting to extract workflow from tensor")
                
            # Create temporary file to save the image
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_filename = temp_file.name
                
            # Convert tensor to PIL and save
            if len(image.shape) == 4:  # [B,H,W,C]
                img_np = image[0].cpu().numpy()
            else:  # [H,W,C]
                img_np = image.cpu().numpy()
                
            # Convert to uint8 for PIL
            import numpy as np
            if img_np.dtype != np.uint8:
                img_np = (img_np * 255).clip(0, 255).astype(np.uint8)
                
            # Convert to PIL image and save
            from PIL import Image
            pil_image = Image.fromarray(img_np)
            pil_image.save(temp_filename)
            
            # NEW: Use enhanced processor to extract workflow data
            extraction_result = self.workflow_processor.extract_from_source('file', temp_filename)
            
            # Clean up temporary file
            try:
                import os
                os.unlink(temp_filename)
            except:
                pass
                
            # Check if extraction succeeded
            if 'error' not in extraction_result and 'workflow' in extraction_result:
                workflow_data = extraction_result['workflow']
                workflow_source = extraction_result.get('source', self._identify_workflow_source(workflow_data))
                if debug_logging:
                    print(f"[WorkflowToolkit] Successfully extracted workflow from tensor: {workflow_source}")
                return workflow_data, workflow_source
        
        # If we get here, tensor extraction failed or was skipped
        if input_filepath and os.path.exists(input_filepath):
            # Check if we already have this in cache
            if input_filepath in self.workflow_cache:
                if debug_logging:
                    print("[WorkflowToolkit] Using cached workflow data")
                return self.workflow_cache[input_filepath]
            
            # NEW: Use enhanced processor to extract from file
            extraction_result = self.workflow_processor.extract_from_source('file', input_filepath)
            
            # Check if extraction succeeded
            if 'error' not in extraction_result and 'workflow' in extraction_result:
                workflow_data = extraction_result['workflow']
                workflow_source = extraction_result.get('source', self._identify_workflow_source(workflow_data))
                # Cache the result
                self.workflow_cache[input_filepath] = (workflow_data, workflow_source)
                if debug_logging:
                    print(f"[WorkflowToolkit] Successfully extracted workflow: {workflow_source}")
                return workflow_data, workflow_source
        
        # If we get here, all extraction methods failed
        return {}, "unknown"
    
    def _extract_from_png(self, filepath: str) -> Dict:
        """Extract workflow data directly from PNG metadata"""
        try:
            with Image.open(filepath) as img:
                # Check for various metadata fields where workflow might be stored
                for field in ['parameters', 'workflow', 'prompt']:
                    if field in img.info:
                        data = img.info[field]
                        try:
                            # Try to parse as JSON
                            return json.loads(data)
                        except json.JSONDecodeError:
                            # Not JSON, might be raw text
                            continue
            
            return {}
        except Exception as e:
            print(f"[WorkflowToolkit] PNG extraction error: {str(e)}")
            return {}
    
    def _extract_from_tensor(self, image: torch.Tensor) -> Dict:
        """Extract workflow data from image tensor"""
        try:
            # Convert tensor to PIL Image
            if len(image.shape) == 4:  # [B,H,W,C]
                # Take first image if batched
                img_np = image[0].cpu().numpy()
            else:  # [H,W,C]
                img_np = image.cpu().numpy()
            
            # Convert to uint8 for PIL
            if img_np.dtype != np.uint8:
                img_np = (img_np * 255).clip(0, 255).astype(np.uint8)
            
            # Convert to PIL image
            pil_image = Image.fromarray(img_np)
            
            # Create temporary file to save the image
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # Save image to temporary file
            pil_image.save(temp_filename)
            
            # Extract workflow from the saved PNG
            result = self._extract_from_png(temp_filename)
            
            # Clean up temporary file
            try:
                os.unlink(temp_filename)
            except:
                pass
                
            return result
            
        except Exception as e:
            print(f"[WorkflowToolkit] Tensor extraction error: {str(e)}")
            return {}
    
    def _identify_workflow_source(self, workflow: Dict) -> str:
        """Identify the source AI system of the workflow"""
        # Check for explicit type marker
        if 'type' in workflow:
            workflow_type = workflow.get('type', '')
            if 'comfy' in workflow_type.lower():
                return 'comfyui'
            if 'a1111' in workflow_type.lower() or 'automatic' in workflow_type.lower():
                return 'automatic1111'
            if 'stable' in workflow_type.lower() and 'diffusion' in workflow_type.lower():
                return 'stable_diffusion_webui'
            if 'novelai' in workflow_type.lower():
                return 'novelai'
            return workflow_type
            
        # Look for ComfyUI specific structure
        if 'prompt' in workflow and isinstance(workflow['prompt'], dict) and 'nodes' in workflow.get('prompt', {}):
            return 'comfyui'
            
        # Look for A1111 specific structure
        if all(k in workflow for k in ['prompt', 'negative_prompt', 'sampler']):
            return 'automatic1111'
            
        # Look for NovelAI specific markers
        if 'novelai' in str(workflow).lower() or 'nai' in str(workflow).lower():
            return 'novelai'
            
        return 'unknown'
    
    def _handle_extraction(self, 
                          input_filepath: str,
                          workflow_data: Dict,
                          workflow_source: str,
                          write_to_xmp: bool,
                          embed_metadata: bool,
                          write_text_file: bool,
                          write_to_database: bool,
                          overwrite_existing: bool) -> str:
        """Handle workflow extraction and storage in metadata"""
        if not input_filepath:
            return "Cannot extract workflow: No input filepath provided"
        
        # Structure the metadata
        metadata = {
            'ai_info': {
                'workflow': workflow_data,
                'generation': self._extract_generation_params(workflow_data, workflow_source)
            }
        }
        
        # Set targets based on user preferences
        targets = []
        if write_to_xmp: targets.append('xmp')
        if embed_metadata: targets.append('embedded')
        if write_text_file: targets.append('txt')
        if write_to_database: targets.append('db')
        
        if not targets:
            return "Workflow extracted but no storage targets selected"
        
        # Set resource identifier
        filename = os.path.basename(input_filepath)
        resource_uri = f"file:///{filename}"
        self.metadata_service.set_resource_identifier(resource_uri)
        
        # Store the workflow
        if overwrite_existing:
            # Write directly
            write_results = self.metadata_service.write_metadata(
                input_filepath, metadata, targets=targets)
        else:
            # Merge with existing metadata
            write_results = self.metadata_service.merge_metadata(
                input_filepath, metadata, targets=targets)
        
        # Build result message
        success_targets = [t for t, success in write_results.items() if success]
        fail_targets = [t for t, success in write_results.items() if not success]
        
        if all(write_results.values()):
            return f"Successfully extracted workflow ({workflow_source}) and stored to all targets"
        elif any(write_results.values()):
            return f"Partially stored workflow ({workflow_source})\nSuccess: {', '.join(success_targets)}\nFailed: {', '.join(fail_targets)}"
        else:
            return f"Extracted workflow ({workflow_source}) but failed to store to any target"
    
    def _extract_generation_params(self, workflow: Dict, source: str) -> Dict:
        """Extract generation parameters from workflow based on source"""
        generation_params = {}
        
        if source == 'comfyui':
            # Extract from ComfyUI workflow
            if 'prompt' in workflow and isinstance(workflow['prompt'], dict):
                nodes = workflow['prompt'].get('nodes', {})
                
                # Find checkpoint nodes
                for node_id, node in nodes.items():
                    node_type = node.get('class_type', '')
                    inputs = node.get('inputs', {})
                    
                    # Extract model
                    if 'Checkpoint' in node_type and 'ckpt_name' in inputs:
                        generation_params['model'] = inputs['ckpt_name']
                    
                    # Extract sampler settings
                    elif 'KSampler' in node_type:
                        generation_params['sampler'] = inputs.get('sampler_name')
                        generation_params['scheduler'] = inputs.get('scheduler')
                        generation_params['steps'] = inputs.get('steps')
                        generation_params['cfg_scale'] = inputs.get('cfg')
                        generation_params['seed'] = inputs.get('seed')
                    
                    # Extract VAE
                    elif 'VAE' in node_type and 'vae_name' in inputs:
                        generation_params['vae'] = inputs['vae_name']
                    
                    # Extract prompt
                    elif 'CLIPTextEncode' in node_type and 'text' in inputs:
                        if node.get('is_negative', False):
                            generation_params['negative_prompt'] = inputs['text']
                        else:
                            generation_params['prompt'] = inputs['text']
            
        elif source in ['automatic1111', 'stable_diffusion_webui']:
            # Direct copy of parameters from A1111/SD-WebUI
            for key in ['model', 'prompt', 'negative_prompt', 'sampler',
                      'steps', 'cfg_scale', 'seed', 'vae']:
                if key in workflow:
                    generation_params[key] = workflow[key]
        
        # Add timestamp
        generation_params['timestamp'] = datetime.datetime.now().isoformat()
        
        return generation_params
    
    def _analyze_workflow(self, 
                        workflow_data: Dict, 
                        workflow_source: str,
                        detailed_output: bool) -> str:
        """
        Generate detailed analysis of workflow
        
        Args:
            workflow_data: Raw workflow data
            workflow_source: Source of the workflow (comfyui, automatic1111, etc.)
            detailed_output: Whether to include detailed information
            
        Returns:
            str: Textual analysis of the workflow
        """
        try:
            # Process workflow data with our processor
            metadata = self.workflow_processor.process_workflow_data(workflow_data)
            
            # Store metadata for other operations if needed
            self.last_analyzed_metadata = metadata
            
            # Create text representation for display - use the processor's formatter
            text_analysis = self.workflow_processor.format_metadata_for_output(metadata, format_type='text')
            
            # For detailed output, add workflow statistics if available
            if detailed_output and 'ai_info' in metadata and 'workflow_stats' in metadata['ai_info']:
                stats = metadata['ai_info']['workflow_stats']
                stats_text = ["\n## Workflow Statistics"]
                
                if 'node_count' in stats:
                    stats_text.append(f"- Total nodes: {stats['node_count']}")
                if 'connection_count' in stats:
                    stats_text.append(f"- Connections: {stats['connection_count']}")
                if 'complexity' in stats:
                    stats_text.append(f"- Complexity score: {stats['complexity']}")
                if 'unique_node_types' in stats:
                    stats_text.append(f"- Unique node types: {stats['unique_node_types']}")
                    
                # Add node type breakdown if available
                if 'node_types' in stats and detailed_output:
                    stats_text.append("\n### Node Type Breakdown")
                    for node_type, count in stats['node_types'].items():
                        stats_text.append(f"- {node_type}: {count}")
                
                # Append stats to the analysis
                text_analysis += "\n" + "\n".join(stats_text)
            
            return text_analysis
            
        except Exception as e:
            # Provide clear error message
            error_msg = f"Error analyzing workflow: {str(e)}"
            if self.debug:
                import traceback
                error_msg += f"\n{traceback.format_exc()}"
            return error_msg
    
    def _export_metadata(self, workflow_data, output_path):
        """Export processed metadata to a file"""
        
        # Process workflow data
        metadata = self.workflow_processor.process_embedded_data(workflow_data)
        
        # Save to JSON file
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        return f"Metadata exported to {output_path}"

    def _analyze_comfyui_workflow(self, workflow: Dict, detailed: bool) -> List[str]:
        """Analyze ComfyUI workflow"""
        analysis = []
        
        # Get the prompt data
        prompt = workflow.get('prompt', {})
        nodes = prompt.get('nodes', {})
        
        analysis.append(f"\nTotal nodes: {len(nodes)}")
        
        # Find interesting nodes like checkpoints, samplers, etc.
        checkpoints = []
        samplers = []
        vae = []
        text_prompts = []
        loras = []
        
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Extract model info
            if 'Checkpoint' in node_type and 'ckpt_name' in inputs:
                checkpoints.append(inputs['ckpt_name'])
            
            # Extract sampler info
            elif 'KSampler' in node_type:
                sampler_info = {
                    'sampler': inputs.get('sampler_name', 'unknown'),
                    'scheduler': inputs.get('scheduler', 'unknown'),
                    'steps': inputs.get('steps', 0),
                    'cfg': inputs.get('cfg', 0),
                    'seed': inputs.get('seed', 0),
                }
                samplers.append(sampler_info)
            
            # Extract VAE info
            elif 'VAE' in node_type and 'vae_name' in inputs:
                vae.append(inputs['vae_name'])
            
            # Extract prompt info
            elif 'CLIPTextEncode' in node_type and 'text' in inputs:
                text_type = 'negative' if node.get('is_negative', False) else 'positive'
                text_prompts.append({
                    'type': text_type,
                    'text': inputs['text']
                })
                
            # Extract LoRA info
            elif 'LoRA' in node_type:
                lora_info = {
                    'name': inputs.get('lora_name', 'unknown'),
                    'strength_model': inputs.get('strength_model', 1.0),
                    'strength_clip': inputs.get('strength_clip', 1.0)
                }
                loras.append(lora_info)
        
        # Write the extracted information
        if checkpoints:
            analysis.append("\n## Models")
            for cp in checkpoints:
                analysis.append(f"- {cp}")
            
        if vae:
            analysis.append("\n## VAE")
            for v in vae:
                analysis.append(f"- {v}")
            
        if samplers:
            analysis.append("\n## Sampling")
            for i, s in enumerate(samplers):
                analysis.append(f"Sampler {i+1}:")
                analysis.append(f"  - Type: {s['sampler']} + {s['scheduler']}")
                analysis.append(f"  - Steps: {s['steps']}")
                analysis.append(f"  - CFG: {s['cfg']}")
                analysis.append(f"  - Seed: {s['seed']}")
            
        if loras:
            analysis.append("\n## LoRAs")
            for i, lora in enumerate(loras):
                analysis.append(f"- {lora['name']} (Model: {lora['strength_model']}, CLIP: {lora['strength_clip']})")
            
        if text_prompts:
            analysis.append("\n## Prompts")
            
            # Group by type
            positive = [p['text'] for p in text_prompts if p['type'] == 'positive']
            negative = [p['text'] for p in text_prompts if p['type'] == 'negative']
            
            if positive:
                analysis.append("\nPositive prompt:")
                for p in positive:
                    analysis.append(p)
            
            if negative:
                analysis.append("\nNegative prompt:")
                for n in negative:
                    analysis.append(n)
        
        # Add node type summary if detailed
        if detailed:
            node_types = {}
            for node_id, node in nodes.items():
                node_type = node.get('class_type', 'Unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            analysis.append("\n## Node Types")
            for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
                analysis.append(f"- {node_type}: {count}")
        
        return analysis
    
    def _analyze_a1111_workflow(self, workflow: Dict, detailed: bool) -> List[str]:
        """Analyze Automatic1111/SD-WebUI workflow"""
        analysis = []
        
        # Basic info
        if 'model' in workflow:
            analysis.append(f"\n## Model")
            analysis.append(f"- {workflow['model']}")
        
        if 'vae' in workflow:
            analysis.append(f"\n## VAE")
            analysis.append(f"- {workflow['vae']}")
        
        # Sampling parameters
        analysis.append(f"\n## Sampling Parameters")
        for param in ['sampler', 'steps', 'cfg_scale', 'seed']:
            if param in workflow:
                analysis.append(f"- {param}: {workflow[param]}")
        
        # Prompt information
        if 'prompt' in workflow:
            analysis.append(f"\n## Positive Prompt")
            analysis.append(workflow['prompt'])
        
        if 'negative_prompt' in workflow:
            analysis.append(f"\n## Negative Prompt")
            analysis.append(workflow['negative_prompt'])
        
        # Extra parameters if detailed
        if detailed:
            analysis.append(f"\n## Additional Parameters")
            skip_keys = ['model', 'vae', 'sampler', 'steps', 'cfg_scale', 'seed', 
                        'prompt', 'negative_prompt']
            
            for key, value in workflow.items():
                if key not in skip_keys:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:97] + "..."
                    analysis.append(f"- {key}: {value}")
        
        return analysis
    
    def _visualize_workflow(self, 
                           input_filepath: str,
                           workflow_data: Dict, 
                           workflow_source: str,
                           visualization_type: str,
                           output_directory: str,
                           detailed_output: bool) -> str:
        """
        Generate workflow visualization in various formats
        
        This method creates visual representations of workflow data in different formats:
        - text: A human-readable text description of the workflow
        - json: A structured JSON representation of the workflow
        - graph: A visual graph representation of the workflow using graphviz
        
        Args:
            input_filepath: Path to the image file (used for naming output)
            workflow_data: Raw workflow data dictionary
            workflow_source: Source of the workflow (comfyui, automatic1111, etc.)
            visualization_type: Format of visualization ('text', 'json', or 'graph')
            output_directory: Directory to save visualization files
            detailed_output: Whether to include detailed information
            
        Returns:
            str: Path to the visualization file or error message
            
        Notes:
            - Graph visualization requires graphviz to be installed
            - For unsupported workflow sources, falls back to JSON
        """
        # Create output directory if needed
        output_path = self._ensure_output_directory(output_directory)
        if not output_path:
            return "Failed to create output directory"
        
        # Create base filename
        if input_filepath:
            basename = os.path.basename(input_filepath)
            base_name = os.path.splitext(basename)[0]
        else:
            # Create a name based on timestamp if no input file
            base_name = f"workflow_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Handle different visualization types
        if visualization_type == "text":
            # Text representation
            output_file = os.path.join(output_path, f"{base_name}_workflow.txt")
            return self._create_text_visualization(
                workflow_data, workflow_source, output_file, detailed_output)
                
        elif visualization_type == "json":
            # JSON representation
            output_file = os.path.join(output_path, f"{base_name}_workflow.json")
            return self._create_json_visualization(workflow_data, output_file)
            
        elif visualization_type == "graph":
            # Graph visualization
            output_file = os.path.join(output_path, f"{base_name}_workflow_graph.png")
            
            if not self.has_graphviz and workflow_source == 'comfyui':
                print("[WorkflowToolkit] Warning: graphviz not available, falling back to JSON")
                output_file = os.path.join(output_path, f"{base_name}_workflow.json")
                return self._create_json_visualization(
                    workflow_data, output_file,
                    "Graphviz not available for graph visualization; using JSON instead"
                )
            
            return self._create_graph_visualization(
                workflow_data, workflow_source, output_file, detailed_output)
        
        return f"Unknown visualization type: {visualization_type}"
    
    def _ensure_output_directory(self, output_directory: str) -> str:
        """Create output directory if needed"""
        try:
            # Handle absolute and relative paths
            if os.path.isabs(output_directory):
                full_path = output_directory
            else:
                # Use current directory as base
                base_path = os.getcwd()
                full_path = os.path.join(base_path, output_directory)
            
            # Create the directory if needed
            os.makedirs(full_path, exist_ok=True)
            return full_path
        except Exception as e:
            print(f"[WorkflowToolkit] Failed to create output directory: {str(e)}")
            return ""
    
    def _create_text_visualization(self, 
                                 workflow_data: Dict,
                                 workflow_source: str,
                                 output_file: str,
                                 detailed: bool) -> str:
        """Create text visualization of workflow"""
        try:
            # Get analysis text
            analysis = self._analyze_workflow(workflow_data, workflow_source, detailed)
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis)
            
            return f"Text visualization saved to {output_file}"
        except Exception as e:
            return f"Failed to create text visualization: {str(e)}"
    
    def _create_json_visualization(self, 
                                 workflow_data: Dict,
                                 output_file: str,
                                 message: Optional[str] = None) -> str:
        """Create JSON visualization of workflow"""
        try:
            # Write JSON to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2)
            
            return message or f"JSON workflow saved to {output_file}"
        except Exception as e:
            return f"Failed to create JSON visualization: {str(e)}"
    
    def _create_graph_visualization(self, 
                                  workflow_data: Dict,
                                  workflow_source: str,
                                  output_file: str,
                                  detailed: bool) -> str:
        """Create graph visualization of workflow"""
        if workflow_source == 'comfyui':
            return self._create_comfyui_graph(workflow_data, output_file, detailed)
        else:
            # For non-ComfyUI workflows, fall back to JSON for now
            json_file = output_file.replace('.png', '.json')
            return self._create_json_visualization(
                workflow_data, json_file,
                f"Graph visualization not supported for {workflow_source}; saved as JSON instead"
            )
    
    def _create_comfyui_graph(self, 
                            workflow_data: Dict,
                            output_file: str,
                            detailed: bool) -> str:
        """Create graph visualization for ComfyUI workflow"""
        try:
            import graphviz
            
            # Create a new directed graph
            dot = graphviz.Digraph(comment='ComfyUI Workflow Visualization')
            dot.attr(rankdir='TB', size='12,12', dpi='150')
            
            # Get the nodes and links
            prompt = workflow_data.get('prompt', {})
            nodes = prompt.get('nodes', {})
            
            if not nodes:
                return "Cannot create graph: No nodes found in workflow"
            
            # First pass: Create all nodes
            for node_id, node in nodes.items():
                node_class = node.get('class_type', 'Unknown')
                
                # Customize node appearance based on type
                node_style = {
                    'shape': 'box',
                    'style': 'filled',
                    'fontsize': '10',
                }
                
                # Color-code by node type
                if 'Checkpoint' in node_class:
                    node_style['fillcolor'] = '#d0f0d0'  # Green for models
                elif 'KSampler' in node_class:
                    node_style['fillcolor'] = '#f0d0d0'  # Red for sampling
                elif 'VAE' in node_class:
                    node_style['fillcolor'] = '#d0d0f0'  # Blue for VAE
                elif 'CLIPText' in node_class:
                    node_style['fillcolor'] = '#f0f0d0'  # Yellow for text
                elif 'Save' in node_class or 'Save' in node_class:
                    node_style['fillcolor'] = '#f0c0a0'  # Orange for outputs
                elif 'LoRA' in node_class:
                    node_style['fillcolor'] = '#e6ccff'  # Purple for LoRAs
                else:
                    node_style['fillcolor'] = '#f0f0f0'  # Gray for others
                
                # Create a label with relevant info
                label_parts = [node_class]
                
                # Add key node parameters to label
                inputs = node.get('inputs', {})
                
                # Only include important fields in label
                important_fields = {
                    'ckpt_name': 'Model',
                    'vae_name': 'VAE',
                    'sampler_name': 'Sampler',
                    'scheduler': 'Scheduler',
                    'steps': 'Steps',
                    'cfg': 'CFG',
                    'seed': 'Seed',
                    'lora_name': 'LoRA',
                    'strength_model': 'Strength'
                }
                
                for field, label in important_fields.items():
                    if field in inputs:
                        label_parts.append(f"{label}: {inputs[field]}")
                
                # Handle text specially (truncate if needed)
                if 'text' in inputs:
                    text = inputs['text']
                    if len(text) > 50:
                        text = text[:47] + "..."
                    label_parts.append(f"Text: {text}")
                
                # Create node with proper styling
                dot.node(node_id, '\n'.join(label_parts), **node_style)
            
            # Second pass: Connect nodes
            for node_id, node in nodes.items():
                inputs = node.get('inputs', {})
                
                # Connect each input to its source
                for input_name, input_value in inputs.items():
                    if isinstance(input_value, list) and len(input_value) == 2:
                        source_node_id, source_output_name = input_value
                        
                        # Check if source node exists
                        if source_node_id in nodes:
                            # Add edge with label showing the connection
                            edge_label = f"{source_output_name} → {input_name}" if detailed else ""
                            dot.edge(
                                source_node_id, node_id, 
                                label=edge_label, 
                                fontsize='8'
                            )
            
            # Render the graph to file
            dot.render(output_file.replace('.png', ''), format='png', cleanup=True)
            
            # Return the actual output filepath (graphviz adds .png)
            actual_output = output_file.replace('.png', '') + '.png'
            return f"Graph visualization saved to {actual_output}"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # Fallback to JSON on error
            json_file = output_file.replace('.png', '.json')
            return self._create_json_visualization(
                workflow_data, json_file,
                f"Graph visualization failed ({str(e)}); saved as JSON instead"
            )
    
    def _process_workflow_data(self, workflow_data, workflow_source, detailed_output=True):
        """
        Process workflow data and return both structured and text representations
        
        Args:
            workflow_data: Raw workflow data dictionary
            workflow_source: Source of the workflow (comfyui, automatic1111, etc.)
            detailed_output: Whether to include detailed information
            
        Returns:
            dict: {
                'metadata': Processed metadata structure,
                'text_analysis': Text representation of the analysis,
                'summary': Brief summary of key workflow components
            }
        """
        # Process the workflow data with processor
        metadata = self.workflow_processor.process_workflow_data(workflow_data)
        
        # Generate text analysis based on metadata
        text_analysis = []
        summary = {}
        
        # Add header based on source
        text_analysis.append(f"# {workflow_source.upper()} Workflow Analysis")
        text_analysis.append("=" * 40)
        
        # Extract summary information
        if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
            generation = metadata['ai_info']['generation']
            
            # Build summary dictionary for structured access
            if 'model' in generation:
                summary['model'] = generation['model']
                text_analysis.append("\n## Base Model")
                text_analysis.append(f"- {generation['model']}")
            
            # Add other generation parameters
            text_analysis.append("\n## Generation Parameters")
            for param, label in [
                ('sampler', 'Sampler'),
                ('scheduler', 'Scheduler'),
                ('steps', 'Steps'),
                ('cfg_scale', 'CFG Scale'),
                ('seed', 'Seed')
            ]:
                if param in generation:
                    summary[param] = generation[param]
                    text_analysis.append(f"- {label}: {generation[param]}")
            
            # Add dimensions
            if 'width' in generation and 'height' in generation:
                dimensions = f"{generation['width']}x{generation['height']}"
                summary['dimensions'] = dimensions
                text_analysis.append(f"- Dimensions: {dimensions}")
        
        # Process other sections similarly...
        
        # Add LoRA information
        if 'ai_info' in metadata and 'loras' in metadata['ai_info']:
            loras = metadata['ai_info']['loras']
            if loras:
                lora_list = []
                text_analysis.append("\n## LoRA Models")
                for lora in loras:
                    if isinstance(lora, dict):
                        name = lora.get('name', 'Unknown')
                        strength = lora.get('strength', 1.0)
                        lora_list.append({"name": name, "strength": strength})
                        text_analysis.append(f"- {name} (Strength: {strength})")
                    else:
                        lora_list.append({"name": str(lora), "strength": 1.0})
                        text_analysis.append(f"- {lora}")
                summary['loras'] = lora_list
        
        # Return both structured and text representation
        return {
            'metadata': metadata,
            'text_analysis': "\n".join(text_analysis),
            'summary': summary
        }

    def manage_workflow_cache(self, action='get', input_filepath=None, cache_data=None):
        """
        Manage the workflow cache with various operations
        
        Args:
            action: 'get', 'set', 'clear', 'refresh', or 'info'
            input_filepath: Path to use as cache key
            cache_data: Data to store in cache (for 'set' action)
            
        Returns:
            Various data depending on action
        """
        if action == 'get' and input_filepath and input_filepath in self.workflow_cache:
            return self.workflow_cache[input_filepath]
        
        elif action == 'set' and input_filepath and cache_data:
            self.workflow_cache[input_filepath] = cache_data
            return True
        
        elif action == 'clear':
            if input_filepath and input_filepath in self.workflow_cache:
                # Clear specific entry
                del self.workflow_cache[input_filepath]
                return True
            else:
                # Clear entire cache
                self.workflow_cache.clear()
                return True
        
        elif action == 'refresh' and input_filepath:
            # Remove and reload specific entry
            if input_filepath in self.workflow_cache:
                del self.workflow_cache[input_filepath]
            # The actual reload would happen elsewhere
            return True
        
        elif action == 'info':
            # Return information about cache
            return {
                'size': len(self.workflow_cache),
                'keys': list(self.workflow_cache.keys()),
                'memory_usage': sum(len(str(v)) for v in self.workflow_cache.values())
            }
        
        return None
    def _safely_process_file(self, filepath, operation_func, *args, **kwargs):
        """
        Safely process a file with proper error handling
        
        Args:
            filepath: Path to the file
            operation_func: Function to call on successful file access
            *args, **kwargs: Additional arguments to pass to operation_func
            
        Returns:
            tuple: (result, error_message)
        """
        if not filepath:
            return None, "No filepath provided"
        
        if not os.path.exists(filepath):
            return None, f"File not found: {filepath}"
        
        try:
            # Check if file is accessible
            with open(filepath, 'rb') as f:
                # Just test access
                pass
            
            # Call the operation function
            result = operation_func(filepath, *args, **kwargs)
            return result, None
            
        except PermissionError:
            return None, f"Permission denied: {filepath}"
        except IsADirectoryError:
            return None, f"Expected a file, got directory: {filepath}"
        except FileNotFoundError:
            return None, f"File not found: {filepath}"
        except Exception as e:
            import traceback
            error_msg = f"Error processing file {filepath}: {str(e)}"
            if self.debug:
                error_msg += f"\n{traceback.format_exc()}"
            return None, error_msg

    def _check_graphviz(self) -> bool:
        """Check if graphviz is available"""
        try:
            import graphviz
            return True
        except ImportError:
            print("[WorkflowToolkit] Graphviz not available; graph visualization disabled")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Workflow_Toolkit_v2": WorkflowToolkitNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Workflow_Toolkit_v2": "Eric's Workflow Toolkit_v2"
}