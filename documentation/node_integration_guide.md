# Metadata System Integration Guide (PREVIEW)

## 1. Introduction

This guide explains how to integrate your custom nodes with the new metadata system. The system allows nodes to read and write metadata to multiple storage formats while ensuring proper data structure and compatibility.

> **Note**: This is a preview guide and may evolve as we finalize testing of the system.

## 2. System Overview

The metadata system uses a service-based architecture to provide a unified interface for handling metadata:

- **MetadataService**: Central façade that coordinates operations across different handlers
- **Handlers**: Specialized components for different storage formats (embedded, XMP, text, database)
- **Utilities**: Namespace registration, format detection, error handling, etc.

## 3. Integration Steps

### 3.1 Basic Integration

To integrate your node with the metadata system:

```python
# 1. Import the service
from eric_metadata.service import MetadataService

class MyAnalysisNode:
    """My analysis node with metadata support"""
    
    def __init__(self):
        # Initialize the metadata service
        self.metadata_service = MetadataService(debug=False)
        
    def process(self, input_image, input_path):
        """Process input image and update metadata
        
        Args:
            input_image: Image to process
            input_path: Path to the image file
        """
        # Use the metadata service here
        # ...
```

### 3.2 Using the Resource Identifier

The resource identifier is critically important for XMP sidecar files. It ensures all nodes use the same identifier for the same file:

```python
# Always set the resource identifier before writing metadata
filename = os.path.basename(input_filepath)
resource_uri = f"file:///{filename}"
self.metadata_service.set_resource_identifier(resource_uri)
```

### 3.3 Reading Existing Metadata

To read metadata from an image:

```python
# Read from preferred source with fallback to others
metadata = self.metadata_service.read_metadata(input_filepath, source='xmp', fallback=True)

# Access specific sections
if 'analysis' in metadata and 'blur' in metadata['analysis']:
    blur_score = metadata['analysis']['blur'].get('score', 0.0)
```

### 3.4 Merging Metadata

The system automatically merges new metadata with existing data. If you need to merge manually:

```python
# Read existing metadata
existing = self.metadata_service.read_metadata(filepath)

# Create your new metadata
new_metadata = {'analysis': {'my_feature': {'score': 0.75}}}

# Merge them (this happens automatically in write_metadata)
merged = self.metadata_service.merge_metadata(filepath, new_metadata)
```

## 4. Metadata Structure Guidelines

### 4.1 Top-Level Organization

```python
metadata = {
    'basic': {},        # Title, description, keywords, etc.
    'regions': {}       # Face regions, subject areas, etc.
}
```

### 4.2 Basic Metadata

```python
basic_data = {
    'title': 'My Image Title',
    'rating': 4  # 0-5 scale
}
metadata['basic'] = basic_data
```

### 4.3 Analysis Data

For measurements and scores:

```python
analysis_data = {
    'technical': {
        'blur': {
            'score': 0.85,
            'higher_better': False,
            'timestamp': '2023-12-01T12:34:56'
        },
        'noise': {
            'score': 0.12,
            'higher_better': False
        }
    }
}
metadata['analysis'] = analysis_data
```

### 4.4 AI Generation Data

```python
ai_data = {
    'generation': {
        'model': 'sd_xl_base_1.0',
        'prompt': 'a photo of a cat',
        'negative_prompt': 'blurry, low quality',
        'seed': 42,
        'steps': 30,
        'cfg_scale': 7.5,
        'sampler': 'euler_a',
        'timestamp': datetime.now().isoformat()
    }
}
metadata['ai_info'] = ai_data
```

## 5. Advanced Integration

### 5.1 Node Types

Different node types benefit from different integration patterns:

#### Analysis Nodes

```python
class ImageAnalysisNode:
    def __init__(self):
        self.metadata_service = MetadataService(debug=False)
    
    def analyze(self, image_path):
        # Run your analysis
        sharpness_score = self._calculate_sharpness(image_path)
        
        # Prepare metadata
        metadata = {
            'analysis': {
                'technical': {
                    'sharpness': {
                        'score': sharpness_score,
                        'higher_better': True,
                        'timestamp': datetime.now().isoformat()
                    }
                }
            }
        }
        
        # Write metadata
        self.metadata_service.write_metadata(
            image_path,
            metadata,
            targets=['embedded', 'xmp']
        )
        
        return sharpness_score
```

#### Generation Nodes

```python
class MyGenerationNode:
    def __init__(self):
        self.metadata_service = MetadataService(debug=False)
    
    def generate_image(self, model_name, prompt, seed):
        # Generate image (implementation specific)
        image, path = self._generate_image(model_name, prompt, seed)
        
        # Prepare generation metadata
        metadata = {
            'ai_info': {
                'generation': {
                    'model': model_name,
                    'prompt': prompt,
                    'seed': seed,
                    'timestamp': datetime.now().isoformat()
                }
            }
        }
        
        # Write metadata
        self.metadata_service.write_metadata(path, metadata)
        
        return image, path
```

### 5.2 Format-Specific Options

Configure handler-specific behavior:

```python
# Configure specific handler options
self.metadata_service.configure_handler(
    'embedded',
    preserve_workflow_data=True,  # PNG workflow preservation
    use_exiftool=True             # Force ExifTool for certain formats
)

# Configure XMP handler options
self.metadata_service.configure_handler(
    'xmp',
    create_sidecar_for_raw=True,  # Always create XMP sidecar for RAW files
    merge_strategy='newest'        # How to handle conflicts
)

# Configure database handler
self.metadata_service.configure_handler(
    'database',
    db_path='/path/to/metadata.db',
    auto_index_keywords=True
)
```

### 5.3 Working With Regions

For facial recognition or object detection nodes:

```python
def process_faces(self, image_path, faces):
    # Create regions metadata
    regions_metadata = {
        'regions': {
            'faces': [],
            'summary': {
                'face_count': len(faces),
                'detector_type': 'my_face_detector_v1'
            }
        }
    }
    
    # Build face entries
    for idx, face in enumerate(faces):
        face_data = {
            'type': 'Face',
            'name': f'Face {idx+1}',
            'area': {
                'x': face['x'] / img_width,  # Normalized coordinates (0-1)
                'y': face['y'] / img_height,
                'w': face['width'] / img_width,
                'h': face['height'] / img_height
            },
            'extensions': {
                'eiqa': {
                    'face_analysis': {
                        'confidence': face['confidence'],
                        'age': face.get('age', 0),
                        'gender': face.get('gender', 'unknown'),
                        'emotion': {
                            'scores': face.get('emotions', {})
                        }
                    }
                }
            }
        }
        regions_metadata['regions']['faces'].append(face_data)
    
    # Write metadata
    self.metadata_service.write_metadata(image_path, regions_metadata)
```

### 5.4 Example for XMP Sidecar Handler

```python
from eric_metadata.handlers.xmp import XMPSidecarHandler

def create_separate_xmp_file(self, image_path, metadata):
    # Using the handler directly gives more control over specific XMP features
    # that aren't exposed through the general service interface
    xmp_handler = XMPSidecarHandler(debug=False)
    
    # Set resource identifier 
    filename = os.path.basename(image_path)
    xmp_handler.set_resource_identifier(f"file:///{filename}")
    
    # Write XMP sidecar file
    return xmp_handler.write_metadata(image_path, metadata)
```

## 6. Error Handling

### 6.1 Graceful Error Handling

```python
def safe_read_metadata(self, filepath):
    try:
        metadata = self.metadata_service.read_metadata(filepath, fallback=True)
        return metadata
    except Exception as e:
        print(f"Error reading metadata: {e}")
        # Return empty structure as fallback
        return {'basic': {}, 'analysis': {}, 'ai_info': {}, 'regions': {}}
```

### 6.2 Format Recovery

```python
# Try embedded first, with fallback to others if it fails
metadata = self.metadata_service.read_metadata(
    filepath,
    source='embedded',
    fallback=True,
    fallback_priority=['xmp', 'database']
)

# Write with fallback options
success = self.metadata_service.write_metadata(
    filepath, 
    metadata,
    targets=['embedded'],
    fallback_targets=['xmp']  # If embedded fails, try XMP
)
```

## 7. Advanced Metadata Patterns

### 7.1 Handling Batched Images

```python
def process_batch(self, image_paths):
    results = {}
    
    # Use batch operations for efficiency
    metadata_map = self.metadata_service.batch_read(image_paths)
    
    for path, metadata in metadata_map.items():
        # Process each image's metadata
        # ...
        
        # Update with new data
        new_metadata = self._generate_metadata(path)
        merged = self.metadata_service.merge_metadata(metadata, new_metadata)
        results[path] = merged
    
    # Write back in batch
    self.metadata_service.batch_write(results)
    
    return results
```

```python
# For very large batches, consider processing in chunks to manage memory usage
max_chunk_size = 100
for i in range(0, len(large_file_list), max_chunk_size):
    chunk = large_file_list[i:i + max_chunk_size]
    self.metadata_service.batch_operation('read', chunk)
```

### 7.2 Using Specific Handlers Directly

```python
from eric_metadata.handlers.db import DatabaseHandler

# Direct database queries for advanced needs
def find_images_by_criteria(self, criteria):
    # Create database handler directly
    db_handler = DatabaseHandler(debug=False)
    
    # Build query
    query = {
        'scores': [
            # category, metric, operator, value
            ('technical', 'blur.score', '>', 0.8)  
        ],
        'keywords': ['portrait', 'outdoor'],
        'classifications': [('style', 'cinematic')],
        'orientation': 'landscape',
        'order_by': 'i.rating DESC',
        'limit': 50
    }
    
    # Execute search
    results = db_handler.search_images(query)
    return results
```

### 7.3 Custom Metadata Extensions

```python
# Create custom metadata sections
metadata = {
    'my_extension': {
        'custom_field1': 'value1',
        'measurements': {
            'value': 42.5,
            'units': 'pixels',
            'confidence': 0.95
        }
    }
}

# Configure the service to register your extension namespace
self.metadata_service.register_namespace(
    'my_ext', 
    'http://example.org/myextension/'
)

# Write with your extension
self.metadata_service.write_metadata(filepath, metadata)
```

## 8. Performance Considerations

### 8.1 Resource Management

```python
# Use context manager for clean resource handling
with MetadataService() as metadata_service:
    metadata = metadata_service.read_metadata(filepath)
    # Process metadata...
    metadata_service.write_metadata(filepath, metadata)
# Resources automatically cleaned up
```

### 8.2 Optimizing for Large Batches

```python
# For large batches, configure connection pooling
self.metadata_service.configure_handler(
    'database',
    connection_pooling=True,
    max_connections=5
)

# Perform operations in chunks
for chunk in self._chunks(large_file_list, 100):
    self.metadata_service.batch_operation('read', chunk)
```

### 8.3 Minimizing Size for Embedding

```python
def prepare_compact_metadata(self, full_metadata):
    # Create compact version for embedding
    compact = {}
    
    # Include only essential fields
    if 'basic' in full_metadata:
        compact['basic'] = {
            'title': full_metadata['basic'].get('title'),
            'keywords': full_metadata['basic'].get('keywords')
        }
    
    if 'ai_info' in full_metadata:
        # Just include critical generation parameters
        gen_data = full_metadata['ai_info'].get('generation', {})
        compact['ai_info'] = {
            'generation': {
                'model': gen_data.get('model'),
                'seed': gen_data.get('seed'),
                'sampler': gen_data.get('sampler'),
                'steps': gen_data.get('steps')
            }
        }
    
    return compact
```

### 8.4 Thread Safety

When multiple nodes might be accessing the metadata service concurrently:

```python
# The metadata service's write operations are internally thread-safe
# but for complex operations, consider using locks

import threading

class ThreadSafeNode:
    def __init__(self):
        self.metadata_service = MetadataService()
        self._lock = threading.Lock()
        
    def process_batch(self, items):
        with self._lock:
            # Perform a sequence of read/modify/write operations atomically
            results = []
            for item in items:
                metadata = self.metadata_service.read_metadata(item)
                # modify metadata
                self.metadata_service.write_metadata(item, metadata)
                results.append(metadata)
            return results
```

## 9. Complete Working Example

Here's an example of a complete node integration:

```python
import os
from datetime import datetime
from eric_metadata.service import MetadataService

class ImageEnhancementNode:
    """Node that enhances images and records metadata about the process"""
    
    def __init__(self):
        self.metadata_service = MetadataService(debug=False)
        self.metadata_service.configure_handler('embedded', preserve_workflow_data=True)
    
    def enhance_image(self, input_filepath, enhancement_type, strength):
        """Enhance image and record metadata about the enhancement"""
        # 1. Read existing metadata (if any)
        existing_metadata = self.metadata_service.read_metadata(
            input_filepath, 
            fallback=True
        )
        
        # 2. Process the image (implementation-specific)
        output_path = self._enhance_image(input_filepath, enhancement_type, strength)
        
        # 3. Set resource identifier (important for XMP)
        filename = os.path.basename(output_path)
        resource_uri = f"file:///{filename}"
        self.metadata_service.set_resource_identifier(resource_uri)
        
        # 4. Create new metadata about the enhancement
        enhancement_metadata = {
            'basic': {
                'title': f"{enhancement_type.capitalize()} Enhanced Image",
                'description': f"Enhanced using {enhancement_type} algorithm with strength {strength}",
                'keywords': [enhancement_type, 'enhanced', 'processed']
            },
            'analysis': {
                'processing': {
                    'enhancement_type': enhancement_type,
                    'strength': strength,
                    'quality_estimate': self._estimate_quality(output_path),
                    'timestamp': datetime.now().isoformat()
                }
            },
            'workflow_info': {
                'node_type': 'ImageEnhancement',
                'version': '1.0.0',
                'processing_time_ms': self._last_processing_time
            }
        }
        
        # 5. Write metadata to all targets
        self.metadata_service.write_metadata(
            output_path, 
            enhancement_metadata,
            targets=['embedded', 'xmp']
        )
        
        # 6. Return the enhanced image path
        return output_path
        
    def _enhance_image(self, input_path, enhancement_type, strength):
        """Implementation of actual enhancement"""
        # Actual enhancement code here...
        output_path = f"{os.path.splitext(input_path)[0]}_enhanced.png"
        self._last_processing_time = 1250  # Example processing time in ms
        return output_path
        
    def _estimate_quality(self, image_path):
        """Estimate quality of enhanced output"""
        # Quality estimation code here...
        return 0.85  # Example quality score
```

## 10. Common Use Cases

### 10.1 Image Analysis Node

```python
def analyze_and_tag(self, image_path):
    """Analyze image content and add metadata tags"""
    # Run image analysis (implementation-specific)
    analysis_results = self._analyze_content(image_path)
    
    # Extract tags from analysis
    tags = [item['label'] for item in analysis_results 
            if item['confidence'] > 0.7]
    
    # Build confidence scores dictionary
    confidence_scores = {
        item['label']: item['confidence'] 
        for item in analysis_results
    }
    
    # Create metadata
    metadata = {
        'basic': {
            'keywords': tags
        },
        'analysis': {
            'classification': {
                'tags': tags,
                'confidence_scores': confidence_scores,
                'detector': 'my_classifier_v1'
            }
        }
    }
    
    # Write metadata
    self.metadata_service.write_metadata(
        image_path, metadata, targets=['embedded', 'xmp', 'database']
    )
    
    # Return analysis results and tags
    return analysis_results, tags
```

### 10.2 Copyright and Attribution Node

```python
def add_copyright_info(self, image_path, creator, rights_usage, copyright_text):
    """Add copyright and attribution information"""
    # Format standard copyright statement
    if not copyright_text:
        current_year = datetime.now().year
        copyright_text = f"© {current_year} {creator}. All rights reserved."
    
    # Create metadata
    metadata = {
        'basic': {
            'creator': creator,
            'copyright': copyright_text,
            'rights': rights_usage
        }
    }
    
    # Add additional XMP Rights fields
    metadata['xmp_rights'] = {
        'Marked': True,
        'UsageTerms': rights_usage or copyright_text,
        'WebStatement': f"https://example.com/rights/{creator}"
    }
    
    # Write metadata with priority to embedded
    self.metadata_service.write_metadata(
        image_path, metadata, targets=['embedded', 'xmp']
    )
    
    return copyright_text
```

### 10.3 Workflow Capture Node

```python
from eric_metadata.utils.workflow_parser import WorkflowParser
from eric_metadata.utils.workflow_extractor import WorkflowExtractor

def capture_workflow(self, image_path, workflow_data=None):
    """Capture workflow information in metadata"""
    
    # If no workflow data provided, try to extract from current context
    if not workflow_data:
        extractor = WorkflowExtractor()
        workflow_data = extractor.extract_current_workflow()
    
    # Parse workflow to extract key information
    if workflow_data:
        parser = WorkflowParser(workflow_data)
        workflow_summary = parser.get_summary()
        
        # Create metadata structure
        metadata = {
            'ai_info': {
                'workflow_info': {
                    'node_count': workflow_summary.get('node_count', 0),
                    'execution_time': workflow_summary.get('execution_time', 0),
                    'creation_app': 'ComfyUI',
                    'timestamp': datetime.now().isoformat()
                }
            }
        }
        
        # Store full workflow data
        if workflow_data:
            # Store in database only to avoid size issues in embedded/XMP
            db_metadata = {
                'ai_info': {
                    'workflow': workflow_data
                }
            }
            self.metadata_service.write_metadata(
                image_path, db_metadata, targets=['database']
            )
        
        # Write summary to all targets
        self.metadata_service.write_metadata(
            image_path, metadata, targets=['embedded', 'xmp']
        )
        
        return workflow_summary
    
    return None
```

## 11. Working with Namespaces

When extending the metadata system with custom fields or integrating with specific applications, you may need to register custom namespaces:

```python
from eric_metadata.utils.namespace import NamespaceManager

def register_custom_namespaces(self):
    """Register custom namespaces for specialized metadata"""
    
    # Register a custom namespace for your application
    NamespaceManager.register_namespace(
        'myapp', 
        'http://example.org/myapp/1.0/',
        register_with_pyexiv2=True
    )
    
    # Register an industry standard namespace
    NamespaceManager.register_namespace(
        'plus', 
        'http://ns.useplus.org/ldf/xmp/1.0/',
        register_with_pyexiv2=True
    )
    
    # Get all registered namespaces
    all_namespaces = NamespaceManager.get_all_namespaces()
    print(f"Available namespaces: {all_namespaces}")
```

## 12. Debugging

Enable debug mode for detailed logging:

```python
# Enable debug logging in the service constructor
metadata_service = MetadataService(debug=True)

# Or enable it later
metadata_service.set_debug(True)

# Configure logging level for specific handlers
metadata_service.configure_handler('embedded', debug=True)
```

Common debug patterns:
- Check for XMP namespace registration issues with `NamespaceManager.print_registered_namespaces()`
- Verify file permissions when writing fails
- For XMP sidecar issues, ensure resource identifiers are set correctly

This guide is a preview and will be updated based on testing results and feedback. If you encounter any issues or have suggestions, please share them to help improve the system.