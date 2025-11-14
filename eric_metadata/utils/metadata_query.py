"""
MetadataQuery Utility - March 2025
Description: Utility for querying images based on metadata criteria. This utility provides functions for searching and filtering images based on metadata criteria.
    It integrates with the MetadataService for consistent metadata handling.
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

import os
import glob
from typing import List, Dict, Any, Optional, Union, Set
import json
import re
from AAA_Metadata_System import MetadataService
from AAA_Metadata_System.eric_metadata.utils.workflow_parser import WorkflowParser

class MetadataQuery:
    """Utility for querying images based on metadata criteria"""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the metadata query utility
        
        Args:
            debug: Whether to enable debug logging
        """
        self.debug = debug
        self.metadata_service = MetadataService(debug=debug)
        self.workflow_parser = WorkflowParser(debug=debug)
    
    def find_images(self, folder_path: str, criteria: Dict[str, Any], 
                  limit: int = None, recursive: bool = False,
                  search_embedded_workflow: bool = True,
                  metadata_sources: List[str] = None) -> List[Dict[str, Any]]:
        """
        Find images matching complex metadata criteria
        
        Args:
            folder_path: Path to image folder
            criteria: Dict of metadata criteria
            limit: Maximum number of results to return
            recursive: Whether to search subfolders recursively
            search_embedded_workflow: Whether to search PNG embedded workflows
            metadata_sources: List of metadata sources to check ('embedded', 'xmp', 'txt', 'db')
                             If None, defaults to ['embedded', 'xmp']
            
        Returns:
            List of dicts with image path and relevant metadata
        """
        # Set default metadata sources if not specified
        if metadata_sources is None:
            metadata_sources = ['embedded', 'xmp']
        
        # Get all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.tiff', '*.tif']:
            if recursive:
                pattern = os.path.join(folder_path, '**', ext)
                image_files.extend(glob.glob(pattern, recursive=True))
            else:
                pattern = os.path.join(folder_path, ext)
                image_files.extend(glob.glob(pattern))
        
        # Log count of files found
        if self.debug:
            print(f"[MetadataQuery] Found {len(image_files)} image files to search")
        
        results = []
        
        for img_path in image_files:
            # First read metadata using service (will try sources in order)
            metadata = self.metadata_service.read_metadata(img_path, fallback=True)
            
            # For PNGs, also check embedded workflow if needed and if not already extracted
            if (search_embedded_workflow and 
                img_path.lower().endswith('.png') and
                (not metadata or 'ai_info' not in metadata or 'workflow' not in metadata.get('ai_info', {}))):
                
                # Extract workflow and convert to metadata format
                workflow_data = self._extract_workflow_data(img_path)
                if workflow_data:
                    # Merge workflow data with existing metadata
                    if not metadata:
                        metadata = {}
                    
                    # Merge with existing metadata
                    metadata = self.metadata_service._merge_metadata(metadata, workflow_data)
            
            # Check if image matches all criteria
            if self._matches_criteria(metadata, criteria):
                score = self._calculate_score(metadata, criteria)
                results.append({
                    'path': img_path,
                    'score': score,
                    'metadata': self._extract_relevant_metadata(metadata, criteria)
                })
        
        # Sort by score (if sorting criteria provided)
        if 'sort_by' in criteria:
            results.sort(key=lambda x: x['score'], reverse=criteria.get('sort_order', 'desc') == 'desc')
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            results = results[:limit]
            
        # Log results count
        if self.debug:
            print(f"[MetadataQuery] Found {len(results)} matching images")
            
        return results
    
    def _extract_workflow_data(self, img_path: str) -> Dict[str, Any]:
        """
        Extract workflow data from PNG and convert to metadata format
        
        Args:
            img_path: Path to PNG file
            
        Returns:
            dict: Workflow data in metadata format
        """
        try:
            # Use the workflow parser to extract complete data
            return self.workflow_parser.extract_and_convert_to_ai_metadata(img_path)
        except Exception as e:
            if self.debug:
                print(f"[MetadataQuery] Error extracting workflow: {str(e)}")
            return {}
    
    def _matches_criteria(self, metadata: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """
        Check if metadata matches all criteria
        
        Args:
            metadata: Metadata dictionary
            criteria: Criteria dictionary
            
        Returns:
            bool: True if metadata matches all criteria
        """
        for field, condition in criteria.items():
            # Skip special fields like sort_by
            if field in ['sort_by', 'sort_order']:
                continue
                
            # Handle nested fields using dot notation
            value = self._get_nested_value(metadata, field)
            
            # Different condition types
            if isinstance(condition, dict):
                # Check all condition requirements
                for op, check_value in condition.items():
                    if not self._evaluate_condition(value, op, check_value):
                        return False
            else:
                # Simple equality check
                if value != condition:
                    return False
                    
        return True
    
    def _evaluate_condition(self, value: Any, op: str, check_value: Any) -> bool:
        """
        Evaluate a single condition
        
        Args:
            value: The value to check
            op: Operation ('min', 'max', 'equals', etc.)
            check_value: The value to check against
            
        Returns:
            bool: Whether the condition is met
        """
        if op == 'min':
            return value is not None and value >= check_value
        elif op == 'max':
            return value is not None and value <= check_value
        elif op == 'equals':
            return value == check_value
        elif op == 'not_equals':
            return value != check_value
        elif op == 'contains':
            return self._contains_value(value, check_value)
        elif op == 'contains_all':
            return self._contains_all_values(value, check_value)
        elif op == 'contains_any':
            return self._contains_any_values(value, check_value)
        elif op == 'regex':
            return self._matches_regex(value, check_value)
        elif op == 'greater_than':
            return value is not None and value > check_value
        elif op == 'less_than':
            return value is not None and value < check_value
        else:
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Get value from nested dict using dot notation path
        
        Args:
            data: Data dictionary
            field_path: Field path with dot notation (e.g., 'ai_info.generation.model')
            
        Returns:
            The value at the specified path or None if not found
        """
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
            
        return current
    
    def _contains_value(self, container: Any, value: Any) -> bool:
        """
        Check if container contains value (handles different container types)
        
        Args:
            container: Container to search in
            value: Value to search for
            
        Returns:
            bool: True if value is found
        """
        if container is None:
            return False
            
        if isinstance(container, str):
            return value.lower() in container.lower()  # Case-insensitive search for strings
            
        if isinstance(container, (list, tuple, set)):
            # For string values in lists, do case-insensitive comparison
            if all(isinstance(item, str) for item in container):
                return any(value.lower() == item.lower() for item in container)
            return value in container
            
        if isinstance(container, dict):
            return value in container or value in container.values()
            
        return False
    
    def _contains_all_values(self, container: Any, values: List[Any]) -> bool:
        """
        Check if container contains all values in the list
        
        Args:
            container: Container to search in
            values: List of values to search for
            
        Returns:
            bool: True if all values are found
        """
        return all(self._contains_value(container, value) for value in values)
    
    def _contains_any_values(self, container: Any, values: List[Any]) -> bool:
        """
        Check if container contains any value in the list
        
        Args:
            container: Container to search in
            values: List of values to search for
            
        Returns:
            bool: True if any value is found
        """
        return any(self._contains_value(container, value) for value in values)
    
    def _matches_regex(self, value: Any, pattern: str) -> bool:
        """
        Check if value matches regex pattern
        
        Args:
            value: Value to check
            pattern: Regex pattern
            
        Returns:
            bool: True if matches
        """
        if not isinstance(value, str):
            return False
            
        try:
            return bool(re.search(pattern, value))
        except:
            return False
    
    def _calculate_score(self, metadata: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """
        Calculate score for sorting based on criteria
        
        Args:
            metadata: Metadata dictionary
            criteria: Criteria dictionary
            
        Returns:
            float: Score for sorting
        """
        # Get sort field
        sort_field = criteria.get('sort_by')
        if not sort_field:
            return 0.0
            
        # Get value from metadata
        value = self._get_nested_value(metadata, sort_field)
        
        # Handle different value types
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            return len(value)  # String length as score
        elif isinstance(value, (list, tuple, set)):
            return len(value)  # Container length as score
        elif isinstance(value, dict):
            return len(value)  # Dict size as score
            
        return 0.0
    
    def _extract_relevant_metadata(self, metadata: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only metadata fields relevant to the criteria
        
        Args:
            metadata: Complete metadata
            criteria: Criteria used for filtering
            
        Returns:
            dict: Subset of metadata with relevant fields
        """
        result = {}
        
        # Get fields mentioned in criteria
        fields = list(criteria.keys())
        
        # Add sort field if present
        if 'sort_by' in criteria:
            fields.append(criteria['sort_by'])
            
        # Extract each field
        for field in fields:
            # Skip special fields
            if field in ['sort_by', 'sort_order']:
                continue
                
            value = self._get_nested_value(metadata, field)
            if value is not None:
                # Build nested structure
                self._set_nested_value(result, field, value)
                
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], field_path: str, value: Any) -> None:
        """
        Set value in nested dict using dot notation path
        
        Args:
            data: Data dictionary to update
            field_path: Field path with dot notation
            value: Value to set
        """
        parts = field_path.split('.')
        current = data
        
        # Create nested dictionaries
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
            
        # Set the final value
        current[parts[-1]] = value

    def get_unique_values(self, folder_path: str, field_path: str,
                        recursive: bool = False) -> Set[Any]:
        """
        Get set of unique values for a specific metadata field across images
        
        Args:
            folder_path: Path to image folder
            field_path: Field path with dot notation
            recursive: Whether to search subfolders recursively
            
        Returns:
            set: Set of unique values
        """
        # Find all images without any filtering criteria
        results = self.find_images(folder_path, {'sort_by': field_path}, recursive=recursive)
        
        # Extract unique values for the specified field
        unique_values = set()
        for result in results:
            value = self._get_nested_value(result['metadata'], field_path)
            if value is not None:
                if isinstance(value, (list, tuple, set)):
                    for item in value:
                        unique_values.add(item)
                else:
                    unique_values.add(value)
        
        return unique_values
    
    def get_value_counts(self, folder_path: str, field_path: str,
                       recursive: bool = False) -> Dict[Any, int]:
        """
        Get count of occurrences for each unique value of a field
        
        Args:
            folder_path: Path to image folder
            field_path: Field path with dot notation
            recursive: Whether to search subfolders recursively
            
        Returns:
            dict: Mapping of values to counts
        """
        # Find all images without any filtering criteria
        results = self.find_images(folder_path, {'sort_by': field_path}, recursive=recursive)
        
        # Count occurrences of each value
        value_counts = {}
        for result in results:
            value = self._get_nested_value(result['metadata'], field_path)
            if value is not None:
                if isinstance(value, (list, tuple, set)):
                    for item in value:
                        value_counts[item] = value_counts.get(item, 0) + 1
                else:
                    value_counts[value] = value_counts.get(value, 0) + 1
        
        return value_counts
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
            
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
