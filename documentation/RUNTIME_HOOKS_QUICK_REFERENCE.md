# Runtime Hooks Quick Reference

## Enable Runtime Hooks

**Method 1: Per-Node Toggle (Recommended - No Restart Required!) ✨**

In your workflow's save node:
1. Find the `enable_runtime_hooks` dropdown
2. Select:
   - **"Auto (use config)"** - Use config.json setting (default)
   - **"Enabled"** - Force ON for this workflow
   - **"Disabled"** - Force OFF for this workflow
3. Save/run - takes effect immediately!

**Priority:** Per-node > Config > Default

**Use cases:**
- Override config for specific workflows
- Test hooks without changing config
- Disable for problematic workflows

---

**Method 2: Config File (Recommended for global setting)**
```json
{
  "runtime_hooks": {
    "enabled": true
  }
}
```
Restart ComfyUI after editing `config.json`

**Method 3: Environment Variable (Recommended for testing)**
```powershell
$env:AAA_METADATA_ENABLE_HOOKS = "true"
.\run_nvidia_gpu.bat
```

---

## Debug Features

### See Hook Performance
```json
{
  "runtime_hooks": {
    "enabled": true,
    "log_performance": true
  },
  "debug": {
    "enabled": true
  }
}
```
**Output:** `[AAA Metadata Hooks] Performance: ... - 47 calls, total=1.23ms, avg=0.026ms, max=0.089ms`

### See Parser Disagreements
```json
{
  "runtime_hooks": {
    "enabled": true,
    "log_disagreements": true
  },
  "debug": {
    "enabled": true
  }
}
```
**Output:** `[MetadataSaveImage] Disagreement at 'ai_info.generation.sampler.steps': parser=20 → runtime=25`

---

## Tune Sidecar Threshold

**Default:** 32KB (good for most workflows)

**For smaller image files:**
```json
{
  "runtime_hooks": {
    "inline_size_limit_kb": 16
  }
}
```

**For maximum portability:**
```json
{
  "runtime_hooks": {
    "inline_size_limit_kb": 128
  }
}
```

---

## Check Hook Status

### In Metadata
Look for `capture_mode` in saved images:
- `"parser+hooks"` = Hooks enabled and working
- `"parser"` = Hooks disabled or not available

### In Logs (ComfyUI console)
```
[AAA Metadata Hooks] Runtime hooks enabled
```
or
```
[AAA Metadata Hooks] Runtime hooks disabled (config)
```

---

## Troubleshooting

### Hooks Not Enabling?
1. Check config.json syntax (must be valid JSON)
2. Verify environment variable: `$env:AAA_METADATA_ENABLE_HOOKS`
3. Restart ComfyUI completely
4. Check logs for conflict warnings

### Sidecar Files Every Time?
- Increase `inline_size_limit_kb` from 32 to 64 or 128
- Simplify workflow to generate less runtime data

### Performance Issues?
- Disable performance logging: `"log_performance": false`
- Check logs with performance enabled to measure actual overhead
- Disable hooks if overhead > 1%: `"enabled": false`

---

## Config Priority

From highest to lowest:
1. Environment variable `AAA_METADATA_ENABLE_HOOKS`
2. `config.json` file
3. Hardcoded defaults

**Tip:** Use environment variable for temporary testing without editing config

---

## Performance Expectations

- **Typical overhead:** 0.15% - 0.20%
- **With all logging enabled:** ~0.25%
- **Negligible impact:** Yes, for most workflows
- **Monitor via:** `log_performance` option

---

## Common Workflows

### Development/Debug Mode
```json
{
  "runtime_hooks": {
    "enabled": true,
    "log_disagreements": true,
    "log_performance": true,
    "inline_size_limit_kb": 32
  },
  "debug": {
    "enabled": true
  }
}
```

### Production Mode (Conservative)
```json
{
  "runtime_hooks": {
    "enabled": false
  },
  "debug": {
    "enabled": false
  }
}
```

### Production Mode (Maximum Accuracy)
```json
{
  "runtime_hooks": {
    "enabled": true,
    "log_disagreements": false,
    "log_performance": false,
    "inline_size_limit_kb": 32
  },
  "debug": {
    "enabled": false
  }
}
```

---

## Related Documentation

- **Full Guide:** `documentation/CONFIG_GUIDE.md`
- **Enhancements:** `documentation/RUNTIME_HOOKS_ENHANCEMENTS_SUMMARY.md`
- **Safety Research:** `documentation/SAFE_RUNTIME_HOOKS_RESEARCH.md`
- **Implementation Plan:** `documentation/runtime_hook_implementation_plan.md`

---

**Version:** 1.1.0  
**Last Updated:** 2025-11-19
