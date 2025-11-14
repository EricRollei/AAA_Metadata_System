"""
workflow_parser.py - Enhanced Workflow Parser for ComfyUI and A1111
Description: Extracts detailed metadata from ComfyUI workflows by deeply analyzing node structures
    and connections to identify generation parameters regardless of their location.
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

Enhanced Workflow Parser - March 2025

Extracts detailed metadata from ComfyUI workflows by deeply analyzing node structures
and connections to identify generation parameters regardless of their location.
"""

import json
import os
import re
import time
from typing import Dict, List, Any, Optional, Tuple, Set

class WorkflowParser:
    """Enhanced parser for extracting detailed metadata from workflows"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.unknown_node_types = set()
        
        # Update parameter mappings to use direct parameter names
        self.parameter_mappings = {
            # Samplers
            'KSampler': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler',
                'steps': 'steps',
                'cfg_scale': 'cfg',
                'seed': 'seed',
                'denoise': 'denoise'
            },
            'SamplerCustom': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler',
                'steps': 'steps',
                'cfg_scale': 'cfg',
                'seed': 'seed'
            },
            'KSamplerAdvanced': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler',
                'steps': 'steps',
                'cfg_scale': 'cfg',
                'seed': 'seed',
                'denoise': 'denoise'
            },
            'SamplerCustom': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler',
                'steps': 'steps',
                'cfg_scale': 'cfg',
                'seed': 'seed'
            },

            # Models and checkpoints
            'CheckpointLoaderSimple': {
                'model': 'ckpt_name'
            },
            'CheckpointLoader': {
                'model': 'ckpt_name'
            },
            'DiffusersLoader': {
                'model': 'model_path'
            },
            
            # VAE
            'VAELoader': {
                'vae': 'vae_name'
            },
            'VAEDecodeTiled': {
                'vae': 'vae'
            },
            
            # LoRAs
            'LoraLoader': {
                'lora_name': 'lora_name',
                'strength_model': 'strength_model',
                'strength_clip': 'strength_clip'
            },
            
            # Text prompts
            'CLIPTextEncode': {
                'prompt': 'text',
                'clip': 'clip',
                'is_negative': 'is_negative'
            },
            
            # Latent dimensions
            'EmptyLatentImage': {
                'width': 'width',
                'height': 'height',
                'batch_size': 'batch_size'
            },
            
            # Control nets
            'ControlNetLoader': {
                'controlnet_model': 'control_net_name'
            },
            'ControlNetApply': {
                'controlnet_weight': 'strength'
            },
            
            # IP Adapters
            'IPAdapterModelLoader': {
                'ip_adapter_model': 'ipadapter_file'
            },
            
            # Style models
            'StyleModelLoader': {
                'style_model': 'style_model_name'
            },
            
            # Upscalers
            'UpscaleModelLoader': {
                'upscale_model': 'model_name'
            },
            
            # UNET models
            'UNETLoader': {
                'unet_model': 'unet_name'
            },
            
            # Flux settings
            'ModelSamplingFlux': {
                'flux_fraction': 'flux_frac',
                'flux_mode': 'flux_mode'
            }
        }
        
        # Also check common input field names regardless of node type
        self.common_input_fields = {
            'model': ['model', 'checkpoint', 'ckpt_name', 'ckpt', 'model_name'],
            'prompt': ['prompt', 'text', 'positive', 'positive_prompt'],
            'negative_prompt': ['negative', 'negative_prompt', 'neg', 'neg_prompt'],
            'seed': ['seed', 'noise_seed'],
            'steps': ['steps', 'max_steps', 'sampling_steps'],
            'cfg_scale': ['cfg', 'cfg_scale', 'guidance_scale', 'scale'],
            'sampler': ['sampler', 'sampler_name'],
            'scheduler': ['scheduler', 'scheduler_name'],
            'width': ['width', 'w', 'image_width'],
            'height': ['height', 'h', 'image_height']
        }
        
        # Create reverse mapping to identify field purpose from name
        self.field_purpose_mapping = {}
        for purpose, field_names in self.common_input_fields.items():
            for field_name in field_names:
                self.field_purpose_mapping[field_name] = purpose
        
    def extract_and_analyze(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract meaningful metadata from workflow data
        
        Args:
            workflow_data: Raw workflow data
            
        Returns:
            dict: Extracted and analyzed metadata
        """
        if not workflow_data:
            return {}
            
        # Initialize result with standard structure
        result = {
            'workflow_type': self._detect_workflow_type(workflow_data),
            'raw_nodes': {},
            'prompts': {'positive': [], 'negative': []},
            'connections': [],
            'generation_parameters': {}
        }
        
        try:
            # Extract ComfyUI workflow data
            if result['workflow_type'] == 'comfyui':
                # Get nodes and connections
                prompt_data = workflow_data.get('prompt', {})
                if not prompt_data and isinstance(workflow_data, dict) and 'nodes' in workflow_data:
                    # Direct nodes structure
                    prompt_data = workflow_data
                
                nodes = prompt_data.get('nodes', {})
                links = prompt_data.get('links', [])
                if not links and 'connections' in prompt_data:
                    links = prompt_data.get('connections', [])
                
                result['raw_nodes'] = nodes
                
                # Identify output nodes (save image, preview, etc.)
                output_nodes = self._identify_output_nodes(nodes)
                
                # Get node execution order by tracing backward from outputs
                node_order = self._calculate_node_execution_order(nodes, links, output_nodes)
                result['node_order'] = node_order
                
                # Extract detailed parameter information from nodes
                self._extract_detailed_parameters(nodes, result)
                
                # Parse prompt information with connection analysis
                self._extract_detailed_prompts(nodes, links, result)
                
                # Add image dimension information
                latent_dimensions = self._extract_latent_dimensions(nodes)
                if latent_dimensions:
                    result['dimensions'] = latent_dimensions
            
            # Extract parameters for other workflow types (A1111, etc.)
            elif result['workflow_type'] == 'automatic1111':
                # Direct mapping of common fields for A1111 format
                for field in ['prompt', 'negative_prompt', 'sampler', 'steps', 'cfg_scale', 'seed']:
                    if field in workflow_data:
                        if field in ['prompt', 'negative_prompt']:
                            # Store in prompts structure
                            key = 'positive' if field == 'prompt' else 'negative'
                            result['prompts'][key] = [workflow_data[field]]
                        else:
                            # Store in generation parameters
                            result['generation_parameters'][field] = workflow_data[field]
                
                # Map model information
                if 'model' in workflow_data:
                    result['generation_parameters']['model'] = workflow_data['model']
                elif 'checkpoint' in workflow_data:
                    result['generation_parameters']['model'] = workflow_data['checkpoint']
        
        except Exception as e:
            if self.debug:
                print(f"[WorkflowParser] Error extracting workflow details: {str(e)}")
        
        return result
    
    def _detect_workflow_type(self, data: Dict[str, Any]) -> str:
        """Detect the type of workflow"""
        if not data:
            return "unknown"
            
        # Check for explicit type
        if 'type' in data:
            workflow_type = data['type'].lower()
            if 'comfy' in workflow_type:
                return 'comfyui'
            elif 'automatic' in workflow_type or 'webui' in workflow_type:
                return 'automatic1111'
            return workflow_type
        
        # Check for ComfyUI structure
        if 'prompt' in data and isinstance(data['prompt'], dict):
            if 'nodes' in data['prompt']:
                return 'comfyui'
        
        # Check for direct nodes structure
        if 'nodes' in data and isinstance(data['nodes'], dict):
            return 'comfyui'
            
        # Check for A1111 structure
        if all(k in data for k in ['prompt', 'negative_prompt']):
            return 'automatic1111'
            
        # Check for NovelAI keywords
        if 'novelai' in str(data).lower() or 'nai' in str(data).lower():
            return 'novelai'
            
        return 'unknown'
    
    def _identify_output_nodes(self, nodes: Dict[str, Any]) -> List[str]:
        """Identify output nodes like SaveImage, PreviewImage, etc."""
        output_nodes = []
        output_node_types = [
            'SaveImage', 'PreviewImage', 'SaveImageWithMetadata', 
            'MetadataAwareSaveImage', 'ImageOutput'
        ]
        
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            # Check if this is an output node
            if any(output_type in node_type for output_type in output_node_types):
                output_nodes.append(node_id)
            # Also check for title hints
            elif '_meta' in node and 'title' in node['_meta']:
                title = node['_meta']['title']
                if any(output_word in title for output_word in ['Save', 'Output', 'Preview']):
                    output_nodes.append(node_id)
        
        return output_nodes
    
    def _calculate_node_execution_order(self, nodes: Dict[str, Any], 
                                       links: List[Any], 
                                       output_nodes: List[str]) -> List[str]:
        """Calculate node execution order by tracing backward from outputs"""
        if not output_nodes:
            return []
            
        # Build a reverse lookup of connections (what feeds into each node)
        connections = {}
        for link in links:
            # Format: [id, from_node, from_slot, to_node, to_slot, type]
            if len(link) >= 4:
                to_node = link[3]
                from_node = link[1]
                
                if to_node not in connections:
                    connections[to_node] = []
                connections[to_node].append(from_node)
        
        # Trace backward from output nodes
        visited = set()
        node_order = []
        
        def visit_node(node_id):
            if node_id in visited:
                return
            
            visited.add(node_id)
            
            # Visit inputs first (recursive DFS)
            if node_id in connections:
                for input_node in connections[node_id]:
                    visit_node(input_node)
            
            # Add this node to the order
            node_order.append(node_id)
        
        # Process all output nodes
        for output_node in output_nodes:
            visit_node(output_node)
        
        return node_order

    def _build_connection_map(self, links: List[Any]) -> Dict[Tuple[str, int], Tuple[str, int]]:
        """
        Build a map of connections for resolving linked values
        
        Args:
            links: Workflow links
            
        Returns:
            dict: Map from (to_node, to_slot) to (from_node, from_slot)
        """
        connection_map = {}
        
        for link in links:
            # ComfyUI link format varies, handle different possibilities
            
            # Format: [id, from_node, from_slot, to_node, to_slot]
            if len(link) >= 5:
                from_node = link[1]
                from_slot = link[2]
                to_node = link[3]
                to_slot = link[4]
                connection_map[(to_node, to_slot)] = (from_node, from_slot)
                
            # Format: [from_node, from_slot, to_node, to_slot]
            elif len(link) >= 4:
                from_node = link[0]
                from_slot = link[1]
                to_node = link[2]
                to_slot = link[3]
                connection_map[(to_node, to_slot)] = (from_node, from_slot)
        
        return connection_map

    def _resolve_linked_value(self, link_ref: List[Any], nodes: Dict[str, Any], connection_map: Dict[Tuple[str, int], Tuple[str, int]]) -> Any:
        """
        Resolve a linked value by tracing through the workflow graph
        
        Args:
            link_ref: Link reference [node_id, slot]
            nodes: All nodes in the workflow
            connection_map: Map of connections
            
        Returns:
            any: The resolved value
        """
        # Handle direct values (not references)
        if not isinstance(link_ref, list) or len(link_ref) != 2:
            return link_ref
            
        from_node_id, from_slot = link_ref
        
        # Get the source node
        if from_node_id not in nodes:
            if self.debug:
                print(f"[WorkflowParser] Source node not found: {from_node_id}")
            return f"Unknown node: {from_node_id}"
            
        source_node = nodes[from_node_id]
        class_type = source_node.get('class_type', '')
        
        # For nodes that directly output values
        if class_type in ['CheckpointLoader', 'CheckpointLoaderSimple']:
            if 'ckpt_name' in source_node.get('inputs', {}):
                return source_node['inputs']['ckpt_name']
                
        elif class_type == 'VAELoader':
            if 'vae_name' in source_node.get('inputs', {}):
                return source_node['inputs']['vae_name']
        
        # For primitive/value nodes
        elif class_type in ['PrimitiveNode', 'IntegerNode', 'FloatNode', 'StringNode']:
            if 'value' in source_node.get('inputs', {}):
                return source_node['inputs']['value']
            elif 'string' in source_node.get('inputs', {}):  # For string nodes
                return source_node['inputs']['string']
        
        # For combo/dropdown nodes with fixed options
        elif class_type in ['SamplerNode', 'SchedulerNode', 'ModelSelect']:
            for field in ['value', 'selected', 'option', 'sampler_name', 'scheduler_name', 'ckpt_name']:
                if field in source_node.get('inputs', {}):
                    return source_node['inputs'][field]
        
        # For specific node types we know
        elif class_type == 'KSamplerSelect':
            if 'sampler_name' in source_node.get('inputs', {}):
                return source_node['inputs']['sampler_name']
        
        elif class_type == 'CLIPTextEncode':
            if 'text' in source_node.get('inputs', {}):
                return source_node['inputs']['text']
                
        # Look for output values
        outputs = source_node.get('outputs', {})
        if isinstance(outputs, dict) and str(from_slot) in outputs:
            return outputs[str(from_slot)].get('value')
                
        # Return node class type if we can't resolve the value
        return f"{class_type}"

    def _extract_detailed_parameters(self, nodes: Dict[str, Any], links: List[Any], result: Dict[str, Any]) -> None:
        """
        Extract detailed parameters from nodes based on node type.
        
        Args:
            nodes: Workflow nodes
            links: Workflow links
            result: Result dictionary to update
        """
        # Create a connection map for reference resolution
        connection_map = self._build_connection_map(links)
        
        # Initialize structured parameter storage
        generation_params = {}
        model_info = {}
        vae_info = None
        loras = []
        control_nets = []
        ip_adapters = []
        upscalers = []
        unet_models = []
        
        # Process each node by type
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Skip if node type not in our mappings
            if node_type not in self.parameter_mappings:
                if node_type and self.debug:
                    self.unknown_node_types.add(node_type)
                continue
            
            # Extract parameters based on mappings
            mapping = self.parameter_mappings[node_type]
            extracted_values = {}
            
            for target_field, input_field in mapping.items():
                # Check if the parameter exists in inputs
                if input_field in inputs:
                    value = inputs[input_field]
                    
                    # Resolve linked values if needed
                    if isinstance(value, list) and len(value) == 2:
                        resolved_value = self._resolve_linked_value(value, nodes, connection_map)
                        value = resolved_value
                    
                    # Store the extracted value
                    extracted_values[target_field] = value
            
            # Skip if we didn't extract any values
            if not extracted_values:
                continue
                
            # Categorize based on node type (rest of the method continues as before)
            if node_type in ['CheckpointLoader', 'CheckpointLoaderSimple', 'DiffusersLoader']:
                if 'model' in extracted_values:
                    model_info = {
                        'name': extracted_values['model'],
                        'type': node_type
                    }
                    # Save to generation parameters
                    generation_params['model'] = extracted_values['model']
            
            elif node_type in ['VAELoader', 'VAEDecodeTiled']:
                if 'vae' in extracted_values:
                    vae_info = extracted_values['vae']
                    # Save to generation parameters
                    generation_params['vae'] = vae_info
            
            elif node_type == 'LoraLoader':
                lora_info = {
                    'name': extracted_values.get('lora_name', 'unknown'),
                    'strength_model': extracted_values.get('strength_model', 1.0),
                    'strength_clip': extracted_values.get('strength_clip', 1.0)
                }
                loras.append(lora_info)
            
            elif node_type in ['KSampler', 'KSamplerAdvanced', 'SamplerCustom']:
                # Add all sampler parameters to generation parameters
                for field, value in extracted_values.items():
                    generation_params[field] = value
            
            elif node_type == 'EmptyLatentImage':
                if 'width' in extracted_values and 'height' in extracted_values:
                    generation_params['width'] = extracted_values['width']
                    generation_params['height'] = extracted_values['height']
                    if 'batch_size' in extracted_values:
                        generation_params['batch_size'] = extracted_values['batch_size']
            
            elif node_type == 'CLIPTextEncode':
                if 'prompt' in extracted_values:
                    is_negative = extracted_values.get('is_negative', False)
                    
                    # Also check node metadata for negative indicators
                    if '_meta' in node and 'title' in node['_meta']:
                        title = node['_meta']['title'].lower()
                        if 'negative' in title or 'neg' in title:
                            is_negative = True
                            
                    # Store in appropriate field
                    if is_negative:
                        generation_params['negative_prompt'] = extracted_values['prompt']
                    else:
                        generation_params['prompt'] = extracted_values['prompt']
            
            elif node_type in ['ControlNetLoader', 'ControlNetApply']:
                if 'controlnet_model' in extracted_values or 'controlnet_weight' in extracted_values:
                    control_net_info = {
                        'model': extracted_values.get('controlnet_model'),
                        'weight': extracted_values.get('controlnet_weight')
                    }
                    control_nets.append(control_net_info)
            
            elif node_type == 'IPAdapterModelLoader':
                if 'ip_adapter_model' in extracted_values:
                    ip_adapters.append({
                        'model': extracted_values['ip_adapter_model']
                    })
            
            elif node_type == 'StyleModelLoader':
                if 'style_model' in extracted_values:
                    generation_params['style_model'] = extracted_values['style_model']
                    
            elif node_type == 'UpscaleModelLoader':
                if 'upscale_model' in extracted_values:
                    upscalers.append({
                        'model': extracted_values['upscale_model']
                    })
                    
            elif node_type == 'UNETLoader':
                if 'unet_model' in extracted_values:
                    unet_models.append({
                        'model': extracted_values['unet_model']
                    })
                    
            elif node_type == 'ModelSamplingFlux':
                if 'flux_fraction' in extracted_values or 'flux_mode' in extracted_values:
                    generation_params['flux'] = {
                        'fraction': extracted_values.get('flux_fraction', 0.5),
                        'mode': extracted_values.get('flux_mode', 'extend')
                    }
        
        # Store all collected information in result structure
        result['generation_parameters'] = generation_params
        
        # Add other collections only if they have data
        if loras:
            generation_params['loras'] = loras
        
        if control_nets:
            generation_params['control_nets'] = control_nets
            
        if ip_adapters:
            generation_params['ip_adapters'] = ip_adapters
            
        if upscalers:
            generation_params['upscalers'] = upscalers
            
        if unet_models:
            generation_params['unet_models'] = unet_models
            
        # Add timestamp
        import datetime
        generation_params['timestamp'] = datetime.datetime.now().isoformat()
    
    def _extract_detailed_prompts(self, nodes: Dict[str, Any], links: List[Any], 
                                 result: Dict[str, Any]) -> None:
        """Extract prompts with attention to negative prompts and connections"""
        positive_prompts = []
        negative_prompts = []
        
        # Identify nodes that contain prompts
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            
            # Check for CLIP text encode nodes
            if 'CLIPTextEncode' in node_type and 'inputs' in node and 'text' in node['inputs']:
                text = node['inputs']['text']
                is_negative = False
                
                # Check explicit negative flag
                if 'is_negative' in node and node['is_negative']:
                    is_negative = True
                
                # Check title for "negative" hints
                if '_meta' in node and 'title' in node['_meta']:
                    title = node['_meta']['title'].lower()
                    if 'negative' in title or 'neg' in title:
                        is_negative = True
                
                # Store in appropriate list
                if is_negative:
                    negative_prompts.append(text)
                else:
                    positive_prompts.append(text)
        
        # Store results
        if positive_prompts:
            result['prompts']['positive'] = positive_prompts
        if negative_prompts:
            result['prompts']['negative'] = negative_prompts
    
    def _extract_latent_dimensions(self, nodes: Dict[str, Any]) -> Dict[str, int]:
        """Extract latent dimensions from nodes"""
        dimensions = {}
        
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Check for EmptyLatentImage node
            if 'EmptyLatent' in node_type:
                if 'width' in inputs and 'height' in inputs:
                    try:
                        dimensions['width'] = int(inputs['width'])
                        dimensions['height'] = int(inputs['height'])
                        if 'batch_size' in inputs:
                            dimensions['batch_size'] = int(inputs['batch_size'])
                        return dimensions  # Found dimensions, return immediately
                    except (ValueError, TypeError):
                        pass
                        
            # Check for other nodes with width/height inputs
            elif 'width' in inputs and 'height' in inputs:
                try:
                    # Check if values are directly accessible (not node references)
                    if not isinstance(inputs['width'], list) and not isinstance(inputs['height'], list):
                        dimensions['width'] = int(inputs['width'])
                        dimensions['height'] = int(inputs['height'])
                        return dimensions
                except (ValueError, TypeError):
                    pass
        
        return dimensions
    
    def identify_active_nodes(self, workflow_data):
        """
        Identify which nodes are actively contributing to the output
        
        Args:
            workflow_data: Raw workflow data
            
        Returns:
            set: Set of active node IDs
        """
        active_nodes = set()
        
        try:
            # Get nodes and links
            prompt_data = workflow_data.get('prompt', {})
            if not prompt_data and isinstance(workflow_data, dict) and 'nodes' in workflow_data:
                prompt_data = workflow_data
                
            nodes = prompt_data.get('nodes', {})
            links = prompt_data.get('links', [])
            if not links and 'connections' in prompt_data:
                links = prompt_data.get('connections', [])
            
            # Identify output nodes
            output_nodes = self._identify_output_nodes(nodes)
            
            # Trace backward from output nodes
            to_process = list(output_nodes)
            while to_process:
                current_node = to_process.pop()
                if current_node in active_nodes:
                    continue
                    
                active_nodes.add(current_node)
                
                # Find all links that connect to this node's inputs
                for link in links:
                    # Format: [link_id, from_node, from_output, to_node, to_input, type]
                    if len(link) >= 4 and link[3] == current_node:  # if this link connects to current node
                        from_node = link[1]
                        if from_node not in active_nodes:
                            to_process.append(from_node)
        except Exception as e:
            if self.debug:
                print(f"[WorkflowParser] Error identifying active nodes: {str(e)}")
        
        return active_nodes
    
    def convert_to_metadata_format(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert workflow data to standardized metadata format
        
        Args:
            workflow_data: Raw workflow data
            
        Returns:
            dict: Metadata in proper format for MetadataService
        """
        # If input is null or empty, return empty dict
        if not workflow_data:
            return {}
        
        # Extract detailed data from workflow
        analysis = self.extract_and_analyze(workflow_data)
        
        # Structure for ai_info section
        metadata = {
            'ai_info': {
                'generation': {},
                'workflow': workflow_data
            }
        }
        
        # Extract generation parameters
        generation = {}
        
        # Map model
        if 'model' in analysis:
            generation['model'] = analysis['model']
        elif 'generation_parameters' in analysis and 'model' in analysis['generation_parameters']:
            generation['model'] = analysis['generation_parameters']['model']
            
        # Map prompts
        if 'prompts' in analysis:
            prompts = analysis['prompts']
            if prompts.get('positive'):
                generation['prompt'] = '\n'.join(prompts['positive'])
            if prompts.get('negative'):
                generation['negative_prompt'] = '\n'.join(prompts['negative'])
                
        # Map sampler parameters
        if 'sampler' in analysis:
            sampler = analysis['sampler']
            for field in ['seed', 'steps', 'cfg_scale']:
                if field in sampler:
                    generation[field] = sampler[field]
            
            # Map sampler name and scheduler
            if 'sampler' in sampler:
                generation['sampler'] = sampler['sampler']
            if 'scheduler' in sampler:
                generation['scheduler'] = sampler['scheduler']
                
        # Map dimensions if available
        if 'dimensions' in analysis:
            dimensions = analysis['dimensions']
            if 'width' in dimensions and 'height' in dimensions:
                generation['width'] = dimensions['width']
                generation['height'] = dimensions['height']
                
        # Extract additional parameters from generation_parameters
        if 'generation_parameters' in analysis:
            params = analysis['generation_parameters']
            for key, value in params.items():
                # Skip if already handled
                if key in ['model', 'prompt', 'negative_prompt', 'seed', 'steps', 'cfg_scale', 'sampler', 'scheduler']:
                    continue
                # Add additional parameters
                generation[key] = value
                
        # Add VAE if present
        if 'generation_parameters' in analysis and 'vae' in analysis['generation_parameters']:
            generation['vae'] = analysis['generation_parameters']['vae']
            
        # Extract LoRAs if present
        loras = []
        if 'generation_parameters' in analysis:
            params = analysis['generation_parameters']
            if 'lora_name' in params:
                lora_info = {
                    'name': params['lora_name'],
                    'strength': params.get('strength_model', 1.0)
                }
                loras.append(lora_info)
                
        if loras:
            generation['loras'] = loras
            
        # Add timestamp
        generation['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Add to metadata
        metadata['ai_info']['generation'] = generation
        
        return metadata