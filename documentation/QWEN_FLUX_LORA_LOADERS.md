# Qwen and Flux Multi-LoRA Loaders

## 🎉 New Nodes Created

### 1. Multi-LoRA Loader (Qwen)
**File**: `Multi_LoRA_Loader_Qwen.py`

**Configuration**:
- **Platform Name**: Qwen
- **Directory Filter**: `Lora\Qwen\`
- **CLIP Support**: No (model-only)
- **Default Architecture**: Qwen
- **Default Strength**: 1.0
- **Category**: `loaders/multi-lora/qwen`

**Features**:
- Scans only: `L:\stable-diffusion-webui\models\Lora\Qwen\`
- Model-only loading (no CLIP)
- 8 LoRA slots
- Optimized for Qwen vision/language models

**Categories**:
- Any, unknown, style, character, concept, tool, enhancement, effect

---

### 2. Multi-LoRA Loader (Flux)
**File**: `Multi_LoRA_Loader_Flux.py`

**Configuration**:
- **Platform Name**: Flux
- **Directory Filter**: `Lora\Flux\`
- **CLIP Support**: Yes
- **Default Architecture**: Flux
- **Default Strength**: 0.8 (model), 1.0 (CLIP)
- **Category**: `loaders/multi-lora/flux`

**Features**:
- Scans only: `L:\stable-diffusion-webui\models\Lora\Flux\`
- Full CLIP support for image generation
- 8 LoRA slots with separate model and CLIP strength controls
- Optimized for Flux image generation workflows

**Categories**:
- Any, unknown, style, character, concept, pose, clothing, background, effect, artistic, photographic, lighting, mood, texture, enhancement

---

## 🚀 How to Use

### Step 1: Restart ComfyUI
Close and restart ComfyUI to load the new nodes.

### Step 2: Verify Loading
Check the console for:
```
[Qwen] Found X LoRAs
[Flux] Found X LoRAs
```

If you see `Found 0 LoRAs`:
- Verify directories exist:
  - `L:\stable-diffusion-webui\models\Lora\Qwen\`
  - `L:\stable-diffusion-webui\models\Lora\Flux\`
- Add some LoRA files to those directories

### Step 3: Add Nodes in ComfyUI

**For Qwen**:
```
Right-click → Add Node → loaders → multi-lora → qwen
→ Select: "Multi-LoRA Loader (Qwen)"
```

**For Flux**:
```
Right-click → Add Node → loaders → multi-lora → flux
→ Select: "Multi-LoRA Loader (Flux)"
```

### Step 4: Connect and Configure

**Qwen Workflow** (Model-only):
```
[Qwen Model Loader]
        ↓ MODEL
[Multi-LoRA Loader (Qwen)]
        ↓ MODEL
[Qwen Sampler/Processor]
```

**Flux Workflow** (With CLIP):
```
[Flux Model Loader]
        ↓ MODEL, CLIP
[Multi-LoRA Loader (Flux)]
        ↓ MODEL, CLIP
[CLIP Text Encode]
        ↓
[KSampler]
```

---

## 📊 Complete Node Lineup

You now have **6 platform-specific Multi-LoRA loaders**:

| Node | Platform | CLIP | Directory | Use Case |
|------|----------|------|-----------|----------|
| Multi-LoRA Loader (Wan i2v) | Wan | ❌ | `Wan\i2v\` | Wan Image-to-Video |
| Multi-LoRA Loader (Wan t2v) | Wan | ❌ | `Wan\t2v\` | Wan Text-to-Video |
| Multi-LoRA Loader (Qwen) | Qwen | ❌ | `Qwen\` | Qwen Vision/Language |
| Multi-LoRA Loader (Flux) | Flux | ✅ | `Flux\` | Flux Image Generation |
| Multi-LoRA Loader (Model Only) | Generic | ❌ | All | Generic Diffusion Models |
| Multi-LoRA Loader v02 | Generic | ✅ | All | SDXL/SD1.5/General |

---

## 🎯 Key Differences

### Qwen vs Flux

**Qwen** (Model-Only):
- No CLIP input/output
- No clip_strength parameters
- Single strength per LoRA
- Optimized for vision/language models
- Returns: `(model, prompt, prompt_with_triggers, ...)`

**Flux** (With CLIP):
- Requires CLIP input
- Returns CLIP output
- Separate model and clip_strength per LoRA
- Optimized for image generation
- Returns: `(model, clip, prompt, prompt_with_triggers, ...)`

---

## 💡 Usage Tips

### For Qwen:
1. **Connect model only** - No CLIP needed
2. **Default strength 1.0** works well
3. **Categories**: Focus on tool, enhancement, effect
4. **Prompts**: Can be natural language descriptions

### For Flux:
1. **Connect both model and CLIP**
2. **Model strength 0.8, CLIP 1.0** recommended defaults
3. **Categories**: Style, artistic, photographic work well
4. **Prompts**: Use standard Flux prompt format
5. **Trigger words**: Enable Civitai query for best results

### General Tips:
- **Additional filtering**: Use search_filename to narrow down
- **Check outputs**: Connect `filtered_loras_list` to text display
- **Trigger words**: Use `prompt_with_triggers` output
- **Civitai integration**: Enable `query_civitai` for automatic trigger word fetching

---

## 🔧 Troubleshooting

### Qwen Node Issues:

**Problem**: No LoRAs showing
- **Solution**: Create `L:\stable-diffusion-webui\models\Lora\Qwen\` directory
- Add some `.safetensors` files to that directory

**Problem**: LoRAs not loading
- **Solution**: Check console for errors
- Verify LoRA files are compatible with Qwen

### Flux Node Issues:

**Problem**: Missing CLIP input error
- **Solution**: Flux requires CLIP! Connect CLIP input from model loader
- Use the dual-output Flux model loader

**Problem**: Different results than expected
- **Solution**: Adjust clip_strength separately from model strength
- Try model: 0.8, clip: 1.0 as starting point

---

## 📈 Benefits Summary

### Before:
```
❌ Dropdown with 3600+ LoRAs (unusable)
❌ Manual filtering required
❌ Can't tell which LoRAs are for which platform
```

### After:
```
✅ Qwen dropdown: ~20-50 Qwen LoRAs only
✅ Flux dropdown: ~100-200 Flux LoRAs only  
✅ Wan i2v dropdown: ~50-80 Wan i2v LoRAs only
✅ Wan t2v dropdown: ~60-100 Wan t2v LoRAs only
✅ Clear platform separation
✅ No manual filtering needed
✅ Direct dropdown selection
```

---

## 🚀 Next Steps

### Want More Platforms?

Easy to add using the template! Popular platforms to add:

1. **SDXL** - For Stable Diffusion XL LoRAs
   - Directory: `SDXL\`
   - CLIP: Yes
   - Time: 5-10 minutes

2. **SD3.5 Medium** - For SD3.5 Medium LoRAs
   - Directory: `SD3.5\Medium\` or `SD35\Medium\`
   - CLIP: Yes
   - Time: 5-10 minutes

3. **SD3.5 Large** - For SD3.5 Large LoRAs
   - Directory: `SD3.5\Large\` or `SD35\Large\`
   - CLIP: Yes
   - Time: 5-10 minutes

4. **Pony** - For Pony Diffusion LoRAs
   - Directory: `Pony\`
   - CLIP: Yes
   - Time: 5-10 minutes

### How to Add:
1. Copy `TEMPLATE_Multi_LoRA_Loader_Platform.py`
2. Search/replace 5 values
3. Restart ComfyUI
4. Done!

---

## ✨ Summary

You now have **Qwen** and **Flux** platform-specific LoRA loaders!

**Qwen**: Perfect for vision/language models, model-only  
**Flux**: Optimized for image generation, full CLIP support  

Both nodes:
- ✅ Show only relevant LoRAs in dropdowns
- ✅ No manual filtering needed
- ✅ Database integration
- ✅ Civitai API support
- ✅ Trigger word management
- ✅ Usage tracking

Enjoy your new organized LoRA workflow! 🎉
