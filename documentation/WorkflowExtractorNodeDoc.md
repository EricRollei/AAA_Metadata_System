# Workflow Extractor Node Documentation

## Overview

The Workflow Extractor Node is a lightweight utility node that extracts workflow metadata from existing images created with ComfyUI or other AI generation tools. It provides a simpler alternative to the full Workflow Toolkit when you only need to extract metadata without visualization or analysis features.

## Key Features

- **Simple Extraction**: Extracts embedded workflow data from PNG files with minimal configuration
- **JSON Output**: Returns extracted metadata as formatted JSON
- **Metadata Compatible**: Uses the same metadata processor as the full Workflow Toolkit
- **Low Resource Usage**: Lightweight alternative when only extraction is needed

## Input Parameters

### Required Inputs

- **image_path**: Path to the image file containing the workflow data to extract

### Optional Inputs

- **debug_logging**: Enable detailed debug information during extraction process

## Output

- **metadata_json**: Extracted workflow metadata as a formatted JSON string

## Usage Examples

### Basic Workflow Extraction

Connect a filepath to an image generated with ComfyUI. The node will extract the embedded workflow data and return it as formatted JSON.

### Debug Mode

Enable debug_logging to see detailed information about the extraction process, which is helpful when troubleshooting extraction issues.

## Differences from Workflow Toolkit

The Workflow Extractor Node is a simplified version of the full Workflow Toolkit with these key differences:

1. **Focus**: Only extracts data, doesn't analyze or visualize
2. **Simplicity**: Minimal configuration options
3. **Output**: Returns only raw JSON data
4. **Resource Usage**: Lower memory and processing requirements

## Technical Notes

- Uses the same core WorkflowMetadataProcessor as the full Workflow Toolkit
- Returns properly formatted JSON with indentation for readability
- Compatible with images from ComfyUI and other supported generators
- Does not modify the original image file

## Integration with Other Nodes

The Workflow Extractor Node works well with:
- Text nodes for displaying the extracted JSON
- Save Text nodes for writing the JSON to a file
- Custom script nodes that need to process workflow metadata

## Use Cases

- Quickly check if an image contains workflow data
- Extract workflow data for external processing
- Build custom workflow analysis pipelines
- Batch extract metadata from multiple images
- Debug workflow embedding in other nodes

This node provides a simple, focused way to extract workflow data from images for further processing or reference.