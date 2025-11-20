"""JPEG Metadata Fallback Utilities.

Implements 4-stage fallback for JPEG metadata to prevent EXIF size limit errors:
Stage 1 (Full): All metadata including workflow JSON
Stage 2 (Reduced): Drop workflow JSON, keep all other fields
Stage 3 (Minimal): Essential fields only (prompts, model, seed, steps, sampler, dimensions, LoRAs)
Stage 4 (Sidecar): Minimal EXIF + pointer to .json sidecar

Author: Eric Hiss
Date: 2025-11-18
"""

import json
from typing import Dict, Any, Tuple, Optional
from copy import deepcopy


# JPEG EXIF has practical limits - Adobe recommends staying under 60KB for compatibility
JPEG_EXIF_SIZE_THRESHOLD = 60 * 1024  # 60KB in bytes


def estimate_metadata_size(metadata: Dict[str, Any]) -> int:
    """
    Estimate the serialized size of metadata in bytes.
    
    This is an approximation used to predict if metadata will fit in EXIF.
    Uses JSON serialization as a proxy for EXIF/XMP size.
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        Estimated size in bytes
    """
    try:
        # Serialize to JSON to get approximate size
        json_str = json.dumps(metadata, default=str, ensure_ascii=False)
        return len(json_str.encode('utf-8'))
    except Exception:
        # If serialization fails, return a large number to trigger fallback
        return JPEG_EXIF_SIZE_THRESHOLD + 1


def trim_to_essential(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trim metadata to essential fields only for minimal EXIF embedding.
    
    Essential fields preserved:
    - Prompts (positive and negative)
    - Model information (name, hash)
    - Seed
    - Sampler settings (steps, cfg, sampler name, scheduler)
    - Dimensions (width, height)
    - LoRAs (name and strengths)
    - Basic info (title, creator, timestamp)
    
    Args:
        metadata: Full metadata dictionary
        
    Returns:
        Trimmed metadata with only essential fields
    """
    essential = {}
    
    # Basic metadata (if present)
    if 'basic' in metadata:
        basic = metadata['basic']
        essential['basic'] = {}
        for key in ['title', 'creator', 'timestamp']:
            if key in basic:
                essential['basic'][key] = basic[key]
    
    # AI generation info (essential parameters only)
    if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
        gen = metadata['ai_info']['generation']
        essential['ai_info'] = {'generation': {}}
        ess_gen = essential['ai_info']['generation']
        
        # Direct fields
        for key in ['prompt', 'negative_prompt', 'seed', 'steps', 'cfg_scale', 
                    'sampler', 'scheduler', 'width', 'height', 'denoise', 'timestamp']:
            if key in gen:
                ess_gen[key] = gen[key]
        
        # Model info
        if 'base_model' in gen:
            model = gen['base_model']
            ess_gen['base_model'] = {}
            for key in ['name', 'hash', 'checkpoint']:
                if key in model:
                    ess_gen['base_model'][key] = model[key]
        
        # Sampling parameters (if grouped)
        if 'sampling' in gen:
            sampling = gen['sampling']
            ess_gen['sampling'] = {}
            for key in ['sampler', 'scheduler', 'steps', 'cfg_scale', 'seed', 'denoise']:
                if key in sampling:
                    ess_gen['sampling'][key] = sampling[key]
        
        # Dimensions (if grouped)
        if 'dimensions' in gen:
            dims = gen['dimensions']
            ess_gen['dimensions'] = {}
            for key in ['width', 'height', 'batch_size']:
                if key in dims:
                    ess_gen['dimensions'][key] = dims[key]
        
        # LoRAs
        if 'loras' in gen:
            ess_gen['loras'] = gen['loras']  # Keep all LoRA info as it's usually small
        
        # Embeddings
        if 'embeddings' in gen:
            ess_gen['embeddings'] = gen['embeddings']
    
    # Provenance (for traceability)
    if 'provenance' in metadata:
        prov = metadata['provenance']
        essential['provenance'] = {}
        for key in ['created_by', 'created_at', 'source', 'capture_mode']:
            if key in prov:
                essential['provenance'][key] = prov[key]
    
    return essential


def create_reduced_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create reduced metadata by dropping workflow JSON but keeping all other fields.
    
    This is Stage 2 of the fallback - removes the largest single item (workflow JSON)
    which can often be 20-40KB or more.
    
    Args:
        metadata: Full metadata dictionary
        
    Returns:
        Metadata without workflow JSON
    """
    reduced = deepcopy(metadata)
    
    # Remove workflow data (largest contributor to metadata size)
    if 'ai_info' in reduced and 'workflow' in reduced['ai_info']:
        del reduced['ai_info']['workflow']
    
    if 'ai_info' in reduced and 'generation' in reduced['ai_info']:
        gen = reduced['ai_info']['generation']
        # Remove workflow-related fields
        for key in ['workflow', 'workflow_data', 'workflow_api']:
            if key in gen:
                del gen[key]
    
    # Remove analysis data (can be regenerated)
    if 'analysis' in reduced:
        del reduced['analysis']
    
    return reduced


def determine_fallback_stage(metadata: Dict[str, Any], 
                            threshold: int = JPEG_EXIF_SIZE_THRESHOLD) -> Tuple[int, Dict[str, Any], int]:
    """
    Determine which fallback stage is needed based on metadata size.
    
    Args:
        metadata: Full metadata dictionary
        threshold: Size threshold in bytes (default 60KB)
        
    Returns:
        Tuple of (stage_number, metadata_to_use, estimated_size)
        - stage_number: 1-4 indicating which stage was selected
        - metadata_to_use: The metadata dict that should be written
        - estimated_size: Estimated size in bytes of the metadata
    """
    # Stage 1: Try full metadata
    full_size = estimate_metadata_size(metadata)
    if full_size <= threshold:
        return (1, metadata, full_size)
    
    # Stage 2: Try reduced (no workflow)
    reduced = create_reduced_metadata(metadata)
    reduced_size = estimate_metadata_size(reduced)
    if reduced_size <= threshold:
        return (2, reduced, reduced_size)
    
    # Stage 3: Try minimal (essential only)
    minimal = trim_to_essential(metadata)
    minimal_size = estimate_metadata_size(minimal)
    if minimal_size <= threshold:
        return (3, minimal, minimal_size)
    
    # Stage 4: Sidecar only
    # Return very minimal metadata with a pointer
    sidecar_minimal = {
        'basic': {
            'title': metadata.get('basic', {}).get('title', 'AI Generated Image'),
            'description': 'Full metadata in sidecar file'
        },
        'provenance': {
            'metadata_location': 'sidecar',
            'created_by': metadata.get('provenance', {}).get('created_by', 'AAA_Metadata_System')
        }
    }
    return (4, sidecar_minimal, estimate_metadata_size(sidecar_minimal))


def add_fallback_provenance(metadata: Dict[str, Any], stage: int, 
                            original_size: int, final_size: int) -> Dict[str, Any]:
    """
    Add provenance tracking for fallback stage to metadata.
    
    Args:
        metadata: Metadata dictionary to update
        stage: Fallback stage used (1-4)
        original_size: Original metadata size estimate
        final_size: Final metadata size after fallback
        
    Returns:
        Updated metadata with provenance info
    """
    if 'provenance' not in metadata:
        metadata['provenance'] = {}
    
    stage_names = {
        1: 'full',
        2: 'reduced',
        3: 'minimal',
        4: 'sidecar'
    }
    
    metadata['provenance']['jpeg_fallback_stage'] = stage
    metadata['provenance']['jpeg_fallback_stage_name'] = stage_names.get(stage, 'unknown')
    metadata['provenance']['jpeg_metadata_size_original'] = original_size
    metadata['provenance']['jpeg_metadata_size_final'] = final_size
    
    # Add description of what was done
    descriptions = {
        1: 'Full metadata embedded',
        2: 'Workflow JSON removed to reduce size',
        3: 'Only essential fields embedded',
        4: 'Minimal EXIF with pointer to sidecar file'
    }
    metadata['provenance']['jpeg_fallback_description'] = descriptions.get(stage, 'Unknown fallback')
    
    return metadata
