"""
workflow_helpers.py
Description: Helper functions for workflow data processing, metadata enhancement, and visualization utilities.
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

"""

import json
import os
import re
import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

def identify_workflow_source(workflow_data: Dict[str, Any]) -> str:
    """
    Identify the source of a workflow (which AI system created it)
    
    Args:
        workflow_data: Raw workflow data dictionary
        
    Returns:
        str: Identified source ('comfyui', 'automatic1111', 'novelai', etc.)
    """
    # Check for explicit type marker
    if 'type' in workflow_data:
        workflow_type = workflow_data.get('type', '')
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
    if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict) and 'nodes' in workflow_data.get('prompt', {}):
        return 'comfyui'
        
    # Look for A1111 specific structure
    if all(k in workflow_data for k in ['prompt', 'negative_prompt', 'sampler']):
        return 'automatic1111'
        
    # Look for NovelAI specific markers
    if 'novelai' in str(workflow_data).lower() or 'nai' in str(workflow_data).lower():
        return 'novelai'
        
    return 'unknown'

def extract_generation_parameters(workflow_data: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Extract generation parameters from workflow based on its source
    
    Args:
        workflow_data: Raw workflow data dictionary
        source: Identified source ('comfyui', 'automatic1111', etc.)
        
    Returns:
        dict: Extracted generation parameters
    """
    generation_params = {}
    
    if source == 'comfyui':
        # Extract from ComfyUI workflow
        if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            nodes = workflow_data['prompt'].get('nodes', {})
            
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
            if key in workflow_data:
                generation_params[key] = workflow_data[key]
    
    # Add timestamp
    generation_params['timestamp'] = datetime.datetime.now().isoformat()
    
    return generation_params

def calculate_workflow_complexity(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate complexity metrics for a workflow
    
    Args:
        workflow_data: Raw workflow data dictionary
        
    Returns:
        dict: Complexity metrics including node count, connection count,
              complexity score, etc.
    """
    stats = {
        'node_count': 0,
        'connection_count': 0,
        'unique_node_types': 0,
        'complexity_score': 0,
        'node_types': {}
    }
    
    # Check for ComfyUI structure
    if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
        nodes = workflow_data['prompt'].get('nodes', {})
        links = workflow_data['prompt'].get('links', [])
        
        # Count nodes and node types
        stats['node_count'] = len(nodes)
        node_types = {}
        
        for node_id, node in nodes.items():
            node_type = node.get('class_type', 'Unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        stats['node_types'] = node_types
        stats['unique_node_types'] = len(node_types)
        
        # Count connections
        stats['connection_count'] = len(links)
        
        # Calculate complexity score
        # More nodes, more connections, and more unique node types = more complex
        stats['complexity_score'] = (
            stats['node_count'] * 2 + 
            stats['connection_count'] * 1.5 + 
            stats['unique_node_types'] * 3
        )
    
    return stats

def extract_embedded_workflow(filepath: str) -> Dict[str, Any]:
    """
    Extract workflow data from embedded metadata in an image file
    
    Args:
        filepath: Path to the image file
        
    Returns:
        dict: Extracted workflow data or empty dict if none found
    """
    try:
        from PIL import Image
        
        with Image.open(filepath) as img:
            # Check for workflow data in PNG text chunks
            if 'prompt' in img.info:
                try:
                    return json.loads(img.info['prompt'])
                except json.JSONDecodeError:
                    pass
            
            # Check for workflow in extra PNG info
            if 'workflow' in img.info:
                try:
                    return json.loads(img.info['workflow'])
                except json.JSONDecodeError:
                    pass
                    
            # Check for parameters in A1111 format
            if 'parameters' in img.info:
                try:
                    params = img.info['parameters']
                    # Parse A1111 parameters string into a structured format
                    result = {'type': 'automatic1111'}
                    
                    # Split on the first 'Negative prompt:'
                    parts = params.split('Negative prompt:', 1)
                    if len(parts) == 2:
                        result['prompt'] = parts[0].strip()
                        # The rest contains negative prompt and settings
                        neg_and_settings = parts[1].split('Steps:', 1)
                        if len(neg_and_settings) == 2:
                            result['negative_prompt'] = neg_and_settings[0].strip()
                            # Parse the technical settings
                            settings_text = 'Steps:' + neg_and_settings[1]
                            settings_pattern = r'([a-zA-Z\s]+):\s*([^,]+)(?:,|$)'
                            for setting_match in re.finditer(settings_pattern, settings_text):
                                key = setting_match.group(1).strip().lower().replace(' ', '_')
                                value = setting_match.group(2).strip()
                                result[key] = value
                        else:
                            result['negative_prompt'] = neg_and_settings[0].strip()
                    else:
                        result['prompt'] = params
                    
                    return result
                except Exception:
                    pass
        
        return {}
    except Exception as e:
        print(f"Error extracting embedded workflow: {str(e)}")
        return {}

def extract_workflow_node_types(workflow_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Extract and count all node types used in a workflow
    
    Args:
        workflow_data: Raw workflow data dictionary
        
    Returns:
        dict: Mapping of node type names to their count in the workflow
    """
    node_types = {}
    
    # Handle ComfyUI workflow structure
    if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
        nodes = workflow_data['prompt'].get('nodes', {})
        
        for node_id, node in nodes.items():
            if isinstance(node, dict) and 'class_type' in node:
                node_type = node['class_type']
                node_types[node_type] = node_types.get(node_type, 0) + 1
    
    # Direct node structure
    elif isinstance(workflow_data, dict):
        for key, value in workflow_data.items():
            if isinstance(value, dict) and 'class_type' in value:
                node_type = value['class_type']
                node_types[node_type] = node_types.get(node_type, 0) + 1
    
    return node_types

def extract_model_names(workflow_data: Dict[str, Any]) -> List[str]:
    """
    Extract all model names (checkpoints, VAEs, LoRAs, etc.) from a workflow
    
    Args:
        workflow_data: Raw workflow data dictionary
        
    Returns:
        list: List of model names found in the workflow
    """
    models = []
    
    # Check for ComfyUI structure
    if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
        nodes = workflow_data['prompt'].get('nodes', {})
        
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            class_type = node['class_type']
            inputs = node.get('inputs', {})
            
            # Checkpoint loader
            if 'CheckpointLoader' in class_type and 'ckpt_name' in inputs:
                models.append(inputs['ckpt_name'])
            
            # VAE loader
            elif 'VAELoader' in class_type and 'vae_name' in inputs:
                models.append(inputs['vae_name'])
            
            # LoRA loader
            elif 'LoRA' in class_type and 'lora_name' in inputs:
                models.append(inputs['lora_name'])
            
            # ControlNet model
            elif 'ControlNet' in class_type and 'control_net_name' in inputs:
                models.append(inputs['control_net_name'])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_models = [m for m in models if not (m in seen or seen.add(m))]
    
    return unique_models

def extract_prompts(workflow_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract positive and negative prompts from a workflow
    
    Args:
        workflow_data: Raw workflow data dictionary
        
    Returns:
        dict: Dictionary with 'positive' and 'negative' prompt lists
    """
    result = {
        'positive': [],
        'negative': []
    }
    
    # Check for ComfyUI structure
    if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
        nodes = workflow_data['prompt'].get('nodes', {})
        
        for node_id, node in nodes.items():
            if not isinstance(node, dict) or 'class_type' not in node:
                continue
            
            # Look for CLIP text encode nodes
            if 'CLIPTextEncode' in node['class_type']:
                inputs = node.get('inputs', {})
                if 'text' in inputs:
                    text = inputs['text']
                    
                    # Determine if positive or negative
                    is_negative = False
                    
                    # Check node title for indication
                    title = node.get('title', '').lower()
                    if 'negative' in title or 'neg' in title:
                        is_negative = True
                        
                    # Check connections for indication
                    for link_id, link in enumerate(workflow_data['prompt'].get('links', [])):
                        if link[0] == node_id:  # Node is source
                            # Check if target is negative input
                            target_id = link[2]
                            target_slot = link[3]
                            target = nodes.get(target_id, {})
                            if target.get('inputs', {}).get('neg_conditioning') == target_slot:
                                is_negative = True
                                break
                    
                    # Add to appropriate list
                    if is_negative:
                        result['negative'].append(text)
                    else:
                        result['positive'].append(text)
    
    # Check for direct prompt fields (A1111 style)
    elif isinstance(workflow_data, dict):
        if 'prompt' in workflow_data:
            result['positive'].append(workflow_data['prompt'])
        if 'negative_prompt' in workflow_data:
            result['negative'].append(workflow_data['negative_prompt'])
    
    return result

def format_workflow_summary(workflow_data: Dict[str, Any], format_type: str = 'text') -> str:
    """
    Create a user-friendly summary of a workflow
    
    Args:
        workflow_data: Raw workflow data dictionary
        format_type: Output format ('text', 'html', 'markdown')
        
    Returns:
        str: Formatted workflow summary
    """
    # Identify workflow source
    source = identify_workflow_source(workflow_data)
    
    # Extract key components
    models = extract_model_names(workflow_data)
    prompts = extract_prompts(workflow_data)
    node_types = extract_workflow_node_types(workflow_data)
    complexity = calculate_workflow_complexity(workflow_data)
    parameters = extract_generation_parameters(workflow_data, source)
    
    # Format based on output type
    if format_type == 'text':
        return _format_workflow_summary_as_text(
            source, models, prompts, node_types, complexity, parameters)
    elif format_type == 'html':
        return _format_workflow_summary_as_html(
            source, models, prompts, node_types, complexity, parameters)
    elif format_type == 'markdown':
        return _format_workflow_summary_as_markdown(
            source, models, prompts, node_types, complexity, parameters)
    else:
        return f"Unknown format type: {format_type}"

def _format_workflow_summary_as_text(
        source: str, 
        models: List[str], 
        prompts: Dict[str, List[str]], 
        node_types: Dict[str, int], 
        complexity: Dict[str, Any],
        parameters: Dict[str, Any]) -> str:
    """Format workflow summary as plain text"""
    lines = [f"Workflow Source: {source.upper()}", ""]
    
    # Add models
    if models:
        lines.append("Models:")
        for model in models:
            lines.append(f"- {model}")
        lines.append("")
    
    # Add generation parameters
    if parameters:
        lines.append("Generation Parameters:")
        for key, value in parameters.items():
            if key not in ('prompt', 'negative_prompt'):
                lines.append(f"- {key}: {value}")
        lines.append("")
    
    # Add prompts
    if prompts['positive']:
        lines.append("Positive Prompt:")
        for prompt in prompts['positive']:
            lines.append(prompt)
        lines.append("")
    
    if prompts['negative']:
        lines.append("Negative Prompt:")
        for prompt in prompts['negative']:
            lines.append(prompt)
        lines.append("")
    
    # Add complexity info
    if complexity:
        lines.append("Workflow Complexity:")
        if 'node_count' in complexity:
            lines.append(f"- Nodes: {complexity['node_count']}")
        if 'connection_count' in complexity:
            lines.append(f"- Connections: {complexity['connection_count']}")
        if 'complexity_score' in complexity:
            lines.append(f"- Complexity Score: {complexity['complexity_score']}")
        if 'unique_node_types' in complexity:
            lines.append(f"- Unique Node Types: {complexity['unique_node_types']}")
        lines.append("")
    
    # Add node type summary (top 10)
    if node_types:
        lines.append("Top Node Types:")
        sorted_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)
        for node_type, count in sorted_types[:10]:
            lines.append(f"- {node_type}: {count}")
    
    return "\n".join(lines)

def _format_workflow_summary_as_markdown(
        source: str, 
        models: List[str], 
        prompts: Dict[str, List[str]], 
        node_types: Dict[str, int], 
        complexity: Dict[str, Any],
        parameters: Dict[str, Any]) -> str:
    """Format workflow summary as markdown"""
    lines = [f"# Workflow Analysis ({source.upper()})", ""]
    
    # Add models
    if models:
        lines.append("## Models")
        for model in models:
            lines.append(f"- {model}")
        lines.append("")
    
    # Add generation parameters
    if parameters:
        lines.append("## Generation Parameters")
        for key, value in parameters.items():
            if key not in ('prompt', 'negative_prompt'):
                lines.append(f"- **{key}:** {value}")
        lines.append("")
    
    # Add prompts
    if prompts['positive']:
        lines.append("## Positive Prompt")
        for prompt in prompts['positive']:
            lines.append(f"```\n{prompt}\n```")
        lines.append("")
    
    if prompts['negative']:
        lines.append("## Negative Prompt")
        for prompt in prompts['negative']:
            lines.append(f"```\n{prompt}\n```")
        lines.append("")
    
    # Add complexity info
    if complexity:
        lines.append("## Workflow Complexity")
        if 'node_count' in complexity:
            lines.append(f"- **Nodes:** {complexity['node_count']}")
        if 'connection_count' in complexity:
            lines.append(f"- **Connections:** {complexity['connection_count']}")
        if 'complexity_score' in complexity:
            lines.append(f"- **Complexity Score:** {complexity['complexity_score']}")
        if 'unique_node_types' in complexity:
            lines.append(f"- **Unique Node Types:** {complexity['unique_node_types']}")
        lines.append("")
    
    # Add node type summary (top 10)
    if node_types:
        lines.append("## Top Node Types")
        sorted_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)
        for node_type, count in sorted_types[:10]:
            lines.append(f"- **{node_type}:** {count}")
    
    return "\n".join(lines)

def _format_workflow_summary_as_html(
        source: str, 
        models: List[str], 
        prompts: Dict[str, List[str]], 
        node_types: Dict[str, int], 
        complexity: Dict[str, Any],
        parameters: Dict[str, Any]) -> str:
    """Format workflow summary as HTML"""
    html = [
        "<html><head><title>Workflow Analysis</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 20px; }",
        "h1, h2 { color: #333366; }",
        "h1 { border-bottom: 1px solid #cccccc; padding-bottom: 5px; }",
        "h2 { margin-top: 20px; }",
        "ul { margin-top: 5px; }",
        "pre { background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd; }",
        ".section { margin-bottom: 20px; }",
        "</style>",
        "</head><body>",
        f"<h1>Workflow Analysis ({source.upper()})</h1>"
    ]
    
    # Add models
    if models:
        html.append("<div class='section'>")
        html.append("<h2>Models</h2>")
        html.append("<ul>")
        for model in models:
            html.append(f"<li>{model}</li>")
        html.append("</ul>")
        html.append("</div>")
    
    # Add generation parameters
    if parameters:
        html.append("<div class='section'>")
        html.append("<h2>Generation Parameters</h2>")
        html.append("<ul>")
        for key, value in parameters.items():
            if key not in ('prompt', 'negative_prompt'):
                html.append(f"<li><strong>{key}:</strong> {value}</li>")
        html.append("</ul>")
        html.append("</div>")
    
    # Add prompts
    if prompts['positive']:
        html.append("<div class='section'>")
        html.append("<h2>Positive Prompt</h2>")
        for prompt in prompts['positive']:
            html.append(f"<pre>{prompt}</pre>")
        html.append("</div>")
    
    if prompts['negative']:
        html.append("<div class='section'>")
        html.append("<h2>Negative Prompt</h2>")
        for prompt in prompts['negative']:
            html.append(f"<pre>{prompt}</pre>")
        html.append("</div>")
    
    # Add complexity info
    if complexity:
        html.append("<div class='section'>")
        html.append("<h2>Workflow Complexity</h2>")
        html.append("<ul>")
        if 'node_count' in complexity:
            html.append(f"<li><strong>Nodes:</strong> {complexity['node_count']}</li>")
        if 'connection_count' in complexity:
            html.append(f"<li><strong>Connections:</strong> {complexity['connection_count']}</li>")
        if 'complexity_score' in complexity:
            html.append(f"<li><strong>Complexity Score:</strong> {complexity['complexity_score']}</li>")
        if 'unique_node_types' in complexity:
            html.append(f"<li><strong>Unique Node Types:</strong> {complexity['unique_node_types']}</li>")
        html.append("</ul>")
        html.append("</div>")
    
    # Add node type summary (top 10)
    if node_types:
        html.append("<div class='section'>")
        html.append("<h2>Top Node Types</h2>")
        html.append("<ul>")
        sorted_types = sorted(node_types.items(), key=lambda x: x[1], reverse=True)
        for node_type, count in sorted_types[:10]:
            html.append(f"<li><strong>{node_type}:</strong> {count}</li>")
        html.append("</ul>")
        html.append("</div>")
    
    html.append("</body></html>")
    return "\n".join(html)
