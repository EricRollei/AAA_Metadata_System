"""
format_detect.py
Description: Detects and handles different image formats for metadata processing.
    This module provides functionality to identify the format of image files and determine
    the appropriate handler for reading and writing metadata.
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
# Metadata_system/src/eric_metadata/utils/format_detect.py
import os
from typing import Optional, Callable, Dict, List, Set, Tuple

class FormatHandler:
    """Format detection and handling for different image types"""
    
    # Group formats by their handling requirements
    FORMAT_HANDLERS: Dict[str, List[str]] = {
        'standard': ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp'],
        'raw': ['.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2'],
        'layered': ['.psd', '.xcf'],
        'special': ['.heic', '.heif', '.avif']
    }
    
    # Formats PyExiv2 can handle
    PYEXIV2_COMPATIBLE: List[str] = ['.jpg', '.jpeg', '.tif', '.tiff', '.png']
    
    # Formats requiring ExifTool
    EXIFTOOL_REQUIRED: List[str] = [
        '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2',
        '.psd', '.heic', '.heif', '.avif'
    ]
    
    @classmethod
    def get_handler_for_file(cls, filepath: str) -> str:
        """
        Determine appropriate handler type for a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            str: Handler type ('standard', 'raw', 'layered', 'special', 'unknown')
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        for category, extensions in cls.FORMAT_HANDLERS.items():
            if ext in extensions:
                return category
                
        return 'unknown'
    
    @classmethod
    def can_use_pyexiv2(cls, filepath: str) -> bool:
        """
        Check if PyExiv2 can handle this file format
        
        Args:
            filepath: Path to the file
            
        Returns:
            bool: True if PyExiv2 can handle this format
        """
        ext = os.path.splitext(filepath)[1].lower()
        return ext in cls.PYEXIV2_COMPATIBLE
    
    @classmethod
    def requires_exiftool(cls, filepath: str) -> bool:
        """
        Check if ExifTool is required for this file format
        
        Args:
            filepath: Path to the file
            
        Returns:
            bool: True if ExifTool is required
        """
        ext = os.path.splitext(filepath)[1].lower()
        return ext in cls.EXIFTOOL_REQUIRED
    
    @classmethod
    def get_file_info(cls, filepath: str) -> Dict[str, any]:
        """
        Get information about a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            dict: File information including format, handler type, etc.
        """
        ext = os.path.splitext(filepath)[1].lower()
        handler_type = cls.get_handler_for_file(filepath)
        
        return {
            'path': filepath,
            'extension': ext,
            'handler_type': handler_type,
            'can_use_pyexiv2': cls.can_use_pyexiv2(filepath),
            'requires_exiftool': cls.requires_exiftool(filepath),
            'is_raw': handler_type == 'raw',
            'is_layered': handler_type == 'layered',
            'is_special': handler_type == 'special',
            'is_standard': handler_type == 'standard',
            'base_path': os.path.splitext(filepath)[0]
        }