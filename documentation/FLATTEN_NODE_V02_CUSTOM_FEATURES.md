# Flatten Node v0.2 - Custom Features Guide

## New Features Added (October 2025)

The Flatten Node v0.2 now includes powerful customization options for organizing your files exactly how you want them.

---

## 🎯 Feature #1: Custom Extension Mappings

**Parameter:** `custom_type_mappings`  
**Format:** JSON string

### What It Does
Map specific file extensions directly to custom folder names. This allows you to create completely custom file type categories.

### Example Use Cases

#### 1. Organize PDFs into "Documents" folder
```json
{".pdf": "documents"}
```
Result: All `.pdf` files go to `/documents/` instead of `/text/`

#### 2. Separate RAW photos from regular images
```json
{
  ".cr2": "raw_photos",
  ".nef": "raw_photos",
  ".arw": "raw_photos",
  ".dng": "raw_photos"
}
```
Result: RAW files go to `/raw_photos/`, JPEGs still go to `/images/`

#### 3. Organize by project file types
```json
{
  ".psd": "photoshop_files",
  ".ai": "illustrator_files",
  ".indd": "indesign_files",
  ".svg": "vectors"
}
```

#### 4. Archive and compressed files
```json
{
  ".zip": "archives",
  ".rar": "archives",
  ".7z": "archives",
  ".tar": "archives",
  ".gz": "archives"
}
```

### How To Use
1. In the node, find the `custom_type_mappings` field
2. Enter valid JSON with extension-to-folder mappings
3. Extensions must include the dot (`.pdf`, not `pdf`)
4. Folder names should be lowercase with underscores/hyphens

---

## 📂 Feature #2: Custom Folder Name Mappings

**Parameter:** `custom_folder_mappings`  
**Format:** JSON string

### What It Does
Rename the default type folders (images, movies, text, etc.) to custom names you prefer.

### Example Use Cases

#### 1. Use your preferred naming convention
```json
{
  "images": "photos",
  "movies": "videos",
  "text": "documents"
}
```
Result: 
- `images/` becomes `photos/`
- `movies/` becomes `videos/`
- `text/` becomes `documents/`

#### 2. Create project-specific organization
```json
{
  "movies": "old-movies",
  "images": "family-photos",
  "text": "letters"
}
```

#### 3. Multiple versions/archives
```json
{
  "images": "images_backup_2025",
  "movies": "video_archive_oct"
}
```

### How To Use
1. Find the `custom_folder_mappings` field
2. Enter JSON mapping standard types to your preferred names
3. Standard types: `images`, `movies`, `text`, `sidecars`, `other`

---

## 🏷️ Feature #3: Source Folder Name Preservation

**Parameter:** `preserve_source_folder`  
**Options:** `none`, `prefix`, `suffix`

### What It Does
Adds the source folder name to the filename so you can track where files came from after flattening.

### Examples

Original structure:
```
scraped_content/
  ├── instagram/
  │   └── user123/
  │       ├── image001.jpg
  │       └── image002.jpg
  └── twitter/
      └── artist456/
          └── photo.jpg
```

#### Using `prefix` mode:
```
flattened/
  ├── user123_image001.jpg
  ├── user123_image002.jpg
  └── artist456_photo.jpg
```

#### Using `suffix` mode:
```
flattened/
  ├── image001_user123.jpg
  ├── image002_user123.jpg
  └── photo_artist456.jpg
```

#### Using `none` mode:
```
flattened/
  ├── image001.jpg
  ├── image002.jpg
  └── photo.jpg
```

### Smart Behavior
- Type folder names (images, movies, text, etc.) are **NOT** added to filenames
- Only meaningful parent folder names are preserved
- Prevents filenames like `images_photo.jpg`

### Use Cases
1. **Track sources:** Know which Instagram/Twitter/website each file came from
2. **Prevent conflicts:** Different folders might have same filename
3. **Maintain context:** Keep organizational hints in the filename itself

---

## 💡 Combining Features

You can use all three features together for powerful custom workflows!

### Example: Complete Custom Organization

**Scenario:** You're archiving scraped social media content with various file types

**Settings:**
```
preserve_source_folder: prefix
organize_by_type: true

custom_type_mappings:
{
  ".pdf": "documents",
  ".gif": "animations",
  ".webp": "images"
}

custom_folder_mappings:
{
  "movies": "videos",
  "images": "photos"
}
```

**Before:**
```
scraped/
  ├── instagram/
  │   └── artist123/
  │       ├── art.jpg
  │       ├── comic.pdf
  │       └── animated.gif
  └── twitter/
      └── photos/
          ├── pic.webp
          └── video.mp4
```

**After:**
```
organized/
  ├── photos/
  │   ├── artist123_art.jpg
  │   └── photos_pic.webp
  ├── videos/
  │   └── photos_video.mp4
  ├── documents/
  │   └── artist123_comic.pdf
  └── animations/
      └── artist123_animated.gif
```

---

## 📋 JSON Syntax Tips

### Valid JSON Examples ✅
```json
{".pdf": "documents"}
```
```json
{".pdf": "documents", ".doc": "documents", ".txt": "text_files"}
```
```json
{
  "images": "photos",
  "movies": "old-movies"
}
```

### Invalid JSON Examples ❌
```json
{.pdf: "documents"}              // Missing quotes around key
```
```json
{".pdf": "documents",}           // Trailing comma
```
```json
{"images": "photos" "movies": "videos"}  // Missing comma
```
```json
{'.pdf': 'documents'}            // Must use double quotes
```

### Testing Your JSON
1. Use an online JSON validator before pasting
2. Watch the ComfyUI console for "WARNING: Invalid JSON" messages
3. The node will still run but ignore invalid JSON

---

## 🎯 Common Workflows

### 1. Professional Photographer Workflow
```
custom_type_mappings:
{
  ".cr2": "raw",
  ".nef": "raw",
  ".arw": "raw",
  ".xmp": "metadata"
}

custom_folder_mappings:
{
  "images": "exports",
  "movies": "videos"
}

preserve_source_folder: prefix
```

### 2. Content Archiver Workflow
```
preserve_source_folder: prefix
organize_by_type: true

custom_folder_mappings:
{
  "movies": "videos",
  "images": "pictures"
}
```

### 3. Project Asset Organizer
```
custom_type_mappings:
{
  ".psd": "photoshop",
  ".ai": "illustrator",
  ".blend": "blender",
  ".fbx": "3d_models",
  ".obj": "3d_models"
}

organize_by_type: true
preserve_source_folder: suffix
```

---

## 🔧 Technical Notes

- **Custom extension mappings** are checked first, before standard type detection
- **Custom folder mappings** only affect the folder name, not which files go there
- **Source folder preservation** skips type folder names automatically
- All features respect the `organize_by_type` setting
- JSON parsing errors are logged but won't stop the operation
- Empty strings in parameters are safely ignored

---

## 📝 Version History

**v0.2.1** (October 2025)
- Added custom extension to folder mappings
- Added custom type folder name mappings  
- Added source folder name preservation (prefix/suffix)
- Fixed over-nesting issue with type folders

**v0.2.0** (October 2025)
- Initial release with paired file support
- Configurable flatten depth
- Multiple operation modes

---

## 🆘 Troubleshooting

**Custom folders not being created?**
- Check `organize_by_type` is enabled
- Verify JSON syntax is valid
- Check console for error messages

**Filenames not getting folder prefixes?**
- Ensure `preserve_source_folder` is set to "prefix" or "suffix"
- Check that source folder isn't a type folder name

**Some extensions not being sorted correctly?**
- Ensure extensions in JSON start with a dot: `.pdf` not `pdf`
- Check for typos in extension names
- Verify JSON syntax with a validator

---

Author: Eric Hiss  
Contact: eric@historic.camera, eric@rollei.us  
License: Dual License (Non-Commercial and Commercial Use)
