"""
XML Tools - XML processing utilities for metadata handling

Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
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
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union, Tuple
import re

class XMLTools:
    """XML processing utilities for metadata handling"""
    
    @staticmethod
    def indent_xml(elem: ET.Element, level: int = 0, indent: str = "  ") -> None:
        """
        Format XML with proper indentation for readability
        
        Args:
            elem: The XML element to indent
            level: Current indentation level
            indent: Indentation string (default: two spaces)
        """
        i = "\n" + level * indent
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                XMLTools.indent_xml(elem, level + 1, indent)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    @staticmethod
    def create_xmp_wrapper(include_packet_wrapper: bool = True) -> Tuple[str, str]:
        """
        Create XMP packet wrappers
        
        Args:
            include_packet_wrapper: Whether to include the xpacket markers
            
        Returns:
            tuple: (start_wrapper, end_wrapper)
        """
        if include_packet_wrapper:
            start = '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            end = '\n<?xpacket end="w"?>'
        else:
            start = ''
            end = ''
            
        return start, end
    
    @staticmethod
    def is_rdf_container(field_path: str) -> Optional[str]:
        """
        Determine if a field should be an RDF container type
        
        Args:
            field_path: The field path to check
            
        Returns:
            str or None: Container type ('Bag', 'Seq', 'Alt') or None
        """
        # Fields needing Bag containers (multiple values)
        bag_fields = ['keywords', 'subject', 'categories', 'RegionList']
        
        # Fields needing Seq containers (ordered lists)
        seq_fields = ['creator', 'History', 'loras']
        
        # Fields needing Alt containers (language alternatives)
        alt_fields = ['title', 'description', 'rights']
        
        # Check field path against patterns
        for field in bag_fields:
            if field in field_path:
                return 'Bag'
        
        for field in seq_fields:
            if field in field_path:
                return 'Seq'
                
        for field in alt_fields:
            if field in field_path:
                return 'Alt'
                
        return None
    
    @staticmethod
    def get_namespace_from_tag(tag: str) -> Tuple[str, str]:
        """
        Extract namespace prefix and local name from a tag
        
        Args:
            tag: The XML tag (possibly with namespace)
            
        Returns:
            tuple: (namespace_prefix, local_name)
        """
        match = re.match(r'\{([^}]+)\}(.*)', tag)
        if match:
            namespace = match.group(1)
            local_name = match.group(2)
            # Try to find prefix for this namespace
            from .namespace import NamespaceManager
            for prefix, uri in NamespaceManager.NAMESPACES.items():
                if uri == namespace:
                    return prefix, local_name
            return namespace, local_name
        else:
            return '', tag
    
    @staticmethod
    def add_list_to_container(parent_elem: ET.Element, 
                             container_type: str, 
                             items: List[Any], 
                             ns_map: Dict[str, str],
                             lang: Optional[str] = None) -> ET.Element:
        """
        Add items to an RDF container (Bag/Seq/Alt)
        
        Args:
            parent_elem: Parent XML element
            container_type: Type of container ('Bag', 'Seq', 'Alt')
            items: List of items to add
            ns_map: Namespace map (prefix -> URI)
            lang: Language code for Alt containers
            
        Returns:
            Element: The created container element
        """
        # Create container element
        container = ET.SubElement(parent_elem, f'{{{ns_map["rdf"]}}}{container_type}')
        
        # Add items to container
        for item in items:
            li = ET.SubElement(container, f'{{{ns_map["rdf"]}}}li')
            
            # Handle language attribute for Alt containers
            if container_type == 'Alt' and lang:
                li.set(f'{{{ns_map["xml"]}}}lang', lang)
                
            # Handle complex items (dict)
            if isinstance(item, dict):
                # Create a Description element
                desc = ET.SubElement(li, f'{{{ns_map["rdf"]}}}Description')
                
                # Add dict items as attributes/elements
                for key, value in item.items():
                    # Try to determine namespace
                    parts = key.split(':')
                    if len(parts) == 2 and parts[0] in ns_map:
                        # Use specified namespace
                        prefix, local_name = parts
                        element = ET.SubElement(desc, f'{{{ns_map[prefix]}}}{local_name}')
                    else:
                        # Use default namespace
                        element = ET.SubElement(desc, key)
                        
                    # Set value
                    if isinstance(value, (str, int, float, bool)):
                        element.text = str(value)
                    elif isinstance(value, dict):
                        # Recursively handle nested dictionaries
                        for sub_key, sub_value in value.items():
                            sub_elem = ET.SubElement(element, sub_key)
                            sub_elem.text = str(sub_value)
            else:
                # Simple item
                li.text = str(item)
                
        return container
    
    @staticmethod
    def xmp_to_dict(xmp_content: str) -> Dict[str, Any]:
        """
        Parse XMP content to a dictionary
        
        Args:
            xmp_content: XMP content as string
            
        Returns:
            dict: Parsed metadata
        """
        # Clean up XMP content - remove XML declaration and packet markers
        content = re.sub(r'<\?xml[^>]+\?>', '', xmp_content)
        content = re.sub(r'<\?xpacket[^>]+\?>', '', content)
        content = re.sub(r'<\?xpacket end="[^"]+"\?>', '', content)
        
        # Parse XML
        root = ET.fromstring(content.strip())
        
        # Extract namespaces
        nsmap = {}
        for key, value in re.findall(r'xmlns:([A-Za-z0-9_\-]+)="([^"]+)"', content):
            nsmap[key] = value
            
        # Build result dictionary
        result = {}
        
        # Find Description element
        for desc in root.findall('.//{*}RDF/{*}Description'):
            XMLTools._extract_description_to_dict(desc, result, nsmap)
            
        return result
    
    @staticmethod
    def _process_rdf_container(container: ET.Element, nsmap: Dict[str, str]) -> List[Any]:
        """Convert an RDF Bag/Seq into a Python list preserving nested descriptions."""
        rdf_ns = nsmap.get('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        items: List[Any] = []

        for li in container.findall(f'{{{rdf_ns}}}li'):
            if len(li):
                # Nested description inside the list item
                desc = li.find(f'{{{rdf_ns}}}Description')
                if desc is not None:
                    item_dict: Dict[str, Any] = {}
                    XMLTools._extract_description_to_dict(desc, item_dict, nsmap)
                    if item_dict:
                        items.append(item_dict)
                    continue

                # Fall back to extracting data directly from the list item
                fallback_dict: Dict[str, Any] = {}
                XMLTools._extract_description_to_dict(li, fallback_dict, nsmap)
                if fallback_dict:
                    items.append(fallback_dict)
                    continue

            text = (li.text or '').strip()
            if text:
                items.append(text)

        return items

    @staticmethod
    def _process_alt_container(alt: ET.Element, nsmap: Dict[str, str]) -> Dict[str, Any]:
        """Convert an RDF Alt container into a lang -> value mapping."""
        rdf_ns = nsmap.get('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
        xml_ns = nsmap.get('xml', 'http://www.w3.org/XML/1998/namespace')
        values: Dict[str, Any] = {}

        for li in alt.findall(f'{{{rdf_ns}}}li'):
            lang = li.get(f'{{{xml_ns}}}lang', 'x-default')
            if len(li):
                desc = li.find(f'{{{rdf_ns}}}Description')
                if desc is not None:
                    nested: Dict[str, Any] = {}
                    XMLTools._extract_description_to_dict(desc, nested, nsmap)
                    if nested:
                        values[lang] = nested
                    continue

                fallback_dict: Dict[str, Any] = {}
                XMLTools._extract_description_to_dict(li, fallback_dict, nsmap)
                if fallback_dict:
                    values[lang] = fallback_dict
                    continue

            text = (li.text or '').strip()
            if text:
                values[lang] = text

        return values

    @staticmethod
    def _extract_element_attributes(element: ET.Element, nsmap: Dict[str, str]) -> Dict[str, Any]:
        """Return a simplified mapping of an element's attributes."""
        attributes: Dict[str, Any] = {}
        for attr_key, attr_value in element.attrib.items():
            _, local_name = XMLTools.get_namespace_from_tag(attr_key)
            attributes[local_name] = attr_value
        return attributes

    @staticmethod
    def _extract_description_to_dict(desc: ET.Element, result: Dict[str, Any], 
                                    nsmap: Dict[str, str]) -> None:
        """
        Extract data from an RDF Description element into a dictionary
        
        Args:
            desc: Description element
            result: Result dictionary to update
            nsmap: Namespace map
        """
        # Process attributes
        for key, value in desc.attrib.items():
            if key != '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about':
                prefix, local_name = XMLTools.get_namespace_from_tag(key)
                section = result.setdefault(prefix, {})
                section[local_name] = value
                
        # Process child elements
        for child in desc:
            prefix, local_name = XMLTools.get_namespace_from_tag(child.tag)
            
            # Handle different element types
            if prefix in nsmap:
                # Initialize section if needed
                section = result.setdefault(prefix, {})
                
                # Check for container elements (Bag/Seq/Alt)
                bag = child.find(f'{{{nsmap.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")}}}Bag')
                seq = child.find(f'{{{nsmap.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")}}}Seq')
                alt = child.find(f'{{{nsmap.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")}}}Alt')

                if bag is not None:
                    section[local_name] = XMLTools._process_rdf_container(bag, nsmap)
                    continue

                if seq is not None:
                    section[local_name] = XMLTools._process_rdf_container(seq, nsmap)
                    continue

                if alt is not None:
                    section[local_name] = XMLTools._process_alt_container(alt, nsmap)
                    continue

                # Complex nested element or attribute-only element
                nested_desc = child.find(f'{{{nsmap.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")}}}Description')
                if nested_desc is not None:
                    nested_dict: Dict[str, Any] = {}
                    XMLTools._extract_description_to_dict(nested_desc, nested_dict, nsmap)
                    section[local_name] = nested_dict
                    continue

                if child.attrib:
                    section[local_name] = XMLTools._extract_element_attributes(child, nsmap)
                    continue

                if child.text and child.text.strip():
                    section[local_name] = child.text.strip()
    
    @staticmethod
    def add_list_to_container(parent: ET.Element, container_type: str, 
                            items: List[Any], namespaces: Dict[str, str]) -> None:
        """
        Add a list of items to an RDF container
        
        Args:
            parent: Parent element to add container to
            container_type: Type of container ('Bag', 'Seq', 'Alt')
            items: List of items to add
            namespaces: Namespace dictionary
        """
        if not items:
            return
            
        # Create container element
        container = ET.SubElement(parent, f'{{{namespaces["rdf"]}}}{container_type}')
        
        # Add items
        for item in items:
            li = ET.SubElement(container, f'{{{namespaces["rdf"]}}}li')
            if isinstance(item, dict):
                # Complex item - create nested description
                desc = ET.SubElement(li, f'{{{namespaces["rdf"]}}}Description')
                for key, value in item.items():
                    elem = ET.SubElement(desc, f'{{{namespaces.get("ai", namespaces["xmp"])}}}{key}')
                    elem.text = str(value)
            else:
                # Simple item
                li.text = str(item)
                    