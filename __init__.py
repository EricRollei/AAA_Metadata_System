# AAA_Metadata_System/__init__.py
import importlib.util
import os
import sys
import shutil

# Add this import for ComfyUI paths
try:
    import folder_paths
except ImportError:
    folder_paths = None

# NumExpr logs a noisy warning when it detects many cores without guidance; cap to ComfyUI's default unless user sets it
if "NUMEXPR_MAX_THREADS" not in os.environ:
    os.environ["NUMEXPR_MAX_THREADS"] = "8"

# Make this package importable as both its folder name and as 'AAA_Metadata_System'
# This allows: from AAA_Metadata_System import MetadataService
sys.modules['AAA_Metadata_System'] = sys.modules.get(__name__, sys.modules[__name__])

# Export core functionality for easy access
from .eric_metadata.service import MetadataService
from .eric_metadata.handlers.base import BaseHandler
from .eric_metadata.handlers.xmp import XMPSidecarHandler
from .eric_metadata.handlers.embedded import EmbeddedMetadataHandler
from .eric_metadata.handlers.txt import TxtFileHandler
from .eric_metadata.handlers.db import DatabaseHandler
from .eric_metadata.hooks.runtime_capture import auto_enable_from_env

# Initialize node mappings
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Get the nodes directory
def get_nodes_dir(subpath=None, mkdir=False):
    dir = os.path.dirname(__file__)
    if subpath is not None:
        dir = os.path.join(dir, subpath)

    dir = os.path.abspath(dir)

    if mkdir and not os.path.exists(dir):
        os.makedirs(dir)
    return dir

# Copy web extensions to ComfyUI's main extensions directory
def install_web_extensions():
    if not folder_paths:
        print("[AAA_Metadata_System] Warning: folder_paths not available, web extensions may not work")
        return
        
    try:
        # Get the path to ComfyUI's web/extensions directory
        extension_path = os.path.join(os.path.dirname(folder_paths.__file__), "web", "extensions")
        my_extension_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")
        
        # Create MetadataSystem subfolder in ComfyUI extensions
        metadata_extension_path = os.path.join(extension_path, "MetadataSystem")
        os.makedirs(metadata_extension_path, exist_ok=True)
        
        # Clean up existing files in the MetadataSystem folder
        if os.path.exists(metadata_extension_path):
            for file in os.listdir(metadata_extension_path):
                file_path = os.path.join(metadata_extension_path, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        # Copy our extension files to ComfyUI's extensions/MetadataSystem directory
        if os.path.exists(my_extension_path):
            for file in os.listdir(my_extension_path):
                if file.endswith('.js'):
                    src = os.path.join(my_extension_path, file)
                    dst = os.path.join(metadata_extension_path, file)
                    print(f"[AAA_Metadata_System] Copying extension file: {file}")
                    shutil.copy2(src, dst)
                    
        print(f"[AAA_Metadata_System] Web extensions installed to: {metadata_extension_path}")
        
    except Exception as e:
        print(f"[AAA_Metadata_System] Error installing web extensions: {e}")

# Install web extensions
install_web_extensions()

# Enable runtime hooks if the environment flag requests it (defaults to off).
auto_enable_from_env()

# Import nodes from the nodes directory
nodes_dir = get_nodes_dir("nodes")
for file in os.listdir(nodes_dir):
    if not file.endswith(".py") or file.startswith("__"):
        continue
        
    name = os.path.splitext(file)[0]
    try:
        # Import the module
        imported_module = importlib.import_module(".nodes.{}".format(name), __name__)
        
        # Extract and update node mappings
        if hasattr(imported_module, 'NODE_CLASS_MAPPINGS'):
            NODE_CLASS_MAPPINGS.update(imported_module.NODE_CLASS_MAPPINGS)
            
        if hasattr(imported_module, 'NODE_DISPLAY_NAME_MAPPINGS'):
            NODE_DISPLAY_NAME_MAPPINGS.update(imported_module.NODE_DISPLAY_NAME_MAPPINGS)
            
        print(f"Loaded node module: {name}")
    except Exception as e:
        print(f"Error loading node module {name}: {str(e)}")

# Version info
__version__ = "0.1.0"

# Add web directory for UI components if needed
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]