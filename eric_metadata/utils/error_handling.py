"""
error_handling.py
Description: Handles error recovery strategies for metadata operations.
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
# Metadata_system/src/eric_metadata/utils/error_handling.py
from typing import Dict, Any, Callable, Optional
import os
import json
import subprocess
import traceback

class ErrorRecovery:
    """Strategies for recovering from metadata operations errors"""
    
    @staticmethod
    def recover_write_error(handler, context: Dict[str, Any]) -> bool:
        """
        Recover from write errors
        
        Args:
            handler: The handler that encountered the error
            context: Error context including filepath, metadata, error_type
            
        Returns:
            bool: True if recovery succeeded
        """
        filepath = context.get('filepath')
        metadata = context.get('metadata')
        
        if not filepath or not metadata:
            return False
            
        # Try different approaches based on error type
        error_type = context.get('error_type')
        
        if error_type == 'PyExiv2Error':
            # Try ExifTool as fallback
            return ErrorRecovery._write_with_exiftool(filepath, metadata)
        
        elif error_type == 'XMLError':
            # Try simplified XML structure
            return ErrorRecovery._write_simplified_xml(filepath, metadata)
        
        elif error_type == 'IOError':
            # Try writing to alternate location
            return ErrorRecovery._write_to_backup(filepath, metadata)
            
        # Default strategy: Write to JSON backup
        return ErrorRecovery._write_to_json_backup(filepath, metadata)
    
    @staticmethod
    def recover_read_error(handler, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recover from read errors
        
        Args:
            handler: The handler that encountered the error
            context: Error context including filepath, error_type
            
        Returns:
            dict: Recovered metadata or empty dict
        """
        filepath = context.get('filepath')
        
        if not filepath:
            return {}
            
        # Try different approaches based on error type
        error_type = context.get('error_type')
        
        if error_type == 'PyExiv2Error':
            # Try ExifTool as fallback
            return ErrorRecovery._read_with_exiftool(filepath)
        
        elif error_type == 'XMLError':
            # Try parsing with more lenient XML parser
            return ErrorRecovery._read_with_lenient_parser(filepath)
            
        # Check for backup files
        backup_path = f"{os.path.splitext(filepath)[0]}.json"
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        return {}
    
    @staticmethod
    def _write_with_exiftool(filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata using ExifTool
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Create a temporary JSON file with the metadata
            temp_json = f"{filepath}.temp.json"
            with open(temp_json, 'w') as f:
                json.dump(metadata, f)
                
            # Use ExifTool to write the metadata
            cmd = [
                'exiftool',
                '-json',
                f"{temp_json}",
                '-overwrite_original',
                filepath
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            if os.path.exists(temp_json):
                os.remove(temp_json)
                
            return result.returncode == 0
            
        except Exception as e:
            print(f"ExifTool write failed: {e}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def _read_with_exiftool(filepath: str) -> Dict[str, Any]:
        """
        Read metadata using ExifTool
        
        Args:
            filepath: Path to the file
            
        Returns:
            dict: Metadata read from the file
        """
        try:
            # Use ExifTool to read the metadata
            cmd = [
                'exiftool',
                '-json',
                '-a', # Process duplicate tags
                '-G', # Show group names
                filepath
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {}
                
            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list) and len(data) > 0:
                    return ErrorRecovery._convert_exiftool_data(data[0])
                return {}
            except json.JSONDecodeError:
                return {}
                
        except Exception:
            return {}
    
    @staticmethod
    def _convert_exiftool_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ExifTool data format to our standard format
        
        Args:
            data: ExifTool data
            
        Returns:
            dict: Converted metadata
        """
        result = {
            'basic': {},
            'analysis': {},
            'ai_info': {}
        }
        
        # Process different tag groups
        for key, value in data.items():
            # XMP tags (most important for us)
            if key.startswith('XMP:'):
                tag_name = key[4:]
                
                if tag_name == 'Title':
                    result['basic']['title'] = value
                elif tag_name == 'Subject':
                    result['basic']['keywords'] = value if isinstance(value, list) else [value]
                elif tag_name == 'Description':
                    result['basic']['description'] = value
                elif tag_name == 'Rating':
                    result['basic']['rating'] = int(value)
                    
            # Look for custom namespaces
            elif key.startswith('XMP-eiqa:'):
                tag_name = key[9:]
                parts = tag_name.split(':')
                
                if len(parts) == 1:
                    # Top-level EIQA tag
                    if parts[0] not in result['analysis']:
                        result['analysis'][parts[0]] = {}
                    result['analysis'][parts[0]] = value
                elif len(parts) >= 2:
                    # Nested EIQA tag
                    if parts[0] not in result['analysis']:
                        result['analysis'][parts[0]] = {}
                    
                    current = result['analysis'][parts[0]]
                    for part in parts[1:-1]:
                        current = current.setdefault(part, {})
                    current[parts[-1]] = value
                    
            elif key.startswith('XMP-ai:'):
                tag_name = key[7:]
                parts = tag_name.split(':')
                
                if len(parts) == 1:
                    # Top-level AI tag
                    if parts[0] not in result['ai_info']:
                        result['ai_info'][parts[0]] = {}
                    result['ai_info'][parts[0]] = value
                elif len(parts) >= 2:
                    # Nested AI tag
                    if parts[0] not in result['ai_info']:
                        result['ai_info'][parts[0]] = {}
                    
                    current = result['ai_info'][parts[0]]
                    for part in parts[1:-1]:
                        current = current.setdefault(part, {})
                    current[parts[-1]] = value
                    
        return result
    
    @staticmethod
    def _write_simplified_xml(filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write simplified XML structure when complex structure fails
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            import xml.etree.ElementTree as ET
            from ..utils.namespace import NamespaceManager
            
            # Get the base path for XMP sidecar
            base_path, _ = os.path.splitext(filepath)
            xmp_path = f"{base_path}.xmp"
            
            # Create a simplified XMP structure
            root = ET.Element("{adobe:ns:meta/}xmpmeta")
            
            # Add namespaces
            for prefix, uri in NamespaceManager.NAMESPACES.items():
                root.set(f"xmlns:{prefix}", uri)
                
            # Create RDF element
            rdf = ET.SubElement(root, f"{{{NamespaceManager.NAMESPACES['rdf']}}}RDF")
            
            # Create Description element
            desc = ET.SubElement(rdf, f"{{{NamespaceManager.NAMESPACES['rdf']}}}Description")
            desc.set(f"{{{NamespaceManager.NAMESPACES['rdf']}}}about", "")
            
            # Add basic metadata as attributes
            if 'basic' in metadata:
                if 'title' in metadata['basic']:
                    desc.set(f"{{{NamespaceManager.NAMESPACES['dc']}}}title", str(metadata['basic']['title']))
                if 'description' in metadata['basic']:
                    desc.set(f"{{{NamespaceManager.NAMESPACES['dc']}}}description", str(metadata['basic']['description']))
                    
            # Add analysis data (flattened)
            if 'analysis' in metadata:
                for section, data in metadata['analysis'].items():
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (str, int, float, bool)):
                                desc.set(f"{{{NamespaceManager.NAMESPACES['eiqa']}}}{section}.{key}", str(value))
                                
            # Add AI data (flattened)
            if 'ai_info' in metadata:
                for section, data in metadata['ai_info'].items():
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, (str, int, float, bool)):
                                desc.set(f"{{{NamespaceManager.NAMESPACES['ai']}}}{section}.{key}", str(value))
                                
            # Write to file
            tree = ET.ElementTree(root)
            tree.write(xmp_path, encoding='utf-8', xml_declaration=True)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def _read_with_lenient_parser(filepath: str) -> Dict[str, Any]:
        """
        Read with a more lenient XML parser
        
        Args:
            filepath: Path to the file
            
        Returns:
            dict: Metadata read from the file
        """
        try:
            # Handle XMP sidecar file
            if filepath.endswith('.xmp'):
                xmp_path = filepath
            else:
                base_path, _ = os.path.splitext(filepath)
                xmp_path = f"{base_path}.xmp"
                
            if not os.path.exists(xmp_path):
                return {}
                
            # Read the file content
            with open(xmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Use a simple regex-based parser
            result = {
                'basic': {},
                'analysis': {},
                'ai_info': {}
            }
            
            # Extract basic metadata
            title_match = re.search(r'dc:title="([^"]*)"', content)
            if title_match:
                result['basic']['title'] = title_match.group(1)
                
            desc_match = re.search(r'dc:description="([^"]*)"', content)
            if desc_match:
                result['basic']['description'] = desc_match.group(1)
                
            # Extract EIQA data
            for match in re.finditer(r'eiqa:([a-zA-Z0-9_.]+)="([^"]*)"', content):
                path = match.group(1).split('.')
                value = match.group(2)
                
                if len(path) == 1:
                    result['analysis'][path[0]] = value
                elif len(path) >= 2:
                    if path[0] not in result['analysis']:
                        result['analysis'][path[0]] = {}
                        
                    current = result['analysis'][path[0]]
                    for part in path[1:-1]:
                        current = current.setdefault(part, {})
                    current[path[-1]] = value
                    
            # Extract AI data
            for match in re.finditer(r'ai:([a-zA-Z0-9_.]+)="([^"]*)"', content):
                path = match.group(1).split('.')
                value = match.group(2)
                
                if len(path) == 1:
                    result['ai_info'][path[0]] = value
                elif len(path) >= 2:
                    if path[0] not in result['ai_info']:
                        result['ai_info'][path[0]] = {}
                        
                    current = result['ai_info'][path[0]]
                    for part in path[1:-1]:
                        current = current.setdefault(part, {})
                    current[path[-1]] = value
                    
            return result
            
        except Exception:
            return {}
    
    @staticmethod
    def _write_to_backup(filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to a backup file
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(filepath), '.metadata_backup')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filepath
            filename = os.path.basename(filepath)
            backup_path = os.path.join(backup_dir, f"{filename}.xmp")
            
            # Write XMP sidecar to backup location
            return ErrorRecovery._write_simplified_xml(backup_path, metadata)
            
        except Exception:
            # Last resort: write to JSON backup
            return ErrorRecovery._write_to_json_backup(filepath, metadata)
    
    @staticmethod
    def _write_to_json_backup(filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to a JSON backup file
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Create backup filepath
            base_path, _ = os.path.splitext(filepath)
            backup_path = f"{base_path}.metadata.json"
            
            # Write JSON
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
            return True
            
        except Exception:
            return False