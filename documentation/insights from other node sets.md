# Insights from Other ComfyUI Metadata Node Repositories

**Analysis Date:** January 2025  
**Repositories Examined:**
- [xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal) (Fork of nkchocoai with extensive enhancements)
- [nkchocoai/ComfyUI-SaveImageWithMetaData](https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData) (Original foundation)
- [Light-x02/ComfyUI-Image-Metadata-Nodes](https://github.com/Light-x02/ComfyUI-Image-Metadata-Nodes) (Preservation-focused)
- [giriss/comfy-image-saver](https://github.com/giriss/comfy-image-saver) (Minimal approach)

---

## 🤝 Automatic1111 & Civitai interoperability strategy

### Goals

Provide optional interoperability without sacrificing our richer, namespaced metadata. Allow users to:

- Embed a canonical Automatic1111 (A1111) style "parameters" string for downstream prompt explorers and gallery sites.
- Prepare (or auto-generate) a Civitai-compatible resource payload for uploads (models, LoRAs, VAE, ControlNet, refiner chain).
- Keep Adobe / cataloging software friendly XMP + structured JSON unchanged. These are complementary, not mutually exclusive.

### Philosophy: Dual-layer metadata

"Rich layer" (ours): Namespaced JSON + XMP for tooling, search, analytics.
"Compatibility layer": A tightly formatted text string + optional Civitai JSON block. Derived—never the canonical source of truth.

### Automatic1111 parameter string rules

Line 1: Positive prompt.
Line 2: `Negative prompt: ...` (omit line if empty).
Line 3+: Comma + space separated key=value style entries in consistent order:

1. Steps
2. Sampler
3. CFG scale
4. Seed (and subseed if added later)
5. Size (WIDTHxHEIGHT)
6. Model
7. Model hash (short 8 or full 64; configurable)
8. Clip skip (if present)
9. VAE / VAE hash
10. Denoise strength (img2img/refiner)
11. ControlNet modules (Module n: name (weight))
12. LoRAs (LoRA name: strength_model[:strength_clip])
13. Refiner (Refiner: name (start=0.7))
14. Scheduler variant / advanced settings
15. Metadata generator tag (AAA_Metadata vX.Y.Z)

Formatting guidelines:

- Floats: max 4 decimal places.
- Use dot decimals regardless of locale.
- Preserve prompt text verbatim; do not escape unless implementing reverse parsing.

### Mapping from our namespaces

- ai_info.generation.positive_prompt → line 1
- ai_info.generation.negative_prompt → line 2
- ai_info.generation.steps → Steps
- ai_info.generation.sampler → Sampler
- ai_info.generation.cfg_scale → CFG scale
- ai_info.generation.seed → Seed
- technical.width + technical.height → Size
- ai_info.assets.models[0].name → Model
- ai_info.assets.models[0].hash.sha256 → Model hash
- ai_info.assets.vae.name (+ hash) → VAE / VAE hash
- ai_info.generation.denoise_strength → Denoise strength
- ai_info.assets.loras[] → LoRA entries
- ai_info.assets.controlnets[] → ControlNet Module list
- ai_info.assets.refiner.model → Refiner
- environment.clip_skip → Clip skip
- metadata.writer_version → Metadata generator

### Example A1111 string

```text
masterpiece, cinematic lighting, epic scale
Negative prompt: low quality, blurry, artifacts
Steps: 30, Sampler: dpmpp_2m, CFG scale: 7, Seed: 123456789, Size: 1024x768, Model: SDXL_base, Model hash: 1a2b3c4d, Refiner: SDXL_refiner (start=0.7), Denoise strength: 0.55, VAE: SDXL_VAE, LoRA: detail_lora:0.8:0.6, ControlNet Module 1: depth (0.85), AAA_Metadata v0.9.9
```

### Reversibility (optional future)

Maintain deterministic key ordering and unique key names; optionally append footer delimiter:

```text
---META_JSON--- {"checksum":"<sha256-of-parameters-line>"}
```

This enables machine parsing without confusing A1111-only consumers.

### Civitai resource JSON (sidecar or PNG chunk)

Sidecar file (`image.civitai.json`) can store richer asset list:

```json
{
    "model": {"name": "SDXL_base", "hash": "<sha256>", "type": "checkpoint"},
    "refiner": {"name": "SDXL_refiner", "hash": "<sha256>", "start_at": 0.7},
    "vae": {"name": "SDXL_VAE", "hash": "<sha256>"},
    "loras": [
        {"name": "detail_lora", "hash": "<sha256>", "strength_model": 0.8, "strength_clip": 0.6}
    ],
    "controlnets": [
        {"module": "depth", "model": "control_depth_fp16", "weight": 0.85}
    ],
    "parameters": {
        "steps": 30,
        "sampler": "dpmpp_2m",
        "cfg_scale": 7,
        "seed": 123456789,
        "size": "1024x768",
        "denoise": 0.55
    },
    "prompts": {
        "positive": "masterpiece, cinematic lighting, epic scale",
        "negative": "low quality, blurry, artifacts"
    },
    "generator": {"name": "AAA_Metadata_System", "version": "0.9.9"}
}
```

Pointer in A1111 line: `Civitai sidecar: image.civitai.json`.

### Coexistence strategy

- PNG: Keep our XMP/JSON; add `parameters` text chunk for A1111; optional `civitai_resources` chunk or sidecar.
- JPEG: A1111 string in UserComment/COM; structured JSON trimmed only if necessary; full JSON in sidecar.
- Non-mutual exclusivity: removing compatibility layer never deletes canonical metadata.

### Edge cases

- Very long prompts: truncate only A1111 display (add `…`); retain full text internally.
- Multiple checkpoints: choose primary as Model; append `Extra models: nameB, nameC`.
- Missing hash: emit `Model hash: unknown`.
- LoRA conflict (loader vs inline): prefer loader strengths; record inline original in sidecar.
- Unicode names: keep UTF‑8; optional ASCII alias key if a downstream tool fails.

### Roadmap

1. Implement A1111 string generator (toggle + tests).
2. Generate Civitai sidecar JSON; link in parameters.
3. Optional reverse parser + checksum footer.
4. Upload assistant node (future) leveraging sidecar.

### Testing checklist

- Deterministic ordering of parameter keys.
- Regeneration after internal JSON changes stable except for intentionally added fields.
- Length stress tests (prompt >8k chars) produce graceful truncated compatibility line.
- Sidecar pointer correct when sidecar exists; omitted cleanly otherwise.

### Why safe for Adobe/catalog systems

Adobe/XMP consumers ignore the `parameters` text chunk; catalog tools continue to index our structured namespaces. No field renaming or flattening occurs, so compatibility is preserved.


## 📊 Executive Summary

After analyzing four metadata collection systems, the most significant insights are:

1. **Execution hooks + BFS graph traversal** is the standard approach for automatic metadata collection
2. **Declarative rule systems** dramatically reduce maintenance and enable user extensibility
3. **Hash caching** (.sha256 sidecars) is essential for performance
4. **LoRA inline tag parsing** captures metadata even when loader nodes are absent
5. **JPEG fallback strategies** handle size constraints gracefully
6. **Our current parser-based approach is functional but could benefit from selective adoption of these patterns**

---

## 🧠 Blueprint: Catalog‑friendly AI metadata system

### What this system must achieve

- Be first‑class in Digital Asset Management (DAM) tools: readable by Adobe Bridge/Lightroom and enterprise DAMs via XMP/IPTC.
- Capture four pillars of metadata in a single, coherent model:
    1. Descriptive/classification data (keywords, subjects, people/places, hierarchical taxonomies)
    2. Technical/administrative data (format, color, DPI, rights)
    3. AI generation provenance (prompts, models, seeds, graph, assets with hashes)
    4. AI analysis/classification outputs (tags with confidence, detections, OCR, captions)
- Remain extensible for future modalities (video/audio/3D) and new AI tasks.
- Preserve integrity and provenance while giving users privacy controls.

### Design principles

- Dual‑layer representation: standards‑first XMP/IPTC for catalogers + rich canonical JSON for tooling/analytics.
- Namespaced, versioned schema with explicit migration rules; no silent field renames.
- Deterministic, reproducible outputs (stable key ordering, formatted numbers, consistent timezones).
- Performance aware (hash caching, lazy collection, bounded sizes with graceful fallbacks).

### Data model (high level)

- basic: title, description, creator, copyright, usage terms, source, language.
- classification:
    - keywords[]: value, lang, path (hierarchy), uri (e.g., Wikidata), source (human|model), confidence.
    - subject_codes[]: IPTC subject codes or custom scheme URIs.
- technical:
    - pixel: width, height, colorspace, bit_depth, dpi, profile_name.
    - file: format, size_bytes, content_hash.sha256, created_at, modified_at.
- ai_info:
    - generation: prompts (pos/neg), steps, sampler, cfg, seed/subseed, schedule, tiling/hires params.
    - assets: models[], vae, loras[], controlnets[], embeddings[], each with name, path_hint, hash{algo→hex}, version, source.
    - workflow: graph_hash, engine{comfyui_commit, node_pack_versions}, parameters_diff (compact changes vs defaults).
    - analysis: tags[] {label, score, model, threshold, method}, detections[] {label, score, bbox/polygon, model, frame?}, ocr[] {text, bbox, conf, model}, caption[] {text, model, lang}.
- provenance:
        - generator: tool_name, tool_version, writer_version, schema_version.
        - timestamps: started_at, finished_at, duration_ms, timezone.
        - environment: os, python, torch/cuda, gpu model/count, memory.
        - signatures (optional): jws/jcs signature over canonical JSON; signer, cert chain.

### Storage and interoperability

- Embedded XMP: map descriptive/classification/rights to IPTC Core/Extension and XMP (dc:, photoshop:, xmpRights:, iptcExt:), and carry ai_info summaries under a custom aaa: namespace (URI stable and documented).
- PNG: embed XMP packet; add parameters text chunk for A1111 compatibility; keep canonical JSON in an iTXt chunk (compressed if necessary).
- JPEG: embed XMP + selected EXIF fields; apply staged fallback; if overflow, store canonical JSON in sidecar .json and reference it in XMP as a pointer.
- Sidecars:
        - image.json (canonical JSON, JSON‑LD friendly with @context for aaa: and selected standards)
        - model/asset .sha256 cache files for fast identity
        - optional C2PA manifest (when adopted), kept orthogonal to our JSON
- Ecosystem compatibility: emit optional A1111 parameters string and Civitai resource JSON derived from canonical JSON; never the source of truth.

### Canonical JSON contract (minimal)

- Input signals: workflow graph JSON, runtime values (resolved), image bytes, classifier outputs.
- Output artifacts:
        - canonical metadata JSON (versioned)
        - embedded XMP (subset + pointers)
        - optional sidecars (JSON, Civitai, CSV exports)
- Error modes:
    - collection errors never fail the image save; emit warnings and best‑effort metadata.
    - size overflows trigger progressive degradation with recorded fallback_stage.

### Standards alignment (pragmatic)

- IPTC Photo Metadata: DigitalSourceType, Creator/Title/Description, Keywords (hierarchical), PersonsShown, ArtworkOrObject when relevant.
- XMP namespaces: dc:, xmp:, xmpMM:, photoshop:, xmpRights:, plus aaa: for AI‑specific structures.
- JSON‑LD ready: define an @context for aaa: to enable semantic linking without forcing LD in all tools.

### How to improve this toolset (actionable roadmap)

1) Schema and validation
     - Publish JSON Schema for canonical model with semantic versioning.
     - Add runtime validator that logs precise, actionable errors; include a “strict mode” and a “best‑effort” mode.
     - Provide migration utilities between schema versions; annotate deprecations.

2) XMP/IPTC mapping layer
     - Implement a mapping table from canonical JSON to XMP/IPTC, with defaults and normalization (e.g., language tags, keyword hierarchies).
     - Expose a “profile” switch: catalog‑friendly minimal vs. full research profile.

3) Classification ingestion and regions
     - Standardize ingestion adapters for common classifiers (e.g., face, nsfw, object, OCR) with model/version capture.
     - Add region support (bbox/polygons) in canonical JSON and write IPTC Image Region when available; else store regions in aaa: namespace.

4) Provenance, integrity, and privacy
     - Add content_hash for pixel data, workflow_hash, and per‑asset hashes; sign the canonical JSON optionally (detached JWS) and record signer.
     - Add privacy filters to remove sensitive paths, usernames, serials when exporting for public sharing.

5) Tooling surface
     - CLI: inspect, validate, migrate, and rewrite images/sidecars; export CSV/Parquet for DAM imports.
     - SDK: small Python package to read/write the canonical JSON and XMP, with adapters for PNG/JPEG.
     - UI nodes: “Metadata Inspector” to preview embedded/sidecar content; “Redactor” for public‑safe exports.

6) Performance and robustness
     - Hash sidecar caching (done above) and async hashing where safe; cache model index for LoRA/embeddings.
     - Graceful fallbacks for JPEG; chunked compression of JSON in PNG.

7) Interop emitters (optional)
     - A1111 parameters string, Civitai resource JSON, and schema.org minimal JSON‑LD snippet for web.

### Edge cases to handle

- Very long prompts/captions: truncate only compatibility strings; keep full text in canonical JSON and XMP alt‑text.
- Batch/variation runs: record batch_index and seeds[], with linkage back to the prompt.
- Mixed‑source images (photo + AI inpaint): record IPTC DigitalSourceType and per‑region provenance if possible.
- Locale/encoding: normalize numbers with dot decimals; store text as UTF‑8; add lang codes.
- Third‑party fields: preserve unknown keys in a vendor: namespace to avoid data loss.

### Success criteria

- Opens in Adobe/DAMs with keywords, title, rights, and source type visible; no metadata drop on save/export.
- Reconstructable AI setup: from metadata to runnable parameters at high fidelity.
- Searchable analytics: filter by model, subject, tag confidences, environment.
- Safe sharing: public export with redacted sensitive data and stable pointers to sidecars.

---

## � Canonical JSON Schema (skeleton)

Note: This is a draft JSON Schema skeleton (v0). It defines the primary sections and key properties without all constraints; we’ll iterate as features land. Use this as a contract for producers/consumers and for validation tooling.

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://aaa.example.org/schema/ai-image-metadata.schema.json",
    "title": "AAA Canonical AI Image Metadata",
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "basic": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "creator": {"type": "string"},
                "copyright": {"type": "string"},
                "usage_terms": {"type": "string"},
                "language": {"type": "string"}
            },
            "additionalProperties": true
        },
        "classification": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "lang": {"type": "string"},
                            "path": {"type": "string"},
                            "uri": {"type": "string", "format": "uri"},
                            "source": {"type": "string", "enum": ["human", "model", "other"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                        },
                        "required": ["value"],
                        "additionalProperties": false
                    }
                },
                "subject_codes": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": false
        },
        "technical": {
            "type": "object",
            "properties": {
                "pixel": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "minimum": 1},
                        "height": {"type": "integer", "minimum": 1},
                        "colorspace": {"type": "string"},
                        "bit_depth": {"type": "integer", "minimum": 1},
                        "dpi": {"type": "number", "minimum": 1},
                        "profile_name": {"type": "string"}
                    },
                    "additionalProperties": false
                },
                "file": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "string"},
                        "size_bytes": {"type": "integer", "minimum": 0},
                        "content_hash": {
                            "type": "object",
                            "properties": {
                                "sha256": {"type": "string", "pattern": "^[A-Fa-f0-9]{64}$"}
                            },
                            "additionalProperties": false
                        },
                        "created_at": {"type": "string", "format": "date-time"},
                        "modified_at": {"type": "string", "format": "date-time"}
                    },
                    "additionalProperties": false
                }
            },
            "additionalProperties": false
        },
        "ai_info": {
            "type": "object",
            "properties": {
                "generation": {
                    "type": "object",
                    "properties": {
                        "positive_prompt": {"type": "string"},
                        "negative_prompt": {"type": "string"},
                        "steps": {"type": "integer", "minimum": 1},
                        "sampler": {"type": "string"},
                        "cfg_scale": {"type": "number"},
                        "seed": {"type": "integer"},
                        "subseed": {"type": "integer"}
                    },
                    "additionalProperties": true
                },
                "assets": {
                    "type": "object",
                    "properties": {
                        "models": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/asset"}
                        },
                        "vae": {"$ref": "#/$defs/asset"},
                        "loras": {"type": "array", "items": {"$ref": "#/$defs/lora"}},
                        "controlnets": {"type": "array", "items": {"$ref": "#/$defs/asset"}},
                        "embeddings": {"type": "array", "items": {"$ref": "#/$defs/asset"}}
                    },
                    "additionalProperties": false
                },
                "workflow": {
                    "type": "object",
                    "properties": {
                        "graph_hash": {"type": "string"},
                        "engine": {
                            "type": "object",
                            "properties": {
                                "comfyui_commit": {"type": "string"},
                                "node_pack_versions": {"type": "object"}
                            },
                            "additionalProperties": true
                        }
                    },
                    "additionalProperties": true
                },
                "analysis": {
                    "type": "object",
                    "properties": {
                        "tags": {"type": "array", "items": {"$ref": "#/$defs/tag"}},
                        "detections": {"type": "array", "items": {"$ref": "#/$defs/detection"}},
                        "ocr": {"type": "array", "items": {"$ref": "#/$defs/ocr"}},
                        "caption": {"type": "array", "items": {"$ref": "#/$defs/caption"}}
                    },
                    "additionalProperties": false
                }
            },
            "additionalProperties": false
        },
        "provenance": {
            "type": "object",
            "properties": {
                "generator": {"type": "object", "properties": {"tool_name": {"type": "string"}, "tool_version": {"type": "string"}, "writer_version": {"type": "string"}, "schema_version": {"type": "integer"}}, "additionalProperties": false},
                "timestamps": {"type": "object", "properties": {"started_at": {"type": "string", "format": "date-time"}, "finished_at": {"type": "string", "format": "date-time"}, "duration_ms": {"type": "integer"}}, "additionalProperties": false},
                "environment": {"type": "object", "properties": {"os": {"type": "string"}, "python": {"type": "string"}, "cuda": {"type": "string"}, "gpu": {"type": "string"}}, "additionalProperties": true},
                "signature": {"type": "object", "properties": {"type": {"type": "string"}, "value": {"type": "string"}}, "additionalProperties": true}
            },
            "additionalProperties": false
        }
    },
    "$defs": {
        "asset": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "path_hint": {"type": "string"},
                "hash": {"type": "object", "properties": {"sha256": {"type": "string", "pattern": "^[A-Fa-f0-9]{64}$"}}, "additionalProperties": true},
                "version": {"type": "string"},
                "source": {"type": "string"}
            },
            "required": ["name"],
            "additionalProperties": true
        },
        "lora": {
            "allOf": [
                {"$ref": "#/$defs/asset"},
                {"type": "object", "properties": {"strength_model": {"type": "number"}, "strength_clip": {"type": "number"}}, "additionalProperties": true}
            ]
        },
        "tag": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "score": {"type": "number"}, "model": {"type": "string"}, "threshold": {"type": "number"}, "method": {"type": "string"}},
            "required": ["label"],
            "additionalProperties": false
        },
        "detection": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "score": {"type": "number"}, "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}, "polygon": {"type": "array", "items": {"type": "number"}}, "model": {"type": "string"}},
            "required": ["label"],
            "additionalProperties": true
        },
        "ocr": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}, "conf": {"type": "number"}, "model": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": true
        },
        "caption": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "lang": {"type": "string"}, "model": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": false
        }
    }
}
```

---

## 🗺️ XMP/IPTC mapping table (draft)

Below is a pragmatic first pass mapping of canonical JSON paths to XMP/IPTC properties. The aaa: namespace is our extension (stable URI to be documented). Some entries are lossy summaries or pointers by design.

| Canonical JSON path | XMP/IPTC property | Notes |
|---|---|---|
| basic.title | dc:title["x-default"] | Localized Alt text supported |
| basic.description | dc:description["x-default"] |  |
| basic.creator | dc:creator[1] | List supported |
| basic.copyright | dc:rights["x-default"] | Or xmpRights:Marked/UsageTerms |
| basic.usage_terms | xmpRights:UsageTerms["x-default"] |  |
| basic.language | dc:language | RFC 5646 tag |
| classification.keywords[].value | dc:subject | Flattened; hierarchical to iptcExt:CVterm |
| classification.keywords[].path | lr:hierarchicalSubject | Lightroom hierarchical keywords |
| classification.keywords[].uri | iptcExt:CVterm | With iptcExt:CVtermAbout |
| technical.pixel.width | tiff:ImageWidth | PNG/JPEG as applicable |
| technical.pixel.height | tiff:ImageLength |  |
| technical.pixel.colorspace | photoshop:ColorMode | Or exif:ColorSpace |
| technical.pixel.profile_name | photoshop:ICCProfile |  |
| technical.file.format | dc:format | image/png, image/jpeg |
| technical.file.size_bytes | xmpMM:FileSize | Not always embedded |
| technical.file.content_hash.sha256 | xmpMM:InstanceID | Or custom aaa:hashes with algo |
| ai_info.generation.positive_prompt | aaa:gen/aaa:positivePrompt | Namespaced |
| ai_info.generation.negative_prompt | aaa:gen/aaa:negativePrompt |  |
| ai_info.generation.steps | aaa:gen/aaa:steps |  |
| ai_info.generation.sampler | aaa:gen/aaa:sampler |  |
| ai_info.generation.cfg_scale | aaa:gen/aaa:cfgScale |  |
| ai_info.generation.seed | aaa:gen/aaa:seed |  |
| ai_info.assets.models[] | aaa:assets/aaa:models | name, hash, version |
| ai_info.assets.loras[] | aaa:assets/aaa:loras | name, strengths, hash |
| ai_info.assets.controlnets[] | aaa:assets/aaa:controlnets |  |
| ai_info.workflow.graph_hash | aaa:workflow/aaa:graphHash |  |
| ai_info.workflow.engine | aaa:workflow/aaa:engine | comfyui_commit, packs |
| ai_info.analysis.tags[] | aaa:analysis/aaa:tags | label, score, model |
| ai_info.analysis.detections[] | iptcExt:ImageRegion or aaa:analysis/aaa:detections | Prefer IPTC region where possible |
| ai_info.analysis.ocr[] | aaa:analysis/aaa:ocr |  |
| ai_info.analysis.caption[] | aaa:analysis/aaa:caption | Lang alt-text possible |
| provenance.generator | aaa:prov/aaa:generator | tool/version/writer/schema |
| provenance.timestamps | xmp:CreateDate, xmp:MetadataDate, aaa:prov/aaa:durationMs |  |
| provenance.environment | aaa:prov/aaa:environment | os/python/cuda/gpu |
| sidecar pointer (overflow) | aaa:sidecarRef | If JSON stored externally |

Namespace notes:

- dc: <http://purl.org/dc/elements/1.1/>
- xmp: <http://ns.adobe.com/xap/1.0/>
- xmpMM: <http://ns.adobe.com/xap/1.0/mm/>
- photoshop: <http://ns.adobe.com/photoshop/1.0/>
- tiff: <http://ns.adobe.com/tiff/1.0/>
- xmpRights: <http://ns.adobe.com/xap/1.0/rights/>
- iptcExt: <http://iptc.org/std/Iptc4xmpExt/2008-02-29/>
- lr: <http://ns.adobe.com/lightroom/1.0/>
- aaa: <https://aaa.example.org/ns/1.0/>

---

## 🧩 Fault tolerance and validation policy

Our default stance: always write what you have. The system never blocks image saving due to missing or malformed metadata. Validation is advisory by default and focuses on essential safety checks only.

Principles
- Write‑what‑you‑have guarantee: missing fields or parse errors never prevent writing; we only omit/clean problematic fields.
- No invented defaults: we don’t fabricate values (seed, cfg, hashes). If a field is unknown, we either omit it in the canonical JSON/XMP or mark it as unknown in compatibility strings only.
- Essential checks only (default):
    - Structural: width/height > 0; strings are UTF‑8 clean; remove control characters that break XMP.
    - Size safety: estimate embedded sizes; if too large, apply staged fallback (reduced → minimal → sidecar) and record the stage.
    - Type sanity: drop or coerce obviously malformed types (e.g., non‑numeric in numeric fields) with a warning.
- Advisory checks (opt‑in): reproducibility completeness, asset hash presence, enum suggestions, timestamp ordering.
- Profiles control strictness: “generated‑minimal” by default (lenient); “generated‑repro” or “research‑full” can elevate some warnings to errors, but only when explicitly selected.

Enums policy
- Enums are hints, not gates. We document recommended values to aid interop and UI dropdowns, but do not reject novel values in default mode. Strict mode may enforce enums for CI/QA use cases.

Error handling
- Per‑field try/except and error aggregation; we log warnings with concise codes and continue.
- Normalization is idempotent and deterministic; re‑validation of normalized output is a no‑op.

Why this matches our goals
- Fault‑tolerant by design, minimal bloat, and no hidden assumptions. Catalogers still get reliable XMP; advanced users can opt into stricter guarantees when needed.

---

## 🛡️ Schema & profiles policy (non‑blocking design)

We define profiles to communicate expectations without turning them into gates. Profiles never stop image saving; they only annotate gaps.

### Profile matrix (essentials vs advisory)

| Profile | Essential (warn if missing) | Advisory (inform only) | Notes |
|---------|-----------------------------|-------------------------|-------|
| generated-minimal (default) | pixel.width/height, file.format, model name, steps, sampler | seed, cfg_scale, model hash, positive_prompt | Suitable for casual sharing; omissions allowed |
| generated-repro (opt-in) | all generated-minimal + seed + cfg_scale + model hash + workflow.graph_hash | vae hash, lora hashes, subseed | Ensures near-reproducibility |
| catalog-minimal | pixel.width/height, file.format, title OR description | keywords, language, creator | For DAM ingestion when AI data may be partial |
| research-full | all generated-repro + all asset hashes + environment details + analysis tags | detections polygons, ocr, caption language | Internal analytics & audits |

Behavior

- Essential missing: logged as warning (code=WARN_REQUIRED_MISSING, path=...).
- Advisory missing: logged as info only; never escalated.
- Strict mode (opt-in) can elevate essential warnings to errors for CI but still does not block image write; errors just set validation_result.ok=false for downstream automation.

### Non-blocking strategy

- All write paths call validator in best-effort mode first.
- If validator reports structural corruption (e.g., cannot serialize JSON), we strip only offending keys, then proceed.
- Fallback metadata stages never discard prompts unless size constraints force minimal set—then we keep full prompts in sidecar.

### Required field philosophy

- A field is only “essential” if downstream tooling commonly depends on it (dimensions, format, core model identity). Everything else is enrichment.
- Hashes: recommended essential only in reproducibility or research profiles; casual profile treats them as advisory.
- Prompts: positive prompt is advisory (some generations might be classifier-only or redacted); we never invent a placeholder.

### Enum usage recap

- Documented set published separately (e.g., sampler, colorspace) for UI hints.
- Accept any unknown value silently; on strict mode we can warn UNRECOGNIZED_ENUM but never block.

### Error code list (concise)

- WARN_REQUIRED_MISSING – Essential field absent for selected profile.
- WARN_SIZE_FALLBACK – Fallback stage applied (reduced/minimal/sidecar).
- WARN_TYPE_COERCED – Value coerced ("32" -> 32 int) successfully.
- INFO_ADVISORY_MISSING – Advisory field absent (no action needed).
- INFO_ENUM_HINT – Value outside documented hints.
- INFO_NORMALIZED – Whitespace/control chars cleaned.
- ERROR_SERIALIZATION_STRIPPED – A value dropped due to irreparable structure (still writing remainder).

### Minimal validator stub shape (for later implementation)

```python
class ValidationResult(TypedDict):
    ok: bool  # Always True in default mode unless catastrophic serialization failure
    warnings: list[dict]
    info: list[dict]
    errors: list[dict]
    normalized: dict  # post-normalization
    profile: str
    fallback_stage: str | None

def validate(metadata: dict, profile: str = "generated-minimal", strict: bool = False) -> ValidationResult:
    # 1. Shallow structural checks
    # 2. Gather essentials list based on profile; mark missing as warnings
    # 3. Advisory fields -> info
    # 4. Size estimation -> fallback recommendations (not implemented here)
    # 5. Normalizations (trim whitespace, remove control chars)
    return result
```

### Practical outcome

- Users never lose an image due to metadata issues.
- Partial metadata is still valuable; enrichment can occur in later passes (post-process augmentation or batch migration).
- Downstream automation can read warnings to improve quality iteratively without fearing blocked saves.

---

## �🔑 Core Metadata Collection Approaches

### 1. Execution Hooks (xxmjskxx & nkchocoai)

**How it works:**

```python
# saveimage_unimeta/hook.py
def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt, current_extra_data
    current_prompt = prompt
    current_extra_data = extra_data
    prompt_executer = self

def pre_get_input_data(inputs, class_def, unique_id, *args):
    global current_save_image_node_id
    if class_def == SaveImageWithMetaDataUniversal:
        current_save_image_node_id = unique_id
```

**Advantages:**

- Captures the **live execution state** (only nodes that actually ran)
- Access to resolved values via `get_input_data()` (not just static workflow JSON)
- Can trace connections backwards from save node

**Risks:**

- Relies on monkey-patching ComfyUI's dispatcher (future API changes can break it)
- Multiple node packs hooking the same functions can conflict
- Hook logic runs on every node execution (performance impact if heavy)
- State can leak between simultaneous workflows or queued runs
- Exceptions in hooks surface as execution failures for unrelated nodes

**Our Current Approach:**

✅ We use `WorkflowParser` + `WorkflowExtractor` to walk the workflow JSON without hooks  
✅ Safer for multi-session environments  
❌ May miss runtime-only values or conditional branches  

**Recommendation:** **Hybrid approach** - Keep our parser-based system as default, but add an **optional hook mode** for advanced users who need runtime value resolution. Gate it behind a feature flag and provide clear warnings about multi-pack conflicts.

---

### 2. BFS Graph Traversal for Sampler Discovery

**Implementation (saveimage_unimeta/trace.py):**

```python
@classmethod
def trace(cls, start_node_id, prompt):
    Q = deque()
    Q.append((start_node_id, 0))  # (node_id, distance)
    visited = set()
    trace_tree = {start_node_id: (0, class_type)}
    
    while Q:
        current_node_id, distance = Q.popleft()
        input_fields = prompt[current_node_id]["inputs"]
        
        for value in input_fields.values():
            if isinstance(value, list):
                nid = value[0]  # Connection reference
                if nid not in visited and nid in prompt:
                    class_type = prompt[nid]["class_type"]
                    trace_tree[nid] = (distance + 1, class_type)
                    Q.append((nid, distance + 1))
                    visited.add(nid)
    
    return trace_tree  # {node_id: (distance, class_type)}
```

**Sampler Selection Strategies:**

1. **Distance-based:** Farthest/Nearest from save node
2. **Explicit ID:** User specifies exact node ID
3. **Heuristic fallback:** Looks for nodes with `Steps` + `CFG` fields when sampler not explicitly defined

**Filtering by Distance:**

```python
@classmethod
def filter_inputs_by_trace_tree(cls, inputs, trace_tree):
    filtered_inputs = {}
    for meta, inputs_list in inputs.items():
        for entry in inputs_list:
            node_id, input_value = entry[0], entry[1]
            trace = trace_tree.get(node_id)
            if trace:
                distance = trace[0]
                filtered_inputs.setdefault(meta, []).append(
                    (node_id, input_value, distance)
                )
    
    # Sort by distance (closest first)
    for k, v in filtered_inputs.items():
        filtered_inputs[k] = sorted(v, key=lambda x: x[2])
    
    return filtered_inputs
```

**Our Current Approach:**

✅ `WorkflowParser` walks the graph and identifies samplers  
❌ Doesn't prioritize by distance or handle multiple samplers gracefully  
❌ No heuristic fallback for unknown sampler types  

**Recommendation:** **Add BFS-based distance sorting to `WorkflowParser`**

- Prioritize nodes closer to the save node when multiple candidates exist
- Implement heuristic sampler detection (nodes with `steps` + `cfg` fields)
- Support multi-sampler workflows (e.g., Wan 2.2 i2v refiner patterns)

**Concrete Implementation:**

```python
# eric_metadata/utils/workflow_parser.py
def _trace_from_node(self, start_node_id: str, workflow: Dict) -> Dict[str, Tuple[int, str]]:
    """BFS trace returning {node_id: (distance, class_type)}"""
    from collections import deque
    Q = deque([(start_node_id, 0)])
    visited = {start_node_id}
    trace = {start_node_id: (0, workflow[start_node_id].get('class_type', 'Unknown'))}
    
    while Q:
        nid, dist = Q.popleft()
        inputs = workflow[nid].get('inputs', {})
        for val in inputs.values():
            if isinstance(val, list) and val[0] in workflow and val[0] not in visited:
                child_type = workflow[val[0]].get('class_type', 'Unknown')
                trace[val[0]] = (dist + 1, child_type)
                Q.append((val[0], dist + 1))
                visited.add(val[0])
    return trace

def _find_best_sampler(self, trace: Dict[str, Tuple[int, str]], workflow: Dict) -> Optional[str]:
    """Find closest sampler using distance + heuristics"""
    candidates = []
    for nid, (dist, ctype) in trace.items():
        if ctype in self.parameter_mappings:  # Known sampler
            candidates.append((dist, 0, nid))  # priority 0 = exact match
        else:
            node = workflow[nid]
            inputs = node.get('inputs', {})
            if 'steps' in inputs and 'cfg' in inputs:  # Heuristic match
                candidates.append((dist, 1, nid))  # priority 1 = heuristic
    
    if not candidates:
        return None
    
    # Sort by (distance, priority) - closest exact match wins
    candidates.sort()
    return candidates[0][2]
```

---

### 3. Declarative Rule-Based Capture System

**The Innovation (xxmjskxx):**

Instead of hardcoding logic for every node type, they use **declarative JSON/Python rules**:

**Rule Structure:**

```python
# saveimage_unimeta/defs/captures.py
CAPTURE_FIELD_LIST = {
    'KSampler': {
        MetaField.SAMPLER_NAME: {'field_name': 'sampler_name'},
        MetaField.SCHEDULER: {'field_name': 'scheduler'},
        MetaField.STEPS: {'field_name': 'steps'},
        MetaField.CFG: {'field_name': 'cfg'},
        MetaField.SEED: {'field_name': 'seed'},
        MetaField.DENOISE: {'field_name': 'denoise'}
    },
    'LoraLoader': {
        MetaField.LORA_MODEL_NAME: {'field_name': 'lora_name'},
        MetaField.LORA_STRENGTH_MODEL: {'field_name': 'strength_model'},
        MetaField.LORA_STRENGTH_CLIP: {'field_name': 'strength_clip'}
    }
}
```

**Advanced Features:**

1. **Validators** - Conditional capture based on graph context:

```python
def is_positive_prompt(node_inputs, input_data):
    """Check if this CLIP encoder is in the positive conditioning chain"""
    # Logic to trace connections and determine role
    pass

MetaField.POSITIVE_PROMPT: {
    'field_name': 'text',
    'validate': is_positive_prompt  # Only capture if validator returns True
}
```

1. **Formatters** - Transform raw values:

```python
def calc_model_hash(ckpt_name, input_data):
    """Calculate hash from checkpoint path"""
    path = folder_paths.get_full_path("checkpoints", ckpt_name)
    return hash_file_with_cache(path)

MetaField.MODEL_HASH: {
    'field_name': 'ckpt_name',
    'format': calc_model_hash
}
```

1. **Dynamic User Extensions:**

```json
// saveimage_unimeta/user_captures.json
{
  "nodes": {
    "MyCustomSampler": {
      "SAMPLER_NAME": {"field_name": "my_sampler_field"},
      "STEPS": {"field_name": "iteration_count"}
    }
  }
}
```

**Rule Scanner Tool:**

- Scans all installed nodes automatically
- Generates suggested capture rules based on input field names
- Outputs user-editable JSON that gets merged at runtime
- "Missing-only lens" shows gaps in current coverage

**Our Current Approach:**

✅ `node_parameter_mapping.py` has some field mappings  
❌ Hardcoded in Python (requires code changes for new nodes)  
❌ No user extensibility without editing source  
❌ No validator/formatter system  

**Recommendation:** **Implement a hybrid declarative rule system**

#### Phase 1: Internal Refactor (Low Risk)

```python
# eric_metadata/utils/node_capture_rules.py
from typing import Dict, Any, Callable, Optional
from enum import Enum

class MetadataField(Enum):
    POSITIVE_PROMPT = "positive_prompt"
    NEGATIVE_PROMPT = "negative_prompt"
    MODEL = "model"
    SAMPLER = "sampler"
    # ... etc

class CaptureRule:
    def __init__(
        self,
        field_name: str,
        validator: Optional[Callable] = None,
        formatter: Optional[Callable] = None
    ):
        self.field_name = field_name
        self.validator = validator
        self.formatter = formatter

# Built-in rules
DEFAULT_RULES: Dict[str, Dict[MetadataField, CaptureRule]] = {
    'KSampler': {
        MetadataField.SAMPLER: CaptureRule('sampler_name'),
        MetadataField.STEPS: CaptureRule('steps'),
        # ...
    }
}

# Load user extensions from JSON
def load_user_rules() -> Dict:
    """Load from eric_metadata/user_node_rules.json if it exists"""
    pass
```

#### Phase 2: User Extension Support (Medium Risk)

- Add JSON file: `eric_metadata/user_node_rules.json`
- Merge user rules with defaults at runtime
- Document JSON schema in `docs/CUSTOM_NODE_RULES.md`

#### Phase 3: Rule Scanner UI (Advanced)

- Optional node that scans installed packs
- Generates suggested rules
- Lets users copy/edit before saving

---

### 4. LoRA Inline Tag Parsing

**The Problem:**

LoRAs can be specified in three ways:

1. **Loader nodes** (e.g., `LoraLoader`)
2. **Inline tags** in prompts: `<lora:name:strength_model:strength_clip>`
3. **Prompt control extensions** that parse tags dynamically

**xxmjskxx Solution (saveimage_unimeta/utils/lora.py):**

```python
# Strict pattern: <lora:name:float:float>
STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")

# Legacy fallback
LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")

def parse_lora_syntax(text: str) -> tuple[list[str], list[float], list[float]]:
    """Extract LoRA names and strengths from prompt text"""
    names, strengths_model, strengths_clip = [], [], []
    
    for match in STRICT.finditer(text):
        names.append(match.group(1))
        strengths_model.append(float(match.group(2)))
        strengths_clip.append(float(match.group(3)) if match.group(3) else float(match.group(2)))
    
    # If nothing found, try legacy pattern
    if not names:
        for match in LEGACY.finditer(text):
            # ... parse legacy format
    
    return names, strengths_model, strengths_clip

def resolve_lora_display_names(raw_names: list[str]) -> list[str]:
    """Look up full filenames from base names"""
    lora_index = build_lora_index()  # Scan LoRA folder
    resolved = []
    for name in raw_names:
        # Try exact match, then case-insensitive, then fuzzy
        resolved.append(lora_index.get(name, name))
    return resolved
```

**Reconciliation with Loader Nodes:**

```python
def gen_loras(cls, inputs):
    # Collect from loader nodes
    model_names = inputs.get(MetaField.LORA_MODEL_NAME, [])
    
    # Parse inline tags from prompts
    prompts = inputs.get(MetaField.POSITIVE_PROMPT, []) + \
              inputs.get(MetaField.NEGATIVE_PROMPT, [])
    
    for prompt_text in prompts:
        inline_names, inline_sm, inline_sc = parse_lora_syntax(prompt_text)
        model_names.extend(inline_names)
        # ... merge strengths
    
    # Deduplicate and emit
    return deduplicated_loras
```

**Our Current Approach:**
❌ `workflow_parser.py` has no LoRA inline tag support  
❌ Only captures LoRAs from loader nodes  
❌ Prompt Control and similar extensions cause missed LoRAs  

**Recommendation:** **Add inline LoRA tag parser to `WorkflowParser`**

```python
# eric_metadata/utils/workflow_parser.py

import re
from typing import List, Tuple

class WorkflowParser:
    # Add regex patterns
    LORA_STRICT = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)(?::([0-9]*\.?[0-9]+))?>")
    LORA_LEGACY = re.compile(r"<lora:([^:>]+):([^>]+)>")
    
    def _parse_lora_tags(self, text: str) -> List[Tuple[str, float, float]]:
        """Extract LoRA info from inline tags in prompt text"""
        loras = []
        
        for match in self.LORA_STRICT.finditer(text):
            name = match.group(1)
            strength_model = float(match.group(2))
            strength_clip = float(match.group(3)) if match.group(3) else strength_model
            loras.append((name, strength_model, strength_clip))
        
        # Fallback to legacy if nothing found
        if not loras:
            for match in self.LORA_LEGACY.finditer(text):
                name = match.group(1)
                strength_str = match.group(2)
                # Parse "0.8" or "0.8:0.6" format
                parts = strength_str.split(':')
                sm = float(parts[0])
                sc = float(parts[1]) if len(parts) > 1 else sm
                loras.append((name, sm, sc))
        
        return loras
    
    def extract_and_analyze(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        # ... existing code ...
        
        # After extracting prompts, scan for inline LoRAs
        all_loras = []
        
        for prompt_text in result['prompts']['positive'] + result['prompts']['negative']:
            inline_loras = self._parse_lora_tags(prompt_text)
            all_loras.extend(inline_loras)
        
        # Merge with LoRAs from loader nodes
        for node_id, node_data in result['raw_nodes'].items():
            if node_data.get('class_type') == 'LoraLoader':
                # ... existing loader logic
                pass
        
        # Deduplicate (keep first occurrence)
        seen_names = set()
        unique_loras = []
        for name, sm, sc in all_loras:
            if name not in seen_names:
                unique_loras.append({'name': name, 'strength_model': sm, 'strength_clip': sc})
                seen_names.add(name)
        
        result['generation_parameters']['loras'] = unique_loras
        
        return result
```

---

### 5. Hash Calculation with Caching

**The Problem:**
Hashing large checkpoint files (2-8GB+) is slow. Repeated workflow executions re-hash the same files.

**xxmjskxx Solution (.sha256 sidecars):**

```python
# saveimage_unimeta/defs/formatters.py

def hash_file_with_cache(path: str) -> str:
    """Calculate SHA256 hash, using .sha256 cache file if available"""
    cache_path = path + '.sha256'
    
    # Check if cache exists and is newer than the file
    if os.path.exists(cache_path):
        file_mtime = os.path.getmtime(path)
        cache_mtime = os.path.getmtime(cache_path)
        
        if cache_mtime >= file_mtime:
            # Cache is valid, read it
            try:
                with open(cache_path, 'r') as f:
                    cached_hash = f.read().strip()
                if len(cached_hash) == 64:  # Valid SHA256
                    return cached_hash
            except Exception:
                pass
    
    # Cache miss or invalid - compute hash
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    
    hash_value = sha256.hexdigest()
    
    # Write cache file
    try:
        with open(cache_path, 'w') as f:
            f.write(hash_value)
    except Exception:
        pass  # Non-fatal if we can't write cache
    
    return hash_value
```

**Benefits:**

- **First run:** Normal hash time (e.g., 5-10 seconds for 8GB model)
- **Subsequent runs:** Instant (<1ms file read)
- **Auto-invalidation:** Re-hashes if model file is modified

**Our Current Approach:**
❌ No hash caching system  
❌ Re-computes hashes on every save  

**Recommendation:** **Implement .sha256 sidecar caching**

```python
# eric_metadata/utils/hash_utils.py (enhance existing file)

import hashlib
import os
from typing import Optional

def hash_file_sha256(path: str, use_cache: bool = True) -> Optional[str]:
    """
    Calculate SHA256 hash of file, optionally using .sha256 cache.
    
    Args:
        path: Absolute path to file
        use_cache: If True, read/write .sha256 sidecar files
    
    Returns:
        Hex digest string, or None if file doesn't exist
    """
    if not os.path.exists(path):
        return None
    
    cache_path = path + '.sha256'
    
    # Try cache first
    if use_cache and os.path.exists(cache_path):
        try:
            file_mtime = os.path.getmtime(path)
            cache_mtime = os.path.getmtime(cache_path)
            
            if cache_mtime >= file_mtime:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = f.read().strip()
                if len(cached) == 64 and all(c in '0123456789abcdef' for c in cached.lower()):
                    return cached
        except Exception as e:
            if self.debug:
                print(f"[HashCache] Failed to read cache for {path}: {e}")
    
    # Compute hash
    try:
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(8192):  # 8KB chunks
                sha256.update(chunk)
        
        hash_value = sha256.hexdigest()
        
        # Write cache
        if use_cache:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    f.write(hash_value + '\n')
            except Exception as e:
                if self.debug:
                    print(f"[HashCache] Failed to write cache for {path}: {e}")
        
        return hash_value
        
    except Exception as e:
        print(f"[Hash] Error hashing {path}: {e}")
        return None

# Update existing hash functions to use cache
def get_model_hash(model_path: str) -> str:
    """Get model hash with caching"""
    return hash_file_sha256(model_path, use_cache=True) or "unknown"
```

**Update Workflow Metadata Processor:**

```python
# eric_metadata/utils/workflow_metadata_processor.py

# Replace direct hash calls with cached version
from .hash_utils import hash_file_sha256

def _get_checkpoint_hash(self, checkpoint_name: str) -> str:
    try:
        path = folder_paths.get_full_path("checkpoints", checkpoint_name)
        if path:
            return hash_file_sha256(path, use_cache=True) or "unknown"
    except Exception:
        pass
    return "unknown"
```

---

### 6. JPEG Metadata Fallback Strategy

**The Problem:**
JPEG EXIF has a hard ~64KB limit. Large workflows exceed this.

**xxmjskskxx Tiered Fallback:**

```python
# saveimage_unimeta/nodes/save_image.py

def save_images(self, file_format="png", max_jpeg_exif_kb=60, ...):
    if file_format == "jpeg":
        exif_bytes = build_exif(workflow, metadata)
        
        if len(exif_bytes) > max_jpeg_exif_kb * 1024:
            # Stage 1: Parameters-only (drop workflow JSON)
            exif_bytes = build_exif(parameters_only=True)
            fallback_stage = "reduced-exif"
            
            if len(exif_bytes) > max_jpeg_exif_kb * 1024:
                # Stage 2: Minimal parameters (trim non-essential fields)
                parameters = trim_to_minimal(parameters)
                exif_bytes = build_exif(minimal_parameters=parameters)
                fallback_stage = "minimal"
                
                if len(exif_bytes) > max_jpeg_exif_kb * 1024:
                    # Stage 3: COM marker (JPEG comment, not EXIF)
                    exif_bytes = None
                    fallback_stage = "com-marker"
        
        # Append fallback indicator to parameters string
        if fallback_stage != "none":
            parameters += f", Metadata Fallback: {fallback_stage}"
```

**Minimal Parameters Allowlist:**

```python
def _build_minimal_parameters(full_parameters: str) -> str:
    """Keep only essential fields for JPEG COM marker"""
    allow_keys = {
        "Steps", "Sampler", "CFG scale", "Seed",
        "Model", "Model hash", "VAE", "VAE hash",
        "Hashes", "Metadata generator version"
    }
    allow_prefixes = ("Lora_",)  # Keep all LoRA entries
    
    # Parse and filter
    # ... (see implementation in source)
    return minimal_string
```

**Our Current Approach:**
✅ We support JPEG via standard save  
❌ No size monitoring or fallback strategy  
❌ Large workflows may fail silently or strip all metadata  

**Recommendation:** **Add staged JPEG fallback**

```python
# nodes/eric_metadata_save_image_v099d.py

def _save_as_jpeg(self, image, path, metadata_dict, workflow_json, max_exif_kb=60):
    """Save JPEG with intelligent metadata fallback"""
    
    # Stage 1: Try full metadata
    exif_data = self._build_exif_dict(metadata_dict, workflow_json, include_workflow=True)
    exif_bytes = piexif.dump(exif_data)
    
    fallback_stage = "full"
    
    if len(exif_bytes) > max_exif_kb * 1024:
        # Stage 2: Drop workflow, keep metadata
        exif_data = self._build_exif_dict(metadata_dict, workflow_json=None, include_workflow=False)
        exif_bytes = piexif.dump(exif_data)
        fallback_stage = "reduced"
        
        if len(exif_bytes) > max_exif_kb * 1024:
            # Stage 3: Minimal metadata only
            minimal_metadata = self._trim_to_essential(metadata_dict)
            exif_data = self._build_exif_dict(minimal_metadata, workflow_json=None, include_workflow=False)
            exif_bytes = piexif.dump(exif_data)
            fallback_stage = "minimal"
            
            if len(exif_bytes) > max_exif_kb * 1024:
                # Stage 4: Use JPEG comment instead of EXIF
                img.save(path, quality=quality, optimize=True, 
                        comment=self._format_minimal_comment(metadata_dict))
                fallback_stage = "comment"
                if self.debug:
                    print(f"[JPEG] Metadata too large for EXIF, using comment marker")
                return
    
    # Save with EXIF
    img.save(path, quality=quality, optimize=True, exif=exif_bytes)
    
    if fallback_stage != "full" and self.debug:
        print(f"[JPEG] Applied fallback stage: {fallback_stage}")

def _trim_to_essential(self, metadata: dict) -> dict:
    """Keep only critical fields for minimal JPEG fallback"""
    essential = {}
    
    # Always keep
    keep_keys = [
        'ai_info.generation.positive_prompt',
        'ai_info.generation.negative_prompt', 
        'ai_info.generation.model',
        'ai_info.generation.seed',
        'ai_info.generation.steps',
        'ai_info.generation.cfg_scale',
        'ai_info.generation.sampler',
        'technical.width',
        'technical.height'
    ]
    
    for key_path in keep_keys:
        value = self._get_nested_value(metadata, key_path)
        if value is not None:
            self._set_nested_value(essential, key_path, value)
    
    # Keep all LoRAs (compact representation)
    if 'ai_info' in metadata and 'loras' in metadata['ai_info']:
        essential.setdefault('ai_info', {})['loras'] = metadata['ai_info']['loras']
    
    return essential
```

---

### 7. Metadata Storage Format Comparison

| Repository | Format | Namespace | Workflow Embedding | Notes |
|------------|--------|-----------|-------------------|-------|
| **xxmjskxx** | A1111-style parameter string | None (flat keys) | PNG: Yes, JPEG: Conditional | `"Positive prompt: ...\nNegative prompt: ...\nSteps: 20, Sampler: euler, CFG scale: 7..."` |
| **nkchocoai** | A1111-style parameter string | None (flat keys) | PNG: Yes | Same as xxmjskxx parent |
| **Light-x02** | Preserves existing format | N/A (pass-through) | Preserved as-is | Doesn't generate metadata, only preserves |
| **giriss** | A1111-style parameter string | None (flat keys) | PNG: Optional | Manual field wiring required |
| **AAA_Metadata_System** | Structured JSON + XMP | ✅ Namespaced sections | PNG: Yes, multiple formats | `{"basic": {...}, "ai_info": {"generation": {...}}, "technical": {...}}` |

**Key Insight:**

**We are the ONLY repository using namespaced/structured metadata.** This is a **significant advantage** for:

- Query flexibility (JSONPath, dot notation)
- Conflict-free extension (new sections don't clash)
- Schema validation and versioning
- Professional software compatibility (XMP standard)

**Recommendation:** **Keep our namespaced approach** but add:

1. **Optional A1111 compatibility mode** - Generate flat parameter string for Civitai/PrompHero/etc.
2. **Embed both formats** - Structured in XMP + PNG chunks, flat string in PNG "parameters" field for tool compat

---

## 🎯 Detailed Improvement Recommendations for AAA_Metadata_System

### Priority 1: High Impact, Low Risk

#### 1.1 Add Hash Caching System

**Effort:** Low (2-3 hours)  
**Impact:** High (10x performance improvement for repeated saves)

**Implementation:**

- Modify `eric_metadata/utils/hash_utils.py` to use `.sha256` sidecars
- Add `use_cache` parameter (default True)
- Update all hash calls in `workflow_metadata_processor.py`

**Testing:**

```python
# Add test
def test_hash_caching():
    path = "test_model.safetensors"
    # First call - slow
    hash1 = hash_file_sha256(path, use_cache=True)
    # Second call - fast
    hash2 = hash_file_sha256(path, use_cache=True)
    assert hash1 == hash2
    assert os.path.exists(path + '.sha256')
```

---

#### 1.2 Add LoRA Inline Tag Parsing

**Effort:** Medium (4-6 hours)  
**Impact:** High (captures missed LoRAs from Prompt Control, etc.)

**Implementation:**

- Add regex patterns to `WorkflowParser`
- Scan positive/negative prompts for `<lora:name:strength>` tags
- Merge with loader node LoRAs
- Deduplicate by name

**Testing:**

- Test workflows with inline tags
- Test mixed (loader + inline tags)
- Test Prompt Control node workflows

---

#### 1.3 Implement A1111 Compatibility Mode

**Effort:** Medium (6-8 hours)  
**Impact:** High (Civitai/Prompthero compatibility)

**Implementation:**

```python
# nodes/eric_metadata_save_image_v099d.py

def _generate_a1111_string(self, metadata: dict) -> str:
    """Generate Automatic1111-style parameter string from structured metadata"""
    parts = []
    
    # Positive prompt (first line)
    pos = metadata.get('ai_info', {}).get('generation', {}).get('positive_prompt', '')
    if pos:
        parts.append(pos)
    
    # Negative prompt (second line)
    neg = metadata.get('ai_info', {}).get('generation', {}).get('negative_prompt', '')
    if neg:
        parts.append(f"Negative prompt: {neg}")
    
    # Parameters (comma-separated)
    params = []
    gen = metadata.get('ai_info', {}).get('generation', {})
    
    if 'steps' in gen:
        params.append(f"Steps: {gen['steps']}")
    if 'sampler' in gen:
        params.append(f"Sampler: {gen['sampler']}")
    if 'cfg_scale' in gen:
        params.append(f"CFG scale: {gen['cfg_scale']}")
    if 'seed' in gen:
        params.append(f"Seed: {gen['seed']}")
    
    # Size
    tech = metadata.get('technical', {})
    if 'width' in tech and 'height' in tech:
        params.append(f"Size: {tech['width']}x{tech['height']}")
    
    # Model
    if 'model' in gen:
        params.append(f"Model: {gen['model']}")
    if 'model_hash' in gen:
        params.append(f"Model hash: {gen['model_hash']}")
    
    # LoRAs
    for i, lora in enumerate(gen.get('loras', []), 1):
        name = lora.get('name', f'Lora{i}')
        sm = lora.get('strength_model', 1.0)
        sc = lora.get('strength_clip', sm)
        params.append(f"Lora {i}: {name} ({sm:.2f}, {sc:.2f})")
    
    if params:
        parts.append(", ".join(params))
    
    return "\n".join(parts)

# Add to save logic
if self.enable_metadata and self.save_embedded:
    # Structured metadata (our format)
    self.metadata_service.save_embedded(...)
    
    # A1111 compatibility (optional)
    if self.a1111_compat_mode:  # New parameter
        a1111_string = self._generate_a1111_string(metadata)
        pnginfo.add_text("parameters", a1111_string)
```

---

### Priority 2: Medium Impact, Medium Risk

#### 2.1 Add BFS Distance-Based Prioritization

**Effort:** High (8-12 hours)  
**Impact:** Medium (better sampler selection in complex workflows)

**Implementation:**

- Add `_trace_from_node()` method to `WorkflowParser`
- Modify `_find_samplers()` to use distance sorting
- Add heuristic fallback for unknown samplers
- Handle multi-sampler workflows (Wan 2.2 i2v refiner)

**Testing:**

- Simple linear workflow (should work same as before)
- Multi-sampler workflow (should pick closest)
- Unknown sampler type (should use heuristic)

---

#### 2.2 Implement JPEG Fallback Strategy

**Effort:** High (8-12 hours)  
**Impact:** Medium (prevents JPEG metadata loss)

**Implementation:**

- Add size checking to JPEG save path
- Implement 4-stage fallback (full → reduced → minimal → comment)
- Add minimal metadata trimmer
- Log fallback stage for user awareness

---

#### 2.3 Add Declarative Rule System (Internal)

**Effort:** Very High (16-24 hours)  
**Impact:** Medium (easier maintenance, future extensibility)

##### Phase 1: Internal refactor

- Create `eric_metadata/utils/node_capture_rules.py`
- Define `CaptureRule` class
- Convert `parameter_mappings` to rule format
- No external API changes yet

---

### Priority 3: Advanced Features (Future)

#### 3.1 Optional Execution Hooks

**Effort:** Very High (24-40 hours)  
**Risk:** High (conflicts with other packs)

**Implementation:**

- Add feature flag: `use_execution_hooks` (default False)
- Implement hook registration (like xxmjskxx)
- Add conflict detection (check if other packs registered hooks)
- Add fallback to parser if hooks fail

**Not Recommended for Initial Implementation** - Wait for user demand

---

#### 3.2 User-Extensible Rules (JSON)

**Effort:** Very High (20-30 hours)  
**Dependencies:** Requires 2.3 (Internal declarative system)

**Implementation:**

- Define JSON schema for user rules
- Add `eric_metadata/user_node_rules.json`
- Implement JSON → Python rule converter
- Add validation and error handling

---

#### 3.3 Rule Scanner Tool

**Effort:** Very High (40-60 hours)  
**Dependencies:** Requires 3.2 (User rules)

**Implementation:**

- Node that scans `NODE_CLASS_MAPPINGS`
- Analyzes `INPUT_TYPES()` for each node
- Generates suggested rules
- UI for editing/approving rules

**Very Advanced** - Only if user demand is high

---

## 📋 Implementation Roadmap

### Immediate (Next 2 Weeks)

1. ✅ Hash caching system (2-3 hours)
2. ✅ LoRA inline tag parsing (4-6 hours)
3. ✅ A1111 compatibility mode (6-8 hours)

**Total:** ~16 hours

### Short Term (Next Month)

1. BFS distance prioritization (8-12 hours)
2. JPEG fallback strategy (8-12 hours)

**Total:** ~20 hours

### Medium Term (Next Quarter)

1. Internal declarative rules refactor (16-24 hours)

### Long Term (Future Consideration)

1. Execution hooks (optional) - Wait for demand
2. User-extensible rules - After internal refactor proven
3. Rule scanner tool - Only if high user demand

---

## ⚠️ Risks and Mitigation

### Execution Hooks

**Risks:**

- Monkey-patching ComfyUI dispatcher
- Conflicts with other packs
- State leakage in multi-session environments
- Future API changes breaking hooks
- Exceptions causing execution failures

**Mitigation:**

- Make it opt-in (default off)
- Add conflict detection
- Provide clear warnings in UI
- Fallback to parser if hooks fail
- Extensive error handling

**Recommendation:** **Defer until proven user need**

### Declarative Rules

**Risks:**

- Breaking changes to internal APIs
- JSON schema validation complexity
- User confusion about rule format
- Rule conflicts/duplicates

**Mitigation:**

- Start with internal refactor only
- Extensive testing before exposing to users
- Clear documentation with examples
- Validation and helpful error messages

**Recommendation:** **Internal refactor first, user extension later**

---

## 🔍 Key Architectural Differences

| Aspect | xxmjskxx/nkchocoai | AAA_Metadata_System |
|--------|-------------------|---------------------|
| **Metadata Collection** | Execution hooks + BFS tracing | Workflow JSON parsing + discovery |
| **Metadata Format** | Flat A1111-style string | Namespaced JSON + XMP |
| **Node Support** | Declarative rules (user-extensible) | Hardcoded mappings |
| **LoRA Detection** | Loader nodes + inline tags | Loader nodes only |
| **Hash Caching** | .sha256 sidecars | No caching |
| **JPEG Handling** | Staged fallback (4 levels) | Standard save (no fallback) |
| **Multi-Sampler** | Distance-based priority + heuristics | Basic detection |
| **Workflow Embedding** | PNG only (JPEG conditional) | PNG + multiple formats |
| **Extensibility** | High (user JSON rules) | Low (requires code changes) |

**Our Strengths:**

- ✅ Namespaced metadata (professional, queryable)
- ✅ Multiple storage formats (embedded, XMP, text, DB)
- ✅ Human-readable text output
- ✅ Metadata query node (JSONPath, regex, dot notation)
- ✅ No execution hooks (safer for multi-pack environments)

**Their Strengths:**

- ✅ Hash caching (performance)
- ✅ LoRA inline tags (completeness)
- ✅ Distance-based sampler priority (accuracy)
- ✅ JPEG fallback (reliability)
- ✅ User-extensible rules (maintainability)

---

## 📝 Summary

**Bottom Line:**  
Our metadata system is already architecturally sound with unique advantages (namespaced structure, multi-format support, query tools). The most impactful improvements are:

1. **Hash caching** (massive performance win)
2. **LoRA inline tag parsing** (completeness)
3. **A1111 compatibility mode** (ecosystem compatibility)
4. **JPEG fallback** (reliability)
5. **BFS distance prioritization** (accuracy in complex workflows)

**Defer:**

- Execution hooks (risky, marginal benefit given our parser works well)
- User rule system (wait until internal refactor proven)
- Rule scanner UI (advanced feature, low ROI initially)

**Maintain our unique advantages:**

- Namespaced metadata structure
- Multi-format persistence
- Query/filter tools
- Human-readable output

---

## 📌 Direct answers to the original six questions

1. If we use execution hooks can it interfere with other nodes, can it cause slowdown of ComfyUI runs, what is the safest best way to implement them?

- Yes, interference is possible. Hooks monkey‑patch core execution entry points; multiple packs can register hooks and the order of registration matters. Uncaught exceptions inside a hook will bubble up as node failures. Hooks also run for every node, so heavy work inside them will slow runs.
- Slowdown: minimal when hooks only capture IDs/references and defer work; noticeable if they compute hashes, do filesystem scans, or walk large graphs synchronously in pre_execute/pre_get_input_data.
- Safest way:
    - Make it opt‑in via a feature flag (default off).
    - Detect conflicts (e.g., if another hook already patched the same function), warn and auto‑disable.
    - Keep hooks “thin”: collect only prompt, current node id, and a timestamp; defer any parsing/heavy I/O to after image save (or to our existing parser path).
    - Scope state per-execution using a context object keyed by prompt_id to avoid leakage across queued runs.
    - Provide a hard fallback: if hook initialization fails, automatically fall back to the JSON‑parser path.

1. What restructuring will we need to do with our metadata formatting and writing if we collect more data?

- Keep our namespaced JSON; do not flatten. Introduce explicit schema versioning and a stable namespace plan:
    - basic, technical, ai_info.generation, ai_info.assets (models, vae, loras, controlnets), provenance, environment.
    - Add ai_info.assets.hashes as a map per asset: { algo: value, source: path, cached: true/false }.
    - Add xmp.schema_version and writer_version for forwards/backwards compatibility.
- Add soft‑deprecation: keep old fields for one release behind a deprecated_ prefix or write both old and new fields and mark deprecated in metadata.generator.notes.
- Provide a migration shim in the writer that can read old keys and emit new ones when re‑saving.

1. How can we improve our discovery and workflow parsing?

- Add BFS distance sorting from the save node to prioritize samplers/clip encoders near the output in multi‑branch graphs.
- Add heuristic sampler discovery: any node with fields like steps + cfg qualifies as a candidate sampler if type is unknown.
- Parse inline LoRA tags in prompts to complement loader‑node discovery.
- Move hardcoded field mapping toward a small internal “rule” layer so we can add validators/formatters per node type without touching traversal logic.

1. How does getting the hash of the models help us?

- Stable identity even when filenames change; improves provenance, deduplication, caching, and reproducibility.
- Makes shares/uploads compatible with sites that key on model hash (e.g., Civitai derives identity from SHA).
- Lets us detect mismatches (file changed since last run) and surface “hash changed since last render” warnings.
- With sidecar caching (.sha256), hash lookup is instant on subsequent runs while still auto‑invalidating when the file mtime changes.

1. If a LoRA is called out in text like <lora:name:strength>, is it really used?

- Not by core ComfyUI automatically. Inline tags only have an effect when a node/extension parses them and applies a LoRA (e.g., Prompt Control, LoRA Manager, Impact Pack variants). If no such node is wired, the tag is inert for generation.
- For metadata, we should record both: LoRAs loaded by loader nodes and LoRAs mentioned inline in prompts. When both exist, we reconcile/deduplicate by name, and prefer actual loader strengths when available.

1. What are other ways we can improve our metadata saving functions?

- A1111 compatibility block (flat “parameters” string) in PNG text and JPEG comment for ecosystem compatibility.
- JPEG staged fallback (full → reduced → minimal → comment) to avoid silent metadata loss.
- Sidecar JSON file with extended details when image‑embedded space is insufficient, and a compact pointer in EXIF/parameters to that sidecar.
- Add environment/provenance capture: CUDA, torch/cudnn versions, AAA node version, ComfyUI commit hash.
- Add content hashes for the workflow JSON itself to detect “same pipeline, different params” vs “pipeline changed”.

---

## 🧭 Implementation playbooks (step‑by‑step)

### A. Hash caching (.sha256 sidecars)

- Files:
    - `eric_metadata/utils/hash_utils.py`: add `hash_file_sha256`(path, use_cache=True)
    - `workflow_metadata_processor.py`: route all hash lookups through the cached variant
- Steps:
    1. If path.sha256 exists and mtime(cache) ≥ mtime(file), read and validate 64‑hex digest; return if valid.
    2. Stream file in 8–16KB chunks; compute SHA‑256; write cache (best‑effort) and return.
    3. Wrap with Optional[str] return; on any error, return None and let caller map to "unknown".
- Edge cases:
    - File missing or moved; permissions errors; partial cache content; very large files on network drives.
    - Use try/except around I/O; never fail the render if hashing fails.
- Performance tips:
    - Keep chunk size modest to balance I/O and CPU; reuse a single hashlib object per file; avoid reading the same file twice in one run.

### B. Inline LoRA tag parsing

- Files:
    - `eric_metadata/utils/workflow_parser.py`: add regex and `_parse_lora_tags`(); merge with loaders.
- Steps:
    1. Compile strict and legacy patterns at class load.
    2. On extraction, after prompts collected, run parser over positive + negative strings.
    3. Reconcile with loader list: if name matches, prefer loader strengths; otherwise record inline strengths.
    4. Deduplicate by normalized name (case‑insensitive, strip extension hints).
- Edge cases:
    - Conflicting strengths between inline and loader; missing strength in legacy tags; non‑ASCII names.
    - Use best‑effort numeric parsing; default clip_strength = model_strength when omitted.

### C. A1111 compatibility mode

- Files:
    - `nodes/eric_metadata_save_image_*.py`: add `a1111_compat_mode` toggle and `_generate_a1111_string`()
- Steps:
    1. Build a two‑line header: positive prompt, then "Negative prompt: ...".
    2. Create a comma‑separated parameters list: Steps, Sampler, CFG scale, Seed, Size WxH, Model, Model hash, VAE, VAE hash, LoRAs.
    3. Attach as PNG text chunk key "parameters", and for JPEG, include in EXIF UserComment or as JPEG COM when falling back.
- Edge cases:
    - Very long prompts; ensure we also keep our namespaced JSON in XMP/PNG.
    - Localized decimal separators; format numbers with dot decimal to match ecosystem expectations.

### D. BFS sampler priority + heuristic discovery

- Files:
    - `workflow_parser.py`: add `_trace_from_node()`, `_find_best_sampler()`; integrate into extraction.
- Steps:
    1. BFS from save node backwards through inputs, keeping (node_id → distance, class_type).
    2. Candidates: known sampler types (exact) and heuristic (presence of steps + cfg fields).
    3. Choose by (distance, priority) with exact match preferred; expose all candidates optionally under ai_info.assets.samplers[].
- Edge cases:
    - Loops/self‑references; multiple “save” nodes; refiner chains where the sampler closest to save might be the refiner—record both base and refiner if present.

### E. JPEG metadata fallback

- Files:
    - `nodes/eric_metadata_save_image_*.py`: implement `_save_as_jpeg`() with staged paths.
- Steps:
    1. Build full EXIF (JSON in XMP + parameters in UserComment); if > threshold, drop workflow JSON (reduced).
    2. If still too big, trim to minimal allow‑list (essentials + all LoRAs compact form).
    3. If still too big, store a compact parameters string in JPEG COM and write a sidecar JSON; include a pointer key (e.g., Sidecar: filename.json) in the comment.
- Edge cases:
    - EXIF library limits; Windows path length in sidecar pointers; non‑ASCII text in EXIF—ensure UTF‑8 encoding where supported.

### F. Internal declarative capture rules (phase 1)

- Files:
    - `eric_metadata/utils/node_capture_rules.py`
    - Replace or bridge existing `parameter_mappings` with rule objects supporting optional validator/formatter.
- Steps:
    1. Define MetadataField enum and CaptureRule dataclass.
    2. Migrate 3–5 key nodes first (KSampler, LoraLoader, CheckpointLoader, VAELoader) to validate approach.
    3. Add simple validators (e.g., is_positive_prompt) and formatters (e.g., calc_model_hash via hash utils).
    4. Keep public API stable; only the internal mapping changes.
- Edge cases:
    - Conflicting rules for the same field; define merge precedence (built‑ins over user rules once phase 2 exists).

---

## 🧱 Metadata schema evolution plan

- Versioning: add ai_info.schema_version (integer) and metadata.writer_version (semantic).
- Namespaces and keys (additions):
    - ai_info.assets.models[]: name, path, hash:{algo→hex}, size_bytes, sha_cached.
    - ai_info.assets.loras[]: name, strength_model, strength_clip, source:{loader|inline}.
    - provenance: comfyui_commit, aaa_metadata_version, execution_time, batch_index.
- Backwards compatibility: when reading old images, populate new keys where inferable; when writing, preserve legacy keys for one release unless opt‑out flag set.
- Migration: provide a tiny CLI/script to batch‑re‑write existing PNG/JPEG to the latest schema while preserving originals.

Example diff (conceptual):

```diff
- ai_info.generation.model_hash: abcd…
+ ai_info.assets.models[0].hash.sha256: abcd…
+ ai_info.assets.models[0].name: SDXL_1_0
```

---

## ✅ Test strategy and coverage

- Unit tests
    - Hash caching: cache hit/miss, invalid cache, mtime change invalidation, permission errors (graceful fallback).
    - LoRA parsing: strict/legacy tags, unicode names, duplicate names, conflict resolution.
    - A1111 generator: formatting, numeric precision, long prompt handling.
    - BFS: candidate ranking by distance; cycle safety; heuristic fallback.
- Integration tests
    - Full workflow fixtures: base sampler + refiner; Prompt Control with inline LoRA; loader‑only LoRA; JPEG save with each fallback level.
    - Verify embedded metadata round‑trip (PNG text, XMP, JPEG EXIF/COM) and sidecar creation.
- Performance tests
    - Hashing 2–8GB mock files (sparse files) to verify cache accelerates subsequent runs by >1000×.
    - Parser traversal time on large graphs (>500 nodes) remains under a target threshold.

---

## 🛡️ Risk and mitigation deep dive

- Execution hooks
    - Likelihood: medium; Impact: medium→high when conflicts occur.
        - Mitigation: opt‑in, conflict detection, minimal work in hook, per‑prompt context isolation, automatic fallback.
- JPEG EXIF overflows
    - Likelihood: high on complex workflows; Impact: medium (metadata loss).
        - Mitigation: staged fallback + sidecar; explicit indicator of fallback stage in parameters.
- Hash I/O failures
    - Likelihood: low; Impact: low.
        - Mitigation: best‑effort cache writes; never abort on hash errors; log once per session.
- Schema churn
    - Likelihood: medium as we add features; Impact: medium.
        - Mitigation: explicit schema versioning; writer emits both old+new during transition; migration script.

---

## 📚 Glossary and references

- BFS: Breadth‑First Search graph traversal used to compute node distances from the save node.
- Sidecar: a small file alongside the main asset (e.g., model.safetensors.sha256) storing auxiliary data.
- XMP: Extensible Metadata Platform, an ISO standard for embedding structured metadata in media files.
- A1111 parameters string: The flat, multi‑line textual format popularized by Automatic1111 WebUI.
- LoRA inline tag: Prompt syntax like <lora:name:0.8[:0.6]> parsed by certain nodes/extensions.

References:

- <https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal>
- <https://github.com/nkchocoai/ComfyUI-SaveImageWithMetaData>
- <https://github.com/Light-x02/ComfyUI-Image-Metadata-Nodes>
- <https://github.com/giriss/comfy-image-saver>
