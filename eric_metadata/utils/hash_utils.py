"""
Hash Utility Functions - Perceptual image hashing utilities for duplicate detection

This module provides functions for calculating perceptual image hashes
and storing them in metadata. It also offers helpers for hashing arbitrary
files with optional sidecar caching to avoid re-reading large model files.

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

import hashlib
import logging
import os
import string
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from PIL import Image


logger = logging.getLogger(__name__)

# Check for imagehash library
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    print("Warning: imagehash library not installed. To enable image hash functionality:")
    print("pip install imagehash")
    IMAGEHASH_AVAILABLE = False

def calculate_image_hash(image, hash_algorithm="phash"):
    """
    Calculate perceptual hash for an image
    
    Args:
        image: PIL Image object
        hash_algorithm: Hash algorithm to use ('phash', 'dhash', 'average_hash', 'whash-haar')
        
    Returns:
        str: String representation of the hash, or None if error
    """
    if not IMAGEHASH_AVAILABLE:
        return None
        
    try:
        # Calculate hash based on selected algorithm
        hash_value = None
        if hash_algorithm == "phash":
            hash_value = imagehash.phash(image)
        elif hash_algorithm == "dhash":
            hash_value = imagehash.dhash(image)
        elif hash_algorithm == "whash-haar":
            hash_value = imagehash.whash(image)
        else:  # default to average_hash
            hash_value = imagehash.average_hash(image)
            
        # Return string representation
        return str(hash_value)
        
    except Exception as e:
        print(f"Error calculating image hash: {e}")
        return None

def calculate_hash_from_file(file_path, hash_algorithm="phash"):
    """
    Calculate perceptual hash for an image file
    
    Args:
        file_path: Path to image file
        hash_algorithm: Hash algorithm to use
        
    Returns:
        str: String representation of the hash, or None if error
    """
    if not IMAGEHASH_AVAILABLE:
        return None
        
    try:
        # Open image
        img = Image.open(file_path)
        # Calculate hash
        return calculate_image_hash(img, hash_algorithm)
    except Exception as e:
        print(f"Error calculating hash from file {file_path}: {e}")
        return None

def save_hash_to_metadata(file_path, hash_value, hash_algorithm, metadata_service):
    """
    Save hash value to image metadata
    
    Args:
        file_path: Path to image file
        hash_value: String representation of hash
        hash_algorithm: Hash algorithm used
        metadata_service: Initialized metadata service
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not metadata_service:
        return False
        
    try:
        # Create hash metadata
        hash_metadata = {
            'eiqa': {
                'technical': {
                    'hashes': {
                        hash_algorithm: hash_value,
                        'hash_time': datetime.now().isoformat()
                    }
                }
            }
        }
        
        # Set resource identifier
        filename = os.path.basename(file_path)
        resource_uri = f"file:///{filename}"
        metadata_service.set_resource_identifier(resource_uri)
        
        # Write hash metadata
        metadata_service.write_metadata(
            file_path,
            hash_metadata,
            targets=['embedded', 'xmp', 'database']
        )
        
        return True
        
    except Exception as e:
        print(f"Error saving hash to metadata: {e}")
        return False

def calculate_and_save_hash(image_or_path, file_path, metadata_service, hash_algorithm="phash"):
    """
    Calculate image hash and save to metadata
    
    Args:
        image_or_path: PIL Image or path to image file
        file_path: Path where image is/will be saved
        metadata_service: Initialized metadata service
        hash_algorithm: Hash algorithm to use
        
    Returns:
        str: String representation of the hash or None if error
    """
    try:
        # Calculate hash
        hash_value = None
        
        if isinstance(image_or_path, str):
            # It's a file path
            hash_value = calculate_hash_from_file(image_or_path, hash_algorithm)
        else:
            # It's a PIL Image
            hash_value = calculate_image_hash(image_or_path, hash_algorithm)
            
        if hash_value:
            # Save to metadata
            save_hash_to_metadata(file_path, hash_value, hash_algorithm, metadata_service)
            
        return hash_value
        
    except Exception as e:
        print(f"Error in calculate_and_save_hash: {e}")
        return None


def _is_valid_sha256_digest(value: str) -> bool:
    """Quick validation for cached SHA256 strings."""
    if len(value) != 64:
        return False
    return all(ch in string.hexdigits for ch in value)


def hash_file_sha256(file_path: Union[str, Path], use_cache: bool = True) -> Optional[str]:
    """Compute a SHA256 hash for ``file_path`` with optional sidecar caching.

    The cache keeps a ``.sha256`` file next to the original resource and is
    considered valid when its mtime is not older than the source file. Invalid
    or outdated caches are ignored and overwritten on successful recomputation.

    Args:
        file_path: Path to the file that should be hashed.
        use_cache: Whether to consult and persist the optional ``.sha256``
            sidecar. Set to ``False`` to force a live recompute without writing
            cache data.

    Returns:
        The 64-character hexadecimal digest, or ``None`` when the file does not
        exist or hashing fails for any reason.
    """

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        logger.warning("hash_file_sha256: Path does not exist or is not a file: %s", path)
        return None

    cache_path = path.with_suffix(path.suffix + ".sha256")

    if use_cache and cache_path.exists():
        try:
            cache_mtime = cache_path.stat().st_mtime
            source_mtime = path.stat().st_mtime

            if cache_mtime >= source_mtime:
                cached_value = cache_path.read_text(encoding="utf-8").strip()
                if _is_valid_sha256_digest(cached_value):
                    return cached_value.lower()

                logger.debug("hash_file_sha256: Invalid cache contents in %s", cache_path)
        except OSError as exc:
            logger.debug("hash_file_sha256: Failed to read cache %s (%s)", cache_path, exc)

    try:
        sha256_hash = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha256_hash.update(chunk)

        digest = sha256_hash.hexdigest()

        if use_cache:
            try:
                cache_path.write_text(digest + "\n", encoding="utf-8")
            except OSError as exc:
                logger.debug("hash_file_sha256: Unable to write cache %s (%s)", cache_path, exc)

        return digest
    except OSError as exc:
        logger.error("hash_file_sha256: Failed hashing %s (%s)", path, exc)
        return None