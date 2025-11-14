# Save Image with Metadata Node

## Overview

The "Save Image with Metadata" node extends ComfyUI's standard image saving capabilities with comprehensive metadata handling. It captures AI generation parameters, workflow information, and user-provided descriptive metadata, then embeds this information directly into saved images.

This node is designed to create well-documented images that preserve their creation history for archiving, organization, and future reference.

## Installation & Dependencies

### Requirements:
- ComfyUI
- Metadata_system package
- Python Imaging Library (PIL/Pillow)
- PyExiv2 (for metadata handling)

### Installation:
1. Ensure the Metadata_system package is installed in your ComfyUI environment
2. Place the node file in your ComfyUI custom_nodes directory
3. Restart ComfyUI

## How It Works

### Comprehensive Metadata Structure:
- The basic metadata section includes fields for title, description, copyright, creator, and project
- Keywords are properly parsed from comma-separated input
- Rights metadata follows standard XMP conventions

### AI Generation Information:
- Automatically captures generation parameters (model, prompts, sampler, seed, etc.)
- Preserves workflow information, identifying active nodes that contributed to the output
- Includes summary information about the workflow complexity

### Advanced File Handling:
- Supports custom output directories
- Automatically formats filenames with datetime and project information when enabled
- Maintains compatibility with ComfyUI's folder structure

### User Flexibility:
- All metadata fields are optional - you can fill in as much or as little as you want
- Boolean toggles for including datetime/project in filenames
- Supports multiple metadata storage formats (embedded, XMP sidecar, text files)

## Input Parameters

### Required Inputs:
- **images**: The image tensor to save
- **filename_prefix**: Base prefix for the output filename

### Optional Inputs:

#### Basic Metadata:
- **title**: Image title
- **description**: Detailed image description
- **keywords**: Comma-separated keywords for categorization
- **copyright**: Rights information
- **project**: Project name (useful for grouping related images)
- **creator**: Author/creator name

#### Generation Parameters:
- **model_name**: Name of the model used
- **positive_prompt**: Positive generation prompt
- **negative_prompt**: Negative generation prompt
- **seed**: Generation seed
- **steps**: Number of generation steps
- **cfg_scale**: CFG scale value
- **sampler**: Sampler name
- **scheduler**: Scheduler name

#### File Handling:
- **custom_output_directory**: Path to custom save location
- **include_datetime**: Add date/time to filenames (boolean)
- **include_project**: Add project name to filenames (boolean)

#### Workflow Options:
- **workflow_data**: Explicit workflow JSON data
- **enable_metadata**: Toggle metadata writing (boolean)
- **metadata_targets**: Comma-separated list of targets (embedded,xmp,txt)
- **custom_metadata**: JSON string with custom metadata
- **auto_capture_workflow**: Attempt to capture workflow automatically (boolean)
- **workflow_id**: Specific workflow ID to use

## Technical Details

### Metadata Standards:
- **XMP**: Adobe's Extensible Metadata Platform for standardized metadata
- **IPTC**: International Press Telecommunications Council standard
- **EXIF**: Exchangeable Image File Format for camera data

### Storage Locations:
- **Embedded**: Metadata stored directly inside image files
- **XMP Sidecar**: Companion XML files with `.xmp` extension
- **Text Files**: Human-readable text files with `.txt` extension
- **Database**: Optional storage in SQLite database (if configured)

### Workflow Capture Methods:
1. **Direct Input**: From workflow_data parameter (highest priority)
2. **ComfyUI Context**: Automatically captured from current execution (when enabled)
3. **Active Node Analysis**: Identifies which nodes contributed to the final output

## Troubleshooting

### Common Issues:

#### Metadata Not Appearing:
- Ensure `enable_metadata` is set to True
- Check that appropriate targets are included in `metadata_targets`
- Verify you have writing permissions for the output location

#### Workflow Data Missing:
- Enable `auto_capture_workflow`
- Check ComfyUI version compatibility
- Try providing explicit workflow data via connection

#### Invalid Output Directory:
- Ensure custom directory path exists or can be created
- Check permissions for the specified location
- Use absolute paths to avoid ambiguity

## Advanced Usage

### Custom Metadata Format:
You can provide additional custom metadata via JSON. Example format:
```json
{
  "basic": {
    "rating": 5
  },
  "analysis": {
    "technical": {
      "quality_score": 0.95
    }
  }
}
```

### Integration with Other Nodes:
- Connect text nodes to metadata fields
- Use output from analysis nodes as input to custom_metadata
- Chain with other metadata-aware nodes for complete workflows

### Batch Processing:
When processing batched images, the node will add sequential numbering to filenames automatically and apply the same metadata to each image in the batch.
