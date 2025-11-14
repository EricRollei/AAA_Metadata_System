"""
workflowmetadataprocessor.py
Description: Processes workflow metadata from ComfyUI workflows or embedded image data.
    This class serves as a comprehensive processor for workflow data, providing a unified approach
    to extract metadata from ComfyUI workflows or embedded image data. (old version leaving in for now)
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
- opencv-python (cv2): Apache 2.0
- [Add other key dependencies used in this specific script]

Note: If this script depends on ultralytics (YOLO), be aware that it uses the AGPL-3.0
license which has implications for code distribution and modification.
"""
# Metadata_system/eric_metadata/workflow_metadata.py
import os
import json
import datetime
import re
import traceback
from typing import Dict, Any, Optional, List, Union, Tuple
import numpy as np
import xml.etree.ElementTree as ET
import io
import traceback  # For detailed error tracking in debug mode
import numpy as np
from PIL import Image

class WorkflowMetadataProcessor:
    """
    Processes workflow metadata from ComfyUI workflows or embedded image data.
    
    This class serves as a comprehensive processor for workflow data, providing
    functionality to extract, enhance, and format metadata from AI image generation
    workflows. It supports various input sources and can be used by multiple nodes
    that need to work with workflow metadata.
    
    Key capabilities:
    - Extract workflow data from images or direct workflow input
    - Process and structure metadata in a standardized format
    - Enhance metadata with additional contextual information
    - Generate search-optimized metadata fields
    - Format metadata for various output formats
    
    The class works with the WorkflowParser and WorkflowExtractor components
    to provide a complete metadata processing pipeline.
    """
    
    def __init__(self, debug: bool = False, discovery_mode: bool = False):
        """
        Initialize the workflow metadata processor.
        
        Args:
            debug: Whether to enable detailed debug output to console
            discovery_mode: Whether to collect and log unknown node types and parameters
                            for system improvement
        """
        self.debug = debug
        self.discovery_mode = discovery_mode
        
        # Initialize workflow parser and extractor components
        from .utils.workflow_parser import WorkflowParser
        from .utils.workflow_extractor import WorkflowExtractor
        
        self.workflow_parser = WorkflowParser(debug=self.debug)
        self.workflow_extractor = WorkflowExtractor(debug=self.debug, discovery_mode=self.discovery_mode)
    
    def process_workflow_data(self, prompt=None, extra_pnginfo=None):
        """
        Process workflow data from ComfyUI's prompt and extra_pnginfo structures.
        
        This method extracts and enhances metadata from the raw workflow data, combining
        information from multiple sources including the workflow graph, generation parameters,
        and additional context.
        
        Args:
            prompt: ComfyUI prompt data containing nodes and connections
            extra_pnginfo: Additional PNG info with possible workflow details
            
        Returns:
            dict: Processed metadata with AI generation info, workflow structure, and analysis
        """
        if not prompt:
            return {}
            
        # Initialize result structure with standard sections
        result = {
            'basic': {},  # Basic metadata like title, description
            'analysis': {},  # Analysis of workflow structure and complexity
            'ai_info': {  # AI-specific information
                'generation': {},  # Generation parameters
                'workflow_info': {}  # Workflow structure information
            }
        }
        
        # Extract metadata using workflow parser
        try:
            workflow_metadata = self.workflow_parser.convert_to_metadata_format(prompt)
            
            # Merge workflow metadata into result
            if 'ai_info' in workflow_metadata:
                # Copy all ai_info data
                for key, value in workflow_metadata['ai_info'].items():
                    if key == 'generation':
                        # For generation data, merge at the field level
                        for gen_key, gen_value in value.items():
                            result['ai_info']['generation'][gen_key] = gen_value
                    else:
                        # For other categories, copy the entire section
                        result['ai_info'][key] = value
                    
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error in workflow parser: {str(e)}")
        
        # Use workflow extractor for additional details
        try:
            extractor_metadata = self.workflow_extractor.extract_metadata(prompt, extra_pnginfo)
            self._merge_extractor_metadata(result, extractor_metadata)
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error in workflow extractor: {str(e)}")
        
        # Apply additional enhancements (extract LoRAs, upscalers, etc.)
        result = self.enhance_metadata(result, prompt, extra_pnginfo)
        
        # Add timestamp if not present
        if 'generation' in result['ai_info'] and 'timestamp' not in result['ai_info']['generation']:
            result['ai_info']['generation']['timestamp'] = datetime.datetime.now().isoformat()
        
        return result
    
    def process_embedded_data(self, image_path):
        """
        Extract and process workflow data from embedded image metadata.
        
        This method reads an image file and attempts to extract workflow data
        from its embedded metadata (like PNG text chunks).
        
        Args:
            image_path: Path to the image file to extract data from
            
        Returns:
            dict: Processed metadata from the embedded image data
        """
        if not image_path:
            return {'error': 'No image path provided'}
            
        try:
            # Read embedded workflow data
            from PIL import Image
            import json
            import os
                
            # Check if file exists
            if not os.path.exists(image_path):
                return {'error': f"Image file not found: {image_path}"}
                
            with Image.open(image_path) as img:
                # Try to get workflow data from PNG text chunks
                prompt = None
                extra_pnginfo = {}
                    
                if hasattr(img, 'text') and img.text:
                    # Look for workflow data in text chunks
                    if 'prompt' in img.text:
                        try:
                            prompt_text = img.text['prompt']
                            # Handle both string and bytes types
                            if isinstance(prompt_text, bytes):
                                prompt_text = prompt_text.decode('utf-8')
                            prompt = json.loads(prompt_text)
                        except Exception as e:
                            if self.debug:
                                print(f"[WorkflowMetadataProcessor] Error parsing prompt text chunk: {str(e)}")
                        
                    # Look for extra png info
                    if 'workflow' in img.text:
                        try:
                            workflow_text = img.text['workflow']
                            # Handle both string and bytes types
                            if isinstance(workflow_text, bytes):
                                workflow_text = workflow_text.decode('utf-8')
                            extra_pnginfo['workflow'] = json.loads(workflow_text)
                        except Exception as e:
                            if self.debug:
                                print(f"[WorkflowMetadataProcessor] Error parsing workflow text chunk: {str(e)}")
                                
                    # Check for A1111-style parameters
                    if 'parameters' in img.text and not prompt:
                        try:
                            # Extract A1111 parameters to a structured format
                            parameters = img.text['parameters']
                            if isinstance(parameters, bytes):
                                parameters = parameters.decode('utf-8')
                                
                            # This is a simple A1111 format parser
                            prompt_data = {'type': 'automatic1111'}
                            
                            # Try to extract prompt and negative prompt
                            parts = parameters.split('Negative prompt:', 1)
                            if len(parts) == 2:
                                prompt_data['prompt'] = parts[0].strip()
                                
                                # Split the remaining text to get negative prompt and parameters
                                remaining = parts[1]
                                param_start = remaining.find('Steps:')
                                
                                if param_start > 0:
                                    prompt_data['negative_prompt'] = remaining[:param_start].strip()
                                    param_text = remaining[param_start:]
                                    
                                    # Extract parameters using regex
                                    import re
                                    param_pattern = r'([a-zA-Z\s]+):\s*([^,]+)(?:,|$)'
                                    for match in re.finditer(param_pattern, param_text):
                                        key = match.group(1).strip().lower().replace(' ', '_')
                                        value = match.group(2).strip()
                                        prompt_data[key] = value
                                else:
                                    prompt_data['negative_prompt'] = remaining.strip()
                            else:
                                prompt_data['prompt'] = parameters
                                
                            # Use this as our prompt data
                            prompt = prompt_data
                        except Exception as e:
                            if self.debug:
                                print(f"[WorkflowMetadataProcessor] Error parsing parameters: {str(e)}")
                    
                if prompt:
                    # Process the workflow data
                    return self.process_workflow_data(prompt, extra_pnginfo)
                else:
                    # No valid workflow data found
                    return {'error': 'No workflow data found in image'}
                    
        except FileNotFoundError:
            error_msg = f"Image file not found: {image_path}"
            if self.debug:
                print(f"[WorkflowMetadataProcessor] {error_msg}")
            return {'error': error_msg}
        except PermissionError:
            error_msg = f"Permission denied: {image_path}"
            if self.debug:
                print(f"[WorkflowMetadataProcessor] {error_msg}")
            return {'error': error_msg}
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error processing embedded data: {str(e)}")
            return {'error': f"Failed to process image: {str(e)}"}
    
    def _parse_a1111_parameters(self, params_text):
        """
        Parse Automatic1111 style parameters text into structured data
        
        Args:
            params_text: Parameters text from image metadata
                
        Returns:
            dict: Structured parameter data
        """
        result = {'type': 'automatic1111'}
        
        try:
            # Split on the first 'Negative prompt:'
            parts = params_text.split('Negative prompt:', 1)
            if len(parts) == 2:
                result['prompt'] = parts[0].strip()
                result['negative_prompt'] = parts[1].strip()
            else:
                result['prompt'] = params_text.strip()
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error parsing A1111 parameters: {str(e)}")
        
        return result
    
    def enhance_metadata(self, metadata, prompt, extra_pnginfo=None):
        """
        Enhance metadata with additional contextual information.
        
        This method adds extra details to the metadata, such as LoRA models,    
        upscalers, and other workflow-specific information.
        
        Args:
            metadata: Metadata structure to enhance
            prompt: ComfyUI prompt data
            extra_pnginfo: Additional PNG info
            
        Returns:
            dict: Enhanced metadata
        """
        # Extract LoRA information
        loras = self._extract_lora_info(prompt)
        if loras:
            if 'ai_info' not in metadata:
                metadata['ai_info'] = {}
            metadata['ai_info']['loras'] = loras
            
        # Extract conditioning information
        conditioning = self._extract_conditioning_info(prompt)
        if conditioning:
            if 'ai_info' not in metadata:
                metadata['ai_info'] = {}
            metadata['ai_info']['conditioning'] = conditioning    
        
        # Extract upscaler information
        upscalers = self._extract_upscaler_info(prompt)
        if upscalers:
            if 'ai_info' not in metadata:
                metadata['ai_info'] = {}
            metadata['ai_info']['upscalers'] = upscalers
        
        # Extract workflow name
        workflow_name = self._find_workflow_name(prompt, extra_pnginfo)
        if workflow_name:
            if 'workflow_info' not in metadata['ai_info']:
                metadata['ai_info']['workflow_info'] = {}
            
            metadata['ai_info']['workflow_info']['name'] = workflow_name
            
            # Also add to basic metadata for easier access in searches
            if 'basic' not in metadata:
                metadata['basic'] = {}
            
            metadata['basic']['workflow'] = workflow_name
        
        # Add workflow_info.app key to identify this as ComfyUI data
        if 'workflow_info' not in metadata['ai_info']:
            metadata['ai_info']['workflow_info'] = {}
        metadata['ai_info']['workflow_info']['app'] = 'ComfyUI'
        
        # Add search-optimized metadata fields for easier discovery
        metadata = self._add_search_optimized_metadata(metadata, prompt, extra_pnginfo)
        
        return metadata
    
    def _add_search_optimized_metadata(self, metadata, prompt, extra_pnginfo=None):
        """
        Add search-optimized metadata fields to metadata.
        
        Creates flattened, standardized fields for easier searching and indexing
        of common AI generation parameters.
        
        Args:
            metadata: Metadata structure to enhance
            prompt: ComfyUI prompt data
            extra_pnginfo: Additional PNG info
            
        Returns:
            dict: Enhanced metadata with search-optimized fields
        """
        # Skip if no metadata
        if not metadata:
            return metadata
        
        import datetime  # Import datetime module for timestamp
        
        search_metadata = {}
        
        # Extract AI generation parameters
        if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
            generation = metadata['ai_info']['generation']
            
            # Map generation parameters to search-optimized flat keys
            param_mapping = {
                'model': 'ai:model',
                'sampler': 'ai:sampler',
                'scheduler': 'ai:scheduler',
                'steps': 'ai:steps',
                'cfg_scale': 'ai:cfg_scale',
                'seed': 'ai:seed',
                'width': 'ai:width',
                'height': 'ai:height',
                'vae': 'ai:vae'
            }
            
            for src_key, dest_key in param_mapping.items():
                if src_key in generation:
                    search_metadata[dest_key] = generation[src_key]
            
            # Handle prompts separately
            if 'prompt' in generation:
                search_metadata['ai:prompt'] = generation['prompt']
            if 'negative_prompt' in generation:
                search_metadata['ai:negative_prompt'] = generation['negative_prompt']
        
        # Extract LoRA information
        if 'ai_info' in metadata and 'loras' in metadata['ai_info']:
            loras = metadata['ai_info']['loras']
            if loras:
                lora_names = []
                for lora in loras:
                    if isinstance(lora, dict):
                        if 'name' in lora:
                            lora_names.append(lora['name'])
                    else:
                        lora_names.append(str(lora))
                
                if lora_names:
                    search_metadata['ai:loras'] = ', '.join(lora_names)
        
        # Extract workflow name
        if 'ai_info' in metadata and 'workflow_info' in metadata['ai_info']:
            workflow_info = metadata['ai_info']['workflow_info']
            if 'name' in workflow_info:
                search_metadata['ai:workflow_name'] = workflow_info['name']
            if 'app' in workflow_info:
                search_metadata['ai:app'] = workflow_info['app']
        
        # Add version and creation info
        search_metadata['ai:metadata_version'] = '1.0'
        search_metadata['ai:created'] = datetime.datetime.now().isoformat()
        
        # Add search-optimized fields to metadata
        if search_metadata:
            if 'search_optimized' not in metadata:
                metadata['search_optimized'] = {}
            metadata['search_optimized'].update(search_metadata)
        
        return metadata
    
    def _merge_extractor_metadata(self, result, extractor_metadata):
        """
        Merge metadata from workflow extractor into the result structure.
        
        Takes data extracted by the WorkflowExtractor component and merges it
        into the main metadata structure.
        
        Args:
            result: Result metadata structure to update (modified in place)
            extractor_metadata: Metadata from workflow extractor to merge in
        """
        # Extract generation parameters
        if 'generation' in extractor_metadata:
            gen_data = extractor_metadata['generation']
            
            # Update generation parameters, ignoring None and empty values
            if 'ai_info' not in result:
                result['ai_info'] = {}
            if 'generation' not in result['ai_info']:
                result['ai_info']['generation'] = {}
            
            for key, value in gen_data.items():
                if value not in (None, "", [], {}):
                    result['ai_info']['generation'][key] = value
        
        # Extract workflow info
        if 'workflow_info' in extractor_metadata:
            workflow_info = extractor_metadata['workflow_info']
            
            # Create workflow_info if not present
            if 'ai_info' not in result:
                result['ai_info'] = {}
            if 'workflow_info' not in result['ai_info']:
                result['ai_info']['workflow_info'] = {}
            
            # Update workflow info
            for key, value in workflow_info.items():
                if value not in (None, "", [], {}):
                    result['ai_info']['workflow_info'][key] = value
        
        # Extract model collections if present
        for collection_name in ['models', 'vae_models', 'loras', 'controlnets', 'upscalers']:
            if collection_name in extractor_metadata:
                collection = extractor_metadata[collection_name]
                if collection:
                    if 'ai_info' not in result:
                        result['ai_info'] = {}
                    result['ai_info'][collection_name] = collection
                    
        # Add workflow statistics if present
        if 'workflow_stats' in extractor_metadata:
            if 'ai_info' not in result:
                result['ai_info'] = {}
            result['ai_info']['workflow_stats'] = extractor_metadata['workflow_stats']
        
        # Add file/workflow history if present
        if 'history' in extractor_metadata:
            if 'ai_info' not in result:
                result['ai_info'] = {}
            result['ai_info']['history'] = extractor_metadata['history']
        
        return result
    
    def _enhance_workflow_extraction(self, workflow_or_prompt_data, result):
        """
        Perform in-depth workflow analysis with node traversal and categorization.
        
        This method performs advanced analysis of workflow nodes and connections, 
        categorizing node types and building a more complete understanding of the workflow.
        
        Args:
            workflow_or_prompt_data: Raw workflow data or prompt data
            result: Result dictionary to enhance (modified in place)
        """
        # Skip if no data
        if not workflow_or_prompt_data:
            return result
            
        # Get nodes from the workflow data
        nodes = None
        if isinstance(workflow_or_prompt_data, dict):
            if 'nodes' in workflow_or_prompt_data:
                nodes = workflow_or_prompt_data['nodes']
            elif 'prompt' in workflow_or_prompt_data and isinstance(workflow_or_prompt_data['prompt'], dict):
                if 'nodes' in workflow_or_prompt_data['prompt']:
                    nodes = workflow_or_prompt_data['prompt']['nodes']
        
        if not nodes:
            return result
            
        # Initialize AI info if not present
        if 'ai_info' not in result:
            result['ai_info'] = {}
            
        # Initialize workflow info if not present
        if 'workflow_info' not in result['ai_info']:
            result['ai_info']['workflow_info'] = {}
        
        # Node type categories
        node_categories = {
            'input': [],
            'processing': [],
            'output': [],
            'model': [],
            'conditioning': [],
            'sampling': [],
            'image': []
        }
        
        # Traverse nodes and categorize
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            node_type = node['class_type']
            
            # Categorize based on node type
            if any(x in node_type for x in ['Load', 'Loader', 'Import']):
                node_categories['input'].append(node_id)
            elif any(x in node_type for x in ['Save', 'Export', 'Output', 'Preview']):
                node_categories['output'].append(node_id)
            elif any(x in node_type for x in ['Checkpoint', 'UNET', 'Model']):
                node_categories['model'].append(node_id)
            elif any(x in node_type for x in ['Conditioning', 'ControlNet', 'IP-Adapter']):
                node_categories['conditioning'].append(node_id)
            elif any(x in node_type for x in ['Sampler', 'KSampler']):
                node_categories['sampling'].append(node_id)
            elif any(x in node_type for x in ['Image', 'LatentImage', 'Resize']):
                node_categories['image'].append(node_id)
            else:
                # Default to processing
                node_categories['processing'].append(node_id)
        
        # Store the categories 
        result['ai_info']['workflow_info']['node_categories'] = {
            category: ids for category, ids in node_categories.items() if ids
        }
        
        # Count nodes by type
        node_type_counts = {}
        for node_id, node in nodes.items():
            if isinstance(node, dict) and 'class_type' in node:
                node_type = node['class_type']
                node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        # Store the node type counts
        if node_type_counts:
            result['ai_info']['workflow_info']['node_type_counts'] = node_type_counts
        
        # Add workflow complexity score
        if 'workflow_stats' in result['ai_info'] and 'complexity' in result['ai_info']['workflow_stats']:
            result['ai_info']['workflow_info']['complexity_score'] = result['ai_info']['workflow_stats']['complexity']
        
        return result

    def _extract_lora_info(self, prompt):
        """
        Extract LoRA information from workflow
        
        Args:
            prompt: ComfyUI prompt data
            
        Returns:
            list: List of LoRA information dictionaries
        """
        loras = []
        
        # Skip if no prompt data
        if not isinstance(prompt, dict):
            return loras
        
        # Get nodes from prompt
        nodes = None
        if 'nodes' in prompt:
            nodes = prompt['nodes']
        elif 'prompt' in prompt and isinstance(prompt['prompt'], dict):
            nodes = prompt['prompt'].get('nodes', {})
            
        if not nodes:
            return loras
            
        # Extract LoRA information from nodes
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            # Check for LoRA nodes - many possible variations
            if 'LoRA' in node['class_type'] or 'Lora' in node['class_type']:
                inputs = node.get('inputs', {})
                
                lora_info = {
                    'node_id': node_id,
                    'type': node['class_type']
                }
                
                # Extract LoRA name
                if 'lora_name' in inputs:
                    lora_info['name'] = inputs['lora_name']
                elif 'name' in inputs:
                    lora_info['name'] = inputs['name']
                    
                # Extract strength parameters
                for param in ['strength', 'strength_model', 'strength_clip', 'model_strength', 'clip_strength']:
                    if param in inputs:
                        lora_info[param] = inputs[param]
                
                # Add to result if we found a name
                if 'name' in lora_info:
                    # Add a display strength (average of model/clip if both exist)
                    if 'strength_model' in lora_info and 'strength_clip' in lora_info:
                        lora_info['strength'] = (float(lora_info['strength_model']) + float(lora_info['strength_clip'])) / 2
                    elif 'strength' not in lora_info:
                        # Default strength
                        lora_info['strength'] = 1.0
                    
                    loras.append(lora_info)
        
        return loras

    def _extract_conditioning_info(self, prompt):
        """
        Extract conditioning information (ControlNet, IP-Adapter, etc.) from the workflow
        
        Args:
            prompt: ComfyUI prompt data
            
        Returns:
            dict: Conditioning information by type
        """
        result = {
            'controlnet': [],
            'ip_adapter': [],
            't2i_adapter': [],
            'other': []
        }
        
        # Skip if no prompt data
        if not isinstance(prompt, dict):
            return result
        
        # Get nodes from prompt
        nodes = None
        if 'nodes' in prompt:
            nodes = prompt['nodes']
        elif 'prompt' in prompt and isinstance(prompt['prompt'], dict):
            nodes = prompt['prompt'].get('nodes', {})
            
        if not nodes:
            return result
        
        # Look for conditioning nodes
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            node_type = node['class_type']
            inputs = node.get('inputs', {})
            
            # Extract ControlNet info
            if 'ControlNet' in node_type:
                controlnet_info = {
                    'node_id': node_id,
                    'type': node_type
                }
                
                # Extract ControlNet name and parameters
                if 'control_net_name' in inputs:
                    controlnet_info['name'] = inputs['control_net_name']
                
                for param in ['strength', 'weight', 'guidance_start', 'guidance_end']:
                    if param in inputs:
                        controlnet_info[param] = inputs[param]
                
                # Try to determine control mode/type
                for key, value in inputs.items():
                    if 'mode' in key or 'type' in key:
                        controlnet_info['control_mode'] = value
                
                result['controlnet'].append(controlnet_info)
                
            # Extract IP-Adapter info
            elif 'IPAdapter' in node_type or 'IP-Adapter' in node_type:
                ip_adapter_info = {
                    'node_id': node_id,
                    'type': node_type
                }
                
                # Extract IP-Adapter parameters
                for param in ['model_name', 'weight', 'strength', 'image', 'noise']:
                    if param in inputs:
                        ip_adapter_info[param] = inputs[param]
                
                result['ip_adapter'].append(ip_adapter_info)
                
            # Extract T2I-Adapter info
            elif 'T2IAdapter' in node_type or 'T2I-Adapter' in node_type:
                t2i_adapter_info = {
                    'node_id': node_id,
                    'type': node_type
                }
                
                # Extract T2I-Adapter parameters
                for param in ['model_name', 'weight', 'strength']:
                    if param in inputs:
                        t2i_adapter_info[param] = inputs[param]
                
                result['t2i_adapter'].append(t2i_adapter_info)
                
            # Check for other conditioning nodes
            elif ('Conditioning' in node_type or 'condition' in node_type.lower()) and 'Combine' not in node_type:
                other_info = {
                    'node_id': node_id,
                    'type': node_type
                }
                
                # Extract common parameters
                for param in ['strength', 'weight']:
                    if param in inputs:
                        other_info[param] = inputs[param]
                
                result['other'].append(other_info)
        
        # Remove empty categories
        return {k: v for k, v in result.items() if v}

    def _extract_workflow_statistics(self, prompt):
        """
        Extract workflow statistics from the prompt.
        
        Args:
            prompt: ComfyUI prompt data
            
        Returns:
            dict: Workflow statistics
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict):
            return {}
        
        # Check if workflow or prompt structure
        nodes = {}
        if 'nodes' in prompt:
            nodes = prompt['nodes']
        elif 'prompt' in prompt and isinstance(prompt['prompt'], dict) and 'nodes' in prompt['prompt']:
            nodes = prompt['prompt'].get('nodes', {})
        else:
            return {}
        
        # Count node types
        node_types = {}
        for node_id, node in nodes.items():
            class_type = node.get('class_type', 'Unknown')
            node_types[class_type] = node_types.get(class_type, 0) + 1 
        
        # Count connections
        connection_count = 0
        if 'links' in prompt:
            connection_count = len(prompt['links'])
        elif 'prompt' in prompt and 'links' in prompt['prompt']:
            connection_count = len(prompt['prompt']['links'])
        
        # Calculate complexity score (simple heuristic)
        complexity = len(nodes) * 2 + connection_count
        
        # Count node categories - higher-level grouping
        categories = {
            'input': 0,
            'output': 0,
            'model': 0,
            'sampler': 0,
            'conditioning': 0,
            'image': 0,
            'processing': 0
        }
        
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            node_type = node.get('class_type', '')
            
            # Categorize based on node type
            if any(x in node_type for x in ['Load', 'Loader', 'Import']):
                categories['input'] += 1
            elif any(x in node_type for x in ['Save', 'Export', 'Output', 'Preview']):
                categories['output'] += 1
            elif any(x in node_type for x in ['Checkpoint', 'UNET', 'Model']):
                categories['model'] += 1
            elif any(x in node_type for x in ['Sampler', 'KSampler']):
                categories['sampler'] += 1
            elif any(x in node_type for x in ['Conditioning', 'ControlNet', 'IP-Adapter']):
                categories['conditioning'] += 1
            elif any(x in node_type for x in ['Image', 'LatentImage', 'Resize']):
                categories['image'] += 1
            else:
                # Default to processing
                categories['processing'] += 1
        
        # Calculate workflow type flags
        has_upscale = any('Upscale' in node.get('class_type', '') for node_id, node in nodes.items() if isinstance(node, dict))
        has_controlnet = any('ControlNet' in node.get('class_type', '') for node_id, node in nodes.items() if isinstance(node, dict))
        has_lora = any('LoRA' in node.get('class_type', '') or 'Lora' in node.get('class_type', '') 
                      for node_id, node in nodes.items() if isinstance(node, dict))
        has_ip_adapter = any('IPAdapter' in node.get('class_type', '') or 'IP-Adapter' in node.get('class_type', '') 
                            for node_id, node in nodes.items() if isinstance(node, dict))
        
        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v > 0}
        
        return {
            'node_count': len(nodes),
            'connection_count': connection_count,
            'node_types': node_types,
            'complexity': complexity,
            'unique_node_types': len(node_types),
            'categories': categories,
            'has_upscale': has_upscale,
            'has_controlnet': has_controlnet,
            'has_lora': has_lora,
            'has_ip_adapter': has_ip_adapter
        }

    def _find_workflow_name(self, prompt, extra_pnginfo):
        """
        Extract workflow name from prompt data or extra_pnginfo
        
        Args:
            prompt: ComfyUI prompt data
            extra_pnginfo: Extra PNG info
            
        Returns:
            str: Extracted workflow name or empty string if not found
        """
        # Try extracting from extra_pnginfo first (often contains more metadata)
        if extra_pnginfo and isinstance(extra_pnginfo, dict):
            # Look for workflow name in extra_pnginfo
            if 'workflow' in extra_pnginfo and isinstance(extra_pnginfo['workflow'], dict):
                if 'name' in extra_pnginfo['workflow']:
                    return extra_pnginfo['workflow']['name']
                # Look in metadata section if present
                if 'metadata' in extra_pnginfo['workflow'] and isinstance(extra_pnginfo['workflow']['metadata'], dict):
                    if 'name' in extra_pnginfo['workflow']['metadata']:
                        return extra_pnginfo['workflow']['metadata']['name']
        
        # If not found, try to extract from prompt
        if isinstance(prompt, dict):
            # Look for metadata section in prompt
            if 'metadata' in prompt and isinstance(prompt['metadata'], dict):
                if 'name' in prompt['metadata']:
                    return prompt['metadata']['name']
            
            # If still not found, try to guess from the workflow structure
            # Look for SaveImage nodes with filename_prefix
            nodes = None
            if 'nodes' in prompt:
                nodes = prompt['nodes']
            elif 'prompt' in prompt and isinstance(prompt['prompt'], dict):
                nodes = prompt['prompt'].get('nodes', {})
                
            if nodes:
                for node_id, node in nodes.items():
                    if not isinstance(node, dict) or 'class_type' not in node:
                        continue
                        
                    # Look for Save nodes with filename information
                    if 'Save' in node['class_type'] and 'inputs' in node:
                        inputs = node['inputs']
                        if 'filename_prefix' in inputs:
                            # Clean up the prefix to create a name
                            prefix = inputs['filename_prefix']
                            # Remove date/time patterns and common prefixes
                            prefix = re.sub(r'[0-9_\-]+$', '', prefix)  # Remove trailing numbers and separators
                            prefix = re.sub(r'^output[_\-]', '', prefix, flags=re.IGNORECASE)  # Remove leading "output_"
                            prefix = prefix.strip()
                            if prefix:
                                return prefix
        
        # If no name found, return empty string
        return ""

    def _extract_upscaler_info(self, prompt):
        """
        Extract information about upscalers from workflow.
        
        Args:
            prompt: ComfyUI prompt data containing nodes
            
        Returns:
            list: List of upscaler information dictionaries
        """
        if not isinstance(prompt, dict) or not prompt:
            return []
        
        upscalers = []
        upscaler_patterns = [
            'Upscale', 'ESRGAN', 'RealESRGAN', 'ScuNET', 'Upscaler', 'UpscaleModel', 'Resample', 'Resize'
        ]
        
        # First check direct prompt structure   
        nodes = prompt.get('nodes', prompt)
        
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node.get('class_type', '')
            
            # Check if this is an upscaler node
            if any(pattern in class_type for pattern in upscaler_patterns):
                # Extract upscaler info
                inputs = node.get('inputs', {})
                upscaler_info = {
                    'type': class_type,
                    'node_id': node_id
                }
                
                # Add relevant parameters
                for param in ['model_name', 'upscale_by', 'scale_factor', 'width', 'height']:
                    if param in inputs:
                        upscaler_info[param] = inputs[param]
                
                upscalers.append(upscaler_info)
        
        return upscalers
    
    def _extract_node_parameters(self, node, node_type, node_id=None):
        """
        Extract parameters from a node based on its type.
        
        Args:
            node: Node data
            node_type: Type of the node
            node_id: Node ID in the workflow (optional)
            
        Returns:
            dict: Node parameters
        """
        # Initialize with basic info
        node_data = {
            'node_type': node_type
        }
        
        # Add node_id if provided
        if node_id is not None:
            node_data['node_id'] = node_id
        
        # Add node title if available
        if 'title' in node:
            node_data['title'] = node['title']
        
        # Handle different node structure formats
        
        # Format 1: Nodes with 'inputs' dictionary (typical for ComfyUI dict structure)
        if 'inputs' in node and isinstance(node['inputs'], dict):    
            # Copy all inputs to node data
            for key, value in node['inputs'].items():
                # Skip complex inputs like connections
                if not isinstance(value, (list, dict)) or isinstance(value, (str, int, float, bool)):
                    node_data[key] = value
        elif 'widgets_values' in node and isinstance(node['widgets_values'], list):
            # Format 2: Nodes with widgets_values list (common in some ComfyUI exports)
            # Try to extract based on widget order
            widget_values = node['widgets_values']
            
            # Handle specific node types
            if 'CLIPTextEncode' in node_type and len(widget_values) > 0:
                node_data['text'] = widget_values[0]
            elif 'KSampler' in node_type and len(widget_values) >= 5:
                params = ['seed', 'steps', 'cfg', 'sampler_name', 'scheduler']
                for i, param in enumerate(params):
                    if i < len(widget_values):
                        node_data[param] = widget_values[i]
        
        # Add meta information if available
        if '_meta' in node:
            node_data['_meta'] = node['_meta']
        
        # Special handling for specific node types
        
        # For UNETLoader, ensure model_name is present
        if 'UNETLoader' in node_type and 'unet_name' in node_data:
            node_data['model_name'] = node_data['unet_name']
        elif 'CheckpointLoader' in node_type and 'ckpt_name' in node_data:
            node_data['model_name'] = node_data['ckpt_name']
        elif 'VAELoader' in node_type and 'vae_name' in node_data:
            node_data['model_name'] = node_data['vae_name']
        elif ('CLIPTextEncode' in node_type or 'Text Multiline' in node_type) and 'text' in node_data:
            # Determine if this is a negative prompt
            is_negative = False
            if 'title' in node and ('negative' in node['title'].lower() or 'neg' in node['title'].lower()):
                is_negative = True
            node_data['is_negative'] = is_negative
        elif 'LoadImage' in node_type and 'image' in node_data:
            # For LoadImage, the image parameter contains the filename
            node_data['filename'] = node_data['image']
        
        return node_data

    def _extract_api_model_info(self, prompt, result):
        """
        Extract API model information from the workflow.
        
        Args:
            prompt: ComfyUI prompt data
            result: Result structure to update
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict) or 'nodes' not in prompt:
            return
        
        # Look for API-related nodes
        api_models = []
        
        for node_id, node in prompt['nodes'].items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node.get('class_type', '')
            
            # Check for API model nodes
            if 'API' in class_type and 'Model' in class_type:
                inputs = node.get('inputs', {})
                api_info = {
                    'node_id': node_id,
                    'type': class_type
                }
                
                # Extract API parameters
                for param in ['api_key', 'model_name', 'endpoint']:
                    if param in inputs:
                        api_info[param] = inputs[param]
                
                api_models.append(api_info)
        
        # Add to result if we found any API models
        if api_models:
            if 'api_models' not in result['ai_info']:
                result['ai_info']['api_models'] = []
            result['ai_info']['api_models'].extend(api_models)

    def _extract_image_dimensions(self, prompt, result):
        """
        Extract image dimensions from the workflow.
        
        Args:
            prompt: ComfyUI prompt data
            result: Result structure to update
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict) or 'nodes' not in prompt:
            return
        
        # Look for nodes that define dimensions
        dimension_nodes = ['EmptyLatentImage', 'VAEDecode', 'VAEEncode', 'LoadImage', 'ImageResize']
        
        # Find the most likely candidate
        best_node = None
        best_priority = -1
        
        # Priority order: EmptyLatentImage > ImageResize > VAEDecode > VAEEncode > LoadImage
        priority_map = {
            'EmptyLatentImage': 4,
            'ImageResize': 3,
            'VAEDecode': 2,
            'VAEEncode': 1,
            'LoadImage': 0
        }
        
        for node_id, node in prompt['nodes'].items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node.get('class_type', '')
            
            # Check if this node defines dimensions
            for dim_node in dimension_nodes:
                if dim_node in class_type:
                    # Check priority
                    priority = priority_map.get(dim_node, -1)
                    if priority > best_priority:
                        best_node = node
                        best_priority = priority
                    break
        
        # Extract dimensions from best node
        if best_node:
            inputs = best_node.get('inputs', {})
            
            width = inputs.get('width', None)
            height = inputs.get('height', None)
            
            if width is not None and height is not None:
                if 'generation' not in result['ai_info']:
                    result['ai_info']['generation'] = {}
                result['ai_info']['generation']['width'] = width
                result['ai_info']['generation']['height'] = height

    def _extract_postprocessing_info(self, prompt, result):
        """
        Extract post-processing information from the workflow.
        
        Args:
            prompt: ComfyUI prompt data
            result: Result structure to update
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict) or 'nodes' not in prompt:
            return
        
        # Look for post-processing nodes
        postprocessing = []
        
        # Define patterns to look for
        upscale_patterns = ['Upscale', 'ESRGAN', 'RealESRGAN', 'ScuNET', 'Upscaler']
        denoise_patterns = ['Denoise', 'Restore', 'FaceRestore', 'GFPGAN', 'CodeFormer']
        sharpen_patterns = ['Sharpen', 'Unsharp', 'DetailEnhance']
        
        for node_id, node in prompt['nodes'].items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node.get('class_type', '')
            
            # Check if this is a post-processing node
            pp_type = None
            if any(pattern in class_type for pattern in upscale_patterns):
                pp_type = 'upscale'
            elif any(pattern in class_type for pattern in denoise_patterns):
                pp_type = 'denoise'
            elif any(pattern in class_type for pattern in sharpen_patterns):
                pp_type = 'sharpen'
                
            if pp_type:
                # Extract node parameters
                inputs = node.get('inputs', {})
                pp_info = {
                    'type': pp_type,
                    'node_type': class_type,
                    'node_id': node_id
                }
                
                # Add parameters based on type
                if pp_type == 'upscale':
                    for param in ['model_name', 'upscale_by', 'scale_factor']:
                        if param in inputs:
                            pp_info[param] = inputs[param]
                elif pp_type == 'denoise':
                    for param in ['strength', 'model_name']:
                        if param in inputs:
                            pp_info[param] = inputs[param]
                
                postprocessing.append(pp_info)
        
        # Add to result if we found any post-processing steps
        if postprocessing:
            if 'postprocessing' not in result['ai_info']:
                result['ai_info']['postprocessing'] = []
            result['ai_info']['postprocessing'].extend(postprocessing)

    def _extract_advanced_sampler_info(self, prompt, result):
        """
        Extract detailed sampler information from advanced sampler nodes.        
        
        Args:
            prompt: ComfyUI prompt data
            result: Result structure to update
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict) or 'nodes' not in prompt:
            return
        
        # Look for advanced sampler nodes
        for node_id, node in prompt['nodes'].items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node.get('class_type', '')
            
            # Check for advanced sampler nodes
            if ('KSampler' in class_type or 'Sampler' in class_type) and 'Advanced' in class_type:
                inputs = node.get('inputs', {})
                
                # Initialize sampler info if not present
                if 'generation' not in result['ai_info']:
                    result['ai_info']['generation'] = {}
                
                # Extract common sampler parameters
                for param in ['sampler_name', 'scheduler', 'steps', 'cfg', 'seed']:
                    if param in inputs:
                        result['ai_info']['generation'][param] = inputs[param]
                
                # Extract advanced parameters
                advanced_params = {}
                
                for param in ['start_at_step', 'end_at_step', 'add_noise', 'return_with_leftover_noise']:
                    if param in inputs:
                        advanced_params[param] = inputs[param]
                
                if advanced_params:
                    if 'advanced_sampler' not in result['ai_info']['generation']:
                        result['ai_info']['generation']['advanced_sampler'] = {}
                    result['ai_info']['generation']['advanced_sampler'].update(advanced_params)

    def _extract_workflow_statistics(self, prompt):
        """
        Extract workflow statistics from the prompt.
        
        Args:
            prompt: ComfyUI prompt data
            
        Returns:
            dict: Workflow statistics
        """
        # Skip if prompt doesn't contain nodes
        if not isinstance(prompt, dict):
            return {}
        
        # Check if workflow or prompt structure
        nodes = {}
        if 'nodes' in prompt:
            nodes = prompt['nodes']
        elif 'prompt' in prompt and isinstance(prompt['prompt'], dict) and 'nodes' in prompt['prompt']:
            nodes = prompt['prompt'].get('nodes', {})
        else:
            return {}
        
        # Count node types
        node_types = {}
        for node_id, node in nodes.items():
            class_type = node.get('class_type', 'Unknown')
            node_types[class_type] = node_types.get(class_type, 0) + 1 
        
        # Count connections
        connection_count = 0
        if 'links' in prompt:
            connection_count = len(prompt['links'])
        elif 'prompt' in prompt and 'links' in prompt['prompt']:
            connection_count = len(prompt['prompt']['links'])
        
        # Calculate complexity score (simple heuristic)
        complexity = len(nodes) * 2 + connection_count
        
        # Count node categories - higher-level grouping
        categories = {
            'input': 0,
            'output': 0,
            'model': 0,
            'sampler': 0,
            'conditioning': 0,
            'image': 0,
            'processing': 0
        }
        
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            node_type = node.get('class_type', '')
            
            # Categorize based on node type
            if any(x in node_type for x in ['Load', 'Loader', 'Import']):
                categories['input'] += 1
            elif any(x in node_type for x in ['Save', 'Export', 'Output', 'Preview']):
                categories['output'] += 1
            elif any(x in node_type for x in ['Checkpoint', 'UNET', 'Model']):
                categories['model'] += 1
            elif any(x in node_type for x in ['Sampler', 'KSampler']):
                categories['sampler'] += 1
            elif any(x in node_type for x in ['Conditioning', 'ControlNet', 'IP-Adapter']):
                categories['conditioning'] += 1
            elif any(x in node_type for x in ['Image', 'LatentImage', 'Resize']):
                categories['image'] += 1
            else:
                # Default to processing
                categories['processing'] += 1
        
        # Calculate workflow type flags
        has_upscale = any('Upscale' in node.get('class_type', '') for node_id, node in nodes.items() if isinstance(node, dict))
        has_controlnet = any('ControlNet' in node.get('class_type', '') for node_id, node in nodes.items() if isinstance(node, dict))
        has_lora = any('LoRA' in node.get('class_type', '') or 'Lora' in node.get('class_type', '') 
                      for node_id, node in nodes.items() if isinstance(node, dict))
        has_ip_adapter = any('IPAdapter' in node.get('class_type', '') or 'IP-Adapter' in node.get('class_type', '') 
                            for node_id, node in nodes.items() if isinstance(node, dict))
        
        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v > 0}
        
        return {
            'node_count': len(nodes),
            'connection_count': connection_count,
            'node_types': node_types,
            'complexity': complexity,
            'unique_node_types': len(node_types),
            'categories': categories,
            'has_upscale': has_upscale,
            'has_controlnet': has_controlnet,
            'has_lora': has_lora,
            'has_ip_adapter': has_ip_adapter
        }

    def _merge_additional_metadata(self, result, additional_metadata):
        """
        Merge additional metadata from extra_pnginfo.
        
        Args:
            result: Result structure to update
            additional_metadata: Additional metadata to merge
        """
        # Handle each section
        for section, section_data in additional_metadata.items():
            # Skip non-dictionary sections
            if not isinstance(section_data, dict):
                continue
            
            # Create section if it doesn't exist
            if section not in result:
                result[section] = {}
            
            # Deep merge to preserve structure
            self._deep_merge(result[section], section_data)
    
    def _deep_merge(self, target, source):
        """
        Recursively merge nested dictionaries.
        
        Args:
            target: Target dictionary to update (modified in place)
            source: Source dictionary with values to merge in
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recurse if both values are dicts
                self._deep_merge(target[key], value)
            else:
                # Otherwise replace/set the value
                target[key] = value
        
    def extract_model_information(self, workflow_data):
        """
        Extract comprehensive model information from workflow.
        
        Identifies all models (checkpoints, LoRAs, VAEs, etc.) and their relationships.
        
        Args:
            workflow_data: Raw workflow data dictionary
            
        Returns:
            dict: Structured model information with categories and relationships
        """
        result = {
            'base_models': [],
            'loras': [],
            'vae_models': [],
            'controlnet_models': [],
            'upscaler_models': [],
            'face_restoration_models': [],
            'relationships': {}
        }
        
        # Skip if no workflow data
        if not workflow_data:
            return result
        
        # Get nodes from workflow structure
        nodes = None
        if 'nodes' in workflow_data:
            nodes = workflow_data['nodes']
        elif 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            nodes = workflow_data['prompt'].get('nodes', {})
                
        if not nodes:
            return result
        
        # Process nodes to extract model information
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Extract models based on node type
            if 'CheckpointLoader' in class_type and 'ckpt_name' in inputs:
                result['base_models'].append({
                    'name': inputs['ckpt_name'],
                    'type': 'checkpoint',
                    'node_id': node_id
                })
            elif 'VAELoader' in class_type and 'vae_name' in inputs:
                result['vae_models'].append({
                    'name': inputs['vae_name'],
                    'type': 'vae',
                    'node_id': node_id
                })
            elif 'LoRA' in class_type and 'lora_name' in inputs:
                lora_info = {
                    'name': inputs['lora_name'],
                    'type': 'lora',
                    'node_id': node_id
                }
                
                # Add strength parameters if available
                if 'strength_model' in inputs:
                    lora_info['strength_model'] = inputs['strength_model']
                if 'strength_clip' in inputs:
                    lora_info['strength_clip'] = inputs['strength_clip']
                    
                result['loras'].append(lora_info)
            elif 'ControlNet' in class_type and 'control_net_name' in inputs:
                result['controlnet_models'].append({
                    'name': inputs['control_net_name'],
                    'type': 'controlnet',
                    'node_id': node_id
                })
            elif any(x in class_type for x in ['Upscale', 'ESRGAN']) and 'model_name' in inputs:
                result['upscaler_models'].append({
                    'name': inputs['model_name'],
                    'type': 'upscaler',
                    'node_id': node_id
                })
            elif any(x in class_type for x in ['FaceRestore', 'GFPGAN', 'CodeFormer']) and 'model_name' in inputs:
                result['face_restoration_models'].append({
                    'name': inputs['model_name'],
                    'type': 'face_restoration',
                    'node_id': node_id
                })
        
        # Build relationships between models (which connects to what)
        # This would require analyzing the connections in the workflow
        # Left as a placeholder for future implementation
            
        return result
    
    def extract_prompt_information(self, workflow_data):
        """
        Extract and analyze prompt information from workflow.
        
        Args:
            workflow_data: Raw workflow data dictionary
            
        Returns:
            dict: Structured prompt information with analysis
        """
        result = {
            'positive_prompts': [],
            'negative_prompts': [],
            'combined_positive': '',
            'combined_negative': '',
            'primary_concepts': [],
            'prompt_structure': {}
        }
        
        # Skip if no workflow data
        if not workflow_data:
            return result
        
        # Get nodes from workflow structure
        nodes = None
        if 'nodes' in workflow_data:
            nodes = workflow_data['nodes']
        elif 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            nodes = workflow_data['prompt'].get('nodes', {})
                
        if not nodes:
            return result
        
        # Process nodes to extract prompt information
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Look for text encoding nodes
            if 'CLIPTextEncode' in class_type and 'text' in inputs:
                text = inputs['text']
                
                # Determine if positive or negative prompt
                is_negative = False
                title = node.get('title', '').lower()
                if 'negative' in title or 'neg' in title:
                    is_negative = True
                
                if is_negative:
                    result['negative_prompts'].append(text)
                else:
                    result['positive_prompts'].append(text)
        
        # Combine prompts
        if result['positive_prompts']:
            result['combined_positive'] = ' '.join(result['positive_prompts'])
        if result['negative_prompts']:
            result['combined_negative'] = ' '.join(result['negative_prompts'])
        
        # Analyze prompt structure (keywords, weights, etc.)
        if result['combined_positive']:
            # Simple keyword extraction
            words = result['combined_positive'].lower().split()
            # Remove common words, punctuation, etc.
            keywords = [word for word in words if len(word) > 3 and word.isalpha()]
            # Count frequency
            keyword_counts = {}
            for keyword in keywords:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            # Find primary concepts (most frequent keywords)
            primary_concepts = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            result['primary_concepts'] = [concept[0] for concept in primary_concepts]
            
            # Extract any weights in prompts using regexp
            weight_pattern = r'\(([^:]+):([0-9.]+)\)'
            weights = re.findall(weight_pattern, result['combined_positive'])
            if weights:
                result['prompt_structure']['weights'] = [
                    {'text': text, 'weight': float(weight)}
                    for text, weight in weights
                ]
        
        return result
    
    def extract_technical_parameters(self, workflow_data):
        """
        Extract technical parameters like seeds, samplers, steps, etc.
        
        Args:
            workflow_data: Raw workflow data dictionary
            
        Returns:
            dict: Structured technical parameters
        """
        result = {
            'sampler_nodes': [],
            'primary_sampler': None,
            'seeds': [],
            'steps': [],
            'cfg_values': [],
            'dimensions': None,
            'batch_size': 1
        }
        
        # Skip if no workflow data
        if not workflow_data:
            return result
        
        # Get nodes from workflow structure
        nodes = None
        if 'nodes' in workflow_data:
            nodes = workflow_data['nodes']
        elif 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            nodes = workflow_data['prompt'].get('nodes', {})
                
        if not nodes:
            return result
        
        # Process nodes to extract technical parameters
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
                
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Extract sampler information
            if 'KSampler' in class_type or 'Sampler' in class_type:
                sampler_info = {
                    'node_id': node_id,
                    'class_type': class_type
                }
                
                # Extract common sampler parameters
                for param in ['sampler_name', 'scheduler', 'steps', 'cfg', 'seed', 
                             'denoise', 'noise_seed']:
                    if param in inputs:
                        sampler_info[param] = inputs[param]
                
                # Add to sampler nodes
                result['sampler_nodes'].append(sampler_info)
                
                # Add to specific parameter lists
                if 'seed' in inputs:
                    result['seeds'].append(inputs['seed'])
                if 'steps' in inputs:
                    result['steps'].append(inputs['steps'])
                if 'cfg' in inputs:
                    result['cfg_values'].append(inputs['cfg'])
            
            # Extract dimensions
            elif 'EmptyLatentImage' in class_type:
                if 'width' in inputs and 'height' in inputs:
                    result['dimensions'] = {
                        'width': inputs['width'],
                        'height': inputs['height']
                    }
            
            # Extract batch size
            if 'batch_size' in inputs:
                result['batch_size'] = inputs['batch_size']
        
        # Set primary sampler (most connected one or first one)    
        if result['sampler_nodes']:
            # For now, just use the first one
            result['primary_sampler'] = result['sampler_nodes'][0]
        
        return result
    
    def create_search_optimized_metadata(self, metadata):
        """
        Create flattened, search-optimized metadata fields.
        
        Args:
            metadata: Full metadata structure
            
        Returns:
            dict: Flattened metadata for search optimization
        """
        search_metadata = {}
        
        # Skip if no metadata
        if not metadata:
            return search_metadata
        
        # Extract AI generation parameters
        if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
            generation = metadata['ai_info']['generation']
            
            # Extract model
            if 'model' in generation:
                search_metadata['ai:model'] = generation['model']
            
            # Extract prompt (truncated for search)
            if 'prompt' in generation:
                # Truncated version for search - first 25 words
                words = generation['prompt'].split()
                search_metadata['ai:prompt'] = " ".join(words[:25])
            
            # Extract negative prompt
            if 'negative_prompt' in generation:
                # Truncated version for search
                words = generation['negative_prompt'].split()
                search_metadata['ai:negative_prompt'] = " ".join(words[:15])
            
            # Extract technical parameters
            for param_name, xmp_name in [
                ('seed', 'ai:seed'),
                ('steps', 'ai:steps'),
                ('cfg_scale', 'ai:cfg'),
                ('sampler', 'ai:sampler'),
                ('scheduler', 'ai:scheduler'),
                ('vae', 'ai:vae')
            ]:
                if param_name in generation:
                    search_metadata[xmp_name] = generation[param_name]
        
        # Extract LoRA information
        if 'ai_info' in metadata and 'loras' in metadata['ai_info']:
            loras = metadata['ai_info']['loras']
            if loras:
                lora_names = []
                for lora in loras:
                    if isinstance(lora, dict) and 'name' in lora:
                        lora_names.append(lora['name'])
                    else:
                        lora_names.append(str(lora))
                
                if lora_names:
                    search_metadata['ai:loras'] = ", ".join(lora_names)
        
        # Extract workflow name
        if 'ai_info' in metadata and 'workflow_info' in metadata['ai_info']:
            workflow_info = metadata['ai_info']['workflow_info']
            if 'name' in workflow_info:
                search_metadata['ai:workflow'] = workflow_info['name']
        
        return search_metadata
    
    def format_metadata_for_output(self, metadata, format_type='text'):
        """
        Format metadata for display in various formats.
        
        Args:
            metadata: Metadata dictionary to format
            format_type: Output format ('text', 'html', or 'markdown')
            
        Returns:
            str: Formatted metadata as string
        """
        if format_type.lower() == 'text':
            return self._format_metadata_as_text(metadata)
        elif format_type.lower() == 'html':
            return self._format_metadata_as_html(metadata)
        elif format_type.lower() == 'markdown':
            return self._format_metadata_as_markdown(metadata)
        else:
            return f"Unsupported format type: {format_type}"
    
    def _format_metadata_as_text(self, metadata):
        """
        Format metadata as plain text for display.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            str: Text representation of metadata
        """
        try:
            if not isinstance(metadata, dict):
                return "Error: Invalid metadata format (not a dictionary)"
                
            lines = ["=== Workflow Metadata ===", ""]
            
            # Basic information
            if 'basic' in metadata and metadata['basic']:
                lines.append("=== Basic Information ===")
                for key, value in metadata['basic'].items():
                    lines.append(f"{key}: {value}")
                lines.append("")
            
            # AI generation information
            if 'ai_info' in metadata:
                ai_info = metadata['ai_info']
                
                lines.append("=== AI Generation Information ===")
                
                # Generation parameters
                if 'generation' in ai_info:
                    lines.append("\n-- Generation Parameters --")
                    for key, value in ai_info['generation'].items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"{key}: {self._format_complex_value(value)}")
                        else:
                            lines.append(f"{key}: {value}")
                
                # Model information
                if 'models' in ai_info:
                    lines.append("\n-- Models --")
                    for model in ai_info['models']:
                        if isinstance(model, dict):
                            lines.append(f"- {model.get('name', 'Unknown')}")
                        else:
                            lines.append(f"- {model}")
                
                # LoRA information
                if 'loras' in ai_info:
                    lines.append("\n-- LoRAs --")
                    for lora in ai_info['loras']:
                        if isinstance(lora, dict):
                            name = lora.get('name', 'Unknown')
                            strength = lora.get('strength', 1.0)
                            lines.append(f"- {name} (Strength: {strength})")
                        else:
                            lines.append(f"- {lora}")
                
                # Workflow information
                if 'workflow_info' in ai_info:
                    lines.append("\n-- Workflow Information --")
                    for key, value in ai_info['workflow_info'].items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"{key}: {self._format_complex_value(value)}")
                        else:
                            lines.append(f"{key}: {value}")
                
                # Workflow statistics
                if 'workflow_stats' in ai_info:
                    lines.append("\n-- Workflow Statistics --")
                    stats = ai_info['workflow_stats']
                    for key, value in stats.items():
                        if key == 'node_types' and isinstance(value, dict):
                            lines.append("Node Types:")
                            for node_type, count in value.items():
                                lines.append(f"  - {node_type}: {count}")
                        else:
                            lines.append(f"{key}: {value}")
            
            # Analysis information
            if 'analysis' in metadata and metadata['analysis']:
                lines.append("\n=== Analysis Information ===")
                for analysis_type, analysis_data in metadata['analysis'].items():
                    lines.append(f"\n-- {analysis_type} --")
                    if isinstance(analysis_data, dict):
                        for key, value in analysis_data.items():
                            if isinstance(value, (dict, list)):
                                lines.append(f"{key}: {self._format_complex_value(value)}")
                            else:
                                lines.append(f"{key}: {value}")
                    else:
                        lines.append(str(analysis_data))
            
            # Search optimized metadata
            if 'search_optimized' in metadata and metadata['search_optimized']:
                lines.append("\n=== Search Optimized Fields ===")
                for key, value in metadata['search_optimized'].items():
                    lines.append(f"{key}: {value}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error formatting metadata as text: {str(e)}"
    
    def _format_metadata_as_html(self, metadata):
        """
        Format metadata as HTML for display.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            str: HTML representation of metadata
        """
        try:
            if not isinstance(metadata, dict):
                return "<p>Error: Invalid metadata format (not a dictionary)</p>"
                
            html = ['<!DOCTYPE html>',
                    '<html>',
                    '<head>',
                    '<title>Workflow Metadata</title>',
                    '<style>',
                    'body { font-family: Arial, sans-serif; margin: 20px; }',
                    'h1 { color: #333366; }',
                    'h2 { color: #333366; margin-top: 20px; }',
                    'h3 { color: #333366; margin-top: 15px; }',
                    '.section { margin-bottom: 20px; }',
                    'table { border-collapse: collapse; width: 100%; }',
                    'th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }',
                    'th { background-color: #f2f2f2; }',
                    '.key { font-weight: bold; width: 30%; }',
                    'pre { background-color: #f8f8f8; padding: 10px; border-radius: 4px; overflow: auto; }',
                    '</style>',
                    '</head>',
                    '<body>',
                    '<h1>Workflow Metadata</h1>']
            
            # Basic information
            if 'basic' in metadata and metadata['basic']:
                html.append('<div class="section">')
                html.append('<h2>Basic Information</h2>')
                html.append('<table>')
                for key, value in metadata['basic'].items():
                    html.append(f'<tr><td class="key">{key}</td><td>{value}</td></tr>')
                html.append('</table>')
                html.append('</div>')
            
            # AI generation information
            if 'ai_info' in metadata:
                ai_info = metadata['ai_info']
                
                html.append('<div class="section">')
                html.append('<h2>AI Generation Information</h2>')
                
                # Generation parameters
                if 'generation' in ai_info:
                    html.append('<h3>Generation Parameters</h3>')
                    html.append('<table>')
                    for key, value in ai_info['generation'].items():
                        html_value = value
                        if isinstance(value, (dict, list)):
                            html_value = f'<pre>{self._format_complex_value(value)}</pre>'
                        html.append(f'<tr><td class="key">{key}</td><td>{html_value}</td></tr>')
                    html.append('</table>')
                
                # Model information
                if 'models' in ai_info:
                    html.append('<h3>Models</h3>')
                    html.append('<ul>')
                    for model in ai_info['models']:
                        if isinstance(model, dict):
                            html.append(f'<li>{model.get("name", "Unknown")}</li>')
                        else:
                            html.append(f'<li>{model}</li>')
                    html.append('</ul>')
                
                # LoRA information
                if 'loras' in ai_info:
                    html.append('<h3>LoRAs</h3>')
                    html.append('<ul>')
                    for lora in ai_info['loras']:
                        if isinstance(lora, dict):
                            name = lora.get('name', 'Unknown')
                            strength = lora.get('strength', 1.0)
                            html.append(f'<li><strong>{name}</strong> (Strength: {strength})</li>')
                        else:
                            html.append(f'<li>{lora}</li>')
                    html.append('</ul>')
                
                # Workflow information
                if 'workflow_info' in ai_info:
                    html.append('<h3>Workflow Information</h3>')
                    html.append('<table>')
                    for key, value in ai_info['workflow_info'].items():
                        html_value = value
                        if isinstance(value, (dict, list)):
                            html_value = f'<pre>{self._format_complex_value(value)}</pre>'
                        html.append(f'<tr><td class="key">{key}</td><td>{html_value}</td></tr>')
                    html.append('</table>')
                
                # Workflow statistics
                if 'workflow_stats' in ai_info:
                    html.append('<h3>Workflow Statistics</h3>')
                    stats = ai_info['workflow_stats']
                    html.append('<table>')
                    for key, value in stats.items():
                        if key == 'node_types' and isinstance(value, dict):
                            html.append(f'<tr><td class="key">{key}</td><td>')
                            html.append('<table>')
                            for node_type, count in value.items():
                                html.append(f'<tr><td>{node_type}</td><td>{count}</td></tr>')
                            html.append('</table>')
                            html.append('</td></tr>')
                        else:
                            html.append(f'<tr><td class="key">{key}</td><td>{value}</td></tr>')
                    html.append('</table>')
                
                html.append('</div>')
            
            # Analysis information
            if 'analysis' in metadata and metadata['analysis']:
                html.append('<div class="section">')
                html.append('<h2>Analysis Information</h2>')
                
                for analysis_type, analysis_data in metadata['analysis'].items():
                    html.append(f'<h3>{analysis_type}</h3>')
                    if isinstance(analysis_data, dict):
                        html.append('<table>')
                        for key, value in analysis_data.items():
                            html_value = value
                            if isinstance(value, (dict, list)):
                                html_value = f'<pre>{self._format_complex_value(value)}</pre>'
                            html.append(f'<tr><td class="key">{key}</td><td>{html_value}</td></tr>')
                        html.append('</table>')
                    else:
                        html.append(f'<p>{analysis_data}</p>')
                
                html.append('</div>')
            
            # Search optimized metadata
            if 'search_optimized' in metadata and metadata['search_optimized']:
                html.append('<div class="section">')
                html.append('<h2>Search Optimized Fields</h2>')
                html.append('<table>')
                for key, value in metadata['search_optimized'].items():
                    html.append(f'<tr><td class="key">{key}</td><td>{value}</td></tr>')
                html.append('</table>')
                html.append('</div>')
            
            html.append('</body></html>')
            return '\n'.join(html)
        except Exception as e:
            return f"<p>Error formatting metadata as HTML: {str(e)}</p>"

    def _format_metadata_as_markdown(self, metadata):
        """
        Format metadata as Markdown for display.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            str: Markdown representation of metadata
        """
        try:
            if not isinstance(metadata, dict):
                return "Error: Invalid metadata format (not a dictionary)"
                
            lines = ["# Workflow Metadata Analysis", ""]
            
            # Basic information
            if 'basic' in metadata and metadata['basic']:
                lines.append("## Basic Information")
                for key, value in metadata['basic'].items():
                    lines.append(f"**{key}:** {value}")
                lines.append("")
            
            # AI generation information
            if 'ai_info' in metadata:
                ai_info = metadata['ai_info']
                
                lines.append("## AI Generation Information")
                
                # Generation parameters
                if 'generation' in ai_info:
                    lines.append("\n### Generation Parameters")
                    for key, value in ai_info['generation'].items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"**{key}:**\n```\n{self._format_complex_value(value)}\n```")
                        else:
                            lines.append(f"**{key}:** {value}")
                
                # Model information
                if 'models' in ai_info:
                    lines.append("\n### Models")
                    for model in ai_info['models']:
                        if isinstance(model, dict):
                            lines.append(f"- {model.get('name', 'Unknown')}")
                        else:
                            lines.append(f"- {model}")
                
                # LoRA information
                if 'loras' in ai_info:
                    lines.append("\n### LoRAs")
                    for lora in ai_info['loras']:
                        if isinstance(lora, dict):
                            name = lora.get('name', 'Unknown')
                            strength = lora.get('strength', 1.0)
                            lines.append(f"- **{name}** (Strength: {strength})")
                        else:
                            lines.append(f"- {lora}")
                
                # Workflow information
                if 'workflow_info' in ai_info:
                    lines.append("\n### Workflow Information")
                    for key, value in ai_info['workflow_info'].items():
                        if isinstance(value, (dict, list)):
                            lines.append(f"**{key}:**\n```\n{self._format_complex_value(value)}\n```")
                        else:
                            lines.append(f"**{key}:** {value}")
                
                # Workflow statistics
                if 'workflow_stats' in ai_info:
                    lines.append("\n### Workflow Statistics")
                    stats = ai_info['workflow_stats']
                    for key, value in stats.items():
                        if key == 'node_types' and isinstance(value, dict):
                            lines.append(f"**{key}:**")
                            for node_type, count in value.items():
                                lines.append(f"  - {node_type}: {count}")
                        else:
                            lines.append(f"**{key}:** {value}")
            
            # Analysis information
            if 'analysis' in metadata and metadata['analysis']:
                lines.append("\n## Analysis Information")
                for analysis_type, analysis_data in metadata['analysis'].items():
                    lines.append(f"\n### {analysis_type}")
                    if isinstance(analysis_data, dict):
                        for key, value in analysis_data.items():
                            if isinstance(value, (dict, list)):
                                lines.append(f"**{key}:**\n```\n{self._format_complex_value(value)}\n```")
                            else:
                                lines.append(f"**{key}:** {value}")
                    else:
                        lines.append(str(analysis_data))
            
            # Search optimized metadata
            if 'search_optimized' in metadata and metadata['search_optimized']:
                lines.append("\n## Search Optimized Fields")
                for key, value in metadata['search_optimized'].items():
                    lines.append(f"**{key}:** {value}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error formatting metadata as markdown: {str(e)}"
    
    def _format_complex_value(self, value):
        """
        Format complex values (dicts, lists) for display
        
        Args:
            value: Value to format
            
        Returns:
            str: Formatted representation
        """
        import json
        
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value, indent=2)
            else:
                return str(value)
        except:
            return str(value)