"""
ComfyUI Node: EnhancedMetadataFilterNode_V2
Description: User-friendly metadata filtering with simplified query building and
    MetadataService integration for seamless database and file system searches.
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


Eric's Enhanced Metadata Filter Node V2 - Updated March 12, 2025

User-friendly metadata filtering with simplified query building and
MetadataService integration for seamless database and file system searches.
"""

import os
import torch
import numpy as np
import json
import time
from PIL import Image
from typing import List, Dict, Any

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService

# Import the updated MetadataQuery
from AAA_Metadata_System.eric_metadata.utils.metadata_query import MetadataQuery

class EnhancedMetadataFilterNode_V2:
    """User-friendly metadata filtering with simplified query building and MetadataService integration"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": ""}),
                "field_type": (["keywords", "aesthetic_score", "technical_score", "prompt", "model", "directory", "lora", "any_text"], {"default": "keywords"}),
                "operation": (["contains", "equals", "greater_than", "less_than", "between", "exists"], {"default": "contains"}),
                "value": ("STRING", {"default": ""}),
                "value2": ("STRING", {"default": "", "placeholder": "For 'between' operation"}),
                "limit": ("INT", {"default": 10, "min": 1, "max": 100}),
                "load_images": ("BOOLEAN", {"default": False}),
                "use_database": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "additional_query": ("STRING", {"default": "", "multiline": True}),
                "recursive_search": ("BOOLEAN", {"default": False}),
                "debug_logging": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("STRING", "INT", "IMAGE")
    RETURN_NAMES = ("matched_paths", "match_count", "images")
    FUNCTION = "filter_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def __init__(self):
        """Initialize with MetadataService and query helper"""
        self.metadata_service = MetadataService(debug=False)
        self.query = None  # Will be initialized on first use
        
    def filter_metadata(self, folder_path: str, field_type: str, operation: str, value: str, 
                       value2: str = "", limit: int = 10, load_images: bool = False, 
                       use_database: bool = True, additional_query: str = "",
                       recursive_search: bool = False, debug_logging: bool = False):
        """Filter images based on metadata criteria"""
        try:
            # Initialize query with debug setting
            self.query = MetadataQuery(debug=debug_logging)
            
            # Enable debug logging if requested
            self.metadata_service.debug = debug_logging
            
            if debug_logging:
                print(f"[MetadataFilter] Starting search in {folder_path}")
                print(f"[MetadataFilter] Query: {field_type} {operation} {value}")
            
            # Build the query from UI parameters
            criteria = self._build_query_from_params(field_type, operation, value, value2)
            
            # Add any additional custom query criteria
            if additional_query and additional_query.strip():
                try:
                    additional_criteria = json.loads(additional_query)
                    # Merge the additional criteria with the main criteria
                    criteria.update(additional_criteria)
                    if debug_logging:
                        print(f"[MetadataFilter] Added additional criteria: {additional_criteria}")
                except json.JSONDecodeError:
                    print(f"[MetadataFilter] Warning: Invalid JSON in additional query: {additional_query}")
            
            start_time = time.time()
            
            # Use database if enabled
            if use_database:
                try:
                    # Access database handler through the metadata service
                    # This approach is more maintainable than directly importing the db
                    db_handler = self.metadata_service._get_db_handler()
                    if db_handler:
                        # Convert to database query format
                        db_criteria = self._convert_to_db_criteria(criteria)
                        
                        # Use search_images method from the database handler
                        results = db_handler.search_images(db_criteria, limit=limit)
                        
                        # Extract file paths from results
                        paths = [r.get("filepath", "") for r in results if r.get("filepath")]
                        
                        # Get total match count
                        total_matches = len(paths)
                        
                        if debug_logging:
                            print(f"[MetadataFilter] Database query found {total_matches} matches in {time.time() - start_time:.3f}s")
                        
                        # Load images if requested
                        images = self._load_images(paths) if load_images and paths else torch.zeros(1, 1, 1, 3)
                        return (",".join(paths), total_matches, images)
                    else:
                        if debug_logging:
                            print("[MetadataFilter] Database handler not available, falling back to direct search")
                except Exception as e:
                    print(f"[MetadataFilter] Database error: {str(e)}, falling back to direct search")
            
            # Direct search using metadata query
            if debug_logging:
                print("[MetadataFilter] Performing direct metadata search")
            
            # Determine metadata sources to check
            metadata_sources = ['embedded', 'xmp']
            if 'txt' in criteria.get('metadata_sources', []):
                metadata_sources.append('txt')
                
            # Use the updated MetadataQuery's find_images method with recursive search option
            results = self.query.find_images(
                folder_path, 
                criteria, 
                limit=limit, 
                recursive=recursive_search,
                search_embedded_workflow=True,
                metadata_sources=metadata_sources
            )
            
            paths = [r.get("path", "") for r in results if r.get("path")]
            
            # Get total match count - we need to run a separate query without limit
            try:
                # Only get the count, no need to process results
                total_match_results = self.query.find_images(
                    folder_path, 
                    criteria, 
                    limit=None, 
                    recursive=recursive_search,
                    search_embedded_workflow=True,
                    metadata_sources=metadata_sources
                )
                total_matches = len(total_match_results)
            except Exception as e:
                if debug_logging:
                    print(f"[MetadataFilter] Error getting total matches: {str(e)}")
                total_matches = len(paths)  # Fallback
            
            if debug_logging:
                print(f"[MetadataFilter] Direct query found {total_matches} matches in {time.time() - start_time:.3f}s")
            
            # Load images if requested
            images = self._load_images(paths) if load_images and paths else torch.zeros(1, 1, 1, 3)
            return (",".join(paths), total_matches, images)
            
        except Exception as e:
            print(f"[MetadataFilter] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return ("", 0, torch.zeros(1, 1, 1, 3))
        finally:
            # Ensure cleanup always happens
            self.cleanup()
    
    def _map_field_to_metadata_path(self, field_type: str) -> str:
        """Map UI field types to actual metadata paths"""
        field_mappings = {
            "keywords": "basic.keywords",
            "prompt": "ai_info.generation.prompt",
            "model": "ai_info.generation.model",
            "lora": "ai_info.generation.loras",
            "aesthetic_score": "analysis.aesthetic.score", 
            "technical_score": "analysis.technical.overall_score",
            "directory": "filepath"  # Special case
        }
        
        return field_mappings.get(field_type, field_type)
    
    def _build_query_from_params(self, field_type: str, operation: str, value: str, value2: str) -> Dict[str, Any]:
        """Build a structured query from UI parameters"""
        # Map the UI field type to the actual metadata path
        field_path = self._map_field_to_metadata_path(field_type)
        
        # Handle numeric fields
        if field_type in ["aesthetic_score", "technical_score"]:
            try:
                if operation == "greater_than":
                    return {field_path: {"greater_than": float(value)}}
                elif operation == "less_than":
                    return {field_path: {"less_than": float(value)}}
                elif operation == "between":
                    return {field_path: {"min": float(value), "max": float(value2)}}
                elif operation == "equals":
                    # For equals on numeric fields, use a tight range
                    num_val = float(value)
                    return {field_path: {"equals": num_val}}
                else:
                    return {field_path: {"greater_than": float(value)}}  # Default to greater_than
            except ValueError:
                print(f"[MetadataFilter] Warning: Invalid numeric value: {value}")
                return {field_path: {"greater_than": 0}}
                
        # Handle text fields
        elif field_type in ["keywords", "prompt", "model", "lora", "any_text"]:
            if operation == "contains":
                if field_type == "any_text":
                    # Special case: search across multiple fields
                    multi_field_criteria = {}
                    for text_field in ["basic.keywords", "ai_info.generation.prompt", "ai_info.generation.model"]:
                        multi_field_criteria[text_field] = {"contains": value}
                    # Use OR semantics between fields
                    return {"$or": list(multi_field_criteria.items())}
                else:
                    return {field_path: {"contains": value}}
            elif operation == "equals":
                return {field_path: {"equals": value}} 
            elif operation == "exists":
                # New operation in the updated MetadataQuery
                return {field_path: {"not_equals": None}}
            else:
                # Default to contains for text fields
                return {field_path: {"contains": value}}
                
        # Handle directory specifically 
        elif field_type == "directory":
            # Directory is a special case that looks at the file path
            if operation == "contains":
                return {field_path: {"contains": value}}
            elif operation == "equals":
                return {field_path: {"equals": value}}
            else:
                return {field_path: {"contains": value}}  # Default
                
        # Default fallback
        return {field_path: {"contains": value}}
    
    def _convert_to_db_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Convert metadata query format to database query format"""
        db_criteria = {}
        
        # Process the query to match the database search expected format
        for key, value in criteria.items():
            # Skip special keys
            if key.startswith('$'):
                continue
                
            # Handle different types of queries
            if isinstance(value, dict):
                # Complex query with operators
                if "min" in value and "max" in value:
                    # Range query
                    db_criteria[key] = {"op": "between", "values": [value["min"], value["max"]]}
                elif "min" in value:
                    # Greater than query
                    db_criteria[key] = {"op": ">", "value": value["min"]}
                elif "max" in value:
                    # Less than query
                    db_criteria[key] = {"op": "<", "value": value["max"]}
                elif "greater_than" in value:
                    # Greater than query
                    db_criteria[key] = {"op": ">", "value": value["greater_than"]}
                elif "less_than" in value:
                    # Less than query
                    db_criteria[key] = {"op": "<", "value": value["less_than"]}
                elif "contains" in value:
                    # Contains query
                    db_criteria[key] = {"op": "contains", "value": value["contains"]}
                elif "equals" in value:
                    # Equals query
                    db_criteria[key] = {"op": "=", "value": value["equals"]}
                elif "not_equals" in value:
                    # Not equals query
                    db_criteria[key] = {"op": "!=", "value": value["not_equals"]}
                elif "regex" in value:
                    # Regex query (new in updated MetadataQuery)
                    db_criteria[key] = {"op": "regex", "value": value["regex"]}
            else:
                # Simple value (equals)
                db_criteria[key] = {"op": "=", "value": value}
                
        return db_criteria
    
    def _load_images(self, image_paths: List[str]) -> torch.Tensor:
        """Load a list of images and convert to tensor"""
        try:
            # Load all images
            loaded_images = []
            for path in image_paths:
                if os.path.exists(path):
                    img = Image.open(path).convert('RGB')
                    img_np = np.array(img).astype(np.float32) / 255.0
                    loaded_images.append(img_np)
            
            # Stack images if any were loaded
            if loaded_images:
                # Stack along batch dimension
                image_tensor = torch.from_numpy(np.stack(loaded_images, axis=0))
                return image_tensor
            
            return torch.zeros(1, 1, 1, 3)
        except Exception as e:
            print(f"[MetadataFilter] Image loading error: {str(e)}")
            return torch.zeros(1, 1, 1, 3)
            
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
        
        if hasattr(self, 'query') and self.query is not None:
            self.query.cleanup()
            self.query = None

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "EnhancedMetadataFilterNode_V2": EnhancedMetadataFilterNode_V2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EnhancedMetadataFilterNode_V2": "Eric's Enhanced Metadata Filter V2"
}