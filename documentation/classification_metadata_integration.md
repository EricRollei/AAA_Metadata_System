# Image Classification Metadata Integration Guide

This guide explains how custom classification nodes can send their analysis results into the Metadata System so everything is captured alongside saved outputs.

## When to use this guide

Use these steps for any node that:
- Analyzes an image (classification, tagging, detection, etc.).
- Produces structured information that should persist in XMP, TXT, or database sidecars.
- Already runs inside the AAA Metadata System environment (custom node folder) and can rely on its utilities.

## Implementation checklist

1. **Import the helpers**
   ```python
   from custom_nodes.AAA_Metadata_System import MetadataService
   from custom_nodes.AAA_Metadata_System.eric_metadata.utils.version import get_metadata_system_version_label
   ```

2. **Cache the version label once per module**
   ```python
   METADATA_SYSTEM_GENERATED_BY = get_metadata_system_version_label()
   ```
   *Do this at module scope; the helper caches `version.txt` so other consumers stay in sync.*

3. **Instantiate (or receive) a `MetadataService`**
   - Reuse the service from parent nodes when it is already provided.
   - Otherwise create one with `metadata_service = MetadataService(debug=self.debug)` and keep it around; avoid recreating it per call.

4. **Build a metadata payload**
   Follow the existing structure used by save-image nodes:
   ```python
   classification_metadata = {
       "ai_info": {
           "analysis": {
               "generated_by": METADATA_SYSTEM_GENERATED_BY,
               "classifier": node_name,
               "version": classifier_version,
               "source_image": image_identifier,
               "labels": labels,               # list of {name, confidence}
               "top_label": labels[0] if labels else None,
           }
       }
   }
   ```
   Key points:
   - Keep new data under `ai_info.analysis` (or a more specific namespace) to avoid colliding with generation metadata.
   - Add short summaries (`top_label`, counts, scores) so humans can read the TXT sidecar easily.
   - Include provenance (`generated_by`, classifier name/version, run timestamp).

5. **Optionally attach raw model outputs**
   - Place longer arrays or heatmaps under `analysis["details"]` or `analysis["attachments"]`.
   - Use lightweight structures (lists/dicts) and keep binary data out of the metadata; store large artifacts as separate files.

6. **Merge with existing metadata**
   If the node already receives a metadata dict, use `_deep_merge` or similar logic so you do not overwrite user-provided fields. Example:
   ```python
   merged = metadata_service._merge_metadata(existing_metadata, classification_metadata)
   ```

7. **Select storage targets**
   Decide where to persist your payload:
   - XMP sidecar: `targets=["xmp"]`
   - TXT summary: `targets=["txt"]`
   - Both: `targets=["xmp", "txt"]`
   - Embedded metadata (PNG/JPEG) should only be used if the file format supports it and the data volume is small.

8. **Write the metadata**
   ```python
   metadata_service.write_metadata(
       image_path,
       classification_metadata,
       targets=["xmp", "txt"],
       resource_identifier=image_path,  # or a logical URI
   )
   ```
   - Supply the absolute path (or URI) for the image being annotated.
   - When working on batches, call `write_metadata` for each output or create a shared resource identifier before looping.

9. **Respect discovery/logging hooks**
   - When discovery mode is enabled (`metadata_service.discovery_mode`), capture any unfamiliar classifier names or label schemas so the central logs stay current.

## Best practices

- **Keep structures flat where possible.** Deeply nested dictionaries make sidecar TXT files hard to read.
- **Avoid mutable global state.** Store node-specific context on `self` in the node class.
- **Validate numeric ranges.** Clamp confidence values to `[0, 1]` (or `[0, 100]`) before writing them.
- **Fallback gracefully.** If the node cannot fetch metadata service, log a warning and still return image outputs.
- **Document new keys.** Update the metadata schema docs and add a regression test that asserts the new keys appear when the node runs.

## Example integration snippet

```python
class MetadataAwareClassifier:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.metadata_service = MetadataService(debug=debug)
        self.generated_by = get_metadata_system_version_label()

    def classify_and_store(self, image_path: str, image_tensor):
        labels = self._run_classifier(image_tensor)
        metadata = {
            "ai_info": {
                "analysis": {
                    "generated_by": self.generated_by,
                    "classifier": "ExampleClassifier",
                    "version": "1.2.0",
                    "labels": labels,
                    "top_label": labels[0] if labels else None,
                }
            }
        }
        self.metadata_service.write_metadata(
            image_path,
            metadata,
            targets=["xmp", "txt"],
        )
        return labels
```

## Testing and validation

1. Run the targeted regression suite:
   ```powershell
   A:/Comfy25/ComfyUI_windows_portable/python_embeded/python.exe -m pytest tests/prep/test_module_boundaries.py
   ```
2. Load an output image in an XMP viewer to confirm the `ai_info.analysis` block exists.
3. Open the generated TXT sidecar and verify the classifier summary is human-readable.
4. (Optional) Query the metadata database if the DB handler is enabled to ensure records are inserted as expected.

Following this checklist keeps every classification node aligned with the core Metadata System and ensures downstream consumers (UI, discovery reports, external integrations) see consistent `generated_by` and provenance fields.
