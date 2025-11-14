"""
ComfyUI Node: eric_save_true_svg_image
Description: Specialized node for saving native SVG content with embedded metadata support
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 1.0.0
Date: [July 2025]
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

Description:
This node specializes in saving native SVG content (such as output from WordCloud nodes)
while preserving the full metadata system functionality from the main save image node.
It's designed to handle true vector SVG content without raster-to-vector conversion.
"""

import json
import datetime
import os
import time
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple
import folder_paths

# Import the metadata system components (using relative imports)
try:
    from ..eric_metadata.service import MetadataService
    from ..eric_metadata.utils.workflow_parser import WorkflowParser
    from ..eric_metadata.utils.workflow_extractor import WorkflowExtractor
    from ..eric_metadata.utils.workflow_metadata_processor import WorkflowMetadataProcessor
except ImportError:
    # Fallback for testing - try absolute imports
    try:
        from eric_metadata.service import MetadataService
        from eric_metadata.utils.workflow_parser import WorkflowParser
        from eric_metadata.utils.workflow_extractor import WorkflowExtractor
        from eric_metadata.utils.workflow_metadata_processor import WorkflowMetadataProcessor
    except ImportError:
        # Final fallback - create minimal stubs for testing
        print("[EricSaveTrueSVGImage] Warning: Metadata system not available, using minimal functionality")
        
        class MetadataService:
            def __init__(self): pass
            def save_metadata(self, data): pass
            
        class WorkflowParser:
            def __init__(self): pass
            def ensure_serializable_metadata(self, data): return data
            
        class WorkflowExtractor:
            def __init__(self): pass
            
        class WorkflowMetadataProcessor:
            def __init__(self): pass


class EricSaveTrueSVGImage:
    """
    Specialized node for saving native SVG content with full metadata support.
    
    This node handles true vector SVG content (like WordCloud SVG output) and embeds
    comprehensive metadata including workflow information, custom fields, and Dublin Core
    metadata directly into the SVG file structure.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "svg_content": ("STRING", {"forceInput": True, "tooltip": "Native SVG content as string"}),
                "filename_prefix": ("STRING", {"default": "wordcloud_svg", "tooltip": "Base name for saved files"}),
            },
            "optional": {
                # File naming options
                "include_project": ("BOOLEAN", {"default": False, "tooltip": "Add project name to filename"}),
                "include_datetime": ("BOOLEAN", {"default": True, "tooltip": "Add date and time to filename"}),
                
                # Output location options
                "custom_output_directory": ("STRING", {
                    "default": "", 
                    "tooltip": "Override the default output location. For relative paths, use 'subfolder' format. Leave empty to use default output folder."
                }),
                "output_path_mode": (["Absolute Path", "Subfolder in Output"], 
                    {"default": "Subfolder in Output", 
                    "tooltip": "How to interpret the custom output directory"}),
                "filename_format": (["Default (padded zeros)", "Simple (file1.svg)"], 
                    {"default": "Default (padded zeros)", 
                    "tooltip": "How to format sequential filenames"}),
                
                # Metadata content options
                "enable_metadata": ("BOOLEAN", 
                    {"default": True, "tooltip": "Master switch to enable/disable all metadata writing"}),
                "title": ("STRING", 
                    {"default": "", "tooltip": "SVG title"}),
                "project": ("STRING", 
                    {"default": "", "tooltip": "Project name for organization"}),
                "description": ("STRING", 
                    {"default": "", "tooltip": "SVG description/caption"}),
                "creator": ("STRING", 
                    {"default": "", "tooltip": "Creator/artist name"}),
                "copyright": ("STRING", 
                    {"default": "", "tooltip": "Copyright information"}),
                "keywords": ("STRING", 
                    {"default": "", "tooltip": "Comma-separated keywords/tags"}),
                "custom_metadata": ("STRING", {
                    "default": "{}", 
                    "multiline": False, 
                    "tooltip": "Custom metadata in JSON format"
                }),
                
                # Metadata storage options
                "save_embedded": ("BOOLEAN", 
                    {"default": True, "tooltip": "Embed metadata directly in the SVG file"}),
                "save_workflow_as_json": ("BOOLEAN", 
                    {"default": True, "tooltip": "Save workflow data as a separate JSON file (required for ComfyUI workflow loading)"}),
                "save_workflow_as_txt": ("BOOLEAN", 
                    {"default": False, "tooltip": "Save workflow data as a separate text file"}),
                "save_xmp": ("BOOLEAN", 
                    {"default": False, "tooltip": "Save XMP sidecar file with metadata"}),
                "save_to_db": ("BOOLEAN", 
                    {"default": False, "tooltip": "Save metadata to database"}),
                
                # SVG-specific options
                "svg_optimize": ("BOOLEAN", 
                    {"default": False, "tooltip": "Basic SVG optimization (remove unnecessary whitespace)"}),
                "svg_embed_fonts": ("BOOLEAN", 
                    {"default": False, "tooltip": "Attempt to embed font information as metadata"}),
                
                # Advanced SVG options (similar to main save node)
                "color_profile": (["sRGB v4 Appearance", "sRGB v4 Preference", "sRGB v4 Display Class", "Adobe RGB", "ProPhoto RGB", "None"], 
                    {"default": "sRGB v4 Appearance", "tooltip": "Color profile to embed as metadata (for reference when converting SVG)"}),
                "bit_depth": (["8-bit", "16-bit"], 
                    {"default": "8-bit", "tooltip": "Bit depth for metadata reference (actual SVG is vector format)"}),
                
                # Debug options
                "debug_logging": ("BOOLEAN", 
                    {"default": False, "tooltip": "Enable detailed debug logging"}),
            },
            # Hidden parameters for ComfyUI workflow data (CRITICAL for workflow embedding)
            "hidden": {
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save_svg_with_metadata"
    CATEGORY = "image/save"
    OUTPUT_NODE = True

    def __init__(self):
        """Initialize the SVG save node with metadata services"""
        # Set up output directory
        self.output_dir = folder_paths.get_output_directory()
        self.temp_dir = folder_paths.get_temp_directory()
        
        # Initialize metadata services (same as main save node)
        self.metadata_service = MetadataService()
        self.workflow_parser = WorkflowParser()
        self.workflow_extractor = WorkflowExtractor()
        self.workflow_processor = WorkflowMetadataProcessor()
        
        # Debug mode
        self.debug = False

    def resolve_output_path(self, **kwargs):
        """
        Resolve the output path based on user settings
        (Simplified version of the main save node's path resolution)
        """
        filename_prefix = kwargs.get("filename_prefix", "svg_output")
        custom_dir = kwargs.get("custom_output_directory", "").strip()
        path_mode = kwargs.get("output_path_mode", "Subfolder in Output")
        include_project = kwargs.get("include_project", False)
        project = kwargs.get("project", "").strip()
        
        # Base output directory
        base_output_dir = self.output_dir
        
        # Determine final output directory
        if custom_dir:
            if path_mode == "Absolute Path" and os.path.isabs(custom_dir):
                output_dir = custom_dir
                subfolder = ""
            else:
                # Treat as subfolder
                output_dir = os.path.join(base_output_dir, custom_dir)
                subfolder = custom_dir
        else:
            output_dir = base_output_dir
            subfolder = ""
        
        # Add project to filename if requested
        if include_project and project:
            filename_prefix = f"{project}_{filename_prefix}"
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        return {
            "output_dir": output_dir,
            "filename_prefix": filename_prefix,
            "subfolder": subfolder,
            "base_output_dir": base_output_dir
        }

    def generate_filename(self, prefix, path_info, include_datetime=True, filename_format="Default (padded zeros)"):
        """Generate a unique filename for the SVG file"""
        timestamp = ""
        if include_datetime:
            now = datetime.datetime.now()
            timestamp = f"_{now.strftime('%Y%m%d_%H%M%S')}"
        
        output_dir = path_info["output_dir"]
        
        # Find next available filename
        counter = 1
        while True:
            if filename_format == "Simple (file1.svg)":
                if counter == 1 and not include_datetime:
                    filename = f"{prefix}.svg"
                else:
                    filename = f"{prefix}{timestamp}_{counter}.svg"
            else:  # Default with padded zeros
                if counter == 1 and not include_datetime:
                    filename = f"{prefix}.svg"
                else:
                    filename = f"{prefix}{timestamp}_{counter:05d}.svg"
            
            full_path = os.path.join(output_dir, filename)
            if not os.path.exists(full_path):
                return filename, full_path
            
            counter += 1
            if counter > 99999:
                # Fallback with timestamp
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{prefix}_{unique_id}.svg"
                full_path = os.path.join(output_dir, filename)
                return filename, full_path

    def create_metadata_dict(self, **kwargs):
        """Create metadata dictionary from input parameters"""
        metadata = {}
        
        # Basic Dublin Core metadata
        if kwargs.get("title"):
            metadata["title"] = kwargs["title"]
        if kwargs.get("description"):
            metadata["description"] = kwargs["description"]
        if kwargs.get("creator"):
            metadata["creator"] = kwargs["creator"]
        if kwargs.get("copyright"):
            metadata["rights"] = kwargs["copyright"]
        if kwargs.get("keywords"):
            # Split keywords and clean them
            keywords = [k.strip() for k in kwargs["keywords"].split(",") if k.strip()]
            if keywords:
                metadata["subject"] = keywords
        if kwargs.get("project"):
            metadata["project"] = kwargs["project"]
        
        # Custom metadata
        custom_meta_str = kwargs.get("custom_metadata", "{}")
        if custom_meta_str.strip():
            try:
                custom_meta = json.loads(custom_meta_str)
                if isinstance(custom_meta, dict):
                    metadata.update(custom_meta)
            except json.JSONDecodeError as e:
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Error parsing custom metadata: {e}")
        
        # Add technical metadata
        metadata["format"] = "image/svg+xml"
        metadata["created"] = datetime.datetime.now().isoformat()
        metadata["generator"] = "ComfyUI - EricSaveTrueSVGImage"
        
        return metadata

    def optimize_svg(self, svg_content):
        """Basic SVG optimization"""
        if not svg_content:
            return svg_content
        
        # Remove excessive whitespace between tags
        svg_content = re.sub(r'>\s+<', '><', svg_content)
        
        # Remove empty lines
        lines = svg_content.split('\n')
        lines = [line for line in lines if line.strip()]
        
        return '\n'.join(lines)

    def add_metadata_to_svg(self, svg_content, metadata, workflow_info=None):
        """
        Add comprehensive metadata to SVG content
        """
        if not svg_content or not metadata:
            return svg_content
        
        try:
            # Register namespaces
            ET.register_namespace('', "http://www.w3.org/2000/svg")
            ET.register_namespace('xlink', "http://www.w3.org/1999/xlink")
            
            # Parse SVG
            root = ET.fromstring(svg_content)
            
            # Ensure SVG namespace
            if not root.tag.endswith('}svg'):
                # Add namespace if missing
                root.tag = '{http://www.w3.org/2000/svg}svg'
                root.set('xmlns', 'http://www.w3.org/2000/svg')
            
            # Add or update metadata element
            metadata_elem = root.find('.//{http://www.w3.org/2000/svg}metadata')
            if metadata_elem is None:
                # Insert metadata as first child
                metadata_elem = ET.Element('{http://www.w3.org/2000/svg}metadata')
                root.insert(0, metadata_elem)
            else:
                # Clear existing metadata
                metadata_elem.clear()
            
            # Add Dublin Core metadata
            if metadata.get("title"):
                title_elem = ET.SubElement(metadata_elem, 'dc:title')
                title_elem.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
                title_elem.text = metadata["title"]
            
            if metadata.get("description"):
                desc_elem = ET.SubElement(metadata_elem, 'dc:description')
                desc_elem.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
                desc_elem.text = metadata["description"]
            
            if metadata.get("creator"):
                creator_elem = ET.SubElement(metadata_elem, 'dc:creator')
                creator_elem.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
                creator_elem.text = metadata["creator"]
            
            if metadata.get("rights"):
                rights_elem = ET.SubElement(metadata_elem, 'dc:rights')
                rights_elem.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
                rights_elem.text = metadata["rights"]
            
            if metadata.get("subject"):
                for keyword in metadata["subject"]:
                    subject_elem = ET.SubElement(metadata_elem, 'dc:subject')
                    subject_elem.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
                    subject_elem.text = keyword
            
            # Add technical metadata
            tech_group = ET.SubElement(metadata_elem, 'technical_info')
            for key, value in metadata.items():
                if key not in ["title", "description", "creator", "rights", "subject"]:
                    if isinstance(value, (str, int, float)):
                        tech_elem = ET.SubElement(tech_group, key.replace(" ", "_"))
                        tech_elem.text = str(value)
            
            # Add workflow information if provided
            if workflow_info:
                workflow_group = ET.SubElement(metadata_elem, 'workflow_info')
                workflow_elem = ET.SubElement(workflow_group, 'workflow_data')
                workflow_elem.text = json.dumps(workflow_info, indent=2)
            
            # Convert back to string
            ET.indent(root, space="  ")
            updated_svg = ET.tostring(root, encoding='unicode', method='xml')
            
            # Fix the XML declaration if needed
            if not updated_svg.startswith('<?xml'):
                updated_svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + updated_svg
            
            return updated_svg
            
        except Exception as e:
            if self.debug:
                print(f"[EricSaveTrueSVGImage] Error adding metadata to SVG: {e}")
            return svg_content

    def prepare_workflow_info(self, prompt, extra_pnginfo, embed_workflow):
        """Prepare workflow information for embedding (following main save node pattern)"""
        if not embed_workflow:
            return None
        
        try:
            workflow_data = None
            
            # First check if we have the workflow in a format that already works
            if extra_pnginfo and "workflow" in extra_pnginfo:
                # Use the workflow directly - it should already have the right structure
                workflow_data = extra_pnginfo["workflow"]
                
                # Ensure it has a version field
                if "version" not in workflow_data:
                    workflow_data["version"] = 0.4
                    
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Found workflow in extra_pnginfo with {len(workflow_data.get('nodes', []))} nodes")
                    
            # Otherwise, try to extract from the prompt
            elif prompt is not None:
                # If prompt itself IS the workflow (common case)
                if isinstance(prompt, dict) and "nodes" in prompt:
                    workflow_data = prompt
                    
                    # Ensure it has a version field
                    if "version" not in workflow_data:
                        workflow_data["version"] = 0.4
                        
                    if self.debug:
                        print(f"[EricSaveTrueSVGImage] Found workflow in prompt with {len(workflow_data.get('nodes', []))} nodes")
                
                # If prompt has the complete structure with version at top level
                elif isinstance(prompt, dict) and "version" in prompt:
                    workflow_data = prompt
                    
                    if self.debug:
                        print(f"[EricSaveTrueSVGImage] Found versioned workflow data in prompt")
            
            # If we found a proper workflow structure, return it directly
            if workflow_data:
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Successfully prepared workflow data with version {workflow_data.get('version', 'unknown')}")
                return workflow_data
            else:
                # Fallback: Create basic workflow info with whatever we have
                workflow_info = {
                    "created": datetime.datetime.now().isoformat(),
                    "node_id": "EricSaveTrueSVGImage",
                    "version": "1.0.0",
                    "note": "No ComfyUI workflow data available"
                }
                
                # Include raw data if available for debugging
                if prompt:
                    workflow_info["raw_prompt"] = self._ensure_serializable(prompt)
                if extra_pnginfo:
                    workflow_info["raw_extra_pnginfo"] = self._ensure_serializable(extra_pnginfo)
                
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] No proper workflow found, created fallback metadata")
                    
                return workflow_info
                
        except Exception as e:
            if self.debug:
                print(f"[EricSaveTrueSVGImage] Error preparing workflow info: {str(e)}")
            # Return basic error info
            return {
                "created": datetime.datetime.now().isoformat(),
                "node_id": "EricSaveTrueSVGImage",
                "version": "1.0.0",
                "error": f"Failed to process workflow data: {str(e)}"
            }

    def _save_workflow_json(self, json_path, prompt=None, extra_pnginfo=None):
        """Save workflow data as JSON file (following main save node pattern)"""
        try:
            workflow_data = None
            
            # First check if we have the workflow in a format that already works
            if extra_pnginfo and "workflow" in extra_pnginfo:
                # Use the workflow directly - it should already have the right structure
                workflow_data = extra_pnginfo["workflow"]
                
                # Ensure it has a version field
                if "version" not in workflow_data:
                    workflow_data["version"] = 0.4
            # Otherwise, try to extract from the prompt
            elif prompt is not None:
                # If prompt itself IS the workflow (common case)
                if isinstance(prompt, dict) and "nodes" in prompt:
                    workflow_data = prompt
                    
                    # Ensure it has a version field
                    if "version" not in workflow_data:
                        workflow_data["version"] = 0.4
                
                # If prompt has the complete structure with version at top level
                elif isinstance(prompt, dict) and "version" in prompt:
                    workflow_data = prompt
            
            # If we found a proper workflow structure, save it directly
            if workflow_data:
                # Write JSON file
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                print(f"[EricSaveTrueSVGImage] Saved loadable workflow as JSON: {json_path}")
            else:
                # Fallback: Save the prompt directly for reference
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(prompt, f, indent=2, ensure_ascii=False)
                print(f"[EricSaveTrueSVGImage] Saved prompt data as JSON (may not be loadable)")
        except Exception as e:
            print(f"[EricSaveTrueSVGImage] Error saving workflow as JSON: {str(e)}")

    def _save_xmp_sidecar(self, xmp_path, metadata, workflow_info=None):
        """Save XMP sidecar file with metadata"""
        try:
            # Create XMP content
            xmp_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/"
        xmlns:comfy="http://comfyui.org/xmp/1.0/">
'''
            
            # Add Dublin Core metadata
            if metadata.get("title"):
                xmp_content += f'      dc:title="{self._escape_xml(metadata["title"])}"\n'
            if metadata.get("description"):
                xmp_content += f'      dc:description="{self._escape_xml(metadata["description"])}"\n'
            if metadata.get("creator"):
                xmp_content += f'      dc:creator="{self._escape_xml(metadata["creator"])}"\n'
            if metadata.get("rights"):
                xmp_content += f'      dc:rights="{self._escape_xml(metadata["rights"])}"\n'
            if metadata.get("subject"):
                keywords = ", ".join(metadata["subject"])
                xmp_content += f'      dc:subject="{self._escape_xml(keywords)}"\n'
            
            # Add XMP metadata
            if metadata.get("created"):
                xmp_content += f'      xmp:CreateDate="{metadata["created"]}"\n'
            if metadata.get("generator"):
                xmp_content += f'      xmp:CreatorTool="{self._escape_xml(metadata["generator"])}"\n'
            
            # Add ComfyUI-specific metadata
            if workflow_info:
                workflow_json = json.dumps(workflow_info, separators=(',', ':'))
                workflow_json_escaped = self._escape_xml(workflow_json)
                xmp_content += f'      comfy:workflow="{workflow_json_escaped}"\n'
            
            xmp_content += '''    />
  </rdf:RDF>
</x:xmpmeta>'''
            
            # Write XMP file
            with open(xmp_path, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
            
            if self.debug:
                print(f"[EricSaveTrueSVGImage] Saved XMP sidecar: {xmp_path}")
                
        except Exception as e:
            print(f"[EricSaveTrueSVGImage] Error saving XMP sidecar: {str(e)}")

    def _escape_xml(self, text):
        """Escape XML special characters"""
        if not isinstance(text, str):
            text = str(text)
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

    def _ensure_serializable(self, obj):
        """Fallback method to ensure object is JSON serializable"""
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Try to convert common non-serializable types
            if hasattr(obj, '__dict__'):
                return str(obj)
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
            else:
                return str(obj)

    def save_svg_with_metadata(self, svg_content, filename_prefix="wordcloud_svg", prompt=None, extra_pnginfo=None, unique_id=None, **kwargs):
        """
        Main function to save SVG content with embedded metadata
        """
        # Set debug mode
        self.debug = kwargs.get("debug_logging", False)
        
        if self.debug:
            print(f"[EricSaveTrueSVGImage] Starting SVG save process")
            print(f"[EricSaveTrueSVGImage] SVG content length: {len(svg_content) if svg_content else 0} characters")
        
        # Check if we have SVG content
        if not svg_content or not svg_content.strip():
            error_msg = "No SVG content provided"
            print(f"[EricSaveTrueSVGImage] Error: {error_msg}")
            return (error_msg,)
        
        try:
            # Resolve output path
            path_info = self.resolve_output_path(**kwargs)
            
            # Generate filename
            filename, full_path = self.generate_filename(
                filename_prefix, 
                path_info,
                kwargs.get("include_datetime", True),
                kwargs.get("filename_format", "Default (padded zeros)")
            )
            
            # Create metadata if enabled
            metadata = None
            workflow_info = None
            
            if kwargs.get("enable_metadata", True):
                metadata = self.create_metadata_dict(**kwargs)
                
                # Always prepare workflow info for JSON/XMP export (not for SVG embedding)
                workflow_info = self.prepare_workflow_info(prompt, extra_pnginfo, True)
            
            # Process SVG content
            processed_svg = svg_content
            
            # Optimize if requested
            if kwargs.get("svg_optimize", False):
                processed_svg = self.optimize_svg(processed_svg)
            
            # Add metadata to SVG (but not workflow - that goes in separate files)
            if kwargs.get("save_embedded", True) and metadata:
                processed_svg = self.add_metadata_to_svg(processed_svg, metadata, None)
            
            # Save the SVG file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(processed_svg)
            
            if self.debug:
                print(f"[EricSaveTrueSVGImage] Saved SVG file: {full_path}")
            
            # Save additional files if requested
            base_path = os.path.splitext(full_path)[0]
            
            # Save workflow as JSON (default enabled for ComfyUI compatibility)
            if kwargs.get("save_workflow_as_json", True):
                json_path = f"{base_path}_workflow.json"
                self._save_workflow_json(json_path, prompt, extra_pnginfo)
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Saved workflow JSON: {json_path}")
            
            # Save XMP sidecar if requested
            if kwargs.get("save_xmp", False) and metadata:
                xmp_path = f"{base_path}.xmp"
                self._save_xmp_sidecar(xmp_path, metadata, workflow_info)
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Saved XMP sidecar: {xmp_path}")
            
            # Save workflow as text
            if kwargs.get("save_workflow_as_txt", False) and workflow_info:
                txt_path = f"{base_path}_workflow.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"SVG Generation Workflow\n")
                    f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"File: {filename}\n\n")
                    
                    if metadata:
                        f.write("Metadata:\n")
                        for key, value in metadata.items():
                            f.write(f"  {key}: {value}\n")
                        f.write("\n")
                    
                    f.write("Workflow Data:\n")
                    f.write(json.dumps(workflow_info, indent=2))
                
                if self.debug:
                    print(f"[EricSaveTrueSVGImage] Saved workflow text: {txt_path}")
            
            # Save to database if requested
            if kwargs.get("save_to_db", False):
                try:
                    # Use the metadata service to save to database
                    db_metadata = {
                        "file_path": full_path,
                        "filename": filename,
                        "format": "svg",
                        "metadata": metadata,
                        "workflow": workflow_info
                    }
                    self.metadata_service.save_metadata(db_metadata)
                    if self.debug:
                        print(f"[EricSaveTrueSVGImage] Saved metadata to database")
                except Exception as e:
                    print(f"[EricSaveTrueSVGImage] Error saving to database: {e}")
            
            print(f"[EricSaveTrueSVGImage] Successfully saved: {full_path}")
            return (full_path,)
            
        except Exception as e:
            error_msg = f"Error saving SVG: {str(e)}"
            print(f"[EricSaveTrueSVGImage] {error_msg}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return (error_msg,)


# Registration for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EricSaveTrueSVGImage": EricSaveTrueSVGImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EricSaveTrueSVGImage": "Eric Save True SVG Image (with Metadata)"
}
