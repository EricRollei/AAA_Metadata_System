"""
metadata.py
Description: Metadata model for handling image metadata, including basic info, analysis data, and AI generation data.
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
# Metadata_system/src/eric_metadata/models/metadata.py
from typing import Dict, Any, List, Optional, Union, Set
import datetime
import json

class MetadataModel:
    """Base model for metadata structures"""
    
    def __init__(self):
        """Initialize the metadata model with empty structure"""
        self.data = {
            'basic': {},
            'analysis': {},
            'ai_info': {}
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.data
        
    def from_dict(self, data: Dict[str, Any]) -> 'MetadataModel':
        """Load model from dictionary"""
        self.data = data
        return self
        
    def add_basic_metadata(self, title: Optional[str] = None, 
                         description: Optional[str] = None,
                         keywords: Optional[Union[List[str], Set[str], str]] = None,
                         rating: Optional[int] = None) -> 'MetadataModel':
        """
        Add basic metadata
        
        Args:
            title: Image title
            description: Image description
            keywords: Image keywords
            rating: Image rating (0-5)
            
        Returns:
            self for chaining
        """
        if title is not None:
            self.data['basic']['title'] = title
            
        if description is not None:
            self.data['basic']['description'] = description
            
        if keywords is not None:
            # Handle different keyword formats
            if isinstance(keywords, str):
                # Split by commas
                kw_list = [k.strip() for k in keywords.split(',')]
                self.data['basic']['keywords'] = kw_list
            elif isinstance(keywords, (list, set)):
                self.data['basic']['keywords'] = list(keywords)
                
        if rating is not None:
            # Validate rating range
            rating = max(0, min(5, rating))
            self.data['basic']['rating'] = rating
            
        return self
        
    def add_analysis_data(self, analysis_type: str, data: Dict[str, Any]) -> 'MetadataModel':
        """
        Add analysis data
        
        Args:
            analysis_type: Type of analysis (technical, aesthetic, etc.)
            data: Analysis data
            
        Returns:
            self for chaining
        """
        if analysis_type not in self.data['analysis']:
            self.data['analysis'][analysis_type] = {}
            
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.now().isoformat()
            
        # Merge with existing data
        self.data['analysis'][analysis_type].update(data)
        
        return self
        
    def add_ai_generation_data(self, model: Optional[str] = None,
                            prompt: Optional[str] = None,
                            negative_prompt: Optional[str] = None,
                            seed: Optional[int] = None,
                            steps: Optional[int] = None,
                            cfg_scale: Optional[float] = None,
                            sampler: Optional[str] = None,
                            scheduler: Optional[str] = None,
                            loras: Optional[List[Dict[str, Any]]] = None) -> 'MetadataModel':
        """
        Add AI generation data with improved structure
        
        Args:
            model: Model name
            prompt: Positive prompt
            negative_prompt: Negative prompt
            seed: Generation seed
            steps: Number of steps
            cfg_scale: CFG scale
            sampler: Sampler name
            scheduler: Scheduler name
            loras: List of LoRA configurations
            
        Returns:
            self for chaining
        """
        if 'ai_info' not in self.data:
            self.data['ai_info'] = {}
            
        if 'generation' not in self.data['ai_info']:
            self.data['ai_info']['generation'] = {}
            
        generation = self.data['ai_info']['generation']
        
        # Create structured hierarchical data
        
        # Model information
        if model is not None:
            if 'base_model' not in generation:
                generation['base_model'] = {}
            generation['base_model']['unet'] = model
        
        # Sampling parameters
        if any(param is not None for param in [seed, steps, cfg_scale, sampler, scheduler]):
            if 'sampling' not in generation:
                generation['sampling'] = {}
                
            if seed is not None:
                generation['sampling']['seed'] = seed
                
            if steps is not None:
                generation['sampling']['steps'] = steps
                
            if cfg_scale is not None:
                generation['sampling']['cfg_scale'] = cfg_scale
                
            if sampler is not None:
                generation['sampling']['sampler'] = sampler
                
            if scheduler is not None:
                generation['sampling']['scheduler'] = scheduler
        
        # Prompts
        if prompt is not None:
            generation['prompt'] = prompt
            
        if negative_prompt is not None:
            generation['negative_prompt'] = negative_prompt
        
        # LoRAs
        if loras is not None:
            if 'modules' not in generation:
                generation['modules'] = {}
                
            generation['modules']['loras'] = loras
            
        # Add timestamp if not present
        if 'timestamp' not in generation:
            generation['timestamp'] = datetime.datetime.now().isoformat()
            
        return self
    def add_face_region(self, x: float, y: float, w: float, h: float,
                      name: Optional[str] = None,
                      face_data: Optional[Dict[str, Any]] = None) -> 'MetadataModel':
        """
        Add face region
        
        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)
            w: Width (normalized 0-1)
            h: Height (normalized 0-1)
            name: Face name
            face_data: Face analysis data
            
        Returns:
            self for chaining
        """
        if 'regions' not in self.data:
            self.data['regions'] = {
                'summary': {
                    'face_count': 0,
                    'detector_type': None
                },
                'faces': []
            }
            
        # Create face region
        face = {
            'type': 'Face',
            'name': name or f"Face {len(self.data['regions']['faces']) + 1}",
            'area': {
                'x': max(0.0, min(1.0, x)),
                'y': max(0.0, min(1.0, y)),
                'w': max(0.0, min(1.0, w)),
                'h': max(0.0, min(1.0, h))
            }
        }
        
        # Add face analysis data if provided
        if face_data:
            face['extensions'] = {
                'eiqa': {
                    'face_analysis': {}
                }
            }
            
            face_analysis = face['extensions']['eiqa']['face_analysis']
            
            # Add basic fields
            for field in ['age', 'dominant_gender', 'dominant_race', 'dominant_emotion']:
                if field in face_data:
                    face_analysis[field] = face_data[field]
                    
            # Add detailed scores if present
            if 'gender' in face_data:
                face_analysis['gender'] = {
                    'scores': face_data['gender']
                }
                
            if 'race' in face_data:
                face_analysis['race'] = {
                    'scores': face_data['race']
                }
                
            if 'emotion' in face_data:
                face_analysis['emotion'] = {
                    'scores': face_data['emotion']
                }
        
        # Add face to regions
        self.data['regions']['faces'].append(face)
        
        # Update face count
        self.data['regions']['summary']['face_count'] = len(self.data['regions']['faces'])
        
        return self
        
    def merge(self, other: Union[Dict[str, Any], 'MetadataModel']) -> 'MetadataModel':
        """
        Merge with another metadata model or dictionary
        
        Args:
            other: Another metadata model or dictionary
            
        Returns:
            self for chaining
        """
        # Convert to dict if needed
        other_dict = other.to_dict() if isinstance(other, MetadataModel) else other
        
        # Merge basic metadata
        if 'basic' in other_dict:
            for key, value in other_dict['basic'].items():
                if key == 'keywords':
                    # Combine keywords
                    existing_keywords = set(self.data['basic'].get('keywords', []))
                    new_keywords = set(value if isinstance(value, list) else [value])
                    self.data['basic']['keywords'] = list(existing_keywords | new_keywords)
                else:
                    # Replace other basic fields
                    self.data['basic'][key] = value
                    
        # Merge analysis data
        if 'analysis' in other_dict:
            for analysis_type, data in other_dict['analysis'].items():
                self.add_analysis_data(analysis_type, data)
                
        # Merge AI info
        if 'ai_info' in other_dict:
            if 'generation' in other_dict['ai_info']:
                generation = other_dict['ai_info']['generation']
                self.add_ai_generation_data(
                    model=generation.get('model'),
                    prompt=generation.get('prompt'),
                    negative_prompt=generation.get('negative_prompt'),
                    seed=generation.get('seed'),
                    steps=generation.get('steps'),
                    cfg_scale=generation.get('cfg_scale'),
                    sampler=generation.get('sampler'),
                    scheduler=generation.get('scheduler'),
                    loras=generation.get('loras')
                )
                
        # Merge regions
        if 'regions' in other_dict:
            # Add faces
            for face in other_dict['regions'].get('faces', []):
                area = face.get('area', {})
                face_data = face.get('extensions', {}).get('eiqa', {}).get('face_analysis', {})
                
                self.add_face_region(
                    x=area.get('x', 0),
                    y=area.get('y', 0),
                    w=area.get('w', 0),
                    h=area.get('h', 0),
                    name=face.get('name'),
                    face_data=face_data
                )
                
        return self
        
    def to_json(self) -> str:
        """Convert model to JSON string"""
        return json.dumps(self.data, indent=2)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'MetadataModel':
        """Create model from JSON string"""
        data = json.loads(json_str)
        return cls().from_dict(data)