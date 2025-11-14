"""
base.py
Description: Base class for all metadata handlers with common functionality
This module provides a base class for handling metadata operations, including reading and writing
metadata, logging, and error handling. It is designed to be extended by specific metadata handler classes.
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
# Metadata_system/src/eric_metadata/handlers/base.py
import os
import threading
import datetime
from typing import Dict, Any, Optional, List

class BaseHandler:
    """Base class for all metadata handlers with common functionality"""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the base handler
        
        Args:
            debug: Whether to enable debug logging
        """
        self.debug = debug
        self._lock = threading.Lock()
        self.error_history = []
        self.max_error_history = 100
        self._operation_status = {
            'in_progress': False,
            'operation': None,
            'retries': 0,
            'recovery_attempted': False
        }
        
    def log(self, message: str, level: str = "INFO", error: Exception = None) -> None:
        """
        Log a message with appropriate level
        
        Args:
            message: The message to log
            level: Log level (INFO, DEBUG, WARNING, ERROR)
            error: Optional exception to include in log
        """
        if level == "DEBUG" and not self.debug:
            return
            
        timestamp = self.get_timestamp()
        
        error_text = f" - {str(error)}" if error else ""
        log_message = f"[{timestamp}] {self.__class__.__name__} [{level}] {message}{error_text}"
        
        print(log_message)
        
        # Track errors for recovery
        if level in ["ERROR", "WARNING"]:
            self.error_history.append({
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'error': str(error) if error else None
            })
            
            # Maintain history size
            if len(self.error_history) > self.max_error_history:
                self.error_history.pop(0)
                
    def get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        return datetime.datetime.now().isoformat()
        
    def write_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Abstract method to write metadata to a file
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: Success status
        """
        raise NotImplementedError("Subclasses must implement write_metadata")
        
    def read_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Abstract method to read metadata from a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            dict: Metadata read from the file
        """
        raise NotImplementedError("Subclasses must implement read_metadata")
    
    def _safely_execute(self, operation_name: str, callback, *args, **kwargs) -> Any:
        """
        Execute operation with proper locking and error handling
        
        Args:
            operation_name: Name of the operation for logging
            callback: Function to execute
            *args, **kwargs: Arguments to pass to the callback
            
        Returns:
            Any: Result from the callback or None on error
        """
        with self._lock:
            try:
                # Track operation
                self._operation_status['in_progress'] = True
                self._operation_status['operation'] = operation_name
                self._operation_status['recovery_attempted'] = False
                
                self.log(f"Starting operation: {operation_name}", level="DEBUG")
                result = callback(*args, **kwargs)
                self.log(f"Completed operation: {operation_name}", level="DEBUG")
                
                # Reset operation status
                self._operation_status['in_progress'] = False
                self._operation_status['operation'] = None
                self._operation_status['retries'] = 0
                
                return result
                
            except Exception as e:
                self.log(f"Error in {operation_name}: {str(e)}", level="ERROR", error=e)
                
                # Track error for recovery
                self._operation_status['in_progress'] = False
                
                return None
                
    def _get_sidecar_path(self, filepath: str) -> str:
        """
        Get the path to the XMP sidecar file
        
        Args:
            filepath: Path to the original file
            
        Returns:
            str: Path to the XMP sidecar file
        """
        # Get base path without extension
        base_path, _ = os.path.splitext(filepath)
        
        # Return path with .xmp extension
        sidecar_path = f"{base_path}.xmp"
        
        # Debug log
        if self.debug:
            self.log(f"Input filepath: {filepath}", level="DEBUG")
            self.log(f"Generated sidecar path: {sidecar_path}", level="DEBUG")
            self.log(f"Path exists: {os.path.exists(os.path.dirname(sidecar_path))}", level="DEBUG")
        
        return sidecar_path
    
    def _get_text_file_path(self, filepath: str) -> str:
        """
        Get the path to the text metadata file
        
        Args:
            filepath: Path to the original file
            
        Returns:
            str: Path to the text metadata file
        """
        # Get base path without extension
        base_path, _ = os.path.splitext(filepath)
        
        # Return path with .txt extension
        return f"{base_path}.txt"
    
    def set_resource_identifier(self, about_uri: str) -> None:
        """
        Set the resource identifier for XMP metadata
        
        Args:
            about_uri: The resource URI to use
        """
        self.resource_about = about_uri
        
    def cleanup(self) -> None:
        """Clean up any resources used by the handler"""
        # Base implementation does nothing
        pass
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()