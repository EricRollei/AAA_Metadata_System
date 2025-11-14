# Metadata System Architecture and Handler Documentation

## System Overview

The Metadata System is a comprehensive framework for reading, writing, and managing metadata across multiple storage formats in a consistent and extensible way. It uses a service-based architecture that abstracts the complexity of different metadata formats and storage mechanisms behind a unified API.

### Architecture

The system is built on a modular architecture with the following components:

1. **Central Service Layer** - Coordinates operations across different handlers
2. **Specialized Handlers** - Individual components for different storage formats
3. **Utility Services** - Shared functionality like namespace management and format detection
4. **Error Recovery** - Strategies for handling failures gracefully

The architecture follows a façade pattern, where the MetadataService acts as the main interface, while specialized handlers manage the specifics of each storage format.

### Data Flow

1. Client code interacts with MetadataService
2. Service selects appropriate handler(s) based on requested operation and file format
3. Handler processes the metadata operation (read/write)
4. Results/errors are returned through the service layer
5. In case of failures, error recovery mechanisms attempt to salvage operations

## Handler Classes

### BaseHandler (base.py)

The foundation of the handler system, providing common functionality for all specialized handlers.

**Key features:**
- Thread-safe operations with proper locking
- Consistent logging infrastructure
- Error tracking and management
- Common utility methods for path handling
- Context manager support for resource cleanup
- Abstract methods enforcing a consistent interface

BaseHandler serves as an abstract class that all concrete handlers must extend, ensuring consistency in the metadata handling API.

### EmbeddedMetadataHandler (embedded.py)

Responsible for directly embedding metadata into image files using various libraries.

**Key features:**
- Multi-library support (PyExiv2 and ExifTool)
- Format-specific processing for different image types
- Support for XMP, IPTC, and EXIF standards
- Intelligent format detection and library selection
- Workflow data preservation
- Special handling for PNG and WebP formats
- Complex metadata structure mapping

The EmbeddedMetadataHandler intelligently selects the appropriate method for each file format, preserving existing metadata when possible and handling edge cases like workflow data in PNG files.

### XMPSidecarHandler (xmp.py)

Creates and manages XMP sidecar files that store metadata separately from the original images.

**Key features:**
- MWG-compliant XMP creation
- Proper XML namespace handling
- Support for language alternatives
- Structured metadata organization
- Face and region metadata handling
- Smart merging of existing and new metadata
- Proper XMP packet wrapping

This handler follows Adobe's XMP specification closely, ensuring compatibility with industry-standard tools while organizing metadata in a structured, searchable format.

### DatabaseHandler (db.py)

Provides persistent storage of metadata in an SQLite database for advanced querying capabilities.

**Key features:**
- Relational schema for metadata types
- Transaction support for data integrity
- Query capabilities for finding images by metadata
- Support for scores and measurements
- Region and face data storage
- Classification and keyword indexing
- Batch operations support

The DatabaseHandler excels at scenarios requiring searchability and metadata-based organization, with a schema designed for flexibility and performance.

## Utility Components

### NamespaceManager (namespace.py)

Centralizes XML namespace management across the system.

**Key features:**
- Registration with PyExiv2 and other libraries
- Consistent namespace URIs across the system
- Support for standard and custom namespaces
- ExifTool configuration generation

### FormatHandler (format_detect.py)

Provides intelligence around file format detection and handling.

**Key features:**
- Format categorization (standard, raw, layered)
- Library compatibility detection
- Handler selection logic

### ErrorRecovery (error_handling.py)

Implements strategies for recovering from metadata operation failures.

**Key features:**
- Format-specific recovery approaches
- Alternative storage fallbacks
- Cross-format conversion tools
- Temporary file management

### XML Tools (xml_tools.py)

Utilities for working with XML and XMP structures.

**Key features:**
- XMP packet creation and parsing
- Pretty printing and indentation
- Conversion between XMP and dictionary structures

## Integration Patterns

The system is designed to be integrated into custom nodes through a simple, consistent pattern:

1. Import the MetadataService
2. Initialize the service in the node constructor
3. Configure appropriate handler options
4. Call read/write methods as needed

The service layer handles all the complexity of selecting appropriate handlers, managing errors, and ensuring consistent behavior across different storage formats.

## Handler Selection Logic

When writing or reading metadata, the system uses the following logic to select appropriate handlers:

1. For embedded metadata:
   - PyExiv2 for standard formats (JPEG, TIFF, etc.)
   - ExifTool for RAW and complex formats
   - Special handling for PNG and WebP

2. For XMP sidecars:
   - Always available regardless of format
   - Creates properly formatted XMP files
   - Handles complex structures like regions

3. For database storage:
   - Available for all formats
   - Offers advanced querying capabilities
   - Provides indexing and search

The system will attempt to use multiple handlers as requested by the client code, enabling data redundancy and format-specific optimizations.

## Performance Considerations

- Thread-safe operations for concurrent workflows
- Resource cleanup through context managers
- Efficient metadata representation
- Lazy loading where appropriate
- Transaction support in database operations
- XML optimization for large structures

This architecture provides a robust foundation for metadata handling that balances flexibility, standards compliance, and performance while abstracting the complexities of different storage formats from client code.
