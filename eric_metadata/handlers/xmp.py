"""
xmp.py
This module handles XMP sidecar files for metadata management.
Description: [Brief description of what this script does]
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

Note: If this script depends on ultralytics (YOLO), be aware that it uses the AGPL-3.0
license which has implications for code distribution and modification.
"""
# Metadata_system/src/eric_metadata/handlers/xmp.py
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import json
import re
import datetime

from ..handlers.base import BaseHandler
from ..utils.namespace import NamespaceManager
from ..utils.xml_tools import XMLTools
from ..utils.error_handling import ErrorRecovery

class XMPSidecarHandler(BaseHandler):
    """Handler for XMP sidecar files with MWG compliance"""
    
    def __init__(self, debug: bool = False):
        """
        Initialize the XMP sidecar handler
        
        Args:
            debug: Whether to enable debug logging
        """
        super().__init__(debug)
        
        # Register namespaces
        self.XMP_NS = NamespaceManager.NAMESPACES
        
        # Initialize resource identifier
        self.resource_about = ""
        
        # Register namespaces with ET
        for prefix, uri in self.XMP_NS.items():
            ET.register_namespace(prefix, uri)
            
        # Register with PyExiv2
        self._register_namespaces()
        
    def _register_namespaces(self) -> None:
        """Register namespaces with PyExiv2"""
        NamespaceManager.register_with_pyexiv2(self.debug)

    def _unwrap_namespace_wrappers(self, value: Any) -> Any:
        """Collapse intermediate namespace dictionaries created during parsing."""
        if isinstance(value, dict):
            if len(value) == 1:
                (sole_key, sole_value) = next(iter(value.items()))
                if sole_key in self.XMP_NS:
                    return self._unwrap_namespace_wrappers(sole_value)
            return {key: self._unwrap_namespace_wrappers(sub_value) for key, sub_value in value.items()}
        if isinstance(value, list):
            return [self._unwrap_namespace_wrappers(item) for item in value]
        return value

    @staticmethod
    def _normalize_lang_alt(value: Any) -> Any:
        """Reduce language alternative dictionaries to a single representative value."""
        if isinstance(value, dict):
            for candidate_key in ("x-default", 'lang="x-default"', 'default'):
                if candidate_key in value:
                    return value[candidate_key]
            if len(value) == 1:
                return next(iter(value.values()))
        return value

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase/TitleCase keys to snake_case for internal dictionaries."""
        import re

        if not name:
            return name
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @staticmethod
    def _coerce_numeric(value: Any) -> Any:
        """Try to coerce string numerics into int/float for cleaner metadata."""
        if isinstance(value, str):
            try:
                if value.strip().isdigit():
                    return int(value.strip())
                return float(value.strip())
            except ValueError:
                return value
        return value

    def _coerce_structure(self, value: Any) -> Any:
        """Recursively coerce numeric values within nested structures."""
        if isinstance(value, dict):
            return {key: self._coerce_structure(sub_value) for key, sub_value in value.items()}
        if isinstance(value, list):
            return [self._coerce_structure(item) for item in value]
        return self._coerce_numeric(value)
        
    def write_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to XMP sidecar file
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get sidecar path
            sidecar_path = self._get_sidecar_path(filepath)
            
            # Create or update XMP file
            if os.path.exists(sidecar_path):
                # Update existing XMP
                return self._update_sidecar(sidecar_path, metadata)
            else:
                # Create new XMP
                return self._create_sidecar(sidecar_path, metadata, filepath)
                
        except Exception as e:
            self.log(f"Error writing XMP sidecar: {str(e)}", level="ERROR", error=e)
            
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
        Read metadata from XMP sidecar file
        
        Args:
            filepath: Path to the original file
            
        Returns:
            dict: Metadata from XMP sidecar
        """
        try:
            # Get sidecar path
            sidecar_path = self._get_sidecar_path(filepath)
            
            # Check if sidecar exists
            if not os.path.exists(sidecar_path):
                return {}
                
            # Read XMP file
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                xmp_content = f.read()
                
            # Parse XMP (returns namespace-based structure)
            namespace_data = XMLTools.xmp_to_dict(xmp_content)
            
            # Map to section-based structure
            return self._map_namespaces_to_sections(namespace_data)
                
        except Exception as e:
            self.log(f"Error reading XMP sidecar: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_read_error(self, context)
            
    def _create_sidecar(self, sidecar_path: str, metadata: Dict[str, Any], 
                    original_filepath: str) -> bool:
        """
        Create a new XMP sidecar file
        
        Args:
            sidecar_path: Path to the XMP sidecar file
            metadata: Metadata to write
            original_filepath: Path to the original file
            
        Returns:
            bool: True if successful
        """
        # Get resource identifier
        resource_uri = self.resource_about
        if not resource_uri:
            # Create from filename if not provided
            filename = os.path.basename(original_filepath)
            resource_uri = f"file:///{filename}"
            
        # Create XMP structure
        root = self._create_xmp_base(resource_uri)
        
        # Get description element directly from the structure we just created
        # Instead of using find, we know the structure: root -> rdf[0] -> desc[0]
        rdf = root[0]  # First child of root should be RDF
        if len(rdf) == 0:
            self.log("RDF element has no children", level="ERROR")
            return False
            
        desc = rdf[0]  # First child of RDF should be Description
        
        # Add metadata
        self._add_metadata_to_description(desc, metadata)
        
        # Format XML with proper indentation
        XMLTools.indent_xml(root)
        
        # Write to file
        return self._write_xml_to_file(sidecar_path, root)

    def _update_sidecar(self, sidecar_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Update existing XMP sidecar file
        
        Args:
            sidecar_path: Path to the XMP sidecar file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # First, check if the file exists
            if not os.path.exists(sidecar_path):
                # If file doesn't exist, create a new one instead
                return self._create_sidecar(sidecar_path, metadata, os.path.splitext(sidecar_path)[0])
            
            # Read existing XMP as raw text
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                xmp_content = f.read()
            
            # Remove packet wrapper for parsing
            content = re.sub(r'<\?xpacket[^>]+\?>', '', xmp_content)
            content = re.sub(r'<\?xpacket end="[^"]+"\?>', '', content)
            
            # Parse XML with namespace awareness
            root = ET.fromstring(content.strip())
            
            # Find RDF and Description elements
            rdf_xpath = ".//{*}RDF"
            desc_xpath = ".//{*}Description"
            
            rdf = root.find(rdf_xpath)
            if rdf is None:
                self.log("Failed to find RDF element", level="ERROR")
                return False
                
            desc = rdf.find(desc_xpath)
            if desc is None:
                self.log("Failed to find Description element", level="ERROR")
                return False
            
            # Add metadata to existing Description
            self._add_metadata_to_description(desc, metadata)
            
            # Format XML with proper indentation
            XMLTools.indent_xml(root)
            
            # Write back to file
            return self._write_xml_to_file(sidecar_path, root)
            
        except Exception as e:
            self.log(f"XMP update failed: {str(e)}", level="ERROR", error=e)
            return False
    def _create_xmp_base(self, resource_uri: str) -> ET.Element:
        """
        Create base XMP structure using a string template
        
        Args:
            resource_uri: Resource identifier
            
        Returns:
            Element: Root element
        """
        # Register namespaces with ElementTree
        for prefix, uri in self.XMP_NS.items():
            ET.register_namespace(prefix, uri)
        
        # Create a basic XMP template
        xmlns_str = ' '.join([f'xmlns:{prefix}="{uri}"' for prefix, uri in self.XMP_NS.items()])
        template = f"""
        <x:xmpmeta {xmlns_str}>
        <rdf:RDF>
            <rdf:Description rdf:about="{resource_uri}">
            </rdf:Description>
        </rdf:RDF>
        </x:xmpmeta>
        """
        
        # Parse template
        root = ET.fromstring(template)
        
        # Debug logging
        if self.debug:
            self.log(f"Created XMP base using template", level="DEBUG")
            self.log(f"Root has {len(root)} children", level="DEBUG")
        
        return root

    def _write_xml_to_file(self, filepath: str, root: ET.Element) -> bool:
        """
        Write XML to file with proper encoding and packet wrapper
        
        Args:
            filepath: Path to write to
            root: Root XML element
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert to string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            
            # Add packet wrapper
            start_wrapper, end_wrapper = XMLTools.create_xmp_wrapper()
            xmp_content = f"{start_wrapper}{xml_str}{end_wrapper}"
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xmp_content)
                
            return True
            
        except Exception as e:
            self.log(f"XML write failed: {str(e)}", level="ERROR", error=e)
            return False
    def _add_metadata_to_description(self, desc: ET.Element, metadata: Dict[str, Any]) -> None:
        """
        Add metadata to Description element
        
        Args:
            desc: Description element
            metadata: Metadata to add
        """
        # Add basic metadata
        if 'basic' in metadata:
            self._add_basic_metadata(desc, metadata['basic'])
            
        # Add analysis data
        if 'analysis' in metadata:
            self._add_analysis_metadata(desc, metadata['analysis'])
            
        # Add AI info
        if 'ai_info' in metadata:
            self._add_ai_metadata(desc, metadata['ai_info'])
            
        # Add regions
        if 'regions' in metadata:
            self._add_region_metadata(desc, metadata['regions'])

        # Standard namespace sections
        if 'dc' in metadata:
            self._add_structured_namespace(desc, 'dc', metadata['dc'])
        if 'photoshop' in metadata:
            self._add_structured_namespace(desc, 'photoshop', metadata['photoshop'])
        if 'xmp' in metadata:
            self._add_structured_namespace(desc, 'xmp', metadata['xmp'])
        if 'xmpRights' in metadata:
            self._add_structured_namespace(desc, 'xmpRights', metadata['xmpRights'])
        if 'xmpMM' in metadata:
            self._add_structured_namespace(desc, 'xmpMM', metadata['xmpMM'])
        if 'Iptc4xmpCore' in metadata:
            self._add_structured_namespace(desc, 'Iptc4xmpCore', metadata['Iptc4xmpCore'])
        if 'ai' in metadata:
            self._add_structured_namespace(desc, 'ai', metadata['ai'])
            
        # Handle other sections generically
        handled_sections = {
            'basic',
            'analysis',
            'ai_info',
            'regions',
            'dc',
            'photoshop',
            'xmp',
            'xmpRights',
            'xmpMM',
            'Iptc4xmpCore',
            'ai',
        }
        for section_name, section_data in metadata.items():
            if section_name not in handled_sections and section_data:
                # Determine namespace based on section name
                namespace = self._get_namespace_for_section(section_name)
                self._add_generic_section(desc, section_name, section_data, namespace)
    
    def _get_namespace_for_section(self, section_name: str) -> str:
        """
        Get the appropriate namespace for a metadata section
        
        Args:
            section_name: Name of the metadata section
            
        Returns:
            str: Namespace to use
        """
        # Map section names to namespaces
        namespace_mapping = {
            'photoshop': 'xmp',  # Photoshop metadata goes to XMP namespace
            'ai': 'ai',          # AI metadata goes to AI namespace  
            'workflow': 'ai',    # Workflow data goes to AI namespace
            'technical': 'eiqa', # Technical analysis goes to EIQA
            'aesthetic': 'eiqa', # Aesthetic analysis goes to EIQA
        }
        
        return namespace_mapping.get(section_name, 'xmp')  # Default to XMP namespace
    
    def _add_generic_section(self, desc: ET.Element, section_name: str, 
                           section_data: Dict[str, Any], namespace: str) -> None:
        """
        Add a generic metadata section
        
        Args:
            desc: Description element
            section_name: Name of the section
            section_data: Section data
            namespace: Namespace to use
        """
        try:
            if self.debug:
                self.log(f"Adding generic section '{section_name}' with namespace '{namespace}'", level="DEBUG")
                self.log(f"Section data type: {type(section_data)}, content: {section_data}", level="DEBUG")
                self.log(f"Available namespaces: {list(self.XMP_NS.keys())}", level="DEBUG")
                
            # Validate namespace exists
            if namespace not in self.XMP_NS:
                self.log(f"Warning: namespace '{namespace}' not found, using 'xmp'", level="WARNING")
                namespace = 'xmp'
                
            # Create section element
            try:
                section_elem = ET.SubElement(desc, f'{{{self.XMP_NS[namespace]}}}{section_name}')
                if self.debug:
                    self.log(f"Created section element for '{section_name}' in namespace '{namespace}'", level="DEBUG")
            except Exception as elem_e:
                self.log(f"Failed to create section element: {elem_e}", level="ERROR")
                raise
            
            # Handle the data based on its structure
            if isinstance(section_data, dict):
                # Create description container for complex data
                try:
                    section_desc = ET.SubElement(section_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                    self._add_generic_data(section_desc, section_data, namespace)
                    if self.debug:
                        self.log(f"Added dict data for section '{section_name}'", level="DEBUG")
                except Exception as dict_e:
                    self.log(f"Failed to add dict data: {dict_e}", level="ERROR")
                    raise
            elif isinstance(section_data, (list, set, tuple)):
                # Create bag/seq for list data
                container_type = 'Bag'  # Default to Bag
                XMLTools.add_list_to_container(section_elem, container_type, list(section_data), self.XMP_NS)
                if self.debug:
                    self.log(f"Added list data for section '{section_name}'", level="DEBUG")
            else:
                # Simple value
                section_elem.text = str(section_data)
                if self.debug:
                    self.log(f"Added simple value for section '{section_name}': {section_data}", level="DEBUG")
        except Exception as e:
            self.log(f"Error adding generic section '{section_name}': {str(e)} (type: {type(e).__name__})", level="ERROR", error=e)
            # Continue processing other sections

    def _add_basic_metadata(self, desc: ET.Element, basic_data: Dict[str, Any]) -> None:
        """
        Add basic metadata to Description element
        
        Args:
            desc: Description element
            basic_data: Basic metadata
        """
        # Title with language alternative
        if 'title' in basic_data:
            # Extract text if it's already a language map dict (from previous read/merge)
            title_value = basic_data['title']
            if isinstance(title_value, dict):
                title_text = title_value.get('x-default') or next(iter(title_value.values()), '')
            else:
                title_text = str(title_value)
            
            if title_text:
                # Apply truncation
                title_text, was_truncated = self._truncate_text(title_text)
                
                # Look for existing title element
                existing_title = desc.find(f".//{{{self.XMP_NS['dc']}}}title")
                if existing_title is not None:
                    # Update existing title
                    li_elem = existing_title.find(f".//{{{self.XMP_NS['rdf']}}}li[@{{http://www.w3.org/XML/1998/namespace}}lang='x-default']")
                    if li_elem is not None:
                        li_elem.text = title_text
                    else:
                        # Language tag not found, create new structure inside existing title
                        alt = existing_title.find(f".//{{{self.XMP_NS['rdf']}}}Alt")
                        if alt is None:
                            alt = ET.SubElement(existing_title, f'{{{self.XMP_NS["rdf"]}}}Alt')
                        li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                        li.text = title_text
                else:
                    # Create new title element
                    title_elem = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}title')
                    alt = ET.SubElement(title_elem, f'{{{self.XMP_NS["rdf"]}}}Alt')
                    li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                    li.text = title_text
        
        # Description with language alternative - same pattern as title
        if 'description' in basic_data:
            # Extract text if it's already a language map dict (from previous read/merge)
            desc_value = basic_data['description']
            if isinstance(desc_value, dict):
                desc_text = desc_value.get('x-default') or next(iter(desc_value.values()), '')
            else:
                desc_text = str(desc_value)
            
            if desc_text:
                # Apply truncation
                desc_text, was_truncated = self._truncate_text(desc_text)
                
                existing_desc = desc.find(f".//{{{self.XMP_NS['dc']}}}description")
                if existing_desc is not None:
                    li_elem = existing_desc.find(f".//{{{self.XMP_NS['rdf']}}}li[@{{http://www.w3.org/XML/1998/namespace}}lang='x-default']")
                    if li_elem is not None:
                        li_elem.text = desc_text
                    else:
                        alt = existing_desc.find(f".//{{{self.XMP_NS['rdf']}}}Alt")
                        if alt is None:
                            alt = ET.SubElement(existing_desc, f'{{{self.XMP_NS["rdf"]}}}Alt')
                        li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                        li.text = desc_text
                else:
                    desc_elem = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}description')
                    alt = ET.SubElement(desc_elem, f'{{{self.XMP_NS["rdf"]}}}Alt')
                    li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                    li.text = desc_text
            
        # Keywords as bag
        if 'keywords' in basic_data and basic_data['keywords']:
            keywords = basic_data['keywords']
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',')]
            elif not isinstance(keywords, (list, set, tuple)):
                keywords = [str(keywords)]
            
            # Convert to set for deduplication
            keywords_set = set(keywords)
            
            # Check for existing subject element
            existing_subject = desc.find(f".//{{{self.XMP_NS['dc']}}}subject")
            if existing_subject is not None:
                # Find existing bag
                existing_bag = existing_subject.find(f".//{{{self.XMP_NS['rdf']}}}Bag")
                if existing_bag is not None:
                    # Get existing keywords
                    for li in existing_bag.findall(f".//{{{self.XMP_NS['rdf']}}}li"):
                        if li.text:
                            keywords_set.add(li.text)
                    
                    # Clear existing bag
                    for child in list(existing_bag):
                        existing_bag.remove(child)
                    
                    # Add merged keywords
                    for keyword in sorted(keywords_set):
                        li = ET.SubElement(existing_bag, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.text = str(keyword)
                else:
                    # Create new bag in existing subject
                    bag = ET.SubElement(existing_subject, f'{{{self.XMP_NS["rdf"]}}}Bag')
                    for keyword in sorted(keywords_set):
                        li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.text = str(keyword)
            else:
                # Create new subject element
                subject_elem = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}subject')
                bag = ET.SubElement(subject_elem, f'{{{self.XMP_NS["rdf"]}}}Bag')
                for keyword in sorted(keywords_set):
                    li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.text = str(keyword)
        
        # Rating
        if 'rating' in basic_data:
            # Check for existing rating
            existing_rating = desc.find(f".//{{{self.XMP_NS['xmp']}}}Rating")
            if existing_rating is not None:
                # Update existing rating
                existing_rating.text = str(basic_data['rating'])
            else:
                # Create new rating
                rating_elem = ET.SubElement(desc, f'{{{self.XMP_NS["xmp"]}}}Rating')
                rating_elem.text = str(basic_data['rating'])
        
        # Creator
        if 'creator' in basic_data:
            creator_value = basic_data['creator']
            if not isinstance(creator_value, list):
                creator_value = [str(creator_value)]
                
            # Check for existing creator
            existing_creator = desc.find(f".//{{{self.XMP_NS['dc']}}}creator")
            if existing_creator is not None:
                # Find existing sequence
                existing_seq = existing_creator.find(f".//{{{self.XMP_NS['rdf']}}}Seq")
                if existing_seq is not None:
                    # Replace content with new creator
                    for child in list(existing_seq):
                        existing_seq.remove(child)
                    
                    for creator in creator_value:
                        li = ET.SubElement(existing_seq, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.text = str(creator)
                else:
                    # Create new sequence in existing creator
                    seq = ET.SubElement(existing_creator, f'{{{self.XMP_NS["rdf"]}}}Seq')
                    for creator in creator_value:
                        li = ET.SubElement(seq, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.text = str(creator)
            else:
                # Create new creator element
                creator_elem = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}creator')
                seq = ET.SubElement(creator_elem, f'{{{self.XMP_NS["rdf"]}}}Seq')
                for creator in creator_value:
                    li = ET.SubElement(seq, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.text = str(creator)
        
        # Rights / Copyright - handle both 'rights' and 'copyright' fields
        # Per MWG recommendations, copyright should be in both dc:rights AND xmpRights namespace
        rights_value = basic_data.get('rights') or basic_data.get('copyright')
        if rights_value:
            # Extract text if it's already a language map dict (from previous read/merge)
            if isinstance(rights_value, dict):
                rights_text = rights_value.get('x-default') or next(iter(rights_value.values()), '')
            else:
                rights_text = str(rights_value)
            
            if rights_text:
                # Apply truncation
                rights_text, was_truncated = self._truncate_text(rights_text)
                
                # Add to dc:rights (Dublin Core - for MWG compliance)
                existing_rights = desc.find(f".//{{{self.XMP_NS['dc']}}}rights")
                if existing_rights is not None:
                    # Look for language tag
                    li_elem = existing_rights.find(f".//{{{self.XMP_NS['rdf']}}}li[@{{http://www.w3.org/XML/1998/namespace}}lang='x-default']")
                    if li_elem is not None:
                        li_elem.text = rights_text
                    else:
                        # Language tag not found, create new structure
                        alt = existing_rights.find(f".//{{{self.XMP_NS['rdf']}}}Alt")
                        if alt is None:
                            alt = ET.SubElement(existing_rights, f'{{{self.XMP_NS["rdf"]}}}Alt')
                        li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                        li.text = rights_text
                else:
                    # Create new dc:rights element
                    rights_elem = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}rights')
                    alt = ET.SubElement(rights_elem, f'{{{self.XMP_NS["rdf"]}}}Alt')
                    li = ET.SubElement(alt, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.set(f'{{{self.XMP_NS["xml"]}}}lang', 'x-default')
                    li.text = rights_text

    def _add_analysis_metadata(self, desc: ET.Element, analysis_data: Dict[str, Any]) -> None:
        """
        Add analysis metadata to Description element
        
        Args:
            desc: Description element
            analysis_data: Analysis metadata
        """
        # Process each analysis type
        for analysis_type, data in analysis_data.items():
            # Skip empty data
            if not data:
                continue
                
            # Create container element for this analysis type
            analysis_elem = ET.SubElement(desc, f'{{{self.XMP_NS["eiqa"]}}}{analysis_type}')
            analysis_desc = ET.SubElement(analysis_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
            
            # Add data based on type
            if analysis_type == 'technical':
                self._add_technical_data(analysis_desc, data)
            elif analysis_type == 'aesthetic':
                self._add_aesthetic_data(analysis_desc, data)
            elif analysis_type == 'pyiqa':
                self._add_pyiqa_data(analysis_desc, data)
            elif analysis_type == 'classification':
                self._add_classification_data(analysis_desc, data)
            else:
                # Generic analysis data
                self._add_generic_data(analysis_desc, data, 'eiqa')
    
    def _add_technical_data(self, parent: ET.Element, data: Dict[str, Any]) -> None:
        """
        Add technical analysis data
        
        Args:
            parent: Parent element
            data: Technical analysis data
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested data (e.g., blur.confidence)
                sub_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                sub_desc = ET.SubElement(sub_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                for sub_key, sub_value in value.items():
                    sub_item = ET.SubElement(sub_desc, f'{{{self.XMP_NS["eiqa"]}}}{sub_key}')
                    sub_item.text = str(sub_value)
            else:
                # Simple field
                elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                elem.text = str(value)
    
    def _add_aesthetic_data(self, parent: ET.Element, data: Dict[str, Any]) -> None:
        """
        Add aesthetic analysis data
        
        Args:
            parent: Parent element
            data: Aesthetic analysis data
        """
        for key, value in data.items():
            if key == 'categories':
                # Categories as Bag
                categories_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}categories')
                bag = ET.SubElement(categories_elem, f'{{{self.XMP_NS["rdf"]}}}Bag')
                
                for category in value:
                    li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.text = str(category)
            elif isinstance(value, dict):
                # Nested data (e.g., composition.rule_of_thirds)
                sub_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                sub_desc = ET.SubElement(sub_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                for sub_key, sub_value in value.items():
                    sub_item = ET.SubElement(sub_desc, f'{{{self.XMP_NS["eiqa"]}}}{sub_key}')
                    sub_item.text = str(sub_value)
            else:
                # Simple field
                elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                elem.text = str(value)
    
    def _add_pyiqa_data(self, parent: ET.Element, data: Dict[str, Any]) -> None:
        """
        Add PyIQA analysis data
        
        Args:
            parent: Parent element
            data: PyIQA data
        """
        # Add each model's scores
        for model_name, model_data in data.items():
            model_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{model_name}')
            
            # Handle different data formats
            if isinstance(model_data, dict):
                # Complex model data with score and other info
                model_text = json.dumps(model_data)
            elif isinstance(model_data, (int, float)):
                # Simple numeric score
                model_text = str(model_data)
            else:
                # String or other type
                model_text = str(model_data)
                
            model_elem.text = model_text
            
        # Add timestamp if not present
        if 'timestamp' not in data:
            timestamp_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}timestamp')
            timestamp_elem.text = datetime.datetime.now().isoformat()
    
    def _add_classification_data(self, parent: ET.Element, data: Dict[str, Any]) -> None:
        """
        Add classification data
        
        Args:
            parent: Parent element
            data: Classification data
        """
        for key, value in data.items():
            if key == 'categories':
                # Categories as Bag
                categories_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}categories')
                bag = ET.SubElement(categories_elem, f'{{{self.XMP_NS["rdf"]}}}Bag')
                
                for category in value:
                    li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
                    li.text = str(category)
            elif isinstance(value, dict):
                # Category confidence scores
                cat_elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                cat_desc = ET.SubElement(cat_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                for cat_name, confidence in value.items():
                    cat_score = ET.SubElement(cat_desc, f'{{{self.XMP_NS["eiqa"]}}}{cat_name}')
                    cat_score.text = str(confidence)
            else:
                # Simple field
                elem = ET.SubElement(parent, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                elem.text = str(value)
    
    def _add_ai_metadata(self, desc: ET.Element, ai_data: Dict[str, Any]) -> None:
        """
        Add AI generation metadata with proper RDF structure for searchability
        
        Args:
            desc: Description element
            ai_data: AI metadata
        """
        # Handle generation data
        if 'generation' in ai_data:
            gen_data = ai_data['generation']
            
            # IMPORTANT: Skip workflow data - it's too large for XMP
            workflow_keys_to_remove = ['prompt', 'workflow', 'workflow_data']
            
            # Process different sections with proper CamelCase naming and grouping
            
            # Base model info
            if 'base_model' in gen_data:
                base_model_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}BaseModel')
                base_model_desc = ET.SubElement(base_model_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                for key, value in gen_data['base_model'].items():
                    field_elem = ET.SubElement(base_model_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                    field_elem.text = str(value)
            
            # Sampling parameters
            if 'sampling' in gen_data or any(key in gen_data for key in ['sampler', 'steps', 'cfg_scale', 'seed']):
                # Create Sampling section
                sampling_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}Sampling')
                sampling_desc = ET.SubElement(sampling_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                # First try the sampling section
                if 'sampling' in gen_data:
                    for key, value in gen_data['sampling'].items():
                        field_elem = ET.SubElement(sampling_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        field_elem.text = str(value)
                else:
                    # Try individual parameters
                    for key in ['sampler', 'scheduler', 'steps', 'cfg_scale', 'seed', 'denoise']:
                        if key in gen_data:
                            field_elem = ET.SubElement(sampling_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                            field_elem.text = str(gen_data[key])
            
            # Flux parameters
            if 'flux' in gen_data:
                flux_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}Flux')
                flux_desc = ET.SubElement(flux_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                for key, value in gen_data['flux'].items():
                    field_elem = ET.SubElement(flux_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                    field_elem.text = str(value)
            
            # Dimensions
            if 'dimensions' in gen_data or any(key in gen_data for key in ['width', 'height']):
                # Create Dimensions section
                dimensions_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}Dimensions')
                dimensions_desc = ET.SubElement(dimensions_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                if 'dimensions' in gen_data:
                    for key, value in gen_data['dimensions'].items():
                        field_elem = ET.SubElement(dimensions_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        field_elem.text = str(value)
                else:
                    for key in ['width', 'height', 'batch_size']:
                        if key in gen_data:
                            field_elem = ET.SubElement(dimensions_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                            field_elem.text = str(gen_data[key])
            
            # Modules
            if 'modules' in gen_data:
                modules = gen_data['modules']
                
                # VAE
                if 'vae' in modules:
                    vae_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}VAE')
                    vae_desc = ET.SubElement(vae_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                    
                    for key, value in modules['vae'].items():
                        field_elem = ET.SubElement(vae_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        field_elem.text = str(value)
                
                # CLIP
                if 'clip' in modules:
                    clip_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}CLIP')
                    clip_desc = ET.SubElement(clip_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                    
                    for key, value in modules['clip'].items():
                        field_elem = ET.SubElement(clip_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        field_elem.text = str(value)
                
                # CLIP Vision
                if 'clip_vision' in modules:
                    clip_vision_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}CLIPVision')
                    clip_vision_desc = ET.SubElement(clip_vision_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                    
                    for key, value in modules['clip_vision'].items():
                        field_elem = ET.SubElement(clip_vision_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        field_elem.text = str(value)
                
                # LoRAs
                if 'loras' in modules and modules['loras']:
                    if isinstance(modules['loras'], list) and len(modules['loras']) > 0:
                        # Handle each LoRA in the list (usually there's only one)
                        lora = modules['loras'][0]  # Take the first one
                        loras_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}LoRAs')
                        loras_desc = ET.SubElement(loras_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                        
                        for key, value in lora.items():
                            field_elem = ET.SubElement(loras_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                            field_elem.text = str(value)
                    else:
                        # Single LoRA element or a dictionary
                        loras_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}LoRAs')
                        loras_desc = ET.SubElement(loras_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                        
                        if isinstance(modules['loras'], dict):
                            for key, value in modules['loras'].items():
                                field_elem = ET.SubElement(loras_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                                field_elem.text = str(value)
                
                # Style Models
                if 'style_models' in modules and modules['style_models']:
                    # Create a proper Bag structure
                    style_models_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}StyleModels')
                    
                    if isinstance(modules['style_models'], list) and len(modules['style_models']) > 0:
                        # Multiple style models as Bag
                        bag = ET.SubElement(style_models_elem, f'{{{self.XMP_NS["rdf"]}}}Bag')
                        for style_model in modules['style_models']:
                            li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
                            li_desc = ET.SubElement(li, f'{{{self.XMP_NS["rdf"]}}}Description')
                            
                            for key, value in style_model.items():
                                field_elem = ET.SubElement(li_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                                field_elem.text = str(value)
                    else:
                        # Single style model as Description
                        style_model_desc = ET.SubElement(style_models_elem, f'{{{self.XMP_NS["rdf"]}}}Bag')
                        
                        if isinstance(modules['style_models'], dict):
                            # Add style model details directly
                            for key, value in modules['style_models'].items():
                                field_elem = ET.SubElement(style_model_desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                                field_elem.text = str(value)
            
            # Simple top-level parameters
            for key, value in gen_data.items():
                if key not in ['base_model', 'sampling', 'flux', 'dimensions', 'modules'] + workflow_keys_to_remove:
                    if not isinstance(value, (dict, list)):
                        elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}{key}')
                        elem.text = str(value)
            
            # Add timestamp if missing
            if 'timestamp' not in gen_data:
                timestamp_elem = ET.SubElement(desc, f'{{{self.XMP_NS["ai"]}}}timestamp')
                timestamp_elem.text = datetime.datetime.now().isoformat()
        
            # Now add key AI values to the dc:subject bag for searchability
            important_values = []
            
            # Extract model name
            if 'base_model' in gen_data and isinstance(gen_data['base_model'], dict) and 'unet' in gen_data['base_model']:
                important_values.append(gen_data['base_model']['unet'])
            elif 'model' in gen_data:
                important_values.append(gen_data['model'])
                
            # Extract sampler name
            if 'sampling' in gen_data and isinstance(gen_data['sampling'], dict) and 'sampler' in gen_data['sampling']:
                important_values.append(f"sampler_{gen_data['sampling']['sampler']}")
            elif 'sampler' in gen_data:
                important_values.append(f"sampler_{gen_data['sampler']}")
                
            # Extract LoRA names
            if 'modules' in gen_data and 'loras' in gen_data['modules']:
                loras = gen_data['modules']['loras']
                if isinstance(loras, list):
                    for lora in loras:
                        if isinstance(lora, dict) and 'name' in lora:
                            important_values.append(f"lora_{lora['name']}")
                elif isinstance(loras, dict) and 'name' in loras:
                    important_values.append(f"lora_{loras['name']}")
            elif 'loras' in gen_data:
                loras = gen_data['loras']
                if isinstance(loras, list):
                    for lora in loras:
                        if isinstance(lora, dict) and 'name' in lora:
                            important_values.append(f"lora_{lora['name']}")
            
            # Add these values to the instructions bag instead of subject
            if important_values:
                # Clean up values for better searchability
                cleaned_values = []
                for value in important_values:
                    if '\\' in value:
                        cleaned_values.append(value.replace('\\', '_'))
                    else:
                        cleaned_values.append(value)
                
                # Find existing instructions element or create new one
                existing_instructions = desc.find(f".//{{{self.XMP_NS['dc']}}}instructions")
                existing_bag = None
                
                if existing_instructions is not None:
                    existing_bag = existing_instructions.find(f".//{{{self.XMP_NS['rdf']}}}Bag")
                
                if existing_bag is not None:
                    # Add values to existing bag
                    for value in cleaned_values:
                        # Check if this value is already in the bag
                        already_exists = False
                        for li in existing_bag.findall(f".//{{{self.XMP_NS['rdf']}}}li"):
                            if li.text == value:
                                already_exists = True
                                break
                        
                        if not already_exists:
                            li = ET.SubElement(existing_bag, f'{{{self.XMP_NS["rdf"]}}}li')
                            li.text = value
                else:
                    # Create new instructions element with bag
                    if existing_instructions is None:
                        existing_instructions = ET.SubElement(desc, f'{{{self.XMP_NS["dc"]}}}instructions')
                        existing_bag = ET.SubElement(existing_instructions, f'{{{self.XMP_NS["rdf"]}}}Bag')
                    else:
                        existing_bag = ET.SubElement(existing_instructions, f'{{{self.XMP_NS["rdf"]}}}Bag')
                    
                    # Add values to new bag
                    for value in cleaned_values:
                        li = ET.SubElement(existing_bag, f'{{{self.XMP_NS["rdf"]}}}li')
                        li.text = value
        
            # Add key parameters to the Photoshop namespace for better compatibility
            if 'base_model' in gen_data and isinstance(gen_data['base_model'], dict) and 'unet' in gen_data['base_model']:
                ps_model_elem = ET.SubElement(desc, f'{{{self.XMP_NS["photoshop"]}}}AI_model')
                ps_model_elem.text = gen_data['base_model']['unet']
            
            # Sampling parameters
            if 'sampling' in gen_data and isinstance(gen_data['sampling'], dict):
                for src, dest in [('sampler', 'AI_sampler'), ('steps', 'AI_steps'), 
                                ('cfg_scale', 'AI_cfg_scale'), ('seed', 'AI_seed')]:
                    if src in gen_data['sampling']:
                        ps_field_elem = ET.SubElement(desc, f'{{{self.XMP_NS["photoshop"]}}}{dest}')
                        ps_field_elem.text = str(gen_data['sampling'][src])
    
    def _add_region_metadata(self, desc: ET.Element, regions_data: Dict[str, Any]) -> None:
        """
        Add region metadata in MWG-compliant format
        
        Args:
            desc: Description element
            regions_data: Region data
        """
        # Skip if no regions
        if not regions_data.get('faces') and not regions_data.get('areas'):
            return
            
        # Create regions container
        regions_elem = ET.SubElement(desc, f'{{{self.XMP_NS["mwg-rs"]}}}Regions')
        regions_desc = ET.SubElement(regions_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
        
        # Add summary data if present
        if 'summary' in regions_data:
            for key, value in regions_data['summary'].items():
                elem = ET.SubElement(regions_desc, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                elem.text = str(value)
                
        # Create RegionList container (required by MWG)
        region_list = ET.SubElement(regions_desc, f'{{{self.XMP_NS["mwg-rs"]}}}RegionList')
        bag = ET.SubElement(region_list, f'{{{self.XMP_NS["rdf"]}}}Bag')
        
        # Add face regions
        for face in regions_data.get('faces', []):
            face_li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
            face_desc = ET.SubElement(face_li, f'{{{self.XMP_NS["rdf"]}}}Description')
            
            # Type and name
            type_elem = ET.SubElement(face_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Type')
            type_elem.text = face.get('type', 'Face')
            
            if 'name' in face:
                name_elem = ET.SubElement(face_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Name')
                name_elem.text = face['name']
                
            # Area coordinates
            if 'area' in face:
                area_elem = ET.SubElement(face_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Area')
                
                for coord, value in face['area'].items():
                    area_elem.set(f'{{{self.XMP_NS["stArea"]}}}{coord}', str(value))
                    
            # Extensions (face analysis)
            if 'extensions' in face and 'eiqa' in face['extensions']:
                ext_elem = ET.SubElement(face_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Extensions')
                ext_desc = ET.SubElement(ext_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                
                # Add EIQA face analysis
                face_analysis = face['extensions']['eiqa'].get('face_analysis', {})
                if face_analysis:
                    analysis_elem = ET.SubElement(ext_desc, f'{{{self.XMP_NS["eiqa"]}}}face_analysis')
                    analysis_desc = ET.SubElement(analysis_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                    
                    # Add face analysis fields
                    for key, value in face_analysis.items():
                        if isinstance(value, dict) and 'scores' in value:
                            # Handle scores dictionary
                            scores_elem = ET.SubElement(analysis_desc, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                            scores_desc = ET.SubElement(scores_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                            
                            # Add scores container
                            scores_container = ET.SubElement(scores_desc, f'{{{self.XMP_NS["eiqa"]}}}scores')
                            scores_inner_desc = ET.SubElement(scores_container, f'{{{self.XMP_NS["rdf"]}}}Description')
                            
                            # Add each score
                            for score_name, score_value in value['scores'].items():
                                score_elem = ET.SubElement(scores_inner_desc, f'{{{self.XMP_NS["eiqa"]}}}{score_name}')
                                score_elem.text = str(score_value)
                        else:
                            # Simple field
                            elem = ET.SubElement(analysis_desc, f'{{{self.XMP_NS["eiqa"]}}}{key}')
                            elem.text = str(value)
                            
        # Add area regions
        for area in regions_data.get('areas', []):
            area_li = ET.SubElement(bag, f'{{{self.XMP_NS["rdf"]}}}li')
            area_desc = ET.SubElement(area_li, f'{{{self.XMP_NS["rdf"]}}}Description')
            
            # Type and name
            type_elem = ET.SubElement(area_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Type')
            type_elem.text = area.get('type', 'Area')
            
            if 'name' in area:
                name_elem = ET.SubElement(area_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Name')
                name_elem.text = area['name']
                
            # Area coordinates
            area_elem = ET.SubElement(area_desc, f'{{{self.XMP_NS["mwg-rs"]}}}Area')
            
            # Handle different area formats
            if 'area' in area:
                for coord, value in area['area'].items():
                    area_elem.set(f'{{{self.XMP_NS["stArea"]}}}{coord}', str(value))
            else:
                # Try direct coordinates
                for coord in ['x', 'y', 'w', 'h']:
                    if coord in area:
                        area_elem.set(f'{{{self.XMP_NS["stArea"]}}}{coord}', str(area[coord]))
    
    def _add_structured_namespace(self, desc: ET.Element, prefix: str, data: Dict[str, Any]) -> None:
        """Write structured metadata into ``desc`` for a given namespace prefix."""

        if not data:
            return

        if prefix not in self.XMP_NS:
            self.log(f"Namespace prefix '{prefix}' not registered; skipping", level="WARNING")
            return

        for key, value in data.items():
            if value is None:
                continue
            self._assign_field_value(desc, prefix, key, value)

    def _assign_field_value(
        self,
        parent: ET.Element,
        prefix: str,
        key: str,
        value: Any,
        *,
        allow_remove: bool = True,
    ) -> None:
        """Create or replace a namespaced child element with structured content."""

        ns_uri = self.XMP_NS.get(prefix)
        if not ns_uri:
            self.log(f"Attempted to write to unknown namespace '{prefix}'", level="WARNING")
            return

        if allow_remove:
            existing = parent.find(f"./{{{ns_uri}}}{key}")
            if existing is not None:
                parent.remove(existing)

        element = ET.SubElement(parent, f"{{{ns_uri}}}{key}")
        self._populate_structured_value(element, prefix, key, value)

    def _populate_structured_value(
        self,
        element: ET.Element,
        prefix: str,
        key: str,
        value: Any,
    ) -> None:
        """Populate ``element`` based on the type of ``value``."""

        if isinstance(value, dict):
            if self._is_language_map(value):
                alt = ET.SubElement(element, f"{{{self.XMP_NS['rdf']}}}Alt")
                for lang, text in sorted(value.items()):
                    li = ET.SubElement(alt, f"{{{self.XMP_NS['rdf']}}}li")
                    li.set(f"{{{self.XMP_NS['xml']}}}lang", lang)
                    li.text = self._format_simple_value(text)
                return

            desc = ET.SubElement(element, f"{{{self.XMP_NS['rdf']}}}Description")
            for sub_key, sub_value in value.items():
                if sub_value is None:
                    continue
                self._assign_field_value(desc, prefix, sub_key, sub_value, allow_remove=False)
            return

        if isinstance(value, (list, tuple, set)):
            container_type = XMLTools.is_rdf_container(key) or 'Bag'
            XMLTools.add_list_to_container(
                element,
                container_type,
                list(value),
                self.XMP_NS,
            )
            return

        element.text = self._format_simple_value(value)

    @staticmethod
    def _is_language_map(mapping: Dict[str, Any]) -> bool:
        if not mapping:
            return False
        for lang_code in mapping:
            if not isinstance(lang_code, str):
                return False
            if lang_code == 'x-default':
                continue
            if '-' in lang_code or lang_code.startswith('x-') or len(lang_code) in {2, 5}:
                continue
            return False
        return True

    # XMP text field length limit per Adobe recommendations
    MAX_TEXT_LENGTH = 2000
    TRUNCATION_MARKER = " [...TRUNCATED]"
    
    @classmethod
    def _truncate_text(cls, text: str, max_length: int = None) -> tuple[str, bool]:
        """
        Truncate text to max length if needed, adding continuation marker.
        
        Args:
            text: Text to truncate
            max_length: Maximum length (defaults to MAX_TEXT_LENGTH)
            
        Returns:
            Tuple of (truncated_text, was_truncated)
        """
        if max_length is None:
            max_length = cls.MAX_TEXT_LENGTH
            
        if len(text) <= max_length:
            return text, False
            
        # Reserve space for truncation marker
        effective_length = max_length - len(cls.TRUNCATION_MARKER)
        if effective_length < 100:  # Safety: don't over-truncate
            effective_length = max_length
            
        truncated = text[:effective_length] + cls.TRUNCATION_MARKER
        return truncated, True
    
    @classmethod
    def _format_simple_value(cls, value: Any, max_length: int = None) -> str:
        """
        Format a simple value for XMP, with optional text truncation.
        
        Args:
            value: Value to format
            max_length: Maximum text length (applies to string values only)
            
        Returns:
            Formatted string value
        """
        if isinstance(value, bool):
            return 'True' if value else 'False'
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return ''
        
        text = str(value)
        
        # Apply truncation if max_length specified or text exceeds default limit
        if max_length or len(text) > cls.MAX_TEXT_LENGTH:
            truncated, was_truncated = cls._truncate_text(text, max_length)
            return truncated
        
        return text

    def _add_generic_data(self, parent: ET.Element, data: Dict[str, Any], namespace: str) -> None:
        """
        Add generic metadata to parent element
        
        Args:
            parent: Parent element
            data: Data to add
            namespace: Namespace prefix to use
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # Nested dictionary
                sub_elem = ET.SubElement(parent, f'{{{self.XMP_NS[namespace]}}}{key}')
                sub_desc = ET.SubElement(sub_elem, f'{{{self.XMP_NS["rdf"]}}}Description')
                self._add_generic_data(sub_desc, value, namespace)
            elif isinstance(value, (list, set, tuple)):
                # List -> Bag
                container_type = XMLTools.is_rdf_container(key) or 'Bag'
                container_elem = ET.SubElement(parent, f'{{{self.XMP_NS[namespace]}}}{key}')
                
                XMLTools.add_list_to_container(
                    container_elem, 
                    container_type, 
                    list(value), 
                    self.XMP_NS
                )
            else:
                # Simple value
                elem = ET.SubElement(parent, f'{{{self.XMP_NS[namespace]}}}{key}')
                elem.text = str(value)
    
    def _merge_metadata(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Smart merge of two metadata structures
        
        Args:
            existing: Existing metadata
            new: New metadata to merge
            
        Returns:
            dict: Merged metadata
        """
        result = existing.copy()
        
        # Merge section by section
        for section, data in new.items():
            if section == 'analysis':
                # Analysis data gets merged by type
                if 'analysis' not in result:
                    result['analysis'] = {}
                    
                for analysis_type, type_data in data.items():
                    if analysis_type in result['analysis']:
                        # Merge data in this analysis type
                        result['analysis'][analysis_type] = self._merge_analysis_data(
                            result['analysis'][analysis_type], 
                            type_data,
                            analysis_type
                        )
                    else:
                        # New analysis type, just add it
                        result['analysis'][analysis_type] = type_data
                        
            elif section == 'basic':
                # Handle basic field merging
                if 'basic' not in result:
                    result['basic'] = {}
                    
                # Merge basic fields
                for key, value in data.items():
                    if key == 'keywords':
                        # Combine keywords
                        existing_keywords = set(result['basic'].get('keywords', []))
                        new_keywords = set(value if isinstance(value, (list, set, tuple)) else [value])
                        result['basic']['keywords'] = list(existing_keywords | new_keywords)
                    else:
                        # Replace other fields
                        result['basic'][key] = value
                        
            elif section == 'ai_info':
                # Smart AI info merging
                if 'ai_info' not in result:
                    result['ai_info'] = {}
                    
                # Handle generation data
                if 'generation' in data:
                    gen_data = data['generation']
                    
                    if 'generation' not in result['ai_info']:
                        result['ai_info']['generation'] = gen_data
                    else:
                        # Merge only for missing fields
                        existing_gen = result['ai_info']['generation']
                        
                        for key, value in gen_data.items():
                            if key not in existing_gen or existing_gen[key] is None or existing_gen[key] == '':
                                existing_gen[key] = value
                                
                # Other AI info - just replace
                for key, value in data.items():
                    if key != 'generation':
                        result['ai_info'][key] = value
                        
            elif section == 'regions':
                # Merge region data
                if 'regions' not in result:
                    result['regions'] = data
                else:
                    # Special handling for faces to avoid duplicates
                    if 'faces' in data:
                        if 'faces' not in result['regions']:
                            result['regions']['faces'] = []
                            
                        # Add new faces checking for overlaps
                        for new_face in data['faces']:
                            add_face = True
                            
                            # Check for overlapping faces
                            for existing_face in result['regions'].get('faces', []):
                                if self._are_faces_overlapping(existing_face, new_face):
                                    add_face = False
                                    break
                                    
                            if add_face:
                                result['regions']['faces'].append(new_face)
                                
                    # Update summary
                    if 'summary' in data:
                        if 'summary' not in result['regions']:
                            result['regions']['summary'] = {}
                            
                        result['regions']['summary'].update(data['summary'])
                        
                        # Make sure face count is consistent
                        if 'faces' in result['regions']:
                            result['regions']['summary']['face_count'] = len(result['regions']['faces'])
                    
                    # Add areas
                    if 'areas' in data:
                        if 'areas' not in result['regions']:
                            result['regions']['areas'] = []
                            
                        # Just append areas
                        result['regions']['areas'].extend(data['areas'])
            else:
                # Just replace other sections
                result[section] = data
                
        return result
    
    def _merge_analysis_data(self, existing: Dict[str, Any], new: Dict[str, Any], 
                           analysis_type: str) -> Dict[str, Any]:
        """
        Merge analysis data based on type
        
        Args:
            existing: Existing analysis data
            new: New analysis data
            analysis_type: Type of analysis
            
        Returns:
            dict: Merged analysis data
        """
        result = existing.copy()
        
        # Check timestamps
        existing_time = self._parse_timestamp(existing.get('timestamp'))
        new_time = self._parse_timestamp(new.get('timestamp'))
        
        # If new data is significantly newer, prefer it for most fields
        if new_time and existing_time and (new_time - existing_time).total_seconds() > 60:
            # Special handling for measurements that should be preserved
            if analysis_type in ['technical', 'pyiqa']:
                # Keep all measurements, newer ones override older
                result.update(new)
            elif analysis_type == 'aesthetic':
                # For aesthetic, average the scores
                for key, value in new.items():
                    if key == 'timestamp':
                        result[key] = new[key]  # Use newer timestamp
                    elif isinstance(value, (int, float)) and key in result:
                        # Average numeric scores
                        result[key] = (result[key] + value) / 2
                    else:
                        # Replace other values
                        result[key] = value
            elif analysis_type == 'classification':
                # For classification, keep highest confidence values
                for key, value in new.items():
                    if key == 'timestamp':
                        result[key] = new[key]  # Use newer timestamp
                    elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                        # Compare confidence scores and keep highest
                        for cat, score in value.items():
                            if cat not in result[key] or score > result[key][cat]:
                                result[key][cat] = score
                    else:
                        # Replace other values
                        result[key] = value
            else:
                # For other types, just use newer data
                result = new
        else:
            # Merge fields, with new taking precedence
            result.update(new)
            
        return result
    
    def _map_namespaces_to_sections(self, xmp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map namespace-based structure to section-based structure
        
        Args:
            xmp_data: Data organized by namespace
            
        Returns:
            dict: Data organized by section
        """
        result = {
            'basic': {},
            'analysis': {},
            'ai_info': {},
            'regions': {}
        }
        
        # Map DC namespace to basic metadata
        if 'dc' in xmp_data:
            dc_data = self._unwrap_namespace_wrappers(xmp_data['dc'])

            # Map common fields with normalization of language alternatives
            title_value = dc_data.get('title')
            if title_value:
                normalized_title = self._normalize_lang_alt(title_value)
                result['basic']['title'] = normalized_title
                if isinstance(title_value, dict):
                    result['basic']['title_localized'] = title_value

            description_value = dc_data.get('description')
            if description_value:
                normalized_description = self._normalize_lang_alt(description_value)
                result['basic']['description'] = normalized_description
                if isinstance(description_value, dict):
                    result['basic']['description_localized'] = description_value

            keywords_value = dc_data.get('subject')
            if keywords_value:
                if isinstance(keywords_value, list):
                    result['basic']['keywords'] = keywords_value
                else:
                    result['basic']['keywords'] = [keywords_value]

            creator_value = dc_data.get('creator')
            if creator_value:
                result['basic']['creator'] = creator_value

            rights_value = dc_data.get('rights')
            if rights_value:
                result['basic']['rights'] = rights_value

        # Map XMP namespace to basic metadata
        if 'xmp' in xmp_data:
            xmp_data_fields = self._unwrap_namespace_wrappers(xmp_data['xmp'])

            rating = xmp_data_fields.get('Rating')
            if rating is not None:
                result['basic']['rating'] = self._coerce_numeric(rating)

        # Map EIQA namespace to analysis metadata
        if 'eiqa' in xmp_data:
            eiqa_data = self._unwrap_namespace_wrappers(xmp_data['eiqa'])

            # Map analysis fields based on known categories
            for key, value in eiqa_data.items():
                # Common analysis categories
                if key in ['technical', 'aesthetic', 'classification', 'semantic']:
                    result['analysis'][key] = self._coerce_structure(value)
                else:
                    # Default to technical category for unknown fields
                    if 'technical' not in result['analysis']:
                        result['analysis']['technical'] = {}
                    result['analysis']['technical'][key] = self._coerce_structure(value)
        
        # Map AI namespace to ai_info metadata
        if 'ai' in xmp_data:
            ai_raw = self._unwrap_namespace_wrappers(xmp_data['ai'])
            ai_data = dict(ai_raw)  # shallow copy for mutation safety

            generation: Dict[str, Any] = {}
            modules: Dict[str, Any] = {}

            base_model = ai_data.pop('BaseModel', None)
            if base_model:
                generation['base_model'] = base_model

            sampling = ai_data.pop('Sampling', None)
            if sampling:
                generation['sampling'] = {k: self._coerce_numeric(v) for k, v in sampling.items()}

            dimensions = ai_data.pop('Dimensions', None)
            if dimensions:
                generation['dimensions'] = {k: self._coerce_numeric(v) for k, v in dimensions.items()}

            flux = ai_data.pop('Flux', None)
            if flux:
                generation['flux'] = flux

            for module_key in ['VAE', 'CLIP', 'CLIPVision', 'LoRAs', 'StyleModels']:
                module_value = ai_data.pop(module_key, None)
                if module_value:
                    modules[self._to_snake_case(module_key)] = module_value

            if modules:
                generation['modules'] = modules

            # Collect simple generation fields
            simple_field_map = {
                'prompt': 'prompt',
                'negative_prompt': 'negative_prompt',
                'seed': 'seed',
                'steps': 'steps',
                'sampler': 'sampler',
                'scheduler': 'scheduler',
                'cfg_scale': 'cfg_scale',
                'denoise': 'denoise',
                'model': 'model',
                'model_hash': 'model_hash',
                'timestamp': 'timestamp'
            }

            for raw_key, dest_key in list(simple_field_map.items()):
                if raw_key in ai_data:
                    generation[dest_key] = self._coerce_numeric(ai_data.pop(raw_key))

            # Ensure timestamp gets promoted even if stored with capitalized key
            for alt_key in ['Timestamp', 'timestamp']:
                if alt_key in ai_data:
                    generation['timestamp'] = ai_data.pop(alt_key)
                    break

            if generation:
                result['ai_info']['generation'] = generation

            # Preserve any remaining AI namespace data for diagnostics
            for remaining_key, remaining_value in ai_data.items():
                result['ai_info'][self._to_snake_case(remaining_key)] = remaining_value
        
        # Map MWG-RS namespace to regions metadata
        if 'mwg-rs' in xmp_data:
            mwg_data = self._unwrap_namespace_wrappers(xmp_data['mwg-rs'])

            if isinstance(mwg_data, dict) and 'Regions' in mwg_data:
                raw_regions = mwg_data['Regions']
                faces: List[Dict[str, Any]] = []
                areas: List[Dict[str, Any]] = []

                # Region data can be nested under 'mwg-rs' key or directly
                regions_data = raw_regions.get('mwg-rs', raw_regions) if isinstance(raw_regions, dict) else raw_regions
                region_list = regions_data.get('RegionList', []) if isinstance(regions_data, dict) else []
                
                for entry in region_list:
                    if not isinstance(entry, dict):
                        continue

                    # Entry data may be nested under 'mwg-rs' namespace key
                    entry_data = entry.get('mwg-rs', entry) if 'mwg-rs' in entry else entry
                    
                    entry_type = entry_data.get('Type') or entry_data.get('type', '')
                    normalized: Dict[str, Any] = {}
                    if entry_type:
                        normalized['type'] = entry_type
                    if 'Name' in entry_data or 'name' in entry_data:
                        normalized['name'] = entry_data.get('Name', entry_data.get('name'))
                    if 'Area' in entry_data and isinstance(entry_data['Area'], dict):
                        normalized['area'] = {k: self._coerce_numeric(v) for k, v in entry_data['Area'].items()}
                    if 'Extensions' in entry_data:
                        # Extract extensions, handling nested structure and coercing numeric values
                        ext_raw = entry_data['Extensions']
                        if isinstance(ext_raw, dict):
                            # Handle nested eiqa namespace
                            if 'eiqa' in ext_raw:
                                eiqa_data = ext_raw['eiqa']
                                # Further unwrap if face_analysis contains eiqa wrapper
                                if isinstance(eiqa_data, dict) and 'face_analysis' in eiqa_data:
                                    face_analysis_data = eiqa_data['face_analysis']
                                    # Unwrap one more level if needed
                                    if isinstance(face_analysis_data, dict) and 'eiqa' in face_analysis_data:
                                        # Coerce numeric values in the innermost data
                                        coerced_data = self._coerce_structure(face_analysis_data['eiqa'])
                                        normalized['extensions'] = {'eiqa': {'face_analysis': coerced_data}}
                                    else:
                                        # Coerce the whole eiqa data
                                        coerced_data = self._coerce_structure(eiqa_data)
                                        normalized['extensions'] = {'eiqa': coerced_data}
                                else:
                                    # Coerce the whole eiqa data
                                    coerced_data = self._coerce_structure(eiqa_data)
                                    normalized['extensions'] = {'eiqa': coerced_data}
                            elif 'face_analysis' in ext_raw:
                                coerced_data = self._coerce_structure(ext_raw)
                                normalized['extensions'] = {'eiqa': coerced_data}
                            else:
                                coerced_data = self._coerce_structure(ext_raw)
                                normalized['extensions'] = coerced_data

                    if entry_type.lower() == 'face':
                        faces.append(normalized)
                    else:
                        areas.append(normalized)

                summary_items: Dict[str, Any] = {}
                if isinstance(raw_regions, dict):
                    # Check for eiqa namespace summary data
                    if 'eiqa' in raw_regions:
                        eiqa_summary = raw_regions['eiqa']
                        if isinstance(eiqa_summary, dict):
                            for key, value in eiqa_summary.items():
                                summary_items[key] = self._coerce_numeric(value)
                    
                    # Also check direct fields
                    for key, value in raw_regions.items():
                        if key in ['RegionList', 'mwg-rs', 'eiqa']:
                            continue
                        # Check if this is a summary field
                        if key in ['face_count', 'detector_type', 'area_count']:
                            summary_items[key] = self._coerce_numeric(value)
                        elif isinstance(value, dict) and key not in summary_items:
                            # Could be nested namespace data - flatten it
                            for sub_key, sub_value in value.items():
                                if sub_key not in summary_items:
                                    summary_items[sub_key] = self._coerce_numeric(sub_value)
                        elif key not in summary_items:
                            summary_items[key] = self._coerce_numeric(value)

                if faces and 'face_count' not in summary_items:
                    summary_items['face_count'] = len(faces)
                if areas and 'area_count' not in summary_items:
                    summary_items['area_count'] = len(areas)

                regions_result: Dict[str, Any] = {}
                if faces:
                    regions_result['faces'] = faces
                if areas:
                    regions_result['areas'] = areas
                if summary_items:
                    regions_result['summary'] = summary_items

                if regions_result:
                    result['regions'] = regions_result

        return result
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime.datetime]:
        """
        Parse timestamp string to datetime
        
        Args:
            timestamp_str: Timestamp string in ISO format
            
        Returns:
            datetime or None: Parsed timestamp or None if invalid
        """
        if not timestamp_str:
            return None
            
        try:
            return datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None
    
    def _are_faces_overlapping(self, face1: Dict[str, Any], face2: Dict[str, Any], 
                             threshold: float = 0.5) -> bool:
        """
        Check if two face regions overlap significantly
        
        Args:
            face1: First face region
            face2: Second face region
            threshold: IoU threshold (0-1)
            
        Returns:
            bool: True if faces overlap significantly
        """
        # Extract areas
        area1 = face1.get('area', {})
        area2 = face2.get('area', {})
        
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