"""
embedded.py - Embedded Metadata Handler
Description: This module provides functions for reading and writing embedded metadata in image files using PyExiv2 and ExifTool.    
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

# Metadata_system/src/eric_metadata/handlers/embedded.py
import os
import json
from typing import Dict, Any, Optional, List, Tuple, Union
import re
import datetime
import uuid
import subprocess
import numpy as np
import xml.etree.ElementTree as ET 

from ..handlers.base import BaseHandler
from ..utils.format_detect import FormatHandler
from ..utils.namespace import NamespaceManager
from ..utils.error_handling import ErrorRecovery

class EmbeddedMetadataHandler(BaseHandler):
    """Handler for embedded metadata in image files"""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the embedded metadata handler
        
        Args:
            debug: Whether to enable debug logging
        """
        super().__init__(debug)
        
        # Initialize PyExiv2
        self._initialize_pyexiv2()
        
        # Register namespaces
        self._register_namespaces()
        
        # Create ExifTool config
        self._exiftool_config = self._create_exiftool_config()
        
        # Track current metadata object for cleanup
        self._current_metadata = None
        
        # Resource identifier for XMP
        self.resource_about = ""
    
    def write_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to image file
        
        Args:
            filepath: Path to the image file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get format information
            format_info = FormatHandler.get_file_info(filepath)
            
            # Choose appropriate write method based on format
            if format_info['can_use_pyexiv2']:
                return self._write_with_pyexiv2(filepath, metadata)
            elif format_info['requires_exiftool']:
                return self._write_with_exiftool(filepath, metadata)
            elif format_info['is_standard']:
                # Some formats like PNG need special handling
                return self._write_standard_format(filepath, metadata, format_info)
            else:
                self.log(f"Unsupported format for embedded metadata: {format_info['extension']}", level="WARNING")
                return False
                
        except Exception as e:
            self.log(f"Error writing embedded metadata: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'metadata': metadata,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_write_error(self, context)
    
    def read_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata from image file
        
        Args:
            filepath: Path to the image file
            
        Returns:
            dict: Metadata from image file
        """
        try:
            # Get format information
            format_info = FormatHandler.get_file_info(filepath)
            
            # Choose appropriate read method based on format
            if format_info['can_use_pyexiv2']:
                return self._read_with_pyexiv2(filepath)
            elif format_info['requires_exiftool']:
                return self._read_with_exiftool(filepath)
            elif format_info['is_standard']:
                # Some formats like PNG need special handling
                return self._read_standard_format(filepath, format_info)
            else:
                self.log(f"Unsupported format for embedded metadata: {format_info['extension']}", level="WARNING")
                return {}
                
        except Exception as e:
            self.log(f"Error reading embedded metadata: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_read_error(self, context)
    
    def _initialize_pyexiv2(self):
        """Initialize PyExiv2 module"""
        try:
            import pyexiv2
            if hasattr(pyexiv2, 'exiv2api') and hasattr(pyexiv2.exiv2api, 'init'):
                pyexiv2.exiv2api.init()
                self.log("PyExiv2 initialized successfully")
        except ImportError:
            self.log("PyExiv2 not available", level="WARNING")
        except Exception as e:
            self.log(f"Failed to initialize PyExiv2: {str(e)}", level="WARNING")
    
# In embedded.py, modify the _register_namespaces method
    def _register_namespaces(self):
        """Register namespaces with PyExiv2"""
        success = NamespaceManager.register_with_pyexiv2(self.debug)
        self.log(f"Namespace registration {'succeeded' if success else 'failed'}", level="DEBUG")
        
        # Verify specific namespaces (add this for debugging)
        if self.debug:
            try:
                import pyexiv2
                if hasattr(pyexiv2, 'exiv2api') and hasattr(pyexiv2.exiv2api, 'registeredXmpNamespaces'):
                    namespaces = pyexiv2.exiv2api.registeredXmpNamespaces()
                    self.log(f"Registered XMP namespaces: {namespaces}", level="DEBUG")
            except Exception as e:
                self.log(f"Could not verify namespaces: {e}", level="DEBUG")

    def _create_exiftool_config(self) -> str:
        """Create ExifTool configuration file"""
        return NamespaceManager.create_exiftool_config()
    
    def _write_with_pyexiv2(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata using PyExiv2
        
        Args:
            filepath: Path to the image file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            import pyexiv2
            
            # Open image
            img = pyexiv2.Image(filepath)
            self._current_metadata = img
            
            # Read existing metadata for merging
            existing_xmp = img.read_xmp() or {}
            existing_iptc = img.read_iptc() or {}
            existing_exif = img.read_exif() or {}
            
            # Prepare metadata for writing
            xmp_data = {}
            iptc_data = {}
            exif_data = {}
            
            # Process basic metadata
            if 'basic' in metadata:
                basic_metadata = self._prepare_basic_metadata(metadata['basic'], existing_iptc)
                xmp_data.update(basic_metadata['xmp'])
                iptc_data.update(basic_metadata['iptc'])
                exif_data.update(basic_metadata['exif'])
            
            # Process analysis data
            if 'analysis' in metadata:
                analysis_xmp = self._prepare_analysis_metadata(metadata['analysis'], existing_xmp)
                xmp_data.update(analysis_xmp)
            
            # Process AI info - most important for generation data
            if 'ai_info' in metadata:
                ai_xmp = self._prepare_ai_metadata(metadata['ai_info'], existing_xmp)
                xmp_data.update(ai_xmp)
            
            # Process regions data
            if 'regions' in metadata:
                region_xmp = self._prepare_region_metadata(metadata['regions'], existing_xmp)
                xmp_data.update(region_xmp)
            
            # Write metadata
            self.log(f"Writing {len(xmp_data)} XMP fields to {filepath}", level="DEBUG")
            if xmp_data:
                img.modify_xmp(xmp_data)
                
            if iptc_data:
                img.modify_iptc(iptc_data)
                
            if exif_data:
                img.modify_exif(exif_data)
                
            # Close and save
            img.close()
            self._current_metadata = None
            
            return True
            
        except Exception as e:
            self.log(f"PyExiv2 write failed: {str(e)}", level="ERROR", error=e)
            self._cleanup_current_metadata()
            return False
    
    def _read_with_pyexiv2(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata using PyExiv2
        
        Args:
            filepath: Path to the image file
            
        Returns:
            dict: Metadata from image file
        """
        try:
            import pyexiv2
            
            # Open image
            img = pyexiv2.Image(filepath)
            self._current_metadata = img
            
            result = {
                'basic': {},
                'analysis': {},
                'ai_info': {}
            }
            
            # Read XMP metadata
            xmp_data = img.read_xmp() or {}
            
            # Read IPTC metadata
            iptc_data = img.read_iptc() or {}
            
            # Read EXIF metadata
            exif_data = img.read_exif() or {}
            
            # Extract basic metadata
            self._extract_basic_metadata(result, xmp_data, iptc_data, exif_data)
            
            # Extract analysis metadata
            self._extract_analysis_metadata(result, xmp_data)
            
            # Extract AI metadata
            self._extract_ai_metadata(result, xmp_data)
            
            # Extract region data
            self._extract_region_metadata(result, xmp_data)
            
            # Close image
            img.close()
            self._current_metadata = None
            
            return result
            
        except Exception as e:
            self.log(f"PyExiv2 read failed: {str(e)}", level="ERROR", error=e)
            self._cleanup_current_metadata()
            return {}
    
    def _write_with_exiftool(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata using ExifTool
        
        Args:
            filepath: Path to the image file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Create a temporary JSON file with the metadata
            temp_json = f"{filepath}.temp.json"
            
            # Convert metadata to ExifTool format
            exiftool_meta = self._convert_to_exiftool_format(metadata)
            
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(exiftool_meta, f, indent=2)
                
            # Build ExifTool command
            cmd = [
                'exiftool',
                '-config', self._exiftool_config,
                '-json', temp_json,
                '-overwrite_original',
                filepath
            ]
            
            # Run ExifTool
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp file
            if os.path.exists(temp_json):
                os.remove(temp_json)
                
            if result.returncode != 0:
                self.log(f"ExifTool error: {result.stderr}", level="ERROR")
                return False
                
            return True
            
        except Exception as e:
            self.log(f"ExifTool write failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def _read_with_exiftool(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata using ExifTool
        
        Args:
            filepath: Path to the image file
            
        Returns:
            dict: Metadata from image file
        """
        try:
            # Build ExifTool command
            cmd = [
                'exiftool',
                '-config', self._exiftool_config,
                '-json',
                '-a',  # All tags
                '-G',  # Group names
                filepath
            ]
            
            # Run ExifTool
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.log(f"ExifTool error: {result.stderr}", level="ERROR")
                return {}
                
            # Parse JSON output
            try:
                exiftool_data = json.loads(result.stdout)
                if not exiftool_data:
                    return {}
                    
                # Convert to our format
                return self._convert_from_exiftool_format(exiftool_data[0])
                
            except json.JSONDecodeError as e:
                self.log(f"Failed to parse ExifTool output: {str(e)}", level="ERROR")
                return {}
                
        except Exception as e:
            self.log(f"ExifTool read failed: {str(e)}", level="ERROR", error=e)
            return {}
    
# Metadata_system/src/eric_metadata/handlers/embedded.py (continued)

    def _write_standard_format(self, filepath: str, metadata: Dict[str, Any], 
                            format_info: Dict[str, Any]) -> bool:
        """
        Write metadata to standard formats with special handling
        
        Args:
            filepath: Path to the image file
            metadata: Metadata to write
            format_info: Format information
            
        Returns:
            bool: True if successful
        """
        # Handle PNG format
        if format_info['extension'] in ['.png']:
            return self._write_png_metadata(filepath, metadata)
            
        # Handle WebP format
        elif format_info['extension'] in ['.webp']:
            return self._write_webp_metadata(filepath, metadata)
            
        # Other formats - try ExifTool as fallback
        return self._write_with_exiftool(filepath, metadata)
    
    def _read_standard_format(self, filepath: str, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read metadata from standard formats with special handling
        
        Args:
            filepath: Path to the image file
            format_info: Format information
            
        Returns:
            dict: Metadata from image file
        """
        # Handle PNG format
        if format_info['extension'] in ['.png']:
            return self._read_png_metadata(filepath)
            
        # Handle WebP format
        elif format_info['extension'] in ['.webp']:
            return self._read_webp_metadata(filepath)
            
        # Other formats - try ExifTool as fallback
        return self._read_with_exiftool(filepath)
    
    def _write_png_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to PNG file while preserving workflow data
        
        Args:
            filepath: Path to the PNG file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            from PIL import Image
            from PIL.PngImagePlugin import PngInfo
            
            # First extract existing metadata including workflow
            existing_info = {}
            workflow_data = None
            
            with Image.open(filepath) as img:
                # Store all existing metadata
                for key, value in img.info.items():
                    existing_info[key] = value
                    
                    # Check for workflow data
                    if key == 'parameters':
                        workflow_data = value
                        self.log(f"Found workflow data in PNG", level="DEBUG")
            
            # Create new metadata structure
            info = PngInfo()
            
            # Add all existing metadata back except 'parameters' (workflow) which we'll handle separately
            for key, value in existing_info.items():
                if key != 'parameters' and key != 'XML:com.adobe.xmp':
                    info.add_text(key, str(value))
            
            # Prepare XMP metadata as a string
            xmp_data = self._prepare_xmp_packet(metadata)
            if xmp_data:
                info.add_text('XML:com.adobe.xmp', xmp_data)
            
            # Add back workflow data if it existed
            if workflow_data is not None:
                info.add_text('parameters', workflow_data)
                
            # Open and modify the image
            with Image.open(filepath) as img:
                # Create a temporary file
                temp_filepath = f"{filepath}.temp.png"
                
                # Save with updated metadata
                img.save(temp_filepath, "PNG", pnginfo=info)
                
            # Replace original with temp file
            import os
            os.replace(temp_filepath, filepath)
            
            return True
            
        except Exception as e:
            self.log(f"PNG metadata write failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def _read_png_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata from PNG file including workflow data
        
        Args:
            filepath: Path to the PNG file
            
        Returns:
            dict: Metadata from PNG file
        """
        try:
            from PIL import Image
            
            result = {
                'basic': {},
                'analysis': {},
                'ai_info': {}
            }
            
            with Image.open(filepath) as img:
                # Get XMP metadata
                if 'XML:com.adobe.xmp' in img.info:
                    xmp_data = img.info['XML:com.adobe.xmp']
                    # Parse XMP data
                    xmp_metadata = self._parse_xmp_packet(xmp_data)
                    if xmp_metadata:
                        self._merge_xmp_metadata(result, xmp_metadata)
                        
                # Get workflow data
                if 'parameters' in img.info:
                    workflow_data = img.info['parameters']
                    workflow = self._parse_workflow_data(workflow_data)
                    if workflow:
                        # Store in ai_info section
                        if 'ai_info' not in result:
                            result['ai_info'] = {}
                        result['ai_info']['workflow'] = workflow
            
            return result
            
        except Exception as e:
            self.log(f"PNG metadata read failed: {str(e)}", level="ERROR", error=e)
            return {}
    
    def _write_webp_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to WebP file
        
        Args:
            filepath: Path to the WebP file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        # WebP has limited metadata support, so we use ExifTool
        return self._write_with_exiftool(filepath, metadata)
    
    def _read_webp_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata from WebP file
        
        Args:
            filepath: Path to the WebP file
            
        Returns:
            dict: Metadata from WebP file
        """
        # WebP has limited metadata support, so we use ExifTool
        return self._read_with_exiftool(filepath)
    
    def _parse_workflow_data(self, workflow_data: str) -> Dict[str, Any]:
        """
        Parse ComfyUI workflow data
        
        Args:
            workflow_data: Workflow data as string
            
        Returns:
            dict: Parsed workflow data
        """
        try:
            # Try to parse as JSON
            import json
            
            # Handle string or dict input
            if isinstance(workflow_data, str):
                workflow = json.loads(workflow_data)
            else:
                workflow = workflow_data
            
            # Check for the different sections
            result = {}
            
            # Handle "prompt" section (older format)
            if 'prompt' in workflow and isinstance(workflow['prompt'], dict):
                result['prompt'] = workflow['prompt']
                
            # Handle "workflow" section (newer format)
            if 'workflow' in workflow and isinstance(workflow['workflow'], dict):
                result['workflow'] = workflow['workflow']
            
            # Extract generation parameters from nodes if present
            if 'prompt' in workflow and 'nodes' in workflow['prompt']:
                result['parameters'] = self._extract_parameters_from_nodes(workflow['prompt']['nodes'])
            
            return result
            
        except Exception as e:
            self.log(f"Workflow parsing failed: {str(e)}", level="WARNING")
            # Return the raw data if parsing fails
            return {'raw': str(workflow_data)}
    
    def _extract_parameters_from_nodes(self, nodes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract generation parameters from workflow nodes
        
        Args:
            nodes: Workflow nodes
            
        Returns:
            dict: Extracted parameters
        """
        parameters = {}
        
        # Map of node types to parameter names
        node_parameter_map = {
            'KSampler': {
                'seed': ('inputs', 'seed'),
                'steps': ('inputs', 'steps'),
                'cfg': ('inputs', 'cfg'),
                'sampler_name': ('inputs', 'sampler_name'),
                'scheduler': ('inputs', 'scheduler'),
                'denoise': ('inputs', 'denoise')
            },
            'CLIPTextEncode': {
                'prompt': ('inputs', 'text'),
                'clip': ('inputs', 'clip'),
                'is_negative': ('is_negative',)
            },
            'CheckpointLoaderSimple': {
                'model': ('inputs', 'ckpt_name')
            },
            'VAELoader': {
                'vae': ('inputs', 'vae_name')
            },
            'LoraLoader': {
                'lora_name': ('inputs', 'lora_name'),
                'strength_model': ('inputs', 'strength_model'),
                'strength_clip': ('inputs', 'strength_clip')
            }
        }
        
        # Extract parameters from nodes
        for node_id, node in nodes.items():
            class_type = node.get('class_type')
            if class_type in node_parameter_map:
                param_map = node_parameter_map[class_type]
                for param_name, path in param_map.items():
                    # Navigate path to extract parameter
                    value = node
                    for part in path:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            value = None
                            break
                    
                    if value is not None:
                        parameters[param_name] = value
                        
                # Special handling for negative prompts
                if class_type == 'CLIPTextEncode' and node.get('is_negative'):
                    if 'prompt' in parameters:
                        parameters['negative_prompt'] = parameters.pop('prompt')
        
        return parameters
    
    def _prepare_xmp_packet(self, metadata: Dict[str, Any]) -> str:
        """
        Prepare XMP packet from metadata
        
        Args:
            metadata: Metadata to convert to XMP
            
        Returns:
            str: XMP packet
        """
        try:
            import xml.etree.ElementTree as ET
            
            # Create base XMP structure
            xmpmeta = ET.Element("{adobe:ns:meta/}xmpmeta")
            
            # Add namespaces
            for prefix, uri in NamespaceManager.NAMESPACES.items():
                ET.register_namespace(prefix, uri)
                xmpmeta.set(f"xmlns:{prefix}", uri)
                
            # Create RDF element
            rdf = ET.SubElement(xmpmeta, f"{{{NamespaceManager.NAMESPACES['rdf']}}}RDF")
            
            # Create Description element
            description = ET.SubElement(rdf, f"{{{NamespaceManager.NAMESPACES['rdf']}}}Description")
            description.set(f"{{{NamespaceManager.NAMESPACES['rdf']}}}about", self.resource_about or "")
            
            # Add basic metadata
            if 'basic' in metadata:
                self._add_basic_metadata_to_xmp(description, metadata['basic'])
                
            # Add analysis data
            if 'analysis' in metadata:
                self._add_analysis_metadata_to_xmp(description, metadata['analysis'])
                
            # Add AI info
            if 'ai_info' in metadata:
                self._add_ai_metadata_to_xmp(description, metadata['ai_info'])
                
            # Add regions
            if 'regions' in metadata:
                self._add_region_metadata_to_xmp(description, metadata['regions'])
            
            # Format with indentation
            self._indent_xml(xmpmeta)
            
            # Convert to string
            xmp_str = ET.tostring(xmpmeta, encoding='unicode')
            
            # Add XMP packet wrapper
            return f'<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n{xmp_str}\n<?xpacket end="w"?>'
            
        except Exception as e:
            self.log(f"XMP packet preparation failed: {str(e)}", level="ERROR", error=e)
            return ""
    
    def _parse_xmp_packet(self, xmp_data: str) -> Dict[str, Any]:
        """
        Parse XMP packet to metadata
        
        Args:
            xmp_data: XMP packet as string
            
        Returns:
            dict: Parsed metadata
        """
        try:
            from ..utils.xml_tools import XMLTools
            return XMLTools.xmp_to_dict(xmp_data)
        except Exception as e:
            self.log(f"XMP packet parsing failed: {str(e)}", level="ERROR", error=e)
            return {}
    
    def _merge_xmp_metadata(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Merge XMP metadata into target
        
        Args:
            target: Target metadata to update
            source: Source metadata to merge
        """
        # Basic merge, can be enhanced with more specific merging rules
        for section, data in source.items():
            if section not in target:
                target[section] = data
            elif isinstance(data, dict) and isinstance(target[section], dict):
                # Recursive merge for nested dictionaries
                for key, value in data.items():
                    if key not in target[section]:
                        target[section][key] = value
                    elif isinstance(value, dict) and isinstance(target[section][key], dict):
                        # Deep merge for nested dictionaries
                        self._merge_xmp_metadata(target[section][key], value)
                    else:
                        # Replace with newer value
                        target[section][key] = value
            else:
                # Replace with newer value
                target[section] = data
    
    def _indent_xml(self, elem, level=0):
        """
        Add proper indentation to XML for readability
        
        Args:
            elem: XML element
            level: Indentation level
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def _convert_to_exiftool_format(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert our metadata format to ExifTool format
        
        Args:
            metadata: Our metadata format
            
        Returns:
            dict: ExifTool format
        """
        exiftool_meta = {}
        
        # Basic metadata
        if 'basic' in metadata:
            basic = metadata['basic']
            if 'title' in basic:
                exiftool_meta['XMP:Title'] = basic['title']
                exiftool_meta['IPTC:ObjectName'] = basic['title']
                
            if 'description' in basic:
                exiftool_meta['XMP:Description'] = basic['description']
                exiftool_meta['IPTC:Caption-Abstract'] = basic['description']
                
            if 'keywords' in basic:
                keywords = basic['keywords']
                if isinstance(keywords, (list, set, tuple)):
                    keywords = list(keywords)
                elif isinstance(keywords, str):
                    keywords = [k.strip() for k in keywords.split(',')]
                else:
                    keywords = [str(keywords)]
                    
                exiftool_meta['XMP:Subject'] = keywords
                exiftool_meta['IPTC:Keywords'] = keywords
                
            if 'rating' in basic:
                exiftool_meta['XMP:Rating'] = basic['rating']
                
        # Analysis data
        if 'analysis' in metadata:
            for analysis_type, data in metadata['analysis'].items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        # Handle nested dictionaries
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                exiftool_meta[f'XMP-eiqa:{analysis_type}.{key}.{subkey}'] = subvalue
                        else:
                            exiftool_meta[f'XMP-eiqa:{analysis_type}.{key}'] = value
                else:
                    exiftool_meta[f'XMP-eiqa:{analysis_type}'] = data
                    
        # AI info
        if 'ai_info' in metadata:
            for key, value in metadata['ai_info'].items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        # Handle nested dictionaries
                        if isinstance(subvalue, dict):
                            for subsubkey, subsubvalue in subvalue.items():
                                exiftool_meta[f'XMP-ai:{key}.{subkey}.{subsubkey}'] = subsubvalue
                        else:
                            exiftool_meta[f'XMP-ai:{key}.{subkey}'] = subvalue
                else:
                    exiftool_meta[f'XMP-ai:{key}'] = value
                    
        # Regions - ExifTool supports MWG regions
        if 'regions' in metadata and 'faces' in metadata['regions']:
            # We'll rely on our XMP handling for regions
            # This would need more complex mapping for ExifTool
            pass
            
        return exiftool_meta
    
    def _convert_from_exiftool_format(self, exiftool_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ExifTool format to our metadata format
        
        Args:
            exiftool_data: ExifTool data
            
        Returns:
            dict: Our metadata format
        """
        result = {
            'basic': {},
            'analysis': {},
            'ai_info': {}
        }
        
        # Process ExifTool data
        for key, value in exiftool_data.items():
            # Extract namespace prefix and field name
            parts = key.split(':', 1)
            if len(parts) != 2:
                continue
                
            prefix, field = parts
            
            # Basic metadata
            if prefix in ['XMP', 'IPTC', 'EXIF']:
                if field == 'Title' or field == 'ObjectName':
                    result['basic']['title'] = value
                elif field == 'Description' or field == 'Caption-Abstract':
                    result['basic']['description'] = value
                elif field == 'Subject' or field == 'Keywords':
                    if isinstance(value, str):
                        result['basic']['keywords'] = [value]
                    else:
                        result['basic']['keywords'] = value
                elif field == 'Rating':
                    result['basic']['rating'] = value
                    
            # Analysis data (eiqa namespace)
            elif prefix == 'XMP-eiqa':
                # Handle analysis data with nested structure
                field_parts = field.split('.')
                analysis_type = field_parts[0]
                
                if analysis_type not in result['analysis']:
                    result['analysis'][analysis_type] = {}
                    
                if len(field_parts) == 1:
                    # Direct field
                    result['analysis'][analysis_type] = value
                elif len(field_parts) == 2:
                    # One level of nesting
                    result['analysis'][analysis_type][field_parts[1]] = value
                elif len(field_parts) >= 3:
                    # Multiple levels of nesting
                    current = result['analysis'][analysis_type]
                    for part in field_parts[1:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[field_parts[-1]] = value
                    
            # AI info (ai namespace)
            elif prefix == 'XMP-ai':
                # Handle AI info with nested structure
                field_parts = field.split('.')
                ai_type = field_parts[0]
                
                if ai_type not in result['ai_info']:
                    result['ai_info'][ai_type] = {}
                    
                if len(field_parts) == 1:
                    # Direct field
                    result['ai_info'][ai_type] = value
                elif len(field_parts) == 2:
                    # One level of nesting
                    result['ai_info'][ai_type][field_parts[1]] = value
                elif len(field_parts) >= 3:
                    # Multiple levels of nesting
                    current = result['ai_info'][ai_type]
                    for part in field_parts[1:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[field_parts[-1]] = value
        
        return result
    
    def _prepare_basic_metadata(self, basic_data: Dict[str, Any], existing_iptc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Prepare basic metadata for various formats
        
        Args:
            basic_data: Basic metadata
            existing_iptc: Existing IPTC metadata
            
        Returns:
            dict: Metadata for XMP, IPTC, and EXIF
        """
        result = {
            'xmp': {},
            'iptc': {},
            'exif': {}
        }
        
        # Title
        if 'title' in basic_data:
            title = basic_data['title']
            
            # XMP with language alternative
            result['xmp']['Xmp.dc.title'] = {'x-default': title}
            
            # IPTC
            result['iptc']['Iptc.Application2.ObjectName'] = title
            
            # EXIF
            result['exif']['Exif.Image.ImageDescription'] = title
            
        # Description - handle potential truncation issues
        if 'description' in basic_data:
            desc = basic_data['description']
            
            # Check for long descriptions - increase limit from 2000 to 4000
            if len(desc) > 4000:
                # For XMP with language alternative - truncate with indicator
                truncated_desc = desc[:3997] + "..."
                result['xmp']['Xmp.dc.description'] = {'x-default': truncated_desc}
                
                # For IPTC - has stricter limits, truncate more aggressively
                iptc_desc = desc[:512] + "..." if len(desc) > 512 else desc
                result['iptc']['Iptc.Application2.Caption'] = iptc_desc
                
                # Store full description in a sidecar if needed
                self.log(f"Description truncated for XMP embedding. Original length: {len(desc)}", level="DEBUG")
            else:
                # XMP with language alternative
                result['xmp']['Xmp.dc.description'] = {'x-default': desc}
                
                # IPTC
                result['iptc']['Iptc.Application2.Caption'] = desc
        
        # Keywords
        if 'keywords' in basic_data:
            keywords = basic_data['keywords']
            
            # Ensure keywords is a list
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',')]
            elif not isinstance(keywords, (list, set, tuple)):
                keywords = [str(keywords)]
                
            # Ensure keywords is a list (not set)
            keywords = list(keywords)
            
            # XMP
            result['xmp']['Xmp.dc.subject'] = keywords
            
            # IPTC
            result['iptc']['Iptc.Application2.Keywords'] = keywords
            
        # Rating
        if 'rating' in basic_data:
            rating = basic_data['rating']
            
            # XMP
            result['xmp']['Xmp.xmp.Rating'] = rating
            
        return result
    
    def _prepare_analysis_metadata(self, analysis_data: Dict[str, Any], existing_xmp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare analysis metadata for XMP
        
        Args:
            analysis_data: Analysis metadata
            existing_xmp: Existing XMP metadata
            
        Returns:
            dict: XMP metadata
        """
        result = {}
        
        # Process each analysis type
        for analysis_type, data in analysis_data.items():
            # Skip empty data
            if not data:
                continue
                
            # Handle different analysis types
            if isinstance(data, dict):
                for key, value in data.items():
                    # Handle nested dictionaries
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            result[f'Xmp.eiqa.{analysis_type}.{key}.{subkey}'] = subvalue
                    else:
                        result[f'Xmp.eiqa.{analysis_type}.{key}'] = value
            else:
                result[f'Xmp.eiqa.{analysis_type}'] = data
                
        return result
    
    def _prepare_ai_metadata(self, ai_data: Dict[str, Any], existing_xmp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare AI metadata for XMP with proper RDF structure for complex objects
        
        Args:
            ai_data: AI metadata
            existing_xmp: Existing XMP metadata
            
        Returns:
            dict: XMP metadata
        """
        result = {}
        
        # IMPORTANT: Completely skip workflow data by default - it's too large for XMP
        # Remove both workflow.data and generation.prompt which contain the full workflow
        workflow_keys_to_remove = ['prompt', 'workflow', 'workflow_data']
        
        # First, make a clean copy of the generation data without workflow
        generation_data = {}
        if 'generation' in ai_data:
            generation = ai_data['generation']
            
            # Copy only essential generation parameters, explicitly filtering out workflow data
            for key, value in generation.items():
                # Skip workflow-related fields and raw prompts which are too large
                if key not in workflow_keys_to_remove and not key.endswith('_prompt_raw'):
                    generation_data[key] = value
        
        # Process generation data with proper RDF structure
        if generation_data:
            # Create the base structure for ai namespace
            prefix = 'Xmp.ai.'
            
            # Process different sections with proper grouping
            
            # Base model info
            if 'base_model' in generation_data:
                result.update(self._prepare_dict_for_xmp(f"{prefix}BaseModel", generation_data['base_model']))
            
            # Sampling parameters
            if 'sampling' in generation_data:
                result.update(self._prepare_dict_for_xmp(f"{prefix}Sampling", generation_data['sampling']))
            elif any(key in generation_data for key in ['sampler', 'steps', 'cfg_scale', 'seed']):
                # If sampling section doesn't exist but individual parameters do, create it
                sampling = {}
                for key in ['sampler', 'scheduler', 'steps', 'cfg_scale', 'seed', 'denoise']:
                    if key in generation_data:
                        sampling[key] = generation_data[key]
                if sampling:
                    result.update(self._prepare_dict_for_xmp(f"{prefix}Sampling", sampling))
            
            # Flux parameters
            if 'flux' in generation_data:
                result.update(self._prepare_dict_for_xmp(f"{prefix}Flux", generation_data['flux']))
            
            # Dimensions
            if 'dimensions' in generation_data:
                result.update(self._prepare_dict_for_xmp(f"{prefix}Dimensions", generation_data['dimensions']))
            elif any(key in generation_data for key in ['width', 'height']):
                # If dimensions section doesn't exist but individual parameters do, create it
                dimensions = {}
                for key in ['width', 'height', 'batch_size']:
                    if key in generation_data:
                        dimensions[key] = generation_data[key]
                if dimensions:
                    result.update(self._prepare_dict_for_xmp(f"{prefix}Dimensions", dimensions))
            
            # Modules
            if 'modules' in generation_data:
                modules = generation_data['modules']
                
                # VAE
                if 'vae' in modules:
                    result.update(self._prepare_dict_for_xmp(f"{prefix}VAE", modules['vae']))
                
                # CLIP
                if 'clip' in modules:
                    result.update(self._prepare_dict_for_xmp(f"{prefix}CLIP", modules['clip']))
                
                # CLIP Vision
                if 'clip_vision' in modules:
                    result.update(self._prepare_dict_for_xmp(f"{prefix}CLIPVision", modules['clip_vision']))
                
                # LoRAs
                if 'loras' in modules and modules['loras']:
                    # For LoRAs, use a Bag structure
                    if isinstance(modules['loras'], list):
                        result.update(self._prepare_list_for_xmp(f"{prefix}LoRAs", modules['loras']))
                    else:
                        # Single LoRA or dict
                        result.update(self._prepare_dict_for_xmp(f"{prefix}LoRAs", modules['loras']))
                
                # ControlNets
                if 'controlnets' in modules and modules['controlnets']:
                    result.update(self._prepare_list_for_xmp(f"{prefix}ControlNets", modules['controlnets']))
                
                # Style Models
                if 'style_models' in modules and modules['style_models']:
                    result.update(self._prepare_list_for_xmp(f"{prefix}StyleModels", modules['style_models']))
                
                # IP Adapters
                if 'ip_adapters' in modules and modules['ip_adapters']:
                    result.update(self._prepare_list_for_xmp(f"{prefix}IPAdapters", modules['ip_adapters']))
            
            # Process any top-level parameters not already handled
            for key, value in generation_data.items():
                if key not in ['base_model', 'sampling', 'flux', 'dimensions', 'modules'] and not isinstance(value, (dict, list)):
                    result[f"{prefix}{key}"] = value
            
            # Add timestamp if missing
            if 'timestamp' not in generation_data:
                import datetime
                result[f"{prefix}timestamp"] = datetime.datetime.now().isoformat()

            # Copy key values to the dc:subject (keywords) for searchability
            important_values = []
            
            # Extract model name
            if 'base_model' in generation_data and isinstance(generation_data['base_model'], dict) and 'unet' in generation_data['base_model']:
                important_values.append(generation_data['base_model']['unet'])
            elif 'model' in generation_data:
                important_values.append(generation_data['model'])
            
            # Extract sampler info
            if 'sampling' in generation_data and isinstance(generation_data['sampling'], dict) and 'sampler' in generation_data['sampling']:
                important_values.append(f"sampler_{generation_data['sampling']['sampler']}")
            elif 'sampler' in generation_data:
                important_values.append(f"sampler_{generation_data['sampler']}")
            
            # Extract LoRA names
            if 'modules' in generation_data and 'loras' in generation_data['modules']:
                loras = generation_data['modules']['loras']
                if isinstance(loras, list):
                    for lora in loras:
                        if isinstance(lora, dict) and 'name' in lora:
                            important_values.append(f"lora_{lora['name']}")
                elif isinstance(loras, dict) and 'name' in loras:
                    important_values.append(f"lora_{loras['name']}")
            elif 'loras' in generation_data:
                loras = generation_data['loras']
                if isinstance(loras, list):
                    for lora in loras:
                        if isinstance(lora, dict) and 'name' in lora:
                            important_values.append(f"lora_{lora['name']}")
            
            # Add important values to dc:instructions instead of dc:subject
            prefix_dc = 'Xmp.dc.'
            # First, preserve any existing subject/keywords exactly as they are
            if 'subject' in existing_xmp:
                result[f"{prefix_dc}subject"] = existing_xmp['subject']

            # Now add the AI values to instructions
            if 'instructions' in existing_xmp:
                # Get existing instructions
                existing_instructions = []
                if isinstance(existing_xmp['instructions'], list):
                    existing_instructions = existing_xmp['instructions']
                else:
                    existing_instructions = [existing_xmp['instructions']]
                    
                # Add new items without duplicating
                merged_instructions = existing_instructions.copy()
                for value in important_values:
                    # Clean up file paths for better searchability
                    if '\\' in value:
                        value = value.replace('\\', '_')
                    if value not in merged_instructions:
                        merged_instructions.append(value)
                        
                # Update instructions
                result[f"{prefix_dc}instructions"] = merged_instructions
            else:
                # Create new instructions
                # Clean up file paths
                cleaned_values = []
                for value in important_values:
                    if '\\' in value:
                        cleaned_values.append(value.replace('\\', '_'))
                    else:
                        cleaned_values.append(value)
                result[f"{prefix_dc}instructions"] = cleaned_values
        
        # Handle workflow_info with proper structure (not the workflow itself)
        if 'workflow_info' in ai_data:
            prefix = 'Xmp.ai.WorkflowInfo.'
            workflow_info = ai_data['workflow_info']
            
            for key, value in workflow_info.items():
                if not isinstance(value, (dict, list)) and value is not None:
                    # Simple value, add directly (with size limit)
                    if isinstance(value, str) and len(value) > 2000:
                        result[f"{prefix}{key}"] = value[:1997] + "..."
                    else:
                        result[f"{prefix}{key}"] = value
                elif isinstance(value, dict):
                    # Handle dictionary as rdf:Description
                    result.update(self._prepare_dict_for_xmp(f"{prefix}{key}", value))
                elif isinstance(value, list):
                    # Handle list as rdf:Bag
                    result.update(self._prepare_list_for_xmp(f"{prefix}{key}", value))
        
        # Copy key parameters to Photoshop namespace for better compatibility
        photoshop_prefix = 'Xmp.photoshop.'
        
        # Model name
        if 'base_model' in generation_data and isinstance(generation_data['base_model'], dict) and 'unet' in generation_data['base_model']:
            result[f"{photoshop_prefix}AI_model"] = generation_data['base_model']['unet']
        
        # Sampling parameters
        if 'sampling' in generation_data and isinstance(generation_data['sampling'], dict):
            sampling = generation_data['sampling']
            for src, dest in [('sampler', 'AI_sampler'), ('steps', 'AI_steps'), 
                            ('cfg_scale', 'AI_cfg_scale'), ('seed', 'AI_seed')]:
                if src in sampling:
                    result[f"{photoshop_prefix}{dest}"] = sampling[src]
        
        # Explicitly remove any workflow related fields
        keys_to_remove = []
        for key in result:
            if any(wk in key.lower() for wk in ['workflow.data', 'generation.prompt', 'workflow_data']):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            result.pop(key, None)
            
        return result

    def _prepare_dict_for_xmp(self, prefix: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare dictionary for XMP as rdf:Description
        
        Args:
            prefix: XMP property prefix
            data: Dictionary data
            
        Returns:
            dict: XMP representation
        """
        result = {}
        
        # Create rdf:Description structure
        description = {}
        
        for key, value in data.items():
            if not isinstance(value, (dict, list)) and value is not None:
                # Simple value
                description[key] = value
            elif isinstance(value, dict):
                # Nested dictionary - create a new property with its own rdf:Description
                nested_prefix = f"{prefix}.{key}"
                result.update(self._prepare_dict_for_xmp(nested_prefix, value))
            elif isinstance(value, list):
                # List - create a property with rdf:Bag
                nested_prefix = f"{prefix}.{key}"
                result.update(self._prepare_list_for_xmp(nested_prefix, value))
        
        # Only add the description if it has content
        if description:
            result[prefix] = {"rdf:Description": description}
        
        return result

    def _prepare_list_for_xmp(self, prefix: str, data: List[Any]) -> Dict[str, Any]:
        """
        Prepare list for XMP as rdf:Bag
        
        Args:
            prefix: XMP property prefix
            data: List data
            
        Returns:
            dict: XMP representation
        """
        result = {}
        
        # Skip empty lists
        if not data:
            return result
        
        # Check if this is a list of simple values or complex objects
        has_complex_items = any(isinstance(item, (dict, list)) for item in data)
        
        if has_complex_items:
            # Complex list - each item can be a dictionary or another list
            bag_items = []
            
            for item in data:
                if isinstance(item, dict):
                    # Dictionary item - create rdf:Description
                    desc = {}
                    
                    for k, v in item.items():
                        if not isinstance(v, (dict, list)) and v is not None:
                            desc[k] = v
                    
                    if desc:
                        bag_items.append({"rdf:Description": desc})
                elif not isinstance(item, (dict, list)) and item is not None:
                    # Simple value
                    bag_items.append(item)
            
            if bag_items:
                result[prefix] = {"rdf:Bag": bag_items}
        else:
            # Simple list - all values are scalar
            result[prefix] = {"rdf:Bag": data}
        
        return result

    def _prepare_region_metadata(self, region_data: Dict[str, Any], existing_xmp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare region metadata for XMP following MWG standard
        
        Args:
            region_data: Region metadata
            existing_xmp: Existing XMP metadata
            
        Returns:
            dict: XMP metadata
        """
        # This is a complex method that would require implementing the MWG region standard
        # We'll rely on the detailed implementation in the XMP handler
        # and just create a minimal implementation here
        
        result = {}
        
        # Check if regions exist
        if 'faces' not in region_data or not region_data['faces']:
            return result
            
        # Create region list
        region_list = []
        
        # Process face regions
        for face in region_data['faces']:
            # Create region
            region = {
                'mwg-rs:Type': face.get('type', 'Face'),
                'mwg-rs:Name': face.get('name', 'Face')
            }
            
            # Add area
            if 'area' in face:
                area = face['area']
                region['mwg-rs:Area'] = {
                    'stArea:x': str(area.get('x', 0)),
                    'stArea:y': str(area.get('y', 0)),
                    'stArea:w': str(area.get('w', 0)),
                    'stArea:h': str(area.get('h', 0))
                }
                
            # Add extensions if present
            if 'extensions' in face and 'eiqa' in face['extensions']:
                region['mwg-rs:Extensions'] = face['extensions']
                
            region_list.append(region)
            
        # Create XMP structure
        if region_list:
            result['Xmp.mwg-rs.Regions'] = {
                'mwg-rs:RegionList': {'rdf:Bag': region_list}
            }
            
            # Add summary if present
            if 'summary' in region_data:
                for key, value in region_data['summary'].items():
                    result[f'Xmp.eiqa.face_summary.{key}'] = value
                    
        return result
    
    def _extract_basic_metadata(self, result: Dict[str, Any], xmp_data: Dict[str, Any], 
                                iptc_data: Dict[str, Any], exif_data: Dict[str, Any]) -> None:
        """
        Extract basic metadata from XMP, IPTC, and EXIF
        
        Args:
            result: Result dictionary to update
            xmp_data: XMP metadata
            iptc_data: IPTC metadata
            exif_data: EXIF metadata
        """
        # Initialize basic section
        if 'basic' not in result:
            result['basic'] = {}
            
        # Title (prefer XMP > IPTC > EXIF)
        if 'Xmp.dc.title' in xmp_data:
            title_data = xmp_data['Xmp.dc.title']
            if isinstance(title_data, dict) and 'x-default' in title_data:
                result['basic']['title'] = title_data['x-default']
            else:
                result['basic']['title'] = str(title_data)
        elif 'Iptc.Application2.ObjectName' in iptc_data:
            result['basic']['title'] = iptc_data['Iptc.Application2.ObjectName']
        elif 'Exif.Image.ImageDescription' in exif_data:
            result['basic']['description'] = exif_data['Exif.Image.ImageDescription']
            
        # Description (prefer XMP > IPTC)
        if 'Xmp.dc.description' in xmp_data:
            desc_data = xmp_data['Xmp.dc.description']
            if isinstance(desc_data, dict) and 'x-default' in desc_data:
                result['basic']['description'] = desc_data['x-default']
            else:
                result['basic']['description'] = str(desc_data)
        elif 'Iptc.Application2.Caption' in iptc_data:
            result['basic']['description'] = iptc_data['Iptc.Application2.Caption']
            
        # Keywords (prefer XMP > IPTC)
        keywords = set()
        if 'Xmp.dc.subject' in xmp_data:
            subject_data = xmp_data['Xmp.dc.subject']
            if isinstance(subject_data, list):
                keywords.update(subject_data)
            else:
                keywords.add(str(subject_data))
                
        if 'Iptc.Application2.Keywords' in iptc_data:
            iptc_keywords = iptc_data['Iptc.Application2.Keywords']
            if isinstance(iptc_keywords, list):
                keywords.update(iptc_keywords)
            else:
                keywords.add(str(iptc_keywords))
                
        if keywords:
            result['basic']['keywords'] = list(keywords)
            
        # Rating
        if 'Xmp.xmp.Rating' in xmp_data:
            try:
                result['basic']['rating'] = int(xmp_data['Xmp.xmp.Rating'])
            except (ValueError, TypeError):
                pass
                
        # Creation date
        for date_field in ['Xmp.xmp.CreateDate', 'Exif.Photo.DateTimeOriginal', 'Exif.Image.DateTime']:
            if date_field in xmp_data:
                result['basic']['create_date'] = xmp_data[date_field]
                break
            elif date_field.replace('Xmp.', 'Exif.') in exif_data:
                result['basic']['create_date'] = exif_data[date_field.replace('Xmp.', 'Exif.')]
                break

    def _extract_analysis_metadata(self, result: Dict[str, Any], xmp_data: Dict[str, Any]) -> None:
        """
        Extract analysis metadata from XMP
        
        Args:
            result: Result dictionary to update
            xmp_data: XMP metadata
        """
        # Initialize analysis section
        if 'analysis' not in result:
            result['analysis'] = {}
            
        # Process all eiqa namespace data
        eiqa_prefix = 'Xmp.eiqa.'
        
        # Keep track of which analysis types we've processed
        processed_types = set()
        
        # Find all eiqa fields
        for key in xmp_data:
            if key.startswith(eiqa_prefix):
                # Extract analysis type (first component after eiqa)
                parts = key[len(eiqa_prefix):].split('.')
                
                if not parts:
                    continue
                    
                analysis_type = parts[0]
                processed_types.add(analysis_type)
                
                # Initialize analysis type if needed
                if analysis_type not in result['analysis']:
                    result['analysis'][analysis_type] = {}
                    
                # Process field based on depth
                if len(parts) == 1:
                    # Direct field
                    result['analysis'][analysis_type] = xmp_data[key]
                elif len(parts) == 2:
                    # One level of nesting
                    result['analysis'][analysis_type][parts[1]] = xmp_data[key]
                elif len(parts) >= 3:
                    # Multiple levels of nesting
                    current = result['analysis'][analysis_type]
                    for part in parts[1:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = xmp_data[key]
                    
        # Process special case for PyIQA data
        if 'pyiqa' in processed_types:
            # Make sure we have the proper nested structure
            if isinstance(result['analysis'].get('pyiqa'), dict):
                # Already structured properly
                pass
            else:
                # Create proper structure
                pyiqa_data = {}
                for key in xmp_data:
                    if key.startswith(eiqa_prefix + 'pyiqa.'):
                        model_name = key[len(eiqa_prefix + 'pyiqa.'):]
                        pyiqa_data[model_name] = xmp_data[key]
                        
                if pyiqa_data:
                    result['analysis']['pyiqa'] = pyiqa_data

    def _extract_ai_metadata(self, result: Dict[str, Any], xmp_data: Dict[str, Any]) -> None:
        """
        Extract AI metadata from XMP
        
        Args:
            result: Result dictionary to update
            xmp_data: XMP metadata
        """
        # Initialize ai_info section
        if 'ai_info' not in result:
            result['ai_info'] = {}
            
        # Process all ai namespace data
        ai_prefix = 'Xmp.ai.'
        
        # Keep track of which AI data types we've processed
        processed_types = set()
        
        # Find all ai fields
        for key in xmp_data:
            if key.startswith(ai_prefix):
                # Extract AI data type (first component after ai)
                parts = key[len(ai_prefix):].split('.')
                
                if not parts:
                    continue
                    
                ai_type = parts[0]
                processed_types.add(ai_type)
                
                # Initialize AI type if needed
                if ai_type not in result['ai_info']:
                    result['ai_info'][ai_type] = {}
                    
                # Process field based on depth
                if len(parts) == 1:
                    # Direct field
                    result['ai_info'][ai_type] = xmp_data[key]
                elif len(parts) == 2:
                    # One level of nesting
                    result['ai_info'][ai_type][parts[1]] = xmp_data[key]
                elif len(parts) >= 3:
                    # Multiple levels of nesting
                    current = result['ai_info'][ai_type]
                    for part in parts[1:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = xmp_data[key]
                    
        # Process special case for generation data
        if 'generation' in processed_types:
            # Handle loras list if it exists as RDF sequence
            if 'Xmp.ai.generation.loras' in xmp_data:
                loras_data = xmp_data['Xmp.ai.generation.loras']
                if isinstance(loras_data, dict) and 'rdf:Seq' in loras_data:
                    loras_list = []
                    for item in loras_data['rdf:Seq']:
                        if isinstance(item, dict):
                            lora = {
                                'name': item.get('ai:name', ''),
                                'strength': float(item.get('ai:strength', 1.0))
                            }
                            loras_list.append(lora)
                        else:
                            loras_list.append({'name': str(item)})
                            
                    result['ai_info']['generation']['loras'] = loras_list
                    
        # Process workflow data
        if 'workflow' in processed_types:
            workflow_data = xmp_data.get('Xmp.ai.workflow')
            if workflow_data:
                try:
                    # Try to parse as JSON
                    import json
                    if isinstance(workflow_data, str):
                        result['ai_info']['workflow'] = json.loads(workflow_data)
                    else:
                        result['ai_info']['workflow'] = workflow_data
                except (json.JSONDecodeError, TypeError):
                    # Store as is if parsing fails
                    result['ai_info']['workflow'] = workflow_data

    def _extract_region_metadata(self, result: Dict[str, Any], xmp_data: Dict[str, Any]) -> None:
        """
        Extract region metadata from XMP
        
        Args:
            result: Result dictionary to update
            xmp_data: XMP metadata
        """
        # Check if regions exist
        if 'Xmp.mwg-rs.Regions' not in xmp_data:
            return
            
        # Initialize regions section
        if 'regions' not in result:
            result['regions'] = {
                'summary': {
                    'face_count': 0,
                    'detector_type': None
                },
                'faces': [],
                'areas': []
            }
            
        # Get region list
        regions_data = xmp_data['Xmp.mwg-rs.Regions']
        if not isinstance(regions_data, dict) or 'mwg-rs:RegionList' not in regions_data:
            return
            
        region_list = regions_data['mwg-rs:RegionList']
        if not isinstance(region_list, dict) or 'rdf:Bag' not in region_list:
            return
            
        bag_items = region_list['rdf:Bag']
        if not isinstance(bag_items, list):
            return
            
        # Process each region
        for item in bag_items:
            if not isinstance(item, dict):
                continue
                
            # Get region type
            region_type = item.get('mwg-rs:Type', '')
            
            # Process based on type
            if region_type == 'Face':
                # Extract face data
                face = {
                    'type': 'Face',
                    'name': item.get('mwg-rs:Name', 'Face')
                }
                
                # Extract area
                area_data = item.get('mwg-rs:Area')
                if isinstance(area_data, dict):
                    face['area'] = {
                        'x': float(area_data.get('stArea:x', 0)),
                        'y': float(area_data.get('stArea:y', 0)),
                        'w': float(area_data.get('stArea:w', 0)),
                        'h': float(area_data.get('stArea:h', 0))
                    }
                else:
                    # Skip face without area
                    continue
                    
                # Extract extensions
                extensions_data = item.get('mwg-rs:Extensions')
                if isinstance(extensions_data, dict):
                    face['extensions'] = {'eiqa': {}}
                    
                    # Get face analysis data
                    eiqa_data = extensions_data.get('eiqa:FaceAnalysis')
                    if isinstance(eiqa_data, dict):
                        face['extensions']['eiqa']['face_analysis'] = eiqa_data
                        
                # Add face to list
                result['regions']['faces'].append(face)
                
            elif region_type:
                # Extract area data
                area = {
                    'type': region_type,
                    'name': item.get('mwg-rs:Name', region_type)
                }
                
                # Extract area
                area_data = item.get('mwg-rs:Area')
                if isinstance(area_data, dict):
                    area['area'] = {
                        'x': float(area_data.get('stArea:x', 0)),
                        'y': float(area_data.get('stArea:y', 0)),
                        'w': float(area_data.get('stArea:w', 0)),
                        'h': float(area_data.get('stArea:h', 0))
                    }
                else:
                    # Skip area without coordinates
                    continue
                    
                # Add area to list
                result['regions']['areas'].append(area)
                
        # Update summary
        result['regions']['summary']['face_count'] = len(result['regions']['faces'])
        
        # Get detector type from face analysis summary if present
        eiqa_summary = xmp_data.get('Xmp.eiqa.face_summary', {})
        if isinstance(eiqa_summary, dict) and 'detector_type' in eiqa_summary:
            result['regions']['summary']['detector_type'] = eiqa_summary['detector_type']

    def _add_basic_metadata_to_xmp(self, desc: ET.Element, basic_data: Dict[str, Any]) -> None:
        """
        Add basic metadata to XMP Description element following MWG standards and Adobe specifications
        
        Args:
            desc: Description element
            basic_data: Basic metadata
        """
        
        # Title with language alternative - Adobe standard approach
        if 'title' in basic_data:
            title_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}ObjectName")
            title_attr.text = str(basic_data['title'])

            title_elem = ET.SubElement(desc, f"{{{self.XMP_NS['dc']}}}title")
            alt = ET.SubElement(title_elem, f"{{{self.XMP_NS['rdf']}}}Alt")
            li = ET.SubElement(alt, f"{{{self.XMP_NS['rdf']}}}li")
            li.set(f"{{{self.XMP_NS['xml']}}}lang", "x-default")
            li.text = str(basic_data['title'])
            
            # Add additional title fields for compatibility
            if 'headline' not in basic_data:
                headline_elem = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}Headline")
                headline_elem.text = str(basic_data['title'])
            
        # Description with language alternative - Adobe standard approach
        if 'description' in basic_data:
            desc_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}Caption-Abstract")
            desc_attr.text = str(basic_data['description'])
            desc_elem = ET.SubElement(desc, f"{{{self.XMP_NS['dc']}}}description")
            alt = ET.SubElement(desc_elem, f"{{{self.XMP_NS['rdf']}}}Alt")
            li = ET.SubElement(alt, f"{{{self.XMP_NS['rdf']}}}li")
            li.set(f"{{{self.XMP_NS['xml']}}}lang", "x-default")
            li.text = str(basic_data['description'])
            
            # Add caption field for compatibility
            if 'caption' not in basic_data:
                caption_elem = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}Caption")
                caption_elem.text = str(basic_data['description'])
        
        # Creator as sequence
        if 'creator' in basic_data:
            # For IPTC-IIM compatibility - this is critical for Adobe
            auth_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}Author")
            auth_attr.text = str(basic_data['creator'])
            
            # For IPTC-IIM compatibility - Photoshop also looks at this
            byline_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}Byline")
            byline_attr.text = str(basic_data['creator'])
            
            # Add standard XMP creator with sequence structure
            creator_elem = ET.SubElement(desc, f"{{{self.XMP_NS['dc']}}}creator")
            seq = ET.SubElement(creator_elem, f"{{{self.XMP_NS['rdf']}}}Seq")
            li = ET.SubElement(seq, f"{{{self.XMP_NS['rdf']}}}li")
            li.text = str(basic_data['creator'])
        
        # Rights/Copyright with language alternative - Adobe standard approach
        if 'copyright' in basic_data or 'rights' in basic_data:
            copyright_text = basic_data.get('copyright', basic_data.get('rights', ''))
            
            # For IPTC-IIM compatibility - these are what Adobe reads for copyright
            notice_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}CopyrightNotice")
            notice_attr.text = str(copyright_text)
            
            status_attr = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}CopyrightStatus")
            status_attr.text = "Copyrighted"

            # Standard language alternative structure for rights
            rights_elem = ET.SubElement(desc, f"{{{self.XMP_NS['dc']}}}rights")
            alt = ET.SubElement(rights_elem, f"{{{self.XMP_NS['rdf']}}}Alt")
            li = ET.SubElement(alt, f"{{{self.XMP_NS['rdf']}}}li")
            li.set(f"{{{self.XMP_NS['xml']}}}lang", "x-default")
            li.text = str(copyright_text)
            
            # Standard XMP Rights Management fields
            marked_elem = ET.SubElement(desc, f"{{{self.XMP_NS['xmpRights']}}}Marked")
            marked_elem.text = 'True'
            
            # Add usage terms
            terms_elem = ET.SubElement(desc, f"{{{self.XMP_NS['xmpRights']}}}UsageTerms")
            terms_alt = ET.SubElement(terms_elem, f"{{{self.XMP_NS['rdf']}}}Alt")
            terms_li = ET.SubElement(terms_alt, f"{{{self.XMP_NS['rdf']}}}li")
            terms_li.set(f"{{{self.XMP_NS['xml']}}}lang", "x-default")
            terms_li.text = str(copyright_text)
            
            # Add copyright notice and status fields for compatibility
            copyright_notice = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}CopyrightNotice")
            copyright_notice.text = str(copyright_text)
            
            status_elem = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}CopyrightStatus")
            status_elem.text = 'Copyrighted'
        
        # Rating - standard across Adobe products
        if 'rating' in basic_data:
            rating_elem = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}Rating")
            rating_elem.text = str(basic_data['rating'])
            
        # Keywords as bag - Adobe standard approach
        if 'keywords' in basic_data and basic_data['keywords']:
            keywords = basic_data['keywords']
            
            # Ensure keywords is a list
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',')]
            elif not isinstance(keywords, (list, tuple, set)):
                keywords = [str(keywords)]
                
            # Create standard bag structure
            subject_elem = ET.SubElement(desc, f"{{{self.XMP_NS['dc']}}}subject")
            bag = ET.SubElement(subject_elem, f"{{{self.XMP_NS['rdf']}}}Bag")
            
            # Add each keyword
            for keyword in keywords:
                li = ET.SubElement(bag, f"{{{self.XMP_NS['rdf']}}}li")
                li.text = str(keyword)
        
        # Add CreatorTool field - standard Adobe field for creation application
        creator_tool = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}CreatorTool")
        creator_tool.text = 'ComfyUI'
        
        # Add creation date - critical for Adobe timeline functionality
        if 'create_date' in basic_data:
            create_date = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}CreateDate")
            create_date.text = str(basic_data['create_date'])
        else:
            create_date = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}CreateDate")
            create_date.text = datetime.datetime.now().isoformat()
        
        # Add modification date
        modify_date = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}ModifyDate")
        modify_date.text = datetime.datetime.now().isoformat()
        
        # Add metadata date - when metadata was last modified (MWG standard)
        metadata_date = ET.SubElement(desc, f"{{{self.XMP_NS['xmp']}}}MetadataDate")
        metadata_date.text = datetime.datetime.now().isoformat()
        
        # Add XMP Media Management fields for document tracking (Adobe standard)
        if 'project' in basic_data:
            # Create a document ID based on the project name
            document_id = f"xmp.did:project:{basic_data['project'].replace(' ', '_')}"
            doc_id_elem = ET.SubElement(desc, f"{{{self.XMP_NS['xmpMM']}}}DocumentID")
            doc_id_elem.text = document_id
            
            # Add original document ID
            orig_doc_id = ET.SubElement(desc, f"{{{self.XMP_NS['xmpMM']}}}OriginalDocumentID")
            orig_doc_id.text = document_id
        else:
            # Create a unique ID if no project name
            doc_id_elem = ET.SubElement(desc, f"{{{self.XMP_NS['xmpMM']}}}DocumentID")
            doc_id_elem.text = f"xmp.did:{uuid.uuid4()}"
        
        # Add instance ID for this specific version
        instance_id = ET.SubElement(desc, f"{{{self.XMP_NS['xmpMM']}}}InstanceID")
        instance_id.text = f"xmp.iid:{uuid.uuid4()}"
        
        # Add text layers info if applicable (for formats like PSD, TIFF)
        if 'text_layers' in basic_data and basic_data['text_layers']:
            text_layers = ET.SubElement(desc, f"{{{self.XMP_NS['photoshop']}}}TextLayers")
            layers_seq = ET.SubElement(text_layers, f"{{{self.XMP_NS['rdf']}}}Seq")
            
            for layer in basic_data['text_layers']:
                layer_li = ET.SubElement(layers_seq, f"{{{self.XMP_NS['rdf']}}}li")
                layer_desc = ET.SubElement(layer_li, f"{{{self.XMP_NS['rdf']}}}Description")
                
                layer_name = ET.SubElement(layer_desc, f"{{{self.XMP_NS['photoshop']}}}LayerName")
                layer_name.text = layer.get('name', 'Text Layer')
                
                layer_text = ET.SubElement(layer_desc, f"{{{self.XMP_NS['photoshop']}}}LayerText")
                layer_text.text = layer.get('text', '')

    def _add_analysis_metadata_to_xmp(self, desc: ET.Element, analysis_data: Dict[str, Any]) -> None:
        """
        Add analysis metadata to XMP Description element
        
        Args:
            desc: Description element
            analysis_data: Analysis metadata
        """
        import xml.etree.ElementTree as ET
        
        # Process each analysis type
        for analysis_type, data in analysis_data.items():
            # Skip empty data
            if not data:
                continue
                
            # Create container for this analysis type
            analysis_elem = ET.SubElement(desc, f"{{{self.XMP_NS['eiqa']}}}{analysis_type}")
            analysis_desc = ET.SubElement(analysis_elem, f"{{{self.XMP_NS['rdf']}}}Description")
            
            # Add data based on type
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Nested structure
                        sub_elem = ET.SubElement(analysis_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                        sub_desc = ET.SubElement(sub_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                        
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, dict):
                                # Double nested structure
                                subsub_elem = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}{subkey}")
                                subsub_desc = ET.SubElement(subsub_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                                
                                for subsubkey, subsubvalue in subvalue.items():
                                    subsubval_elem = ET.SubElement(subsub_desc, f"{{{self.XMP_NS['eiqa']}}}{subsubkey}")
                                    subsubval_elem.text = str(subsubvalue)
                            elif isinstance(subvalue, (list, tuple, set)):
                                # List as Bag
                                subval_elem = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}{subkey}")
                                bag = ET.SubElement(subval_elem, f"{{{self.XMP_NS['rdf']}}}Bag")
                                
                                for item in subvalue:
                                    li = ET.SubElement(bag, f"{{{self.XMP_NS['rdf']}}}li")
                                    li.text = str(item)
                            else:
                                # Simple value
                                subval_elem = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}{subkey}")
                                subval_elem.text = str(subvalue)
                    elif isinstance(value, (list, tuple, set)):
                        # List as Bag
                        val_elem = ET.SubElement(analysis_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                        bag = ET.SubElement(val_elem, f"{{{self.XMP_NS['rdf']}}}Bag")
                        
                        for item in value:
                            li = ET.SubElement(bag, f"{{{self.XMP_NS['rdf']}}}li")
                            li.text = str(item)
                    else:
                        # Simple value
                        val_elem = ET.SubElement(analysis_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                        val_elem.text = str(value)
            else:
                # Simple value for entire analysis type
                analysis_desc.text = str(data)
                
            # Add timestamp if not present
            if isinstance(data, dict) and 'timestamp' not in data:
                timestamp_elem = ET.SubElement(analysis_desc, f"{{{self.XMP_NS['eiqa']}}}timestamp")
                timestamp_elem.text = self.get_timestamp()

    def _add_ai_metadata_to_xmp(self, desc: ET.Element, ai_data: Dict[str, Any]) -> None:
        """
        Add AI metadata to XMP Description element
        
        Args:
            desc: Description element
            ai_data: AI metadata
        """
        import xml.etree.ElementTree as ET
        
        # Handle generation data
        if 'generation' in ai_data:
            gen_data = ai_data['generation']
            
            # Create generation container
            gen_elem = ET.SubElement(desc, f"{{{self.XMP_NS['ai']}}}generation")
            gen_desc = ET.SubElement(gen_elem, f"{{{self.XMP_NS['rdf']}}}Description")
            
            # Add each generation parameter
            for key, value in gen_data.items():
                if key == 'loras' and isinstance(value, list):
                    # Handle LoRAs as a sequence
                    loras_elem = ET.SubElement(gen_desc, f"{{{self.XMP_NS['ai']}}}loras")
                    seq = ET.SubElement(loras_elem, f"{{{self.XMP_NS['rdf']}}}Seq")
                    
                    for lora in value:
                        if isinstance(lora, dict):
                            li = ET.SubElement(seq, f"{{{self.XMP_NS['rdf']}}}li")
                            lora_desc = ET.SubElement(li, f"{{{self.XMP_NS['rdf']}}}Description")
                            
                            name_elem = ET.SubElement(lora_desc, f"{{{self.XMP_NS['ai']}}}name")
                            name_elem.text = str(lora.get('name', ''))
                            
                            strength_elem = ET.SubElement(lora_desc, f"{{{self.XMP_NS['ai']}}}strength")
                            strength_elem.text = str(lora.get('strength', 1.0))
                else:
                    # Simple field
                    elem = ET.SubElement(gen_desc, f"{{{self.XMP_NS['ai']}}}{key}")
                    elem.text = str(value)
                    
            # Add timestamp if not present
            if 'timestamp' not in gen_data:
                timestamp_elem = ET.SubElement(gen_desc, f"{{{self.XMP_NS['ai']}}}timestamp")
                timestamp_elem.text = self.get_timestamp()
                
        # Handle workflow data
        if 'workflow' in ai_data:
            workflow_data = ai_data['workflow']
            
            # Create workflow container
            workflow_elem = ET.SubElement(desc, f"{{{self.XMP_NS['ai']}}}workflow")
            
            # Store as JSON string
            import json
            workflow_elem.text = json.dumps(workflow_data)
            
        # Handle other AI data
        for key, value in ai_data.items():
            if key not in ['generation', 'workflow']:
                # Create container
                ai_elem = ET.SubElement(desc, f"{{{self.XMP_NS['ai']}}}{key}")
                
                if isinstance(value, dict):
                    # Complex structure
                    ai_desc = ET.SubElement(ai_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                    
                    for subkey, subvalue in value.items():
                        sub_elem = ET.SubElement(ai_desc, f"{{{self.XMP_NS['ai']}}}{subkey}")
                        sub_elem.text = str(subvalue)
                else:
                    # Simple value
                    ai_elem.text = str(value)

    def _add_region_metadata_to_xmp(self, desc: ET.Element, region_data: Dict[str, Any]) -> None:
        """
        Add region metadata to XMP Description element following MWG standard
        
        Args:
            desc: Description element
            region_data: Region metadata
        """
        import xml.etree.ElementTree as ET
        
        # Check if regions exist
        if 'faces' not in region_data or not region_data['faces']:
            return
            
        # Create regions container
        regions_elem = ET.SubElement(desc, f"{{{self.XMP_NS['mwg-rs']}}}Regions")
        regions_desc = ET.SubElement(regions_elem, f"{{{self.XMP_NS['rdf']}}}Description")
        
        # Create RegionList container
        region_list = ET.SubElement(regions_desc, f"{{{self.XMP_NS['mwg-rs']}}}RegionList")
        bag = ET.SubElement(region_list, f"{{{self.XMP_NS['rdf']}}}Bag")
        
        # Process face regions
        for face in region_data['faces']:
            # Create list item
            li = ET.SubElement(bag, f"{{{self.XMP_NS['rdf']}}}li")
            face_desc = ET.SubElement(li, f"{{{self.XMP_NS['rdf']}}}Description")
            
            # Add type and name
            type_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['mwg-rs']}}}Type")
            type_elem.text = face.get('type', 'Face')
            
            name_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['mwg-rs']}}}Name")
            name_elem.text = face.get('name', 'Face')
            
            # Add area
            if 'area' in face:
                area = face['area']
                area_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['mwg-rs']}}}Area")
                
                # Add coordinates as attributes
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}x", str(area.get('x', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}y", str(area.get('y', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}w", str(area.get('w', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}h", str(area.get('h', 0)))
                
            # Add extensions if present
            if 'extensions' in face and 'eiqa' in face['extensions']:
                ext_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['mwg-rs']}}}Extensions")
                ext_desc = ET.SubElement(ext_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                
                # Add face analysis
                if 'face_analysis' in face['extensions']['eiqa']:
                    face_analysis = face['extensions']['eiqa']['face_analysis']
                    
                    face_elem = ET.SubElement(ext_desc, f"{{{self.XMP_NS['eiqa']}}}face_analysis")
                    face_desc = ET.SubElement(face_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                    
                    # Add face analysis data
                    for key, value in face_analysis.items():
                        if isinstance(value, dict):
                            # Nested structure (e.g., emotion scores)
                            sub_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                            sub_desc = ET.SubElement(sub_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                            
                            for subkey, subvalue in value.items():
                                if subkey == 'scores' and isinstance(subvalue, dict):
                                    # Handle scores as a nested structure
                                    scores_elem = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}scores")
                                    scores_desc = ET.SubElement(scores_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                                    
                                    for score_name, score_value in subvalue.items():
                                        score_elem = ET.SubElement(scores_desc, f"{{{self.XMP_NS['eiqa']}}}{score_name}")
                                        score_elem.text = str(score_value)
                                else:
                                    # Simple value
                                    val_elem = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}{subkey}")
                                    val_elem.text = str(subvalue)
                        else:
                            # Simple value
                            val_elem = ET.SubElement(face_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                            val_elem.text = str(value)
                            
        # Process area regions
        for area in region_data.get('areas', []):
            # Create list item
            li = ET.SubElement(bag, f"{{{self.XMP_NS['rdf']}}}li")
            area_desc = ET.SubElement(li, f"{{{self.XMP_NS['rdf']}}}Description")
            
            # Add type and name
            type_elem = ET.SubElement(area_desc, f"{{{self.XMP_NS['mwg-rs']}}}Type")
            type_elem.text = area.get('type', 'Area')
            
            name_elem = ET.SubElement(area_desc, f"{{{self.XMP_NS['mwg-rs']}}}Name")
            name_elem.text = area.get('name', 'Area')
            
            # Add area
            area_elem = ET.SubElement(area_desc, f"{{{self.XMP_NS['mwg-rs']}}}Area")
            
            # Add coordinates as attributes
            if 'area' in area:
                area_coords = area['area']
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}x", str(area_coords.get('x', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}y", str(area_coords.get('y', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}w", str(area_coords.get('w', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}h", str(area_coords.get('h', 0)))
            else:
                # Handle direct coordinates if not in 'area' subfield
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}x", str(area.get('x', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}y", str(area.get('y', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}w", str(area.get('w', 0)))
                area_elem.set(f"{{{self.XMP_NS['stArea']}}}h", str(area.get('h', 0)))
            
            # Add extensions if present
            if 'extensions' in area:
                ext_elem = ET.SubElement(area_desc, f"{{{self.XMP_NS['mwg-rs']}}}Extensions")
                ext_desc = ET.SubElement(ext_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                
                # Add EIQA extensions
                if 'eiqa' in area['extensions']:
                    for key, value in area['extensions']['eiqa'].items():
                        if isinstance(value, dict):
                            # Handle nested structure
                            sub_elem = ET.SubElement(ext_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                            sub_desc = ET.SubElement(sub_elem, f"{{{self.XMP_NS['rdf']}}}Description")
                            
                            for subkey, subvalue in value.items():
                                sub_item = ET.SubElement(sub_desc, f"{{{self.XMP_NS['eiqa']}}}{subkey}")
                                sub_item.text = str(subvalue)
                        else:
                            # Simple value
                            elem = ET.SubElement(ext_desc, f"{{{self.XMP_NS['eiqa']}}}{key}")
                            elem.text = str(value)
    def cleanup(self):
        """Clean up resources used by the handler"""
        try:
            # Close any open image if present
            if self._current_metadata is not None:
                try:
                    if hasattr(self._current_metadata, 'close'):
                        self._current_metadata.close()
                except Exception as e:
                    self.log(f"Error closing metadata object: {str(e)}", level="WARNING")
                self._current_metadata = None
        except Exception as e:
            self.log(f"Cleanup error: {str(e)}", level="ERROR")
            
    def _cleanup_current_metadata(self):
        """Helper to clean up current metadata object"""
        if self._current_metadata is not None:
            try:
                if hasattr(self._current_metadata, 'close'):
                    self._current_metadata.close()
            except Exception:
                pass
            self._current_metadata = None