# Flatten Nested Files Node v0.2 - Enhancement Summary

## 🎯 Overview

The Flatten Nested Files Node has been significantly enhanced from a simple image flattener to an intelligent file organization tool that respects file relationships and existing organization.

## ✨ New Features

### 1. **Multiple File Type Support**
- **Images Only** - Process just image files (original behavior)
- **All Media** - Process images AND videos together
- **All Files** - Process all file types with organization options

### 2. **Paired File Recognition** 🔗
Automatically detects and keeps together:
- `image.jpg` + `image.xmp` (Adobe metadata)
- `image.jpg` + `image.json` (JSON metadata)
- `image.jpg` + `image.txt` (captions/descriptions)

**Example:**
```
Before:
  subfolder/
    photo001.jpg
    photo001.xmp
    photo001.txt

After (kept together):
  images/
    photo001.jpg
    photo001.xmp
    photo001.txt
```

### 3. **Configurable Flattening Depth** 📏
- **Depth 0** (default): Flatten everything to root
- **Depth 1**: Keep one level of subdirectories
- **Depth 2+**: Keep N levels of folder structure

**Example with depth=1:**
```
Before:
  A:\output\site1\user1\album1\photo.jpg
  
After:
  A:\output\site1\photo.jpg  (keeps "site1" level)
```

### 4. **Smart Folder Detection** 🧠
Automatically skips folders that are already organized:
- Detects existing `images/`, `movies/`, `text/` folders
- Won't create nested organization within organized folders
- Prevents the over-nesting issue you experienced!

### 5. **Three Operation Modes**

#### **flatten_only** (Default)
- Moves files to main directory (or to specified depth)
- No type organization
- Simple flattening

#### **flatten_and_organize**
- Flattens files to specified depth
- THEN organizes into type folders
- Best for cleaning up messy downloads

#### **organize_only**
- Organizes files within their current locations
- No flattening
- Good for adding structure without moving everything

### 6. **Flexible Sidecar Handling**
- **keep_with_images**: All sidecars stay with images (best for training)
- **separate_folder**: Sidecars go to dedicated `sidecars/` folder
- **keep_txt_only**: Only `.txt` files stay with images, others separated

## 🔧 Technical Implementation

### File Type Categories
```python
- images: .jpg, .jpeg, .png, .webp, .bmp, .tiff, .tif, .gif, .heic, .heif
- movies: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v, .mpg, .mpeg
- text: .txt, .md, .doc, .docx, .pdf, .rtf
- sidecars: .xmp, .json, .txt (paired with images)
- other: Everything else
```

### Paired File Logic
```python
# Tracks files by base name within each folder
paired_files[(folder, "photo001")] = [
    photo001.jpg,
    photo001.xmp,
    photo001.txt
]

# Moves them together as a group
```

### Organized Folder Detection
```python
def is_organized_folder(folder):
    """Folder is organized if it has 2+ type folders"""
    type_folders = {'images', 'movies', 'text', 'sidecars'}
    existing = {subfolder in folder if subfolder is type_folder}
    return len(existing) >= 2  # Has organization structure
```

## 📊 Usage Examples

### Example 1: Clean Up Web Scraper Output
```
Scenario: Over-nested folders from web scraper
Operation: flatten_and_organize
Settings:
  - flatten_depth: 0
  - respect_paired_files: True
  - skip_organized_folders: True
  - organize_by_type: True

Result: Clean single-level organization with paired files together
```

### Example 2: Add Structure Without Moving
```
Scenario: Files scattered in many subfolders, want type organization
Operation: organize_only
Settings:
  - organize_by_type: True
  - respect_paired_files: True
  
Result: Each subfolder gets its own images/, movies/, etc.
```

### Example 3: Partial Flatten
```
Scenario: Keep top-level folders but flatten everything below
Operation: flatten_only
Settings:
  - flatten_depth: 1
  - respect_paired_files: True
  
Result: Preserves first folder level, flattens everything below it
```

## 🎛️ Node Inputs

### Required
- **main_directory**: Root directory to process
- **operation_mode**: flatten_only | flatten_and_organize | organize_only

### Optional
- **file_types**: images_only | all_media | all_files
- **flatten_depth**: 0-10 (0 = flatten everything)
- **respect_paired_files**: Boolean (keep sidecars with images)
- **skip_organized_folders**: Boolean (skip folders with structure)
- **organize_by_type**: Boolean (create type subfolders)
- **sidecar_handling**: keep_with_images | separate_folder | keep_txt_only
- **remove_empty_folders**: Boolean (cleanup after processing)
- **dry_run**: Boolean (preview without changes)
- **handle_conflicts**: rename | skip | overwrite
- **max_scan_depth**: 1-50 (recursion limit)

## 📈 Node Outputs

1. **status_message**: Human-readable summary
2. **files_moved**: Total files processed
3. **paired_files_moved**: Count of files moved with paired sidecars
4. **stats_json**: Detailed statistics
5. **log_output**: Detailed operation log

## 🔄 Workflow Integration

### Use with Web Scraper
```
[Web Scraper Node] 
    ↓ (output_path)
[Flatten Nested Files v0.2]
    operation_mode: flatten_and_organize
    skip_organized_folders: True
    respect_paired_files: True
    ↓
Clean, organized output
```

### Use with File Organizer
```
[Flatten Nested Files v0.2]
    operation_mode: flatten_only
    ↓
[File Organizer Node]
    Create type subfolders
    Handle size filtering
    ↓
Organized with size filtering
```

## ⚠️ Important Notes

1. **Paired Files**: When enabled, ALL files sharing the same base name in a folder move together
2. **Organized Folders**: Detection prevents re-organizing already structured folders
3. **Depth Counting**: Starts from main_directory as level 0
4. **Dry Run**: Always test with dry_run=True first on important data!
5. **Conflict Handling**: "rename" adds (1), (2) suffix - safest option

## 🐛 Fixes from v0.1

- ✅ Now handles ALL file types, not just images
- ✅ Recognizes paired files (sidecars)
- ✅ Respects existing organization
- ✅ Configurable flattening depth
- ✅ Three distinct operation modes
- ✅ Better stats and logging
- ✅ Compatible with file-organizer node patterns

## 🎉 Benefits

- **Fixes over-nesting**: Won't create nested type folders
- **Preserves relationships**: Keeps sidecars with images
- **Flexible**: Three modes for different scenarios
- **Safe**: Dry run and smart folder detection
- **Detailed**: Comprehensive stats and logging
- **Training-ready**: Keeps captions with images

## 📝 Version History

- **v0.1**: Simple image flattening only
- **v0.2**: Multi-type support, paired files, depth control, smart detection