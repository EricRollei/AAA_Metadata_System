# Integration Guide

This guide describes how to integrate the Metadata System with your own ComfyUI custom nodes or Python applications.

## Table of Contents

- [ComfyUI Node Integration](#comfyui-node-integration)
  - [Basic Node Integration](#basic-node-integration)
  - [Metadata-Aware Nodes](#metadata-aware-nodes)
  - [Creating a New Metadata Node](#creating-a-new-metadata-node)
- [Python Application Integration](#python-application-integration)
  - [Basic Integration](#basic-integration)
  - [Advanced Integration](#advanced-integration)
- [Custom Handler Implementation](#custom-handler-implementation)
- [Extension Points](#extension-points)

## ComfyUI Node Integration

### Basic Node Integration

To integrate the Metadata System with your ComfyUI nodes, you need to:

1. Import the necessary components:
   ```python
   from AAA_Metadata_System import MetadataService
   from AAA_Metadata_System.utils.workflow_metadata_processor import WorkflowMetadataProcessor
   ```

2. Access metadata in your node:
   ```python
   class MyCustomNode:
       @classmethod
       def INPUT_TYPES(cls):
           return {
               "required": {
                   "images": ("IMAGE",),
                   "metadata": ("METADATA", {"default": None})
               }
           }
       
       RETURN_TYPES = ("IMAGE", "METADATA")
       FUNCTION = "process"
       
       def process(self, images, metadata=None):
           # Initialize metadata if None
           if metadata is None:
               metadata = {}
               
           # Process images...
           
           # Add your own metadata
           if 'analysis' not in metadata:
               metadata['analysis'] = {}
           
           metadata['analysis']['my_analysis'] = {
               'score': 0.85,
               'timestamp': self._get_timestamp()
           }
           
           return (processed_images, metadata)
           
       def _get_timestamp(self):
           import datetime
           return datetime.datetime.now().isoformat()
   ```

3. Add node class mapping:
   ```python
   NODE_CLASS_MAPPINGS = {
       "MyCustomNode": MyCustomNode
   }
   
   NODE_DISPLAY_NAME_MAPPINGS = {
       "MyCustomNode": "My Custom Node"
   }
   ```

### Metadata-Aware Nodes

To make your node metadata-aware (can read and handle metadata):

1. Add a metadata input:
   ```python
   "metadata": ("METADATA", {"default": None})
   ```

2. Return updated metadata:
   ```python
   RETURN_TYPES = ("IMAGE", "METADATA")
   ```

3. Handle gracefully when metadata is None:
   ```python
   if metadata is None:
       metadata = {}
   ```

### Creating a New Metadata Node

To create a new node focused on metadata processing:

1. Create a basic node structure:
   ```python
   class MyMetadataNode:
       @classmethod
       def INPUT_TYPES(cls):
           return {
               "required": {
                   "metadata": ("METADATA", {"default": None}),
                   "field_path": ("STRING", {"default": "basic.title"})
               }
           }
       
       RETURN_TYPES = ("STRING", "METADATA")
       FUNCTION = "process_metadata"
       
       def process_metadata(self, metadata, field_path):
           # Initialize metadata if None
           if metadata is None:
               metadata = {}
               
           # Process metadata...
           value = self._get_field_value(metadata, field_path)
           
           return (value, metadata)
           
       def _get_field_value(self, metadata, field_path):
           # Split path into parts
           parts = field_path.split('.')
           
           # Navigate through the path
           current = metadata
           for part in parts:
               if part in current:
                   current = current[part]
               else:
                   return None
                   
           return str(current)
   ```

2. Add more advanced functionality:
   ```python
   def process_metadata(self, metadata, field_path):
       # Initialize metadata if None
       if metadata is None:
           metadata = {}
           
       # Process metadata...
       value = self._get_field_value(metadata, field_path)
       
       # Create or update MetadataService for advanced operations
       service = MetadataService()
       
       # Example: Export to text for debugging
       if value:
           # Create human-readable summary
           service.set_text_format(human_readable=True)
           service.write_metadata("/tmp/debug_output.png", metadata)
           
       return (value, metadata)
   ```

## Python Application Integration

### Basic Integration

Integrate the Metadata System into your Python application:

```python
from AAA_Metadata_System import MetadataService

# Initialize the service
service = MetadataService(debug=False, human_readable_text=True)

# Write metadata to all supported formats
metadata = {
    'basic': {
        'title': 'My Image',
        'description': 'An example image',
        'keywords': ['example', 'test', 'metadata']
    },
    'ai_info': {
        'generation': {
            'model': 'stable-diffusion-v1-5',
            'prompt': 'example prompt',
            'negative_prompt': 'example negative',
            'sampler': 'euler_a',
            'steps': 30,
            'cfg_scale': 7.5,
            'seed': 1234567890
        }
    }
}

# Write to file
result = service.write_metadata('path/to/image.png', metadata)

# Read metadata
stored_metadata = service.read_metadata('path/to/image.png')

# Access metadata
if 'basic' in stored_metadata:
    print(f"Title: {stored_metadata['basic'].get('title')}")
```

### Advanced Integration

For more advanced integration:

```python
import os
from AAA_Metadata_System import MetadataService
from AAA_Metadata_System.handlers.db import DatabaseHandler
from AAA_Metadata_System.utils.workflow_metadata_processor import WorkflowMetadataProcessor

# Initialize the service
service = MetadataService(debug=True)

# Direct access to handlers for specialized operations
db_handler = DatabaseHandler()

# Search for images
results = db_handler.search_images({
    'scores': [('aesthetic', 'overall', '>', 7.0)],
    'keywords': ['landscape']
})

# Process each result
for img_data in results:
    filepath = img_data['filepath']
    
    # Read full metadata
    metadata = service.read_metadata(filepath)
    
    # Process workflow data if available
    if 'ai_info' in metadata and 'workflow' in metadata['ai_info']:
        workflow_data = metadata['ai_info']['workflow']
        
        # Extract parameters
        processor = WorkflowMetadataProcessor()
        params = processor.extract_generation_parameters(workflow_data)
        
        print(f"File: {os.path.basename(filepath)}")
        print(f"Prompt: {params.get('prompt', 'N/A')}")
        print(f"Seed: {params.get('seed', 'N/A')}")
        print("-" * 40)
```

## Custom Handler Implementation

Create your own metadata handler by extending the BaseHandler class:

```python
from AAA_Metadata_System.handlers.base import BaseHandler

class CloudStorageHandler(BaseHandler):
    """Handler for cloud storage of metadata"""
    
    def __init__(self, debug=False, api_key=None, bucket=None):
        super().__init__(debug)
        self.api_key = api_key
        self.bucket = bucket
        self._initialize_client()
    
    def _initialize_client(self):
        # Initialize your cloud storage client
        try:
            # Example with a fictional cloud API
            from cloud_storage_api import CloudClient
            self.client = CloudClient(api_key=self.api_key)
            self.log("Cloud storage client initialized")
        except Exception as e:
            self.log(f"Failed to initialize cloud client: {str(e)}", level="ERROR", error=e)
            self.client = None
    
    def write_metadata(self, filepath, metadata):
        """Write metadata to cloud storage"""
        return self._safely_execute(
            "write_cloud_metadata",
            self._write_cloud_metadata_impl,
            filepath,
            metadata
        )
    
    def _write_cloud_metadata_impl(self, filepath, metadata):
        """Implementation of cloud metadata writing"""
        if not self.client:
            self.log("Cloud client not available", level="ERROR")
            return False
            
        try:
            # Convert metadata to string or bytes
            import json
            meta_json = json.dumps(metadata)
            
            # Generate cloud path
            filename = os.path.basename(filepath)
            cloud_path = f"{self.bucket}/{filename}.meta.json"
            
            # Upload to cloud
            self.client.upload_data(
                data=meta_json,
                path=cloud_path,
                content_type="application/json"
            )
            
            self.log(f"Metadata uploaded to {cloud_path}")
            return True
            
        except Exception as e:
            self.log(f"Cloud upload failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def read_metadata(self, filepath):
        """Read metadata from cloud storage"""
        return self._safely_execute(
            "read_cloud_metadata",
            self._read_cloud_metadata_impl,
            filepath
        )
    
    def _read_cloud_metadata_impl(self, filepath):
        """Implementation of cloud metadata reading"""
        if not self.client:
            self.log("Cloud client not available", level="ERROR")
            return {}
            
        try:
            # Generate cloud path
            filename = os.path.basename(filepath)
            cloud_path = f"{self.bucket}/{filename}.meta.json"
            
            # Check if metadata exists
            if not self.client.path_exists(cloud_path):
                self.log(f"No metadata found at {cloud_path}", level="WARNING")
                return {}
            
            # Download from cloud
            meta_json = self.client.download_data(cloud_path)
            
            # Parse JSON
            import json
            metadata = json.loads(meta_json)
            
            self.log(f"Metadata downloaded from {cloud_path}")
            return metadata
            
        except Exception as e:
            self.log(f"Cloud download failed: {str(e)}", level="ERROR", error=e)
            return {}
```

Integrate your custom handler with the MetadataService:

```python
from AAA_Metadata_System import MetadataService
from my_module import CloudStorageHandler

# Initialize your custom handler
cloud_handler = CloudStorageHandler(
    debug=True,
    api_key="your_api_key",
    bucket="metadata_bucket"
)

# Initialize the service
service = MetadataService(debug=True)

# Store your handler reference for manual access
service._cloud_handler = cloud_handler

# Use your handler with custom targets
metadata = {...}  # Your metadata
filepath = "path/to/image.png"

# Write to standard targets plus your custom handler
service.write_metadata(filepath, metadata)

# Use custom handler directly
cloud_handler.write_metadata(filepath, metadata)
```

## Extension Points

The Metadata System has several extension points for customization:

### 1. Custom Metadata Sections

Add your own metadata sections to extend the standard structure:

```python
metadata = {
    'basic': {...},
    'analysis': {...},
    'ai_info': {...},
    'regions': {...},
    
    # Your custom section
    'my_custom_section': {
        'custom_field1': 'value1',
        'custom_field2': 42,
        'nested_data': {
            'sub_field': 'sub_value'
        }
    }
}

# All handlers will preserve your custom sections
service.write_metadata(filepath, metadata)
```

### 2. Custom Analysis Categories

Add new analysis categories under the analysis section:

```python
# Add custom analysis
if 'analysis' not in metadata:
    metadata['analysis'] = {}
    
metadata['analysis']['my_analyzer'] = {
    'primary_score': 0.92,
    'confidence': 0.87,
    'features': {
        'feature1': 0.78,
        'feature2': 0.65
    },
    'timestamp': service.get_timestamp()
}
```

### 3. Custom Extraction Logic

Create custom extraction from workflow data:

```python
from AAA_Metadata_System.utils.workflow_metadata_processor import WorkflowMetadataProcessor

class CustomWorkflowProcessor(WorkflowMetadataProcessor):
    def __init__(self, debug=False):
        super().__init__(debug)
    
    def extract_custom_data(self, workflow_data):
        """Extract custom data from workflow"""
        result = {}
        
        try:
            nodes = workflow_data.get('nodes', {})
            
            # Extract data from specific node types
            for node_id, node in nodes.items():
                class_type = node.get('class_type')
                
                # Handle your custom node types
                if class_type == 'MyCustomNode':
                    inputs = node.get('inputs', {})
                    result['custom_parameter'] = inputs.get('my_param')
                    
            return result
            
        except Exception as e:
            self.log(f"Custom extraction failed: {str(e)}", level="ERROR")
            return {}

# Use your custom processor
processor = CustomWorkflowProcessor(debug=True)
custom_data = processor.extract_custom_data(workflow_data)
```

### 4. Event Hooks

Add event hooks by subclassing handlers:

```python
from AAA_Metadata_System.handlers.txt import TxtFileHandler

class HookedTxtFileHandler(TxtFileHandler):
    def __init__(self, debug=False, human_readable=False):
        super().__init__(debug, human_readable)
        self.on_write_callbacks = []
        self.on_read_callbacks = []
    
    def add_write_hook(self, callback):
        """Add callback to run after successful write"""
        self.on_write_callbacks.append(callback)
    
    def add_read_hook(self, callback):
        """Add callback to run after successful read"""
        self.on_read_callbacks.append(callback)
    
    def write_metadata(self, filepath, metadata):
        """Write metadata with hooks"""
        result = super().write_metadata(filepath, metadata)
        
        if result:
            # Execute hooks
            for callback in self.on_write_callbacks:
                try:
                    callback(filepath, metadata)
                except Exception as e:
                    self.log(f"Write hook error: {str(e)}", level="WARNING")
        
        return result
    
    def read_metadata(self, filepath):
        """Read metadata with hooks"""
        metadata = super().read_metadata(filepath)
        
        if metadata:
            # Execute hooks
            for callback in self.on_read_callbacks:
                try:
                    callback(filepath, metadata)
                except Exception as e:
                    self.log(f"Read hook error: {str(e)}", level="WARNING")
        
        return metadata

# Usage example
def on_write(filepath, metadata):
    print(f"Wrote metadata to {filepath}")
    # Send notification, update external system, etc.

handler = HookedTxtFileHandler(debug=True, human_readable=True)
handler.add_write_hook(on_write)
```

### 5. Custom Formatters

Create custom format processors:

```python
from AAA_Metadata_System.handlers.txt import TxtFileHandler

class XMLFormatHandler(TxtFileHandler):
    def __init__(self, debug=False):
        super().__init__(debug, human_readable=False)
    
    def write_metadata(self, filepath, metadata):
        """Write metadata as XML"""
        try:
            # Get text file path with xml extension
            xml_path = os.path.splitext(filepath)[0] + '.xml'
            
            # Convert to XML
            xml_content = self._format_as_xml(metadata)
            
            # Write to file
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
                
            return True
            
        except Exception as e:
            self.log(f"XML write failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def _format_as_xml(self, metadata):
        """Format metadata as XML"""
        import xml.dom.minidom as md
        from xml.etree.ElementTree import Element, SubElement, tostring
        
        # Create root element
        root = Element('metadata')
        
        # Add each section
        for section_name, section_data in metadata.items():
            section_elem = SubElement(root, section_name)
            self._add_xml_elements(section_elem, section_data)
        
        # Convert to string and pretty-print
        xml_str = tostring(root, encoding='unicode')
        pretty_xml = md.parseString(xml_str).toprettyxml(indent="  ")
        
        return pretty_xml
    
    def _add_xml_elements(self, parent, data):
        """Recursively add elements to XML"""
        if isinstance(data, dict):
            for key, value in data.items():
                child = SubElement(parent, key)
                self._add_xml_elements(child, value)
        elif isinstance(data, list):
            for item in data:
                item_elem = SubElement(parent, 'item')
                self._add_xml_elements(item_elem, item)
        else:
            parent.text = str(data)
```

These extension points allow for flexible customization of the Metadata System to meet specific workflow requirements.