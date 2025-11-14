"""
PNG Info Diagnostic Node V3

Enhanced version of the PNG Info Diagnostic node that works with the new MetadataService
and properly detects various metadata formats and workflows.

Features:
- Supports standard and split workflows
- Improved metadata parsing with the unified MetadataService
- Better error handling
- Enhanced visualization options
- Proper resource management
"""

import os
import json
import base64
import re
import io
from PIL import Image, PngImagePlugin
from typing import Dict, Any, List, Tuple, Optional, Union

# Import the metadata service from the package
from custom_nodes.AAA_Metadata_System import MetadataService

class PngInfoDiagnosticNode_V3:
    """Enhanced PNG Info diagnostic node for examining metadata in PNG files"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_filepath": ("STRING", {"default": ""}),
                "output_mode": (["summary", "full_text", "raw_info", "structured_json"], {"default": "summary"}),
                "include_workflow": ("BOOLEAN", {"default": True}),
                "include_sidecar": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "debug_logging": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "DICT")
    RETURN_NAMES = ("info", "filename", "metadata")
    FUNCTION = "diagnose_png"
    CATEGORY = "Eric's Nodes/Tools"
    
    def __init__(self):
        """Initialize with metadata service"""
        self.metadata_service = MetadataService(debug=True)

    def diagnose_png(self, input_filepath: str, output_mode: str = "summary", 
                    include_workflow: bool = True, include_sidecar: bool = True,
                    debug_logging: bool = False) -> Tuple[str, str, Dict]:
        """
        Extract and display metadata information from a PNG file
        
        Args:
            input_filepath: Path to PNG file to analyze
            output_mode: Level of detail for output (summary, full_text, raw_info, structured_json)
            include_workflow: Whether to include workflow data
            include_sidecar: Whether to check for XMP sidecar
            debug_logging: Whether to enable debug logging
            
        Returns:
            Tuple of (info_text, filename, metadata_dict)
        """
        try:
            # Enable debug logging if requested
            if debug_logging:
                self.metadata_service.debug = True
                print(f"[PngInfoDiagnostic] Analyzing: {input_filepath}")
            
            # Validate input
            if not input_filepath or not os.path.exists(input_filepath):
                return ("No valid file provided", "", {})
                
            if not input_filepath.lower().endswith('.png'):
                return (f"File is not a PNG: {input_filepath}", os.path.basename(input_filepath), {})
            
            # Print file size and path
            file_size = os.path.getsize(input_filepath)
            file_name = os.path.basename(input_filepath)
            info_lines = [
                f"File: {file_name}",
                f"Path: {os.path.dirname(os.path.abspath(input_filepath))}",
                f"Size: {self._format_size(file_size)}"
            ]
            
            # Extract metadata
            metadata = {}
            
            # Process PNG chunks
            chunk_info = self._extract_png_chunks(input_filepath)
            if chunk_info:
                info_lines.append("\n== PNG Chunks ==")
                info_lines.append(f"Total chunks: {len(chunk_info['chunks'])}")
                
                for chunk in chunk_info['chunks']:
                    # Add basic chunk info
                    if output_mode in ["full_text", "raw_info"]:
                        info_lines.append(f"{chunk['type']}: {self._format_size(chunk['size'])}")
                    
                    # Store metadata
                    metadata["chunks"] = chunk_info
            
            # Extract text metadata (parameters)
            text_metadata = self._extract_text_metadata(input_filepath)
            if text_metadata:
                info_lines.append("\n== Text Metadata ==")
                
                # Report available fields
                fields = list(text_metadata.keys())
                info_lines.append(f"Available fields: {', '.join(fields)}")
                
                # Add details based on output mode
                if output_mode in ["full_text", "raw_info"]:
                    for field, value in text_metadata.items():
                        if field == "workflow" and not include_workflow:
                            continue
                            
                        # Summarize long values
                        if isinstance(value, str) and len(value) > 100:
                            info_lines.append(f"{field}: {len(value)} characters")
                        else:
                            info_lines.append(f"{field}: {value}")
                            
                # Store metadata
                metadata["text"] = text_metadata
            
            # Extract embedded metadata using the new service
            # Set proper resource identifier
            filename = os.path.basename(input_filepath)
            resource_uri = f"file:///{filename}"
            self.metadata_service.set_resource_identifier(resource_uri)
            
            # Read embedded metadata (from image)
            embedded_metadata = self.metadata_service.read_metadata(input_filepath, source='embedded')
            if embedded_metadata:
                info_lines.append("\n== Embedded Metadata ==")
                
                # Report available sections
                sections = list(embedded_metadata.keys())
                info_lines.append(f"Available sections: {', '.join(sections)}")
                
                # Add details based on output mode
                if output_mode in ["full_text", "raw_info"]:
                    for section, data in embedded_metadata.items():
                        info_lines.append(f"\n{section}:")
                        if isinstance(data, dict):
                            for key, value in data.items():
                                summary = self._summarize_value(value)
                                info_lines.append(f"  {key}: {summary}")
                        else:
                            info_lines.append(f"  {self._summarize_value(data)}")
                
                # Store metadata
                metadata["embedded"] = embedded_metadata
            
            # Check for XMP sidecar if requested
            if include_sidecar:
                # Read from XMP sidecar using the service
                sidecar_metadata = self.metadata_service.read_metadata(input_filepath, source='xmp')
                if sidecar_metadata:
                    info_lines.append("\n== XMP Sidecar ==")
                    
                    # Report available sections
                    sections = list(sidecar_metadata.keys())
                    info_lines.append(f"Available sections: {', '.join(sections)}")
                    
                    # Add details based on output mode
                    if output_mode in ["full_text", "raw_info"]:
                        for section, data in sidecar_metadata.items():
                            info_lines.append(f"\n{section}:")
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    summary = self._summarize_value(value)
                                    info_lines.append(f"  {key}: {summary}")
                            else:
                                info_lines.append(f"  {self._summarize_value(data)}")
                    
                    # Store metadata
                    metadata["sidecar"] = sidecar_metadata
                    
                    # Check for split workflow
                    if include_workflow and "ai_info" in sidecar_metadata and "workflow" in sidecar_metadata["ai_info"]:
                        info_lines.append("\nDetected split workflow in XMP sidecar")
                else:
                    info_lines.append("\nNo XMP sidecar found")
            
            # Check for workflow in PNG text
            if include_workflow and "workflow" in text_metadata:
                workflow_data = self._extract_workflow(text_metadata["workflow"])
                if workflow_data:
                    # Format workflow summary based on output mode
                    if output_mode in ["summary"]:
                        workflow_summary = self._summarize_workflow(workflow_data)
                        info_lines.append("\n== Workflow Summary ==")
                        info_lines.extend(workflow_summary)
                    elif output_mode in ["full_text", "raw_info"]:
                        info_lines.append(f"\n== Workflow Data ({len(text_metadata['workflow'])} bytes) ==")
                        if output_mode == "raw_info":
                            # Limit workflow output in raw_info mode
                            info_lines.append("Workflow data available (not shown in raw_info mode)")
                        else:
                            # Show formatted workflow in full_text mode
                            formatted_workflow = json.dumps(workflow_data, indent=2)
                            if len(formatted_workflow) > 1000:
                                info_lines.append(formatted_workflow[:1000] + "...(truncated)")
                            else:
                                info_lines.append(formatted_workflow)
                    
                    metadata["workflow"] = workflow_data
            
            # Final output formatting
            if output_mode == "structured_json":
                # Return structured JSON instead of text
                return (json.dumps(metadata, indent=2), file_name, metadata)
            else:
                return ("\n".join(info_lines), file_name, metadata)
                
        except Exception as e:
            import traceback
            error_text = f"Error analyzing file: {str(e)}\n{traceback.format_exc()}"
            print(f"[PngInfoDiagnostic] ERROR: {error_text}")
            return (error_text, os.path.basename(input_filepath) if input_filepath else "", {})
        finally:
            # Ensure cleanup always happens
            self.cleanup()

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

    def _summarize_value(self, value: Any) -> str:
        """Create a summary of a value based on its type/length"""
        if value is None:
            return "None"
            
        if isinstance(value, dict):
            return f"{{...}} ({len(value)} items)"
            
        if isinstance(value, list):
            return f"[...] ({len(value)} items)"
            
        if isinstance(value, str):
            if len(value) > 100:
                return f"{value[:97]}... ({len(value)} chars)"
            return value
            
        return str(value)

    def _extract_png_chunks(self, filepath: str) -> Dict:
        """Extract and analyze PNG chunks"""
        try:
            chunks = []
            
            with open(filepath, 'rb') as file:
                # Skip PNG header (8 bytes)
                file.read(8)
                
                # Read chunks
                while True:
                    try:
                        # Read chunk length (4 bytes)
                        length_bytes = file.read(4)
                        if not length_bytes or len(length_bytes) < 4:
                            break
                            
                        # Convert to integer
                        length = int.from_bytes(length_bytes, byteorder='big')
                        
                        # Read chunk type (4 bytes)
                        chunk_type = file.read(4)
                        if not chunk_type or len(chunk_type) < 4:
                            break
                            
                        # Convert to string
                        chunk_type_str = chunk_type.decode('ascii', errors='replace')
                        
                        # Skip chunk data and CRC
                        file.seek(length + 4, 1)  # current position + length + 4 byte CRC
                        
                        # Add chunk info
                        chunks.append({
                            'type': chunk_type_str,
                            'size': length
                        })
                        
                        # Check for IEND chunk
                        if chunk_type_str == 'IEND':
                            break
                    except Exception as e:
                        # Skip to next chunk on error
                        break
                        
            return {'chunks': chunks}
            
        except Exception as e:
            print(f"[PngInfoDiagnostic] Error extracting PNG chunks: {str(e)}")
            return {}

    def _extract_text_metadata(self, filepath: str) -> Dict:
        """Extract text metadata from PNG"""
        try:
            with Image.open(filepath) as img:
                # Get text chunks
                metadata = {}
                if 'parameters' in img.info:
                    metadata['parameters'] = img.info['parameters']
                    
                # Look for workflow
                if 'workflow' in img.info:
                    metadata['workflow'] = img.info['workflow']
                elif 'prompt' in img.info:
                    metadata['workflow'] = img.info['prompt']
                    
                # Add other text fields
                for key, value in img.info.items():
                    if isinstance(value, str) and key not in metadata:
                        metadata[key] = value
                        
                return metadata
                
        except Exception as e:
            print(f"[PngInfoDiagnostic] Error extracting text metadata: {str(e)}")
            return {}

    def _extract_workflow(self, workflow_data: str) -> Dict:
        """Extract workflow from string data"""
        try:
            # If already a dict, return as is
            if isinstance(workflow_data, dict):
                return workflow_data
            
            # Try parsing as JSON
            if isinstance(workflow_data, str):
                try:
                    return json.loads(workflow_data)
                except:
                    pass
                    
            # Try base64 decode
            try:
                decoded = base64.b64decode(workflow_data).decode('utf-8')
                return json.loads(decoded)
            except:
                pass
                
            return {}
                
        except Exception as e:
            print(f"[PngInfoDiagnostic] Error extracting workflow: {str(e)}")
            return {}

    def _summarize_workflow(self, workflow_data: Dict) -> List[str]:
        """Create a summary of workflow data"""
        summary = []
        
        # Check if it's a ComfyUI workflow
        if 'prompt' in workflow_data and isinstance(workflow_data['prompt'], dict):
            prompt = workflow_data['prompt']
            
            # Count nodes by type
            nodes = prompt.get('nodes', {})
            summary.append(f"Total nodes: {len(nodes)}")
            
            # Count node types
            node_types = {}
            for node in nodes.values():
                node_type = node.get('class_type', 'Unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
                
            summary.append("\nNode types:")
            for node_type, count in node_types.items():
                summary.append(f"- {node_type}: {count}")
                
            # Find key nodes
            summary.append("\nKey components:")
            
            # Models
            checkpoints = [node.get('inputs', {}).get('ckpt_name') 
                          for node in nodes.values() 
                          if 'Checkpoint' in node.get('class_type', '') 
                          and 'ckpt_name' in node.get('inputs', {})]
            if checkpoints:
                summary.append(f"- Model(s): {', '.join(checkpoints)}")
            
            # VAE
            vaes = [node.get('inputs', {}).get('vae_name') 
                   for node in nodes.values() 
                   if 'VAE' in node.get('class_type', '') 
                   and 'vae_name' in node.get('inputs', {})]
            if vaes:
                summary.append(f"- VAE(s): {', '.join(vaes)}")
            
            # Samplers
            samplers = []
            for node in nodes.values():
                if 'KSampler' in node.get('class_type', ''):
                    inputs = node.get('inputs', {})
                    if 'sampler_name' in inputs:
                        sampler = (
                            f"{inputs.get('sampler_name')}"
                            f" ({inputs.get('steps', '?')} steps,"
                            f" cfg {inputs.get('cfg', '?')})"
                        )
                        samplers.append(sampler)
            if samplers:
                summary.append(f"- Sampler(s): {', '.join(samplers)}")
                
        # Check if it's an A1111 workflow
        elif all(k in workflow_data for k in ['prompt', 'negative_prompt']):
            summary.append("A1111/SD-WebUI Format")
            summary.append(f"Model: {workflow_data.get('model', 'Unknown')}")
            summary.append(f"Sampler: {workflow_data.get('sampler', '')} ({workflow_data.get('steps', '?')} steps)")
            
            # Add prompt summary
            prompt = workflow_data.get('prompt', '')
            negative = workflow_data.get('negative_prompt', '')
            
            if prompt:
                if len(prompt) > 100:
                    summary.append(f"Prompt: {prompt[:97]}... ({len(prompt)} chars)")
                else:
                    summary.append(f"Prompt: {prompt}")
            
            if negative:
                if len(negative) > 100:
                    summary.append(f"Negative: {negative[:97]}... ({len(negative)} chars)")
                else:
                    summary.append(f"Negative: {negative}")
                    
        # Generic workflow
        else:
            summary.append("Unknown workflow format")
            summary.append(f"Fields: {', '.join(workflow_data.keys())}")
            
        return summary

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'metadata_service'):
            self.metadata_service.cleanup()

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()

# Node registration
NODE_CLASS_MAPPINGS = {
    "PngInfoDiagnosticV3": PngInfoDiagnosticNode_V3
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PngInfoDiagnosticV3": "PNG Info Diagnostic V3"
}