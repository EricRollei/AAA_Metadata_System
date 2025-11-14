# Extending Metadata Extraction: Adding New Node Types

This guide explains how to add new ComfyUI node types to the metadata extraction system to ensure their important parameters are captured in embedded metadata.

## How the Metadata System Works

The metadata extraction process follows these steps:

1. When a user saves an image with the `MetadataAwareSaveImage` node, the workflow data is passed to the extraction system
2. The `WorkflowMetadataProcessor` analyzes the workflow nodes and connections
3. Specific node types and their important parameters are identified using predefined mappings
4. The parameters are extracted and structured into a metadata hierarchy
5. The metadata is embedded in the image file according to user-selected formats

## Where to Add New Node Types

The main location for adding new node types is in the `_extract_detailed_parameters` method in:
```python
a:\Comfy_Dec\ComfyUI\custom_nodes\Metadata_system\eric_metadata\utils\workflow_metadata_processor.py
```

This method contains:
1. The `parameters` dictionary defining parameter categories to extract
2. The `node_mappings` dictionary defining which node types to look for and which inputs to extract

## How to Add a New Node Type

### Step 1: Identify the Node Type and Important Parameters

First, examine the node type in the `central_workflow_discovery.json` file or ComfyUI interface to determine:

- The exact node type name (e.g., `UNETLoader`, `ModelSamplingFlux`)
- Which parameters are most important to extract (model names, key settings)
- How to categorize each parameter (model, settings, etc.)

### Step 2: Add to Parameters Dictionary (if needed)

If your node uses a new parameter category not already defined, add it to the `parameters` dictionary:

```python
parameters = {
    'model': [],
    # ...existing categories...
    'new_category': [],  # Add your new category here
}
```

### Step 3: Add to Node Mappings Dictionary

Add your node type to the `node_mappings` dictionary with mappings to the parameters you want to extract:

```python
node_mappings = {
    # ...existing mappings...
    
    # New node type
    'NewNodeType': {
        'parameter_category': 'input_field_name',
        'another_parameter': 'another_input_field'
    },
}
```

For example, to add a new model loader:

```python
'MyNewModelLoader': {
    'model': 'ckpt_name',
    'model_type': 'model_type'
}
```

### Step 4: Handle Special Processing (if needed)

For parameters that need special processing or should be structured differently, add handling in the processing section near the end of the method:

```python
# For each parameter type, use the first found value
for param_key, values in parameters.items():
    if values:
        # Handle special parameters that need processing
        if param_key == 'my_special_param' and values:
            # Create a structured object
            special_data = {'primary_value': values[0]['value']}
            
            # Look for related parameters
            for other_entry in parameters.get('related_param', []):
                special_data['other_field'] = other_entry['value']
                break
                
            # Store as structured object
            generation['my_special_param'] = special_data
        else:
            # Standard parameter extraction
            generation[param_key] = values[0]['value']
```

### Step 5: Update Embedded Handler (if needed)

If your new parameter requires special formatting in the embedded metadata, update the `_prepare_ai_metadata` method in:
```python
a:\Comfy_Dec\ComfyUI\custom_nodes\Metadata_system\eric_metadata\handlers\embedded.py
```

Add handling similar to how special parameters are processed:

```python
# Add special handling for your parameter type
if 'your_parameter' in generation and generation['your_parameter']:
    if isinstance(generation['your_parameter'], dict):
        # Process structured data
        param_data = generation['your_parameter']
        param_str = f"field1:{param_data.get('field1', '')}|field2:{param_data.get('field2', '')}"
        result[f"{prefix}your_parameter"] = param_str
    else:
        # Simple value
        result[f"{prefix}your_parameter"] = str(generation['your_parameter'])
```

## Parameter Categorization Guidelines

When categorizing parameters, follow these guidelines:

### Models and Weights
- `model`: Main checkpoint models
- `style_model`: Style models (StyleGAN, LoRA adapters for style)
- `unet_model`: UNET models like Flux
- `controlnet_model`: ControlNet models
- `ip_adapter_model`: IP-Adapter models
- `upscale_model`: Upscaling models like ESRGAN
- `vae`: VAE models

### Generation Settings
- `sampler`: Sampler algorithms (Euler, DDIM, etc.)
- `scheduler`: Scheduler types (Karras, normal, etc.)
- `steps`: Sampling steps
- `cfg_scale`: CFG/guidance scale
- `seed`: Random seeds
- `denoise`: Denoise strength
- `clip_skip`: CLIP skip setting

### Dimensions
- `width`: Image width
- `height`: Image height

### Images and References
- `reference_image`: Input images, reference images
- `prompt_text`: Text prompts, instructions

### Custom Settings
- Create parameters for unique functionality like `flux_settings`

## Example: Adding a New Node Type

Here's a complete example of adding a new type of model loader:

```python
# In workflow_metadata_processor.py

def _extract_detailed_parameters(self, nodes: Dict[str, Any], links: List[Any], result: Dict[str, Any]) -> None:
    # Parameters to extract
    parameters = {
        # ...existing parameters...
        'new_model_type': [],  # New parameter category
    }
    
    # Node mappings
    node_mappings = {
        # ...existing mappings...
        
        # Add new model loader
        'FancyModelLoader': {
            'model': 'model_path',               # Map to existing parameter
            'new_model_type': 'model_version',   # Map to new parameter
            'denoise': 'strength'                # Map to existing parameter
        },
    }
    
    # ...existing code for collecting parameters...
    
    # For each parameter type, use the first found value
    for param_key, values in parameters.items():
        if values:
            # Handle special case for new model type
            if param_key == 'new_model_type' and values:
                # Create structured data
                model_info = {
                    'version': values[0]['value'],
                    'type': 'fancy'
                }
                generation['model_info'] = model_info
            else:
                # Standard parameters
                generation[param_key] = values[0]['value']
```

## Testing Your Changes

After adding a node type:

1. Run a workflow that includes your new node type
2. Save an image with the `MetadataAwareSaveImage` node with debugging enabled
3. Check the console output to confirm your parameters are being extracted
4. Examine the saved image metadata to verify it's properly embedded

You can use tools like ExifTool or XnView to inspect the embedded metadata.
