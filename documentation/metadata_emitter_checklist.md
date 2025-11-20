# Metadata Emitter Integration Checklist

Use this checklist when wiring **any** custom node or utility into the AAA Metadata System so emitted data remains consistent and versioned correctly.

## 1. Imports and shared constants
- `from custom_nodes.AAA_Metadata_System import MetadataService`
- `from custom_nodes.AAA_Metadata_System.eric_metadata.utils.version import get_metadata_system_version_label`
- Cache once per module: `METADATA_SYSTEM_GENERATED_BY = get_metadata_system_version_label()`

## 2. Acquire the MetadataService
- Reuse a service passed in by parent nodes when available.
- Otherwise construct one during `__init__` (e.g., `self.metadata_service = MetadataService(debug=self.debug, human_readable_text=True)`).
- Do **not** instantiate a new service inside hot call loops.

## 3. Decide where the emitter sits in the pipeline
Choose the correct section in the metadata payload:
- `ai_info.generation` for sampler/execution details (already defined by save-image nodes).
- `ai_info.analysis` for inspections or classifiers.
- `workflow`/`assist` namespaces only if aligning with established schema; coordinate before introducing new top-level keys.

## 4. Shape and merge the payload
- Start from an empty dict or augment an existing metadata object with `_deep_merge` / `_merge_metadata`.
- Always add a provenance stamp: `payload_section['generated_by'] = METADATA_SYSTEM_GENERATED_BY`.
- Prefer explicit keys (`top_prompt`, `primary_subject`) over ambiguous arrays.
- Clamp numeric values, strip long strings when embedding, and move large blobs to sidecar attachments.

## 5. Select targets before writing
| Use Case | Suggested Targets |
|----------|-------------------|
| Human-readable summary only | `['txt']` |
| Structured data only | `['xmp']` |
| Shareable + structured | `['txt', 'xmp']` |
| PNG/JPEG with small payload | include `'embedded'` |
| Database sync enabled | append `'db'` |

Adjust per node defaults or expose toggles to the user.

## 6. Write the metadata
```python
self.metadata_service.write_metadata(
    resource_path,
    payload,
    targets=targets,
    resource_identifier=resource_uri,  # optional but recommended
)
```
- `resource_path` should point at the primary output file.
- If emitting pre-save (e.g., analysis-only node), use a logical URI and let downstream writers merge later.

## 7. Coordinate with discovery mode
- When `self.metadata_service.discovery_mode` is `True`, collect unknown labels, node types, or schema changes and push them into `metadata_service.discovery_logger`.
- Keep log messages concise; avoid spamming the console.

## 8. Tests & validation
1. Extend or add pytest coverage that exercises the emitter and asserts the expected keys.
2. Run the standard regression suite:
   ```powershell
   A:/Comfy25/ComfyUI_windows_portable/python_embeded/python.exe -m pytest tests/prep/test_module_boundaries.py
   ```
3. Manually inspect an emitted TXT/XMP file to confirm `generated_by` matches `version.txt`.
4. (If applicable) open the discovery report to ensure new fields appear under the correct namespace.

## 9. Documentation & change log
- Summarize the emitter addition in `documentation/edit_log.md` with test command.
- Update any relevant schema docs so downstream consumers know about new keys or namespaces.

Following this checklist keeps every metadata emitter aligned with the shared version helper and prevents accidental divergence between nodes.
