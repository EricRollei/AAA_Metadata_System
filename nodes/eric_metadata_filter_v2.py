
"""
ComfyUI Node: Eric's Metadata Filter V2
Description: Search and filter images based on their metadata across a folder or database.
Uses the new MetadataService architecture for improved performance and compatibility.
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

Eric's Metadata Filter Node V2 - Updated March 2025

Search and filter images based on their metadata across a folder or database.
Uses the new MetadataService architecture for improved performance and compatibility.

Features:
- User-friendly query building (no JSON knowledge required)
- Searches across multiple metadata storage methods
- Support for numeric ranges, text matching, and existence checks
- Database integration for faster searches
- Returns image paths and optionally loads matched images
"""

import os
import torch
import numpy as np
import json
import time
import datetime
from PIL import Image
from typing import List, Dict, Any, Tuple, Optional, Union

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService
from AAA_Metadata_System.eric_metadata.utils.workflow_parser import WorkflowParser
from AAA_Metadata_System.eric_metadata.utils.workflow_extractor import WorkflowExtractor
from AAA_Metadata_System.eric_metadata.utils.workflow_metadata_processor import WorkflowMetadataProcessor

class MetadataFilterNodeV2:
    """Search for images by metadata across folders or database"""
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)
        self.search_cache = {}
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": ""}),
                "field_type": (["keywords", "aesthetic_score", "technical_score", 
                               "prompt", "model", "directory", "lora", "any_text", 
                               "rating", "faces", "blur", "custom"], 
                               {"default": "keywords"}),
                "operation": (["contains", "equals", "greater_than", "less_than", 
                              "between", "exists", "missing"], 
                             {"default": "contains"}),
                "value": ("STRING", {"default": ""}),
                "limit": ("INT", {"default": 10, "min": 1, "max": 1000}),
            },
            "optional": {
                # Secondary search value
                "value2": ("STRING", {"default": "", "placeholder": "For 'between' operation"}),
                # Custom query field
                "custom_field": ("STRING", {"default": "", "placeholder": "For custom field_type"}),
                # Search options
                "recursive_search": ("BOOLEAN", {"default": True}),
                "use_database": ("BOOLEAN", {"default": True}),
                "include_substrings": ("BOOLEAN", {"default": True}),
                "case_sensitive": ("BOOLEAN", {"default": False}),
                # Result options
                "load_images": ("BOOLEAN", {"default": False}),
                "skip_missing": ("BOOLEAN", {"default": True}),
                "sort_by": (["none", "filename", "modified_date", "created_date", "value"], 
                           {"default": "none"}),
                "sort_descending": ("BOOLEAN", {"default": False}),
                # Advanced options
                "advanced_query": ("STRING", {"default": "", "multiline": True})
            }
        }

    RETURN_TYPES = ("STRING", "INT", "IMAGE")
    RETURN_NAMES = ("matched_paths", "match_count", "images")
    FUNCTION = "filter_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def filter_metadata(self, 
                       folder_path: str, 
                       field_type: str, 
                       operation: str, 
                       value: str, 
                       limit: int = 10,
                       value2: str = "",
                       custom_field: str = "",
                       recursive_search: bool = True,
                       use_database: bool = True,
                       include_substrings: bool = True,
                       case_sensitive: bool = False,
                       load_images: bool = False,
                       skip_missing: bool = True,
                       sort_by: str = "none",
                       sort_descending: bool = False,
                       advanced_query: str = "") -> Tuple[str, int, torch.Tensor]:
        """
        Search for images with matching metadata
        
        Args:
            folder_path: Directory to search in
            field_type: Type of metadata field to search
            operation: Operation to use (contains, equals, etc.)
            value: Primary search value
            limit: Maximum number of results to return
            value2: Secondary search value (for 'between' operation)
            custom_field: Custom field path for 'custom' field_type
            recursive_search: Whether to search subdirectories
            use_database: Whether to use database for searching
            include_substrings: Whether to match substrings in text
            case_sensitive: Whether text matching is case sensitive
            load_images: Whether to load and return matched images
            skip_missing: Whether to skip files that don't exist
            sort_by: Sort results by this field
            sort_descending: Whether to sort in descending order
            advanced_query: Advanced JSON query string
            
        Returns:
            Tuple of (matched_paths, match_count, images)
        """
        try:
            start_time = time.time()
            
            # Validate folder_path
            if not folder_path:
                print("[MetadataFilter] No folder path provided")
                return "", 0, torch.zeros(1, 1, 1, 3)
            
            if not os.path.exists(folder_path):
                print(f"[MetadataFilter] Folder not found: {folder_path}")
                return "", 0, torch.zeros(1, 1, 1, 3)
            
            # Build the query from UI parameters
            query = self._build_query_from_params(
                field_type, operation, value, value2, custom_field,
                include_substrings, case_sensitive)
            
            # Add any additional custom query criteria
            if advanced_query and advanced_query.strip():
                try:
                    additional_criteria = json.loads(advanced_query)
                    # Merge the additional criteria with the main query
                    query = self._merge_queries(query, additional_criteria)
                except json.JSONDecodeError:
                    print(f"[MetadataFilter] Warning: Invalid JSON in advanced query")
            
            # Cache key for similar searches
            cache_key = f"{folder_path}:{json.dumps(query)}:{limit}:{recursive_search}:{sort_by}:{sort_descending}"
            
            # Check cache for recent identical search
            if cache_key in self.search_cache:
                cache_data = self.search_cache[cache_key]
                cache_time, paths, total_matches = cache_data
                
                # Use cache if it's recent (less than 30 seconds old)
                if time.time() - cache_time < 30:
                    print(f"[MetadataFilter] Using cached search results ({total_matches} matches)")
                    
                    # Load images if requested
                    if load_images and paths:
                        images = self._load_images(paths, skip_missing)
                    else:
                        images = torch.zeros(1, 1, 1, 3)
                        
                    return (",".join(paths), total_matches, images)
            
            # Search using appropriate method
            if use_database:
                # Try database search first
                try:
                    paths, total_matches = self._search_database(
                        query, limit, sort_by, sort_descending)
                    
                    print(f"[MetadataFilter] Database search found {total_matches} matches " +
                          f"in {time.time() - start_time:.3f}s")
                except Exception as e:
                    print(f"[MetadataFilter] Database search failed: {str(e)}")
                    print("[MetadataFilter] Falling back to direct file search")
                    paths, total_matches = self._search_files(
                        folder_path, query, limit, recursive_search,
                        sort_by, sort_descending, skip_missing)
            else:
                # Direct file search
                paths, total_matches = self._search_files(
                    folder_path, query, limit, recursive_search,
                    sort_by, sort_descending, skip_missing)
                
                print(f"[MetadataFilter] File search found {total_matches} matches " +
                      f"in {time.time() - start_time:.3f}s")
            
            # Update cache
            self.search_cache[cache_key] = (time.time(), paths, total_matches)
            
            # Load images if requested
            if load_images and paths:
                images = self._load_images(paths, skip_missing)
            else:
                images = torch.zeros(1, 1, 1, 3)
                
            return (",".join(paths), total_matches, images)
            
        except Exception as e:
            import traceback
            print(f"[MetadataFilter] Error: {str(e)}")
            traceback.print_exc()
            return ("", 0, torch.zeros(1, 1, 1, 3))
        finally:
            # Always ensure cleanup happens
            self.cleanup()
    
    def _build_query_from_params(self, 
                                field_type: str, 
                                operation: str, 
                                value: str, 
                                value2: str,
                                custom_field: str,
                                include_substrings: bool,
                                case_sensitive: bool) -> Dict[str, Any]:
        """Build a structured query from UI parameters"""
        # Handle custom field
        if field_type == "custom" and custom_field:
            field = custom_field
        else:
            field = field_type
            
        # Map field types to actual metadata paths
        field_mapping = {
            "aesthetic_score": "analysis.aesthetic.score",
            "technical_score": "analysis.technical.score",
            "blur": "analysis.technical.blur.score",
            "prompt": "ai_info.generation.prompt",
            "model": "ai_info.generation.model",
            "lora": "ai_info.generation.loras",
            "faces": "regions.faces",
            "rating": "basic.rating",
            "keywords": "basic.keywords"
        }
        
        # Use mapping or direct field name
        search_field = field_mapping.get(field, field)
        
        # Handle numeric fields
        if field_type in ["aesthetic_score", "technical_score", "blur", "rating"]:
            try:
                if operation == "greater_than":
                    return {"field": search_field, "op": "gt", "value": float(value)}
                elif operation == "less_than":
                    return {"field": search_field, "op": "lt", "value": float(value)}
                elif operation == "between":
                    return {"field": search_field, "op": "between", 
                            "min_value": float(value), "max_value": float(value2)}
                elif operation == "equals":
                    return {"field": search_field, "op": "eq", "value": float(value)}
                elif operation == "exists":
                    return {"field": search_field, "op": "exists"}
                elif operation == "missing":
                    return {"field": search_field, "op": "missing"}
                else:
                    return {"field": search_field, "op": "gt", "value": float(value)}
            except ValueError:
                print(f"[MetadataFilter] Warning: Invalid numeric value: {value}")
                return {"field": search_field, "op": "exists"}
                
        # Handle text fields
        elif field_type in ["keywords", "prompt", "model", "lora", "any_text", "custom"]:
            if operation == "contains":
                return {"field": search_field, "op": "contains", "value": value,
                        "substring": include_substrings, "case_sensitive": case_sensitive}
            elif operation == "equals":
                return {"field": search_field, "op": "eq", "value": value,
                        "case_sensitive": case_sensitive}
            elif operation == "exists":
                return {"field": search_field, "op": "exists"}
            elif operation == "missing":
                return {"field": search_field, "op": "missing"}
            else:
                return {"field": search_field, "op": "contains", "value": value,
                        "substring": include_substrings, "case_sensitive": case_sensitive}
                
        # Handle directory specifically 
        elif field_type == "directory":
            if operation == "contains":
                return {"field": "filepath", "op": "contains", "value": value,
                        "substring": include_substrings, "case_sensitive": case_sensitive}
            elif operation == "equals":
                return {"field": "filepath", "op": "eq", "value": value,
                        "case_sensitive": case_sensitive}
            else:
                return {"field": "filepath", "op": "contains", "value": value,
                        "substring": include_substrings, "case_sensitive": case_sensitive}
                
        # Default fallback
        return {"field": search_field, "op": "contains", "value": value}
    
    def _merge_queries(self, query1: Dict[str, Any], query2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two queries with AND logic"""
        if "and" in query1:
            # If query1 already has AND, add query2 to it
            if isinstance(query2, dict) and "and" in query2:
                # If both have AND, combine the lists
                return {"and": query1["and"] + query2["and"]}
            else:
                # Add query2 to query1's AND list
                return {"and": query1["and"] + [query2]}
        elif "and" in query2:
            # If only query2 has AND, add query1 to it
            return {"and": [query1] + query2["and"]}
        else:
            # Neither has AND, create new AND with both
            return {"and": [query1, query2]}
    
    def _search_database(self, 
                        query: Dict[str, Any], 
                        limit: int,
                        sort_by: str,
                        sort_descending: bool) -> Tuple[List[str], int]:
        """Search for images using the database"""
        # Get database handler through service
        db_handler = self.metadata_service._get_db_handler()
        if not db_handler:
            raise ValueError("Database handler not available")
        
        # Convert query to database format if needed
        db_query = self._convert_to_db_format(query)
        
        # Determine sort field and direction
        sort_field = None
        if sort_by == "filename":
            sort_field = "filename"
        elif sort_by == "modified_date":
            sort_field = "updated_date"
        elif sort_by == "created_date":
            sort_field = "created_date"
        # "value" sort and "none" handled separately
        
        # Execute search
        results = db_handler.search_images(
            db_query, 
            limit=limit if limit > 0 else None,
            order_by=sort_field,
            descending=sort_descending
        )
        
        # Get matching file paths
        paths = [r.get("filepath", "") for r in results if r.get("filepath")]
        
        # For "value" sorting, we need to extract and sort by the search field
        if sort_by == "value" and "field" in query:
            # This would need custom sorting logic based on query field
            # Simplified implementation for now
            pass
        
        # Get total count (might be different from len(paths) if limit applied)
        try:
            # This assumes the database handler has a count_matches method
            # You might need to implement this or use a different approach
            total_matches = db_handler.count_matches(db_query)
        except:
            total_matches = len(paths)
        
        return paths, total_matches
    
    def _search_files(self,
                     folder_path: str,
                     query: Dict[str, Any],
                     limit: int,
                     recursive: bool,
                     sort_by: str,
                     sort_descending: bool,
                     skip_missing: bool) -> Tuple[List[str], int]:
        """Search for images by scanning files and checking metadata"""
        matching_paths = []
        total_checked = 0
        
        # Get all image files in the folder
        image_paths = self._get_image_files(folder_path, recursive)
        
        # Check each file's metadata
        for filepath in image_paths:
            total_checked += 1
            
            # Skip files that don't exist if requested
            if skip_missing and not os.path.exists(filepath):
                continue
            
            # Read metadata (with fallback across storage methods)
            try:
                metadata = self.metadata_service.read_metadata(filepath, fallback=True)
                
                # Check if this file matches the query
                if self._matches_query(filepath, metadata, query):
                    matching_paths.append(filepath)
                    
                    # Stop if we've reached the limit
                    if limit > 0 and len(matching_paths) >= limit:
                        break
            except Exception as e:
                print(f"[MetadataFilter] Error reading metadata for {filepath}: {str(e)}")
        
        # Apply sorting if requested
        if sort_by != "none" and matching_paths:
            matching_paths = self._sort_results(
                matching_paths, sort_by, sort_descending, query)
        
        # Count total matches (might be limited by limit parameter)
        total_matches = len(matching_paths)
        
        return matching_paths, total_matches
    
    def _get_image_files(self, folder_path: str, recursive: bool) -> List[str]:
        """Get all image files in a folder"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif']
        image_files = []
        
        if recursive:
            # Walk through all subdirectories
            for root, _, files in os.walk(folder_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in image_extensions:
                        image_files.append(os.path.join(root, file))
        else:
            # Only check the specified directory
            for file in os.listdir(folder_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions:
                    image_files.append(os.path.join(folder_path, file))
        
        return image_files
    
    def _matches_query(self, filepath: str, metadata: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if metadata matches the query"""
        # Handle compound queries (AND/OR)
        if "and" in query:
            return all(self._matches_query(filepath, metadata, subquery) 
                      for subquery in query["and"])
        elif "or" in query:
            return any(self._matches_query(filepath, metadata, subquery) 
                      for subquery in query["or"])
        
        # Get field, operation and value from query
        field = query.get("field", "")
        op = query.get("op", "")
        value = query.get("value", "")
        
        # Special case for filepath
        if field == "filepath":
            return self._check_field_match(op, filepath, value, query)
        
        # Get field value using dot notation path
        field_value = self._get_field_value(metadata, field)
        
        # Check match based on operation
        return self._check_field_match(op, field_value, value, query)
    
    def _get_field_value(self, metadata: Dict[str, Any], field_path: str) -> Any:
        """Get a value from a nested dictionary using dot notation path"""
        if not field_path:
            return None
        
        # Handle special case for any_text
        if field_path == "any_text":
            # Convert metadata to string for full-text search
            return json.dumps(metadata)
        
        # Split path by dots
        parts = field_path.split(".")
        
        # Navigate the nested structure
        current = metadata
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _check_field_match(self, op: str, field_value: Any, search_value: Any, query: Dict[str, Any]) -> bool:
        """Check if a field matches based on the operation"""
        # Handle missing values
        if field_value is None:
            return op == "missing"
        
        # Existence check
        if op == "exists":
            return field_value is not None
        elif op == "missing":
            return field_value is None
        
        # Handle lists (e.g., keywords)
        if isinstance(field_value, list):
            # For lists, check if any item matches
            if op == "contains":
                substring = query.get("substring", True)
                case_sensitive = query.get("case_sensitive", False)
                
                # Convert list items to strings for text matching
                for item in field_value:
                    item_str = str(item)
                    if self._text_matches(item_str, search_value, substring, case_sensitive):
                        return True
                return False
            elif op == "eq":
                # For equals, check if the value is in the list
                return search_value in field_value
            elif op in ["gt", "lt", "between"]:
                # For numeric operations on lists, check if any item satisfies
                for item in field_value:
                    if isinstance(item, (int, float)):
                        if self._numeric_matches(op, item, search_value, query):
                            return True
                return False
        
        # Text matching for strings
        elif isinstance(field_value, str):
            if op == "contains" or op == "eq":
                substring = query.get("substring", True) and op == "contains"
                case_sensitive = query.get("case_sensitive", False)
                return self._text_matches(field_value, search_value, substring, case_sensitive)
        
        # Numeric matching for numbers
        elif isinstance(field_value, (int, float)):
            return self._numeric_matches(op, field_value, search_value, query)
        
        # Default: convert to string and do text matching
        else:
            if op == "contains" or op == "eq":
                substring = query.get("substring", True) and op == "contains"
                case_sensitive = query.get("case_sensitive", False)
                return self._text_matches(str(field_value), str(search_value), 
                                         substring, case_sensitive)
        
        return False
    
    def _text_matches(self, text: str, search: str, substring: bool, case_sensitive: bool) -> bool:
        """Check if text matches search string"""
        if not case_sensitive:
            text = text.lower()
            search = search.lower()
        
        if substring:
            return search in text
        else:
            return text == search
    
    def _numeric_matches(self, op: str, value: float, search: Any, query: Dict[str, Any]) -> bool:
        """Check if numeric value matches based on operation"""
        if op == "eq":
            # Handle numeric equality with small tolerance
            try:
                return abs(value - float(search)) < 0.0001
            except (ValueError, TypeError):
                return False
        elif op == "gt":
            try:
                return value > float(search)
            except (ValueError, TypeError):
                return False
        elif op == "lt":
            try:
                return value < float(search)
            except (ValueError, TypeError):
                return False
        elif op == "between":
            try:
                min_val = float(query.get("min_value", 0))
                max_val = float(query.get("max_value", 0))
                return min_val <= value <= max_val
            except (ValueError, TypeError):
                return False
        
        return False
    
    def _sort_results(self, 
                     paths: List[str], 
                     sort_by: str, 
                     descending: bool,
                     query: Dict[str, Any]) -> List[str]:
        """Sort results by the specified field"""
        if sort_by == "filename":
            # Sort by filename
            return sorted(paths, key=os.path.basename, reverse=descending)
        elif sort_by == "modified_date":
            # Sort by file modification time
            return sorted(paths, key=os.path.getmtime, reverse=descending)
        elif sort_by == "created_date":
            # Sort by file creation time (not available on all platforms)
            try:
                return sorted(paths, key=os.path.getctime, reverse=descending)
            except:
                return sorted(paths, key=os.path.getmtime, reverse=descending)
        elif sort_by == "value" and "field" in query:
            # Sort by the query field value (complex, requires reading metadata again)
            field_path = query.get("field")
            
            def get_sort_value(path):
                try:
                    metadata = self.metadata_service.read_metadata(path, fallback=True)
                    value = self._get_field_value(metadata, field_path)
                    
                    # Handle different value types
                    if isinstance(value, (int, float)):
                        return value
                    elif isinstance(value, list) and value and isinstance(value[0], (int, float)):
                        return value[0]  # Use first value for lists
                    elif isinstance(value, list) and value:
                        return str(value[0])  # String conversion for non-numeric lists
                    elif isinstance(value, str):
                        return value.lower()  # Case-insensitive sorting for strings
                    else:
                        return str(value)
                except Exception:
                    # Return a default value that works for the expected type
                    return "" if isinstance(query.get("value", ""), str) else 0
            
            return sorted(paths, key=get_sort_value, reverse=descending)
        
        # Default: return unsorted
        return paths
    
    def _convert_to_db_format(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Convert query to database format if needed"""
        # Simple pass-through for now
        # This could be expanded to handle format differences
        return query
    
    def _load_images(self, image_paths: List[str], skip_missing: bool) -> torch.Tensor:
        """Load a list of images and convert to tensor"""
        try:
            # Load all images
            loaded_images = []
            for path in image_paths:
                if not os.path.exists(path):
                    if skip_missing:
                        continue
                    else:
                        # Create a small placeholder for missing images
                        img_np = np.zeros((64, 64, 3), dtype=np.float32)
                        loaded_images.append(img_np)
                        continue
                
                try:
                    img = Image.open(path).convert('RGB')
                    img_np = np.array(img).astype(np.float32) / 255.0
                    loaded_images.append(img_np)
                except Exception as e:
                    print(f"[MetadataFilter] Error loading image {path}: {str(e)}")
                    if not skip_missing:
                        # Add placeholder for error images
                        img_np = np.zeros((64, 64, 3), dtype=np.float32)
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
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Metadata_Filter_V2": MetadataFilterNodeV2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Metadata_Filter_V2": "Eric's Metadata Filter V2"
}