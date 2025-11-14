# Metadata Implementation Plan

## Strategic Overview

### Vision
To create a comprehensive metadata management system for AI-generated images that captures, organizes, and stores critical workflow information in a structured, searchable format compatible with industry standards while maintaining flexibility for future expansion.

### Core Goals
1. Extract and organize relevant metadata from ComfyUI workflows
2. Structure metadata in a logical, hierarchical format reflecting natural AI workflow relationships
3. Maintain compatibility with industry standards (Adobe XMP, etc.)
4. Provide flexibility for adding new metadata fields as needed
5. Eliminate redundancy and duplication in stored metadata
6. Leverage existing handler code for different storage mechanisms

## Architecture Design

### 1. Metadata Structure
We will adopt a hierarchical structure with clear organization around functional areas:

```
metadata
├── basic
│   ├── title
│   ├── description
│   ├── keywords
│   ├── creator
│   └── copyright
├── ai_info
│   ├── generation
│   │   ├── model
│   │   ├── sampler
│   │   ├── scheduler
│   │   ├── steps
│   │   ├── cfg_scale
│   │   ├── seed
│   │   ├── prompt
│   │   ├── negative_prompt
│   │   ├── width
│   │   ├── height
│   │   ├── vae
│   │   ├── loras
│   │   │   ├── [0]
│   │   │   │   ├── name
│   │   │   │   ├── strength_model
│   │   │   │   └── strength_clip
│   │   │   └── [1]...
│   │   └── timestamp
│   └── workflow_info
│       ├── version
│       └── node_count
├── analysis
│   ├── technical
│   ├── aesthetic
│   └── classification
└── adobe_compatible
    ├── dc
    ├── photoshop
    ├── xmp
    └── xmpRights
```

This structure:
- Clearly separates basic metadata from AI-specific information
- Groups related parameters logically
- Allows for hierarchical representation of model-related parameters
- Provides space for analysis data
- Maintains a section for Adobe compatibility fields

### 2. Component Responsibilities

#### Extraction Layer
- **Purpose**: Extract metadata from ComfyUI workflows
- **Key Components**:
  - Node pattern recognition
  - Parameter extraction
  - Hierarchical organization

#### Processing Layer
- **Purpose**: Process and structure extracted metadata
- **Key Components**:
  - Metadata merging
  - Validation
  - Format conversion

#### Storage Layer
- **Purpose**: Store metadata in various formats
- **Key Components**:
  - Use existing handlers
  - Adapt metadata to handler requirements

### 3. Implementation Components

#### WorkflowMetadataExtractor
- Focus on extracting data from specific node types identified in discovery
- Group extracted data into logical categories
- Provide a consistent output structure

#### MetadataProcessor
- Handle merging of extracted data with user inputs
- Ensure Adobe compatibility
- Validate metadata structure

#### Integration with Handlers
- Format metadata correctly for handler expectations
- Use existing handlers for storage operations
- Handle errors gracefully

## Implementation Plan

### Phase 1: Fix Current Issues
1. **Eliminate Duplication**
   - Refactor `save_with_metadata` to extract workflow data only once
   - Remove redundant calls to workflow extraction methods
   - Ensure workflow data is stored in a single location

2. **Improve Adobe Compatibility**
   - Fix mappings for creator, copyright, and other fields
   - Ensure proper language alternative structures
   - Test with Photoshop/Lightroom to verify

3. **Enhance Data Extraction**
   - Implement targeted extraction of critical parameters
   - Focus on the most commonly used node types first
   - Ensure consistent field naming

### Phase 2: Refine Metadata Structure
1. **Standardize Field Names**
   - Define canonical names for commonly extracted parameters
   - Document the standard structure
   - Implement conversion to/from standard format

2. **Implement Hierarchical Organization**
   - Group parameters by logical categories
   - Maintain relationships between related data
   - Allow for nested structures where appropriate

3. **Create Extensibility Mechanism**
   - Design a method to easily add new field definitions
   - Create registration system for new metadata types
   - Document extension process

### Phase 3: Integration and Refinement
1. **Integrate with Existing Handlers**
   - Ensure metadata is formatted correctly for handlers
   - Test all storage mechanisms
   - Optimize for performance

2. **Add Discovery-Based Enhancements**
   - Integrate findings from discovery process
   - Add support for additional node types
   - Refine extraction logic based on common patterns

3. **Documentation and Examples**
   - Create comprehensive documentation
   - Provide examples of extending the system
   - Include usage examples for different scenarios

## Field Addition Process

To add new fields to the metadata structure:

1. **Identify Field Need**
   - From discovery data or new requirements
   - Define field purpose and expected values

2. **Define Field Location**
   - Determine logical location in hierarchy
   - Consider relationships to existing fields

3. **Update Node Pattern Registry**
   - Add pattern recognition for relevant nodes
   - Define parameter extraction rules

4. **Test and Validate**
   - Ensure field extraction works as expected
   - Verify compatibility with storage mechanisms

## Implementation Priorities

1. **Fix Existing Save Image Node**
   - Eliminate duplicate workflow data
   - Fix Adobe compatibility
   - Extract critical parameters

2. **Enhance Workflow Extraction**
   - Focus on specific node types
   - Implement logical grouping
   - Maintain consistent structure

3. **Improve Metadata Merging**
   - Properly combine user input with extracted data
   - Avoid duplications
   - Preserve important fields

## Known Limitations

### XMP Field Size Limitations

XMP metadata has practical size limitations that can cause issues with very large values:

1. **Description Truncation**: Long descriptions (>2000 characters) will be automatically truncated with an ellipsis (...) at the end
2. **Workflow Data**: Complete workflow JSON is too large for XMP and may be truncated or omitted entirely
3. **Subject/Keywords**: In XMP, keywords are stored as `dc:subject` - this is the standard Adobe format

If you need to preserve very long descriptions or complete workflow data without truncation, consider using:

1. The PNG workflow embedding (for workflows)
2. The separate JSON file option (for workflows)
3. Text files (for long descriptions)

### Adobe Compatibility

The metadata is structured to be compatible with Adobe applications (Photoshop, Lightroom, Bridge), which means:

1. Keywords appear as `dc:subject` in XMP but will show correctly as Keywords in Adobe apps
2. Workflow data is stored in a custom namespace that Adobe apps will ignore

## Implementation Notes

The implementation follows these principles:

1. **User input takes priority** over extracted workflow data
2. **Avoid duplication** between different metadata sections
3. **Truncate gracefully** when necessary instead of failing
4. **Use standard Adobe formats** for maximum compatibility