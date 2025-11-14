"""
service.py
Description: Unified interface for metadata operations
    This service coordinates between different handlers to provide
    a simple interface for reading and writing metadata.
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
# Metadata_system/src/eric_metadata/service.py
import os
from typing import Dict, Any, List, Optional, Union, Set, Tuple
import datetime

from .handlers.base import BaseHandler
from .handlers.xmp import XMPSidecarHandler
from .utils.format_detect import FormatHandler

class MetadataService:
    """
    Unified interface for metadata operations
    
    This service coordinates between different handlers to provide
    a simple interface for reading and writing metadata.
    """
    
    def __init__(self, debug: bool = False, human_readable_text: bool = True):
        """
        Initialize the metadata service
        
        Args:
            debug: Whether to enable debug logging
            human_readable_text: Whether to use human-readable format for text files
        """
        self.debug = debug
        self.human_readable_text = human_readable_text
        
        # Initialize handlers on demand
        self._embedded_handler = None
        self._xmp_handler = None
        self._txt_handler = None
        self._db_handler = None
        
        # Cache for format info
        self._format_cache = {}
    
    def write_metadata(self, filepath: str, metadata: Dict[str, Any], 
                    targets: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Write metadata to specified targets with proper merging
        
        Args:
            filepath: Path to image file
            metadata: Metadata to write
            targets: List of targets ('embedded', 'xmp', 'txt', 'db')
                    If None, writes to all available targets
        
        Returns:
            dict: Status of each write operation
        """
        if targets is None:
            targets = ['embedded', 'xmp', 'txt', 'db']
            
        results = {}
        
        # Get file format info
        format_info = self._get_format_info(filepath)
        
        # Track errors for logging
        errors = []
        
        # Get existing metadata for merging
        existing_metadata = self.read_metadata(filepath, fallback=True)
        merged_metadata = self._merge_metadata(existing_metadata, metadata) if existing_metadata else metadata
        
        # Process each target
        for target in targets:
            try:
                if target == 'embedded':
                    if format_info.get('can_use_pyexiv2', False) or format_info.get('requires_exiftool', False):
                        handler = self._get_embedded_handler()
                        results['embedded'] = handler.write_metadata(filepath, merged_metadata)
                    else:
                        # Skip if format doesn't support embedded metadata
                        results['embedded'] = False
                        
                elif target == 'xmp':
                    handler = self._get_xmp_handler()
                    results['xmp'] = handler.write_metadata(filepath, merged_metadata)
                    
                elif target == 'txt':
                    handler = self._get_txt_handler()
                    # Configure text handler to use human-readable format if enabled
                    handler.set_output_format(human_readable=self.human_readable_text)
                    results['txt'] = handler.write_metadata(filepath, merged_metadata)
                    
                elif target == 'db':
                    handler = self._get_db_handler()
                    if handler:  # DB handler is optional
                        results['db'] = handler.write_metadata(filepath, merged_metadata)
                    else:
                        results['db'] = False
                else:
                    self._log(f"Unknown target: {target}", level="WARNING")
                    results[target] = False
            except Exception as e:
                self._log(f"Error writing to {target}: {str(e)}", level="ERROR")
                results[target] = False
                errors.append(f"{target}: {str(e)}")
        
        # Log summary
        if all(results.values()):
            self._log(f"Successfully wrote metadata to all targets: {', '.join(targets)}")
        elif any(results.values()):
            successful = [t for t, result in results.items() if result]
            failed = [t for t, result in results.items() if not result]
            self._log(f"Partially wrote metadata. Success: {', '.join(successful)}. Failed: {', '.join(failed)}")
        else:
            self._log(f"Failed to write metadata to any target. Errors: {'; '.join(errors)}", level="ERROR")
            
        return results
    def read_metadata(self, filepath: str, source: str = 'embedded',
                     fallback: bool = True) -> Dict[str, Any]:
        """
        Read metadata from specified source
        
        Args:
            filepath: Path to image file
            source: Source to read from ('embedded', 'xmp', 'txt', 'db')
            fallback: Whether to try other sources if primary fails
            
        Returns:
            dict: Metadata from specified source
        """
        result = {}
        tried_sources = []
        
        # Order of fallback attempts if primary source fails
        fallback_order = ['embedded', 'xmp', 'txt', 'db']
        if source in fallback_order:
            # Move the requested source to the front
            fallback_order.remove(source)
            fallback_order.insert(0, source)
        else:
            # Source not in standard list, add it first
            fallback_order.insert(0, source)
        
        # Try each source until success or all fails
        for src in fallback_order:
            # Skip after first success if not in fallback mode
            if tried_sources and not fallback:
                break
                
            tried_sources.append(src)
            
            try:
                if src == 'embedded':
                    format_info = self._get_format_info(filepath)
                    if format_info.get('can_use_pyexiv2', False) or format_info.get('requires_exiftool', False):
                        handler = self._get_embedded_handler()
                        result = handler.read_metadata(filepath)
                    else:
                        continue  # Skip to next source
                        
                elif src == 'xmp':
                    handler = self._get_xmp_handler()
                    xmp_result = handler.read_metadata(filepath)
                    if xmp_result:
                        result = xmp_result
                    else:
                        continue  # Skip to next source
                        
                elif src == 'txt':
                    handler = self._get_txt_handler()
                    txt_result = handler.read_metadata(filepath)
                    if txt_result:
                        result = txt_result
                    else:
                        continue  # Skip to next source
                        
                elif src == 'db':
                    handler = self._get_db_handler()
                    if handler:  # DB handler is optional
                        db_result = handler.read_metadata(filepath)
                        if db_result:
                            result = db_result
                        else:
                            continue  # Skip to next source
                    else:
                        continue  # Skip to next source
                        
                else:
                    self._log(f"Unknown source: {src}", level="WARNING")
                    continue  # Skip to next source
                    
                # If we got here with data, break the loop
                if result:
                    break
                    
            except Exception as e:
                self._log(f"Error reading from {src}: {str(e)}", level="WARNING")
                continue  # Try next source
        
        # Log result summary
        if result:
            self._log(f"Successfully read metadata from {tried_sources[-1]}")
        else:
            self._log(f"Failed to read metadata from any source: {', '.join(tried_sources)}", level="WARNING")
            
        return result
    
    def merge_metadata(self, filepath: str, metadata: Dict[str, Any],
                      targets: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Merge new metadata with existing metadata
        
        Args:
            filepath: Path to image file
            metadata: New metadata to merge
            targets: List of targets to update
            
        Returns:
            dict: Status of each merge operation
        """
        results = {}
        
        # Get existing metadata
        existing = self.read_metadata(filepath, fallback=True)
        
        if not existing:
            # No existing metadata, just write new
            return self.write_metadata(filepath, metadata, targets)
            
        # Perform merge
        merged = self._merge_metadata(existing, metadata)
        
        # Write merged metadata
        return self.write_metadata(filepath, merged, targets)
    
    def _merge_metadata(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge existing and new metadata intelligently
        
        Args:
            existing: Existing metadata
            new: New metadata
            
        Returns:
            dict: Merged metadata
        """
        # Request XMP handler to perform the merge (it has the most robust merge logic)
        handler = self._get_xmp_handler()
        # Use the private method directly for merging without writing
        if hasattr(handler, '_merge_metadata'):
            return handler._merge_metadata(existing, new)
        
        # Fallback if XMP handler doesn't have the method
        result = existing.copy()
        
        # Merge section by section
        for section, data in new.items():
            if section not in result:
                # New section, just add it
                result[section] = data
            elif section == 'basic':
                # Special handling for basic metadata
                if 'basic' not in result:
                    result['basic'] = {}
                    
                # Merge basic fields
                for key, value in data.items():
                    if key == 'keywords':
                        # Combine keywords
                        existing_keywords = set(result['basic'].get('keywords', []))
                        new_keywords = set(value if isinstance(value, (list, set)) else [value])
                        result['basic']['keywords'] = list(existing_keywords | new_keywords)
                    else:
                        # Replace other fields
                        result['basic'][key] = value
            elif section == 'analysis':
                # Special handling for analysis data
                if 'analysis' not in result:
                    result['analysis'] = {}
                    
                # Merge each analysis type
                for analysis_type, analysis_data in data.items():
                    if analysis_type not in result['analysis']:
                        result['analysis'][analysis_type] = analysis_data
                    elif isinstance(analysis_data, dict) and isinstance(result['analysis'][analysis_type], dict):
                        # Recursive merge for nested analysis data
                        for key, value in analysis_data.items():
                            if key not in result['analysis'][analysis_type]:
                                result['analysis'][analysis_type][key] = value
                            elif isinstance(value, dict) and isinstance(result['analysis'][analysis_type][key], dict):
                                # Deep merge for nested dictionaries
                                result['analysis'][analysis_type][key].update(value)
                            else:
                                # Replace with newer value
                                result['analysis'][analysis_type][key] = value
                    else:
                        # Replace with newer value
                        result['analysis'][analysis_type] = analysis_data
            elif section == 'regions':
                # Special handling for regions
                if 'regions' not in result:
                    result['regions'] = data
                else:
                    # Merge faces with overlap detection
                    if 'faces' in data:
                        if 'faces' not in result['regions']:
                            result['regions']['faces'] = []
                            
                        # Get existing face regions
                        existing_faces = result['regions'].get('faces', [])
                        
                        # Add new faces that don't overlap existing ones
                        for new_face in data.get('faces', []):
                            # Flag to track if we found an overlap
                            overlap_found = False
                            
                            # Check for overlapping faces
                            for i, existing_face in enumerate(existing_faces):
                                if self._regions_overlap(new_face, existing_face):
                                    # We found an overlap, update with new data if it has extensions
                                    if 'extensions' in new_face:
                                        existing_faces[i] = new_face
                                    overlap_found = True
                                    break
                                    
                            # If no overlap, add the new face
                            if not overlap_found:
                                existing_faces.append(new_face)
                                
                        # Update the faces list
                        result['regions']['faces'] = existing_faces
                        
                    # Update summary
                    if 'summary' in data:
                        if 'summary' not in result['regions']:
                            result['regions']['summary'] = {}
                            
                        result['regions']['summary'].update(data['summary'])
                        
                        # Make sure face count is correct
                        result['regions']['summary']['face_count'] = len(result['regions'].get('faces', []))
            elif section == 'ai_info':
                # Special handling for AI generation info
                if 'ai_info' not in result:
                    result['ai_info'] = data
                else:
                    # Preserve existing fields, add new ones
                    for key, value in data.items():
                        if key not in result['ai_info']:
                            result['ai_info'][key] = value
                        elif key == 'generation':
                            # Special handling for generation data
                            if 'generation' not in result['ai_info']:
                                result['ai_info']['generation'] = {}
                                
                            # Only update missing fields, preserving existing values
                            for gen_key, gen_value in value.items():
                                if gen_key not in result['ai_info']['generation'] or not result['ai_info']['generation'][gen_key]:
                                    result['ai_info']['generation'][gen_key] = gen_value
                        else:
                            # Update other sections
                            result['ai_info'][key] = value
            else:
                # Default handling for other sections
                result[section] = data
                
        return result
    
    def _regions_overlap(self, region1: Dict[str, Any], region2: Dict[str, Any], threshold: float = 0.5) -> bool:
        """
        Check if two regions overlap significantly
        
        Args:
            region1: First region
            region2: Second region
            threshold: IoU threshold (0-1)
            
        Returns:
            bool: True if regions overlap significantly
        """
        try:
            # Extract areas
            area1 = region1.get('area', {})
            area2 = region2.get('area', {})
            
            # Get coordinates
            x1, y1 = area1.get('x', 0), area1.get('y', 0)
            w1, h1 = area1.get('w', 0), area1.get('h', 0)
            
            x2, y2 = area2.get('x', 0), area2.get('y', 0)
            w2, h2 = area2.get('w', 0), area2.get('h', 0)
            
            # Calculate intersection
            x_intersection = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_intersection = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            intersection_area = x_intersection * y_intersection
            
            # Calculate areas
            area1_size = w1 * h1
            area2_size = w2 * h2
            
            # Calculate IoU
            union_area = area1_size + area2_size - intersection_area
            if union_area <= 0:
                return False
                
            iou = intersection_area / union_area
            return iou > threshold
            
        except Exception as e:
            self._log(f"Error checking region overlap: {str(e)}", level="WARNING")
            return False

    def get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        return datetime.datetime.now().isoformat()

    def set_resource_identifier(self, resource_uri: str) -> None:
        """Set resource identifier for all handlers"""
        # Set for XMP handler
        xmp_handler = self._get_xmp_handler()
        if xmp_handler:
            xmp_handler.set_resource_identifier(resource_uri)
        
        # Set for embedded handler
        embedded_handler = self._get_embedded_handler()
        if embedded_handler:
            embedded_handler.set_resource_identifier(resource_uri)
    
    def set_text_format(self, human_readable: bool) -> None:
        """
        Set the text output format
        
        Args:
            human_readable: Whether to use human-readable format for text files
        """
        self.human_readable_text = human_readable
        
        # Update the handler if it's already initialized
        if self._txt_handler is not None:
            self._txt_handler.set_output_format(human_readable=human_readable)
    
    def _get_embedded_handler(self) -> BaseHandler:
        """Get embedded metadata handler (lazy initialization)"""
        if self._embedded_handler is None:
            from .handlers.embedded import EmbeddedMetadataHandler
            self._embedded_handler = EmbeddedMetadataHandler(debug=self.debug)
        return self._embedded_handler
    
    def _get_xmp_handler(self) -> BaseHandler:
        """Get XMP sidecar handler (lazy initialization)"""
        if self._xmp_handler is None:
            from .handlers.xmp import XMPSidecarHandler
            self._xmp_handler = XMPSidecarHandler(debug=self.debug)
        return self._xmp_handler
    
    def _get_txt_handler(self) -> BaseHandler:
        """Get text file handler (lazy initialization)"""
        if self._txt_handler is None:
            from .handlers.txt import TxtFileHandler
            self._txt_handler = TxtFileHandler(debug=self.debug, human_readable=self.human_readable_text)
        return self._txt_handler
    
    def _get_db_handler(self) -> Optional[BaseHandler]:
        """Get database handler (lazy initialization)"""
        if self._db_handler is None:
            try:
                from .handlers.db import DatabaseHandler
                db_handler = DatabaseHandler(debug=self.debug)
                
                # Verify the handler has a valid connection
                if hasattr(db_handler, 'conn') and db_handler.conn is not None:
                    self._db_handler = db_handler
                else:
                    self._log("Database handler initialized but connection failed", level="WARNING")
                    return None
                    
            except ImportError:
                # Database handler is optional
                self._log("DatabaseHandler not available", level="DEBUG")
                return None
        return self._db_handler
    
    def _get_format_info(self, filepath: str) -> Dict[str, Any]:
        """
        Get cached format info for file
        
        Args:
            filepath: Path to file
            
        Returns:
            dict: Format information
        """
        if filepath not in self._format_cache:
            self._format_cache[filepath] = FormatHandler.get_file_info(filepath)
        return self._format_cache[filepath]
    
    def get_handler_for_format(self, filepath: str) -> Tuple[str, BaseHandler]:
        """
        Get appropriate handler for file format
        
        Args:
            filepath: Path to file
            
        Returns:
            tuple: (handler_type, handler)
        """
        format_info = self._get_format_info(filepath)
        
        if format_info.get('can_use_pyexiv2', False):
            return 'embedded', self._get_embedded_handler()
        elif format_info.get('requires_exiftool', False):
            return 'embedded', self._get_embedded_handler()
        else:
            # Default to XMP sidecar for unsupported formats
            return 'xmp', self._get_xmp_handler()
    
    def cleanup(self):
        """Clean up resources used by handlers"""
        handlers = [
            self._embedded_handler,
            self._xmp_handler,
            self._txt_handler,
            self._db_handler
        ]
        
        for handler in handlers:
            if handler is not None:
                handler.cleanup()
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        if level == "DEBUG" and not self.debug:
            return
            
        timestamp = self._get_timestamp()
        print(f"[{timestamp}] MetadataService [{level}] {message}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        handler = self._get_xmp_handler()
        return handler.get_timestamp()
    
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()
