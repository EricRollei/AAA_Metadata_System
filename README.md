# AAA Metadata System for ComfyUI

![GitHub License](https://img.shields.io/github/license/EricRollei/AAA_Metadata_System)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

One save node that does it all - PNG, JPG, WebP, TIFF, PSD, APNG and SVG, true 16-bit, Photoshop layers, real colour management - and that writes what made each image where Lightroom, XnView MP and Capture One can search it. Plus the load, metadata, LoRA, colour and file nodes that go with it.

## ⭐ AAA Save Image All - the Swiss army knife of image saving

**Node:** `AAA Save Image All PNG WebP JPG PSD TIFF SVG w Metadata` (menu: *Eric's Nodes / Output*).
Search for it by what you need: `psd`, `tiff`, `layers`, `icc`, `color management`, `metadata`, `xmp`, `lightroom`.

Connect your images and press Queue. No wiring of prompts, models or seeds: the node watches the workflow run and records what was actually used.

### What sets it apart

**1. Your images become searchable in a photo catalogue.**
Most save nodes put the prompt in a PNG text chunk that only AI tools read. This node writes standard XMP fields that photo software indexes:

| What | Where it is written | Where you see it |
|---|---|---|
| Prompt | `dc:description` | Lightroom "Caption", XnView "Description", Capture One "Description" |
| Checkpoint, LoRAs, sampler, your own keywords | `dc:subject` + hierarchical keywords | Keyword lists and keyword search everywhere |
| Title, creator, copyright, project | `dc:title`, `dc:creator`, `dc:rights`, headline | Standard IPTC panels |
| Full generation record (every pass, seed, strength, hash) | `hcai:` namespace, as fields and as one JSON | Any XMP-aware tool; the pack's own Query / Filter nodes |
| Quality measurements | `eiqa:` namespace | The pack's Query / Filter nodes |

Type a LoRA name into Lightroom's keyword filter and get every image made with it.

**2. Generation data is collected while the workflow runs - not guessed from the graph.**
- Works with switches, wildcards, prompt rewriters and all-in-one sampler nodes: what is stored is what the node received, including the prompt after an LLM rewrote it (the typed prompt is kept as well).
- Every model with its role: checkpoint / UNet, text encoders, VAE, LoRAs with strengths, upscale models.
- Every sampling pass: steps, CFG, sampler, scheduler, seed, start / end step.
- Model hashes and an A1111-style parameters block, so Civitai and AI image browsers recognise the resources.
- Parameter sweeps (Eric_Krea2): each image of the batch carries the settings of its own cell.
- Scores from analysis nodes (Eric-image-classification: UniPercept, IQA, blur...) that looked at the image in the same run are stored automatically.

**3. Layers that open as layers in Photoshop - in PSD and in TIFF.**
- Two overlay layers and two mask layers next to the main image, each with its own name, opacity and blend mode (normal, multiply, screen, overlay, add, subtract, difference, darken, lighten, colour dodge, colour burn).
- 8-bit and true 16-bit PSD.
- Layered TIFF: the layers are written in Photoshop's own TIFF layer format, so the file opens with its layer stack in Photoshop while every other program shows the flattened picture.
- The matching load node (`Eric Load Image with Layers v2`) brings the layers back into ComfyUI.

**4. Real colour management.**
- sRGB (three v4 variants), Adobe RGB, ProPhoto RGB and Display P3.
- The pixels are converted into the chosen colour space with the rendering intent you pick, and the ICC profile is embedded - the file looks the same in a colour-managed viewer as in ComfyUI. (Attach-only, without conversion, is one switch away.)
- True 16-bit PNG, TIFF and PSD: the full precision of the tensor, not an 8-bit image in a 16-bit container.

**5. Seven formats, and two at once.**
- PNG, JPG, WebP, TIFF, PSD, animated PNG, and true vector SVG (traced; needs `vtracer`).
- Optional second copy of every image in another format, with its own quality, colour profile and file-name suffix - for example a 16-bit ProPhoto TIFF master plus an sRGB JPG for the web, in one pass.
- Three quality presets; alpha as premultiplied, straight, matte on a colour of your choice, or saved separately.

**6. Files where you want them.**
- Output sub-folder or any absolute path; date tokens in folder and file names; project name and date / time in the file name; padded or simple numbering.
- Next to the image, as you choose: XMP sidecar, a readable `.txt` report, the workflow as JSON.
- The ComfyUI workflow stays embedded in PNGs, so drag-and-drop back into ComfyUI keeps working; for other formats it can be saved as JSON.

### Good to know
- **ExifTool is required** for the metadata inside the image files. Without it the node still saves the image, the XMP sidecar and the `.txt` report, and tells you in its `summary` output that nothing was embedded. Install: <https://exiftool.org/install.html>.
- Old-style IPTC (IIM) blocks are removed on purpose: Capture One prefers them over XMP and would show stale data.
- Disk paths of your models are not stored unless you switch `include_model_paths` on - names and hashes only.
- **Coming from `Save Image with Metadata v099d`?** Nothing to do. Existing workflows load unchanged and now run this node's code: all v099d widgets are in the same place, the new ones follow at the end. One visible change: with Adobe RGB or ProPhoto selected the pixels are now converted (v099d only attached the profile). `AAA_META_KEEP_OLD_SAVE=1` restores the old behaviour.

### The nodes around it
| Node | What it does |
|---|---|
| Eric Load Image Extended v2 / Load Image with Layers v2 | Load at full 16-bit precision, read layers from PSD and TIFF, hand out the stored prompt and record |
| Eric's Metadata Entry V3 | Add or change title, caption, keywords, rating on existing files |
| Add Measurements to Image v1 | Store scores from any analysis node in a file |
| Eric's Metadata Query V4, Filter V3, Enhanced Filter V3 | Read fields and pick images by what is stored in them |
| Metadata Debugger V3, Consolidator V3, Generation Record (debug) v1 | See exactly what is stored and what was collected |
| Eric Save True SVG Image v2, Save Qwen Layers v2 | SVG with metadata; layer stacks from Qwen-Image-Layered as PSD / layered TIFF |
| PNG Metadata Extractor V4, Civitai Prompt Extractor v2, Workflow Toolkit v3 | Read prompts, resources and workflows out of existing images |

`tools/backfill_library.py` makes the PNGs you already have searchable from their embedded workflow (dry run by default).

## What else is in the pack

82 nodes under one menu tree, *Eric's Nodes / ...*. Every node can be found in the node search by what it does (for example `duplicates`, `lora stack`, `word cloud`, `aspect ratio`).

| Menu | Nodes |
|---|---|
| **Output** | AAA Save Image All · Save True SVG Image v2 · Save Qwen Layers v2 · Save Image with Metadata (Simple) |
| **Input** | Load Image Extended v2 (16-bit, PSD, TIFF, stored prompt and record as outputs) · Load Image with Layers v2 |
| **Metadata** | Metadata Entry V3 · Query V4 · Filter V3 · Enhanced Filter V3 · Debugger V3 · Consolidator V3 · Add Measurements to Image v1 · Generation Record (debug) v1 · PNG Metadata Extractor V4 · Split Workflow Extractor V3 · Civitai Prompt Extractor v2 (+ Auto LoRA Loader) |
| **Loaders** | Multi-LoRA Loaders (Flux, Qwen, Wan t2v / i2v, Z-Image, model-only, filtered) · LoRA Tester suite (12 nodes: notes, ratings, trigger words, gallery, database) · Checkpoint Tester suite (5 nodes) |
| **Files** | Duplicate Image Finder v05 · Fast Duplicate Finder · File Organizer v2 · Flatten Nested Files |
| **Color** | Color Palette Analyzer v3 · Cultural Color Palette Generator · Color Selector · Color Name to RGB / Hex |
| **Crop & Compose** | Compose Crop · Compose Crop (Scored) · Smart Image Cropper |
| **Size & Aspect** | Wan 2.2 Aspect Ratio Helper · Wan 2.2 Size Preset · Qwen Aspect Ratio Helper (+ Advanced) · Aspect Ratio for 2-step Latent · Tile Calculator |
| **Text** | Text Overlay v04 · Word Cloud Generator |
| **Tools / Workflow** | PNG Info Diagnostic V4 · Workflow Toolkit v3 |
| **Deprecated** | Earlier versions of the nodes above. They stay so existing workflows load; new workflows should use the current ones. |

## Installation

### 1. Install the pack

**ComfyUI Manager / Comfy Registry** - search for **AAA Metadata System** (registry id `aaa-metadata-system`), install, restart ComfyUI.

**Or with git:**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/EricRollei/AAA_Metadata_System.git
cd AAA_Metadata_System
pip install -r requirements.txt
```

With the portable Windows build use its own Python: `..\..\..\python_embeded\python.exe -m pip install -r requirements.txt`.

### 2. Install ExifTool (required for metadata inside the image files)

AAA Save Image All and the current metadata nodes use [ExifTool](https://exiftool.org) to write metadata into image files. **Without ExifTool the images are still saved, with the `.xmp` sidecar and the `.txt` report, but nothing is written inside the image file** - so Lightroom, XnView and Capture One will not see prompt, keywords or models unless they read the sidecar.

| System | Install |
|---|---|
| **Windows** | Download the 64-bit zip from <https://exiftool.org>, rename `exiftool(-k).exe` to `exiftool.exe`, and put it (together with its `exiftool_files` folder) in `C:\Program Files\exiftool\`, or anywhere on your `PATH`. |
| **macOS** | `brew install exiftool` |
| **Linux** | `sudo apt install libimage-exiftool-perl` (Debian / Ubuntu) or `sudo dnf install perl-Image-ExifTool` (Fedora) |

Check: `exiftool -ver` in a terminal prints a version number. In ComfyUI, the `summary` output of the save node says "metadata NOT embedded" when ExifTool could not be used.

### 3. Optional

- `vtracer` - for SVG output (`pip install vtracer`)
- `pyexiv2` - only used by the deprecated nodes

### Requirements

- ComfyUI (developed and tested on ComfyUI 0.45 with Python 3.12)
- ExifTool (see above)
- The Python packages in `requirements.txt` (Pillow, numpy, OpenCV, psd-tools, tifffile and others)

## Compatibility with photo software

| Program | What works |
|---|---|
| **Adobe Lightroom Classic** | Caption (prompt), title, keywords incl. hierarchy `AI > Model / LoRA / Sampler`, creator, copyright, rating - all searchable in the Library filter. After changing files outside Lightroom use *Metadata > Read Metadata from File*. |
| **XnView MP** | Description, keywords, title, creator and rating in the info panel and in search. |
| **Capture One** | Description, keywords, title, creator. Old-style IPTC blocks are removed from the files because Capture One prefers them over XMP. |
| **Adobe Photoshop** | File Info shows the standard fields; PSD and layered TIFF open with their layers; embedded ICC profiles are honoured. |
| **Civitai, AI image browsers** | A1111-style parameters block with model and LoRA hashes; the ComfyUI workflow in PNGs. |

Checked in Lightroom Classic and Photoshop. XnView MP and Capture One read the same standard XMP fields.

## What is stored

**Standard fields** (what every program understands)

| Field | Content |
|---|---|
| `dc:description` | Your description, then the prompt |
| `dc:title`, `dc:creator`, `dc:rights` | Title, creator, copyright from the node |
| `dc:subject` | Your keywords + model, LoRA and sampler names + project |
| `lr:hierarchicalSubject` | `AI|Model|...`, `AI|LoRA|...`, `AI|Sampler|...`, `Project|...` |
| `photoshop:Headline` | Base model(s) |
| `photoshop:Instructions` | One-line summary of the settings |
| `xmp:Rating` | Star rating (set with Metadata Entry V3) |

**Generation record** - namespace `hcai` (`http://historic.camera/ns/ai/2.0/`): prompt, negative prompt, the prompt as typed when a rewriter changed it, every model with role / strength / hash, every sampling pass with steps, CFG, sampler, scheduler, seed, image size, and the complete record once more as JSON (`hcai:RecordJSON`). Where a generator node states its own settings (Eric_Krea2), that statement is stored as the record's `recipe`.

**Measurements** - namespace `eiqa` (`http://historic.camera/ns/eiqa/2.0/`): scores and classifications from analysis nodes, one group per node, plus the same as JSON (`eiqa:AnalysisJSON`).

**Next to the image**, if switched on: `.xmp` sidecar (same content), `.txt` report, workflow `.json`.

Files written by earlier versions of this pack (namespaces under `ericproject.org`) are still read by all current nodes.

## Nodes in more detail

### AAA Save Image All

See [the section at the top](#-aaa-save-image-all---the-swiss-army-knife-of-image-saving). `Save Image with Metadata v099d` is listed under *Eric's Nodes / Deprecated*; workflows that use it keep working and run the current code.

[Widget-by-widget documentation of the options shared with v099d](documentation/ReadMe%20Docs/MetadataSaveImage_Node_Documentation.md)

### Metadata Query V4

Reads values out of an image's metadata:

- **Three query methods**: dot paths (`ai_info.generation.model`), JSONPath expressions, regular expressions
- **Sources**: the image file, its XMP sidecar, the text report, or the database - with a fallback order you choose
- **Reads both generations of files**: images saved by the current nodes and by earlier versions of the pack
- Default values when a field is missing; whole sections or single values as output

Useful for workflows that branch on metadata, or to show a stored prompt or score.

[Detailed documentation](documentation/ReadMe%20Docs/MetadataQueryNodeDoc.md)

### Text Overlay Node

Overlay text on images with extensive styling:

- Font selection from system fonts, size, colour, alignment, spacing, bold and italic
- Effects: gradient, metal, neon, emboss; drop shadow and outline
- Blend modes (normal, multiply, screen, overlay) and adjustable opacity
- Automatic wrapping by width or character count; text from TXT or Markdown files
- Percentage-based positioning

For watermarks, captions and titles.

[Detailed documentation](documentation/ReadMe%20Docs/TextOverlayNodev04Documentation.md)

### Duplicate Image Finder

Scans folders for duplicates and similar images with perceptual hashing:

- Hash algorithms: pHash, dHash, aHash, wHash
- Three levels: exact duplicates, similar images, variants
- File-name pattern and metadata analysis in addition to the hashes
- Move or copy duplicates into folders, grouped by similarity; keep the largest / best file
- JSON report, CSV export, summary statistics

[Detailed documentation](documentation/ReadMe%20Docs/DuplicateImageFinderNodeDoc.md)

### Wan 2.2 size nodes

- **Wan 2.2 Aspect Ratio Helper**: analyses an input image and gives suitable dimensions for image-to-video
- **Wan 2.2 Size Preset**: dimensions from predefined aspect ratios for text-to-video

Both keep all dimensions divisible by 8, check the known Wan 2.2 training sizes first, and offer six size presets from Tiny (~200K pixels) to Gigantic (~2M pixels). Size Preset has 15 predefined ratios (6 portrait, square, 8 landscape).

## Settings

Environment variables, read when ComfyUI starts. None is needed for normal use.

| Variable | Effect |
|---|---|
| `AAA_META_VERBOSE=1` | Full console output (the pack is quiet by default) |
| `AAA_META_CAPTURE=0` | Switch off the collection of generation data while workflows run |
| `AAA_META_MIRROR=0` | Do not mirror what other nodes write through the older metadata service |
| `AAA_META_MEASUREMENT_PACKS=a,b` | Node packs whose results count as measurements (default: Eric-image-classification) |
| `AAA_META_KEEP_OLD_SAVE=1` | Keep the original v099d save code for the v099d node |
| `AAA_META_KEEP_OLD_LABELS=1` / `AAA_META_KEEP_OLD_CATEGORIES=1` | No "(deprecated)" labels / keep the previous menu categories |
| `AAA_META_NO_SEARCH_ALIASES=1` | Do not add search words to the nodes |

## For developers

The pack has two layers:

```
 ComfyUI nodes
   AAA Save Image All, Entry V3, Query V4, Filter V3, load nodes v2 ...
        |                                         |
        v                                         v
 aaa_meta  (current core)                 eric_metadata  (first generation)
   capture/   what ran: inputs, outputs,    MetadataService facade
              loaded files                  handlers: embedded, XMP sidecar,
   builder    -> GenerationRecord                     text file, SQLite
   xmp_packet -> standard + hcai + eiqa     still used for the database and by
   writer / reader / embed (ExifTool)       the deprecated nodes; everything it
   psd_writer, layers, color, pixels        writes is mirrored into the new fields
```

**Read what is stored in a file** (inside ComfyUI's Python):

```python
from AAA_Metadata_System.aaa_meta import reader

data = reader.read_file("path/to/image.png")      # embedded metadata, else the .xmp sidecar
print(data["standard"])                            # title, description, keywords ...
print(data["record"])                              # the generation record (dict) or None
print(data["analysis"])                            # measurements
print(reader.generation_summary(data))             # flat: prompt, model, loras, sampler, seed ...
```

**Add measurements or change fields in an existing file** (pixels untouched, nothing else erased):

```python
from AAA_Metadata_System.aaa_meta import writer

writer.add_analysis("path/to/image.png", {"my_node": {"sharpness": 0.82, "label": "portrait"}})
writer.patch_metadata("path/to/image.png", rating=4, project="Spring catalogue", sidecar=True)
```

**The first-generation service** still works and is what the Query / Filter nodes present as their structure (`basic`, `ai_info.generation`, `analysis`):

```python
from AAA_Metadata_System import MetadataService

service = MetadataService(debug=False, human_readable_text=True)
service.write_metadata("path/to/image.png", {
    "basic": {"title": "My image", "keywords": ["landscape"], "rating": 4},
    "analysis": {"technical": {"blur": {"score": 0.92, "higher_better": True}}},
})
stored = service.read_metadata("path/to/image.png", source="embedded", fallback=True)
```

**Let the save node pick up your node's settings.** If your generator node returns its settings as a JSON string - an object with a key ending in `_settings_version` - AAA Save Image All stores it with the image automatically. Results of analysis nodes are collected the same way when the pack is listed in `AAA_META_MEASUREMENT_PACKS`.

More: [architecture](documentation/ReadMe%20Docs/MetadataSystemArchitecture.md) · [metadata structure of the first-generation service](documentation/ReadMe%20Docs/MetadataStructureReference.md) · [API reference](documentation/ReadMe%20Docs/API_Reference.md) · [usage guide](documentation/ReadMe%20Docs/MetadataSystemUsageGuide.md). These four describe the first-generation service; `documentation/OVERHAUL_PLAN_2026-11.md` documents the current core.

## 👏 Acknowledgements

- The ComfyUI team for the platform
- Phil Harvey for ExifTool
- psd-tools, tifffile, Pillow and vtracer
- The Metadata Working Group (MWG) and IPTC for the metadata standards


## Contributing

Contributions are welcome! The codebase follows PEP 8 style guidelines and uses comprehensive docstrings for all classes and methods. See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:

- Code of conduct
- Development setup
- Pull request process
- Coding standards
- Documentation requirements
- Testing approach

## License

Dual License:

1. Non-Commercial Use: This software is licensed under the terms of the Creative Commons Attribution-NonCommercial 4.0 International License.
   
2. Commercial Use: For commercial use, a separate license is required. Please contact Eric Hiss at eric@historic.camera or eric@rollei.us for licensing options.

## 📞 Contact

- GitHub: [EricRollei](https://github.com/EricRollei)
- Email: eric@historic.camera or eric@rollei.us