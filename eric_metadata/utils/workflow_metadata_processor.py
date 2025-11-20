"""
workflow_metadata_processor.py
================================
Description: Comprehensive workflow metadata processor that extracts, analyzes, and formats
    workflow data from ComfyUI and other AI image generators.
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

"""
# Enhanced WorkflowMetadataProcessor with unified extraction logic
# Metadata_system/eric_metadata/workflow_metadata.py
import os
import json
import datetime
import re
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
import numpy as np
import xml.etree.ElementTree as ET
import io
import traceback  # For detailed error tracking in debug mode
import numpy as np
from PIL import Image

try:
    import folder_paths  # type: ignore
except ImportError:  # pragma: no cover - ComfyUI runtime provides this
    folder_paths = None

from .hash_utils import hash_file_sha256

from ..workflow import WorkflowParsingService, SamplerCandidate, PromptNodeRef


def _normalise_asset_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()

class WorkflowMetadataProcessor:
    """
    Comprehensive workflow metadata processor that extracts, analyzes, and formats
    workflow data from ComfyUI and other AI image generators.
    
    This class serves as the unified extraction engine for workflow data,
    providing a single source of truth for extraction logic and consistent output.
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
        
        # Cache for recently processed workflows
        self.extraction_cache = {}

        # Focused helpers for prompt parsing and traversal
        self._parsing_service = WorkflowParsingService(debug=debug)
        
        # Track discovered node types if in discovery mode
        if discovery_mode:
            self.discovered_node_types = set()
            self.node_type_frequencies = {}
            self.parameter_frequencies = {}
            self.discovery_log = []

    def _resolve_model_path(self, value: Optional[Union[str, Path]]) -> Optional[str]:
        """Attempt to resolve a model reference to an on-disk file path."""

        if value is None:
            return None

        if isinstance(value, Path):
            candidate_path = value.expanduser()
            if candidate_path.is_file():
                return str(candidate_path)
            value = str(candidate_path)

        if not isinstance(value, str):
            return None

        candidate = value.strip()
        if not candidate or candidate.lower() == "none":
            return None

        expanded = os.path.expanduser(candidate)

        potential_paths: List[Path] = []

        # Direct absolute reference
        path_obj = Path(expanded)
        if path_obj.is_file():
            return str(path_obj)

        # Relative path with separators
        if any(sep in candidate for sep in ("\\", "/")):
            relative_candidate = Path(candidate)
            if relative_candidate.is_file():
                return str(relative_candidate.resolve())
            potential_paths.append(Path.cwd() / relative_candidate)

        # Try folder_paths lookup when available
        if folder_paths is not None:
            folder_map = getattr(folder_paths, "folder_names_and_paths", {})
            for folder_type in folder_map.keys():
                try:
                    resolved = folder_paths.get_full_path(folder_type, candidate)
                except Exception:
                    resolved = None

                if resolved:
                    resolved_path = Path(resolved)
                    if resolved_path.is_file():
                        return str(resolved_path)

        # Fall back to first existing potential path
        for potential in potential_paths:
            if potential.is_file():
                return str(potential.resolve())

        return None

    def _populate_model_metadata(self, metadata: Dict[str, Any], enable_hash_cache: bool) -> None:
        """Enrich extracted metadata with model paths and SHA256 hashes."""

        if not isinstance(metadata, dict):
            return

        ai_info = metadata.get("ai_info")
        if not isinstance(ai_info, dict):
            return

        generation = ai_info.get("generation")
        if not isinstance(generation, dict):
            return

        base_model = generation.get("base_model")
        if not isinstance(base_model, dict):
            base_model = {}
            generation["base_model"] = base_model

        # Collect candidate references for path resolution
        path_candidates: List[Optional[Union[str, Path]]] = [
            base_model.get("path"),
            base_model.get("full_path"),
            base_model.get("model_path"),
            base_model.get("ckpt_path"),
        ]

        name_candidates = [
            base_model.get("name"),
            base_model.get("model"),
            base_model.get("unet"),
            base_model.get("ckpt_name"),
            generation.get("model"),
        ]

        path_value: Optional[str] = None

        for candidate in path_candidates:
            path_value = self._resolve_model_path(candidate)
            if path_value:
                break

        if not path_value:
            for candidate in name_candidates:
                path_value = self._resolve_model_path(candidate)
                if path_value:
                    break

        if not path_value:
            if self.debug:
                print("[WorkflowMetadataProcessor] Unable to resolve base model path for hashing")
            return

        path_obj = Path(path_value)
        if not path_obj.is_file():
            return

        if not base_model.get("name"):
            for candidate in name_candidates:
                if isinstance(candidate, str) and candidate.strip() and candidate.lower() != "none":
                    base_model["name"] = candidate.strip()
                    break
            else:
                base_model["name"] = path_obj.name

        digest = hash_file_sha256(path_obj, use_cache=enable_hash_cache)
        if not digest:
            return

        short_digest = digest[:8]

        base_model["path"] = str(path_obj)
        base_model["sha256"] = digest
        base_model["checksum"] = digest
        base_model["model_hash_sha256"] = digest
        base_model["hash"] = short_digest
        base_model["model_hash"] = short_digest
        base_model["short_hash"] = short_digest

        generation["model_hash"] = short_digest
        generation["model_hash_sha256"] = digest

        if self.debug:
            print(
                f"[WorkflowMetadataProcessor] Computed base model hash {short_digest} from {path_obj.name}"
            )
    
    def extract_from_source(self, source_type: str, source_data: Any) -> Dict[str, Any]:
        """
        Unified extraction method that handles different source types.
        
        Args:
            source_type: Type of source ('file', 'image', 'tensor', 'dict', etc.)
            source_data: The raw source data to extract from
            
        Returns:
            dict: {
                'workflow': Raw workflow data dictionary,
                'source': Identified source type (comfyui, automatic1111, etc.),
                'error': Error message if extraction failed,
                'metadata': Any additional metadata about the extraction
            }
        """
        try:
            # Check cache first if applicable
            cache_key = self._get_cache_key(source_type, source_data)
            if cache_key and cache_key in self.extraction_cache:
                if self.debug:
                    print(f"[WorkflowMetadataProcessor] Using cached workflow data for {cache_key}")
                return self.extraction_cache[cache_key]
            
            # Extract based on source type
            if source_type == 'file':
                result = self._extract_from_file(source_data)
            elif source_type == 'image':
                result = self._extract_from_pil_image(source_data)
            elif source_type == 'tensor':
                result = self._extract_from_tensor(source_data)
            elif source_type == 'dict':
                result = {
                    'workflow': source_data,
                    'source': self._identify_workflow_source(source_data)
                }
            else:
                return {'error': f"Unsupported source type: {source_type}"}
            
            # Cache the result if successful and has a cache key
            if cache_key and 'workflow' in result and not result.get('error'):
                self.extraction_cache[cache_key] = result
                
            return result
            
        except Exception as e:
            error_msg = f"Error extracting workflow from {source_type}: {str(e)}"
            if self.debug:
                import traceback
                print(f"[WorkflowMetadataProcessor] {error_msg}")
                traceback.print_exc()
            return {'error': error_msg}
    
    def _extract_from_file(self, filepath: str) -> Dict[str, Any]:
        """
        Extract workflow data from a file.
        
        Args:
            filepath: Path to the file to extract from
            
        Returns:
            dict: Extraction result with workflow data and metadata
        """
        if not filepath or not os.path.exists(filepath):
            return {'error': f"File not found: {filepath}"}
            
        try:
            # Determine file type from extension
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                # Handle image file formats
                from PIL import Image
                try:
                    with Image.open(filepath) as img:
                        return self._extract_from_pil_image(img, filepath)
                except Exception as e:
                    return {'error': f"Failed to open image file: {str(e)}"}
            
            elif ext == '.json':
                # Handle JSON workflow file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    return {
                        'workflow': workflow_data,
                        'source': self._identify_workflow_source(workflow_data),
                        'metadata': {'origin': 'json_file'}
                    }
                except Exception as e:
                    return {'error': f"Failed to parse JSON file: {str(e)}"}
            
            else:
                return {'error': f"Unsupported file type: {ext}"}
                
        except Exception as e:
            return {'error': f"Error extracting from file: {str(e)}"}
    
    def _extract_from_pil_image(self, img, filepath=None) -> Dict[str, Any]:
        """
        Extract workflow data from a PIL Image.
        
        Args:
            img: PIL Image object
            filepath: Optional original filepath for reference
            
        Returns:
            dict: Extraction result with workflow data and metadata
        """
        try:
            # Check for various metadata fields where workflow might be stored
            for field in ['parameters', 'workflow', 'prompt']:
                if field in img.info:
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(img.info[field], str) or isinstance(img.info[field], bytes):
                            data = img.info[field]
                            if isinstance(data, bytes):
                                data = data.decode('utf-8')
                            workflow_data = json.loads(data)
                            workflow_source = self._identify_workflow_source(workflow_data)
                            return {
                                'workflow': workflow_data,
                                'source': workflow_source,
                                'metadata': {
                                    'origin': 'image_metadata',
                                    'field': field
                                }
                            }
                        elif isinstance(img.info[field], dict):
                            # Already a dict
                            workflow_data = img.info[field]
                            workflow_source = self._identify_workflow_source(workflow_data)
                            return {
                                'workflow': workflow_data,
                                'source': workflow_source,
                                'metadata': {
                                    'origin': 'image_metadata',
                                    'field': field
                                }
                            }
                    except json.JSONDecodeError:
                        # If it's not valid JSON, try A1111-style parameter parsing
                        if field == 'parameters':
                            try:
                                params = img.info[field]
                                if isinstance(params, bytes):
                                    params = params.decode('utf-8')
                                    
                                # Parse A1111 format
                                workflow_data = self._parse_a1111_parameters(params)
                                return {
                                    'workflow': workflow_data,
                                    'source': 'automatic1111',
                                    'metadata': {
                                        'origin': 'image_metadata',
                                        'field': field,
                                        'format': 'a1111_text'
                                    }
                                }
                            except Exception as parse_e:
                                if self.debug:
                                    print(f"[WorkflowMetadataProcessor] A1111 parsing failed: {str(parse_e)}")
            
            # If we get here, no workflow data was found
            return {'error': "No workflow data found in image metadata"}
            
        except Exception as e:
            return {'error': f"Error extracting from image: {str(e)}"}
    
    def _extract_from_tensor(self, tensor) -> Dict[str, Any]:
        """
        Extract workflow data from a tensor (e.g., from ComfyUI).
        
        Args:
            tensor: Image tensor
            
        Returns:
            dict: Extraction result with workflow data and metadata
        """
        try:
            # Convert tensor to PIL Image
            import numpy as np
            from PIL import Image
            
            # Handle different tensor formats
            if len(tensor.shape) == 4:  # [B,H,W,C]
                # Take first image if batched
                img_np = tensor[0].cpu().numpy()
            else:  # [H,W,C]
                img_np = tensor.cpu().numpy()
            
            # Convert to uint8 for PIL
            if img_np.dtype != np.uint8:
                img_np = (img_np * 255).clip(0, 255).astype(np.uint8)
            
            # Create PIL image
            pil_image = Image.fromarray(img_np)
            
            # Extract from PIL image
            return self._extract_from_pil_image(pil_image)
            
        except Exception as e:
            return {'error': f"Error extracting from tensor: {str(e)}"}
    
    def _parse_a1111_parameters(self, params_text: str) -> Dict[str, Any]:
        """
        Parse Automatic1111 style parameters text into structured data.
        
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
                
                # Split the remaining text to get negative prompt and parameters
                remaining = parts[1]
                param_start = remaining.find('Steps:')
                
                if param_start > 0:
                    result['negative_prompt'] = remaining[:param_start].strip()
                    param_text = remaining[param_start:]
                    
                    # Extract parameters using regex
                    import re
                    param_pattern = r'([a-zA-Z\s]+):\s*([^,]+)(?:,|$)'
                    for match in re.finditer(param_pattern, param_text):
                        key = match.group(1).strip().lower().replace(' ', '_')
                        value = match.group(2).strip()
                        
                        # Try to convert numeric values
                        try:
                            if '.' in value:
                                result[key] = float(value)
                            else:
                                result[key] = int(value)
                        except ValueError:
                            result[key] = value
                else:
                    result['negative_prompt'] = remaining.strip()
            else:
                result['prompt'] = params_text.strip()
                
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error parsing A1111 parameters: {str(e)}")
            result['parse_error'] = str(e)
            result['raw_params'] = params_text
            
        return result
    
    def analyze_workflow(self, workflow_data: Dict[str, Any], analysis_type: str = 'full') -> Dict[str, Any]:
        """
        Analyze workflow data to produce structured metadata.
        
        Args:
            workflow_data: Raw workflow data
            analysis_type: Type of analysis ('full', 'basic', 'technical', etc.)
            
        Returns:
            dict: Structured analysis results
        """
        try:
            if not workflow_data:
                return {'error': 'No workflow data to analyze'}
            
            # Determine workflow source if not already known
            workflow_source = self._identify_workflow_source(workflow_data)
            
            # Initialize result structure
            result = {
                'workflow_type': workflow_source,
                'generation': {},
                'workflow_info': {}
            }
            
            # Process based on workflow source
            if workflow_source == 'comfyui':
                self._analyze_comfyui_workflow(workflow_data, result, analysis_type)
            elif workflow_source in ['automatic1111', 'stable_diffusion_webui']:
                self._analyze_a1111_workflow(workflow_data, result, analysis_type)
            elif workflow_source == 'novelai':
                self._analyze_novelai_workflow(workflow_data, result, analysis_type)
            else:
                # Generic analysis for unknown workflow types
                self._analyze_generic_workflow(workflow_data, result, analysis_type)
            
            # Add workflow statistics if doing full analysis
            if analysis_type in ['full', 'technical']:
                stats = self._extract_workflow_statistics(workflow_data, workflow_source)
                if stats:
                    result['workflow_stats'] = stats
            
            # Format metadata for AI info structure
            metadata = {
                'ai_info': {
                    'generation': result.get('generation', {}),
                    'workflow_info': result.get('workflow_info', {}),
                    'workflow': workflow_data
                }
            }
            
            # Add structured workflow data
            result['metadata'] = metadata
            
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing workflow: {str(e)}"
            if self.debug:
                import traceback
                print(f"[WorkflowMetadataProcessor] {error_msg}")
                traceback.print_exc()
            return {'error': error_msg}
    
    def _analyze_comfyui_workflow(self, workflow_data: Dict[str, Any], result: Dict[str, Any], analysis_type: str) -> None:
        """
        Analyze ComfyUI workflow data and update the result dictionary.
        
        Args:
            workflow_data: Raw workflow data
            result: Result dictionary to update
            analysis_type: Type of analysis
        """
        # Get the nodes and connections
        prompt_data = workflow_data.get('prompt', {})
        if not prompt_data and isinstance(workflow_data, dict) and 'nodes' in workflow_data:
            prompt_data = workflow_data
            
        nodes = prompt_data.get('nodes', {})
        links = prompt_data.get('links', [])
        if not links and 'connections' in prompt_data:
            links = prompt_data.get('connections', [])
        
        # Store raw node data for reference
        result['raw_nodes'] = nodes
        
        # Extract prompts with proper analysis of connections
        self._extract_detailed_prompts(nodes, links, result)
        
        # Extract primary parameters
        self._extract_detailed_parameters(nodes, links, result)
        
        # NEW: Analyze node sources
        if analysis_type in ['full', 'technical']:
            node_sources = self._analyze_node_sources(nodes)
            if node_sources:
                # Add to workflow_info
                if 'workflow_info' not in result:
                    result['workflow_info'] = {}
                result['workflow_info']['node_sources'] = node_sources
        
        # Extract additional info depending on analysis type
        if analysis_type in ['full', 'technical']:
            # Extract dimensions
            dimensions = self._extract_latent_dimensions(nodes)
            if dimensions:
                result['generation'].update(dimensions)
            
            # Extract prompt-linked assets (LoRAs, embeddings)
            loras, embeddings = self._extract_lora_info(nodes, links)
            if loras:
                result['loras'] = loras
                generation = result.setdefault('generation', {})
                generation['loras'] = loras
            if embeddings:
                result['embeddings'] = embeddings
                generation = result.setdefault('generation', {})
                generation['embeddings'] = embeddings
            
            # Extract VAE info
            vae = self._extract_vae_info(nodes)
            if vae:
                result['generation']['vae'] = vae
        
        # Add workflow info
        workflow_name = self._find_workflow_name(workflow_data)
        if workflow_name:
            result['workflow_info']['name'] = workflow_name
            
        # Add timestamp
        if 'generation' in result and 'timestamp' not in result['generation']:
            import datetime
            result['generation']['timestamp'] = datetime.datetime.now().isoformat()
    
    def _analyze_a1111_workflow(self, workflow_data: Dict[str, Any], result: Dict[str, Any], analysis_type: str) -> None:
        """
        Analyze Automatic1111/SD-WebUI workflow data and update the result dictionary.
        
        Args:
            workflow_data: Raw workflow data
            result: Result dictionary to update
            analysis_type: Type of analysis
        """
        # Extract parameters directly - A1111 has a flatter structure
        generation = result.get('generation', {})
        
        # Map common A1111 parameters to our structure
        param_mapping = {
            'prompt': 'prompt',
            'negative_prompt': 'negative_prompt',
            'model': 'model',
            'sampler_name': 'sampler',
            'sampler': 'sampler',
            'steps': 'steps',
            'cfg_scale': 'cfg_scale',
            'seed': 'seed',
            'vae': 'vae',
            'width': 'width',
            'height': 'height',
            'denoising_strength': 'denoise'
        }
        
        # Add parameters to generation data
        for src_key, dest_key in param_mapping.items():
            if src_key in workflow_data and workflow_data[src_key] is not None:
                generation[dest_key] = workflow_data[src_key]
        
        # Add prompts to result structure
        if 'prompt' in workflow_data:
            if 'prompts' not in result:
                result['prompts'] = {'positive': [], 'negative': []}
            result['prompts']['positive'] = [workflow_data['prompt']]
            
        if 'negative_prompt' in workflow_data:
            if 'prompts' not in result:
                result['prompts'] = {'positive': [], 'negative': []}
            result['prompts']['negative'] = [workflow_data['negative_prompt']]
        
        # Set dimensions if width and height are available
        if 'width' in workflow_data and 'height' in workflow_data:
            try:
                width = int(workflow_data['width'])
                height = int(workflow_data['height'])
                generation['width'] = width
                generation['height'] = height
            except (ValueError, TypeError):
                pass
        
        # Extract additional special parameters
        for key in workflow_data:
            if key not in param_mapping:
                if key in ['lora', 'loras', 'lyco']:
                    # Handle LoRA information
                    self._extract_a1111_loras(workflow_data[key], result)
                elif key in ['controlnet', 'control_net', 'controlnets']:
                    # Handle ControlNet information
                    self._extract_a1111_controlnet(workflow_data[key], result)
                    
        # Set generation data back to result
        result['generation'] = generation
        
        # Add timestamp
        if 'timestamp' not in result['generation']:
            import datetime
            result['generation']['timestamp'] = datetime.datetime.now().isoformat()

    def _analyze_novelai_workflow(self, workflow_data: Dict[str, Any], result: Dict[str, Any], analysis_type: str) -> None:
        """
        Analyze NovelAI workflow data and update the result dictionary.
        
        Args:
            workflow_data: Raw workflow data
            result: Result dictionary to update
            analysis_type: Type of analysis
        """
        # NovelAI-specific analysis
        # This is a placeholder that should be implemented based on NovelAI workflow structure
        pass
        
    def _analyze_generic_workflow(self, workflow_data: Dict[str, Any], result: Dict[str, Any], analysis_type: str) -> None:
        """
        Generic analysis for unknown workflow types, extracting whatever parameters can be found.
        
        Args:
            workflow_data: Raw workflow data
            result: Result dictionary to update
            analysis_type: Type of analysis
        """
        # Look for common parameter names in any workflow structure
        common_params = {
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
        
        generation = result.get('generation', {})
        
        # Extract parameters by looking for common names
        self._extract_by_common_names(workflow_data, common_params, generation)
        
        # Store back to result
        result['generation'] = generation
        
    def _extract_by_common_names(self, data: Dict[str, Any], param_mapping: Dict[str, List[str]], target: Dict[str, Any]) -> None:
        """
        Extract parameters from data by checking common parameter names.
        
        Args:
            data: Data dictionary to extract from
            param_mapping: Mapping of target keys to possible source key names
            target: Target dictionary to update with found values
        """
        # Recursive function to search for parameters
        def search_dict(d, depth=0):
            # Limit recursion depth to avoid stack overflow
            if depth > 10:
                return
                
            if isinstance(d, dict):
                for key, value in d.items():
                    # Check if this key matches any of our target parameters
                    for target_key, possible_keys in param_mapping.items():
                        if key in possible_keys and target_key not in target:
                            target[target_key] = value
                    
                    # Recurse into nested dictionaries
                    if isinstance(value, dict):
                        search_dict(value, depth + 1)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                search_dict(item, depth + 1)
        
        # Start recursive search
        search_dict(data)
    
    def _extract_detailed_prompts(self, nodes: Dict[str, Any], links: List[Any], result: Dict[str, Any]) -> None:
        """Extract prompts and update ``result`` using the parsing service."""

        workflow_stub = {
            'prompt': {
                'nodes': nodes,
                'links': links,
            }
        }

        parsed_prompts = self._parsing_service.parse_prompts(workflow_stub)

        if 'prompts' not in result:
            result['prompts'] = {'positive': [], 'negative': []}

        workflow_info = result.setdefault('workflow_info', {})
        positive_prompts: List[str] = []
        negative_prompts: List[str] = []
        ranked_metadata: List[Dict[str, Any]] = []

        best_sampler = self._select_best_sampler_candidate(workflow_stub)
        if best_sampler:
            trace_map = self._parsing_service.trace_from_node(
                workflow_stub,
                best_sampler.node_id,
                direction='backward',
            )
            if trace_map:
                workflow_info.setdefault('node_distances', trace_map)

            prompt_nodes = self._find_connected_text_nodes(
                workflow_stub,
                best_sampler.node_id,
                max_depth=5,
                min_length=5,
            )

            for node_ref in prompt_nodes:
                text_value = self._select_prompt_text(node_ref.texts)
                if not text_value:
                    continue

                metadata_entry = {
                    'node_id': node_ref.node_id,
                    'class_type': node_ref.class_type,
                    'distance': node_ref.distance,
                    'text': text_value,
                    'is_negative': node_ref.is_negative,
                }
                if node_ref.sources:
                    metadata_entry['sources'] = node_ref.sources
                ranked_metadata.append(metadata_entry)

                if node_ref.is_negative:
                    negative_prompts.append(text_value)
                else:
                    positive_prompts.append(text_value)

                if self.discovery_mode:
                    self.discovery_log.append(
                        {
                            'event': 'prompt_discovery',
                            'sampler_anchor': best_sampler.node_id,
                            'node_id': node_ref.node_id,
                            'distance': node_ref.distance,
                            'text_length': len(text_value),
                            'sources': node_ref.sources,
                        }
                    )

        if not (positive_prompts or negative_prompts):
            positive_prompts = [entry.text for entry in parsed_prompts.positive]
            negative_prompts = [entry.text for entry in parsed_prompts.negative]
            ranked_metadata = []

        # Deduplicate while preserving order
        positive_prompts = self._dedupe_preserve_order(positive_prompts)
        negative_prompts = self._dedupe_preserve_order(negative_prompts)

        result['prompts']['positive'] = positive_prompts
        result['prompts']['negative'] = negative_prompts

        generation = result.setdefault('generation', {})
        if positive_prompts:
            generation['prompt'] = '\n'.join(positive_prompts)
        else:
            generation.pop('prompt', None)
        if negative_prompts:
            generation['negative_prompt'] = '\n'.join(negative_prompts)
        else:
            generation.pop('negative_prompt', None)

        if ranked_metadata:
            generation['prompt_nodes'] = ranked_metadata
        else:
            generation.pop('prompt_nodes', None)
    
    def _extract_detailed_parameters(self, nodes: Dict[str, Any], links: List[Any], result: Dict[str, Any]) -> None:
        """
        Extract detailed parameters from nodes with improved connection tracing
        
        Args:
            nodes: Workflow nodes
            links: Workflow links
            result: Result dictionary to update
        """

        # Create a connection map for resolving references
        connection_map = self._build_connection_map(links)
    
        # Parameters to extract by node type
        node_mappings = {
            # Samplers
            'KSampler': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler',
                'steps': 'steps',
                'cfg_scale': 'cfg',
                'seed': 'seed',
                'denoise': 'denoise'
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
            # Add support for KSamplerSelect
            'KSamplerSelect': {
                'sampler': 'sampler_name',
                'scheduler': 'scheduler'
            },
            
            # Model loaders
            'CheckpointLoaderSimple': {
                'model': 'ckpt_name',
                'model_type': 'model_type'
            },
            'CheckpointLoader': {
                'model': 'ckpt_name'
            },
            'DiffusersLoader': {
                'model': 'model_path'
            },
            'UNETLoader': {
                'unet_model': 'unet_name'
            },
            'LoraLoader': {
                'lora_name': 'lora_name',
                'strength_model': 'strength_model',
                'strength_clip': 'strength_clip'
            },
            'Power Lora Loader (rgthree)': {
                'loras': 'lora_*',  # Special handling needed for this format
                'custom_handler': 'power_lora_loader'
            },
            'VAELoader': {
                'vae': 'vae_name'
            },
            'VAEDecoderLoad': {
                'vae': 'vae_name'
            },
            'ControlNetLoader': {
                'controlnet_models': 'control_net_name'
            },
            'ControlNetApply': {
                'controlnet_weights': 'strength'
            },
            'IPAdapterModelLoader': {
                'ip_adapter_models': 'ipadapter_file'
            },
            'StyleModelLoader': {
                'style_model': 'style_model_name'
            },
            'ModelSamplingFlux': {
                'flux_fraction': 'flux_frac',
                'flux_mode': 'flux_mode',
                'max_shift': 'max_shift',
                'base_shift': 'base_shift'
            },
            
            # Upscalers
            'UpscaleModelLoader': {
                'upscale_models': 'model_name'
            },
            
            # Latent dimensions
            'EmptyLatentImage': {
                'width': 'width',
                'height': 'height',
                'batch_size': 'batch_size'
            },
            'LatentUpscale': {
                'width': 'width',
                'height': 'height'
            },
            
            # Text prompts
            'CLIPTextEncode': {
                'prompt': 'text',
                'is_negative': 'is_negative'
            },
            'Text Multiline': {
                'prompt': 'text',
                'text': 'text'
            },
            'TextMultiline': {
                'prompt': 'text',
                'text': 'text'
            },
            'String': {
                'prompt': 'String',
                'text': 'String'
            },
            'Text': {
                'prompt': 'text',
                'text': 'text'
            },
            
            # Flux-specific nodes
            'FluxGuidance': {
                'guidance': 'guidance'
            }
        }
        
        # Initialize parameter storage (reuse existing generation data when available)
        generation = result.setdefault('generation', {})
        
        # Process each node by type
        for node_id, node in nodes.items():
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Special handling for Power Lora Loader before standard mapping
            if class_type == 'Power Lora Loader (rgthree)':
                if 'loras' not in generation:
                    generation['loras'] = []
                    
                # Parse the special Power Lora format
                for key, value in inputs.items():
                    if key.startswith('lora_') and isinstance(value, dict):
                        # Check if lora is enabled
                        if value.get('on', False) and value.get('lora'):
                            lora = {
                                'name': value['lora'],
                                'strength': value.get('strength', 1.0)
                            }
                            generation['loras'].append(lora)
                continue  # Skip standard processing for this node
            
            # Skip if node type not in mappings
            if class_type not in node_mappings:
                continue
                
            # Get parameter mapping for this node type
            mapping = node_mappings[class_type]
            
            # Extract values based on mapping
            for output_key, input_key in mapping.items():
                if input_key in inputs:
                    input_value = inputs[input_key]
                    
                    # Resolve linked values
                    if isinstance(input_value, list) and len(input_value) == 2:
                        resolved_value = self._resolve_linked_value(input_value, nodes, connection_map)
                        
                        # Skip empty or None values
                        if resolved_value is None or resolved_value == "":
                            continue
                            
                        # Use the resolved value
                        input_value = resolved_value

                    # Special handling for different parameter types
                    if class_type == 'LoraLoader' and output_key == 'lora_name':
                        # For LoRAs, maintain a list
                        if 'loras' not in generation:
                            generation['loras'] = []
                            
                        # Create LoRA entry
                        lora = {
                            'name': input_value,
                            'strength_model': inputs.get('strength_model', 1.0),
                            'strength_clip': inputs.get('strength_clip', 1.0)
                        }
                        generation['loras'].append(lora)
                        
                    elif (class_type == 'CLIPTextEncode' or 
                          'Text Multiline' in class_type or 
                          'TextMultiline' in class_type or
                          'String' in class_type or
                          'Text' in class_type) and output_key in ['prompt', 'text']:
                        # For prompts, determine if positive or negative
                        is_negative = inputs.get('is_negative', False)
                        
                        # Check node title for negative indicators
                        if '_meta' in node and 'title' in node['_meta']:
                            title = node['_meta']['title'].lower()
                            if 'negative' in title or 'neg' in title:
                                is_negative = True
                                
                        # Store in appropriate field
                        if is_negative:
                            generation['negative_prompt'] = input_value
                        else:
                            generation['prompt'] = input_value
                    
                    elif output_key.endswith('_models') or output_key.endswith('_weights'):
                        # For lists of models or weights, maintain arrays
                        if output_key not in generation:
                            generation[output_key] = []
                        generation[output_key].append(input_value)
                    
                    elif class_type == 'ModelSamplingFlux':
                        # Structure FLUX settings
                        if 'flux' not in generation:
                            generation['flux'] = {}
                        
                        if output_key in ['max_shift', 'base_shift']:
                            generation['flux'][output_key] = input_value
                        elif output_key == 'flux_fraction':
                            generation['flux']['fraction'] = input_value
                        elif output_key == 'flux_mode':
                            generation['flux']['mode'] = input_value
                    
                    elif class_type == 'FluxGuidance':
                        # Structure FLUX guidance settings
                        if 'flux' not in generation:
                            generation['flux'] = {}
                        
                        if output_key == 'guidance':
                            generation['flux']['guidance'] = input_value
                    
                    else:
                        # Standard parameter - store directly
                        generation[output_key] = input_value
        
        # Add to result
        if generation:
            if 'ai_info' not in result:
                result['ai_info'] = {}
            result['ai_info']['generation'] = generation
            
            # Post-process to ensure Text Multiline content becomes main prompt
            if 'text_inputs' in generation and 'multiline' in generation['text_inputs']:
                # If we don't already have a main prompt, use the multiline text
                if 'prompt' not in generation:
                    generation['prompt'] = generation['text_inputs']['multiline']
                    
            # Also add timestamp
            if 'timestamp' not in generation:
                import datetime
                generation['timestamp'] = datetime.datetime.now().isoformat()

        # Ensure sampler information is captured even for unknown node types
        self._fallback_sampler_detection(nodes, links, result)

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
                print(f"[WorkflowMetadataProcessor] Source node not found: {from_node_id}")
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
                
        # Return node class type if we can't resolve the value
        return f"{class_type}"
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
            # Standard ComfyUI link format [from_node, from_slot, to_node, to_slot]
            if len(link) == 4:
                from_node, from_slot, to_node, to_slot = link
                connection_map[(to_node, to_slot)] = (from_node, from_slot)
                
        return connection_map

    def _resolve_linked_value(self, link_ref: List[Any], nodes: Dict[str, Any], 
                             connection_map: Dict[Tuple[str, int], Tuple[str, int]]) -> Any:
        """
        Resolve a linked value by tracing through the workflow graph
        
        Args:
            link_ref: Link reference [node_id, slot]
            nodes: All nodes in the workflow
            connection_map: Map of connections
            
        Returns:
            any: The resolved value
        """
        # Handle direct string values
        if not isinstance(link_ref, list) or len(link_ref) != 2:
            return link_ref
            
        from_node_id, from_slot = link_ref
        
        # Get the source node
        if from_node_id not in nodes:
            return f"Unknown node: {from_node_id}"
            
        source_node = nodes[from_node_id]
        class_type = source_node.get('class_type', '')
        
        # For primitive nodes that directly output values
        if class_type == 'PrimitiveNode' or class_type.startswith('Primitive'):
            if 'value' in source_node:
                return source_node['value']
                
        # For string nodes
        if class_type == 'StringNode' or class_type == 'String':
            if 'string' in source_node.get('inputs', {}):
                return source_node['inputs']['string']
                
        # For value nodes
        if class_type == 'ValueNode' or class_type == 'IntegerNode' or class_type == 'FloatNode':
            if 'value' in source_node.get('inputs', {}):
                return source_node['inputs']['value']
                
        # For combo/dropdown nodes containing fixed options
        if class_type in ['SamplerNode', 'SchedulerNode', 'ModelNode', 'VAENode'] or 'Select' in class_type:
            # Try common option field names
            for option_field in ['value', 'selected', 'option', 'sampler_name', 'scheduler_name', 'model_name', 'vae_name']:
                if option_field in source_node.get('inputs', {}):
                    return source_node['inputs'][option_field]
        
        # For nodes that transform other values, trace back further
        # Look for specific class types that we know how to handle
        if class_type == 'KSamplerSelect':
            if 'sampler_name' in source_node.get('inputs', {}):
                return source_node['inputs']['sampler_name']
            if 'scheduler' in source_node.get('inputs', {}):
                return source_node['inputs']['scheduler']
        
        # For other node types, see if we can find the value from outputs
        if 'outputs' in source_node and from_slot < len(source_node['outputs']):
            output_info = source_node['outputs'][from_slot]
            # Some nodes have direct output values
            if isinstance(output_info, dict) and 'value' in output_info:
                return output_info['value']
        
        # As a fallback, return a string representation of the node reference
        return f"{class_type}:{from_node_id}"

    def _extract_latent_dimensions(self, nodes: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract latent dimensions from nodes.
        
        Args:
            nodes: Workflow nodes
            
        Returns:
            dict: Dimensions dictionary with width and height
        """
        for node_id, node in nodes.items():
            node_type = node.get('class_type', '')
            
            # Check for EmptyLatentImage node
            if 'EmptyLatent' in node_type:
                inputs = node.get('inputs', {})
                if 'width' in inputs and 'height' in inputs:
                    try:
                        width = int(inputs['width'])
                        height = int(inputs['height'])
                        return {'width': width, 'height': height}
                    except (ValueError, TypeError):
                        pass
                        
            # Check for other nodes with width/height inputs
            elif 'inputs' in node:
                inputs = node['inputs']
                if 'width' in inputs and 'height' in inputs:
                    try:
                        # Check if values are directly accessible (not node references)
                        if not isinstance(inputs['width'], list) and not isinstance(inputs['height'], list):
                            width = int(inputs['width'])
                            height = int(inputs['height'])
                            return {'width': width, 'height': height}
                    except (ValueError, TypeError):
                        pass
        
        return {}
    
    def _extract_lora_info(
        self,
        nodes: Dict[str, Any],
        links: List[Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract LoRA and embedding information from the workflow."""
        workflow_stub = {
            'prompt': {
                'nodes': nodes,
                'links': links,
            }
        }

        discovery = self._parsing_service.discover_assets(workflow_stub)
        loras: List[Dict[str, Any]] = []
        embeddings: List[Dict[str, Any]] = []

        def _to_float(value: Any) -> Optional[float]:
            try:
                if value is None:
                    return None
                return float(value)
            except (TypeError, ValueError):
                return None

        for record in discovery.loras:
            node = nodes.get(record.node_id, {})
            class_type = node.get('class_type', record.source)
            clean_name = _normalise_asset_name(record.name)
            if not clean_name:
                continue
            entry: Dict[str, Any] = {
                'node_id': record.node_id,
                'type': class_type,
                'name': clean_name,
                'source': record.source,
            }

            extra = record.extra or {}

            if 'slot' in extra:
                entry['slot'] = extra['slot']

            prompt_role = extra.get('prompt_role')
            if prompt_role:
                entry['prompt_role'] = prompt_role

            prompt_node = extra.get('source_prompt')
            if prompt_node:
                entry['prompt_node_id'] = prompt_node

            for strength_key in ('strength', 'strength_model', 'strength_clip'):
                if strength_key in extra:
                    coerced = _to_float(extra[strength_key])
                    if coerced is not None:
                        entry[strength_key] = coerced

            # Derive aggregate strength when not explicitly provided
            if 'strength' not in entry:
                strengths = [
                    entry.get('strength_model'),
                    entry.get('strength_clip'),
                ]
                numeric = [value for value in strengths if isinstance(value, (int, float))]
                if numeric:
                    entry['strength'] = sum(numeric) / len(numeric)
                else:
                    entry['strength'] = 1.0

            loras.append(entry)

        aggregated: Dict[str, Dict[str, Any]] = {}

        for entry in loras:
            key = entry['name'].lower()
            existing = aggregated.get(key)

            if existing is None:
                # Track detection sources with a private set
                entry['_detected_from'] = {entry['source']}
                aggregated[key] = entry
                continue

            detected_from = existing.setdefault('_detected_from', {existing['source']})
            detected_from.add(entry['source'])

            if existing['source'] == 'loader':
                if entry['source'] == 'inline':
                    if 'prompt_role' in entry:
                        existing.setdefault('inline_prompt_role', entry['prompt_role'])
                    if 'prompt_node_id' in entry:
                        existing.setdefault('inline_prompt_node_id', entry['prompt_node_id'])
                continue

            if entry['source'] == 'loader':
                # Promote loader data while preserving inline provenance
                carry_inline_role = existing.get('prompt_role') or existing.get('inline_prompt_role')
                carry_inline_node = existing.get('prompt_node_id') or existing.get('inline_prompt_node_id')

                entry['_detected_from'] = detected_from
                if carry_inline_role:
                    entry['inline_prompt_role'] = carry_inline_role
                if carry_inline_node:
                    entry['inline_prompt_node_id'] = carry_inline_node
                aggregated[key] = entry
                continue

            # Both entries are non-loader (e.g., multiple inline hits). Prefer first, augment metadata.
            if 'prompt_role' in entry and 'prompt_role' not in existing:
                existing['prompt_role'] = entry['prompt_role']
            if 'prompt_node_id' in entry and 'prompt_node_id' not in existing:
                existing['prompt_node_id'] = entry['prompt_node_id']

        final_loras: List[Dict[str, Any]] = []
        for entry in aggregated.values():
            detected = entry.pop('_detected_from', None)
            if detected:
                entry['detected_from'] = sorted(detected)
            final_loras.append(entry)

        for record in discovery.embeddings:
            node = nodes.get(record.node_id, {})
            class_type = node.get('class_type', record.source)
            clean_name = _normalise_asset_name(record.name)
            if not clean_name:
                continue
            entry: Dict[str, Any] = {
                'node_id': record.node_id,
                'type': class_type,
                'name': clean_name,
                'source': record.source,
            }

            extra = record.extra or {}
            prompt_role = extra.get('prompt_role')
            if prompt_role:
                entry['prompt_role'] = prompt_role

            prompt_node = extra.get('source_prompt')
            if prompt_node:
                entry['prompt_node_id'] = prompt_node

            entry['detected_from'] = [record.source]

            embeddings.append(entry)

        return final_loras, embeddings

    def _fallback_sampler_detection(
        self,
        nodes: Dict[str, Any],
        links: List[Any],
        result: Dict[str, Any],
    ) -> None:
        generation = result.setdefault('generation', {})
        if generation.get('sampler'):
            return

        workflow_stub = {
            'prompt': {
                'nodes': nodes,
                'links': links,
            }
        }

        best_candidate = self._select_best_sampler_candidate(workflow_stub)
        if not best_candidate:
            return

        generation['sampler'] = best_candidate.class_type or 'UnknownSampler'
        generation['sampler_node_id'] = best_candidate.node_id
        generation['sampler_detection'] = {
            'method': 'bfs',
            'reason': best_candidate.reason,
            'distance': best_candidate.distance,
            'priority': best_candidate.priority,
        }

        self._apply_sampler_inputs_to_generation(generation, best_candidate.inputs)
        ai_generation = result.setdefault('ai_info', {}).setdefault('generation', generation)
        if ai_generation is not generation:
            ai_generation.setdefault('sampler', generation['sampler'])
            ai_generation.setdefault('sampler_node_id', generation['sampler_node_id'])
            ai_generation.setdefault('sampler_detection', generation['sampler_detection'])
            self._apply_sampler_inputs_to_generation(ai_generation, best_candidate.inputs, overwrite=False)

    def _identify_output_nodes(self, nodes: Dict[str, Any]) -> List[str]:
        anchors: List[str] = []
        if not isinstance(nodes, dict):
            return anchors

        for node_id, node in nodes.items():
            class_type = str(node.get('class_type') or '')
            lowered = class_type.lower()
            if any(keyword in lowered for keyword in ('save', 'output', 'preview', 'display', 'export')):
                anchors.append(str(node_id))
        return anchors

    def _apply_sampler_inputs_to_generation(
        self,
        generation: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> None:
        if not inputs:
            return

        def maybe_set(key: str, value: Any) -> None:
            if value is None:
                return
            if overwrite or key not in generation or generation[key] in (None, ""):
                generation[key] = value

        def coerce_number(value: Any) -> Optional[Union[int, float]]:
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                candidate = value.strip()
                if not candidate:
                    return None
                try:
                    if '.' in candidate:
                        return float(candidate)
                    return int(candidate)
                except ValueError:
                    return None
            return None

        def extract_first(*keys: str) -> Optional[Any]:
            for key in keys:
                if key in inputs:
                    value = inputs[key]
                    if isinstance(value, list):
                        continue
                    return value
            return None

        steps_value = extract_first('steps', 'step_count')
        steps_number = coerce_number(steps_value)
        if steps_number is not None:
            maybe_set('steps', int(round(steps_number)))

        cfg_value = extract_first('cfg', 'cfg_scale', 'cfg_strength', 'guidance', 'guidance_scale')
        cfg_number = coerce_number(cfg_value)
        if cfg_number is not None:
            maybe_set('cfg_scale', float(cfg_number))

        scheduler_value = extract_first('scheduler', 'schedule', 'scheduler_name')
        if isinstance(scheduler_value, str) and scheduler_value:
            maybe_set('scheduler', scheduler_value)

        denoise_value = extract_first('denoise', 'denoise_strength')
        denoise_number = coerce_number(denoise_value)
        if denoise_number is not None:
            maybe_set('denoise', float(denoise_number))

        seed_value = extract_first('seed')
        seed_number = coerce_number(seed_value)
        if seed_number is not None:
            maybe_set('seed', int(round(seed_number)))

    def _select_best_sampler_candidate(
        self,
        workflow_stub: Dict[str, Any],
    ) -> Optional[SamplerCandidate]:
        prompt_section = workflow_stub.get('prompt', {})
        raw_nodes = prompt_section.get('nodes', {})
        if not isinstance(raw_nodes, dict) or not raw_nodes:
            return None

        links = prompt_section.get('links', [])
        if not links and isinstance(prompt_section, dict):
            links = prompt_section.get('connections', [])

        nodes = {str(node_id): node for node_id, node in raw_nodes.items()}
        normalized_stub = {
            'prompt': {
                'nodes': nodes,
                'links': links,
            }
        }

        anchor_ids = self._identify_output_nodes(nodes)
        if not anchor_ids:
            anchor_ids = list(nodes.keys())

        best_candidate: Optional[SamplerCandidate] = None

        for anchor in anchor_ids:
            if anchor not in nodes:
                continue
            candidate = self._parsing_service.find_best_sampler(
                normalized_stub,
                anchor,
            )
            if not candidate:
                continue
            if best_candidate is None or (
                (candidate.priority, candidate.distance) < (best_candidate.priority, best_candidate.distance)
            ):
                best_candidate = candidate

        return best_candidate

    def _find_connected_text_nodes(
        self,
        workflow_stub: Dict[str, Any],
        anchor_node: str,
        *,
        max_depth: int = 5,
        min_length: int = 5,
    ) -> List[PromptNodeRef]:
        if not anchor_node:
            return []

        try:
            return self._parsing_service.discover_text_nodes(
                workflow_stub,
                anchor_node,
                max_depth=max_depth,
                min_length=min_length,
            )
        except Exception:
            if self.debug:
                print(
                    f"[WorkflowMetadataProcessor] discover_text_nodes failed for anchor {anchor_node}",
                )
            return []

    @staticmethod
    def _select_prompt_text(texts: Dict[str, str]) -> Optional[str]:
        for key in ('prompt', 'text', 'string', 'value'):
            if key in texts and texts[key]:
                return texts[key]
        for value in texts.values():
            if value:
                return value
        return None

    @staticmethod
    def _dedupe_preserve_order(items: List[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered
    
    def _extract_vae_info(self, nodes: Dict[str, Any]) -> Optional[str]:
        """
        Extract VAE information from workflow.
        
        Args:
            nodes: Workflow nodes
            
        Returns:
            str or None: VAE name if found
        """
        for node_id, node in nodes.items():
            class_type = node.get('class_type', '')
            
            # Check for VAE nodes
            if 'VAE' in class_type:
                inputs = node.get('inputs', {})
                
                # Look for VAE name
                if 'vae_name' in inputs:
                    return inputs['vae_name']
        
        return None
    
    def _extract_a1111_loras(self, lora_data: Any, result: Dict[str, Any]) -> None:
        """
        Extract LoRA information from Automatic1111 workflow.
        
        Args:
            lora_data: LoRA data from A1111
            result: Result dictionary to update
        """
        loras = []
        
        # Handle different LoRA data formats
        if isinstance(lora_data, str):
            # Parse string format like "lora1:0.75,lora2:0.5"
            parts = lora_data.split(',')
            for part in parts:
                if ':' in part:
                    name, strength = part.split(':', 1)
                    try:
                        loras.append({
                            'name': name.strip(),
                            'strength': float(strength.strip())
                        })
                    except ValueError:
                        loras.append({
                            'name': name.strip(),
                            'strength': 1.0
                        })
                else:
                    loras.append({
                        'name': part.strip(),
                        'strength': 1.0
                    })
        elif isinstance(lora_data, list):
            # List format
            for item in lora_data:
                if isinstance(item, dict):
                    # Dict with name and strength
                    lora_info = {}
                    if 'name' in item:
                        lora_info['name'] = item['name']
                    elif 'lora_name' in item:
                        lora_info['name'] = item['lora_name']
                    else:
                        continue  # Skip if no name found
                        
                    # Get strength
                    if 'strength' in item:
                        lora_info['strength'] = item['strength']
                    elif 'weight' in item:
                        lora_info['strength'] = item['weight']
                    else:
                        lora_info['strength'] = 1.0
                        
                    loras.append(lora_info)
                elif isinstance(item, str):
                    # String item - assume it's just the name
                    loras.append({
                        'name': item,
                        'strength': 1.0
                    })
        elif isinstance(lora_data, dict):
            # Dictionary mapping names to strengths
            for name, strength in lora_data.items():
                try:
                    loras.append({
                        'name': name,
                        'strength': float(strength) if strength is not None else 1.0
                    })
                except (ValueError, TypeError):
                    loras.append({
                        'name': name,
                        'strength': 1.0
                    })
        
        # Add to result
        if loras:
            result['loras'] = loras
    
    def _extract_a1111_controlnet(self, controlnet_data: Any, result: Dict[str, Any]) -> None:
        """
        Extract ControlNet information from Automatic1111 workflow.
        
        Args:
            controlnet_data: ControlNet data from A1111
            result: Result dictionary to update
        """
        controlnets = []
        
        # Handle different ControlNet data formats
        if isinstance(controlnet_data, list):
            for item in controlnet_data:
                if isinstance(item, dict):
                    controlnet_info = {}
                    
                    # Extract common fields
                    for field in ['model', 'weight', 'control_mode', 'image']:
                        if field in item:
                            controlnet_info[field] = item[field]
                    
                    # Add if has minimum information
                    if 'model' in controlnet_info:
                        controlnets.append(controlnet_info)
        elif isinstance(controlnet_data, dict):
            # Single controlnet as dict
            controlnet_info = {}
            
            # Extract common fields
            for field in ['model', 'weight', 'control_mode', 'image']:
                if field in controlnet_data:
                    controlnet_info[field] = controlnet_data[field]
            
            # Add if has minimum information
            if 'model' in controlnet_info:
                controlnets.append(controlnet_info)
        
        # Add to result
        if controlnets:
            result['controlnets'] = controlnets
    
    def _extract_workflow_statistics(self, workflow_data: Dict[str, Any], workflow_source: str) -> Dict[str, Any]:
        """
        Extract workflow statistics including node counts, complexity, etc.
        
        Args:
            workflow_data: Raw workflow data
            workflow_source: Workflow source type
            
        Returns:
            dict: Statistics dictionary
        """
        stats = {}
        
        if workflow_source == 'comfyui':
            # Get the nodes and links
            prompt_data = workflow_data.get('prompt', {})
            if not prompt_data and isinstance(workflow_data, dict) and 'nodes' in workflow_data:
                prompt_data = workflow_data
                
            nodes = prompt_data.get('nodes', {})
            links = prompt_data.get('links', [])
            if not links and 'connections' in prompt_data:
                links = prompt_data.get('connections', [])
            
            # Count nodes
            stats['node_count'] = len(nodes)
            
            # Count connections
            stats['connection_count'] = len(links)
            
            # Count node types
            node_types = {}
            for node_id, node in nodes.items():
                class_type = node.get('class_type', 'Unknown')
                node_types[class_type] = node_types.get(class_type, 0) + 1
                
            stats['node_types'] = node_types
            stats['unique_node_types'] = len(node_types)
            
            # Calculate complexity score (simple heuristic)
            stats['complexity'] = len(nodes) * 2 + len(links)
            
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
            
            # Remove empty categories
            categories = {k: v for k, v in categories.items() if v > 0}
            stats['categories'] = categories
            
            # Calculate workflow type flags
            stats['has_upscale'] = any('Upscale' in node.get('class_type', '') 
                                      for node_id, node in nodes.items() if isinstance(node, dict))
            stats['has_controlnet'] = any('ControlNet' in node.get('class_type', '') 
                                         for node_id, node in nodes.items() if isinstance(node, dict))
            stats['has_lora'] = any(('LoRA' in node.get('class_type', '') or 'Lora' in node.get('class_type', '')) 
                                   for node_id, node in nodes.items() if isinstance(node, dict))
            stats['has_ip_adapter'] = any(('IPAdapter' in node.get('class_type', '') or 'IP-Adapter' in node.get('class_type', '')) 
                                         for node_id, node in nodes.items() if isinstance(node, dict))
        
        elif workflow_source in ['automatic1111', 'stable_diffusion_webui']:
            # A1111 has a simpler structure but we can still extract some statistics
            stats['parameter_count'] = len(workflow_data)
            stats['has_prompt'] = 'prompt' in workflow_data
            stats['has_negative_prompt'] = 'negative_prompt' in workflow_data
            stats['has_lora'] = any(k in workflow_data for k in ['lora', 'loras', 'lyco'])
            stats['has_controlnet'] = any(k in workflow_data for k in ['controlnet', 'control_net', 'controlnets'])
        
        return stats
    
    def _find_workflow_name(self, workflow_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract workflow name from metadata if available.
        
        Args:
            workflow_data: Raw workflow data
            
        Returns:
            str or None: Workflow name if found
        """
        # Try to extract from ComfyUI workflow
        if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            # Check for metadata section
            if 'metadata' in workflow_data['prompt'] and isinstance(workflow_data['prompt']['metadata'], dict):
                metadata = workflow_data['prompt']['metadata']
                if 'name' in metadata:
                    return metadata['name']
        
        # Check for extra_pnginfo
        if 'extra_pnginfo' in workflow_data and isinstance(workflow_data['extra_pnginfo'], dict):
            # Check in workflow section
            if 'workflow' in workflow_data['extra_pnginfo'] and isinstance(workflow_data['extra_pnginfo']['workflow'], dict):
                workflow = workflow_data['extra_pnginfo']['workflow']
                if 'name' in workflow:
                    return workflow['name']
                
            # Check in direct fields
            if 'name' in workflow_data['extra_pnginfo']:
                return workflow_data['extra_pnginfo']['name']
        
        # Check for title field in A1111-style workflows
        if 'title' in workflow_data:
            return workflow_data['title']
        
        return None
    
    def _identify_workflow_source(self, workflow_data: Dict[str, Any]) -> str:
        """
        Identify the source generator of the workflow.
        
        Args:
            workflow_data: Raw workflow data
            
        Returns:
            str: Source type ('comfyui', 'automatic1111', 'novelai', etc.)
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
        if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            if 'nodes' in workflow_data['prompt']:
                return 'comfyui'
            
        # Look for nodes directly in top level
        if 'nodes' in workflow_data and isinstance(workflow_data['nodes'], dict):
            return 'comfyui'
            
        # Look for A1111 specific structure
        if all(k in workflow_data for k in ['prompt', 'negative_prompt', 'sampler']):
            return 'automatic1111'
            
        # Look for NovelAI specific markers
        if 'novelai' in str(workflow_data).lower() or 'nai' in str(workflow_data).lower():
            return 'novelai'
            
        return 'unknown'
    
    def _get_cache_key(self, source_type: str, source_data: Any) -> Optional[str]:
        """
        Generate a cache key for the given source if possible.
        
        Args:
            source_type: Type of source
            source_data: Source data
            
        Returns:
            str or None: Cache key if cacheable, None otherwise
        """
        if source_type == 'file' and isinstance(source_data, str):
            # Use filepath as cache key
            return f"file:{source_data}"
        # Tensors and PIL images aren't easily cacheable by value
        return None
    
    def format_for_output(self, analysis_data: Dict[str, Any], format_type: str) -> Any:
        """
        Format analyzed data for specific output purposes.
        
        Args:
            analysis_data: Analyzed workflow data
            format_type: Desired output format ('metadata', 'text', 'html', 'markdown', 'json')
            
        Returns:
            Formatted output data
        """
        if format_type == 'metadata':
            # Return metadata structure for the metadata system
            if 'metadata' in analysis_data:
                return analysis_data['metadata']
            
            # Create metadata structure if not already present
            return {
                'ai_info': {
                    'generation': analysis_data.get('generation', {}),
                    'workflow_info': analysis_data.get('workflow_info', {}),
                    'workflow': analysis_data.get('workflow', {})
                }
            }
            
        elif format_type == 'text':
            return self._format_metadata_as_text(analysis_data)
            
        elif format_type == 'html':
            return self._format_metadata_as_html(analysis_data)
            
        elif format_type == 'markdown':
            return self._format_metadata_as_markdown(analysis_data)
            
        elif format_type == 'json':
            import json
            return json.dumps(analysis_data, indent=2)
            
        else:
            return f"Unsupported format type: {format_type}"
    
    def _format_metadata_as_text(self, metadata: Dict[str, Any]) -> str:
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
            
            # Workflow type/source
            if 'workflow_type' in metadata:
                lines.append(f"Workflow Source: {metadata['workflow_type'].upper()}")
                lines.append("")
            
            # Generation parameters
            if 'generation' in metadata:
                gen = metadata['generation']
                lines.append("=== Generation Parameters ===")
                
                # Model
                if 'model' in gen:
                    lines.append(f"Model: {gen['model']}")
                
                # Sampling parameters
                for param, label in [
                    ('sampler', 'Sampler'),
                    ('scheduler', 'Scheduler'),
                    ('steps', 'Steps'),
                    ('cfg_scale', 'CFG Scale'),
                    ('seed', 'Seed'),
                    ('denoise', 'Denoise Strength')
                ]:
                    if param in gen:
                        lines.append(f"{label}: {gen[param]}")
                
                # Dimensions
                if 'width' in gen and 'height' in gen:
                    lines.append(f"Dimensions: {gen['width']}x{gen['height']}")
                
                # VAE
                if 'vae' in gen:
                    lines.append(f"VAE: {gen['vae']}")
                    
                lines.append("")
            
            # Prompts
            if 'prompts' in metadata:
                prompts = metadata['prompts']
                
                if 'positive' in prompts and prompts['positive']:
                    lines.append("=== Positive Prompt ===")
                    lines.append('\n'.join(prompts['positive']))
                    lines.append("")
                
                if 'negative' in prompts and prompts['negative']:
                    lines.append("=== Negative Prompt ===")
                    lines.append('\n'.join(prompts['negative']))
                    lines.append("")
            
            # LoRAs
            if 'loras' in metadata and metadata['loras']:
                lines.append("=== LoRA Models ===")
                for lora in metadata['loras']:
                    if isinstance(lora, dict):
                        name = lora.get('name', 'Unknown')
                        strength = lora.get('strength', 1.0)
                        lines.append(f"- {name} (Strength: {strength})")
                    else:
                        lines.append(f"- {lora}")
                lines.append("")
            
            # Workflow stats
            if 'workflow_stats' in metadata:
                stats = metadata['workflow_stats']
                lines.append("=== Workflow Statistics ===")
                
                if 'node_count' in stats:
                    lines.append(f"Node Count: {stats['node_count']}")
                if 'connection_count' in stats:
                    lines.append(f"Connection Count: {stats['connection_count']}")
                if 'complexity' in stats:
                    lines.append(f"Complexity Score: {stats['complexity']}")
                if 'unique_node_types' in stats:
                    lines.append(f"Unique Node Types: {stats['unique_node_types']}")
                
                # Node type breakdown
                if 'node_types' in stats:
                    lines.append("\nNode Type Breakdown:")
                    for node_type, count in sorted(stats['node_types'].items(), 
                                                key=lambda x: x[1], 
                                                reverse=True)[:10]:  # Top 10 only
                        lines.append(f"- {node_type}: {count}")
                
                lines.append("")
            
            # Workflow info
            if 'workflow_info' in metadata:
                info = metadata['workflow_info']
                if info:
                    lines.append("=== Workflow Information ===")
                    for key, value in info.items():
                        lines.append(f"{key}: {value}")
                    lines.append("")
            
            # Add node source information if available
            if 'workflow_info' in metadata and 'node_sources' in metadata['workflow_info']:
                node_sources = metadata['workflow_info']['node_sources']
                lines.append("\n=== Node Sources ===")
                
                # Core nodes
                if 'core' in node_sources and node_sources['core']:
                    lines.append(f"\nCore Nodes: {len(node_sources['core'])}")
                    if self.debug:  # Show details only in debug mode
                        for node in node_sources['core'][:5]:  # Show first 5
                            lines.append(f"- {node['type']} (ID: {node['id']})")
                        if len(node_sources['core']) > 5:
                            lines.append(f"  ...and {len(node_sources['core']) - 5} more")
                
                # Custom nodes
                if 'custom' in node_sources and node_sources['custom']:
                    lines.append(f"\nCustom Node Packages: {len(node_sources['custom'])}")
                    for package, nodes in node_sources['custom'].items():
                        version = nodes[0].get('version', 'unknown')
                        lines.append(f"- {package} (Version: {version}, Nodes: {len(nodes)})")
                
                # Unknown nodes
                if 'unknown' in node_sources and node_sources['unknown']:
                    lines.append(f"\nUnknown Source Nodes: {len(node_sources['unknown'])}")
                    if self.debug:  # Show details only in debug mode
                        for node in node_sources['unknown'][:5]:  # Show first 5
                            lines.append(f"- {node['type']} (ID: {node['id']})")
                        if len(node_sources['unknown']) > 5:
                            lines.append(f"  ...and {len(node_sources['unknown']) - 5} more")
                
                lines.append("")

            return "\n".join(lines)
            
        except Exception as e:
            import traceback
            error_msg = f"Error formatting metadata as text: {str(e)}"
            if self.debug:
                error_msg += f"\n{traceback.format_exc()}"
            return error_msg
    
    def _format_metadata_as_html(self, metadata: Dict[str, Any]) -> str:
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
                    '<body>']
            
            # Workflow type/source
            if 'workflow_type' in metadata:
                html.append(f'<h1>Workflow Metadata ({metadata["workflow_type"].upper()})</h1>')
            else:
                html.append('<h1>Workflow Metadata</h1>')
            
            # Generation parameters
            if 'generation' in metadata:
                gen = metadata['generation']
                html.append('<div class="section">')
                html.append('<h2>Generation Parameters</h2>')
                html.append('<table>')
                
                # Model
                if 'model' in gen:
                    html.append(f'<tr><td class="key">Model</td><td>{gen["model"]}</td></tr>')
                
                # Sampling parameters
                for param, label in [
                    ('sampler', 'Sampler'),
                    ('scheduler', 'Scheduler'),
                    ('steps', 'Steps'),
                    ('cfg_scale', 'CFG Scale'),
                    ('seed', 'Seed'),
                    ('denoise', 'Denoise Strength')
                ]:
                    if param in gen:
                        html.append(f'<tr><td class="key">{label}</td><td>{gen[param]}</td></tr>')
                
                # Dimensions
                if 'width' in gen and 'height' in gen:
                    html.append(f'<tr><td class="key">Dimensions</td><td>{gen["width"]}x{gen["height"]}</td></tr>')
                
                # VAE
                if 'vae' in gen:
                    html.append(f'<tr><td class="key">VAE</td><td>{gen["vae"]}</td></tr>')
                
                html.append('</table>')
                html.append('</div>')
            
            # Prompts
            if 'prompts' in metadata:
                prompts = metadata['prompts']
                
                if 'positive' in prompts and prompts['positive']:
                    html.append('<div class="section">')
                    html.append('<h2>Positive Prompt</h2>')
                    for prompt in prompts['positive']:
                        html.append(f'<pre>{prompt}</pre>')
                    html.append('</div>')
                
                if 'negative' in prompts and prompts['negative']:
                    html.append('<div class="section">')
                    html.append('<h2>Negative Prompt</h2>')
                    for prompt in prompts['negative']:
                        html.append(f'<pre>{prompt}</pre>')
                    html.append('</div>')
            
            # LoRAs
            if 'loras' in metadata and metadata['loras']:
                html.append('<div class="section">')
                html.append('<h2>LoRA Models</h2>')
                html.append('<ul>')
                for lora in metadata['loras']:
                    if isinstance(lora, dict):
                        name = lora.get('name', 'Unknown')
                        strength = lora.get('strength', 1.0)
                        html.append(f'<li><strong>{name}</strong> (Strength: {strength})</li>')
                    else:
                        html.append(f'<li>{lora}</li>')
                html.append('</ul>')
                html.append('</div>')
            
            # Workflow stats
            if 'workflow_stats' in metadata:
                stats = metadata['workflow_stats']
                html.append('<div class="section">')
                html.append('<h2>Workflow Statistics</h2>')
                
                html.append('<table>')
                if 'node_count' in stats:
                    html.append(f'<tr><td class="key">Node Count</td><td>{stats["node_count"]}</td></tr>')
                if 'connection_count' in stats:
                    html.append(f'<tr><td class="key">Connection Count</td><td>{stats["connection_count"]}</td></tr>')
                if 'complexity' in stats:
                    html.append(f'<tr><td class="key">Complexity Score</td><td>{stats["complexity"]}</td></tr>')
                if 'unique_node_types' in stats:
                    html.append(f'<tr><td class="key">Unique Node Types</td><td>{stats["unique_node_types"]}</td></tr>')
                html.append('</table>')
                
                # Node type breakdown
                if 'node_types' in stats:
                    html.append('<h3>Node Type Breakdown</h3>')
                    html.append('<table>')
                    html.append('<tr><th>Node Type</th><th>Count</th></tr>')
                    for node_type, count in sorted(stats['node_types'].items(), 
                                                key=lambda x: x[1], 
                                                reverse=True)[:10]:  # Top 10 only
                        html.append(f'<tr><td>{node_type}</td><td>{count}</td></tr>')
                    html.append('</table>')
                
                html.append('</div>')
            
            # Workflow info
            if 'workflow_info' in metadata:
                info = metadata['workflow_info']
                if info:
                    html.append('<div class="section">')
                    html.append('<h2>Workflow Information</h2>')
                    html.append('<table>')
                    for key, value in info.items():
                        html.append(f'<tr><td class="key">{key}</td><td>{value}</td></tr>')
                    html.append('</table>')
                    html.append('</div>')
            
            # Node sources information
            if 'workflow_info' in metadata and 'node_sources' in metadata['workflow_info']:
                node_sources = metadata['workflow_info']['node_sources']
                html.append('<div class="section">')
                html.append('<h2>Node Sources</h2>')
                
                # Core nodes
                if 'core' in node_sources and node_sources['core']:
                    html.append(f'<h3>Core Nodes ({len(node_sources["core"])})</h3>')
                    if self.debug:
                        html.append('<ul>')
                        for node in node_sources['core'][:5]:
                            html.append(f'<li>{node["type"]} (ID: {node["id"]})</li>')
                        html.append('</ul>')
                        if len(node_sources['core']) > 5:
                            html.append(f'<p>...and {len(node_sources["core"]) - 5} more</p>')
                
                # Custom nodes
                if 'custom' in node_sources and node_sources['custom']:
                    html.append(f'<h3>Custom Node Packages ({len(node_sources["custom"])})</h3>')
                    html.append('<ul>')
                    for package, nodes in node_sources['custom'].items():
                        version = nodes[0].get('version', 'unknown')
                        html.append(f'<li><strong>{package}</strong> (Version: {version}, Nodes: {len(nodes)})</li>')
                    html.append('</ul>')
                
                # Unknown nodes
                if 'unknown' in node_sources and node_sources['unknown']:
                    html.append(f'<h3>Unknown Source Nodes ({len(node_sources["unknown"])})</h3>')
                    if self.debug:
                        html.append('<ul>')
                        for node in node_sources['unknown'][:5]:
                            html.append(f'<li>{node["type"]} (ID: {node["id"]})</li>')
                        html.append('</ul>')
                        if len(node_sources['unknown']) > 5:
                            html.append(f'<p>...and {len(node_sources["unknown"]) - 5} more</p>')
                
                html.append('</div>')
            
            html.append('</body></html>')
            return '\n'.join(html)
            
        except Exception as e:
            import traceback
            error_msg = f"Error formatting metadata as HTML: {str(e)}"
            if self.debug:
                error_msg += f"\n{traceback.format_exc()}"
            return f"<p>{error_msg}</p>"
    
    def _format_metadata_as_markdown(self, metadata: Dict[str, Any]) -> str:
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
                
            lines = []
            
            # Workflow type/source
            if 'workflow_type' in metadata:
                lines.append(f"# Workflow Metadata ({metadata['workflow_type'].upper()})")
            else:
                lines.append("# Workflow Metadata")
            lines.append("")
            
            # Generation parameters
            if 'generation' in metadata:
                gen = metadata['generation']
                lines.append("## Generation Parameters")
                
                # Model
                if 'model' in gen:
                    lines.append(f"**Model:** {gen['model']}")
                
                # Sampling parameters
                for param, label in [
                    ('sampler', 'Sampler'),
                    ('scheduler', 'Scheduler'),
                    ('steps', 'Steps'),
                    ('cfg_scale', 'CFG Scale'),
                    ('seed', 'Seed'),
                    ('denoise', 'Denoise Strength')
                ]:
                    if param in gen:
                        lines.append(f"**{label}:** {gen[param]}")
                
                # Dimensions
                if 'width' in gen and 'height' in gen:
                    lines.append(f"**Dimensions:** {gen['width']}x{gen['height']}")
                
                # VAE
                if 'vae' in gen:
                    lines.append(f"**VAE:** {gen['vae']}")
                
                lines.append("")
            
            # Prompts
            if 'prompts' in metadata:
                prompts = metadata['prompts']
                
                if 'positive' in prompts and prompts['positive']:
                    lines.append("## Positive Prompt")
                    for prompt in prompts['positive']:
                        lines.append(f"```\n{prompt}\n```")
                    lines.append("")
                
                if 'negative' in prompts and prompts['negative']:
                    lines.append("## Negative Prompt")
                    for prompt in prompts['negative']:
                        lines.append(f"```\n{prompt}\n```")
                    lines.append("")
            
            # LoRAs
            if 'loras' in metadata and metadata['loras']:
                lines.append("## LoRA Models")
                for lora in metadata['loras']:
                    if isinstance(lora, dict):
                        name = lora.get('name', 'Unknown')
                        strength = lora.get('strength', 1.0)
                        lines.append(f"- **{name}** (Strength: {strength})")
                    else:
                        lines.append(f"- {lora}")
                lines.append("")
            
            # Workflow stats
            if 'workflow_stats' in metadata:
                stats = metadata['workflow_stats']
                lines.append("## Workflow Statistics")
                
                if 'node_count' in stats:
                    lines.append(f"**Node Count:** {stats['node_count']}")
                if 'connection_count' in stats:
                    lines.append(f"**Connection Count:** {stats['connection_count']}")
                if 'complexity' in stats:
                    lines.append(f"**Complexity Score:** {stats['complexity']}")
                if 'unique_node_types' in stats:
                    lines.append(f"**Unique Node Types:** {stats['unique_node_types']}")
                lines.append("")
                
                # Node type breakdown
                if 'node_types' in stats:
                    lines.append("### Node Type Breakdown")
                    for node_type, count in sorted(stats['node_types'].items(), 
                                                key=lambda x: x[1], 
                                                reverse=True)[:10]:  # Top 10 only
                        lines.append(f"- **{node_type}:** {count}")
                lines.append("")
            
            # Workflow info
            if 'workflow_info' in metadata:
                info = metadata['workflow_info']
                if info:
                    lines.append("## Workflow Information")
                    for key, value in info.items():
                        lines.append(f"**{key}:** {value}")
                    lines.append("")
            
            # Node sources information
            if 'workflow_info' in metadata and 'node_sources' in metadata['workflow_info']:
                node_sources = metadata['workflow_info']['node_sources']
                lines.append("## Node Sources")
                
                # Core nodes
                if 'core' in node_sources and node_sources['core']:
                    lines.append(f"\n### Core Nodes ({len(node_sources['core'])})")
                    if self.debug:
                        for node in node_sources['core'][:5]:
                            lines.append(f"- **{node['type']}** (ID: {node['id']})")
                        if len(node_sources['core']) > 5:
                            lines.append(f"- ...and {len(node_sources['core']) - 5} more")
                
                # Custom nodes
                if 'custom' in node_sources and node_sources['custom']:
                    lines.append(f"\n### Custom Node Packages ({len(node_sources['custom'])})")
                    for package, nodes in node_sources['custom'].items():
                        version = nodes[0].get('version', 'unknown')
                        lines.append(f"- **{package}** (Version: {version}, Nodes: {len(nodes)})")
                
                # Unknown nodes
                if 'unknown' in node_sources and node_sources['unknown']:
                    lines.append(f"\n### Unknown Source Nodes ({len(node_sources['unknown'])})")
                    if self.debug:
                        for node in node_sources['unknown'][:5]:
                            lines.append(f"- **{node['type']}** (ID: {node['id']})")
                        if len(node_sources['unknown']) > 5:
                            lines.append(f"- ...and {len(node_sources['unknown']) - 5} more")
                
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            import traceback
            error_msg = f"Error formatting metadata as markdown: {str(e)}"
            if self.debug:
                error_msg += f"\n{traceback.format_exc()}"
            return error_msg

    def ensure_xmp_compatibility(self, metadata):
        """
        Ensure metadata follows Adobe XMP structure conventions
        and properly formats complex hierarchical structures for XMP
        """
        if "ai_info" in metadata and "generation" in metadata["ai_info"]:
            generation = metadata["ai_info"]["generation"]
            
            # Create/ensure the ai namespace exists for direct XMP access
            if "ai" not in metadata:
                metadata["ai"] = {}
            
            # Process simple top-level properties
            for key, value in generation.items():
                if not isinstance(value, (list, dict)):
                    metadata["ai"][f"generation.{key}"] = value
            
            # Process base_model structure
            if "base_model" in generation and isinstance(generation["base_model"], dict):
                for key, value in generation["base_model"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.base_model.{key}"] = value
            
            # Process sampling parameters
            if "sampling" in generation and isinstance(generation["sampling"], dict):
                for key, value in generation["sampling"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.sampling.{key}"] = value
            
            # Process flux parameters
            if "flux" in generation and isinstance(generation["flux"], dict):
                for key, value in generation["flux"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.flux.{key}"] = value
            
            # Process dimensions
            if "dimensions" in generation and isinstance(generation["dimensions"], dict):
                for key, value in generation["dimensions"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.dimensions.{key}"] = value
            
            # Process reference
            if "reference" in generation and isinstance(generation["reference"], dict):
                for key, value in generation["reference"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.reference.{key}"] = value
                        
            # Process colorization
            if "colorization" in generation and isinstance(generation["colorization"], dict):
                for key, value in generation["colorization"].items():
                    if not isinstance(value, (list, dict)):
                        metadata["ai"][f"generation.colorization.{key}"] = value
            
            # Process modules
            if "modules" in generation and isinstance(generation["modules"], dict):
                modules = generation["modules"]
                
                # Process VAE
                if "vae" in modules and isinstance(modules["vae"], dict):
                    for key, value in modules["vae"].items():
                        if not isinstance(value, (list, dict)):
                            metadata["ai"][f"generation.modules.vae.{key}"] = value
                
                # Process CLIP
                if "clip" in modules and isinstance(modules["clip"], dict):
                    for key, value in modules["clip"].items():
                        if not isinstance(value, (list, dict)):
                            metadata["ai"][f"generation.modules.clip.{key}"] = value
                
                # Process clip_vision
                if "clip_vision" in modules and isinstance(modules["clip_vision"], dict):
                    for key, value in modules["clip_vision"].items():
                        if not isinstance(value, (list, dict)):
                            metadata["ai"][f"generation.modules.clip_vision.{key}"] = value
                
                # Process collections (arrays)
                collections = [
                    ("loras", "lora"), 
                    ("controlnets", "controlnet"),
                    ("ip_adapters", "ip_adapter"),
                    ("style_models", "style_model"),
                    ("upscalers", "upscaler")
                ]
                
                for coll_name, single_name in collections:
                    if coll_name in modules and isinstance(modules[coll_name], list):
                        for i, item in enumerate(modules[coll_name], 1):
                            if isinstance(item, dict):
                                for prop, val in item.items():
                                    if not isinstance(val, (list, dict)):
                                        metadata["ai"][f"generation.{single_name}{i}.{prop}"] = val
            
            # Add to photoshop namespace for better visibility/compatibility
            if "photoshop" not in metadata:
                metadata["photoshop"] = {}
                
            # Add key AI parameters to photoshop namespace for broader compatibility
            ps_mapping = {
                "base_model.name": "AI_model",
                "sampling.sampler": "AI_sampler",
                "sampling.steps": "AI_steps",
                "sampling.cfg_scale": "AI_cfg_scale",
                "sampling.seed": "AI_seed",
                "modules.vae.name": "AI_vae",
                "modules.clip.primary": "AI_clip",
                "modules.clip.name": "AI_clip"
            }
            
            # Add values to photoshop namespace using flattened paths
            for ai_path, ps_key in ps_mapping.items():
                # Split path and traverse generation dict
                parts = ai_path.split('.')
                current = generation
                found = True
                
                for part in parts:
                    if part in current and current[part] is not None:
                        current = current[part]
                    else:
                        found = False
                        break
                
                if found:
                    metadata["photoshop"][ps_key] = current
        
        return metadata

    def process_workflow_data(self, prompt=None, extra_pnginfo=None, *, enable_hash_cache: bool = True):
        """
        Process workflow data from ComfyUI's prompt and extra_pnginfo structures.
        
        This is a compatibility method for backward compatibility with existing code.
        
        Args:
            prompt: ComfyUI prompt data containing nodes and connections
            extra_pnginfo: Additional PNG info with possible workflow details
            
        Returns:
            dict: Processed metadata with AI generation info, workflow structure, and analysis
        """
        try:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Processing workflow data")
                    
            # Create workflow data dictionary based on input
            workflow_data = prompt
            if extra_pnginfo and isinstance(extra_pnginfo, dict):
                # Add extra_pnginfo to workflow data to ensure it's analyzed
                workflow_data = {
                    'prompt': prompt,
                    'extra_pnginfo': extra_pnginfo
                }
            
            # Extract nodes from the prompt
            nodes = None
            if prompt and isinstance(prompt, dict):
                # Direct access to nodes
                if "nodes" in prompt:
                    nodes = prompt["nodes"]
                # Standard ComfyUI structure
                elif all(not k.startswith('_') and isinstance(v, dict) for k, v in prompt.items()):
                    nodes = prompt
            
            # Use direct parameter mapping if nodes available
            if nodes:
                from ..utils.node_parameter_mapping import extract_by_parameter_mapping
                metadata = extract_by_parameter_mapping(nodes, self.debug)
                
                # Add basic metadata structure if not present
                if "basic" not in metadata:
                    metadata["basic"] = {}
                
                # Enrich with hashes before ensuring XMP compatibility
                self._populate_model_metadata(metadata, enable_hash_cache)

                # Apply XMP compatibility adjustments
                metadata = self.ensure_xmp_compatibility(metadata)
                    
                return metadata
                    
            # Fall back to original extraction method if can't use direct mapping
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Falling back to legacy extraction method")
                
            # Continue with original extraction logic...
            extraction_result = self.extract_from_source('dict', workflow_data)
            
            # Check for extraction errors
            if 'error' in extraction_result:
                if self.debug:
                    print(f"[WorkflowMetadataProcessor] Extraction error: {extraction_result['error']}")
                return {'error': extraction_result['error']}
                
            # Get workflow data and analyze
            workflow = extraction_result.get('workflow', workflow_data)
            analysis_result = self.analyze_workflow(workflow)

            metadata = self.format_for_output(analysis_result, 'metadata')
            self._populate_model_metadata(metadata, enable_hash_cache)
            metadata = self.ensure_xmp_compatibility(metadata)

            return metadata

        except Exception as e:
            if self.debug:
                import traceback
                print(f"[WorkflowMetadataProcessor] Error processing workflow data: {str(e)}")
                traceback.print_exc()
            return {'error': f"Failed to process workflow data: {str(e)}"}

    def process_embedded_data(self, image_path):
        """
        Extract and process workflow data from embedded image metadata.
        
        This is a compatibility method for backward compatibility with existing code.
        
        Args:
            image_path: Path to the image file to extract data from
            
        Returns:
            dict: Processed metadata from the embedded image data
        """
        try:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Processing embedded data from {image_path}")
                
            # Use our new extract_from_source method with 'file' type
            extraction_result = self.extract_from_source('file', image_path)
            
            # Check for extraction errors
            if 'error' in extraction_result:
                if self.debug:
                    print(f"[WorkflowMetadataProcessor] Extraction error: {extraction_result['error']}")
                return {'error': extraction_result['error']}
                
            # Get workflow data and analyze
            workflow_data = extraction_result.get('workflow', {})
            analysis_result = self.analyze_workflow(workflow_data)
            
            # Format as metadata
            return self.format_for_output(analysis_result, 'metadata')
            
        except Exception as e:
            if self.debug:
                import traceback
                print(f"[WorkflowMetadataProcessor] Error processing embedded data: {str(e)}")
                traceback.print_exc()
            return {'error': f"Failed to process embedded data: {str(e)}"}

    def extract_and_convert_to_ai_metadata(self, source: Any, source_type: str = 'file') -> Dict[str, Any]:
        """
        Extract workflow data and convert to AI metadata format suitable for storage.
        
        This is a convenience method that combines extraction and formatting into
        a single call, returning metadata ready for the MetadataService.
        
        Args:
            source: Source to extract from (filepath, tensor, etc.)
            source_type: Type of source ('file', 'image', 'tensor', 'dict', etc.)
            
        Returns:
            dict: Metadata structure ready for storage
        """
        # Extract workflow data
        extraction_result = self.extract_from_source(source_type, source)
        
        # Check for errors
        if 'error' in extraction_result:
            return {'error': extraction_result['error']}
        
        # Get workflow data and source
        workflow_data = extraction_result.get('workflow', {})
        workflow_source = extraction_result.get('source', 'unknown')
        
        # Analyze the workflow
        analysis_result = self.analyze_workflow(workflow_data)
        
        # Check for analysis errors
        if 'error' in analysis_result:
            return {'error': analysis_result['error']}
        
        # Format for metadata storage
        metadata = self.format_for_output(analysis_result, 'metadata')
        
        # Ensure workflow is included
        if 'ai_info' in metadata and 'workflow' not in metadata['ai_info']:
            metadata['ai_info']['workflow'] = workflow_data
            
        return metadata
        
    def track_discovery(self, node_type: str, node: Dict[str, Any]) -> None:
        """
        Track discovered node types and their parameters if in discovery mode.
        
        Args:
            node_type: Node type name
            node: Node data
        """
        if not self.discovery_mode:
            return
            
        # Track node type
        if node_type not in self.discovered_node_types:
            self.discovered_node_types.add(node_type)
            self.discovery_log.append(f"Discovered new node type: {node_type}")
            
        # Track node type frequency
        if node_type not in self.node_type_frequencies:
            self.node_type_frequencies[node_type] = 0
        self.node_type_frequencies[node_type] += 1
        
        # Track parameters
        inputs = node.get('inputs', {})
        if inputs:
            if node_type not in self.discovered_parameters:
                self.discovered_parameters[node_type] = {}
                
            for param_key, param_value in inputs.items():
                if param_key not in self.discovered_parameters[node_type]:
                    self.discovered_parameters[node_type][param_key] = {
                        'type': type(param_value).__name__,
                        'examples': []
                    }
                    
                # Track parameter frequency
                param_id = f"{node_type}.{param_key}"
                if param_id not in self.parameter_frequencies:
                    self.parameter_frequencies[param_id] = 0
                self.parameter_frequencies[param_id] += 1
                
                # Store example values (up to 3 unique examples)
                examples = self.discovered_parameters[node_type][param_key]['examples']
                example_value = str(param_value)
                
                # Truncate very long examples
                if len(example_value) > 100:
                    example_value = example_value[:97] + "..."
                    
                if len(examples) < 3 and example_value not in examples:
                    examples.append(example_value)

    def _analyze_node_sources(self, nodes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze node sources to identify core vs. custom nodes.
        
        Args:
            nodes: Workflow nodes
            
        Returns:
            dict: Analysis of node sources and versions
        """
        node_sources = {
            'core': [],
            'custom': {},
            'unknown': []
        }
        
        for node_id, node in nodes.items():
            # Get node type
            node_type = node.get('class_type', '')
            
            # Check for properties that might indicate source
            properties = node.get('properties', {})
            
            if properties:
                # Check for cnr_id to determine source
                cnr_id = properties.get('cnr_id')
                if cnr_id == 'comfy-core':
                    # This is a core node
                    version = properties.get('ver')
                    node_sources['core'].append({
                        'id': node_id,
                        'type': node_type,
                        'version': version
                    })
                elif cnr_id:
                    # This is a custom node with registry ID
                    package = cnr_id
                    if package not in node_sources['custom']:
                        node_sources['custom'][package] = []
                        
                    node_sources['custom'][package].append({
                        'id': node_id,
                        'type': node_type,
                        'version': properties.get('ver')
                    })
                elif 'aux_id' in properties:
                    # Alternative ID for custom nodes
                    package = properties.get('aux_id')
                    if package not in node_sources['custom']:
                        node_sources['custom'][package] = []
                        
                    node_sources['custom'][package].append({
                        'id': node_id,
                        'type': node_type,
                        'version': properties.get('ver')
                    })
                else:
                    # Unknown source
                    node_sources['unknown'].append({
                        'id': node_id,
                        'type': node_type
                    })
            else:
                # No properties, try to guess based on node type
                if node_type.startswith(('Checkpoint', 'KSampler', 'CLIPText', 'VAE')):
                    # Likely core nodes
                    node_sources['core'].append({
                        'id': node_id,
                        'type': node_type
                    })
                else:
                    # Unknown source
                    node_sources['unknown'].append({
                        'id': node_id,
                        'type': node_type
                    })
        
        return node_sources    
    def save_discovery_report(self, filepath: str) -> bool:
        """
        Save discovery information to a JSON file.
        
        Args:
            filepath: Path to save the report
            
        Returns:
            bool: True if successful
        """
        if not self.discovery_mode:
            return False
            
        try:
            import json
            import datetime
            
            # Format the report
            report = {
                'timestamp': datetime.datetime.now().isoformat(),
                'discovered_node_types': sorted(list(self.discovered_node_types)),
                'node_type_frequencies': self.node_type_frequencies,
                'discovered_parameters': self.discovered_parameters,
                'parameter_frequencies': self.parameter_frequencies,
                'discovery_log': self.discovery_log[-100:]  # Keep only last 100 log entries
            }
            
            # Create directory if needed
            import os
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
                
            return True
            
        except Exception as e:
            if self.debug:
                print(f"[WorkflowMetadataProcessor] Error saving discovery report: {str(e)}")
            return False