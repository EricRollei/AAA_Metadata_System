"""
Hash Utility Functions - Perceptual image hashing utilities for duplicate detection

This module provides functions for calculating perceptual image hashes
and storing them in metadata.
"""

import os
from datetime import datetime
from PIL import Image

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