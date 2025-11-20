# JPEG Metadata Touchpoints (2025-11-15)

This note captures the current write-paths for JPEG exports in `nodes/eric_metadata_save_image_v099d.py` so the staged fallback work can begin with a clear map of where metadata is injected.

## Primary save call (`save_with_metadata`)
- After the JPEG image is written, metadata embedding is triggered inside the `enable_metadata` check by calling `self.metadata_service.write_metadata(image_path, metadata, targets=targets_to_use)` around line 2535.
- No payload size guard is applied before handing control to `MetadataService`. Large metadata structures are written verbatim, so the new fallback should hook in before this call.

## Additional format helper (`_save_additional_format`)
- JPEG copies created via the "additional format" option write metadata in two places:
  - A direct `pil_image.save(... format='JPEG' ...)` call that omits size monitoring.
  - A subsequent `self.metadata_service.write_metadata(additional_path, metadata, targets=targets)` call when `additional_format.lower() not in ['svg']`.
- Similar to the primary path, there is no guardrail around metadata size prior to embedding.

## Advanced alpha save (`_save_with_advanced_alpha`)
- When the main run requests JPEG output with alpha handling, the function eventually saves the composited RGB image via `processed_image.save(image_path, format=format, **save_options)` (with `format` resolved to `'JPEG'`). The same `write_metadata` invocation in the parent method handles metadata afterwards, still without a byte-limit check.

## Action Items
1. Introduce a pre-embed inspector that estimates the combined XMP/IPTC payload size and decides which fallback tier to use before calling `write_metadata`.
2. Plumb the chosen fallback stage back into the provenance block (e.g. `provenance.jpeg_fallback_stage`) so downstream tooling can report what happened.
3. Ensure the additional-format path reuses the same guard logic to avoid silent divergence between primary and secondary JPEGs.
