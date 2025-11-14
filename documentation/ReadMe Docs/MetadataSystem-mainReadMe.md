# Metadata System for ComfyUI

A comprehensive metadata management system for ComfyUI that enables storing, retrieving, and manipulating image metadata across multiple formats.

## Overview

This metadata system provides a unified way to handle image metadata for ComfyUI workflows, supporting:

- Embedded metadata within image files
- XMP sidecar files
- Human-readable text files
- SQLite database storage

The system captures and preserves metadata related to image generation, analysis results, technical characteristics, and more, making your AI-generated images more organized and traceable.

## Features

- **Multi-format Support**: Store metadata in multiple locations simultaneously for maximum compatibility
- **Smart Merging**: Intelligently merge metadata from different sources
- **Extensible Structure**: Well-organized metadata structure with sections for different types of information
- **ComfyUI Integration**: Seamlessly integrates with ComfyUI nodes
- **Human-readable Output**: Optional human-readable text format for easy viewing
- **MWG Standard Compliance**: Follows Metadata Working Group standards for compatibility
- **Workflow Data Preservation**: Captures generation parameters and workflow structure

## Installation

### Requirements

- Python 3.8+
- ComfyUI
- PyExiv2 (optional, for enhanced embedded metadata support)
- ExifTool (optional, for additional format support)

### Install as ComfyUI Custom Node

1. Clone this repository into your ComfyUI custom_nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EricRollei/Metadata_system.git
```

2. Install required dependencies:

```bash
cd Metadata_system
pip install -r requirements.txt
```

3. Restart ComfyUI

## Usage

### Basic Usage

```python
from Metadata_system import MetadataService

# Initialize the service
service = MetadataService(debug=False, human_readable_text=True)

# Write metadata to all supported formats
metadata = {
    'basic': {
        'title': 'My AI Image',
        'description': 'A beautiful landscape',
        'keywords': ['landscape', 'mountains', 'AI generated']
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

# Read metadata with fallback to other formats if primary fails
stored_metadata = service.read_metadata('path/to/image.png', source='embedded', fallback=True)
```

### ComfyUI Node Integration

The system includes several ComfyUI nodes for integration:

- **Metadata Save Image**: Save images with metadata
- **Metadata Entry**: Add custom metadata
- **Metadata Query**: Filter and retrieve metadata
- **Metadata Consolidator**: Combine metadata from multiple sources
- **Workflow Extractor**: Extract workflow data from images

## System Architecture

### Components

- **MetadataService**: Main interface for all metadata operations
- **Handlers**: Specialized components for different metadata formats
  - `EmbeddedMetadataHandler`: For metadata within image files
  - `XMPSidecarHandler`: For XMP sidecar files
  - `TxtFileHandler`: For text file metadata
  - `DatabaseHandler`: For SQLite database storage
- **Utilities**: Support components for format detection, error handling, etc.

### Metadata Structure

The metadata is organized into sections:

- **basic**: Title, description, keywords, etc.
- **analysis**: Technical analysis of the image (blur, noise, aesthetic scores)
- **ai_info**: AI generation parameters and workflow data
- **regions**: Information about faces or specific areas in the image

## Advanced Features

### Human-readable Text Format

Enable human-readable text output for easy viewing:

```python
service = MetadataService(human_readable_text=True)
```

This creates text files that look like:

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

The system supports querying the database for images matching specific criteria:

```python
from Metadata_system.handlers.db import DatabaseHandler

db = DatabaseHandler()
results = db.search_images({
    'scores': [('aesthetic', 'overall', '>', 7.0)],
    'keywords': ['mountains'],
    'orientation': 'landscape'
})
```

## License

Dual License:

1. Non-Commercial Use: This software is licensed under the terms of the Creative Commons Attribution-NonCommercial 4.0 International License.
   
2. Commercial Use: For commercial use, a separate license is required. Please contact Eric Hiss at [eric@historic.camera, eric@rollei.us] for licensing options.

## Dependencies

This project uses several third-party libraries, each with its own license. See [license-dependencies.md](license-dependencies.md) for details.

## Contributing

Contributions are welcome! Please see [contributing.md](contributing.md) for guidelines.

## Acknowledgments

- ComfyUI team for the amazing AI image generation framework
- ExifTool creators for their powerful metadata management tool
- PyExiv2 team for Python bindings to exiv2

## Contact

- GitHub: [EricRollei](https://github.com/EricRollei)
- Email: [eric@historic.camera](mailto:eric@historic.camera)