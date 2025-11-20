# Configuration Guide

## Overview

The AAA Metadata System can be configured via `config.json` in the root directory. This file controls various system behaviors including runtime hooks, debug mode, and caching.

## Configuration File Location

```
ComfyUI/custom_nodes/AAA_Metadata_System/config.json
```

## Configuration Options

### Runtime Hooks

```json
{
  "runtime_hooks": {
    "enabled": false
  }
}
```

**What it does:** Enables runtime execution hooks to capture actual node execution data (values after conditional logic, execution order, timestamps).

**Performance impact:** ~0.2% overhead (negligible)

**Safety:** All safety principles implemented (opt-in, conflict detection, session isolation, exception handling)

**When to enable:**
- ✅ You want maximum metadata accuracy
- ✅ You use conditional workflows (switch nodes, etc.)
- ✅ You're comfortable with alpha/beta features
- ✅ Single-user ComfyUI instance

**When to keep disabled:**
- ⚠️ You use many custom extensions (potential conflicts)
- ⚠️ Production/shared ComfyUI server
- ⚠️ You prioritize absolute stability over metadata accuracy

**Requires:** ComfyUI restart to take effect

### Debug Mode

```json
{
  "debug": {
    "enabled": false
  }
}
```

**What it does:** Enables detailed debug logging for troubleshooting.

**When to enable:** When investigating issues or reporting bugs

### Hash Caching

```json
{
  "metadata": {
    "enable_hash_cache": true
  }
}
```

**What it does:** Caches model/LoRA hash calculations in `.sha256` files for ~1000x faster subsequent runs.

**Performance impact:** First hash takes ~1-2 seconds, subsequent lookups < 1ms

**When to disable:** If you want to force re-calculation of all hashes (rarely needed)

## Priority System

Settings can be controlled via multiple methods with the following priority order:

### For Runtime Hooks

1. **Environment Variable** (highest priority)
   ```powershell
   # PowerShell
   $env:AAA_METADATA_ENABLE_HOOKS = "true"
   
   # Batch file
   set AAA_METADATA_ENABLE_HOOKS=true
   ```

2. **Config File**
   ```json
   {"runtime_hooks": {"enabled": true}}
   ```

3. **Default** (lowest priority)
   ```
   false (disabled)
   ```

### Why Environment Variable Wins

The environment variable always takes precedence to allow easy testing without modifying config files:

```powershell
# Test with hooks enabled
$env:AAA_METADATA_ENABLE_HOOKS = "true"
.\run_nvidia_gpu.bat

# Test with hooks disabled (even if config.json says enabled)
$env:AAA_METADATA_ENABLE_HOOKS = "false"
.\run_nvidia_gpu.bat
```

## Configuration Methods

### Method 1: Edit config.json (Recommended for Permanent Settings)

1. Open `config.json` in a text editor
2. Change settings as needed
3. Save file
4. Restart ComfyUI

**Pros:** Persistent, version-controlled, easy to backup  
**Cons:** Requires restart

### Method 2: Environment Variable (Recommended for Testing)

**Session-specific (PowerShell):**
```powershell
$env:AAA_METADATA_ENABLE_HOOKS = "true"
.\run_nvidia_gpu.bat
```

**Permanent (Windows System Settings):**
1. Win+R → `sysdm.cpl`
2. Advanced → Environment Variables
3. Add `AAA_METADATA_ENABLE_HOOKS` = `true`

**Batch File (Automatic):**
Add to `run_nvidia_gpu.bat`:
```batch
set AAA_METADATA_ENABLE_HOOKS=true
```

**Pros:** Easy to test, doesn't modify files  
**Cons:** Session-specific (unless made system-wide)

### Method 3: Per-Node UI Toggle (Recommended)

**Status:** ✅ Implemented (Phase 4.4 complete)

**How to use:**
1. Open any workflow in ComfyUI
2. Find your save node (MetadataAwareSaveImage)
3. Scroll down to the `enable_runtime_hooks` dropdown
4. Select your preference:
   - **"Auto (use config)"** - Uses config.json setting (default)
   - **"Enabled"** - Forces hooks ON for this workflow only
   - **"Disabled"** - Forces hooks OFF for this workflow only
5. No restart required! Takes effect immediately

**Priority system:**
```
Per-node setting > config.json > default (false)
```

**Best for:** 
- ✅ Per-workflow control without restart
- ✅ Testing hooks on specific workflows
- ✅ Disabling hooks for problematic workflows while keeping globally enabled
- ✅ Overriding config for specific use cases

**Example use cases:**
- Config has hooks **disabled**, but you want them **enabled** for one workflow → Set to "Enabled"
- Config has hooks **enabled**, but one workflow has conflicts → Set to "Disabled"
- You want standard behavior → Leave on "Auto (use config)"

**Notes:**
- Changes take effect immediately (no restart)
- Per-node setting always wins when explicitly set
- "Auto" and leaving blank both use config.json

## Verification

Check if runtime hooks are enabled:

```powershell
# Look for this in ComfyUI startup logs:
[AAA Metadata Hooks] Runtime hooks enabled
```

Check metadata in saved images:
```json
{
  "ai_info": {
    "provenance": {
      "capture_mode": "parser+hooks"  // Hooks enabled
      // or
      "capture_mode": "parser"        // Hooks disabled
    }
  }
}
```

## Troubleshooting

### Hooks Not Enabling

**Problem:** Set `config.json` to `true` but hooks still disabled

**Solutions:**
1. Check for environment variable override: `$env:AAA_METADATA_ENABLE_HOOKS`
2. Verify config.json syntax (must be valid JSON)
3. Restart ComfyUI completely
4. Check startup logs for conflicts

### Config Changes Not Taking Effect

**Problem:** Changed `config.json` but nothing happened

**Solution:** Restart ComfyUI (config is loaded at startup)

### Hook Conflicts

**Problem:** `[AAA Metadata Hooks] pre_execute already wrapped`

**Solution:** Another extension is using hooks. Options:
1. Disable our hooks (no functionality loss - parser still works)
2. Change extension load order
3. Contact other extension author for coordination

## Examples

### Development Setup
```json
{
  "runtime_hooks": {"enabled": true},
  "debug": {"enabled": true},
  "metadata": {"enable_hash_cache": true}
}
```

### Production Setup (Conservative)
```json
{
  "runtime_hooks": {"enabled": false},
  "debug": {"enabled": false},
  "metadata": {"enable_hash_cache": true}
}
```

### Testing Environment Variable Override
```powershell
# Config says false, but enable for this session:
$env:AAA_METADATA_ENABLE_HOOKS = "true"
.\run_nvidia_gpu.bat

# Metadata will show: "capture_mode": "parser+hooks"
```

## Advanced Usage

### Reload Config Without Restart (Python)

```python
from eric_metadata.utils.config import reload_config

# Reload configuration from disk
new_config = reload_config()
print(f"Runtime hooks enabled: {new_config['runtime_hooks']['enabled']}")
```

**Note:** Reloading config doesn't enable/disable hooks mid-session. Hooks are registered at startup.

### Check Current Config (Python)

```python
from eric_metadata.utils.config import get_runtime_hooks_enabled, get_debug_enabled

print(f"Hooks: {get_runtime_hooks_enabled()}")
print(f"Debug: {get_debug_enabled()}")
```

## Related Documentation

- **Runtime Hooks Safety:** `documentation/SAFE_RUNTIME_HOOKS_RESEARCH.md`
- **Implementation Plan:** `documentation/runtime_hook_implementation_plan.md`
- **Edit Log:** `documentation/edit_log.md`

## Support

For issues or questions:
- Check logs for error messages
- Review `SAFE_RUNTIME_HOOKS_RESEARCH.md` for troubleshooting
- Report issues with: config.json content, startup logs, OS/ComfyUI version
