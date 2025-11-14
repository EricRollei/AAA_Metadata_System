"""
ComfyUI Node: Eric's Metadata Debugger V2
Description: Debug and inspect metadata across all storage methods.
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


Eric's Metadata Debugger V2 - Updated March 2025

Debug and inspect metadata across all storage methods.
Useful for diagnosing issues with metadata writing and reading.
"""

import os
import json
import datetime
from typing import Dict, Any, List

# Import the metadata service from the package
from AAA_Metadata_System import MetadataService

class MetadataDebugNodeV2:
    """Debug and inspect metadata across all storage methods"""
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filepath": ("STRING", {"default": ""}),
            },
            "optional": {
                "check_xmp": ("BOOLEAN", {"default": True}),
                "check_embedded": ("BOOLEAN", {"default": True}),
                "check_text": ("BOOLEAN", {"default": False}),
                "check_database": ("BOOLEAN", {"default": False}),
                "show_raw_data": ("BOOLEAN", {"default": False}),
                "verbose": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("debug_info",)
    FUNCTION = "debug_metadata"
    CATEGORY = "Eric's Nodes/Metadata"

    def debug_metadata(self, filepath, check_xmp=True, check_embedded=True, 
                     check_text=False, check_database=False, 
                     show_raw_data=False, verbose=False):
        """Generate a detailed report on metadata status"""
        try:
            result = ["Metadata Debug Report"]
            result.append("=" * 50)
            
            # Verify file exists
            if not os.path.exists(filepath):
                return (f"Error: File not found - {filepath}",)
                
            # File info
            result.append(f"File: {filepath}")
            result.append(f"Size: {os.path.getsize(filepath):,} bytes")
            file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            result.append(f"Last modified: {file_mod_time.isoformat()}")
            result.append("")
            
            # Check format information using FormatHandler
            format_info = self.metadata_service._get_format_info(filepath)
            result.append("File Format Information:")
            result.append("-" * 30)
            result.append(f"Extension: {format_info.get('extension', 'unknown')}")
            result.append(f"Handler type: {format_info.get('handler_type', 'unknown')}")
            result.append(f"Supports PyExiv2: {'Yes' if format_info.get('can_use_pyexiv2', False) else 'No'}")
            result.append(f"Requires ExifTool: {'Yes' if format_info.get('requires_exiftool', False) else 'No'}")
            result.append("")
            
            # Create path variables for checks
            base_path = os.path.splitext(filepath)[0]
            xmp_path = f"{base_path}.xmp"
            txt_path = f"{base_path}.txt"
            incorrect_xmp_path = f"{filepath}.xmp"
            
            # Check XMP sidecar
            if check_xmp:
                result.append("XMP Sidecar Check:")
                result.append("-" * 30)
                result.append(f"Expected sidecar path: {xmp_path}")
                
                # Check for incorrect sidecar file naming
                if os.path.exists(incorrect_xmp_path):
                    result.append("⚠️ WARNING: Found sidecar with incorrect name format!")
                    result.append(f"Incorrect sidecar: {incorrect_xmp_path}")
                    result.append(f"Size: {os.path.getsize(incorrect_xmp_path):,} bytes")
                
                # Check for correct sidecar
                if os.path.exists(xmp_path):
                    result.append("✓ Sidecar file exists")
                    result.append(f"Size: {os.path.getsize(xmp_path):,} bytes")
                    
                    # Read using MetadataService
                    try:
                        metadata = self.metadata_service.read_metadata(filepath, source='xmp')
                        self._analyze_metadata(metadata, result, "XMP", show_raw_data, verbose)
                    except Exception as e:
                        result.append(f"Error reading XMP metadata: {str(e)}")
                else:
                    result.append("✗ Sidecar file does not exist")
                
                result.append("")
            
            # Check embedded metadata
            if check_embedded:
                result.append("Embedded Metadata Check:")
                result.append("-" * 30)
                
                try:
                    metadata = self.metadata_service.read_metadata(filepath, source='embedded')
                    
                    if metadata:
                        result.append("✓ Embedded metadata found")
                        self._analyze_metadata(metadata, result, "Embedded", show_raw_data, verbose)
                    else:
                        result.append("✗ No embedded metadata found")
                except Exception as e:
                    result.append(f"Error reading embedded metadata: {str(e)}")
                    
                result.append("")
            
            # Check text file
            if check_text:
                result.append("Text File Check:")
                result.append("-" * 30)
                result.append(f"Expected text file: {txt_path}")
                
                if os.path.exists(txt_path):
                    result.append("✓ Text file exists")
                    result.append(f"Size: {os.path.getsize(txt_path):,} bytes")
                    
                    try:
                        metadata = self.metadata_service.read_metadata(filepath, source='txt')
                        self._analyze_metadata(metadata, result, "Text", show_raw_data, verbose)
                    except Exception as e:
                        result.append(f"Error reading text metadata: {str(e)}")
                else:
                    result.append("✗ Text file does not exist")
                    
                result.append("")
            
            # Check database
            if check_database:
                result.append("Database Check:")
                result.append("-" * 30)
                
                try:
                    # Get database handler through service
                    db_handler = self.metadata_service._get_db_handler()
                    
                    if db_handler:
                        metadata = self.metadata_service.read_metadata(filepath, source='db')
                        
                        if metadata:
                            result.append("✓ Database record found")
                            self._analyze_metadata(metadata, result, "Database", show_raw_data, verbose)
                            
                            # Check database-specific information if verbose
                            if verbose:
                                # Get image ID from database
                                db_handler.cursor.execute("SELECT id FROM images WHERE filepath = ?", (filepath,))
                                row = db_handler.cursor.fetchone()
                                if row:
                                    img_id = row['id']
                                    result.append(f"Database image ID: {img_id}")
                                    
                                    # Check related tables
                                    tables = ['keywords', 'scores', 'classifications', 'ai_info', 'regions']
                                    for table in tables:
                                        db_handler.cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE image_id = ?", (img_id,))
                                        count = db_handler.cursor.fetchone()['count']
                                        result.append(f"  {table} records: {count}")
                        else:
                            result.append("✗ No database record found")
                    else:
                        result.append("✗ Database handler not available")
                except Exception as e:
                    result.append(f"Error checking database: {str(e)}")
                    
                result.append("")
            
            # Comparison check
            if sum([check_xmp, check_embedded, check_text, check_database]) > 1:
                result.append("Metadata Consistency Check:")
                result.append("-" * 30)
                
                sources = []
                if check_xmp: sources.append('xmp')
                if check_embedded: sources.append('embedded')
                if check_text: sources.append('txt')
                if check_database: sources.append('db')
                
                metadata_by_source = {}
                for source in sources:
                    try:
                        metadata = self.metadata_service.read_metadata(filepath, source=source)
                        if metadata:
                            metadata_by_source[source] = metadata
                    except:
                        pass
                
                if len(metadata_by_source) > 1:
                    # Check if the same sections exist in all sources
                    all_sections = set()
                    for metadata in metadata_by_source.values():
                        all_sections.update(metadata.keys())
                    
                    for section in all_sections:
                        result.append(f"Section '{section}' presence:")
                        for source, metadata in metadata_by_source.items():
                            if section in metadata:
                                result.append(f"  ✓ {source}")
                            else:
                                result.append(f"  ✗ {source} (missing)")
                else:
                    result.append("Not enough metadata sources to compare")
                
            return ("\n".join(result),)
            
        except Exception as e:
            return (f"Debug error: {str(e)}",)
        finally:
            # Clean up resources
            self.metadata_service.cleanup()
    
    def _analyze_metadata(self, metadata: Dict[str, Any], result: List[str], 
                         source_name: str, show_raw: bool, verbose: bool) -> None:
        """Analyze metadata structure and add to result list"""
        if not metadata:
            result.append(f"No {source_name} metadata found")
            return
            
        # Check for key sections
        result.append(f"\n{source_name} metadata sections present:")
        for section in ["basic", "ai_info", "analysis", "regions"]:
            if section in metadata:
                section_data = metadata[section]
                if not section_data:
                    result.append(f"✓ {section} (empty)")
                    continue
                    
                result.append(f"✓ {section}")
                
                # Handle basic section
                if section == "basic":
                    fields = [
                        ("title", "Title"), 
                        ("description", "Description"),
                        ("keywords", "Keywords"),
                        ("rating", "Rating"),
                        ("creator", "Creator/Author"),
                        ("rights", "Copyright"),
                        ("category", "Category")
                    ]
                    
                    for field_key, field_name in fields:
                        if field_key in section_data:
                            value = section_data[field_key]
                            if isinstance(value, list) and len(value) > 5:
                                value = f"{value[:5]} ... ({len(value)} items)"
                            result.append(f"  ✓ {field_name}: {value}")
                            
                # Handle ai_info section
                elif section == "ai_info":
                    if "generation" in section_data:
                        result.append("  ✓ Generation Info")
                        gen = section_data["generation"]
                        
                        if verbose:
                            for key in ["model", "prompt", "negative_prompt", "seed", "steps", "cfg_scale", "sampler"]:
                                if key in gen:
                                    # Truncate long values
                                    value = gen[key]
                                    if isinstance(value, str) and len(value) > 50:
                                        value = value[:50] + "..."
                                    result.append(f"    - {key}: {value}")
                
                # Handle analysis section
                elif section == "analysis":
                    for subsection in section_data:
                        subsection_data = section_data[subsection]
                        result.append(f"  ✓ {subsection}")
                        
                        if verbose:
                            # Different handling based on analysis type
                            if subsection == "pyiqa":
                                # For PyIQA, show model scores
                                for model, score_info in subsection_data.items():
                                    if isinstance(score_info, dict) and "score" in score_info:
                                        score = score_info["score"]
                                        higher_better = score_info.get("higher_better", True)
                                        result.append(f"    - {model}: {score} ({'higher is better' if higher_better else 'lower is better'})")
                            elif subsection == "technical":
                                # For technical, show metrics
                                for metric, metric_data in subsection_data.items():
                                    if isinstance(metric_data, dict) and "score" in metric_data:
                                        score = metric_data["score"]
                                        result.append(f"    - {metric}: {score}")
                                
                # Handle regions section
                elif section == "regions":
                    if "faces" in section_data:
                        faces = section_data["faces"]
                        result.append(f"  ✓ Faces: {len(faces)}")
                        
                        if verbose and faces:
                            for i, face in enumerate(faces[:3]):  # Show first 3 faces
                                result.append(f"    - Face {i+1}: {face.get('name', 'Unnamed')}")
                                if "area" in face:
                                    area = face["area"]
                                    result.append(f"      Position: x={area.get('x', 0):.2f}, y={area.get('y', 0):.2f}, w={area.get('w', 0):.2f}, h={area.get('h', 0):.2f}")
                            
                            if len(faces) > 3:
                                result.append(f"      ... and {len(faces) - 3} more faces")
            else:
                result.append(f"✗ {section} (missing)")
                
        # Show raw data if requested
        if show_raw:
            result.append(f"\nRaw {source_name} metadata:")
            result.append("-" * 30)
            
            try:
                # Limit raw output to prevent overwhelming the UI
                import json
                formatted_json = json.dumps(metadata, indent=2)
                lines = formatted_json.split('\n')
                
                if len(lines) > 50 and not verbose:
                    result.extend(lines[:50])
                    result.append(f"... and {len(lines) - 50} more lines (enable verbose for full output)")
                else:
                    result.extend(lines)
            except Exception as e:
                result.append(f"Error formatting raw data: {str(e)}")

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "Eric_Metadata_Debugger_V2": MetadataDebugNodeV2
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Eric_Metadata_Debugger_V2": "Eric's Metadata Debugger V2"
}