# Duplicate Image Finder Node

Now let me explain the implementation of the duplicate finder node and how it integrates with your metadata system:

## Overview of the Image Duplicate Finder Node
The node I've created is a comprehensive tool for finding and managing duplicate or similar images across your folders. It leverages the imagehash library and integrates with your metadata system for optimal performance.

## Key Features

### Multi-level Similarity Detection:

- Exact duplicates (near-identical pixel content)
- Similar images (minor variations, resizing, etc.)
- Variant images (related content but with significant differences)

### Multiple Hash Algorithms:

- phash (Perceptual Hash) - default, good all-around performance
- dhash (Difference Hash) - good for detecting structural similarities
- average_hash - fastest but less accurate
- whash-haar (Wavelet Hash) - good for texture-based similarities

### Advanced Similarity Analysis:

- Combines hash comparison with filename analysis
- Uses metadata to enhance similarity detection (creation date, dimensions, etc.)
- Supports secondary hash for additional validation

### Metadata Integration:

- Stores hashes in your metadata system under the image.similarity.hashes namespace
- Records similarity relationships between matched images
- Uses existing metadata to help identify related images

### Duplicate Management:

- Options to move or copy duplicates to a separate folder
- Can group duplicates by similarity type and original image
- Smart selection of which image to keep (keeping largest by default)

### Comprehensive Reporting:

- Detailed reports in JSON and/or CSV format
- Statistics on space savings, file counts, etc.
- Clear display of duplicate groups in ComfyUI output

## How It Works

1. **Scanning Phase**: The node recursively scans one or more directories for image files.
2. **Processing Phase**: For each image, it:
   - Computes perceptual hashes using the selected algorithm(s)
   - Extracts file metadata (size, dimensions, etc.)
   - Retrieves existing metadata if available
   - Optionally saves hash values to the metadata system
3. **Grouping Phase**: The node then:
   - Calculates similarity scores between all image pairs
   - Uses a hierarchical grouping algorithm to create groups at different similarity thresholds
   - Sorts groups by size and similarity level
   - Removes redundant groups (e.g., if all images in a "similar" group are already in an "exact" group)
4. **Action Phase**: Based on configuration, it can:
   - Move or copy duplicate files to a specified folder
   - Update metadata with similarity information
   - Generate detailed reports for further analysis

## Metadata Integration
The node integrates with your metadata system in these key ways:

### Hash Storage: 
It stores hash values in the image.similarity.hashes namespace with timestamps:

```json
{
  "image": {
    "similarity": {
      "hashes": {
        "phash": "0xf8e4a291c7f0e3c7",
        "dhash": "0xa1c3e7802f19c38e",
        "hash_time": "2023-05-15T14:22:10"
      }
    }
  }
}
```

### Similarity Records: 
It records relationships between similar images:

```json
{
  "image": {
    "similarity": {
      "matches": [{
        "path": "original_image.jpg",
        "similarity_score": 0.953,
        "match_type": "exact",
        "primary_hash": "0xf8e4a291c7f0e3c7"
      }]
    }
  }
}
```

### Metadata Reading: 
It reads existing metadata to enhance similarity detection, including:

- Previously computed hashes
- AI generation information (seeds, models)
- Creation dates and other file information

## Extensibility
The code is designed to be easily extended:

- New Hash Algorithms: Support for additional algorithms can be added by extending the hash calculation sections.
- Enhanced Metadata Analysis: The _metadata_similarity function can be expanded to look at additional metadata fields.
- Custom Actions: The duplicate handling section can be extended with new actions (like creating thumbnails, generating comparison reports, etc.).

## Usage Recommendations

### For general duplicate finding, start with these settings:

- Primary hash: phash
- Exact threshold: 0.95
- Similar threshold: 0.85
- Variant threshold: 0.7

### For detecting AI-generated variants and modified versions:

- Increase the metadata_weight to 0.4-0.5
- Enable analyze_filename
- Consider using secondary_hash: dhash

### For working with very large image collections:

- Process directories in batches
- Save hashes to metadata to speed up future runs
- Use results_format: json for detailed analysis

Let me know if you'd like me to explain any specific part of the implementation in more detail or if you have any questions about how to extend or modify the node for specific use cases!
