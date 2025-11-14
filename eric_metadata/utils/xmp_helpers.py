"""
xmp_helpers.py
Description: Utilities for creating and manipulating XMP metadata for AI-generated images.
This module provides functions to register namespaces, create XMP packets from metadata,
and extract metadata from XMP packets.
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

XMP Metadata Helpers

Utilities for working with XMP metadata specifically for AI image generation.
Provides namespace registration and standardized structuring for compatibility
with image cataloging software.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

def register_ai_namespaces():
    """
    Register AI-specific namespaces for XMP
    
    This ensures that when writing XMP, the proper namespace prefixes are used
    """
    # Standard namespaces
    ET.register_namespace('x', 'adobe:ns:meta/')
    ET.register_namespace('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    ET.register_namespace('xmp', 'http://ns.adobe.com/xap/1.0/')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
    ET.register_namespace('photoshop', 'http://ns.adobe.com/photoshop/1.0/')
    ET.register_namespace('xmpRights', 'http://ns.adobe.com/xap/1.0/rights/')
    
    # Custom AI namespaces
    ET.register_namespace('ai', 'http://ericproject.org/schemas/ai/1.0/')
    ET.register_namespace('eiqa', 'http://ericproject.org/schemas/eiqa/1.0/')
    ET.register_namespace('sd', 'http://ns.adobe.com/diffusion/1.0/')

def create_xmp_from_metadata(metadata: Dict[str, Any]) -> str:
    """
    Create XMP XML string from metadata dictionary with improved AI structure
    
    Args:
        metadata: Metadata dictionary with AI generation info
        
    Returns:
        str: XMP packet as XML string
    """
    # Register custom namespaces
    register_ai_namespaces()
    
    # Create base XMP structure
    xmpmeta = ET.Element("{adobe:ns:meta/}xmpmeta")
    
    # Add namespaces
    namespaces = {
        'x': 'adobe:ns:meta/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
        'xmpRights': 'http://ns.adobe.com/xap/1.0/rights/',
        'ai': 'http://ericproject.org/schemas/ai/1.0/',
        'eiqa': 'http://ericproject.org/schemas/eiqa/1.0/',
        'sd': 'http://ns.adobe.com/diffusion/1.0/'
    }
    
    for prefix, uri in namespaces.items():
        xmpmeta.set(f"xmlns:{prefix}", uri)
    
    # Create RDF element
    rdf = ET.SubElement(xmpmeta, f"{{{namespaces['rdf']}}}RDF")
    
    # Create Description element
    desc = ET.SubElement(rdf, f"{{{namespaces['rdf']}}}Description")
    desc.set(f"{{{namespaces['rdf']}}}about", "")
    
    # Add basic metadata
    if 'basic' in metadata:
        basic = metadata['basic']
        
        # Handle title, description, etc.
        if 'title' in basic:
            dc_title = ET.SubElement(desc, f"{{{namespaces['dc']}}}title")
            _add_language_alt(dc_title, basic['title'], namespaces)
            
        if 'description' in basic:
            dc_desc = ET.SubElement(desc, f"{{{namespaces['dc']}}}description")
            _add_language_alt(dc_desc, basic['description'], namespaces)
            
        if 'creator' in basic:
            dc_creator = ET.SubElement(desc, f"{{{namespaces['dc']}}}creator")
            _add_seq(dc_creator, [basic['creator']], namespaces)
            
        if 'keywords' in basic:
            keywords = basic['keywords']
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',') if k.strip()]
            dc_subject = ET.SubElement(desc, f"{{{namespaces['dc']}}}subject")
            _add_bag(dc_subject, keywords, namespaces)
    
    # Add AI generation info - enhanced structure
    if 'ai_info' in metadata:
        ai_info = metadata['ai_info']
        
        # Add generation information
        if 'generation' in ai_info:
            gen = ai_info['generation']
            
            # Simplified flat structure for better compatibility
            for key, value in gen.items():
                if key == 'loras':
                    # Handle loras specially
                    continue
                if value is not None:
                    elem = ET.SubElement(desc, f"{{{namespaces['ai']}}}{key}")
                    elem.text = str(value)
            
            # Add LoRAs
            if 'loras' in gen and gen['loras']:
                loras_elem = ET.SubElement(desc, f"{{{namespaces['ai']}}}loras")
                _add_lora_seq(loras_elem, gen['loras'], namespaces)
        
        # Add workflow metadata in a structured way
        if 'workflow_info' in ai_info:
            workflow_info = ai_info['workflow_info']
            for key, value in workflow_info.items():
                if value is not None:
                    elem = ET.SubElement(desc, f"{{{namespaces['ai']}}}{key}")
                    elem.text = str(value)
    
    # Convert to string with proper formatting
    _indent_xml(xmpmeta)
    return ET.tostring(xmpmeta, encoding='unicode')

def _add_language_alt(parent, value, namespaces):
    """Add an RDF language alternative structure"""
    alt = ET.SubElement(parent, f"{{{namespaces['rdf']}}}Alt")
    li = ET.SubElement(alt, f"{{{namespaces['rdf']}}}li")
    li.set('xml:lang', 'x-default')
    li.text = str(value)

def _add_seq(parent, values, namespaces):
    """Add an RDF sequence structure"""
    seq = ET.SubElement(parent, f"{{{namespaces['rdf']}}}Seq")
    for value in values:
        li = ET.SubElement(seq, f"{{{namespaces['rdf']}}}li")
        li.text = str(value)

def _add_bag(parent, values, namespaces):
    """Add an RDF bag structure"""
    bag = ET.SubElement(parent, f"{{{namespaces['rdf']}}}Bag")
    for value in values:
        li = ET.SubElement(bag, f"{{{namespaces['rdf']}}}li")
        li.text = str(value)

def _add_lora_seq(parent, loras, namespaces):
    """
    Add a sequence of LoRA entries with their properties - improved structure
    
    Args:
        parent: Parent XML element to add the sequence to
        loras: List of LoRA entries (dicts or strings)
        namespaces: Dictionary of namespace URI mappings
        
    Returns:
        None
    """
    try:
        seq = ET.SubElement(parent, f"{{{namespaces['rdf']}}}Seq")
        
        for lora in loras:
            li = ET.SubElement(seq, f"{{{namespaces['rdf']}}}li")
            
            if isinstance(lora, dict):
                # Complex LoRA entry with properties
                lora_desc = ET.SubElement(li, f"{{{namespaces['rdf']}}}Description")
                
                # Required properties
                if 'name' in lora:
                    name_elem = ET.SubElement(lora_desc, f"{{{namespaces['ai']}}}name")
                    name_elem.text = str(lora['name'])
                
                # Strength parameters
                for strength_key in ['strength', 'model_strength', 'clip_strength']:
                    if strength_key in lora:
                        strength_elem = ET.SubElement(lora_desc, f"{{{namespaces['ai']}}}{strength_key}")
                        strength_elem.text = str(lora[strength_key])
            else:
                # Simple LoRA name string
                li.text = str(lora)
    except Exception as e:
        print(f"Error creating LoRA sequence: {str(e)}")

def _indent_xml(elem, level=0):
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
            _indent_xml(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
