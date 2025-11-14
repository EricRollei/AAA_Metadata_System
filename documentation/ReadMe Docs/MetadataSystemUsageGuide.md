# Metadata System Usage Guide

This guide provides detailed instructions and examples for using the Metadata System for ComfyUI. It covers basic and advanced usage, as well as integration with ComfyUI nodes.

## Table of Contents

- [Basic Usage](#basic-usage)
  - [Initialization](#initialization)
  - [Writing Metadata](#writing-metadata)
  - [Reading Metadata](#reading-metadata)
  - [Merging Metadata](#merging-metadata)
- [Metadata Structure](#metadata-structure)
  - [Basic Section](#basic-section)
  - [Analysis Section](#analysis-section)
  - [AI Info Section](#ai-info-section)
  - [Regions Section](#regions-section)
- [ComfyUI Node Usage](#comfyui-node-usage)
  - [Metadata Save Image Node](#metadata-save-image-node)
  - [Metadata Entry Node](#metadata-entry-node)
  - [Metadata Query Node](#metadata-query-node)
  - [Workflow Extractor Node](#workflow-extractor-node)
- [Advanced Features](#advanced-features)
  - [Human-readable Text Format](#human-readable-text-format)
  - [Database Queries](#database-queries)
  - [Resource Identifiers](#resource-identifiers)
  - [Batch Operations](#batch-operations)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)

## Basic Usage

### Initialization

Initialize the MetadataService to start working with the system:

```python
from Metadata_system import MetadataService

# Basic initialization
service = MetadataService()

# With debug mode enabled for troubleshooting
service = MetadataService(debug=True)

# With human-readable text format
service = MetadataService(human_readable_text=True)

# Using as a context manager (ensures proper cleanup)
with MetadataService() as service:
    # Your code here
    pass
```

### Writing Metadata

Write metadata to one or more storage formats:

```python
# Create metadata dictionary
metadata = {
    'basic': {
        'title': 'Mountain Landscape',
        'description': 'AI generated mountain landscape',
        'keywords': ['mountains', 'landscape', 'nature', 'AI'],
        'rating': 4
    },
    'ai_info': {
        'generation': {
            'model': 'stable-diffusion-v1-5',
            'prompt': 'majestic mountains with snow caps',
            'negative_prompt': 'ugly, blurry',
            'sampler': 'euler_a',
            'steps': 30,
            'cfg_scale': 7.5,
            'seed': 1234567890
        }
    }
}

# Write to all supported formats
result = service.write_metadata('path/to/image.png', metadata)

# Write to specific formats
result = service.write_metadata('path/to/image.png', metadata, 
                              targets=['embedded', 'xmp'])

# Check results
for target, success in result.items():
    print(f"{target}: {'Succeeded' if success else 'Failed'}")
```

### Reading Metadata

Read metadata from storage formats:

```python
# Read from embedded metadata with fallback
metadata = service.read_metadata('path/to/image.png', source='embedded', fallback=True)

# Read from specific source without fallback
xmp_metadata = service.read_metadata('path/to/image.png', source='xmp', fallback=False)

# Access specific sections
if 'basic' in metadata:
    print(f"Title: {metadata['basic'].get('title', 'No title')}")
    
if 'ai_info' in metadata and 'generation' in metadata['ai_info']:
    gen = metadata['ai_info']['generation']
    print(f"Model: {gen.get('model')}")
    print(f"Prompt: {gen.get('prompt')}")
```

### Merging Metadata

Merge new metadata with existing metadata:

```python
# New metadata to merge
new_metadata = {
    'basic': {
        'keywords': ['new', 'tags', 'to', 'add']
    },
    'analysis': {
        'technical': {
            'blur': {
                'score': 0.92,
                'higher_better': True
            }
        }
    }
}

# Merge with existing metadata
result = service.merge_metadata('path/to/image.png', new_metadata)

# Merge and write to specific targets
result = service.merge_metadata('path/to/image.png', new_metadata, 
                               targets=['embedded', 'txt'])
```

## Metadata Structure

The metadata is organized into sections for different types of information:

### Basic Section

Contains essential image information:

```python
basic = {
    'title': 'Image Title',                         # Image title
    'description': 'Detailed description',          # Description/caption
    'keywords': ['keyword1', 'keyword2'],           # Tags/keywords
    'rating': 4,                                    # Rating (1-5)
    'creator': 'Author Name',                       # Creator/author
    'rights': 'Copyright information',              # Copyright/license
    'create_date': '2025-03-15T12:34:56'            # Creation timestamp
}
```

### Analysis Section

Contains analysis results from various tools:

```python
analysis = {
    'technical': {
        'blur': {
            'score': 0.92,                          # Blur detection score
            'higher_better': True                   # Whether higher is better
        },
        'noise': {
            'score': 0.08,                          # Noise detection score
            'higher_better': False                  # Whether higher is better
        }
    },
    'aesthetic': {
        'composition': 7.8,                         # Composition score
        'color_harmony': 8.2,                       # Color harmony score
        'overall': 7.9                              # Overall aesthetic score
    },
    'pyiqa': {
        'niqe': {                                   # No-reference IQA model
            'score': 3.45,
            'higher_better': False,
            'range': [0, 25]
        },
        'musiq': {                                  # Multi-scale IQA model
            'score': 78.2,
            'higher_better': True,
            'range': [0, 100]
        }
    },
    'classification': {
        'style': 'photorealistic',                  # Detected style
        'content_type': 'landscape',                # Content type
        'has_text': False                           # Text detection result
    }
}
```

### AI Info Section

Contains AI generation information:

```python
ai_info = {
    'generation': {
        'model': 'stable-diffusion-v1-5',           # Base model
        'prompt': 'mountain landscape',             # Positive prompt
        'negative_prompt': 'ugly, blurry',          # Negative prompt
        'sampler': 'euler_a',                       # Sampler name
        'steps': 30,                                # Sampling steps
        'cfg_scale': 7.5,                           # CFG scale
        'seed': 1234567890,                         # Generation seed
        'width': 512,                               # Image width
        'height': 512,                              # Image height
        'loras': [                                  # LoRAs used
            {
                'name': 'example_lora',
                'strength': 0.8
            }
        ]
    },
    'workflow': {                                   # Full workflow data
        # ComfyUI workflow data (simplified for brevity)
        'nodes': { ... }
    }
}
```

### Regions Section

Contains information about specific regions in the image:

```python
regions = {
    'faces': [                                       # Detected faces
        {
            'type': 'Face',
            'name': 'Person 1',
            'area': {                                # Face coordinates
                'x': 0.2,                            # Normalized (0-1)
                'y': 0.3,
                'w': 0.1,
                'h': 0.15
            },
            'extensions': {                          # Extended face data
                'eiqa': {
                    'face_analysis': {
                        'gender': 'female',
                        'age': 28,
                        'emotion': 'happy'
                    }
                }
            }
        }
    ],
    'areas': [                                       # Other detected areas
        {
            'type': 'Object',
            'name': 'Mountain',
            'area': {
                'x': 0.1,
                'y': 0.2,
                'w': 0.8,
                'h': 0.5
            }
        }
    ],
    'summary': {                                     # Summary statistics
        'face_count': 1,
        'detector_type': 'deepface'
    }
}
```

## ComfyUI Node Usage

### Metadata Save Image Node

The `eric_metadata_save_image` node saves images with metadata:

1. Connect your image output to the node's `images` input
2. Connect workflow data (optional) to the `workflow_data` input
3. Set basic parameters:
   - `save_path`: Directory to save images
   - `filename_prefix`: Prefix for generated filenames
   - `filename_number_padding`: Number of digits for sequential numbering
   - `filename_number_start`: Starting number for sequential filenames
4. Metadata options:
   - `title`: Image title
   - `description`: Image description
   - `keywords`: Comma-separated keywords
   - `save_metadata_to`: Formats to save metadata (embedded,xmp,txt,db)
   - `human_readable_text`: Use human-readable text format

This node automatically captures workflow data, generation parameters, and technical image information.

### Metadata Entry Node

The `eric_metadata_entry` node allows adding custom metadata:

1. Connect to any workflow position
2. Fill in metadata fields:
   - Basic information (title, description, keywords)
   - Analysis scores
   - Custom fields
3. Connect to other nodes that process metadata

### Metadata Query Node

The `eric_metadata_query_node` filters and retrieves metadata:

1. Connect to image input
2. Set query parameters:
   - `query_type`: Type of query to perform
   - `field_path`: Path to the metadata field to query
   - `comparison`: Comparison operator (equals, greater_than, etc.)
   - `value`: Value to compare against
3. Use outputs:
   - `result`: Query result
   - `metadata`: Full metadata dictionary
   - `image`: Passed-through image

### Workflow Extractor Node

The `eric_workflow_extractor` node extracts workflow data from images:

1. Connect to image input
2. Set extraction parameters:
   - `extraction_mode`: How to extract workflow data
   - `include_basic_metadata`: Whether to include basic metadata
3. Use outputs:
   - `workflow_data`: Extracted workflow JSON
   - `metadata`: Full metadata dictionary
   - `image`: Passed-through image

## Advanced Features

### Human-readable Text Format

The system can create human-readable text files for easy viewing:

```python
# Enable human-readable text format
service = MetadataService(human_readable_text=True)

# Or change format at runtime
service.set_text_format(human_readable=True)

# Write metadata (will use human-readable format for text files)
service.write_metadata('path/to/image.png', metadata)
```

Example output:
```
Last update: 2025-03-15T10:23:45.123456
Metadata for image.png

Basic Information:
    Title: Mountain Landscape
    Description: AI generated mountain landscape
    Keywords: mountains, landscape, nature, AI

AI Generation Information:
    Prompt: majestic mountains with snow caps
    Negative prompt: ugly, blurry
    Model: stable-diffusion-v1-5
    Sampler: euler_a
    Steps: 30
    Cfg_scale: 7.5
    Seed: 1234567890
```

### Database Queries

Perform advanced queries on the database:

```python
from Metadata_system.handlers.db import DatabaseHandler

db = DatabaseHandler()

# Search for high-quality mountain images
results = db.search_images({
    'scores': [
        ('aesthetic', 'overall', '>', 7.0),
        ('technical', 'blur.score', '>', 0.8)
    ],
    'keywords': ['mountains'],
    'classifications': [('style', 'photorealistic')],
    'orientation': 'landscape',
    'order_by': 'images.created_date DESC',
    'limit': 10
})

# Process results
for image in results:
    print(f"Found image: {image['filepath']}")
    print(f"Rating: {image.get('rating', 'N/A')}")
```

### Resource Identifiers

Set custom resource identifiers for XMP metadata:

```python
# Set resource identifier for all handlers
service.set_resource_identifier("file:///custom/path/to/resource.jpg")

# Write metadata with custom resource identifier
service.write_metadata('path/to/image.jpg', metadata)
```

### Batch Operations

Perform operations on multiple files:

```python
# Using DatabaseHandler for batch operations
from Metadata_system.handlers.db import DatabaseHandler

db = DatabaseHandler()

# Define file paths
file_paths = [
    'path/to/image1.png',
    'path/to/image2.jpg',
    'path/to/image3.webp'
]

# Read metadata from multiple files
results = db.batch_operation('read', file_paths)

# Update metadata for multiple files
new_metadata = {
    'basic': {
        'keywords': ['batch', 'processed']
    }
}
results = db.batch_operation('write', file_paths, new_metadata)

# Check results
for filepath, success in results.items():
    print(f"{filepath}: {'Succeeded' if success else 'Failed'}")
```

## Troubleshooting

### Common Issues

**Issue**: Cannot write embedded metadata to PNG file
**Solution**: Ensure PyExiv2 is installed or use ExifTool as a fallback

```python
# Check if PyExiv2 is available
try:
    import pyexiv2
    print("PyExiv2 is available")
except ImportError:
    print("PyExiv2 is not available, using ExifTool fallback")
```

**Issue**: Files not showing metadata in other applications
**Solution**: Verify format compatibility and try XMP sidecars

```python
# Force write to XMP sidecar
service.write_metadata('path/to/image.png', metadata, targets=['xmp'])
```

**Issue**: Database errors
**Solution**: Check SQLite installation and file permissions

```python
# Use try-except to handle database errors
try:
    from Metadata_system.handlers.db import DatabaseHandler
    db = DatabaseHandler()
    # Operations with db
except Exception as e:
    print(f"Database error: {str(e)}")
    # Fall back to file-based storage
    service.write_metadata('path/to/image.png', metadata, targets=['embedded', 'xmp', 'txt'])
```

### Debug Mode

Enable debug mode for detailed logging:

```python
# Initialize with debug mode
service = MetadataService(debug=True)

# Operations will now produce detailed logs
service.write_metadata('path/to/image.png', metadata)
```

Debug logs include:
- Format detection results
- Handler selection details
- Operation traces
- Error messages with stack traces

Access error history from handlers:

```python
# Get embedded handler
embedded_handler = service._get_embedded_handler()

# Print error history
for error in embedded_handler.error_history:
    print(f"[{error['timestamp']}] {error['level']}: {error['message']}")
    if error['error']:
        print(f"Error: {error['error']}")
    print("---")
```