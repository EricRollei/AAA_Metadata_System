"""
PNG Metadata Extractor Node V3

Enhanced version of the PNG Metadata Extractor node that integrates with the new
MetadataService system. Provides comprehensive extraction of metadata from PNG images.

Features:
- Supports all embedding formats
- Extracts workflows, parameters, and metadata
- Better handling of split workflows
- Structured metadata extraction
- Improved error recovery
"""

import os
import json
import base64
import re
from PIL import Image
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union

# Import the metadata service from the package
from custom_nodes.AAA_Metadata_System import MetadataService

class PngMetadataExtractorNodeV3:
    """Enhanced PNG metadata extraction node using MetadataService"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_filepath": ("STRING", {"default": ""}),
                "extraction_mode": (["workflow", "parameters", "metadata", "all"], {"default": "all"})
            },
            "optional": {
                "key_filter": ("STRING", {"default": ""}),
                "debug_logging": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("DICT", "STRING", "STRING")
    RETURN_NAMES = ("metadata", "json_str", "summary")
    FUNCTION = "extract_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)

    def extract_metadata(self, input_filepath: str, extraction_mode: str = "all", 
                        key_filter: str = "", debug_logging: bool = False) -> Tuple[Dict, str, str]:
        """
        Extract metadata from PNG file
        
        Args:
            input_filepath: Path to PNG file
            extraction_mode: What type of metadata to extract (workflow, parameters, metadata, all)
            key_filter: Filter metadata keys by this string (comma-separated)
            debug_logging: Enable detailed logging
            
        Returns:
            Tuple of (metadata_dict, json_string, summary)
        """
        try:
            # Enable debug logging if requested
            if debug_logging:
                self.metadata_service.debug = True
                print(f"[PNGExtractor] Extracting metadata from: {input_filepath}")
            
            # Validate input
            if not input_filepath or not os.path.exists(input_filepath):
                return ({}, "{}", "No valid file provided")
            
            # Initialize result structures
            result = {}
            filtered_result = {}
            summary_lines = [f"Metadata from: {os.path.basename(input_filepath)}"]
            
            # Parse key filter
            key_filters = []
            if key_filter:
                key_filters = [k.strip() for k in key_filter.split(",")]
            
            # Process based on extraction mode
            if extraction_mode in ["workflow", "all"]:
                workflow = self._extract_workflow(input_filepath)
                if workflow:
                    result["workflow"] = workflow
                    summary_lines.append(f"Extracted workflow ({len(json.dumps(workflow))} bytes)")
                    
                    # Handle case where workflow is stored in metadata
                    if self._is_split_workflow_reference(workflow):
                        summary_lines.append("Detected split workflow reference")
                        full_workflow = self._get_full_workflow(input_filepath)
                        if full_workflow:
                            result["workflow"] = full_workflow
                            summary_lines.append(f"Extracted full workflow from metadata ({len(json.dumps(full_workflow))} bytes)")
            
            if extraction_mode in ["parameters", "all"]:
                parameters = self._extract_parameters(input_filepath)
                if parameters:
                    result["parameters"] = parameters
                    summary_lines.append(f"Extracted parameters ({len(parameters)} chars)")
            
            if extraction_mode in ["metadata", "all"]:
                # Get metadata from all sources
                metadata = self._extract_all_metadata(input_filepath)
                if metadata:
                    result["metadata"] = metadata
                    summary_lines.append(f"Extracted metadata ({len(json.dumps(metadata))} bytes)")
            
            # Apply filters if specified
            if key_filters:
                summary_lines.append(f"\nApplying filters: {', '.join(key_filters)}")
                filtered_result = self._apply_key_filters(result, key_filters)
                
                # Update summary with filter results
                found_keys = self._get_all_keys(filtered_result)
                if found_keys:
                    summary_lines.append(f"Matched keys: {', '.join(found_keys[:10])}")
                    if len(found_keys) > 10:
                        summary_lines.append(f"...and {len(found_keys)-10} more")
                else:
                    summary_lines.append("No keys matched the filter")
            else:
                filtered_result = result
            
            # Prepare return values
            metadata_dict = filtered_result
            json_str = json.dumps(filtered_result, indent=2)
            summary = "\n".join(summary_lines)
            
            if debug_logging:
                print(f"[PNGExtractor] Extraction complete with {len(filtered_result)} sections")
            
            return (metadata_dict, json_str, summary)
        
        except Exception as e:
            import traceback
            error_text = f"Error extracting metadata: {str(e)}\n{traceback.format_exc()}"
            print(f"[PNGExtractor] ERROR: {error_text}")
            return ({}, "{}", error_text)
        finally:
            # Ensure cleanup always happens
            self.cleanup()

    def _extract_workflow(self, filepath: str) -> Dict:
        """Extract workflow data from PNG file"""
        try:
            with Image.open(filepath) as img:
                info = img.info
                
                # Look for workflow in standard locations
                if 'workflow' in info:
                    return self._parse_workflow_data(info['workflow'])
                    
                # Try 'prompt' as used by some versions
                elif 'prompt' in info:
                    return self._parse_workflow_data(info['prompt'])
                
                # Look inside parameters
                elif 'parameters' in info:
                    # Try to extract embedded JSON from parameters
                    return self._extract_workflow_from_parameters(info['parameters'])
                    
            return {}
                
        except Exception as e:
            print(f"[PNGExtractor] Error extracting workflow: {str(e)}")
            return {}

    def _parse_workflow_data(self, data) -> Dict:
        """Parse workflow data from various formats"""
        try:
            # If already dict, return as is
            if isinstance(data, dict):
                return data
                
            # Try parsing as JSON
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except:
                    pass
                    
            # Try base64 decode
            try:
                decoded = base64.b64decode(data).decode('utf-8')
                return json.loads(decoded)
            except:
                pass
                
            return {}
                
        except Exception as e:
            print(f"[PNGExtractor] Error parsing workflow: {str(e)}")
            return {}

    def _extract_parameters(self, filepath: str) -> str:
        """Extract parameter string from PNG"""
        try:
            with Image.open(filepath) as img:
                if 'parameters' in img.info:
                    return img.info['parameters']
            return ""
                
        except Exception as e:
            print(f"[PNGExtractor] Error extracting parameters: {str(e)}")
            return ""

    def _extract_workflow_from_parameters(self, parameters: str) -> Dict:
        """Try to extract JSON workflow from parameters string"""
        try:
            # Look for JSON objects in the parameters
            json_pattern = r'(\{.*\})'
            matches = re.findall(json_pattern, parameters)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    # Check if it looks like a workflow (has prompt/nodes or similar)
                    if 'prompt' in data and isinstance(data['prompt'], dict):
                        return data
                except:
                    pass
                    
            return {}
                
        except Exception as e:
            print(f"[PNGExtractor] Error extracting workflow from parameters: {str(e)}")
            return {}

    def _extract_all_metadata(self, filepath: str) -> Dict:
        """Extract all metadata using the MetadataService"""
        try:
            # Use the metadata service to read from all available sources
            # with fallback to ensure we get something if available
            metadata = self.metadata_service.read_metadata(filepath, source='embedded', fallback=True)
            return metadata or {}
                
        except Exception as e:
            print(f"[PNGExtractor] Error extracting metadata: {str(e)}")
            return {}

    def _is_split_workflow_reference(self, workflow: Dict) -> bool:
        """Check if workflow is just a reference to split workflow"""
        # Look for indicators of split workflow references
        if 'split_workflow' in workflow:
            return True
            
        if 'type' in workflow and workflow['type'] == 'workflow_reference':
            return True
            
        if 'is_reference' in workflow:
            return True
            
        if 'xmp_workflow' in workflow or 'external_workflow' in workflow:
            return True
        
        # Check if workflow seems suspiciously small/simple
        if len(workflow) < 5 and ('reference' in str(workflow).lower() or 'xmp' in str(workflow).lower()):
            return True
            
        return False

    def _get_full_workflow(self, filepath: str) -> Dict:
        """Get full workflow data from metadata"""
        try:
            # Read metadata from all potential sources
            metadata = self.metadata_service.read_metadata(filepath, source='xmp', fallback=True)
            if not metadata:
                return {}
                
            # Extract workflow data from ai_info section
            if 'ai_info' in metadata and 'workflow' in metadata['ai_info']:
                workflow = metadata['ai_info']['workflow']
                
                # If workflow is a string, try to parse as JSON
                if isinstance(workflow, str):
                    try:
                        return json.loads(workflow)
                    except:
                        pass
                        
                # If workflow is already a dict/object, return it
                if isinstance(workflow, dict):
                    return workflow
                    
            return {}
                
        except Exception as e:
            print(f"[PNGExtractor] Error getting full workflow: {str(e)}")
            return {}

    def _apply_key_filters(self, data: Dict, filters: List[str]) -> Dict:
        """Apply key filters to metadata"""
        if not filters:
            return data
            
        result = {}
        
        # Function to recursively filter keys
        def filter_dict(d, path="", target=None):
            if target is None:
                target = {}
                
            if isinstance(d, dict):
                for k, v in d.items():
                    current_path = f"{path}.{k}" if path else k
                    
                    # Check if key matches any filter
                    if any(f.lower() in current_path.lower() for f in filters):
                        # Create path in result if needed
                        parts = current_path.split('.')
                        current = target
                        for i, part in enumerate(parts[:-1]):
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                            
                        # Add value
                        current[parts[-1]] = v
                    
                    # Recursively process nested dicts
                    if isinstance(v, dict):
                        filter_dict(v, current_path, target)
                        
                    # Handle lists of dicts
                    elif isinstance(v, list):
                        for i, item in enumerate(v):
                            if isinstance(item, dict):
                                filter_dict(item, f"{current_path}[{i}]", target)
            
            return target
            
        # Apply filtering
        return filter_dict(data)

    def _get_all_keys(self, data: Dict) -> List[str]:
        """Get all keys in a nested dictionary"""
        keys = []
        
        def collect_keys(d, path=""):
            if isinstance(d, dict):
                for k, v in d.items():
                    current_path = f"{path}.{k}" if path else k
                    keys.append(current_path)
                    
                    if isinstance(v, dict):
                        collect_keys(v, current_path)
                    elif isinstance(v, list):
                        for i, item in enumerate(v):
                            if isinstance(item, dict):
                                collect_keys(item, f"{current_path}[{i}]")
                                
        collect_keys(data)
        return keys

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "PngMetadataExtractorV3": PngMetadataExtractorNodeV3
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PngMetadataExtractorV3": "PNG Metadata Extractor V3"
}