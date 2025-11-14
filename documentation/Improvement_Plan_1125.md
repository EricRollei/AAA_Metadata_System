Plan: Metadata System Enhancement with Safe Hook Integration
This plan focuses on safely collecting more workflow information through backend hooks, improving data structure, and adding ecosystem compatibility—all while maintaining our fault-tolerant "never block save" philosophy.

Steps
Implement safe execution hook layer with conflict detection, per-prompt isolation, and auto-disable on errors. Create eric_metadata/hooks/runtime_capture.py that wraps ComfyUI's PromptExecutor.pre_execute and pre_get_input_data, storing lightweight session data keyed by prompt_id. Add env var toggle (AAA_METADATA_ENABLE_HOOKS) defaulting to off.

Extend metadata schema with runtime section under ai_info.runtime for hook-captured values (resolved inputs, execution order, timestamps). Update merge logic in save node to prefer runtime data when available, mark with provenance.capture_mode = "parser+hooks", and add sidecar pointer field for overflow handling.

Add intelligent backward traversal using BFS from save node to discover prompts/parameters in any connected text nodes (not just CLIPTextEncode). Prioritize by distance and implement heuristic sampler detection (nodes with steps + cfg fields) for unknown types following xxmjskxx patterns.

Implement inline LoRA/embedding parser with regex patterns (<lora:name:strength>, <embedding:name>) scanning all prompt text. Merge with loader-discovered assets, reconcile conflicts (prefer loader strengths), and add source: "inline" flag in metadata to track origin.

Create A1111/Civitai compatibility emitters that generate flat parameter strings from our namespaced JSON. Add optional toggle to embed A1111 "parameters" text chunk in PNG and Civitai sidecar JSON with asset hashes. Keep as derived data—never canonical source.

Enhance XMP/Photoshop compatibility by auditing current aaa: namespace mappings, ensuring all critical fields write to both embedded XMP and our canonical JSON, and implementing JPEG staged fallback (full → reduced → minimal → COM+sidecar) with size monitoring.

Further Considerations
Hook testing strategy? Should we create a ComfyUI execution simulator for integration tests, or rely on manual workflows with common node combinations (conditional samplers, switch nodes, queued prompts)?

Schema migration path? When we add ai_info.runtime, should we version the schema (schema_version: 2) and provide a migration script for existing images, or just start writing the new fields alongside old ones?

Performance monitoring? Add telemetry for hook execution time and metadata collection duration with debug flag to surface bottlenecks, or keep it lightweight and only log errors?

Photoshop visibility specifics? Which fields are Adobe apps currently not seeing—is it custom aaa: namespace fields, or standard XMP mappings that need adjustment?

Plan: Metadata System Enhancement with Safe Hook Integration
This plan focuses on safely collecting more workflow information through backend hooks, improving data structure, and adding ecosystem compatibility—all while maintaining our fault-tolerant "never block save" philosophy.

Implementation Phases
Phase 1: Foundation Improvements (Weeks 1-2)

Hash Caching System - Implement .sha256 sidecar files for model hashes. Create hash_utils.py with hash_file_sha256() function that checks cache mtime, reads/validates cached hash, or computes and writes new cache. Update workflow_metadata_processor.py to use cached hashing. Test with permission errors and mtime changes. (2-3 hours, HIGH priority, LOW risk)

Inline LoRA/Embedding Parser - Add regex patterns to WorkflowParser: <lora:name:strength_model:strength_clip> and <embedding:name>. Scan all prompt text (positive + negative), merge with loader-discovered LoRAs, deduplicate by name preferring loader strengths, mark each with source: "loader" or "inline". (4-6 hours, HIGH priority, LOW risk)

A1111 Compatibility Mode - Create _generate_a1111_string() in save node that formats: Line 1 = positive prompt, Line 2 = Negative prompt: ..., Line 3+ = comma-separated Steps: X, Sampler: Y, CFG scale: Z, Seed: N, Size: WxH, Model: name, Model hash: XXXX, LoRA: name (sm, sc), AAA_Metadata vX.Y.Z. Add toggle parameter a1111_compat_mode to node, embed in PNG text chunk "parameters" and JPEG comment. (6-8 hours, HIGH priority, LOW risk)

Phase 2: Discovery & Traversal (Weeks 3-4)

BFS Distance-Based Prioritization - Implement _trace_from_node() in WorkflowParser using breadth-first search backward from save node, returning {node_id: (distance, class_type)}. Create _find_best_sampler() that ranks candidates by distance and priority (known samplers = 0, heuristic matches with steps+cfg = 1). Handle multi-sampler workflows by selecting closest. (8-12 hours, MEDIUM priority, MEDIUM risk)

Backward Text Node Traversal - Add _find_connected_text_nodes() that traverses backward from sampler up to max_depth=5, identifies any node with text/prompt/string fields containing >10 chars, returns list sorted by distance. Prioritizes closest text source regardless of node type. (4-6 hours, MEDIUM priority, LOW risk)

Phase 3: Storage & Compatibility (Weeks 5-6)

JPEG Staged Fallback - Implement 4-stage fallback in _save_as_jpeg(): Full (all metadata) → Reduced (drop workflow JSON) → Minimal (essential fields only) → Sidecar (minimal EXIF + pointer to .json sidecar). Monitor EXIF size against 60KB threshold, create _trim_to_essential() keeping only prompts, model, seed, steps, sampler, size, LoRAs. Record fallback stage in provenance.jpeg_fallback_stage. (8-12 hours, MEDIUM priority, LOW risk)

XMP/Photoshop Compatibility Audit - Review xmp.py and embedded.py handlers, verify standard namespace mappings (dc:, xmp:, photoshop:, xmpRights:), test custom aaa: namespace fields in Photoshop/Bridge, fix language-alternative structures, ensure creator/copyright/keywords visible in File Info panel. (4-6 hours, HIGH priority, LOW risk)

Phase 4: Safe Runtime Hooks (Weeks 7-8, OPTIONAL)

Hook Infrastructure - Create eric_metadata/hooks/runtime_capture.py with conflict detection, per-prompt session registry, auto-disable on error. Wrap PromptExecutor.pre_execute and pre_get_input_data, store lightweight data keyed by prompt_id. Add env var AAA_METADATA_ENABLE_HOOKS (default False), extend schema with ai_info.runtime section, merge hook data preferring runtime values, mark with provenance.capture_mode = "parser+hooks". See runtime_hook_implementation_plan.md for full design. (24-40 hours, LOW priority, HIGH risk - implement only if runtime values prove critical)
Further Considerations
Hash format preference? Use 8-char short hash in A1111 string, keep full 64-char in canonical JSON for Civitai compatibility.

Schema migration path? Bump schema_version: 2 when adding ai_info.runtime section, provide migration script to upgrade existing images, write both old and new fields during transition period.

Performance monitoring? Add debug flag to log hook execution time and metadata collection duration, surface bottlenecks without impacting normal operation.

Photoshop visibility gaps? Test current XMP implementation in Photoshop/Bridge/Lightroom, document which fields from aaa: namespace are visible vs. need standard namespace mappings, prioritize fixes for creator/copyright/keywords.

Would you like me to expand any section or shall we begin implementing Phase 1?