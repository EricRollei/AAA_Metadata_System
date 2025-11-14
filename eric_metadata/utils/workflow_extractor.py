"""
workflow_extractor.py: Workflow Metadata Extraction Utility
Description: Utility class for extracting metadata from ComfyUI workflows.
    This class can be used by multiple nodes to provide consistent workflow parsing.
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
# Metadata_system/src/eric_metadata/utils/workflow_extractor.py

import os
import json
import datetime
from typing import Dict, Any, List, Optional, Set, Tuple

class WorkflowExtractor:
    """
    Utility class for extracting metadata from ComfyUI workflows
    Can be used by multiple nodes to provide consistent workflow parsing
    """
    
    def __init__(self, debug: bool = False, discovery_mode: bool = False):
        """Initialize the workflow extractor
        
        Args:
            debug: Whether to enable debug output
            discovery_mode: Whether to collect and log unknown node types and parameters
        """
        self.debug = debug
        self.discovery_mode = discovery_mode
        self.node_type_patterns = self._init_node_patterns()
        
        # For tracking discovered elements
        self.discovered_node_types = set()
        self.discovered_parameters = {}
        self.discovery_log = []
        # For tracking discovered elements
        self.discovered_node_types = set()
        self.node_type_frequencies = {}  # Track counts of each node type
        self.discovered_parameters = {}
        self.parameter_frequencies = {}  # Track counts of each parameter
        self.discovery_log = []
        # For tracking connection patterns
        self.connection_patterns = {}

    def _init_node_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize pattern matching for different node types"""
        return {
            'checkpoint': {
                'patterns': ['CheckpointLoader', 'ModelLoader', 'LoadCheckpoint'],
                'param_keys': ['ckpt_name', 'model_name', 'checkpoint'],
                'output_key': 'model'
            },
            'sampler': {
                'patterns': ['KSampler', 'Sampler', 'SamplerAdvanced'],
                'param_keys': {
                    'sampler_name': 'sampler',
                    'scheduler': 'scheduler',
                    'steps': 'steps',
                    'cfg': 'cfg_scale',
                    'seed': 'seed',
                    'denoise': 'denoise'
                }
            },
            # Add more node types here
        }
    
    def extract_metadata(self, prompt: Dict[str, Any], 
                        extra_pnginfo: Optional[Dict[str, Any]] = None,
                        collect_all: bool = False) -> Dict[str, Any]:
        """
        Extract metadata from workflow
        
        Args:
            prompt: The workflow prompt structure
            extra_pnginfo: Additional PNG info
            collect_all: Whether to collect all instances of parameters (e.g. all models)
                         or just the primary ones
        
        Returns:
            dict: Extracted metadata
        """
        # Store all nodes for reference resolution
        self.nodes = prompt  # Add this line near the beginning
        
        # Initialize result structure
        result = {
            'generation': {},
            'workflow_info': {}
        }
        
        # Track collections of similar nodes
        collections = {
            'models': [],
            'samplers': [],
            'vae_models': [],
            'loras': [],
            'prompts': [],
            'negative_prompts': []
        }
        
        # Extract from prompt (node configurations)
        if prompt and isinstance(prompt, dict):
            # Extract node connections for better analysis
            connections = self._build_node_connections(prompt, extra_pnginfo)
            
            # First pass: identify and categorize nodes
            for node_id, node in prompt.items():
                if not isinstance(node, dict):
                    continue
                
                node_type = node.get('class_type', '')
                self._process_node(node, node_id, node_type, collections, connections)
            
            # Second pass: determine primary nodes based on connections
            generation_params = self._prioritize_parameters(collections, connections)
            result['generation'] = generation_params
            
            # If requested, include all collections
            if collect_all:
                for key, collection in collections.items():
                    if collection:  # Only add non-empty collections
                        result[key] = collection
        
        # Extract additional info from extra_pnginfo
        if extra_pnginfo:
            workflow_info = self._extract_from_extra_pnginfo(extra_pnginfo)
            result['workflow_info'] = workflow_info
            
            # Add relevant workflow_info fields to generation params if not already set
            for key in ['version', 'resolution', 'width', 'height']:
                if key in workflow_info and key not in result['generation']:
                    result['generation'][key] = workflow_info[key]
        
        # Add timestamp
        result['generation']['timestamp'] = datetime.datetime.now().isoformat()
        
        return result
    def _track_node_discovery(self, node_type: str, node: Dict[str, Any]) -> None:
        """Track discovered node types and their parameters with frequencies"""
        if not self.discovery_mode:
            return
        
        # Track node type frequency
        if node_type not in self.node_type_frequencies:
            self.node_type_frequencies[node_type] = 0
        self.node_type_frequencies[node_type] += 1
        
        # Track node type if not already seen
        if node_type not in self.discovered_node_types:
            self.discovered_node_types.add(node_type)
            self.discovery_log.append(f"Discovered new node type: {node_type}")
            
        # Track parameters for this node type
        inputs = node.get('inputs', {})
        if inputs:
            if node_type not in self.discovered_parameters:
                self.discovered_parameters[node_type] = {}
            
            # Add all parameter keys
            for param_key, param_value in inputs.items():
                # Track parameter
                self._track_parameter_discovery(node_type, param_key, param_value)
                
                # Track parameter frequency
                param_id = f"{node_type}.{param_key}"
                if param_id not in self.parameter_frequencies:
                    self.parameter_frequencies[param_id] = 0
                self.parameter_frequencies[param_id] += 1

    def _track_connection_patterns(self, connections: Dict[str, Dict]) -> None:
        """Track common connection patterns between node types"""
        if not self.discovery_mode:
            return
            
        for node_id, conn_info in connections.items():
            # Skip if this isn't a valid node
            if node_id not in self.processed_nodes:
                continue
                
            node_type = self.processed_nodes[node_id]
            
            # Track input connections
            for input_node_id in conn_info.get('inputs', []):
                if input_node_id in self.processed_nodes:
                    input_node_type = self.processed_nodes[input_node_id]
                    
                    # Create connection pattern
                    pattern = f"{input_node_type} -> {node_type}"
                    
                    if pattern not in self.connection_patterns:
                        self.connection_patterns[pattern] = 0
                    self.connection_patterns[pattern] += 1

    def _analyze_parameter_patterns(self) -> Dict[str, Any]:
        """Analyze parameter naming patterns across different node types"""
        # Group parameters by similar names
        similar_params = {}
        
        # Process all discovered parameters
        for node_type, params in self.discovered_parameters.items():
            # Handle params whether it's a dict or set
            param_keys = params.keys() if isinstance(params, dict) else params
            
            for param_key in param_keys:
                # Normalize parameter name
                normalized = self._normalize_param_name(param_key)
                
                if normalized not in similar_params:
                    similar_params[normalized] = []
                    
                similar_params[normalized].append({
                    'node_type': node_type,
                    'param_key': param_key,
                    'frequency': self.parameter_frequencies.get(f"{node_type}.{param_key}", 0)
                })
        
        # Sort groups by frequency
        for normalized, params in similar_params.items():
            similar_params[normalized] = sorted(
                params, 
                key=lambda x: x['frequency'], 
                reverse=True
            )
        
        return similar_params

    def _normalize_param_name(self, param_name: str) -> str:
        """Normalize parameter names for pattern matching"""
        # Remove common prefixes/suffixes
        name = param_name.lower()
        for prefix in ['input_', 'param_', 'p_']:
            if name.startswith(prefix):
                name = name[len(prefix):]
                
        for suffix in ['_value', '_param', '_input']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Group similar semantic concepts
        concept_groups = {
            'image': ['img', 'image', 'picture', 'photo'],
            'model': ['model', 'checkpoint', 'ckpt', 'mdl'],
            'strength': ['strength', 'power', 'amount', 'intensity'],
            'seed': ['seed', 'random_seed', 'noise_seed'],
            # Add more semantic groups as needed
        }
        
        for concept, variants in concept_groups.items():
            if name in variants:
                return concept
        
        return name
    def save_discovery_report(self, filepath: str) -> bool:
        """Save comprehensive discovery information to a JSON file"""
        if not self.discovery_mode:
            return False
        
        try:
            import json
            
            # Analyze parameter patterns
            parameter_patterns = self._analyze_parameter_patterns()
            
            # Format the report
            report = {
                'timestamp': datetime.datetime.now().isoformat(),
                'summary': {
                    'node_types_count': len(self.discovered_node_types),
                    'parameters_count': sum(len(params) for params in self.discovered_parameters.values()),
                    'most_common_nodes': sorted(
                        self.node_type_frequencies.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10]
                },
                'node_types': {
                    node_type: {
                        'frequency': self.node_type_frequencies.get(node_type, 0),
                        'parameters': params
                    }
                    for node_type, params in self.discovered_parameters.items()
                },
                'parameter_patterns': parameter_patterns,
                'connection_patterns': {
                    pattern: count for pattern, count in 
                    sorted(self.connection_patterns.items(), key=lambda x: x[1], reverse=True)
                },
                'discovery_log': self.discovery_log
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving discovery report: {str(e)}")
            return False

    def save_html_report(self, filepath: str) -> bool:
        """Save discovery information as an interactive HTML report
        
        Args:
            filepath: Path to save the HTML report
            
        Returns:
            bool: True if successful
        """
        if not self.discovery_mode:
            return False
        
        try:
            # Prepare data for the report
            node_types = sorted(list(self.discovered_node_types))
            node_frequencies = [self.node_type_frequencies.get(nt, 0) for nt in node_types]
            
            # Create parameter patterns analysis
            parameter_patterns = self._analyze_parameter_patterns()
            
            # Generate HTML with interactive charts
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Workflow Discovery Report</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .card {{ border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-bottom: 20px; }}
                    .flex-container {{ display: flex; flex-wrap: wrap; }}
                    .half-width {{ width: 48%; margin-right: 2%; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .search-box {{ margin-bottom: 10px; padding: 8px; width: 100%; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Workflow Discovery Report</h1>
                    <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    
                    <div class="card">
                        <h2>Summary</h2>
                        <p>Discovered {len(self.discovered_node_types)} unique node types with {sum(len(params) for params in self.discovered_parameters.values())} unique parameters.</p>
                        
                        <div class="flex-container">
                            <div class="half-width">
                                <h3>Most Common Node Types</h3>
                                <canvas id="nodeTypeChart"></canvas>
                            </div>
                            <div class="half-width">
                                <h3>Connection Patterns</h3>
                                <canvas id="connectionChart"></canvas>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Node Types</h2>
                        <input type="text" id="nodeSearch" class="search-box" placeholder="Search node types...">
                        <table id="nodeTable">
                            <thead>
                                <tr>
                                    <th>Node Type</th>
                                    <th>Frequency</th>
                                    <th>Parameter Count</th>
                                    <th>Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Will be filled by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="card">
                        <h2>Parameter Patterns</h2>
                        <input type="text" id="paramSearch" class="search-box" placeholder="Search parameter patterns...">
                        <table id="paramTable">
                            <thead>
                                <tr>
                                    <th>Normalized Name</th>
                                    <th>Variations</th>
                                    <th>Node Types</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Will be filled by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <script>
                    // Data for charts
                    const nodeTypes = {json.dumps(node_types)};
                    const nodeFrequencies = {json.dumps(node_frequencies)};
                    const nodeData = {json.dumps({nt: self.discovered_parameters.get(nt, {}) for nt in node_types})};
                    const parameterPatterns = {json.dumps(parameter_patterns)};
                    
                    // Create charts
                    const nodeTypeChart = new Chart(
                        document.getElementById('nodeTypeChart'),
                        {{
                            type: 'bar',
                            data: {{
                                labels: nodeTypes.slice(0, 15),
                                datasets: [{{
                                    label: 'Frequency',
                                    data: nodeFrequencies.slice(0, 15),
                                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                                    borderColor: 'rgb(54, 162, 235)',
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                scales: {{
                                    y: {{
                                        beginAtZero: true
                                    }}
                                }}
                            }}
                        }}
                    );
                    
                    // Fill node table
                    const nodeTable = document.getElementById('nodeTable').getElementsByTagName('tbody')[0];
                    nodeTypes.forEach(nodeType => {{
                        const row = nodeTable.insertRow();
                        const params = nodeData[nodeType] || {{}};
                        
                        row.insertCell(0).textContent = nodeType;
                        row.insertCell(1).textContent = {json.dumps(self.node_type_frequencies)}[nodeType] || 0;
                        row.insertCell(2).textContent = Object.keys(params).length;
                        
                        const detailsCell = row.insertCell(3);
                        const detailsButton = document.createElement('button');
                        detailsButton.textContent = 'View Parameters';
                        detailsButton.onclick = () => {{
                            alert('Parameters for ' + nodeType + ':\\n' + 
                                Object.keys(params).map(p => p + ': ' + 
                                    (typeof params[p] === 'object' ? JSON.stringify(params[p]) : params[p]))
                                    .join('\\n'));
                        }};
                        detailsCell.appendChild(detailsButton);
                    }});
                    
                    // Fill parameter table
                    const paramTable = document.getElementById('paramTable').getElementsByTagName('tbody')[0];
                    Object.entries(parameterPatterns).forEach(([normalizedName, variations]) => {{
                        const row = paramTable.insertRow();
                        
                        row.insertCell(0).textContent = normalizedName;
                        
                        const variationsCell = row.insertCell(1);
                        variationsCell.textContent = variations.map(v => v.param_key).join(', ');
                        
                        const nodeTypesCell = row.insertCell(2);
                        nodeTypesCell.textContent = [...new Set(variations.map(v => v.node_type))].join(', ');
                    }});
                    
                    // Search functionality
                    document.getElementById('nodeSearch').addEventListener('keyup', function() {{
                        const filter = this.value.toLowerCase();
                        const rows = document.getElementById('nodeTable').getElementsByTagName('tbody')[0].rows;
                        
                        for (let i = 0; i < rows.length; i++) {{
                            const nodeType = rows[i].cells[0].textContent.toLowerCase();
                            rows[i].style.display = nodeType.includes(filter) ? '' : 'none';
                        }}
                    }});
                    
                    document.getElementById('paramSearch').addEventListener('keyup', function() {{
                        const filter = this.value.toLowerCase();
                        const rows = document.getElementById('paramTable').getElementsByTagName('tbody')[0].rows;
                        
                        for (let i = 0; i < rows.length; i++) {{
                            const normalizedName = rows[i].cells[0].textContent.toLowerCase();
                            const variations = rows[i].cells[1].textContent.toLowerCase();
                            rows[i].style.display = normalizedName.includes(filter) || variations.includes(filter) ? '' : 'none';
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            
            # Save HTML file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            return True
        except Exception as e:
            print(f"Error saving HTML report: {str(e)}")
            return False

    def _build_connection_map(self, links: List[Any]) -> Dict[str, Dict[str, List[str]]]:
        """
        Build a map of input and output connections for nodes
        
        Args:
            links: Workflow links
            
        Returns:
            dict: Map with node_id keys and input/output connections
        """
        connections = {}
        
        for link in links:
            # Handle different link formats
            
            # Format: [id, from_node, from_slot, to_node, to_slot]
            if len(link) >= 5:
                from_node = link[1]
                from_slot = link[2]
                to_node = link[3]
                to_slot = link[4]
            # Format: [from_node, from_slot, to_node, to_slot]
            elif len(link) >= 4:
                from_node = link[0]
                from_slot = link[1]
                to_node = link[2]
                to_slot = link[3]
            else:
                continue
            
            # Initialize connection entries if needed
            if from_node not in connections:
                connections[from_node] = {'inputs': [], 'outputs': []}
            if to_node not in connections:
                connections[to_node] = {'inputs': [], 'outputs': []}
            
            # Record connections
            connections[from_node]['outputs'].append((to_node, to_slot))
            connections[to_node]['inputs'].append((from_node, from_slot))
        
        return connections

    def _resolve_node_value(self, node_id: str, nodes: Dict[str, Any], connections: Dict[str, Dict[str, List[str]]]) -> Any:
        """
        Resolve a node's primary value based on its type
        
        Args:
            node_id: ID of the node
            nodes: All nodes in the workflow
            connections: Connection map
            
        Returns:
            Any: The resolved value
        """
        if node_id not in nodes:
            return None
            
        node = nodes[node_id]
        class_type = node.get('class_type', '')
        inputs = node.get('inputs', {})
        
        # Handle common value-providing nodes
        if class_type in ['CheckpointLoader', 'CheckpointLoaderSimple']:
            return inputs.get('ckpt_name')
        elif class_type == 'VAELoader':
            return inputs.get('vae_name')
        elif class_type == 'LoraLoader':
            return inputs.get('lora_name')
        elif class_type == 'CLIPTextEncode':
            return inputs.get('text')
        elif class_type in ['PrimitiveNode', 'IntegerNode', 'FloatNode']:
            return inputs.get('value')
        elif class_type == 'StringNode':
            return inputs.get('string')
        
        # For value selector nodes
        elif class_type in ['SamplerNode', 'SchedulerNode', 'ModelSelector']:
            for key in ['value', 'selected', 'option', 'sampler_name', 'scheduler_name']:
                if key in inputs:
                    return inputs[key]
        
        # For more complex nodes that reference other nodes, follow the reference
        for input_name, value in inputs.items():
            if isinstance(value, list) and len(value) == 2:
                # This is a reference to another node's output
                ref_node_id, ref_slot = value
                if ref_node_id in nodes:
                    return self._resolve_node_value(ref_node_id, nodes, connections)
        
        # Default - return the node class type
        return class_type

    def _resolve_linked_value(self, link_ref: List[Any], nodes: Dict[str, Any], connections: Dict[str, Dict[str, List[str]]]) -> Any:
        """
        Resolve a linked value from a node reference
        
        Args:
            link_ref: Link reference [node_id, slot]
            nodes: All nodes in the workflow
            connections: Connection map
            
        Returns:
            Any: The resolved value
        """
        if not isinstance(link_ref, list) or len(link_ref) != 2:
            return link_ref
            
        node_id, slot = link_ref
        return self._resolve_node_value(node_id, nodes, connections)

    def _process_node(self, node: Dict[str, Any], node_id: str, node_type: str, 
                    collections: Dict[str, List], connections: Dict[str, Dict[str, List[str]]]):
        """Process a single node and extract its metadata"""
        # Track discoveries if in discovery mode
        if self.discovery_mode:
            self._track_node_discovery(node_type, node)
            
        # Process node by type rather than by ID
        inputs = node.get('inputs', {})
        
        # Handle checkpoint/model nodes
        if 'checkpoint' in node_type.lower() or 'model' in node_type.lower():
            # Look for common checkpoint parameter names
            for param in ['ckpt_name', 'model_name', 'checkpoint', 'model_path']:
                if param in inputs:
                    value = inputs[param]
                    
                    # Resolve references if needed
                    if isinstance(value, list) and len(value) == 2:
                        value = self._resolve_linked_value(value, self.nodes, connections)
                        
                    model_info = {
                        'name': value,
                        'node_type': node_type
                    }
                    collections['models'].append(model_info)
                    break
        
        # Handle VAE nodes
        elif 'vae' in node_type.lower():
            # Look for common VAE parameter names
            for param in ['vae_name', 'vae']:
                if param in inputs:
                    value = inputs[param]
                    
                    # Resolve references if needed
                    if isinstance(value, list) and len(value) == 2:
                        value = self._resolve_linked_value(value, self.nodes, connections)
                        
                    vae_info = {
                        'name': value,
                        'node_type': node_type
                    }
                    collections['vae_models'].append(vae_info)
                    break
        
        # Handle LoRA nodes
        elif 'lora' in node_type.lower():
            # Look for common LoRA parameters
            lora_name = None
            for param in ['lora_name', 'name']:
                if param in inputs:
                    value = inputs[param]
                    
                    # Resolve references if needed
                    if isinstance(value, list) and len(value) == 2:
                        value = self._resolve_linked_value(value, self.nodes, connections)
                        
                    lora_name = value
                    break
                    
            if lora_name:
                lora_info = {
                    'name': lora_name,
                    'node_type': node_type
                }
                
                # Extract strength parameters
                for strength_param in ['strength', 'strength_model', 'model_strength']:
                    if strength_param in inputs:
                        value = inputs[strength_param]
                        
                        # Resolve references if needed
                        if isinstance(value, list) and len(value) == 2:
                            value = self._resolve_linked_value(value, self.nodes, connections)
                            
                        lora_info['strength_model'] = value
                        break
                        
                for clip_param in ['clip_strength', 'strength_clip']:
                    if clip_param in inputs:
                        value = inputs[clip_param]
                        
                        # Resolve references if needed
                        if isinstance(value, list) and len(value) == 2:
                            value = self._resolve_linked_value(value, self.nodes, connections)
                            
                        lora_info['strength_clip'] = value
                        break
                        
                collections['loras'].append(lora_info)
        
        # Handle sampler nodes
        elif 'sampler' in node_type.lower() or 'ksampler' in node_type.lower():
            sampler_info = {
                'node_type': node_type
            }
            
            # Map common sampler parameters
            param_mapping = {
                'sampler': ['sampler_name', 'sampler'],
                'scheduler': ['scheduler', 'schedule'],
                'steps': ['steps', 'max_steps'],
                'cfg_scale': ['cfg', 'cfg_scale', 'guidance_scale'],
                'seed': ['seed', 'noise_seed'],
                'denoise': ['denoise', 'denoise_strength', 'strength']
            }
            
            for output_key, input_keys in param_mapping.items():
                for input_key in input_keys:
                    if input_key in inputs:
                        value = inputs[input_key]
                        
                        # Resolve references if needed
                        if isinstance(value, list) and len(value) == 2:
                            value = self._resolve_linked_value(value, self.nodes, connections)
                            
                        sampler_info[output_key] = value
                        break
            
            collections['samplers'].append(sampler_info)
        
        # Handle text prompt nodes
        elif 'text' in node_type.lower() and 'encode' in node_type.lower():
            if 'text' in inputs:
                value = inputs['text']
                
                # Resolve references if needed
                if isinstance(value, list) and len(value) == 2:
                    value = self._resolve_linked_value(value, self.nodes, connections)
                
                is_negative = False
                
                # Check explicit negative flag
                if 'is_negative' in node and node['is_negative']:
                    is_negative = True
                
                # Check title for "negative" hints
                if '_meta' in node and 'title' in node['_meta']:
                    title = node['_meta']['title'].lower()
                    if 'negative' in title or 'neg' in title:
                        is_negative = True
                
                # Store in appropriate collection
                if is_negative:
                    collections['negative_prompts'].append({
                        'text': value,
                        'node_type': node_type
                    })
                else:
                    collections['prompts'].append({
                        'text': value,
                        'node_type': node_type
                    })

    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get summary of discovered node types and parameters"""
        return {
            'node_types': sorted(list(self.discovered_node_types)),
            'parameters': {node: sorted(list(params)) 
                        for node, params in self.discovered_parameters.items()},
            'log': self.discovery_log
        }

    def save_discovery_report(self, filepath: str) -> bool:
        """Save discovery information to a JSON file
        
        Args:
            filepath: Path to save the discovery report
            
        Returns:
            bool: True if successful
        """
        if not self.discovery_mode:
            return False
        
        try:
            import json
            
            # Format the report
            report = {
                'timestamp': datetime.datetime.now().isoformat(),
                'discovered_node_types': sorted(list(self.discovered_node_types)),
                'parameter_mappings': {
                    node: sorted(list(params)) 
                    for node, params in self.discovered_parameters.items()
                },
                'discovery_log': self.discovery_log
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving discovery report: {str(e)}")
            return False
    def _prioritize_parameters(self, collections: Dict[str, List], 
                            connections: Dict[str, Dict]) -> Dict[str, Any]:
        """Select primary parameters from collections based on connections"""
        params = {}
        
        # Process models - prefer the one with most output connections
        if collections['models']:
            primary_model = self._find_primary_node(collections['models'], connections, 'outputs')
            params['model'] = primary_model.get('name')
        
        # Process samplers - similar approach
        if collections['samplers']:
            primary_sampler = self._find_primary_node(collections['samplers'], connections, 'outputs')
            # Add sampler parameters to result
            for key, value in primary_sampler.items():
                if key not in ['node_id', 'node_type']:
                    params[key] = value
        
        # Process prompts
        positive_prompts = [p['text'] for p in collections['prompts']]
        negative_prompts = [p['text'] for p in collections['negative_prompts']]
        
        if positive_prompts:
            params['prompt'] = "\n".join(positive_prompts)
        if negative_prompts:
            params['negative_prompt'] = "\n".join(negative_prompts)
        
        # Process VAEs
        if collections['vae_models']:
            primary_vae = collections['vae_models'][0]  # Usually only one VAE
            params['vae'] = primary_vae.get('name')
        
        # Process LoRAs - include all as a list
        if collections['loras']:
            params['loras'] = collections['loras']
        
        return params
    def _track_parameter_discovery(self, node_type: str, param_key: str, 
                                param_value: Any) -> None:
        """Track parameter data types and example values"""
        if not self.discovery_mode:
            return
            
        # Ensure containers exist
        if node_type not in self.discovered_parameters:
            self.discovered_parameters[node_type] = {}
        
        if param_key not in self.discovered_parameters[node_type]:
            self.discovered_parameters[node_type][param_key] = {
                'type': type(param_value).__name__,
                'examples': []
            }
        
        # Track data type
        param_type = type(param_value).__name__
        current_type = self.discovered_parameters[node_type][param_key]['type']
        
        # Update type if different (track type variations)
        if param_type != current_type and param_type not in current_type.split('/'):
            self.discovered_parameters[node_type][param_key]['type'] = f"{current_type}/{param_type}"
        
        # Store example values (up to 3 unique examples)
        examples = self.discovered_parameters[node_type][param_key]['examples']
        example_value = str(param_value)
        
        # Truncate very long examples
        if len(example_value) > 100:
            example_value = example_value[:97] + "..."
            
        if len(examples) < 3 and example_value not in examples:
            examples.append(example_value)

    def _track_node_discovery(self, node_type: str, node: Dict[str, Any]) -> None:
        """Track discovered node types and their parameters with frequencies"""
        if not self.discovery_mode:
            return
        
        # Track node type frequency
        if node_type not in self.node_type_frequencies:
            self.node_type_frequencies[node_type] = 0
        self.node_type_frequencies[node_type] += 1
        
        # Track node type if not already seen
        if node_type not in self.discovered_node_types:
            self.discovered_node_types.add(node_type)
            self.discovery_log.append(f"Discovered new node type: {node_type}")
            
        # Track parameters for this node type
        inputs = node.get('inputs', {})
        if inputs:
            if node_type not in self.discovered_parameters:
                self.discovered_parameters[node_type] = {}
            
            # Add all parameter keys
            for param_key, param_value in inputs.items():
                # Track parameter
                self._track_parameter_discovery(node_type, param_key, param_value)
                
                # Track parameter frequency
                param_id = f"{node_type}.{param_key}"
                if param_id not in self.parameter_frequencies:
                    self.parameter_frequencies[param_id] = 0
                self.parameter_frequencies[param_id] += 1   

    def _find_primary_node(self, nodes: List[Dict[str, Any]], 
                        connections: Dict[str, Dict], 
                        connection_type: str) -> Dict[str, Any]:
        """Find the primary node based on connection count"""
        # Default to first node
        if not nodes:
            return {}
        
        primary = nodes[0]
        max_connections = 0
        
        for node in nodes:
            node_id = node.get('node_id')
            if node_id in connections:
                conn_count = len(connections[node_id].get(connection_type, []))
                if conn_count > max_connections:
                    max_connections = conn_count
                    primary = node
        
        return primary
    def _process_checkpoint_node(self, node, node_id, inputs, collections, connections):
        """Process checkpoint loader nodes"""
        # Find the checkpoint name from any of the possible keys
        ckpt_name = None
        for key in ['ckpt_name', 'model_name', 'checkpoint']:
            if key in inputs:
                ckpt_name = inputs[key]
                break
        
        if ckpt_name:
            model_info = {
                'name': ckpt_name,
                'node_id': node_id,
                'node_type': node.get('class_type', '')
            }
            collections['models'].append(model_info)

    def _process_sampler_node(self, node, node_id, inputs, collections, connections):
        """Process sampler nodes"""
        sampler_info = {
            'node_id': node_id,
            'node_type': node.get('class_type', '')
        }
        
        # Map the parameters using consistent names
        param_mapping = {
            'sampler_name': 'sampler',
            'scheduler': 'scheduler',
            'steps': 'steps',
            'cfg': 'cfg_scale',
            'seed': 'seed',
            'denoise': 'denoise'
        }
        
        for input_key, output_key in param_mapping.items():
            if input_key in inputs:
                sampler_info[output_key] = inputs[input_key]
        
        collections['samplers'].append(sampler_info)

    def load_central_discovery_data(self, filepath: str) -> bool:
        """
        Load discovery data from a central file and merge with current data
        
        Args:
            filepath: Path to the central discovery file
            
        Returns:
            bool: True if successful
        """
        if not os.path.exists(filepath):
            self.discovery_log.append(f"Central discovery file {filepath} not found, will create new")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update discovery data structures
            discovered_node_types = set(data.get('discovered_node_types', []))
            self.discovered_node_types.update(discovered_node_types)
            
            # FIXED: Load node type frequencies rather than adding to current
            # This prevents the exponential growth issue
            if 'node_type_frequencies' in data:
                existing_frequencies = data.get('node_type_frequencies', {})
                
                # For each node type in our current data, increment the count by 1
                # if it's a new observation
                for node_type in self.discovered_node_types:
                    if node_type not in existing_frequencies:
                        existing_frequencies[node_type] = 0
                    existing_frequencies[node_type] += 1
                    
                # Replace our frequencies with the updated values
                self.node_type_frequencies = existing_frequencies
            else:
                # Initialize frequencies if not present in the data
                self.node_type_frequencies = {node_type: 1 for node_type in self.discovered_node_types}
            
            # Update parameter mappings
            for node_type, params in data.get('discovered_parameters', {}).items():
                if node_type not in self.discovered_parameters:
                    self.discovered_parameters[node_type] = {}
                
                # Handle params whether it's a set or dict
                if isinstance(params, dict):
                    for param_key, param_data in params.items():
                        self.discovered_parameters[node_type][param_key] = param_data
                else:
                    # Convert set to dict format for consistency
                    for param_key in params:
                        if param_key not in self.discovered_parameters[node_type]:
                            self.discovered_parameters[node_type][param_key] = {
                                'type': 'unknown',
                                'examples': []
                            }
            
            # FIXED: Handle parameter frequencies similarly
            if 'parameter_frequencies' in data:
                existing_param_frequencies = data.get('parameter_frequencies', {})
                
                # For newly observed parameters, increment by 1
                for node_type, params in self.discovered_parameters.items():
                    param_keys = params.keys() if isinstance(params, dict) else params
                    for param_key in param_keys:
                        param_id = f"{node_type}.{param_key}"
                        if param_id not in existing_param_frequencies:
                            existing_param_frequencies[param_id] = 0
                        existing_param_frequencies[param_id] += 1
                        
                # Replace our frequencies with the updated values
                self.parameter_frequencies = existing_param_frequencies
            else:
                # Initialize parameter frequencies if not present
                self.parameter_frequencies = {}
                for node_type, params in self.discovered_parameters.items():
                    param_keys = params.keys() if isinstance(params, dict) else params
                    for param_key in param_keys:
                        self.parameter_frequencies[f"{node_type}.{param_key}"] = 1
            
            # Update connection patterns (keeping this as-is)
            for pattern, count in data.get('connection_patterns', {}).items():
                if pattern in self.connection_patterns:
                    self.connection_patterns[pattern] += count
                else:
                    self.connection_patterns[pattern] = count
            
            # Log the load
            self.discovery_log.append(f"Loaded discovery data from central file {filepath}")
            
            return True
        except Exception as e:
            print(f"Error loading central discovery data: {str(e)}")
            self.discovery_log.append(f"Error loading central discovery data: {str(e)}")
            return False

    def save_central_discovery_data(self, filepath: str) -> bool:
        """
        Save combined discovery data to a central file
        
        Args:
            filepath: Path to the central discovery file
            
        Returns:
            bool: True if successful
        """
        try:
            # Create report data
            report = {
                'timestamp': datetime.datetime.now().isoformat(),
                'discovered_node_types': sorted(list(self.discovered_node_types)),
                'node_type_frequencies': self.node_type_frequencies,
                'discovered_parameters': self.discovered_parameters,
                'parameter_frequencies': self.parameter_frequencies,
                'connection_patterns': self.connection_patterns,
                'discovery_log': self.discovery_log[-100:]  # Keep only last 100 log entries
            }
            
            # Make directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write report
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
                
            # Log the save
            self.discovery_log.append(f"Saved discovery data to central file {filepath}")
            
            return True
        except Exception as e:
            print(f"Error saving central discovery data: {str(e)}")
            self.discovery_log.append(f"Error saving central discovery data: {str(e)}")
            return False
    def _extract_from_extra_pnginfo(self, extra_pnginfo):
        """Extract data from extra_pnginfo"""
        workflow_info = {}
        
        # Skip if not a dictionary
        if not isinstance(extra_pnginfo, dict):
            return workflow_info
            
        # Extract workflow metadata
        if 'workflow' in extra_pnginfo:
            workflow = extra_pnginfo['workflow']
            if isinstance(workflow, dict):
                # Version information
                if 'version' in workflow:
                    workflow_info['version'] = workflow['version']
                
                # Extract node and link counts
                if 'nodes' in workflow:
                    workflow_info['node_count'] = len(workflow['nodes'])
                if 'links' in workflow:
                    workflow_info['link_count'] = len(workflow['links'])
        
        # Extract dimension information
        for size_key in ['resolution', 'width', 'height']:
            if size_key in extra_pnginfo:
                workflow_info[size_key] = extra_pnginfo[size_key]
        
        # Extract any other useful metadata
        for key in ['comfy_version', 'workflow_name', 'created_by']:
            if key in extra_pnginfo:
                workflow_info[key] = extra_pnginfo[key]
                
        return workflow_info
    def _process_clip_text_encode_node(self, node, node_id, inputs, collections, connections):
        """Process text encoding nodes"""
        if 'text' not in inputs:
            return
        
        # Determine if negative prompt
        is_negative = node.get('is_negative', False)
        
        # Also check title if available
        meta = node.get('_meta', {})
        if meta and 'title' in meta:
            title = meta['title'].lower()
            if 'negative' in title:
                is_negative = True
        
        prompt_info = {
            'text': inputs['text'],
            'node_id': node_id,
            'node_type': node.get('class_type', '')
        }
        
        if is_negative:
            collections['negative_prompts'].append(prompt_info)
        else:
            collections['prompts'].append(prompt_info)
    def _build_node_connections(self, prompt, extra_pnginfo=None):
        """Build a graph of node connections"""
        connections = {}
        
        # Initialize connection tracking for each node
        for node_id in prompt:
            connections[node_id] = {
                'inputs': [],
                'outputs': []
            }
        
        # Process connections from extra_pnginfo if available
        if extra_pnginfo and 'workflow' in extra_pnginfo:
            workflow = extra_pnginfo['workflow']
            if isinstance(workflow, dict) and 'links' in workflow:
                links = workflow['links']
                
                for link in links:
                    # Check if link is a list (the format in your ComfyUI)
                    if isinstance(link, list) and len(link) >= 4:
                        # Format appears to be [from_node, from_output, to_node, to_input]
                        from_node, _, to_node, _ = link[:4]
                    elif isinstance(link, dict):
                        # The originally expected dictionary format
                        from_node = link.get('from_node')
                        to_node = link.get('to_node')
                    else:
                        # Unknown format, skip this link
                        continue
                    
                    if from_node and to_node:
                        if from_node not in connections:
                            connections[from_node] = {'inputs': [], 'outputs': []}
                        if to_node not in connections:
                            connections[to_node] = {'inputs': [], 'outputs': []}
                            
                        connections[from_node]['outputs'].append(to_node)
                        connections[to_node]['inputs'].append(from_node)
        
        # Process connections from prompt inputs
        for node_id, node in prompt.items():
            if isinstance(node, dict) and 'inputs' in node:
                inputs = node['inputs']
                for input_key, input_value in inputs.items():
                    if isinstance(input_value, list) and len(input_value) == 2:
                        # The first element is the source node ID
                        from_node = input_value[0]
                        
                        if from_node in connections:
                            connections[from_node]['outputs'].append(node_id)
                        else:
                            connections[from_node] = {
                                'inputs': [],
                                'outputs': [node_id]
                            }
                        
                        connections[node_id]['inputs'].append(from_node)
        
        return connections
