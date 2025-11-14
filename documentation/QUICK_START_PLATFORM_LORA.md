# Quick Start: Platform-Specific Multi-LoRA Loaders

## 🎯 What Problem Does This Solve?

**Before**: One dropdown with 3600+ LoRAs → Unusable!  
**After**: Platform-specific nodes with 50-200 LoRAs each → Perfect! ✓

## 🚀 Quick Start (2 minutes)

### Step 1: Restart ComfyUI
```bash
# Close and restart ComfyUI to load the new nodes
```

### Step 2: Add Node
In ComfyUI:
- Right-click → Add Node → loaders → multi-lora → wan
- Select: **"Multi-LoRA Loader (Wan i2v)"** or **"Multi-LoRA Loader (Wan t2v)"**

### Step 3: Connect & Configure
```
[Wan Model Loader] 
        ↓ MODEL
[Multi-LoRA Loader (Wan i2v)]
        ↓ MODEL
[Wan Sampler]
```

### Step 4: Select LoRAs
- Open the node
- Each dropdown shows ONLY ~50-200 Wan i2v LoRAs (not 3600!)
- Select from dropdown (no typing needed!)
- Enable checkbox + set strength
- Done! ✓

## 📋 Available Nodes

### ✅ Ready to Use:
1. **Multi-LoRA Loader (Wan i2v)** 
   - Path: `loaders/multi-lora/wan`
   - Filters: `L:\...\Lora\Wan\i2v\`
   - CLIP: No (model-only)

2. **Multi-LoRA Loader (Wan t2v)**
   - Path: `loaders/multi-lora/wan`
   - Filters: `L:\...\Lora\Wan\t2v\`
   - CLIP: No (model-only)

3. **Multi-LoRA Loader (Model Only)**
   - Path: `loaders/multi-lora`
   - Filters: None (all LoRAs)
   - CLIP: No (model-only)

4. **Multi-LoRA Loader v02**
   - Path: `loaders/multi-lora`
   - Filters: None (all LoRAs)
   - CLIP: Yes

## 🔍 Verification

After restart, check console output:
```
[Wan-i2v] Found 52 LoRAs    ← Success!
[Wan-t2v] Found 83 LoRAs    ← Success!
```

If you see `Found 0 LoRAs`:
- Check directory structure matches: `L:\...\Lora\Wan\i2v\` and `L:\...\Lora\Wan\t2v\`
- Verify LoRA files exist in those directories
- Check file extensions: `.safetensors`, `.pt`, or `.bin`

## 💡 Usage Tips

### Tip 1: Additional Filtering
Still too many LoRAs? Use the additional filters:
- **search_filename**: Type `lightning` to show only lightning LoRAs
- **search_category**: Select `artstyle` to show only art style LoRAs
- **min_rating**: Set to `3` to show only rated 3+ LoRAs

### Tip 2: Check Filtered List
Connect the `filtered_loras_list` output to a text display to see:
- All matching LoRAs with details
- Architecture, category, trigger words
- Relative paths for context

### Tip 3: Trigger Words
- Enable `query_civitai` to auto-fetch trigger words
- Use `prompt_with_triggers` output for complete prompt
- Check `all_trigger_words` output for combined triggers

### Tip 4: Subgraph Workflow
1. Create your Wan i2v workflow
2. Select multiple nodes
3. Run as subgraph
4. All LoRAs load seamlessly!

## 🎨 Example Workflow

```
┌─────────────────────────┐
│ Wan i2v Model Loader    │
└────────┬────────────────┘
         │ MODEL
         ▼
┌─────────────────────────────────────────┐
│ Multi-LoRA Loader (Wan i2v)            │
│ ┌─────────────────────────────────────┐│
│ │ [✓] LoRA 1: lightning_fast          ││
│ │     Strength: 0.8                   ││
│ │ [✓] LoRA 2: character_boost         ││
│ │     Strength: 1.0                   ││
│ │ [ ] LoRA 3-8: disabled              ││
│ └─────────────────────────────────────┘│
└────┬──────────────┬─────────────────────┘
     │ MODEL        │ prompt_with_triggers
     ▼              ▼
┌────────────┐  ┌──────────────┐
│ Wan i2v    │  │ Text Display │
│ Sampler    │  │ (Debug)      │
└────────────┘  └──────────────┘
```

## 🔧 Troubleshooting

### Issue: Dropdown still shows all 3600 LoRAs
**Solution**: You're using the wrong node!
- ❌ Don't use: "Multi-LoRA Loader v02"
- ✓ Use: "Multi-LoRA Loader (Wan i2v)" or "(Wan t2v)"

### Issue: Node not showing in menu
**Solution**: 
1. Restart ComfyUI completely
2. Check console for import errors
3. Verify files exist in `nodes/` directory

### Issue: No LoRAs in dropdown (shows only "None")
**Solution**: 
1. Check directory structure: `L:\...\Lora\Wan\i2v\` must exist
2. Verify LoRA files are in that directory
3. Check console for `[Wan-i2v] Found X LoRAs` message
4. If 0 found, check path configuration

### Issue: Can't find specific LoRA
**Solution**: 
1. Use `search_filename` filter
2. Check `filtered_loras_list` output
3. Verify LoRA is actually in the filtered directory

## 📚 More Information

- **Full Documentation**: `MULTI_LORA_PLATFORM_NODES_README.md`
- **Implementation Details**: `PLATFORM_LORA_IMPLEMENTATION_SUMMARY.md`
- **Architecture Diagram**: `PLATFORM_LORA_ARCHITECTURE_DIAGRAM.md`

## 🚀 Next Steps

### Add More Platforms (5-10 minutes each):
1. Copy `Multi_LoRA_Loader_Wan_i2v.py`
2. Change 5 properties (name, directory filter, etc.)
3. Restart ComfyUI
4. Done!

### Suggested Platforms:
- Flux → `L:\...\Lora\Flux\`
- SDXL → `L:\...\Lora\SDXL\`
- SD3.5 → `L:\...\Lora\SD3.5\`
- Qwen → `L:\...\Lora\Qwen\`

## ✨ Enjoy!

You now have manageable, platform-specific LoRA loaders! 🎉

No more scrolling through 3600+ items!  
No more copy-paste from filtered lists!  
Just select and go! ✓
