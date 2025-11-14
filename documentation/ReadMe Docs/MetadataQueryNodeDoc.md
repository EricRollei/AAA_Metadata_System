# Metadata Query Node Documentation

## Overview

The Metadata Query Node is a specialized tool for extracting specific information from image metadata. It allows precise querying of metadata using different query methods, making it easy to retrieve specific values or entire sections of metadata from images.

## Key Features

- **Multiple Query Methods**: Simple dot notation, JSONPath expressions, or regular expressions
- **Source Flexibility**: Query across all metadata storage methods (embedded, XMP, text, database)
- **Source Prioritization**: Configure primary source with optional fallbacks
- **Formatted Output**: Return nicely formatted results for readability
- **Performance Optimization**: Caching for repeated queries of the same file
- **Comprehensive Extraction**: Return specific values or entire metadata structures

## Input Parameters

### Required Inputs

- **input_filepath**: Path to the image file containing metadata to query
- **query_mode**: Method to use for querying:
  - **simple**: Dot notation path (e.g., "ai_info.generation.model")
  - **jsonpath**: Advanced JSONPath expressions for complex queries
  - **regex**: Regular expressions for pattern matching across the entire metadata structure
- **query**: Query string according to the selected mode
- **default_value**: Value to return if the query doesn't match anything

### Optional Inputs

#### Data Source Options
- **source**: Primary metadata source to query:
  - **auto**: Automatically try all sources
  - **embedded**: Use embedded metadata inside the image file
  - **xmp**: Use XMP sidecar files
  - **txt**: Use text files
  - **db**: Use database (if configured)
- **fallback_sources**: Try other sources if the primary source doesn't contain the requested data

#### Output Options
- **return_full**: Return the entire metadata structure instead of just the query result
- **format_output**: Format JSON output with indentation for readability
- **debug_logging**: Enable detailed debug information during query

## Output

- **result**: String containing the query result or formatted JSON
- **metadata**: Complete metadata dictionary for use in other nodes

## Query Methods Explained

### Simple Mode

The simple mode uses dot notation to navigate through nested metadata structures:

```
ai_info.generation.model
```

This would extract the model name from standard metadata structure. You can also access array elements using bracket notation:

```
ai_info.loras[0].name
```

This would extract the name of the first LoRA in the list.

### JSONPath Mode

The JSONPath mode provides more powerful querying capabilities using the JSONPath standard:

```
$.ai_info.generation[?(@.sampler=='euler_a')].steps
```

This would find all generation entries using the 'euler_a' sampler and return their steps values.

### Regex Mode

The regex mode flattens the metadata structure and finds keys matching the pattern:

```
generation\.seed
```

This would find all metadata paths containing "generation.seed" and return their values.

## Usage Examples

### Extract Model Name

Query Mode: simple  
Query: ai_info.generation.model  
Default Value: unknown

This extracts the name of the model used to generate the image.

### Find All LoRA Names

Query Mode: jsonpath  
Query: $..loras[*].name  
Default Value: []

This extracts the names of all LoRAs used in the image generation.

### Extract All Prompts

Query Mode: regex  
Query: .*prompt.*  
Default Value: ""

This finds all metadata fields containing "prompt" in their path and returns their values.

### Get Complete Metadata

Set return_full to True with any query to get the entire metadata structure as JSON.

## Technical Notes

- JSONPath queries require the 'jsonpath-ng' package
- Regex queries use Python's re module with standard regex syntax
- The node optimizes performance by caching the last queried file's metadata
- Source prioritization follows the order: embedded → XMP → text → database
- Complex query results are automatically converted to JSON strings

## Integration with Other Nodes

This query node pairs well with:
- Text nodes for displaying extracted information
- Workflow analysis nodes that need specific metadata fields
- Conditional execution nodes for metadata-based branching
- Text overlay nodes for adding metadata to images

## Troubleshooting

- If queries return default values, check that the file contains the expected metadata
- For complex JSONPath or regex queries, use debug_logging to see the complete metadata structure
- Some metadata sources may structure data differently; try the "auto" source with fallbacks enabled
- For empty or unexpected results, verify the query syntax matches the actual metadata structure

The Metadata Query Node provides a flexible way to extract specific information from image metadata, making it easier to use this information in your workflows.