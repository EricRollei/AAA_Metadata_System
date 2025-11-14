# Multi-LoRA Loader Platform-Specific Nodes

## Overview

This directory contains platform-specific Multi-LoRA loader nodes that automatically filter LoRA dropdowns to show only relevant LoRAs for each platform. This solves the problem of having 3600+ LoRAs making selection impossible.

## Architecture

### Base Class: `Multi_LoRA_Loader_Base.py`
Contains all common LoRA loading logic, database integration, Civitai integration, and filtering capabilities. Platform-specific nodes inherit from this class.

### Platform-Specific Nodes

Each platform node:
- **Auto-filters by directory** at initialization time
- **Shows only relevant LoRAs** in dropdowns (not all 3600+)
- **Customizes behavior** per platform (CLIP yes/no, default strengths, etc.)
- **Maintains consistency** through shared base class

## Current Platform Nodes

### 1. **Multi-LoRA Loader (Wan i2v)** - `Multi_LoRA_Loader_Wan_i2v.py` ✅
- **Directory Filter**: `Wan\i2v`
- **Requires CLIP**: No (model-only)
- **Architecture**: Wan
- **Use Case**: Wan Video Image-to-Video workflows
- **Category**: `loaders/multi-lora/wan`

### 2. **Multi-LoRA Loader (Wan t2v)** - `Multi_LoRA_Loader_Wan_t2v.py` ✅
- **Directory Filter**: `Wan\t2v`
- **Requires CLIP**: No (model-only)
- **Architecture**: Wan
- **Use Case**: Wan Video Text-to-Video workflows
- **Category**: `loaders/multi-lora/wan`

### 3. **Multi-LoRA Loader (Qwen)** - `Multi_LoRA_Loader_Qwen.py` ✅
- **Directory Filter**: `Qwen`
- **Requires CLIP**: No (model-only)
- **Architecture**: Qwen
- **Use Case**: Qwen vision/language model workflows
- **Category**: `loaders/multi-lora/qwen`

### 4. **Multi-LoRA Loader (Flux)** - `Multi_LoRA_Loader_Flux.py` ✅
- **Directory Filter**: `Flux`
- **Requires CLIP**: Yes
- **Architecture**: Flux
- **Use Case**: Flux image generation workflows
- **Category**: `loaders/multi-lora/flux`
- **Default Strengths**: Model 0.8, CLIP 1.0

### 5. **Multi-LoRA Loader (Model Only)** - `Multi_LoRA_Loader_Model_Only.py`
- **Directory Filter**: None (shows all)
- **Requires CLIP**: No (model-only)
- **Use Case**: Generic diffusion models that don't use CLIP
- **Category**: `loaders/multi-lora`

### 6. **Multi-LoRA Loader v02** - `Multi_LoRA_Loader_v02.py`
- **Directory Filter**: None (shows all)
- **Requires CLIP**: Yes
- **Use Case**: Standard SDXL/SD1.5/Flux workflows with full filtering
- **Category**: `loaders/multi-lora`

## Key Features

### ✅ Platform-Specific Filtering
- Dropdowns show only 50-200 relevant LoRAs instead of 3600+
- No need to type directory filters every time
- Pre-configured for your workflow

### ✅ Additional Filtering Options
Each node still supports:
- **Filename search** - Search/filter by filename patterns
- **Category filter** - Filter by lightning, tools, artstyle, etc.
- **Trigger word search** - Search by trigger words from database
- **Rating filter** - Show only LoRAs with minimum rating

### ✅ Database Integration
- Tracks LoRA usage statistics
- Stores trigger words and metadata
- Integrates with LoRA Tester database
- Civitai API integration for automatic trigger word fetching

### ✅ User-Friendly Outputs
- **prompt_with_triggers** - Original prompt with trigger words added
- **loaded_loras_info** - Detailed info about loaded LoRAs
- **all_trigger_words** - Combined list of all trigger words
- **filter_info** - Active filters and match count
- **filtered_loras_list** - Full formatted list of matching LoRAs

## Directory Structure

Your LoRA directory structure:
```
L:\stable-diffusion-webui\models\Lora\
├── Wan\
│   ├── i2v\          ← Filtered by Wan i2v node
│   │   ├── lightning\
│   │   ├── tools\
│   │   ├── artstyle\
│   │   └── ...
│   └── t2v\          ← Filtered by Wan t2v node
│       ├── lightning\
│       ├── tools\
│       └── ...
├── SDXL\
│   └── ...
├── Flux\
│   └── ...
└── ...
```

## Adding New Platform Nodes

To create a new platform-specific node:

1. **Create new file**: `Multi_LoRA_Loader_YourPlatform.py`

2. **Copy this template**:
```python
from .Multi_LoRA_Loader_Base import MultiLoRALoaderBase

class MultiLoRALoaderYourPlatform(MultiLoRALoaderBase):
    # Platform configuration
    PLATFORM_NAME = "YourPlatform"
    PLATFORM_DIRECTORY_FILTER = os.path.join("YourPlatform", "subfolder")
    REQUIRES_CLIP = True  # or False
    DEFAULT_ARCHITECTURE = "YourPlatform"
    MAX_LORA_SLOTS = 8
    
    @classmethod
    def INPUT_TYPES(cls):
        lora_options = ["None"] + cls._get_platform_filtered_loras()
        # ... define inputs (copy from existing node and modify)
    
    # ... implement load_multi_loras method
```

3. **Register in node**:
```python
NODE_CLASS_MAPPINGS = {
    "Multi-LoRA Loader YourPlatform": MultiLoRALoaderYourPlatform,
}
```

4. **Restart ComfyUI** - Auto-import will pick it up!

## Planned Platform Nodes

Future platform-specific nodes to create:
- **Multi-LoRA Loader (Flux)** - For Flux LoRAs
- **Multi-LoRA Loader (SDXL)** - For SDXL LoRAs  
- **Multi-LoRA Loader (SD3.5 Medium)** - For SD3.5 Medium
- **Multi-LoRA Loader (SD3.5 Large)** - For SD3.5 Large
- **Multi-LoRA Loader (Qwen)** - For Qwen LoRAs
- **Multi-LoRA Loader (Pony)** - For Pony LoRAs

## Usage Tips

### 1. **Choose the right node for your workflow**
   - Using Wan i2v? → Use "Multi-LoRA Loader (Wan i2v)"
   - Using Wan t2v? → Use "Multi-LoRA Loader (Wan t2v)"
   - Generic diffusion? → Use "Multi-LoRA Loader (Model Only)"
   - Standard SDXL/SD1.5? → Use "Multi-LoRA Loader v02"

### 2. **Use additional filters to narrow down**
   - Search by filename: `lightning, -slow`
   - Filter by category: `artstyle`
   - Check the `filtered_loras_list` output to see what matches

### 3. **Leverage trigger words**
   - Enable `query_civitai` to auto-fetch trigger words
   - Check `all_trigger_words` output
   - Use `prompt_with_triggers` output for complete prompt

### 4. **Run as subgraph**
   - Select multiple nodes
   - Run selection as subgraph
   - No copy-paste needed!

## Benefits

✅ **Manageable dropdown lists** - 50-200 items instead of 3600+  
✅ **Platform-optimized** - Each node tailored to its platform  
✅ **No manual filtering** - Platform directory filter automatic  
✅ **Consistent interface** - All nodes share same base features  
✅ **Easy to extend** - Add new platforms in minutes  
✅ **Database-backed** - Track usage, ratings, trigger words  
✅ **Civitai integration** - Auto-fetch trigger words  

## Technical Details

### How Directory Filtering Works

1. **At initialization**: `INPUT_TYPES()` is called
2. **Base class instantiated**: `_get_platform_filtered_loras()` called
3. **LoRAs scanned**: Only from `PLATFORM_DIRECTORY_FILTER` subdirectory
4. **Dropdowns populated**: With filtered list only
5. **Additional filters**: Still available at execution time

### Why This Approach Works

- ComfyUI's dropdown system requires static options at init time
- We filter at the **source** (directory level) before populating dropdowns
- Platform nodes are **separate** so each has its own filtered list
- No dynamic dropdown limitations - each node is pre-filtered

## Troubleshooting

### No LoRAs showing in dropdown
- Check that your directory structure matches `PLATFORM_DIRECTORY_FILTER`
- Verify LoRAs exist in the filtered directory
- Check console for "[PlatformName] Found X LoRAs" message

### Wrong LoRAs showing
- Verify you're using the correct platform-specific node
- Check `filter_info` output to see active filters
- Ensure directory structure matches expected pattern

### Node not appearing in ComfyUI
- Restart ComfyUI completely
- Check console for import errors
- Verify file is in `nodes/` directory

## License

Same as parent Metadata_system project.
