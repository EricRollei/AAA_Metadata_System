# Multi-LoRA Loader Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Multi_LoRA_Loader_Base.py                          │
│                         (Base Class)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • LoRA scanning and loading logic                                  │
│  • Database integration (lora_tester_db.json)                       │
│  • Civitai API integration (trigger words)                          │
│  • Filtering system (filename, category, triggers, rating)          │
│  • Usage tracking and statistics                                    │
│  • Hash calculation and architecture detection                      │
│                                                                      │
│  KEY INNOVATION: PLATFORM_DIRECTORY_FILTER                          │
│  └─> Scans only specified subdirectory at initialization           │
└─────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ inherits
                    ┌───────────────┴───────────────┐
                    │                               │
    ┌───────────────▼──────────────┐   ┌───────────▼──────────────┐
    │  Multi_LoRA_Loader_Wan_i2v   │   │  Multi_LoRA_Loader_Wan_t2v│
    ├──────────────────────────────┤   ├──────────────────────────┤
    │ PLATFORM_NAME: "Wan-i2v"     │   │ PLATFORM_NAME: "Wan-t2v" │
    │ FILTER: "Wan\i2v"            │   │ FILTER: "Wan\t2v"        │
    │ REQUIRES_CLIP: False         │   │ REQUIRES_CLIP: False     │
    │ ARCHITECTURE: "Wan"          │   │ ARCHITECTURE: "Wan"      │
    │                              │   │                          │
    │ Dropdown: ~50-200 LoRAs ✓    │   │ Dropdown: ~50-200 LoRAs ✓│
    └──────────────────────────────┘   └──────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      File System Structure                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  L:\stable-diffusion-webui\models\Lora\                            │
│  │                                                                   │
│  ├── Wan\                                                           │
│  │   ├── i2v\  ◄─────── Wan i2v node scans HERE only              │
│  │   │   ├── lightning\                                            │
│  │   │   ├── tools\                                                │
│  │   │   ├── artstyle\                                             │
│  │   │   ├── photostyle\                                           │
│  │   │   ├── character\                                            │
│  │   │   └── body\                                                 │
│  │   │                                                              │
│  │   └── t2v\  ◄─────── Wan t2v node scans HERE only              │
│  │       ├── lightning\                                            │
│  │       ├── tools\                                                │
│  │       └── artstyle\                                             │
│  │                                                                  │
│  ├── SDXL\  ◄─────── Future: SDXL node                            │
│  │   └── ...                                                       │
│  │                                                                  │
│  ├── Flux\  ◄─────── Future: Flux node                            │
│  │   └── ...                                                       │
│  │                                                                  │
│  ├── SD3.5\  ◄─────── Future: SD3.5 node                          │
│  │   └── ...                                                       │
│  │                                                                  │
│  └── Qwen\  ◄─────── Future: Qwen node                            │
│      └── ...                                                       │
│                                                                      │
│  Total LoRAs: 3600+ (Unmanageable in one dropdown!)                │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                      Data Flow                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. ComfyUI starts                                                  │
│     └─> Loads nodes via __init__.py auto-import                    │
│                                                                      │
│  2. Node initialization                                             │
│     └─> INPUT_TYPES() called                                       │
│         └─> _get_platform_filtered_loras() called                  │
│             └─> scan_loras() with PLATFORM_DIRECTORY_FILTER        │
│                 └─> Only scans filtered subdirectory               │
│                     └─> Returns 50-200 LoRAs (not 3600!)           │
│                         └─> Populates dropdown options             │
│                                                                      │
│  3. User selects LoRAs from dropdown                                │
│     └─> Manageable list! ✓                                         │
│                                                                      │
│  4. Node execution                                                  │
│     └─> load_multi_loras() called                                  │
│         ├─> Additional filtering (filename, category, etc.)        │
│         ├─> Load selected LoRAs                                    │
│         ├─> Query Civitai for trigger words (optional)             │
│         ├─> Update usage statistics in database                    │
│         └─> Return: model, prompts, trigger words, info            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                  Node Workflow Example                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐                                                │
│  │   Wan i2v      │                                                │
│  │   Model        │                                                │
│  │   Loader       │                                                │
│  └────┬───────────┘                                                │
│       │ MODEL                                                       │
│       ▼                                                             │
│  ┌────────────────────────────────────────────┐                   │
│  │   Multi-LoRA Loader (Wan i2v)             │                   │
│  ├────────────────────────────────────────────┤                   │
│  │  Dropdown shows ONLY Wan i2v LoRAs:       │                   │
│  │  • lightning_fast.safetensors             │                   │
│  │  • character_boost.safetensors            │                   │
│  │  • smooth_motion.safetensors              │                   │
│  │  • ... (50-200 items total)               │                   │
│  │                                            │                   │
│  │  [✓] LoRA 1: lightning_fast.safetensors   │                   │
│  │      Strength: 0.8                         │                   │
│  │                                            │                   │
│  │  [✓] LoRA 2: character_boost.safetensors  │                   │
│  │      Strength: 1.0                         │                   │
│  │                                            │                   │
│  │  [ ] LoRA 3-8: (disabled)                 │                   │
│  └────┬──────────────────┬────────────────────┘                   │
│       │ MODEL            │ PROMPTS + INFO                          │
│       ▼                  ▼                                         │
│  ┌────────────┐    ┌─────────────────┐                           │
│  │   Wan i2v  │    │  Text/Debug     │                           │
│  │  Sampler   │    │  Displays       │                           │
│  └────────────┘    └─────────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                 Adding New Platform Node                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Want to add a Flux node? Here's the template:                     │
│                                                                      │
│  1. Create file: Multi_LoRA_Loader_Flux.py                         │
│                                                                      │
│  2. Set these 5 properties:                                         │
│     • PLATFORM_NAME = "Flux"                                        │
│     • PLATFORM_DIRECTORY_FILTER = "Flux"                            │
│     • REQUIRES_CLIP = True                                          │
│     • DEFAULT_ARCHITECTURE = "Flux"                                 │
│     • MAX_LORA_SLOTS = 8                                            │
│                                                                      │
│  3. Copy INPUT_TYPES() from Wan i2v node                           │
│                                                                      │
│  4. Copy load_multi_loras() method:                                │
│     • If REQUIRES_CLIP = False: Use Wan i2v version                │
│     • If REQUIRES_CLIP = True: Use Multi_LoRA_Loader_v02 version   │
│                                                                      │
│  5. Register node at bottom of file                                 │
│                                                                      │
│  6. Restart ComfyUI → Done! ✓                                      │
│                                                                      │
│  Time required: 5-10 minutes per platform                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                        Benefits Summary                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Before:  [═══════════ Dropdown with 3600+ items ═══════════]      │
│           ↓ (Unusable! Need to scroll forever)                     │
│           Can't find anything                                        │
│           Have to use text filters → copy-paste                     │
│                                                                      │
│  After:   [═══ Wan i2v: 50 items ═══]  ← Manageable!              │
│           [═══ Wan t2v: 80 items ═══]  ← Perfect!                  │
│           [═══ Flux: 200 items ═══]    ← Easy to find!             │
│           [═══ SDXL: 150 items ═══]    ← Quick selection!          │
│                                                                      │
│  ✓ Platform-specific filtering automatic                            │
│  ✓ Manageable dropdown sizes                                        │
│  ✓ No manual filtering required                                     │
│  ✓ Direct selection (no copy-paste)                                 │
│  ✓ Works with ComfyUI subgraphs                                     │
│  ✓ Easy to extend (5-10 min per platform)                           │
│  ✓ Maintains all advanced features                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
