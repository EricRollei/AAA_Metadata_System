# API Reference

This document provides a comprehensive API reference for the Metadata System for ComfyUI.

## Table of Contents

- [MetadataService](#metadataservice)
- [Handlers](#handlers)
  - [BaseHandler](#basehandler)
  - [EmbeddedMetadataHandler](#embeddedmetadatahandler)
  - [XMPSidecarHandler](#xmpsidecarhandler)
  - [TxtFileHandler](#txtfilehandler)
  - [DatabaseHandler](#databasehandler)
- [Utilities](#utilities)
  - [FormatHandler](#formathandler)
  - [NamespaceManager](#namespacemanager)
  - [ErrorRecovery](#errorrecovery)
  - [XMLTools](#xmltools)
  - [WorkflowMetadataProcessor](#workflowmetadataprocessor)

## MetadataService

The main interface for all metadata operations.

### Constructor

```python
MetadataService(debug=False, human_readable_text=True)
```

- `debug` (bool): Whether to enable debug logging
- `human_readable_text` (bool): Whether to use human-readable text format

### Methods

#### write_metadata

```python
write_metadata(filepath, metadata, targets=None) -> Dict[str, bool]
```

Writes metadata to specified targets.

- `filepath` (str): Path to the image file
- `metadata` (dict): Metadata to write
- `targets` (list, optional): List of targets ('embedded', 'xmp', 'txt', 'db')
- Returns: Dictionary mapping targets to success status

#### read_metadata

```python
read_metadata(filepath, source='embedded', fallback=True) -> Dict[str, Any]
```

Reads metadata from specified source.

- `filepath` (str): Path to the image file
- `source` (str): Source to read from ('embedded', 'xmp', 'txt', 'db')
- `fallback` (bool): Whether to try other sources if primary fails
- Returns: Metadata dictionary

#### merge_metadata

```python
merge_metadata(filepath, metadata, targets=None) -> Dict[str, bool]
```

Merges new metadata with existing metadata and writes the result.

- `filepath` (str): Path to the image file
- `metadata` (dict): New metadata to merge
- `targets` (list, optional): List of targets to update
- Returns: Dictionary mapping targets to success status

#### set_resource_identifier

```python
set_resource_identifier(resource_uri) -> None
```

Sets resource identifier for all handlers.

- `resource_uri` (str): Resource identifier for XMP

#### set_text_format

```python
set_text_format(human_readable) -> None
```

Sets the text output format.

- `human_readable` (bool): Whether to use human-readable format

#### get_handler_for_format

```python
get_handler_for_format(filepath) -> Tuple[str, BaseHandler]
```

Gets appropriate handler for file format.

- `filepath` (str): Path to the file
- Returns: Tuple of (handler_type, handler)

#### cleanup

```python
cleanup() -> None
```

Cleans up resources used by handlers.

## Handlers

### BaseHandler

Abstract base class for all handlers.

#### Constructor

```python
BaseHandler(debug=False)
```

- `debug` (bool): Whether to enable debug logging

#### Methods

##### write_metadata

```python
write_metadata(filepath, metadata) -> bool
```

Abstract method to write metadata to a file.

- `filepath` (str): Path to the file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### read_metadata

```python
read_metadata(filepath) -> Dict[str, Any]
```

Abstract method to read metadata from a file.

- `filepath` (str): Path to the file
- Returns: Metadata dictionary

##### log

```python
log(message, level="INFO", error=None) -> None
```

Logs a message with appropriate level.

- `message` (str): The message to log
- `level` (str): Log level (INFO, DEBUG, WARNING, ERROR)
- `error` (Exception, optional): Optional exception to include in log

##### get_timestamp

```python
get_timestamp() -> str
```

Gets current timestamp in ISO 8601 format.

- Returns: Timestamp string

##### cleanup

```python
cleanup() -> None
```

Cleans up any resources used by the handler.

##### _safely_execute

```python
_safely_execute(operation_name, callback, *args, **kwargs) -> Any
```

Executes operation with proper locking and error handling.

- `operation_name` (str): Name of the operation for logging
- `callback` (callable): Function to execute
- `*args`, `**kwargs`: Arguments to pass to the callback
- Returns: Result from the callback or None on error

### EmbeddedMetadataHandler

Handler for embedded metadata in image files.

#### Constructor

```python
EmbeddedMetadataHandler(debug=False)
```

- `debug` (bool): Whether to enable debug logging

#### Methods

##### write_metadata

```python
write_metadata(filepath, metadata) -> bool
```

Writes metadata to image file.

- `filepath` (str): Path to the image file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### read_metadata

```python
read_metadata(filepath) -> Dict[str, Any]
```

Reads metadata from image file.

- `filepath` (str): Path to the image file
- Returns: Metadata dictionary

##### set_resource_identifier

```python
set_resource_identifier(about_uri) -> None
```

Sets the resource identifier for XMP metadata.

- `about_uri` (str): The resource URI to use

### XMPSidecarHandler

Handler for XMP sidecar files.

#### Constructor

```python
XMPSidecarHandler(debug=False)
```

- `debug` (bool): Whether to enable debug logging

#### Methods

##### write_metadata

```python
write_metadata(filepath, metadata) -> bool
```

Writes metadata to XMP sidecar file.

- `filepath` (str): Path to the original file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### read_metadata

```python
read_metadata(filepath) -> Dict[str, Any]
```

Reads metadata from XMP sidecar file.

- `filepath` (str): Path to the original file
- Returns: Metadata dictionary

##### set_resource_identifier

```python
set_resource_identifier(about_uri) -> None
```

Sets the resource identifier for XMP metadata.

- `about_uri` (str): The resource URI to use

### TxtFileHandler

Handler for text file metadata.

#### Constructor

```python
TxtFileHandler(debug=False, human_readable=False)
```

- `debug` (bool): Whether to enable debug logging
- `human_readable` (bool): Whether to use human-readable format by default

#### Methods

##### write_metadata

```python
write_metadata(filepath, metadata) -> bool
```

Writes metadata to text file using appropriate format.

- `filepath` (str): Path to the original file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### read_metadata

```python
read_metadata(filepath) -> Dict[str, Any]
```

Reads metadata from text file.

- `filepath` (str): Path to the original file
- Returns: Metadata dictionary

##### append_metadata

```python
append_metadata(filepath, metadata) -> bool
```

Appends new metadata to existing text file.

- `filepath` (str): Path to the original file
- `metadata` (dict): Metadata to append
- Returns: Success status

##### write_formatted_text

```python
write_formatted_text(filepath, metadata) -> bool
```

Writes metadata to text file with markdown-style formatting.

- `filepath` (str): Path to the original file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### write_human_readable_text

```python
write_human_readable_text(filepath, metadata) -> bool
```

Writes metadata to text file in human-readable format.

- `filepath` (str): Path to the original file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### set_output_format

```python
set_output_format(human_readable) -> None
```

Sets the output format.

- `human_readable` (bool): Whether to use human-readable format

### DatabaseHandler

Handler for database storage of metadata.

#### Constructor

```python
DatabaseHandler(debug=False, db_path=None)
```

- `debug` (bool): Whether to enable debug logging
- `db_path` (str, optional): Path to the database file

#### Methods

##### write_metadata

```python
write_metadata(filepath, metadata) -> bool
```

Writes metadata to database.

- `filepath` (str): Path to the file
- `metadata` (dict): Metadata to write
- Returns: Success status

##### read_metadata

```python
read_metadata(filepath) -> Dict[str, Any]
```

Reads metadata from database.

- `filepath` (str): Path to the file
- Returns: Metadata dictionary

##### search_images

```python
search_images(query) -> List[Dict[str, Any]]
```

Searches images based on query criteria.

- `query` (dict): Dictionary of search criteria
- Returns: List of matching image records

##### batch_operation

```python
batch_operation(operation, filepaths, data=None) -> Dict[str, bool]
```

Performs batch operation on multiple files.

- `operation` (str): Operation type ('read', 'write', 'delete')
- `filepaths` (list): List of file paths
- `data` (dict, optional): Data for write operation
- Returns: Status for each file

## Utilities

### FormatHandler

Utility for detecting file formats and capabilities.

#### Methods

##### get_file_info

```python
@staticmethod
get_file_info(filepath) -> Dict[str, Any]
```

Gets format information for a file.

- `filepath` (str): Path to the file
- Returns: Dictionary with format information

### NamespaceManager

Manages XMP namespaces.

#### Attributes

- `NAMESPACES` (dict): Dictionary mapping namespace prefixes to URIs

#### Methods

##### register_with_pyexiv2

```python
@staticmethod
register_with_pyexiv2(debug=False) -> bool
```

Registers namespaces with PyExiv2.

- `debug` (bool): Whether to enable debug logging
- Returns: Success status

##### create_exiftool_config

```python
@staticmethod
create_exiftool_config() -> str
```

Creates ExifTool configuration file.

- Returns: Path to configuration file

### ErrorRecovery

Provides recovery strategies for errors.

#### Methods

##### recover_write_error

```python
@staticmethod
recover_write_error(handler, context) -> bool
```

Recovers from write error.

- `handler` (BaseHandler): Handler that encountered the error
- `context` (dict): Error context
- Returns: Success status

##### recover_read_error

```python
@staticmethod
recover_read_error(handler, context) -> Dict[str, Any]
```

Recovers from read error.

- `handler` (BaseHandler): Handler that encountered the error
- `context` (dict): Error context
- Returns: Recovered metadata or empty dictionary

### XMLTools

Utilities for XML handling.

#### Methods

##### xmp_to_dict

```python
@staticmethod
xmp_to_dict(xmp_content) -> Dict[str, Any]
```

Parses XMP content to dictionary.

- `xmp_content` (str): XMP content
- Returns: Dictionary representation

##### indent_xml

```python
@staticmethod
indent_xml(elem, level=0) -> None
```

Adds proper indentation to XML for readability.

- `elem` (Element): XML element
- `level` (int): Indentation level

##### is_rdf_container

```python
@staticmethod
is_rdf_container(key) -> Optional[str]
```

Determines if a key should use a specific RDF container.

- `key` (str): Key name
- Returns: Container type ('Bag', 'Seq', 'Alt') or None

##### create_xmp_wrapper

```python
@staticmethod
create_xmp_wrapper() -> Tuple[str, str]
```

Creates start and end wrappers for XMP packet.

- Returns: Tuple of (start_wrapper, end_wrapper)

### WorkflowMetadataProcessor

Processes ComfyUI workflow data.

#### Constructor

```python
WorkflowMetadataProcessor(debug=False)
```

- `debug` (bool): Whether to enable debug logging

#### Methods

##### extract_workflow_metadata

```python
extract_workflow_metadata(workflow_data) -> Dict[str, Any]
```

Extracts metadata from workflow data.

- `workflow_data` (dict): Workflow data
- Returns: Extracted metadata

##### extract_generation_parameters

```python
extract_generation_parameters(workflow_data) -> Dict[str, Any]
```

Extracts generation parameters from workflow data.

- `workflow_data` (dict): Workflow data
- Returns: Generation parameters

##### get_model_info

```python
get_model_info(workflow_data) -> Dict[str, Any]
```

Gets model information from workflow data.

- `workflow_data` (dict): Workflow data
- Returns: Model information

##### get_sampler_info

```python
get_sampler_info(workflow_data) -> Dict[str, Any]
```

Gets sampler information from workflow data.

- `workflow_data` (dict): Workflow data
- Returns: Sampler information