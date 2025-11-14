# Workflow Toolkit Node Documentation

## Overview

The Workflow Toolkit is a powerful node for ComfyUI that extracts, analyzes, and visualizes workflows from AI-generated images. It helps you understand how images were created, identify their components, and re-use workflows across projects.

## Key Features

- **Workflow Extraction**: Extract embedded workflow data from PNG files created with ComfyUI and other AI generators
- **Advanced Analysis**: Analyze workflows to identify models, samplers, prompts, and other generation parameters
- **Visual Representation**: Generate visual graphs of ComfyUI workflows with color-coded nodes
- **Multiple Export Formats**: Output as JSON, text descriptions, or visual graphs
- **Metadata Integration**: Store workflow data in image metadata for future reference
- **Source Recognition**: Automatically detect the AI system that created the image

## Input Parameters

### Required Inputs

- **input_filepath**: Path to the image file containing the workflow data
- **operation_mode**: The mode of operation:
  - **extract**: Extract and store workflow data from the image
  - **analyze**: Generate detailed analysis of workflow components 
  - **visualize**: Create visual representation of the workflow

### Optional Inputs

#### Input Sources
- **image**: Optional image tensor to extract workflow from instead of file

#### Visualization Options
- **visualization_type**: Type of visualization to create:
  - **graph**: Visual graph diagram of workflow nodes (requires graphviz)
  - **text**: Human-readable text description
  - **json**: Structured JSON representation
- **detailed_output**: Include additional details in the output

#### Extraction Options
- **extract_from_tensor**: Try to extract workflow from image tensor

#### Output Options
- **output_directory**: Where to save visualization files
- **write_to_xmp**: Write extracted metadata to XMP sidecar file
- **embed_metadata**: Embed metadata in the image file itself
- **write_text_file**: Write metadata to separate text file
- **write_to_database**: Store metadata in database (if configured)
- **overwrite_existing**: Overwrite existing metadata (otherwise merge)
- **debug_logging**: Enable detailed debug logging

## Output

- **result**: Text result or path to output file
- **workflow_data**: Raw workflow data dictionary
- **structured_analysis**: Structured workflow analysis data
- **image**: Original or placeholder image tensor

## Detailed Functionality

### Extraction Mode

In extraction mode, the node:
1. Extracts workflow data from the provided image
2. Structures it according to metadata standards
3. Stores it in selected targets (XMP, embedded, text file, database)

This mode is useful for preserving workflow data for future reference or sharing.

### Analysis Mode

In analysis mode, the node:
1. Extracts and processes workflow data
2. Identifies key components (models, samplers, prompts, etc.)
3. Creates a structured summary and textual analysis

The analysis provides insights about how the image was created, showing:
- Base model (checkpoint) used
- Sampler settings and parameters
- Prompt and negative prompt text
- LoRA models applied
- Other workflow-specific information

### Visualization Mode

In visualization mode, the node:
1. Extracts workflow data
2. Creates a visual representation in the selected format
3. Saves it to the specified output directory

#### Graph Visualization

Graph visualization creates a color-coded diagram of the workflow:
- Green nodes: Model checkpoints
- Red nodes: Samplers
- Blue nodes: VAE components
- Yellow nodes: Text prompts
- Orange nodes: Output/save nodes
- Purple nodes: LoRA components
- Gray nodes: Other node types

This provides an intuitive view of how the workflow is structured.

## Usage Examples

### Extracting Workflow from an Image

Connect a filepath to an image generated with ComfyUI, set mode to "extract", and enable the appropriate storage targets (XMP, embedded, etc.). This will extract and save the workflow data for future reference.

### Analyzing an AI-Generated Image

Connect a filepath or image tensor, set mode to "analyze" and detailed_output to True. This will provide a comprehensive breakdown of the generation parameters used to create the image.

### Creating a Workflow Visualization

Connect a filepath to a ComfyUI-generated image, set mode to "visualize", visualization_type to "graph", and specify an output directory. This will generate a color-coded graph of the workflow.

### Storing Workflow in Metadata

Connect an image, set mode to "extract", enable write_to_xmp and embed_metadata. This embeds the workflow into the image's metadata for easy distribution and later extraction.

## Technical Notes

- Graph visualization requires graphviz to be installed
- For ComfyUI images, the node can extract detailed node connections and parameters
- For other generators (A1111, etc.), extraction is more basic but still provides key parameters
- Extracted workflow data is compatible with the metadata system for proper storage
- The node caches workflow data to improve performance with repeated operations

## Integration with Other Nodes

The Workflow Toolkit node works well with:
- Eric's Metadata Save Image node for embedding workflows in new images
- Image Duplicate Finder for organizing workflows
- Text Overlay node for adding workflow information to images

## Troubleshooting

- If extraction fails, check that the image actually contains embedded workflow data
- For graph visualization issues, ensure graphviz is installed
- If metadata writing fails, check file permissions and paths
- Enable debug_logging for detailed information about processing

This node provides essential tools for understanding, documenting, and sharing AI image generation workflows, making it easier to reproduce results and learn from others' techniques.