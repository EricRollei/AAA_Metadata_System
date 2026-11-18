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

# One copy of the pack under every name it is imported by: the name ComfyUI gives it,
# 'AAA_Metadata_System' and 'custom_nodes.AAA_Metadata_System' (see aaa_meta/pack_alias.py).
# This allows: from AAA_Metadata_System import MetadataService - also when the folder has
# another name - and stops the pack from starting a second time.
try:
    from .aaa_meta.pack_alias import install as _install_pack_alias
    if not _install_pack_alias(__name__) and os.environ.get("AAA_META_VERBOSE", "").strip().lower() in ("1", "true", "yes", "on"):
        print(f"[AAA Metadata] already loaded under another name; loading again as {__name__}")
except Exception as _alias_error:
    print(f"[AAA Metadata] import aliases not installed: {_alias_error!r}")
    sys.modules.setdefault('AAA_Metadata_System', sys.modules[__name__])

# Export core functionality for easy access
from .eric_metadata.service import MetadataService
# v2: measurements written through MetadataService also land in the eiqa namespace (AAA_META_MIRROR=0 disables)
try:
    from .aaa_meta.service_mirror import install as _install_v2_mirror
    _install_v2_mirror(MetadataService)
except Exception as _mirror_error:
    print(f"[AAA Metadata] v2 measurement mirror not installed: {_mirror_error!r}")
from .eric_metadata.handlers.base import BaseHandler
from .eric_metadata.handlers.xmp import XMPSidecarHandler
from .eric_metadata.handlers.embedded import EmbeddedMetadataHandler
from .eric_metadata.handlers.txt import TxtFileHandler
from .eric_metadata.handlers.db import DatabaseHandler

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
# TEMP FIX 2026-11-03: disabled. WEB_DIRECTORY = "./web" (below) already serves these files,
# so copying them into ComfyUI/web/extensions/MetadataSystem loaded every JS extension twice.
# See NOTES_2026-11-03_temp_fixes.md
INSTALL_LEGACY_WEB_COPY = False
if INSTALL_LEGACY_WEB_COPY:
    install_web_extensions()

# v2 capture core (aaa_meta): runtime hooks for automatic metadata collection.
# Disable with environment variable AAA_META_CAPTURE=0.
try:
    from .aaa_meta.capture import install as _install_v2_capture
    _install_v2_capture()
except Exception as _capture_error:
    print(f"[AAA Metadata] v2 capture not installed: {_capture_error}")

# Import nodes from the nodes directory
nodes_dir = get_nodes_dir("nodes")
for file in os.listdir(nodes_dir):
    # TEMP FIX 2026-11-03: skip TEMPLATE_ scaffolding files (not real nodes)
    if not file.endswith(".py") or file.startswith("__") or file.startswith("TEMPLATE_"):
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
            
        if os.environ.get("AAA_META_VERBOSE", "").strip().lower() in ("1", "true", "yes", "on"):
            print(f"Loaded node module: {name}")
    except Exception as e:
        print(f"Error loading node module {name}: {str(e)}")

# Workflows built with "Save Image with Metadata v099d" run the v1.0 code (same widgets, same order).
# AAA_META_KEEP_OLD_SAVE=1 keeps the original v099d behaviour.
try:
    from .nodes.eric_metadata_save_image_v100 import upgrade_old_ids as _upgrade_old_save_node
    _upgrade_old_save_node(NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS)
except Exception as _upgrade_error:
    print(f"[AAA Metadata] v099d save node not upgraded: {_upgrade_error!r}")

# Version info
__version__ = "0.2.0"

# Add web directory for UI components if needed
# v2: one menu tree for the whole pack, "Eric's Nodes/..." (AAA_META_KEEP_OLD_CATEGORIES=1 disables)
try:
    from .aaa_meta.categories import apply as _apply_category_tree
    _apply_category_tree(NODE_CLASS_MAPPINGS)
except Exception as _category_error:
    print(f"[AAA Metadata] category tree not applied: {_category_error!r}")
print(f"[AAA Metadata] {len(NODE_CLASS_MAPPINGS)} nodes loaded (set AAA_META_VERBOSE=1 for the full console output)")

# v2: nodes that have a newer version get " (deprecated)" and the Deprecated category (AAA_META_KEEP_OLD_LABELS=1 disables)
try:
    from .aaa_meta.deprecation import apply as _mark_deprecated
    _mark_deprecated(NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS)
except Exception as _deprecation_error:
    print(f"[AAA Metadata] deprecation labels not applied: {_deprecation_error!r}")

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]