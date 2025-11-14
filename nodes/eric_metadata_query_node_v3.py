"""
ComfyUI Node: Eric's Metadata Query V3
Description: Enhanced metadata query node for extracting specific metadata fields
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

Metadata Query Node V3 - Updated March 2025

Enhanced query node for extracting specific information from image metadata.
Supports the new MetadataService architecture with multi-source queries.

Features:
- Queries across all metadata storage methods (embedded, XMP, text, database)
- Multiple query methods (simple, JSONPath, regex)
- Source prioritization for consistent results
- Enhanced output options and formatting
"""

import os
import json
import re
from typing import Dict, Any, List, Tuple, Optional, Union

# Import the metadata service from the package
from custom_nodes.AAA_Metadata_System import MetadataService

class MetadataQueryNodeV3:
    """Enhanced metadata query node for extracting specific metadata fields"""
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)
        
        # Cache for optimization
        self.last_filepath = None
        self.last_metadata = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_filepath": ("STRING", {"default": ""}),
                "query_mode": (["simple", "jsonpath", "regex"], {"default": "simple"}),
                "query": ("STRING", {"default": "ai_info.generation.model", "multiline": False}),
                "default_value": ("STRING", {"default": "unknown", "multiline": False})
            },
            "optional": {
                # Data source options
                "source": (["auto", "embedded", "xmp", "txt", "db"], {"default": "auto"}),
                "fallback_sources": ("BOOLEAN", {"default": True}),
                # Output options
                "return_full": ("BOOLEAN", {"default": False}),
                "format_output": ("BOOLEAN", {"default": True}),
                "debug_logging": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("STRING", "DICT")
    RETURN_NAMES = ("result", "metadata")
    FUNCTION = "query_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def query_metadata(self, 
                      input_filepath: str,
                      query_mode: str = "simple",
                      query: str = "ai_info.generation.model",
                      default_value: str = "unknown",
                      source: str = "auto",
                      fallback_sources: bool = True,
                      return_full: bool = False,
                      format_output: bool = True,
                      debug_logging: bool = False) -> Tuple[str, Dict]:
        """
        Query metadata from image file
        
        Args:
            input_filepath: Path to input image
            query_mode: How to interpret the query string
            query: Query string to extract specific metadata
            default_value: Default value if query fails
            source: Primary source to query ('auto', 'embedded', 'xmp', 'txt', 'db')
            fallback_sources: Whether to try other sources if primary fails
            return_full: Whether to return full metadata or just query result
            format_output: Whether to format the output for readability
            debug_logging: Whether to enable debug logging
            
        Returns:
            Tuple of (result_string, metadata_dict)
        """
        try:
            # Enable debug logging if requested
            self.metadata_service.debug = debug_logging
            
            if debug_logging:
                print(f"[MetadataQuery] Starting query on {input_filepath}")
                print(f"[MetadataQuery] Query: {query_mode} => {query}")
            
            # Validate input
            if not input_filepath or not os.path.exists(input_filepath):
                if debug_logging:
                    print(f"[MetadataQuery] File not found: {input_filepath}")
                return (default_value, {})
            
            # Check if we can use cached metadata
            cache_valid = (self.last_filepath == input_filepath and self.last_metadata is not None)
            
            if not cache_valid:
                # Set resource identifier (important for proper XMP handling)
                filename = os.path.basename(input_filepath)
                resource_uri = f"file:///{filename}"
                self.metadata_service.set_resource_identifier(resource_uri)
                
                # Read metadata from appropriate source(s)
                metadata = self.metadata_service.read_metadata(
                    filepath=input_filepath,
                    source=source,
                    fallback=fallback_sources
                )
                
                # Update cache
                self.last_filepath = input_filepath
                self.last_metadata = metadata
            else:
                metadata = self.last_metadata
                if debug_logging:
                    print(f"[MetadataQuery] Using cached metadata")
            
            # If return full is selected, return whole metadata dict
            if return_full:
                result_str = json.dumps(metadata, indent=2) if format_output else json.dumps(metadata)
                return (result_str, metadata)
                
            # Process query based on mode
            if query_mode == "simple":
                result = self._simple_query(metadata, query, default_value)
            elif query_mode == "jsonpath":
                result = self._jsonpath_query(metadata, query, default_value)
            elif query_mode == "regex":
                result = self._regex_query(metadata, query, default_value)
            else:
                result = default_value
            
            # Convert result to string (formatted if requested)
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result, indent=2) if format_output else json.dumps(result)
            else:
                result_str = str(result)
                
            if debug_logging:
                print(f"[MetadataQuery] Query result: {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
                
            return (result_str, metadata)
                
        except Exception as e:
            import traceback
            print(f"[MetadataQuery] ERROR: {str(e)}")
            if debug_logging:
                traceback.print_exc()
            return (default_value, {})
        finally:
            # Always ensure cleanup happens
            self.cleanup()

    def _simple_query(self, metadata: Dict, query: str, default_value: str) -> Any:
        """
        Process a simple dot-notation query
        
        Args:
            metadata: Metadata dictionary to query
            query: Dot-notation path (e.g. "ai_info.generation.model")
            default_value: Default value if query fails
            
        Returns:
            Query result or default value
        """
        try:
            # Parse the query into path components
            path_parts = query.split('.')
            
            # Navigate down the path
            current = metadata
            for part in path_parts:
                # Handle array indices in brackets, e.g. items[0]
                if '[' in part and part.endswith(']'):
                    base_part, idx_part = part.split('[', 1)
                    idx = int(idx_part[:-1])  # Remove closing bracket
                    
                    if base_part not in current:
                        return default_value
                        
                    current = current[base_part][idx]
                else:
                    if part not in current:
                        return default_value
                    current = current[part]
                    
            return current
            
        except (KeyError, IndexError, TypeError):
            return default_value
        except Exception as e:
            print(f"[MetadataQuery] Error in simple query: {str(e)}")
            return default_value

    def _jsonpath_query(self, metadata: Dict, query: str, default_value: str) -> Any:
        """
        Process a JSONPath query
        
        Args:
            metadata: Metadata dictionary to query
            query: JSONPath expression
            default_value: Default value if query fails
            
        Returns:
            Query result or default value
        """
        try:
            import jsonpath_ng.ext as jsonpath
            
            # Parse and execute JSONPath query
            jsonpath_expr = jsonpath.parse(query)
            matches = [match.value for match in jsonpath_expr.find(metadata)]
            
            # Return result based on matches
            if not matches:
                return default_value
            elif len(matches) == 1:
                return matches[0]
            else:
                return matches
                
        except ImportError:
            print("[MetadataQuery] JSONPath queries require the 'jsonpath-ng' package. Please install it.")
            return default_value
        except Exception as e:
            print(f"[MetadataQuery] Error in JSONPath query: {str(e)}")
            return default_value

    def _regex_query(self, metadata: Dict, query: str, default_value: str) -> Any:
        """
        Process a regex-based query that flattens the structure and searches keys
        
        Args:
            metadata: Metadata dictionary to query
            query: Regular expression pattern
            default_value: Default value if query fails
            
        Returns:
            Dict of matching key-value pairs or default value
        """
        try:
            pattern = re.compile(query)
            
            # Flatten the nested dict with path information
            flat_dict = {}
            
            def _flatten(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        _flatten(value, new_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]"
                        _flatten(item, new_path)
                else:
                    flat_dict[path] = obj
            
            _flatten(metadata)
            
            # Find matches using regex
            matches = {}
            for path, value in flat_dict.items():
                if pattern.search(path):
                    matches[path] = value
                    
            # Return matches or default
            if matches:
                return matches
            else:
                return default_value
                
        except Exception as e:
            print(f"[MetadataQuery] Error in regex query: {str(e)}")
            return default_value

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Metadata_Query_V3": MetadataQueryNodeV3
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Metadata_Query_V3": "Eric's Metadata Query V3"
}