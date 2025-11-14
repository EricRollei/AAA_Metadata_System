"""
txt.py - Text File Metadata Handler
Description: This module handles writing and reading metadata to and from text files.
It supports both machine-readable and human-readable formats, allowing for easy integration with other systems and user-friendly output.
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


TxtFileHandler - Updated March 2025

This handler manages writing metadata to text files in both machine-readable and 
human-readable formats. It handles merging of existing data, proper type conversion,
and provides multiple output format options.

Updates:
- Added human-readable format with context-aware descriptions
- Improved merging behavior with existing files
- Enhanced type handling for better data representation
- Added runtime format switching capability
- Fixed issues with duplicate data when appending
usage:
to use with human-readable output
    handler = TxtFileHandler(human_readable=True)
    handler.write_metadata(filepath, metadata)  # Uses human-readable format
Switch format at runtime:
    handler = TxtFileHandler()
    # ... later in the code ...
    handler.set_output_format(human_readable=True)
    handler.write_metadata(filepath, metadata)  # Now uses human-readable format
 
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
import datetime
import re

from ..handlers.base import BaseHandler
from ..utils.error_handling import ErrorRecovery

class TxtFileHandler(BaseHandler):
    """Handler for text file metadata"""
    
    def __init__(self, debug: bool = False, human_readable: bool = False):
        """
        Initialize the text file handler
        
        Args:
            debug: Whether to enable debug logging
            human_readable: Whether to use human-readable format by default
        """
        super().__init__(debug)
        self.human_readable = human_readable
    
    def write_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to text file using appropriate format
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get text file path
            txt_path = self._get_text_file_path(filepath)
            
            # Check if file exists
            file_exists = os.path.exists(txt_path)
            
            # Format based on selected output format
            if self.human_readable:
                # For human-readable format, just append new sections
                # Generate formatted content for just the new metadata
                formatted_content = self._format_human_readable_sections(filepath, metadata)
                
                # Either create a new file or append to existing
                mode = 'a' if file_exists else 'w'
                with open(txt_path, mode, encoding='utf-8') as f:
                    if not file_exists:
                        # Write header for new files
                        f.write(f"Last update: {self.get_timestamp()}\n")
                        f.write(f"Metadata for {os.path.basename(filepath)}\n\n")
                    else:
                        # Add section separator
                        f.write(f"\n--- Updated: {self.get_timestamp()} ---\n\n")
                    
                    # Write the new sections
                    f.write(formatted_content)
                
                return True
            else:
                # For flat format, use the merge approach
                existing_metadata = {}
                if file_exists:
                    existing_metadata = self.read_metadata(filepath)
                
                merged_metadata = self._merge_metadata(existing_metadata, metadata)
                return self._write_flat_format(filepath, merged_metadata)
                
        except Exception as e:
            self.log(f"Text file write failed: {str(e)}", level="ERROR", error=e)
            
            # Try recovery
            context = {
                'filepath': filepath,
                'metadata': metadata,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_write_error(self, context)

    def _format_human_readable_sections(self, filepath: str, metadata: Dict[str, Any]) -> str:
        """
        Format just the new metadata sections in human-readable format
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to format
            
        Returns:
            str: Formatted content
        """
        content = []
        added_content = False
        
        # Basic metadata
        if 'basic' in metadata and metadata['basic']:
            basic = metadata['basic']
            section_added = False
            
            if 'title' in basic:
                if not section_added:
                    content.append("Basic Information:")
                    section_added = True
                content.append(f"    Title: {basic['title']}")
                added_content = True
                
            if 'description' in basic:
                if not section_added:
                    content.append("Basic Information:")
                    section_added = True
                content.append(f"    Description: {basic['description']}")
                added_content = True
                
            if 'keywords' in basic:
                if not section_added:
                    content.append("Basic Information:")
                    section_added = True
                    
                keywords = basic['keywords']
                if isinstance(keywords, list):
                    # Show all keywords - no truncation
                    content.append(f"    Keywords: {', '.join(str(k) for k in keywords)}")
                else:
                    content.append(f"    Keywords: {keywords}")
                added_content = True
                
            if 'rating' in basic:
                if not section_added:
                    content.append("Basic Information:")
                    section_added = True
                content.append(f"    Rating: {basic['rating']} out of 5")
                added_content = True
                
            if section_added:
                content.append("")
        
        # AI generation info - place this early as it's important for users
        if 'ai_info' in metadata and metadata['ai_info']:
            ai_info = metadata['ai_info']
            
            if 'generation' in ai_info and ai_info['generation']:
                gen = ai_info['generation']
                content.append("AI Generation Information:")
                added_content = True
                
                if 'prompt' in gen:
                    prompt = gen['prompt']
                    # Truncate long prompts for readability
                    if len(prompt) > 200:
                        content.append(f"    Prompt: {prompt[:200]}...")
                    else:
                        content.append(f"    Prompt: {prompt}")
                    
                if 'negative_prompt' in gen:
                    neg_prompt = gen['negative_prompt']
                    # Truncate long prompts for readability
                    if len(neg_prompt) > 200:
                        content.append(f"    Negative prompt: {neg_prompt[:200]}...")
                    else:
                        content.append(f"    Negative prompt: {neg_prompt}")
                
                for key, value in gen.items():
                    if key not in ['prompt', 'negative_prompt', 'timestamp', 'loras']:
                        content.append(f"    {key.replace('_', ' ').capitalize()}: {value}")
                
                if 'loras' in gen and gen['loras']:
                    content.append("    LoRAs:")
                    for lora in gen['loras']:
                        name = lora.get('name', 'Unknown')
                        strength = lora.get('strength', 1.0)
                        content.append(f"        {name} (strength: {strength})")
                
                content.append("")
        
        # Face detection data
        if 'regions' in metadata and metadata['regions']:
            regions = metadata['regions']
            
            if 'faces' in regions and regions['faces']:
                faces = regions['faces']
                content.append(f"Face Detection: Found {len(faces)} face(s)")
                added_content = True
                
                for i, face in enumerate(faces):
                    face_name = face.get('name', f'Face {i+1}')
                    content.append(f"    {face_name}:")
                    
                    if 'area' in face:
                        area = face['area']
                        x, y = area.get('x', 0), area.get('y', 0)
                        w, h = area.get('w', 0), area.get('h', 0)
                        content.append(f"        Position: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")
                        
                    if 'extensions' in face and 'eiqa' in face['extensions'] and 'face_analysis' in face['extensions']['eiqa']:
                        analysis = face['extensions']['eiqa']['face_analysis']
                        
                        for key, value in analysis.items():
                            if not isinstance(value, dict) and key not in ['scores']:
                                content.append(f"        {key.replace('_', ' ').capitalize()}: {value}")
                
                content.append("")
        
        # PyIQA analysis
        if 'analysis' in metadata and isinstance(metadata['analysis'], dict):
            analysis = metadata['analysis']
            
            # PyIQA data
            if 'pyiqa' in analysis and analysis['pyiqa']:
                pyiqa = analysis['pyiqa']
                content.append("PyIQA Image Quality Assessment:")
                added_content = True
                
                for metric, value in pyiqa.items():
                    if metric == 'timestamp':
                        continue
                        
                    # Handle different value formats
                    if isinstance(value, dict) and 'score' in value:
                        score = value.get('score', 'N/A')
                        higher_better = value.get('higher_better', True)
                        range_vals = value.get('range', [0, 1])
                        better_word = "higher" if higher_better else "lower"
                        
                        if isinstance(range_vals, (list, tuple)) and len(range_vals) == 2:
                            content.append(f"    {metric}: {score} (range: {range_vals[0]}-{range_vals[1]}, {better_word} is better)")
                        else:
                            content.append(f"    {metric}: {score} ({better_word} is better)")
                    elif isinstance(value, (int, float, str)):
                        content.append(f"    {metric}: {value}")
                    elif value is not None:
                        content.append(f"    {metric}: {str(value)}")
                
                content.append("")
            
            # Color analysis data
            if 'eiqa' in analysis and isinstance(analysis['eiqa'], dict) and 'color' in analysis['eiqa']:
                color = analysis['eiqa']['color']
                content.append("Color Analysis:")
                added_content = True
                
                # Dominant colors
                if 'dominant_colors' in color and isinstance(color['dominant_colors'], list):
                    content.append("    Dominant Colors:")
                    for color_info in color['dominant_colors']:
                        name = color_info.get('name', 'Unknown')
                        hex_code = color_info.get('hex', '#000000')
                        percentage = color_info.get('percentage', 0)
                        content.append(f"        {name.replace('_', ' ').title()}: {hex_code} ({percentage*100:.1f}%)")
                    
                # Harmony
                if 'harmony' in color and isinstance(color['harmony'], dict):
                    harmony = color['harmony']
                    content.append(f"    Color Harmony: {harmony.get('type', 'Unknown')}")
                    content.append(f"    Harmony Score: {harmony.get('score', 'N/A')}")
                    content.append(f"    Is Harmonious: {harmony.get('is_harmonious', False)}")
                
                # Characteristics
                if 'characteristics' in color and isinstance(color['characteristics'], dict):
                    chars = color['characteristics']
                    content.append("    Color Characteristics:")
                    for key, value in chars.items():
                        content.append(f"        {key.replace('_', ' ').capitalize()}: {value}")
                
                # Emotional quality
                if 'emotional_quality' in color and isinstance(color['emotional_quality'], dict):
                    eq = color['emotional_quality']
                    content.append("    Emotional Quality:")
                    content.append(f"        Quality: {eq.get('quality', 'Unknown')}")
                    content.append(f"        Score: {eq.get('score', 'N/A')}")
                    
                    if 'emotions' in eq:
                        emotions = eq['emotions']
                        if isinstance(emotions, list):
                            content.append(f"        Emotions: {', '.join(emotions)}")
                        else:
                            content.append(f"        Emotions: {emotions}")
                
                # Age appeal
                if 'age_appeal' in color and isinstance(color['age_appeal'], dict):
                    aa = color['age_appeal']
                    content.append("    Age Appeal:")
                    content.append(f"        Primary Appeal: {aa.get('primary_appeal', 'Unknown')}")
                    content.append(f"        Strength: {aa.get('strength', 'N/A')}")
                
                # Cultural significance
                if 'cultural_significance' in color and isinstance(color['cultural_significance'], dict):
                    cs = color['cultural_significance']
                    content.append("    Cultural Significance:")
                    content.append(f"        Primary Culture: {cs.get('primary_culture', 'Unknown')}")
                    content.append(f"        Primary Score: {cs.get('primary_score', 'N/A')}")
                
                content.append("")
            
            # Technical analysis data (noise, blur, etc.)
            if 'technical' in analysis and isinstance(analysis['technical'], dict):
                technical = analysis['technical']
                content.append("Technical Analysis:")
                added_content = True
                
                # Blur analysis
                if 'blur' in technical:
                    blur = technical['blur']
                    score = blur.get('score', 'N/A')
                    higher_better = blur.get('higher_better', True)
                    better_term = "sharper" if higher_better else "more blurry"
                    worse_term = "more blurry" if higher_better else "sharper"
                    max_val = blur.get('max_value', 100)
                    
                    content.append(f"    Blur score is {score} out of {max_val} with {max_val} being the {worse_term}")
                
                # Noise analysis
                if 'noise' in technical:
                    noise = technical['noise']
                    score = noise.get('score', 'N/A')
                    higher_better = noise.get('higher_better', False)
                    better_word = "higher" if higher_better else "lower"
                    max_val = noise.get('max_value', 1.0)
                    
                    content.append(f"    Noise score is {score} out of {max_val} with {better_word} being better")
                
                # Add any other technical metrics
                for key, value in technical.items():
                    if key not in ['blur', 'noise'] and not isinstance(value, dict):
                        content.append(f"    {key.capitalize()}: {value}")
                
                content.append("")
            
            # Any other analysis sections
            for section_name, section_data in analysis.items():
                if section_name not in ['pyiqa', 'eiqa', 'technical']:
                    if isinstance(section_data, dict) and section_data:
                        content.append(f"{section_name.replace('_', ' ').title()} Analysis:")
                        added_content = True
                        
                        for key, value in section_data.items():
                            if not isinstance(value, dict):
                                content.append(f"    {key.replace('_', ' ').capitalize()}: {value}")
                            else:
                                content.append(f"    {key.replace('_', ' ').capitalize()}:")
                                for sub_key, sub_value in value.items():
                                    content.append(f"        {sub_key.replace('_', ' ').capitalize()}: {sub_value}")
                        
                        content.append("")
        
        # If we didn't add any content, return an empty string
        if not added_content:
            content.append("(No data to display)")
            
        # Join and return
        return '\n'.join(content)
    def _write_flat_format(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata in flat key-value format
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get text file path
            txt_path = self._get_text_file_path(filepath)
            
            # Create or overwrite text file (we're using overwrite since we've already merged)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"# Metadata for {os.path.basename(filepath)}\n")
                f.write(f"# Generated: {self.get_timestamp()}\n\n")
                    
                # Write flattened metadata
                flattened = self._flatten_metadata(metadata)
                
                # Write as key-value pairs
                for key, value in sorted(flattened.items()):
                    f.write(f"{key}: {value}\n")
                    
            self.log(f"Wrote metadata to {txt_path}", level="INFO")
            return True
            
        except Exception as e:
            self.log(f"Flat format write failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def read_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata from text file
        
        Args:
            filepath: Path to the original file
            
        Returns:
            dict: Metadata from text file
        """
        try:
            # Get text file path
            txt_path = self._get_text_file_path(filepath)
            
            # Check if text file exists
            if not os.path.exists(txt_path):
                return {}
                
            # Read text file
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse text content
            return self._parse_text_content(content)
            
        except Exception as e:
            self.log(f"Text file read failed: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_read_error(self, context)
    
    def _flatten_metadata(self, metadata: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """
        Flatten nested metadata structure for text file output
        
        Args:
            metadata: The nested metadata dictionary
            prefix: Key prefix for recursion (default: "")
            
        Returns:
            dict: Flattened dictionary with dotted-notation keys
        """
        flattened = {}
        
        for key, value in metadata.items():
            # Create the new key with prefix if needed
            new_key = f"{prefix}.{key}" if prefix else key
            
            # Handle different types
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested_flat = self._flatten_metadata(value, new_key)
                flattened.update(nested_flat)
            elif isinstance(value, (list, tuple, set)):
                # Convert collections to strings
                if all(isinstance(x, (str, int, float, bool)) for x in value):
                    # Simple values in collection
                    flattened[new_key] = ", ".join(str(item) for item in value)
                else:
                    # Complex items in collection
                    try:
                        flattened[new_key] = json.dumps(list(value))
                    except (TypeError, ValueError):
                        flattened[new_key] = str(value)
            else:
                # Simple values
                flattened[new_key] = str(value)
        
        return flattened
    
    def _parse_text_content(self, content: str) -> Dict[str, Any]:
        """
        Parse text file content back into structured metadata
        
        Args:
            content: Text file content
            
        Returns:
            dict: Structured metadata
        """
        result = {}
        
        # Skip header lines
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]
        
        # Process each line
        for line in lines:
            # Skip lines that don't have key-value format
            if ':' not in line:
                continue
                
            # Split into key-value pairs
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
                
            key = parts[0].strip()
            value = parts[1].strip()
            
            # Handle keys with dots (nested structure)
            keys = key.split('.')
            
            # Build nested structure
            current = result
            for i, k in enumerate(keys):
                if i == len(keys) - 1:
                    # Last key, set value
                    current[k] = self._parse_value(value)
                else:
                    # Intermediate key, ensure dictionary exists
                    if k not in current:
                        current[k] = {}
                    current = current[k]
        
        return result
    
    def _parse_value(self, value_str: str) -> Any:
        """
        Parse string value into appropriate Python type
        
        Args:
            value_str: String value
            
        Returns:
            The parsed value with appropriate type
        """
        # Try to parse as JSON first (for lists, dicts)
        if (value_str.startswith('[') and value_str.endswith(']')) or \
           (value_str.startswith('{') and value_str.endswith('}')):
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                pass
                
        # Try to parse as boolean
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'
            
        # Try to parse as number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                try:
                    return int(value_str)
                except ValueError:
                    pass  # Not an integer, continue to other parsers
        except ValueError:
            pass
            
        # Handle comma-separated lists
        if ',' in value_str:
            parts = [p.strip() for p in value_str.split(',')]
            # Try to parse each part as number or boolean
            try:
                return [self._parse_value(p) for p in parts]
            except Exception:
                pass
                
        # Return as string
        return value_str
    
    def _merge_metadata(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge existing and new metadata
        
        Args:
            existing: Existing metadata
            new: New metadata
            
        Returns:
            dict: Merged metadata
        """
        merged = existing.copy()
        
        # Merge at each level
        for key, value in new.items():
            if key not in merged:
                # New section, just add it
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_metadata(merged[key], value)
            elif isinstance(value, (list, tuple, set)) and isinstance(merged[key], (list, tuple, set)):
                # Combine lists/sets, removing duplicates
                if isinstance(merged[key], list):
                    merged[key] = list(set(merged[key]) | set(value))
                elif isinstance(merged[key], tuple):
                    merged[key] = tuple(set(merged[key]) | set(value))
                else:  # set
                    merged[key] = merged[key] | set(value)
            else:
                # For other types, newer value takes precedence
                merged[key] = value
                
        return merged
    
    def append_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Append new metadata to existing text file (convenience method)
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to append
            
        Returns:
            bool: True if successful
        """
        # This is now just a wrapper for write_metadata, which already handles merging
        return self.write_metadata(filepath, metadata)
    
    def write_formatted_text(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to text file with nice formatting using markdown-style headers
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get text file path
            txt_path = self._get_text_file_path(filepath)
            
            # Create formatted text content
            content = [
                f"# Metadata for {os.path.basename(filepath)}",
                f"# Generated: {self.get_timestamp()}",
                ""
            ]
            
            # Add each section
            section_order = ['basic', 'analysis', 'ai_info', 'regions']
            
            # Process ordered sections first
            for section in section_order:
                if section in metadata:
                    section_content = self.format_section(section, metadata[section])
                    content.append(section_content)
                    content.append("")  # Empty line between sections
            
            # Process any remaining sections
            for section, data in metadata.items():
                if section not in section_order:
                    section_content = self.format_section(section, data)
                    content.append(section_content)
                    content.append("")  # Empty line between sections
            
            # Write to file
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            self.log(f"Formatted text write failed: {str(e)}", level="ERROR", error=e)
            return False
            
    def write_human_readable_text(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to text file in a truly human-readable format
        
        Args:
            filepath: Path to the original file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Get text file path
            txt_path = self._get_text_file_path(filepath)
            
            # Get current timestamp
            timestamp = self.get_timestamp()
            
            # Debug logging to see the metadata structure
            if self.debug:
                self.log(f"Received metadata keys: {list(metadata.keys())}", level="DEBUG")
                if 'analysis' in metadata and isinstance(metadata['analysis'], dict):
                    self.log(f"Analysis keys: {list(metadata.get('analysis', {}).keys())}", level="DEBUG")
            
            # Create formatted text content
            content = [
                f"Last update: {timestamp}",
                f"Metadata for {os.path.basename(filepath)}",
                ""
            ]
            
            # Track if we've added any content beyond the header
            added_content = False
            
            # Basic metadata
            if 'basic' in metadata and metadata['basic']:
                basic = metadata['basic']
                section_added = False
                
                if 'title' in basic:
                    if not section_added:
                        content.append("Basic Information:")
                        section_added = True
                    content.append(f"    Title: {basic['title']}")
                    added_content = True
                    
                if 'description' in basic:
                    if not section_added:
                        content.append("Basic Information:")
                        section_added = True
                    content.append(f"    Description: {basic['description']}")
                    added_content = True
                    
                if 'keywords' in basic:
                    if not section_added:
                        content.append("Basic Information:")
                        section_added = True
                        
                    keywords = basic['keywords']
                    if isinstance(keywords, list):
                        # Show all keywords - no truncation
                        content.append(f"    Keywords: {', '.join(str(k) for k in keywords)}")
                    else:
                        content.append(f"    Keywords: {keywords}")
                    added_content = True
                    
                if 'rating' in basic:
                    if not section_added:
                        content.append("Basic Information:")
                        section_added = True
                    content.append(f"    Rating: {basic['rating']} out of 5")
                    added_content = True
                    
                if section_added:
                    content.append("")
            
            # AI generation info - place this early as it's important for users
            if 'ai_info' in metadata and metadata['ai_info']:
                ai_info = metadata['ai_info']
                
                if 'generation' in ai_info and ai_info['generation']:
                    gen = ai_info['generation']
                    content.append("AI Generation Information:")
                    added_content = True
                    
                    if 'prompt' in gen:
                        prompt = gen['prompt']
                        # Truncate long prompts for readability
                        if len(prompt) > 200:
                            content.append(f"    Prompt: {prompt[:200]}...")
                        else:
                            content.append(f"    Prompt: {prompt}")
                        
                    if 'negative_prompt' in gen:
                        neg_prompt = gen['negative_prompt']
                        # Truncate long prompts for readability
                        if len(neg_prompt) > 200:
                            content.append(f"    Negative prompt: {neg_prompt[:200]}...")
                        else:
                            content.append(f"    Negative prompt: {neg_prompt}")
                    
                    for key, value in gen.items():
                        if key not in ['prompt', 'negative_prompt', 'timestamp', 'loras']:
                            content.append(f"    {key.replace('_', ' ').capitalize()}: {value}")
                    
                    if 'loras' in gen and gen['loras']:
                        content.append("    LoRAs:")
                        for lora in gen['loras']:
                            name = lora.get('name', 'Unknown')
                            strength = lora.get('strength', 1.0)
                            content.append(f"        {name} (strength: {strength})")
                    
                    content.append("")
            
            # Face detection data
            if 'regions' in metadata and metadata['regions']:
                regions = metadata['regions']
                
                if 'faces' in regions and regions['faces']:
                    faces = regions['faces']
                    content.append(f"Face Detection: Found {len(faces)} face(s)")
                    added_content = True
                    
                    for i, face in enumerate(faces):
                        face_name = face.get('name', f'Face {i+1}')
                        content.append(f"    {face_name}:")
                        
                        if 'area' in face:
                            area = face['area']
                            x, y = area.get('x', 0), area.get('y', 0)
                            w, h = area.get('w', 0), area.get('h', 0)
                            content.append(f"        Position: x={x:.2f}, y={y:.2f}, width={w:.2f}, height={h:.2f}")
                            
                        if 'extensions' in face and 'eiqa' in face['extensions'] and 'face_analysis' in face['extensions']['eiqa']:
                            analysis = face['extensions']['eiqa']['face_analysis']
                            
                            for key, value in analysis.items():
                                if not isinstance(value, dict) and key not in ['scores']:
                                    content.append(f"        {key.replace('_', ' ').capitalize()}: {value}")
                    
                    content.append("")
            
            # PyIQA analysis
            if 'analysis' in metadata and isinstance(metadata['analysis'], dict):
                analysis = metadata['analysis']
                
                # PyIQA data
                if 'pyiqa' in analysis and analysis['pyiqa']:
                    pyiqa = analysis['pyiqa']
                    content.append("PyIQA Image Quality Assessment:")
                    added_content = True
                    
                    for metric, value in pyiqa.items():
                        if metric == 'timestamp':
                            continue
                            
                        # Handle different value formats
                        if isinstance(value, dict) and 'score' in value:
                            score = value.get('score', 'N/A')
                            higher_better = value.get('higher_better', True)
                            range_vals = value.get('range', [0, 1])
                            better_word = "higher" if higher_better else "lower"
                            
                            if isinstance(range_vals, (list, tuple)) and len(range_vals) == 2:
                                content.append(f"    {metric}: {score} (range: {range_vals[0]}-{range_vals[1]}, {better_word} is better)")
                            else:
                                content.append(f"    {metric}: {score} ({better_word} is better)")
                        elif isinstance(value, (int, float, str)):
                            content.append(f"    {metric}: {value}")
                        elif value is not None:
                            content.append(f"    {metric}: {str(value)}")
                    
                    content.append("")
                
                # Color analysis data
                if 'eiqa' in analysis and isinstance(analysis['eiqa'], dict) and 'color' in analysis['eiqa']:
                    color = analysis['eiqa']['color']
                    content.append("Color Analysis:")
                    added_content = True
                    
                    # Dominant colors
                    if 'dominant_colors' in color and isinstance(color['dominant_colors'], list):
                        content.append("    Dominant Colors:")
                        for color_info in color['dominant_colors']:
                            name = color_info.get('name', 'Unknown')
                            hex_code = color_info.get('hex', '#000000')
                            percentage = color_info.get('percentage', 0)
                            content.append(f"        {name.replace('_', ' ').title()}: {hex_code} ({percentage*100:.1f}%)")
                        
                    # Harmony
                    if 'harmony' in color and isinstance(color['harmony'], dict):
                        harmony = color['harmony']
                        content.append(f"    Color Harmony: {harmony.get('type', 'Unknown')}")
                        content.append(f"    Harmony Score: {harmony.get('score', 'N/A')}")
                        content.append(f"    Is Harmonious: {harmony.get('is_harmonious', False)}")
                    
                    # Characteristics
                    if 'characteristics' in color and isinstance(color['characteristics'], dict):
                        chars = color['characteristics']
                        content.append("    Color Characteristics:")
                        for key, value in chars.items():
                            content.append(f"        {key.replace('_', ' ').capitalize()}: {value}")
                    
                    # Emotional quality
                    if 'emotional_quality' in color and isinstance(color['emotional_quality'], dict):
                        eq = color['emotional_quality']
                        content.append("    Emotional Quality:")
                        content.append(f"        Quality: {eq.get('quality', 'Unknown')}")
                        content.append(f"        Score: {eq.get('score', 'N/A')}")
                        
                        if 'emotions' in eq:
                            emotions = eq['emotions']
                            if isinstance(emotions, list):
                                content.append(f"        Emotions: {', '.join(emotions)}")
                            else:
                                content.append(f"        Emotions: {emotions}")
                    
                    # Age appeal
                    if 'age_appeal' in color and isinstance(color['age_appeal'], dict):
                        aa = color['age_appeal']
                        content.append("    Age Appeal:")
                        content.append(f"        Primary Appeal: {aa.get('primary_appeal', 'Unknown')}")
                        content.append(f"        Strength: {aa.get('strength', 'N/A')}")
                    
                    # Cultural significance
                    if 'cultural_significance' in color and isinstance(color['cultural_significance'], dict):
                        cs = color['cultural_significance']
                        content.append("    Cultural Significance:")
                        content.append(f"        Primary Culture: {cs.get('primary_culture', 'Unknown')}")
                        content.append(f"        Primary Score: {cs.get('primary_score', 'N/A')}")
                    
                    content.append("")
                
                # Technical analysis data (noise, blur, etc.)
                if 'technical' in analysis and isinstance(analysis['technical'], dict):
                    technical = analysis['technical']
                    content.append("Technical Analysis:")
                    added_content = True
                    
                    # Blur analysis
                    if 'blur' in technical:
                        blur = technical['blur']
                        score = blur.get('score', 'N/A')
                        higher_better = blur.get('higher_better', True)
                        better_term = "sharper" if higher_better else "more blurry"
                        worse_term = "more blurry" if higher_better else "sharper"
                        max_val = blur.get('max_value', 100)
                        
                        content.append(f"    Blur score is {score} out of {max_val} with {max_val} being the {worse_term}")
                    
                    # Noise analysis
                    if 'noise' in technical:
                        noise = technical['noise']
                        score = noise.get('score', 'N/A')
                        higher_better = noise.get('higher_better', False)
                        better_word = "higher" if higher_better else "lower"
                        max_val = noise.get('max_value', 1.0)
                        
                        content.append(f"    Noise score is {score} out of {max_val} with {better_word} being better")
                    
                    # Add any other technical metrics
                    for key, value in technical.items():
                        if key not in ['blur', 'noise'] and not isinstance(value, dict):
                            content.append(f"    {key.capitalize()}: {value}")
                    
                    content.append("")
                
                # Any other analysis sections
                for section_name, section_data in analysis.items():
                    if section_name not in ['pyiqa', 'eiqa', 'technical']:
                        if isinstance(section_data, dict) and section_data:
                            content.append(f"{section_name.replace('_', ' ').title()} Analysis:")
                            added_content = True
                            
                            for key, value in section_data.items():
                                if not isinstance(value, dict):
                                    content.append(f"    {key.replace('_', ' ').capitalize()}: {value}")
                                else:
                                    content.append(f"    {key.replace('_', ' ').capitalize()}:")
                                    for sub_key, sub_value in value.items():
                                        content.append(f"        {sub_key.replace('_', ' ').capitalize()}: {sub_value}")
                            
                            content.append("")
            
            # If we didn't add any content beyond the header, add a note
            if not added_content:
                content.append("Note: This file contains metadata for the image. No detailed structured content was found.")
                content.append("")
                
                # Add a structure dump if in debug mode
                if self.debug:
                    content.append("Metadata Structure:")
                    for section, data in metadata.items():
                        if isinstance(data, dict):
                            section_keys = list(data.keys())
                            content.append(f"    {section}: {section_keys}")
                        else:
                            content.append(f"    {section}: {str(data)[:50]}...")
            
            # Write to file
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            self.log(f"Human-readable text write failed: {str(e)}", level="ERROR", error=e)
            
            # Try to write at least some basic information even if the formatting fails
            try:
                txt_path = self._get_text_file_path(filepath)
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"Last update: {self.get_timestamp()}\n")
                    f.write(f"Metadata for {os.path.basename(filepath)}\n\n")
                    f.write("Error generating human-readable format.\n")
                    f.write(f"Error: {str(e)}\n")
                return False
            except:
                return False
    def format_section(self, section_name: str, section_data: Dict[str, Any], indent: int = 0) -> str:
        """
        Format a section for markdown-style output
        
        Args:
            section_name: Name of the section
            section_data: Section data
            indent: Indentation level
            
        Returns:
            str: Formatted section text
        """
        indent_str = ' ' * indent
        result = [f"{indent_str}## {section_name}"]
        
        # Format each item in the section
        for key, value in section_data.items():
            if isinstance(value, dict):
                # Nested section
                result.append(f"{indent_str}### {key}")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        # Double-nested section
                        result.append(f"{indent_str}  #### {sub_key}")
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            result.append(f"{indent_str}    {sub_sub_key}: {sub_sub_value}")
                    else:
                        # Simple value in nested section
                        result.append(f"{indent_str}  {sub_key}: {sub_value}")
            else:
                # Simple value
                result.append(f"{indent_str}{key}: {value}")
                
        return '\n'.join(result)
    
    def set_output_format(self, human_readable: bool) -> None:
        """
        Set the output format
        
        Args:
            human_readable: Whether to use human-readable format
        """
        self.human_readable = human_readable