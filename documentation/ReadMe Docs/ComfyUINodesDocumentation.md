# ComfyUI Nodes Documentation

This document describes the ComfyUI nodes provided by the Metadata System, their inputs, outputs, and usage.

## Metadata Save Image Node

The `eric_metadata_save_image` node saves images with metadata embedded and in sidecar files.

![Metadata Save Image Node](docs/images/save_image_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The image(s) to save |
| `metadata` | METADATA | Optional metadata to include (from other nodes) |
| `workflow_data` | JSON | Optional workflow data to include |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `save_path` | STRING | "outputs" | Directory to save images to |
| `filename_prefix` | STRING | "" | Prefix for generated filenames |
| `filename_pattern` | STRING | "{prefix}_{index}_{seed}" | Pattern for generating filenames |
| `filename_number_padding` | INT | 4 | Number of digits for sequential numbering |
| `filename_number_start` | INT | 1 | Starting number for sequential filenames |
| `overwrite_existing` | BOOLEAN | False | Whether to overwrite existing files |
| `save_format` | COMBO | "png" | Image format to save as (png, jpg, webp) |
| `quality` | INT | 95 | Quality setting for jpg/webp |
| `compress_level` | INT | 4 | Compression level for png |
| `title` | STRING | "" | Image title |
| `description` | STRING | "" | Image description |
| `keywords` | STRING | "" | Comma-separated keywords |
| `save_metadata_to` | COMBO | "embedded,xmp,txt,db" | Where to save metadata |
| `human_readable_text` | BOOLEAN | True | Whether to use human-readable text format |
| `enable_workflow_capture` | BOOLEAN | True | Whether to capture workflow |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `images` | IMAGE | The saved image(s) |
| `metadata` | METADATA | The metadata that was saved |
| `filename` | STRING | The full path of the saved file |

### Usage Example

1. Connect your image generation output to the `images` input
2. Connect a PNGInfo node to the `workflow_data` input if you want to include workflow data
3. Set the save path and filename parameters
4. Run the workflow to save the image with metadata embedded and in sidecar files

## Metadata Entry Node

The `eric_metadata_entry_v2` node allows adding custom metadata to be used with other metadata nodes.

![Metadata Entry Node](docs/images/metadata_entry_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `metadata` | METADATA | Optional metadata to extend (from other nodes) |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | STRING | "" | Image title |
| `description` | STRING | "" | Image description |
| `keywords` | STRING | "" | Comma-separated keywords |
| `rating` | INT | 0 | Rating (0-5) |
| `creator` | STRING | "" | Creator name |
| `rights` | STRING | "" | Copyright information |
| `custom_field_name` | STRING | "" | Name of a custom field |
| `custom_field_value` | STRING | "" | Value for the custom field |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `metadata` | METADATA | The combined metadata |

### Usage Example

1. Create a Metadata Entry node and fill in the desired fields
2. Connect the `metadata` output to a Metadata Save Image node
3. Run the workflow to save the image with your custom metadata

## Metadata Query Node

The `eric_metadata_query_node_v3` node allows querying and filtering metadata.

![Metadata Query Node](docs/images/metadata_query_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The image(s) to query metadata from |
| `metadata` | METADATA | Optional metadata to query (otherwise read from image) |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query_type` | COMBO | "extract" | Type of query (extract, filter, check) |
| `field_path` | STRING | "basic.title" | Path to the metadata field to query |
| `comparison` | COMBO | "equals" | Comparison operator (equals, contains, greater_than, etc.) |
| `value` | STRING | "" | Value to compare against |
| `extract_as_json` | BOOLEAN | False | Whether to extract result as JSON |
| `fallback_value` | STRING | "" | Value to return if field not found |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `result` | STRING | Query result |
| `metadata` | METADATA | Passed-through or filtered metadata |
| `images` | IMAGE | Passed-through or filtered images |
| `condition_met` | BOOLEAN | Whether condition was met |

### Usage Example

1. Connect an image input to the `images` input
2. Set the query parameters (e.g., extract "ai_info.generation.prompt")
3. Connect the outputs to other nodes that need the query results
4. Use the `condition_met` output to conditional nodes for filtering workflows

## Workflow Extractor Node

The `eric_workflow_extractor` node extracts workflow data from images.

![Workflow Extractor Node](docs/images/workflow_extractor_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The image(s) to extract workflow data from |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extraction_mode` | COMBO | "auto" | How to extract workflow data (auto, png_info, embedded, xmp) |
| `include_basic_metadata` | BOOLEAN | True | Whether to include basic metadata |
| `parse_workflow` | BOOLEAN | True | Whether to parse workflow into usable format |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `workflow_data` | JSON | Extracted workflow data |
| `metadata` | METADATA | Full metadata dictionary |
| `images` | IMAGE | Passed-through image(s) |

### Usage Example

1. Connect an image with embedded workflow data to the `images` input
2. Set the extraction parameters
3. Connect the `workflow_data` output to nodes that can use workflow JSON
4. Connect the `metadata` output to other metadata-aware nodes

## Metadata Consolidator Node

The `eric_metadata_consolidator_node_v2` node merges metadata from multiple sources.

![Metadata Consolidator Node](docs/images/metadata_consolidator_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `metadata_1` | METADATA | First metadata source |
| `metadata_2` | METADATA | Second metadata source |
| `metadata_3` | METADATA | Third metadata source (optional) |
| `metadata_4` | METADATA | Fourth metadata source (optional) |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `merge_strategy` | COMBO | "smart" | How to merge metadata (smart, override, append) |
| `favor_source` | COMBO | "latest" | Which source to favor on conflict (latest, first, second, etc.) |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `metadata` | METADATA | Merged metadata |

### Usage Example

1. Connect various metadata sources to the inputs
2. Choose the merge strategy and conflict resolution method
3. Connect the merged metadata to other nodes like Metadata Save Image

## Metadata Debugger Node

The `eric_metadata_debugger_v2` node displays metadata for debugging purposes.

![Metadata Debugger Node](docs/images/metadata_debugger_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The image(s) to debug metadata from |
| `metadata` | METADATA | Optional metadata to debug (otherwise read from image) |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `display_mode` | COMBO | "structured" | How to display metadata (structured, flat, raw) |
| `section_filter` | STRING | "" | Optional filter to show only specific sections |
| `output_to_console` | BOOLEAN | False | Whether to output to console for logging |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `metadata_text` | STRING | Formatted metadata text |
| `images` | IMAGE | Passed-through image(s) |
| `metadata` | METADATA | Passed-through metadata |

### Usage Example

1. Connect an image input to the `images` input
2. Optionally connect metadata from another node to the `metadata` input
3. Set the display mode and any filters
4. View the formatted metadata in the node preview or console

## Metadata Filter Node

The `eric_metadata_filter_v2` node filters images based on metadata criteria.

![Metadata Filter Node](docs/images/metadata_filter_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The image(s) to filter |
| `metadata` | METADATA | Optional metadata to use for filtering |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_type` | COMBO | "basic" | Type of filter (basic, score, keyword, ai) |
| `field_path` | STRING | "basic.title" | Path to the metadata field to filter on |
| `comparison` | COMBO | "contains" | Comparison operator (contains, equals, greater_than, etc.) |
| `value` | STRING | "" | Value to compare against |
| `invert` | BOOLEAN | False | Whether to invert the filter (exclude matches) |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `filtered_images` | IMAGE | Images that passed the filter |
| `rejected_images` | IMAGE | Images that didn't pass the filter |
| `filtered_metadata` | METADATA | Metadata for filtered images |

### Usage Example

1. Connect a batch of images to the `images` input
2. Set up your filter criteria (e.g., filter where "analysis.aesthetic.overall" > 7.0)
3. Connect the filtered outputs to different processing chains
4. Use multiple filter nodes in sequence for complex filtering rules

## PNG Info Diagnostic Node

The `eric_png_info_diagnostic_node_v3` node analyzes and displays PNG metadata.

![PNG Info Diagnostic Node](docs/images/png_info_node.png)

### Inputs

| Input | Type | Description |
|-------|------|-------------|
| `images` | IMAGE | The PNG image(s) to analyze |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `display_mode` | COMBO | "compact" | How to display the info (compact, full, parameters_only) |
| `extract_workflow` | BOOLEAN | True | Whether to extract full workflow JSON |
| `extract_parameters` | BOOLEAN | True | Whether to extract generation parameters |
| `show_preview` | BOOLEAN | True | Whether to show image preview |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `png_info_text` | STRING | Formatted PNG info text |
| `parameters` | STRING | Extracted generation parameters |
| `workflow` | JSON | Extracted workflow data |
| `images` | IMAGE | Passed-through image(s) |

### Usage Example

1. Connect a PNG image to the `images` input
2. Set the display options
3. View the formatted PNG info in the node preview
4. Connect the `workflow` output to nodes that can use workflow JSON