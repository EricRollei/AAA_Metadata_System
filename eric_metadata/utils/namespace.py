"""
namespace.py
Description: Handles XML namespaces for metadata operations
    This module is responsible for managing the registration of XML namespaces
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

# Metadata_system/src/eric_metadata/utils/namespace.py
import os
import sys
import importlib
from typing import Dict, Optional, Tuple, List

class NamespaceManager:
    """Manages XML namespaces for metadata handling"""
    
    # Core namespaces required for metadata operations
    NAMESPACES = {
        'x': 'adobe:ns:meta/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
        'xmpRights': 'http://ns.adobe.com/xap/1.0/rights/',
        'xmpMM': 'http://ns.adobe.com/xap/1.0/mm/',
        'mwg-rs': 'http://www.metadataworkinggroup.com/schemas/regions/',
        'stArea': 'http://ns.adobe.com/xmp/sType/Area#',
        'Iptc4xmpCore': 'http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/',
        'eiqa': 'http://ericproject.org/schemas/eiqa/1.0/',
        'ai': 'http://ericproject.org/schemas/ai/1.0/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'mwg-kw': 'http://www.metadataworkinggroup.com/schemas/keywords/'
    }
    
    @classmethod
    def register_with_pyexiv2(cls, debug: bool = False) -> bool:
        """
        Register all namespaces with PyExiv2
        
        Args:
            debug: Whether to enable debug output
            
        Returns:
            bool: True if at least one namespace was registered
        """
        success_count = 0
        
        # Get PyExiv2 module
        pyexiv2 = cls.get_pyexiv2_module()
        if not pyexiv2:
            if debug:
                print("PyExiv2 module not found")
            return False
        
        # Method 0: Top-level registerNs function (for 2.15.x)
        if hasattr(pyexiv2, 'registerNs'):
            try:
                for prefix, uri in cls.NAMESPACES.items():
                    try:
                        pyexiv2.registerNs(uri, prefix)
                        success_count += 1
                        if debug:
                            print(f"Registered namespace {prefix} with registerNs")
                    except Exception as e:
                        if debug:
                            print(f"registerNs failed for {prefix}: {e}")
            except Exception as e:
                if debug:
                    print(f"registerNs global error: {e}")
        
        # Continue with other methods if top-level method failed
        if success_count == 0:
            # Try the other methods as fallbacks...
            # Method 1: Direct module function (old API)
            if hasattr(pyexiv2, 'registerNamespace'):
                try:
                    for prefix, uri in cls.NAMESPACES.items():
                        try:
                            pyexiv2.registerNamespace(uri, prefix)
                            success_count += 1
                            if debug:
                                print(f"Registered namespace {prefix} with method 1")
                        except Exception as e:
                            if debug:
                                print(f"Method 1 failed for {prefix}: {e}")
                except Exception as e:
                    if debug:
                        print(f"Method 1 global error: {e}")
                        
            # Method 2: xmp module function (newer API)
            if hasattr(pyexiv2, 'xmp'):
                try:
                    for prefix, uri in cls.NAMESPACES.items():
                        try:
                            if hasattr(pyexiv2.xmp, 'register_namespace'):
                                pyexiv2.xmp.register_namespace(uri, prefix)
                                success_count += 1
                                if debug:
                                    print(f"Registered namespace {prefix} with method 2")
                        except Exception as e:
                            if debug:
                                print(f"Method 2 failed for {prefix}: {e}")
                except Exception as e:
                    if debug:
                        print(f"Method 2 global error: {e}")
                        
            # Method 3: exiv2api module function
            if hasattr(pyexiv2, 'exiv2api'):
                try:
                    for prefix, uri in cls.NAMESPACES.items():
                        try:
                            if hasattr(pyexiv2.exiv2api, 'registerNamespace'):
                                pyexiv2.exiv2api.registerNamespace(uri, prefix)
                                success_count += 1
                                if debug:
                                    print(f"Registered namespace {prefix} with method 3")
                        except Exception as e:
                            if debug:
                                print(f"Method 3 failed for {prefix}: {e}")
                except Exception as e:
                    if debug:
                        print(f"Method 3 global error: {e}")
                        
        return success_count > 0

    @classmethod
    def get_pyexiv2_module(cls) -> Optional[object]:
        """
        Get the PyExiv2 module using various methods
        
        Returns:
            object or None: The PyExiv2 module if found
        """
        # First try direct import
        try:
            import pyexiv2
            return pyexiv2
        except ImportError:
            pass
            
        # Try py3exiv2 which is sometimes imported as pyexiv2
        try:
            import py3exiv2
            return py3exiv2
        except ImportError:
            pass
            
        # Try dynamic import
        try:
            pyexiv2 = importlib.import_module('pyexiv2')
            return pyexiv2
        except ImportError:
            try:
                py3exiv2 = importlib.import_module('py3exiv2')
                return py3exiv2
            except ImportError:
                pass
                
        # Look for pyexiv2 in any loaded modules
        for name, module in sys.modules.items():
            if 'pyexiv2' in name or 'exiv2' in name:
                return module
                
        # Not found
        return None
    
    @classmethod
    def create_exiftool_config(cls, output_path: Optional[str] = None) -> str:
        """
        Create ExifTool configuration file with custom namespaces
        
        Args:
            output_path: Optional path to write the config file
                If None, writes to the current directory
                
        Returns:
            str: Path to the created config file
        """
        # Generate namespace configuration
        ns_config = []
        for prefix, uri in cls.NAMESPACES.items():
            ns_config.append(f'    NAMESPACE => {{ "{prefix}" => "{uri}" }}')
            
        # Create config file content
        config = f'''
%Image::ExifTool::UserDefined = (
    'Image::ExifTool::XMP::eiqa' => {{
        GROUPS => {{ 0 => 'XMP', 1 => 'XMP-eiqa', 2 => 'Image' }},
        NAMESPACE => {{ 'eiqa' => '{cls.NAMESPACES["eiqa"]}' }},
        WRITABLE => 'string',
        noise_analysis => {{ }},
        blur_analysis => {{ }},
        quality_sort => {{ }},
        technical => {{ }}
    }},
    'Image::ExifTool::XMP::ai' => {{
        GROUPS => {{ 0 => 'XMP', 1 => 'XMP-ai', 2 => 'Image' }},
        NAMESPACE => {{ 'ai' => '{cls.NAMESPACES["ai"]}' }},
        WRITABLE => 'string',
        aesthetic => {{ }},
        semantic => {{ }},
        clip_iqa => {{ }},
        nima => {{ }}
    }}
);
1;
'''
        
        # Determine output path
        if output_path is None:
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exiftool_config.conf')
            
        # Write config file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(config)
            
        return output_path