# Runtime Hook Implementation Plan

## Overview

We will introduce an optional execution-hook capture layer inspired by
[`ComfyUI_SaveImageWithMetaDataUniversal`](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal)
to gather runtime-resolved parameters that our static `WorkflowParser` cannot
always see. The hook facility must remain opt-in, conflict-aware, and safe to
use alongside other custom node packs.

## Objectives

- Collect additional runtime data (resolved sampler settings, dynamic inputs,
  execution order, timestamps) without destabilising ComfyUI.
- Merge hook-captured values into our canonical metadata structure while
  preserving schema integrity.
- Ensure all additional data can be embedded in images (PNG/JPEG/WEBP), XMP
  sidecars, and optional JSON sidecars.
- Provide clear toggles, logging, and documentation so users understand the
  trade-offs of enabling hooks.

## Out of Scope (for now)

- Replacing the current parser-based discovery (parser stays as baseline).
- Enabling hooks by default. The feature ships disabled and advertised as
  advanced.
- Building user-editable declarative capture rules; that refactor remains a
  separate initiative.

## Safety Principles

1. **Opt-in only**: require explicit configuration (environment variable, node
   checkbox, or settings JSON) before patching ComfyUI internals.
2. **Minimal work inside hooks**: hooks collect references and lightweight
   values only; heavy processing happens after the run finishes.
3. **Scope isolation**: maintain state keyed by `prompt_id` so queued/batched
   runs cannot bleed data across sessions.
4. **Conflict detection**: if another extension has already wrapped the target
   dispatcher methods, log a warning and skip hook registration.
5. **Fail-safe design**: any exception inside hook code is caught, logged once,
   and auto-disables the hook for the remainder of the session.
6. **Graceful teardown**: provide a function to unhook and restore the original
   dispatcher when ComfyUI shuts down or the feature is disabled.

## Hook Strategy

### Targeted Dispatcher Patches

- Mirror the hook points used upstream: `PromptExecutor.pre_execute` and
  `PromptExecutor.pre_get_input_data` (confirm the exact import paths on the
  current ComfyUI version).
- Create a module `eric_metadata/hooks/runtime_capture.py` that exports
  `enable_hooks()` and `disable_hooks()` helpers.
- Store original functions in module-level variables so they can be restored
  later.

### Session Context Management

- Introduce a `HookSession` dataclass containing:
  - `prompt_id`
  - `prompt_json`
  - `start_ts`
  - `executed_nodes` (ordered list of `(node_id, class_type, ts)`)
  - `resolved_inputs` (map of node_id to resolved parameter values)
- Maintain an in-memory registry `{prompt_id: HookSession}` inside the hook
  module. Remove entries once the save node finalises metadata for that
  prompt.
- When the hook sees `SaveImageWithMetadata` class IDs, mark the active save
  node so the post-save integration knows which session to consume.

### Enabling and Disabling

- Activation flow:
  1. On node initialise (or top-level package `__init__`), read configuration
     (env var `AAA_METADATA_ENABLE_HOOKS`, config file, or ComfyUI settings).
  2. If enabled, call `enable_hooks()`; otherwise keep parser-only mode.
  3. Emit a debug log summarising whether hooks are active and if conflicts were
     detected.
- Deactivation flow: provide `disable_hooks()` that restores the dispatcher and
  clears state.

## Data Capture and Merge

### Data Collected via Hooks

- Full prompt JSON as resolved at execution time (guaranteed to match the run).
- Execution order of nodes leading up to the save node.
- Runtime input values (e.g., sampler steps after conditional logic, actual
  checkpoint file chosen by switch nodes, live LoRA strengths).
- Optional timings (start/finish timestamps per node) for provenance.

### Integration with Canonical Metadata

- Extend our metadata schema with a `runtime` section under `ai_info`, for
  example, `ai_info.runtime.sampler.steps_resolved`,
  `ai_info.runtime.nodes_executed[]`, `ai_info.runtime.inputs.<node_id>`.
- During save:
  1. Run the existing `WorkflowParser` to populate canonical fields.
  2. Query the `HookSession` for the current `prompt_id`.
  3. Merge the hook data, favouring hook values when both sources exist (they
     represent runtime truth). Keep parser output as fallback for missing items.
  4. Record a provenance flag `provenance.capture_mode = "parser+hooks"` (or
     similar) so downstream tooling can detect that runtime data was available.
  5. If runtime payloads exceed our safe inline size budget, emit a compact
     pointer (e.g., `ai_info.runtime.sidecar_ref`) to a JSON sidecar that holds
     the full structure. Include the same pointer inside the PNG/JPEG metadata
     for discoverability.

### Storage and Serialization Updates

- **Canonical JSON (PNG/sidecar)**: add the `ai_info.runtime` block and ensure
  it serialises alongside existing fields. Compress large payloads when
  embedding in PNG iTXt chunks.
- **XMP mapping**: surface key runtime parameters (sampler, steps, cfg, seed,
  checkpoint name/hash) using the existing `aaa:` namespace. Keep heavyweight
  arrays (execution trace, resolved inputs) in the canonical JSON only.
- **JPEG fallback**: when EXIF size limits are hit, include the runtime pointer
  in the minimal metadata payload and drop the heavy structures into the
  sidecar.

## Implementation Phases

### Phase 0 – Discovery and Design (1–2 days)

1. Confirm current ComfyUI dispatcher signatures and the exact hook points used
   by `ComfyUI_SaveImageWithMetaDataUniversal`.
2. Document any differences between their fork and upstream ComfyUI that we
   must account for (parameter names, execution context objects, etc.).
3. Finalise schema extensions (`ai_info.runtime`, provenance flag, sidecar
   pointer field names).

### Phase 1 – Hook Infrastructure (2–3 days)

1. Implement `runtime_capture.py` with enable/disable helpers, conflict
   detection, and per-prompt session registry.
2. Add configuration surface (env var + node UI toggle) and debug logging.
3. Write unit tests covering:
   - Hook registration/unregistration restores originals.
   - Conflict detection triggers when dispatcher already patched.
   - Session lifecycle (create on pre_execute, cleanup on teardown).

### Phase 2 – Data Merge and Serialization (2–4 days)

1. Update the save node pipeline to request hook data, merge into canonical
   metadata, and set provenance flags.
2. Extend serializers (PNG, XMP, JPEG fallback) to embed runtime values and
   pointer references.
3. Update documentation of metadata schema and add examples demonstrating the
   new fields in embedded JSON/XMP.

### Phase 3 – Validation and Hardening (1–3 days)

1. Run manual workflows covering:
   - Standard linear graph (baseline comparison).
   - Conditional sampler selection / switch nodes.
   - Queue of multiple prompts to validate isolation.
2. Measure performance impact with hooks enabled vs disabled.
3. Add integration tests ensuring parser-only mode still works when hooks are
   disabled.

## Validation and Testing Strategy

- **Unit tests**: hook enable/disable, conflict detection, session registry,
  merge logic (`runtime` block assembled correctly when both parser and hook
  provide data).
- **Integration tests**: simulated ComfyUI execution harness that invokes the
  hook functions around a stubbed save node to verify captured values end up in
  the saved metadata structure.
- **Regression suite**: re-run existing metadata writer tests to make sure
  nothing regresses when hooks are off.
- **Manual QA**: inspect saved PNG/JPEG/XMP files with external tools to
  confirm new fields are present and correctly mapped.

## Risks and Mitigations

- **Hook conflicts with other packs**: detect patched dispatcher signatures,
  warn user, auto-disable our hooks.
- **Runtime exceptions inside hooks**: wrap hook bodies in try/except, log a
  concise error (once per session), disable hooks for safety.
- **Performance overhead**: keep hook-side work minimal and defer heavy tasks
  to post-save. Provide a debug metric in logs for hook execution time.
- **Schema bloat**: document new fields, cap inline payload size, and favour
  sidecars for verbose data.
- **User surprise**: update README/CHANGELOG, highlight that hooks are optional
  and how to enable them.

## Open Questions

1. Should we expose a per-run toggle in the save node UI (e.g., "Prefer runtime
   capture if available") in addition to global config?
2. What is the maximum acceptable size for the embedded `ai_info.runtime`
   section before we force a sidecar (e.g., 32 KB)?
3. Do we want to log sampler/controlnet resolution differences when parser and
   hook disagree, to aid debugging?
4. How should we present hook status to users in the UI (icon, text label,
   metadata note)?

---

**Next step suggestion**: review these open questions, decide on schema field
names (`capture_mode`, `runtime.sidecar_ref`, etc.), and then green-light Phase
1 implementation.