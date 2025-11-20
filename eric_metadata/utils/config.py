"""Configuration loader for AAA Metadata System."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


_CONFIG_CACHE: Optional[Dict[str, Any]] = None
_CONFIG_PATH: Optional[Path] = None


def get_config_path() -> Path:
    """Get the path to the config.json file."""
    global _CONFIG_PATH
    if _CONFIG_PATH is not None:
        return _CONFIG_PATH
    
    # Get the root directory of the AAA_Metadata_System
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent
    config_path = root_dir / "config.json"
    
    _CONFIG_PATH = config_path
    return config_path


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json file.
    
    Returns:
        dict: Configuration dictionary with defaults for missing values
    """
    global _CONFIG_CACHE
    
    # Return cached config if available
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    # Default configuration
    default_config = {
        "runtime_hooks": {
            "enabled": False,
            "log_disagreements": False,
            "log_performance": False,
            "inline_size_limit_kb": 32
        },
        "debug": {
            "enabled": False
        },
        "metadata": {
            "enable_hash_cache": True
        }
    }
    
    config_path = get_config_path()
    
    # Try to load config file
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Merge with defaults (file config takes precedence)
            merged_config = _deep_merge(default_config, file_config)
            _CONFIG_CACHE = merged_config
            return merged_config
        except Exception as e:
            print(f"[AAA Metadata Config] Warning: Failed to load config.json: {e}")
            print(f"[AAA Metadata Config] Using default configuration")
    
    # No config file or failed to load - use defaults
    _CONFIG_CACHE = default_config
    return default_config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override values taking precedence.
    
    Args:
        base: Base dictionary with defaults
        override: Override dictionary with user values
        
    Returns:
        dict: Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        # Skip comment fields
        if key.startswith('_'):
            continue
            
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_runtime_hooks_enabled() -> bool:
    """
    Check if runtime hooks should be enabled.
    
    Priority order:
    1. Environment variable AAA_METADATA_ENABLE_HOOKS
    2. config.json runtime_hooks.enabled setting
    3. Default: False
    
    Returns:
        bool: True if runtime hooks should be enabled
    """
    # Check environment variable first (highest priority)
    env_value = os.environ.get("AAA_METADATA_ENABLE_HOOKS", "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False
    
    # Check config file
    config = load_config()
    return config.get("runtime_hooks", {}).get("enabled", False)


def get_debug_enabled() -> bool:
    """
    Check if debug mode should be enabled.
    
    Returns:
        bool: True if debug mode should be enabled
    """
    config = load_config()
    return config.get("debug", {}).get("enabled", False)


def get_hash_cache_enabled() -> bool:
    """
    Check if hash caching should be enabled.
    
    Returns:
        bool: True if hash caching should be enabled
    """
    config = load_config()
    return config.get("metadata", {}).get("enable_hash_cache", True)


def get_runtime_log_disagreements() -> bool:
    """
    Check if parser/hook disagreements should be logged.
    
    Returns:
        bool: True if disagreements should be logged
    """
    config = load_config()
    return config.get("runtime_hooks", {}).get("log_disagreements", False)


def get_runtime_log_performance() -> bool:
    """
    Check if runtime performance metrics should be logged.
    
    Returns:
        bool: True if performance should be logged
    """
    config = load_config()
    return config.get("runtime_hooks", {}).get("log_performance", False)


def get_runtime_inline_limit() -> int:
    """
    Get the inline size limit for runtime data in bytes.
    
    Returns:
        int: Size limit in bytes (default 32KB)
    """
    config = load_config()
    limit_kb = config.get("runtime_hooks", {}).get("inline_size_limit_kb", 32)
    return limit_kb * 1024


def reload_config() -> Dict[str, Any]:
    """
    Reload configuration from disk, clearing the cache.
    
    Returns:
        dict: Reloaded configuration
    """
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    return load_config()


__all__ = [
    "load_config",
    "get_config_path",
    "get_runtime_hooks_enabled",
    "get_debug_enabled",
    "get_hash_cache_enabled",
    "get_runtime_log_disagreements",
    "get_runtime_log_performance",
    "get_runtime_inline_limit",
    "reload_config",
]
