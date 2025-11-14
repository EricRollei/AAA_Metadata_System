# Installation Guide

This guide provides detailed instructions for installing the Metadata System for ComfyUI.

## Requirements

### System Requirements

- Python 3.8+
- ComfyUI (latest version recommended)
- 50MB disk space for the system and dependencies

### Optional Dependencies

- **PyExiv2**: For enhanced embedded metadata support
- **ExifTool**: For additional format support
- **SQLite**: For database functionality (included in Python)

## Installation Methods

### Method 1: Install as ComfyUI Custom Node (Recommended)

1. **Clone the repository** into your ComfyUI custom_nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EricRollei/Metadata_system.git
```

2. **Install required dependencies**:

```bash
cd Metadata_system
pip install -r requirements.txt
```

3. **Restart ComfyUI** to load the new nodes

This method integrates the system directly with ComfyUI and makes all nodes immediately available.

### Method 2: Install as Python Package

1. **Clone the repository**:

```bash
git clone https://github.com/EricRollei/Metadata_system.git
cd Metadata_system
```

2. **Install using pip**:

```bash
pip install .
# Or for development installation:
pip install -e .
```

3. **Verify installation**:

```bash
python -c "from Metadata_system import MetadataService; print('Installation successful!')"
```

This method allows you to use the metadata system in your Python code, but does not automatically integrate the nodes with ComfyUI.

## Installing Optional Dependencies

### PyExiv2

PyExiv2 provides enhanced metadata support for many image formats:

```bash
pip install pyexiv2
```

If you encounter issues with PyExiv2 installation:

- **Windows**: Install the pre-built wheels:
  ```bash
  pip install https://github.com/LeoHsiao1/pyexiv2/releases/download/v2.7.1/pyexiv2-2.7.1-cp39-cp39-win_amd64.whl
  ```
  (Choose the appropriate version for your Python version and platform)

- **Linux**: Install required libraries first:
  ```bash
  apt-get update && apt-get install -y libexiv2-dev
  pip install pyexiv2
  ```

- **macOS**: Use Homebrew:
  ```bash
  brew install exiv2
  pip install pyexiv2
  ```

### ExifTool

ExifTool provides support for additional file formats:

1. **Download ExifTool**:
   - Windows: [Download the Windows EXE](https://exiftool.org/exiftool-12.60.zip)
   - Linux: `apt-get install exiftool` or `yum install perl-Image-ExifTool`
   - macOS: `brew install exiftool`

2. **Ensure ExifTool is in your PATH**:
   - Windows: Add the ExifTool directory to your system PATH
   - Linux/macOS: Usually installed in a location already in PATH

3. **Verify installation**:
   ```bash
   exiftool -ver
   ```

## Configuration

The system works with default settings, but you can configure it for better performance.

### Database Location

By default, the database is created in the current working directory. To specify a custom location:

```python
from Metadata_system.handlers.db import DatabaseHandler

# Specify custom database path
db = DatabaseHandler(db_path="/path/to/your/metadata.db")
```

### Human-readable Text Format

Enable or disable human-readable text format:

```python
from Metadata_system import MetadataService

# Enable human-readable text format
service = MetadataService(human_readable_text=True)

# Or change at runtime
service.set_text_format(human_readable=True)
```

### Debug Mode

Enable debug mode for detailed logging:

```python
from Metadata_system import MetadataService

# Enable debug mode
service = MetadataService(debug=True)
```

## Troubleshooting

### Common Installation Issues

**Issue**: `ImportError: No module named 'Metadata_system'`
**Solution**: Ensure the installation directory is in your Python path or install as a package.

**Issue**: `ModuleNotFoundError: No module named 'pyexiv2'`
**Solution**: Install PyExiv2 using the instructions above.

**Issue**: `FileNotFoundError: [Errno 2] No such file or directory: 'exiftool'`
**Solution**: Install ExifTool and ensure it's in your PATH.

**Issue**: ComfyUI nodes not appearing
**Solution**: Make sure you've installed in the correct custom_nodes directory and restarted ComfyUI.

### Testing Your Installation

Run the provided tests to verify your installation:

```bash
cd Metadata_system
python -m pytest tests/
```

Or test basic functionality:

```python
from Metadata_system import MetadataService

# Create a service
service = MetadataService(debug=True)

# Write basic metadata
metadata = {'basic': {'title': 'Test'}}
result = service.write_metadata('test.jpg', metadata)

print(f"Write result: {result}")
```

## Updating

To update to the latest version:

```bash
cd ComfyUI/custom_nodes/Metadata_system
git pull
pip install -r requirements.txt
```

Restart ComfyUI after updating.

## Uninstallation

To remove the system:

1. Remove the directory:
   ```bash
   rm -rf ComfyUI/custom_nodes/Metadata_system
   ```

2. If installed as a package:
   ```bash
   pip uninstall Metadata_system
   ```

## Next Steps

Once installed, refer to the [USAGE_GUIDE.md](USAGE_GUIDE.md) for detailed usage instructions or check the [README.md](README.md) for a quick start.