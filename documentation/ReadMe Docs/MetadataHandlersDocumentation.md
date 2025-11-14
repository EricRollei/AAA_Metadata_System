# Metadata Handlers Documentation

This document provides detailed information about the specialized handlers in the Metadata System, their functionality, and how to use them directly if needed.

## Overview

The Metadata System includes several handlers for different metadata formats:

- **BaseHandler**: Abstract base class for all handlers
- **EmbeddedMetadataHandler**: For metadata embedded within image files
- **XMPSidecarHandler**: For XMP sidecar files
- **TxtFileHandler**: For text file metadata
- **DatabaseHandler**: For SQLite database storage

While the `MetadataService` provides a unified interface for working with these handlers, you can also use them directly for specialized tasks.

## BaseHandler

`BaseHandler` is the abstract base class that provides common functionality for all handlers.

### Key Features

- Thread-safe operations with locks
- Error tracking and recovery
- Logging with multiple levels
- Resource management via context manager
- Common utility methods

### Usage Example

```python
from Metadata_system.handlers.base import BaseHandler

class CustomHandler(BaseHandler):
    def __init__(self, debug=False):
        super().__init__(debug)
        # Custom initialization
        
    def write_metadata(self, filepath, metadata):
        return self._safely_execute(
            "write_custom_metadata",
            self._write_custom_metadata_impl,
            filepath,
            metadata
        )
        
    def _write_custom_metadata_impl(self, filepath, metadata):
        # Implementation details
        pass
        
    def read_metadata(self, filepath):
        return self._safely_execute(
            "read_custom_metadata",
            self._read_custom_metadata_impl,
            filepath
        )
        
    def _read_custom_metadata_impl(self, filepath):
        # Implementation details
        pass
```

## EmbeddedMetadataHandler

`EmbeddedMetadataHandler` manages metadata embedded directly within image files.

### Key Features

- Support for multiple file formats via PyExiv2 and ExifTool
- Special handling for PNG and WebP formats
- Workflow data preservation
- XMP, IPTC, and EXIF writing

### Usage Example

```python
from Metadata_system.handlers.embedded import EmbeddedMetadataHandler

# Initialize handler
handler = EmbeddedMetadataHandler(debug=True)

# Write metadata
metadata = {
    'basic': {
        'title': 'Test Image',
        'description': 'Test description',
        'keywords': ['test', 'image']
    }
}
result = handler.write_metadata('path/to/image.jpg', metadata)

# Read metadata
read_metadata = handler.read_metadata('path/to/image.jpg')
print(f"Title: {read_metadata.get('basic', {}).get('title')}")

# Set resource identifier
handler.set_resource_identifier("file:///custom/path/to/resource.jpg")

# Use as context manager
with EmbeddedMetadataHandler() as handler:
    handler.write_metadata('path/to/image.jpg', metadata)
```

### Format Support

| Format | PyExiv2 Support | ExifTool Support | Special Handling |
|--------|----------------|-----------------|------------------|
| JPEG   | ✓              | ✓               | -                |
| TIFF   | ✓              | ✓               | -                |
| PNG    | ∼ (Limited)    | ✓               | ✓ (Preserves workflow) |
| WebP   | ∼ (Limited)    | ✓               | ✓                |
| HEIC   | ✗              | ✓               | -                |
| AVIF   | ✗              | ✓               | -                |

## XMPSidecarHandler

`XMPSidecarHandler` manages XMP sidecar files.

### Key Features

- MWG standard compliance
- RDF-formatted XML structure
- Smart metadata merging
- Support for complex metadata structures

### Usage Example

```python
from Metadata_system.handlers.xmp import XMPSidecarHandler

# Initialize handler
handler = XMPSidecarHandler(debug=True)

# Write metadata
metadata = {
    'basic': {
        'title': 'Test Image',
        'description': 'Test description',
        'keywords': ['test', 'image']
    }
}
result = handler.write_metadata('path/to/image.jpg', metadata)
# Creates path/to/image.xmp

# Read metadata
read_metadata = handler.read_metadata('path/to/image.jpg')
print(f"Title: {read_metadata.get('basic', {}).get('title')}")

# Set resource identifier
handler.set_resource_identifier("file:///custom/path/to/resource.jpg")

# Directly access merge functionality
merged = handler._merge_metadata(existing_metadata, new_metadata)
```

### XMP Namespaces

The XMP handler supports the following namespaces:

- `dc`: Dublin Core
- `xmp`: XMP Basic
- `xmpRights`: XMP Rights Management
- `xmpMM`: XMP Media Management
- `photoshop`: Adobe Photoshop
- `tiff`: TIFF
- `exif`: EXIF
- `aux`: EXIF Auxiliary
- `crs`: Camera Raw
- `iptc`: IPTC Core
- `iptcExt`: IPTC Extension
- `plus`: PLUS
- `mwg-rs`: MWG Regions
- `stArea`: Structured Area
- `stDim`: Structured Dimensions
- `eiqa`: Eric's Image Quality Assessment
- `ai`: AI Generation

## TxtFileHandler

`TxtFileHandler` manages text file metadata.

### Key Features

- Human-readable format
- Machine-readable format
- Smart value formatting
- Context-aware descriptions

### Usage Example

```python
from Metadata_system.handlers.txt import TxtFileHandler

# Initialize handler with human-readable format
handler = TxtFileHandler(debug=True, human_readable=True)

# Write metadata
metadata = {
    'basic': {
        'title': 'Test Image',
        'description': 'Test description',
        'keywords': ['test', 'image']
    }
}
result = handler.write_metadata('path/to/image.jpg', metadata)
# Creates path/to/image.txt

# Read metadata
read_metadata = handler.read_metadata('path/to/image.jpg')
print(f"Title: {read_metadata.get('basic', {}).get('title')}")

# Change format at runtime
handler.set_output_format(human_readable=False)

# Use explicitly human-readable method
handler.write_human_readable_text('path/to/image.jpg', metadata)
```

### Text Format Examples

#### Human-readable Format

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

#### Machine-readable Format

```
# Metadata for image.png
# Generated: 2025-03-15T10:23:45.123456

basic.title: Mountain Landscape
basic.description: AI generated mountain landscape
basic.keywords: mountains, landscape, nature, AI
ai_info.generation.model: stable-diffusion-v1-5
ai_info.generation.prompt: majestic mountains with snow caps
ai_info.generation.negative_prompt: ugly, blurry
ai_info.generation.sampler: euler_a
ai_info.generation.steps: 30
ai_info.generation.cfg_scale: 7.5
ai_info.generation.seed: 1234567890
```

## DatabaseHandler

`DatabaseHandler` manages SQLite database storage.

### Key Features

- Structured schema
- Complex queries
- Batch operations
- Efficient storage

### Usage Example

```python
from Metadata_system.handlers.db import DatabaseHandler

# Initialize handler
db = DatabaseHandler(debug=True, db_path="custom/path/metadata.db")

# Write metadata
metadata = {
    'basic': {
        'title': 'Test Image',
        'description': 'Test description',
        'keywords': ['test', 'image']
    }
}
result = db.write_metadata('path/to/image.jpg', metadata)

# Read metadata
read_metadata = db.read_metadata('path/to/image.jpg')
print(f"Title: {read_metadata.get('basic', {}).get('title')}")

# Search images
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

# Batch operations
file_paths = ['path/to/image1.png', 'path/to/image2.jpg']
batch_results = db.batch_operation('read', file_paths)

# Delete metadata
db._delete_metadata('path/to/image.jpg')
```

### Database Schema

The database schema includes the following tables:

- `images`: Basic information about images
- `scores`: Numeric measurements and scores
- `keywords`: Image keywords
- `classifications`: Classification results
- `ai_info`: AI generation parameters
- `regions`: Face and object regions
- `metadata_json`: Additional JSON metadata

### Query Structure

The search query structure is a dictionary with the following keys:

```python
query = {
    # Score criteria: (category, metric, operator, value)
    'scores': [
        ('aesthetic', 'overall', '>', 7.0),
        ('technical', 'blur.score', '>', 0.8)
    ],
    
    # Keyword filters
    'keywords': ['mountains', 'landscape'],
    
    # Classification filters: (category, value)
    'classifications': [
        ('style', 'photorealistic'),
        ('content_type', 'landscape')
    ],
    
    # Basic filters
    'orientation': 'landscape',  # 'landscape', 'portrait', 'square'
    'has_text': False,
    'model': 'stable-diffusion-v1-5',
    
    # Ordering and limits
    'order_by': 'images.created_date DESC',
    'limit': 10
}
```

## Advanced Handler Features

### Format Detection

The system uses the `FormatHandler` utility to detect file formats and capabilities:

```python
from Metadata_system.utils.format_detect import FormatHandler

# Get format information
format_info = FormatHandler.get_file_info('path/to/image.png')

# Check capabilities
if format_info['can_use_pyexiv2']:
    # Use PyExiv2
    pass
elif format_info['requires_exiftool']:
    # Use ExifTool
    pass
elif format_info['is_standard']:
    # Use standard format handling
    pass
else:
    # Unsupported format
    pass
```

### Error Recovery

Handlers include error recovery strategies:

```python
from Metadata_system.utils.error_handling import ErrorRecovery

# Create a recovery context
context = {
    'filepath': 'path/to/image.png',
    'metadata': metadata,
    'error_type': 'IOError',
    'error': 'Permission denied'
}

# Attempt recovery
result = ErrorRecovery.recover_write_error(handler, context)
```

### Resource Identification

Set resource identifiers for XMP metadata:

```python
# Set resource identifier
handler.set_resource_identifier("file:///path/to/resource.jpg")

# With MetadataService
service = MetadataService()
service.set_resource_identifier("file:///path/to/resource.jpg")
```

### Thread Safety

All handlers use locks for thread safety:

```python
# BaseHandler includes a lock
self._lock = threading.Lock()

# Operations use the lock
with self._lock:
    # Thread-safe operation
    pass
    
# Or through the _safely_execute method
result = self._safely_execute("operation_name", callback, *args, **kwargs)
```