# Metadata System Node Guide: Text Metadata Handling

## Text File Format Options

The metadata system now supports multiple text file formats for storing metadata. This allows you to choose between machine-readable formats (better for parsing) and human-readable formats (better for direct review).

### Format Options

The TxtFileHandler now supports two main formats:

1. **Flat Format** (Default): Key-value pairs with dotted notation for hierarchy
   - Good for program parsing
   - Preserves all data types accurately
   - Compact representation

2. **Human-Readable Format**: Natural language descriptions with context
   - Provides explanations of values (like "higher is better")
   - Organizes data in logical sections
   - Includes context for measurements

### Using Text Formats in Nodes

To use these formats in your nodes, you can specify the format when writing metadata:

```python
# In your node's process method:

# Option 1: Set format preference in the service
metadata_service = MetadataService(debug=debug_logging)
# Get the TxtFileHandler and set format preference
txt_handler = metadata_service._get_txt_handler()
txt_handler.set_output_format(human_readable=True)

# Option 2: Set format as user parameter
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "image": ("IMAGE",),
            "input_filepath": ("STRING", {"default": ""}),
        },
        "optional": {
            # Other parameters...
            "human_readable_txt": ("BOOLEAN", {"default": True}),
        }
    }

def process(self, image, input_filepath, human_readable_txt=True):
    # Create metadata structure
    metadata = {...}
    
    # Set the text format
    txt_handler = self.metadata_service._get_txt_handler()
    txt_handler.set_output_format(human_readable=human_readable_txt)
    
    # Write the metadata - format will be determined by the setting
    self.metadata_service.write_metadata(filepath, metadata, targets=['txt'])
```

### Example Output: Human-Readable Format

The human-readable format produces output like this:

```
Last update: 2025-03-09T15:30:45.123456
Metadata for image.png

Basic Title: Mountain Landscape
Description: A beautiful mountain landscape at sunset
Keywords: mountains, sunset, landscape

Technical Analysis:
    Blur score is 87.5 out of 100 with 100 being the more blurry
    Noise score is 0.12 out of 1.0 with lower being better

Aesthetic Analysis:
    Composition score: 8.2 out of 10

AI Generation Information:
    Model: stable-diffusion-xl-v1-0
    Prompt: mountain landscape at sunset
    Steps: 30
    CFG Scale: 7.0
```

This format provides a much better experience for users who want to read the metadata directly, as it includes explanations of what each value means and organizes the information logically.

### Recommendations

1. **Default to Human-Readable**: For nodes aimed at end-users, consider defaulting to human-readable format for text files. This makes the metadata immediately useful.

2. **Add Format Toggle**: Include a toggle in your node UI to let users choose between formats.

3. **Combine with Embedded Metadata**: Use both text files (human-readable) and embedded metadata (machine-readable) for the best of both worlds.

4. **Handle Node-Specific Data**: Extend the human-readable formatter in your nodes for any specialized data your node produces:

```python
def _customize_human_readable_output(self, filepath, metadata):
    # Get the TxtFileHandler
    txt_handler = self.metadata_service._get_txt_handler()
    
    # First generate standard output
    success = txt_handler.write_human_readable_text(filepath, metadata)
    if not success:
        return False
    
    # Then add any custom content
    txt_path = txt_handler._get_text_file_path(filepath)
    with open(txt_path, 'a', encoding='utf-8') as f:
        f.write("\nAdditional Custom Information:\n")
        f.write("    My node's special data: ...\n")
    
    return True
```

## Best Practices for Text Metadata

1. **Use section headers**: Group related data under clear section headers
2. **Provide context**: Always include what values mean (e.g., scale, better/worse)
3. **Use natural language**: Write descriptions as sentences, not just label-value pairs
4. **Include units**: Always specify units for measurements
5. **Format for readability**: Use indentation and spacing to make the text scannable

By following these guidelines, your nodes will provide much more useful metadata to users.