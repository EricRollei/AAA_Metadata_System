# AAA_Metadata_System - Overhaul Plan (2026-11-14)

Status: DRAFT for Eric's review. No code has been changed.

## Agreed ground rules

- Acceptance targets: Lightroom Classic, XnView MP, Capture One.
- Metadata/save/load core first; the other ~40 nodes afterwards.
- New nodes with similar names and higher revisions. Old nodes stay registered, marked deprecated, untouched, so saved workflows keep loading.
- Monkeypatching `execution.get_input_data` is approved (with static fallback).
- Existing public API (`from AAA_Metadata_System import MetadataService`) keeps working: Eric-image-classification, Eric_Krea2, eric_semantic_search import it.

## Findings this plan fixes (from the 2026-11-14 review)

Evidence file: `output\Qwen21\Qwen21-_2026-09-29_19-18-01_000.png`

1. No prompt in any indexed field (no dc:description, dc:subject, IPTC).
2. Model name written to `dc:instructions` (not a real property).
3. Embedded structs are stringified Python (`rdf:Description {'unet': ...}`).
4. Linked values unresolved (seed = `SeedGenerator`, width = `ResolutionSelector`).
5. Sampler, CFG, LoRAs, second sampling pass missing.
6. Non-ASCII paths corrupted.
7. Runtime hooks target `comfy.executor.PromptExecutor.pre_execute`, which does not exist.
8. ICC profile is tagged, pixels never converted. 16-bit TIFF is 8-bit x 256. TIFF layers are pages. PSD 8-bit only, masks are pixel layers.
9. Two ~5,500-line duplicate save nodes, ~90 widgets each; three overlapping parsers.

## What we know about the three target apps (to be confirmed in Phase 0)

- Lightroom Classic reads only embedded metadata for JPEG/TIFF/PNG and ignores .xmp sidecars for non-raw files. PNG keywords import correctly when written as separate items.
- Capture One reads embedded EXIF, embedded IPTC-IIM, embedded XMP and .xmp sidecars, and never writes to the original. It has a "prefer sidecar XMP over embedded" preference.
- XnView MP imports only keywords, rating, colour label and face tags into its catalog, and only when the import options under Settings > Metadata are ticked. Other fields are read from the file on demand.
- Not yet known: whether each app reads embedded XMP from PNG and WebP specifically, and which fields each one's search box actually covers. Phase 0 answers this.

Consequence: embedded metadata is the primary carrier (Lightroom requires it). Sidecar .xmp is optional, mainly for Capture One.

## Package layout

New code lives beside the old, nothing old is edited until Phase 5.

```
AAA_Metadata_System/
  eric_metadata/            (old, untouched until Phase 5)
  aaa_meta/                 (new)
    capture/
      resolved_inputs.py    patch of execution.get_input_data, per-node last-known store
      file_loads.py         folder_paths lookup recorder (model files per executing node)
      graph_trace.py        backward trace from the save node over DYNPROMPT
      roles.py              role inference by socket type and input name
    record.py               GenerationRecord dataclasses (canonical record)
    mapping.py              record -> standard fields (one table, driven by Phase 0 results)
    xmp_packet.py           XMP builder: real structs, UTF-8, x-default lang alts
    writers/                png.py jpeg.py tiff.py webp.py psd.py svg.py sidecar.py
    verify.py               exiftool read-back, returns what actually landed
    color.py                ICC conversion (ImageCms), profiles, intents
    a1111.py                parameters string
  nodes/
    eric_metadata_save_image_v100.py     (new)
    ... other new-revision nodes (Phase 4)
  tools/
    make_acceptance_set.py  Phase 0
    backfill_library.py     Phase 4
  tests/v2/
```

## Phase 0 - Acceptance matrix (decides the field mapping)

Goal: stop guessing what each app indexes.

1. `tools/make_acceptance_set.py` writes one small image per format (PNG, JPEG, TIFF, WebP, PSD). Each carries a unique marker token per candidate field, e.g. `ZQDESC01` in dc:description, `ZQSUBJ01` in dc:subject, and so on for: lr:hierarchicalSubject, IPTC-IIM Caption and Keywords, EXIF ImageDescription, EXIF UserComment, XPKeywords/XPComment, photoshop:Headline, photoshop:Instructions, Iptc4xmpExt:DigitalSourceType, custom-namespace fields, PNG `parameters` text chunk, and a sidecar-only token.
2. Eric imports the folder into Lightroom, XnView MP, Capture One and searches each token. Result goes into a table in this document: field x format x app = found in search / visible in panel / not seen.
3. `mapping.py` is written from that table.

Exit: table filled in; mapping agreed.

## Phase 1 - Capture core

1. `resolved_inputs.py`: wrap `execution.get_input_data`. For each executed node store scalar inputs (str, int, float, bool) keyed by node id, together with prompt id from `get_executing_context()`. Keep last-known values per node id across runs so cached nodes still report. If the wrapped signature changes, disable itself and log once.
2. `file_loads.py`: record `folder_paths.get_full_path` / `get_full_path_or_raise` calls (folder category, file name, executing node id). Catches every loader, including ones that keep LoRAs in a JSON state widget.
3. `graph_trace.py`: from the save node walk upstream over the DYNPROMPT graph (covers node expansion and subgraphs). Only ancestors of this save node are considered, so multi-output workflows don't cross-contaminate.
4. `roles.py`: assign roles by socket type, not class name. CONDITIONING feeding `positive` / `negative`; MODEL chain; SAMPLER / SIGMAS / NOISE / GUIDER for custom-advanced sampling; LATENT origin for dimensions; multiple sampling passes kept in order.
5. `record.py`: `GenerationRecord` with prompts (positive, negative, plus the pre-LLM source prompt when present), models (role, name, path, hash), loras (name, strengths, hash), sampling passes (sampler, scheduler, steps, cfg, seed, denoise, step range), dimensions, workflow name, timestamps, ComfyUI version.
6. Static fallback: when no runtime data exists (old images, backfill), trace with link resolution only.

Tests: prompt JSON extracted from real outputs as fixtures. The Qwen21 file is regression case 1. Expected: seed 178292995849258, pass 1 `multistep/res_3m` cfg 3, pass 2 `linear/euler` cfg 1, 34 steps split at 23, scheduler simple, LoRAs from the Pixaroma loader state, model/VAE/CLIP names with intact Unicode.
Limit: the LLM-written prompt can only be verified in a live run, not from fixtures.

Exit: a debug node prints the record for a live run of that workflow and every field is right.

## Phase 2 - Writer

1. `mapping.py` (final values from Phase 0; starting assumption):
   - dc:description + IPTC Caption: positive prompt
   - dc:title: user title, else filename stem
   - dc:subject + IPTC Keywords: model name, LoRA names, sampler, user keywords
   - lr:hierarchicalSubject: `AI|Model|<name>`, `AI|LoRA|<name>`, `AI|Sampler|<name>`
   - Iptc4xmpExt:DigitalSourceType: trainedAlgorithmicMedia
   - xmp:CreatorTool: ComfyUI + version
   - dc:creator, dc:rights, xmpRights: user fields
   - EXIF UserComment (JPEG/WebP) and PNG `parameters`: A1111 string
   - custom namespace: full record as real XMP structs, plus the record as one JSON property for easy machine reading
2. `xmp_packet.py`: one builder used by every format and by the sidecar, so embedded and sidecar can never disagree again.
3. Writers embed during the save call (Pillow 12 takes XMP for PNG, JPEG, WebP, TIFF). No second open-and-rewrite pass.
4. `verify.py`: read back with exiftool; the node's UI text reports the fields that landed and any that did not. Errors are shown, never swallowed.
5. Keyword hygiene: file stem only (no folder path), Unicode preserved, de-duplicated, length-capped for IPTC-IIM.

Exit: Phase 0 searches succeed in all three apps on files written by the new writer.

## Phase 3 - New save node (`MetadataAwareSaveImage_v100`, display "Metadata Save Image v1.0")

V3 schema (`io.ComfyNode`).

- Inputs: images, filename prefix, format (`DynamicCombo`: only the chosen format's options show), layers (`Autogrow`: image, optional mask, name, blend mode, opacity), optional metadata override input.
- Target: about 10 visible widgets instead of about 90.
- Formats:
  - PNG 8/16-bit (16-bit from the float tensor)
  - JPEG, WebP, AVIF
  - TIFF 8/16-bit and 32-bit float, with Photoshop-readable layers (ImageSourceData block) when layers are connected
  - PSD 8/16-bit with real layer masks, groups, blend modes, ICC, XMP
  - SVG: pass-through of ComfyUI's native SVG type, or vtracer trace of a raster
- Colour: real conversion from sRGB to the chosen profile (sRGB, Display P3, Adobe RGB, ProPhoto) with the selected rendering intent; wide-gamut profiles forced to 16-bit to avoid banding.
- Filename tokens: date, model, seed, counter.
- Outputs: images, file path, metadata summary string.

Open technical item: PSD/TIFF layer writing. psd-tools 1.10.9 is installed and is the first candidate; 16-bit layer write and the TIFF ImageSourceData block need a spike before committing to a library.

Exit: each format opens correctly in Photoshop with layers, masks, blend modes and profile intact; metadata passes Phase 0 searches.

## Phase 4 - Companion nodes (new revisions) and backfill

- Metadata Entry V3: manual title/keywords/creator/rights and extra fields; feeds the save node's override input.
- Metadata Inspector V4: replaces PNG Metadata Extractor V3, PNG Info Diagnostic V3 and Metadata Debugger V2 with one reader that shows standard fields, the generation record and a per-app "will be searchable" check.
- Metadata Query V4 / Filter V3: rebuilt on the new record.
- Load Image (Extended / With Layers): output the generation record alongside the image.
- `tools/backfill_library.py` + a node wrapper: walk an existing output folder, static-trace the embedded prompt JSON, write standard fields into the existing files. Makes the back catalogue searchable. Dry-run mode and a per-file report; originals are only modified when Eric says so.

## Phase 5 - Retire and clean

- Old nodes: "(deprecated)" in the display name, moved to a Deprecated category. Not removed.
- `MetadataService` keeps its API and delegates to the new writer.
- Delete the dead runtime-hook module and the unused parsers once nothing imports them.
- Fix the double package init at startup; remove `install_web_extensions()`; move TEMPLATE_ files out of `nodes/`.
- Move `metadata.db` and caches to `ComfyUI/user/`.
- Repository hygiene: `.history` (1 GB), `nodes/debug` (1,000 files), `civitai_cache.json` (40 MB) out of the package and git-ignored; `pyproject.toml` licence classifier corrected from MIT to match CC BY-NC dual licence.
- Version bump, CHANGELOG, registry publish.

## Phase 6 - Remaining nodes

LoRA/checkpoint testers and loaders, colour nodes, word cloud, crop, duplicate finders, file organisers, aspect helpers. Reviewed and planned separately after Phase 5.

## Working method

- Git branch `overhaul-v2`. The working tree currently has uncommitted changes in ~15 files; these need committing (or stashing) first so the branch starts clean.
- Each phase ends with something Eric can run and check before the next begins.
- Widget order on old nodes is never touched.

## Open decisions

1. Node naming: `MetadataAwareSaveImage_v100` / "Metadata Save Image v1.0" for the save node; others bump one revision (Entry V3, Query V4, Filter V3, Inspector V4).
2. Custom namespace: keep prefix `ai`, move URI to `http://ericproject.org/schemas/ai/2.0/` because the structure changes. (Is ericproject.org a domain Eric controls? If not, pick one that is.)
3. Keywords: model, LoRAs, sampler and user keywords only; prompt text stays in the description. Option: also add prompt-derived keywords.
4. Friendly names: keywords use file stems. Option: use display names from comfyui-lora-manager's metadata files when present.
5. Sidecar .xmp default: off for JPEG/TIFF/PNG (Lightroom ignores it), on only if Phase 0 shows Capture One needs it.

---

## Update 2026-11-14 (evening): decisions, survey, Phase 0 status

### Decisions made

1. Names: save node `MetadataAwareSaveImage_v100` ("Metadata Save Image v1.0"); others bump one revision.
2. Namespace: domain historic.camera. Prefix `hcai`, URI `http://historic.camera/ns/ai/2.0/`. A new prefix (not `ai`) so old and new files never collide in exiftool configs.
3. Keywords: model, LoRAs, sampler, user keywords. Prompt text stays in the description.
4. Model/LoRA keywords keep the whole file stem (the Civitai model and version numbers are the meaningful part).
5. Baseline committed on `main` (15a8929); work continues on branch `overhaul-v2`.

### Change to Phase 1: hook point

comfyui-lora-manager (installed here) already wraps `execution._async_map_node_over_list` and `execution.execute`. That call receives prompt id, node id, the resolved inputs AND returns the node's outputs. It is a better capture point than `get_input_data`:
- outputs are available (e.g. the STRING an LLM prompt node returns), not just inputs
- prompt id and node id arrive as arguments
- it is already proven to coexist with other wrappers

Phase 1 step 1 therefore wraps `_async_map_node_over_list` (chaining whatever wrapper is already installed), with `get_input_data` as the fallback if the signature differs.

### Survey of other packs (what to take, what to avoid)

- Civitai-compatible savers (ComfyUI-Image-Saver, SaveImageWithMetaData and its forks, SD Prompt Reader's saver): write the A1111 `parameters` string plus model/LoRA/embedding hashes so Civitai auto-detects resources. Take: hashes for every resource in the A1111 string. Avoid: their collection method - either manual wiring of every value, or tracing from a KSampler through a per-node definition table.
- comfyui-lora-manager: runtime hook as above plus a 57 KB per-node extractor table. Take: the hook point. Avoid: the per-node table (same maintenance trap as our old parser).
- XMP savers (JH XMP Metadata Nodes, comfyui-save-image-xmp, too-xmp-metadata): embed XMP, but the user builds the strings by wiring. comfyui-save-image-xmp's "layered TIFF" is multi-page, like our old one.
- Colour: Radiance (FXTD Studios; OCIO/ACES, 32-bit float, EXR), ComfyUI-OCIO, XENodes (SDR-to-HDR, AVIF with CICP tags), ComfyUI-ICC-nodes and comfyui-image-process (load/embed ICC). Take: CICP tagging for AVIF/PNG, an optional ICC-profile input so a profile loaded elsewhere can be used, EXR output as a later option. Out of scope for the save node: scene-referred grading (leave to Radiance/OCIO packs; accept their float images).
- Nobody surveyed writes catalog-searchable standard fields automatically, real Photoshop-layered TIFF, or reads the result back to verify. Those remain this pack's differentiators.

### Phase 0 status

Built: `tools/make_acceptance_set.py`, `tools/exiftool_hcai.config`.
Test set: `ComfyUI\output\AAA_acceptance_set\` - PNG, JPEG, TIFF, WebP, PSD, plus a bare PNG with a sidecar-only .xmp. 79 marker tokens, all verified present with exiftool.
Results sheet: `acceptance_results.csv` in the same folder (one row per token, a column per app).

How to fill it in:
1. XnView MP first: Settings > Metadata, tick the import options for XMP subject / IPTC keywords, then browse the folder.
2. Import the folder into Lightroom Classic and Capture One.
3. In each app, type `zq` in the search box to see everything it indexed, then note per token: S = found by search, V = visible in the metadata panel only, blank = not seen.

---

## Update 2026-11-14 (night): Phase 1 built

New package `aaa_meta/` (old `eric_metadata/` untouched):
- `capture/exec_hook.py` - wraps `execution._async_map_node_over_list`; keeps each node's resolved scalar inputs and outputs (last known per node id).
- `capture/file_loads.py` - wraps `folder_paths.get_full_path(_or_raise)`; records model files per executing node.
- `graph.py`, `resolve.py` - graph view and value resolution (published > runtime > literal > static follow-through). Stale captures from another workflow are rejected by comparing literals.
- `models.py` - finds model/LoRA references in plain widgets, dict widgets and JSON state strings, with on/off flags and strengths.
- `builder.py` - recognises generators by input shape (ksampler / custom-advanced / all-in-one with sN_ stages), reads prompts through the conditioning chain, orders multiple passes.
- `record.py` - `GenerationRecord`; `hashing.py` - cached SHA-256 (own cache, .sha256 sidecars, LoRA Manager metadata).
- `runtime.py` + node `Eric_Generation_Record_V1` ("Generation Record (debug) v1").
- `aaa_meta.publish(...)` - optional call for node authors to state values explicitly.
- Pack `__init__.py`: 8 added lines to install the hooks (off with env `AAA_META_CAPTURE=0`).

Tests: `tests_v2/test_core.py` (10 tests, synthetic graphs, pass under embedded Python 3.12). `tests_v2/run_fixtures.py` prints the static trace for the 14 local fixtures (git-ignored, personal prompts).

Static-trace results on the 14 real workflows (checked by eye against the graphs, not by an automated oracle): every workflow yields its sampling passes in order, seeds, models and enabled LoRAs with strengths. Values computed by math/convert nodes stay empty statically (steps in the Ideogram workflow, step ranges in the Wan video workflow). The prompt is found statically in 9; in the other 5 it passes through an LLM or prompt-builder node. Both gaps need the runtime hook.

NOT YET VERIFIED: the hooks in a live ComfyUI run (ComfyUI was running during the build; they load on next restart). Exit test for Phase 1: restart, add "Generation Record (debug) v1" after VAE decode in the Qwen21 workflow, confirm the LLM-written prompt, seed 'SeedGenerator' value, both passes and the model files appear with capture = runtime.

Known limits to revisit:
- Unknown-role files on side branches (e.g. depth model for a mask) are listed with role "model"; they never become keywords.
- Async nodes: outputs are picked up when the task finishes.
- V3 nodes with dotted dynamic inputs (`values.a`) are read as flat names.

---

## Update 2026-11-15: Phase 0 results and Phase 1 live test

### Acceptance results (Eric's tests, all three apps)

| Field | Lightroom | XnView MP | Capture One |
|---|---|---|---|
| Files imported | PNG JPG TIFF PSD WebP | PNG JPG TIFF PSD WebP | PNG JPG TIFF PSD (no WebP) |
| XMP title, keywords, hierarchical keywords, creator, rights, instructions, creator tool | found, all formats | found, all formats | found, all 4 formats |
| XMP description, headline | found, all formats | found, all formats | PNG and PSD only; on JPG/TIFF the old-style IPTC caption/headline is shown instead |
| Custom namespace (hcai) | not found | found, all formats | not found |
| Old-style IPTC caption / keywords / headline | not found | TIFF, JPG | TIFF, JPG |
| EXIF image description | not found | TIFF only | not found |
| EXIF user comment | WebP, TIFF, JPG | not found | not found |
| XP keywords / comment, PNG parameters chunk | not found | not found | not found |
| Sidecar-only .xmp | not found | found | found |

### Field mapping decided by these results

- Embedded XMP is the carrier. dc:description = prompt, dc:subject + lr:hierarchicalSubject = model / LoRA / sampler / user keywords. This is searchable in all three apps for PNG, JPG, TIFF and PSD.
- Old-style IPTC (IIM): either not written, or written identical to the XMP. If the two differ, Capture One shows the IIM caption on JPG/TIFF. Default: not written (it also has a 2,000-character caption limit that long prompts exceed). A "legacy IPTC mirror" option can be added later.
- Sidecar .xmp: off by default. Lightroom ignores it for these formats; the other two read the embedded copy anyway.
- PNG `parameters` chunk and EXIF user comment: kept for Civitai / AI tools only. No catalog app reads the PNG chunk; Lightroom does search the EXIF user comment on JPG/WebP/TIFF.
- Custom namespace: the full machine-readable record. Searchable in XnView only; that is fine.
- WebP: fine for Lightroom and XnView; Capture One will not import it.
- photoshop:Headline, photoshop:Instructions and xmp:CreatorTool are searchable too (Headline with the same Capture One caveat as description). Open: what to put there.

### Phase 1 live test (Qwen 2.1 subgraph workflow)

Working: hooks installed (log line present), model files with resolved paths and source runtime, one hash from cache, sampler pass, size, subgraph node ids ("459:451"), 38 node runs captured, 0 errors.

Not working: positive prompt empty. The prompt reaches TextEncodeQwenImage21 over a link (TextGenerate -> ComfySwitchNode -> PreviewAny). Replaying the same graph offline with a simulated capture entry for the encoder gives the right prompt, so the builder logic is right and the live capture entry for that node is missing, rejected, or lacks the text. Cause not yet known.

Added to find it: `aaa_meta/diagnostics.py` and a 4th output `capture_dump` on the debug node (per upstream node: whether a capture entry exists and is trusted, what each input held, outputs, files).

---

## Update 2026-11-15 (afternoon): live capture confirmed; Lightroom plugin read

### Phase 1 live result

Second live run (same Qwen 2.1 models, nodes at top level, ids 488-501): capture = runtime, the LLM-written prompt (2,801 chars) captured from TextEncodeQwenImage21's resolved input, width/height resolved through the ResolutionSelector link, loaders accepted from an earlier run, all four model hashes from cache, 0 errors.

OPEN: the first live run (nodes inside the template subgraph, ids "459:*", with a ComfySwitchNode and thinking on) returned no prompt. That configuration has not been re-run with capture_dump, so the cause is still unknown. Needs one run of the subgraph version with the dump.

Added after reading the dump:
- `positive_source` + `prompt_rewriter` on the record: the typed text and the class of the node that rewrote it (here TextGenerate), found by walking back along text links. Also filled in static mode, where the rewritten text is unknowable.
- Role `prompt_llm` for a text encoder that only feeds the prompt text (the rewriting LLM), separate from the image model's `text_encoder`.

### Sidecars

Eric confirmed: the sidecar-only test file was found in XnView and Capture One, not in Lightroom. The mapping section above stands as written.

### Existing Lightroom plugin (M:\Lighroom_Extension\ComfyUI_Metadata.lrplugin, Jan 2026, unpublished)

How it works: defines 28 custom catalog fields plus a "ComfyUI Workflow" panel view; a menu command runs a Python script per selected PNG that re-parses the embedded workflow JSON (its own class_type table) or an A1111 string; Lua writes the values into the catalog fields and creates keywords under ComfyUI > category > value.

What it shows that plain Lightroom cannot: per-field values (model, seed, steps, sampler...) in the metadata panel, searchable and usable in filters and smart collections.

Limits found in the code:
- PNG only; reads the workflow JSON, not the XMP namespaces; no measured (eiqa) data.
- Fifth copy of the class_type parsing table; same blind spots as the old save node (no LLM prompts, no custom samplers).
- Searchable plugin fields are capped at 512 bytes by Lightroom, so prompts are split into a full field and a truncated searchable preview.
- Values live in the Lightroom catalog only.
- One process launch per image through a temp .bat file; hand-written flat JSON parser.

Plan addition - Phase 4b, Lightroom plugin v2:
- Read the canonical record straight from the file's XMP (generation + measurement namespaces) for every format, no workflow parsing.
- Add measurement fields (UniPercept, sharpness, noise, composition, exposure...) to the panel view.
- One batch call for many photos instead of one launch per image.
- Keep the field ids already in use so catalogs that have the old plugin data keep it.

---

## Update 2026-11-15 (evening): Phase 2 writer built

New modules in `aaa_meta/`:
- `fields.py` - record + user fields -> standard catalog fields (description = prompt; keywords = model / LoRA / sampler / user; hierarchical AI|Model|..., AI|LoRA|..., AI|Sampler|...; Headline = base model; Instructions = one-line settings summary with seed). No old-style IPTC.
- `a1111.py` - parameters string with model / VAE / LoRA hashes (PNG chunk; EXIF UserComment on JPEG/WebP).
- `xmp_packet.py` - one packet builder for every format and for sidecars. Generation data in `hcai` (http://historic.camera/ns/ai/2.0/) as real structures plus a JSON copy; measured data in `eiqa` (http://historic.camera/ns/eiqa/2.0/) as nested structures plus a JSON copy. `merge_packets` replaces our properties, unions keyword lists, keeps everything else. Local model paths are left out of the embedded record unless asked for.
- `embed.py` - save pixels + metadata in one pass (PNG, JPEG, WebP, TIFF via Pillow); `update_file` adds metadata to an existing file without touching pixels (exiftool; also PSD).
- `verify.py` - exiftool read-back; reports present / missing / mismatched fields.
- `writer.py` - `save_with_metadata`, `update_metadata`, `add_analysis`.
- `tools/write_test_images.py` - writes a real record into one file per format and checks it.

Results on this machine (real record from the live Qwen 2.1 run): PNG, JPEG, TIFF, WebP, PSD all verify OK (14.4 KB packet). Adding sample measurements to the PNG afterwards kept the description, keywords, seed and A1111 chunk and left the record readable. 14 unit tests pass.

JPEG size limit, handled in steps with a warning each time: drop the JSON copy, then the second copy of the prompt, then the A1111 string; beyond about 64 KB of XMP the writer refuses and says to use another format.

Test files for the three apps: `ComfyUI\output\AAA_writer_test\`.

Not yet done in Phase 2: reading files written with the old `ericproject.org` namespaces; ComfyUI workflow embedding for JPEG/WebP (PNG chunks are supported); banded keywords for measurements (waiting on which scores and cut-offs).

---

## Update 2026-11-15 (night): Phase 3a - new save node, flat formats

Node `MetadataAwareSaveImage_v100` ("Metadata Save Image v1.0", category Eric's Nodes/Output), V3 schema.
Widgets, in order: images, filename_prefix, format (png: bit_depth, compress_level | jpg: quality | webp: quality, lossless | tiff: bit_depth, compression), color_profile, title, keywords, creator, copyright, embed_metadata, then advanced: embed_workflow, embed_a1111, hash_models, include_model_paths, save_sidecar. 14 inputs against about 90 on the old node. Outputs: images, file_path, summary.
THE WIDGET ORDER IS NOT FROZEN YET: reorder now, before workflows are saved with it.

New modules:
- `color.py` - real conversion sRGB -> Adobe RGB (1998) / ProPhoto RGB in floating point from the published primaries (Bradford adaptation for ProPhoto), plus the matching ICC profile. Checked against published values: sRGB red = (219,0,0) Adobe RGB, (179,70,26) ProPhoto.
- `pixels.py` - true 16-bit PNG (own encoder, Up filter) and 16-bit TIFF (tifffile); both carry XMP, ICC and text chunks.
- `save_core.py` - the node's work without ComfyUI imports (testable offline).

Checked on this machine (`tests_v2/check_save_node.py`, 16 unit tests): PNG 8/16, TIFF 8/16, JPEG, WebP all verify with exiftool; 16-bit files keep every level of a fine gradient; Adobe RGB and ProPhoto files carry the right ICC profile; metadata-off writes no prompt, record or workflow; the V3 schema builds against this ComfyUI's comfy_api.

NOT YET VERIFIED: the node inside a running ComfyUI (loading through the pack's NODE_CLASS_MAPPINGS as a V3 class, the execute path, previews).

Deferred to Phase 3b: layers (Autogrow), layered PSD and TIFF, Display P3 (no profile file in the pack; one must be added or generated), workflow embedding for JPEG/WebP, SVG pass-through, EXR/AVIF.
Dropped from the design: the rendering-intent widget. A matrix conversion between these RGB spaces has no intent choice to make; the old widget did nothing.

## Update 2026-11-16 - Phase 3a redone: full-featured save node

Eric's feedback: the slim v1.0 node dropped features (no save folder) and changed widgets. Not acceptable.

- `MetadataAwareSaveImage_v100` is now a subclass of the v099d node. All 62 v099d widgets, same order;
  4 new widgets appended at the end (hash_models, embed_a1111, include_model_paths, convert_to_color_profile);
  third output `summary`.
- `aaa_meta/legacy_bridge.py` replaces the node's metadata service: embedded + .xmp sidecar go through the
  v2 writer; .txt / database go through the old service, fed with v2 values.
- title / project / description / creator / copyright / keywords / custom_metadata widgets now reach the file
  (typed description is placed above the prompt; project becomes a keyword and `Project|<name>`).
- Fixes that live only in the v1.0 subclass (v099d untouched): JPEG save never worked in v099d
  (matte_color passed twice); double layer-detection crash; 16-bit TIFF now true 16-bit; colour profile
  now converts pixels.
- `tests_v2/check_node_v100.py`: runs the real node on CPU - widget order identical, png / 16-bit Adobe RGB png /
  jpg + webp copy / 16-bit ProPhoto tiff / psd / webp all saved to a custom folder and verified. NODE OK.
- `tools/backfill_library.py`: dry-run-by-default tool that makes existing PNGs searchable from their embedded workflow.
- NOT yet tested inside a running ComfyUI. Layers (mask/overlay), APNG and SVG paths not exercised by the check.
