# eric_compose - Pose-Aware Aesthetic Image Cropping

A subpackage of `AAA_Metadata_System` for cropping photos based on body-part presets and aesthetic scorers. Designed to run as ComfyUI nodes (and eventually as a CLI), sharing one orchestrator.

**Status:** v0.2 - composition-scorer pipeline complete and exposed as a single ComfyUI node. Ready for testing on real photos.

**Author:** Eric Hiss (GitHub: EricRollei)
**License:** Dual License (Non-Commercial and Commercial Use), matches parent `AAA_Metadata_System` package.

---

## What it does

Given an image and (optionally) DWPose keypoints, propose a high-quality crop. Two complementary use cases:

1. **Aesthetic recomposition** - "this is already a clean photo of a person but it'd be better as a head-and-shoulders portrait." Different from the existing `SmartImageCropper` (which extracts embedded photos from scans) and `Florence2ImageCropper` (which extracts language-described regions).

2. **Training-data preparation** - produce body-part-specific crops with the head excluded, for clothing-style / outfit / shoe / pants training where the model should not learn the subject's identity.

Optional `exclude_mask` input lets the user mark regions the crop must avoid - text overlays, watermarks, logos, distracting backgrounds. Mask can come from any source (Florence-2, EasyOCR, manual paint, etc.).

---

## Status & roadmap

### Implemented (v0.2)

- `types.py` - KP, ARSpec, Candidate, ScoreReport, Scorer protocol
- `subjects.py` - POSE_KEYPOINT parsing, Subject body measurements
- `presets.py` - 10 body presets (head_only through legs_only) with documented coefficients
- `selector.py` - geometry, AR conforming, NMS, candidate finalization, **face_excluded + mask_excluded validators**
- `candidates/pose_anchored.py` - variation table over presets and ARs
- `candidates/grid.py` - GAIC-style anchor grid (no pose required)
- `scorers/composition.py` - rule-of-thirds + headroom + lead-room + edge-cut sanity
- `scorers/composite.py` - weighted multi-scorer combiner with min-max normalization
- `pipeline.py` - end-to-end orchestrator with optional exclude_mask filter
- `nodes/eric_compose_crop.py` - "Eric Compose Crop" ComfyUI node

### Architecture changes from the original plan

The original plan called for three nodes (Loader, Crop, Candidates, Pick) and two deep aesthetic scorers (GAIC, CACNet). The shipped v1 has one node and the composition scorer only. Reasons for the simplification:

- **GAIC / CACNet require compiled CUDA C++ extensions** for RoIAlign and RoDAlign. On Windows portable Python and Blackwell (sm_120) this is a build-from-source nightmare for a feature whose role was always "pre-rank candidates before external rerank."
- **External aesthetic rerank already exists** as Eric's UniPercept Scorer (IAA / IQA / ISTA integer outputs). Internal deep aesthetic scoring duplicates capability rather than complementing.
- **Loader node has nothing to load** when composition scorer is the sole scorer (pure Python, no model). Will earn its keep when CLIP-aesthetic or similar lands.
- **Candidates / Pick nodes need empirical knowledge** of how UniPercept's node handles ComfyUI batches before being designed correctly. Better to ship the basic crop, test, then design the rerank surface against measured behavior.

### Planned (v1.5, after real-photo testing)

- `nodes/eric_compose_crop_candidates.py` - top-K crop output for external rerank pipelines
- `nodes/eric_compose_crop_pick.py` - selects best crop given external scores (UniPercept or otherwise)
- `scorers/clip_aesthetic.py` - CLIP-based aesthetic scorer (LAION predictor or similar). MIT-friendly weights, no custom CUDA.
- Soft-penalty mode for `exclude_mask` (current implementation is hard-rejection only)

### Deferred (v2 or beyond)

- CLI entry point (need to know first whether ComfyUI v1 produces good enough crops)
- `candidates/saliency_anchored.py` - saliency-based anchor for non-person images (currently grid-only fallback for non-pose case)
- `scorers/region_quality.py` - per-region IQA (the "bad lighting → tighter crop" use case from initial discussion)
- GAIC / CACNet via pure-PyTorch RoDAlign reimplementation - only worth the effort if composition + UniPercept proves insufficient AND CLIP-aesthetic doesn't fill the gap

### Investigated and not pursued

- **Human-Centric-Image-Cropping** (bcmi, ECCV 2022). Same lab and same era as GAIC PyTorch port; same custom CUDA op problem expected. The unique capability it would add - learned partition-aware features and direction-conditional content preservation - is interesting but the rule-based `lead_room` variation in `pose_anchored.py` plus `Subject.facing()` already encodes the most useful version of that signal. Revisit only if real-photo testing shows our handling of asymmetric framing is consistently weak.

---

## Architecture

### Pipeline flow

1. **Inputs:** image, optional `POSE_KEYPOINT`, AR spec, body preset, optional exclude_mask
2. **Subject extraction** (`subjects.py`): parse pose keypoints → list of `Subject` instances → select primary
3. **Candidate generation** (`candidates/`):
    - If pose present and preset is `auto`: pose-anchored variations + grid
    - If pose present and specific preset: pose-anchored variations only (+ grid if enabled)
    - If no pose: grid only (saliency-anchored deferred)
4. **Constraint filter** (in `finalize_candidate` and `pipeline.py`):
    - AR conform, image-bounds clip, size sanity, must_include preservation
    - Face-exclusion check for face-exclude presets (in candidate generator)
    - **exclude_mask filter** (in pipeline orchestrator, applies to all candidates)
5. **Scoring** (`scorers/`): composite scorer ranks candidates, normalizes per scorer
6. **Selection** (`selector.topk_after_nms`): NMS dedup, top-K by final score
7. **Output:** single best (`Eric Compose Crop` node)

### Module graph (current)

```
types ─┬─ subjects ─┬─ presets ─┬─ candidates/pose_anchored ─┐
       │            │           │                            │
       ├─ selector ─┴───────────┴─ candidates/grid ──────────┤
       │                                                      ├──► pipeline ──► nodes/eric_compose_crop
       └─ scorers/base ─┬─ scorers/composition ───────────────┤
                        └─ scorers/composite ─────────────────┘
```

Strict dependency direction - `types` is leaf, `nodes/*` is root. No circular imports.

---

## Design decisions and notes

### General

- **`PRESETS` is a module-level dict, not a class hierarchy.** The 10 body presets are declarative data with one-shot anchor functions; OO ceremony would add no value.

- **String literals for body presets, not Enum.** Strings pass cleanly through ComfyUI dropdown serialization; Enum values would need conversion at every boundary.

- **`ARMode` IS an Enum** - different surface, no ComfyUI dropdown serialization, lives entirely in the orchestrator.

- **All numeric coefficients are documented inline** with what each represents and the photographic / anthropometric reasoning. Single source of truth for tuning is `presets.py` for body geometry and `scorers/composition.py` for composition weights. No magic constants scattered.

- **Import-time assertions catch declaration drift.** `presets.py` asserts that the `face_policy` column matches `types.FACE_EXCLUDE_PRESETS`; `scorers/composition.py` asserts the four sub-score weights sum to 1.0. Both fail loud on import - preferred over silent inconsistency.

### types.py

- **`Candidate` carries provenance** in `source` (e.g. `pose:half_body:tight_thirds:ar0.800`, `grid:5x5:3x3:a2_1`). For debugging and logging only - the scorer / selector never branch on `source`.

- **`Candidate.must_include`** is the original tight anchor. After AR-conform and clipping, the final box must still contain the must_include - `selector.finalize_candidate` enforces this. Without it, AR-conforming a head_only crop to a tall AR could push the head out of frame.

- **`ScoreReport` carries both `by_scorer` (raw) and `normalized`** so post-hoc analysis can use either. Min-max normalization is per-batch and thus not comparable across runs; absolute scores from `by_scorer` are.

### subjects.py

- **`head_height = 4.5 × inter_eye_distance`** - anthropometric average. Falls back to `1.6 × |neck.y − nose.y|` when eyes aren't visible. Both produce stable measurements for any reasonable pose; head_height is the reference unit for all preset coefficients downstream.

- **`body_axis_x` = mean of available shoulder/hip x-coords**, not nose. Nose drifts badly in 3/4 views; shoulder/hip midline is stable across face directions.

- **`facing()` heuristic uses ear visibility.** Both ears = frontal, one ear = facing the opposite side, neither + nose = frontal (face seen, ears occluded), neither + no nose = back. Replace with face-landmark-based head pose estimation in a future revision if it matters.

- **`select_primary_subject` picks highest mean keypoint confidence** when multiple people are present. Multi-person handling is acknowledged-experimental - in v1 we crop one person and ignore the others.

### presets.py

- **Each preset declares `required_kps` with `min_kp_conf`.** If any required keypoint is below threshold, `applicable_presets()` silently drops the preset. This is why `auto` mode works gracefully on partial-visibility shots.

- **Face-exclude presets (`outfit_full`, `torso_only`, `legs_only`)** position their anchor below the chin by construction. Final candidates additionally pass through `selector.face_excluded()` as belt-and-suspenders - if AR-conform causes the frame to drift up and re-include a face, that candidate is dropped.

- **`bust` and `head_and_shoulders` look similar** in defaults but `bust` is tighter (0.30 stoh below shoulders vs 0.40, 1.3 sw vs 1.4 sw). Both are kept because at different ARs they produce meaningfully different framings.

### selector.py

- **`finalize_candidate` is the single funnel** through which every box becomes a `Candidate`. Both pose-anchored and grid generators call it. Centralizes AR conform + clipping + size sanity + must_include preservation.

- **`expand_to_ar` never shrinks the box.** Reason: the must_include anchor came in pre-sized for the preset; shrinking could exclude it. If the target AR can't be reached without going outside image bounds, we return None (drop the candidate) rather than violate the constraint.

- **NMS at IoU 0.7.** The candidate generators produce many near-duplicates by design. Without NMS, the top-K would be 5 copies of the same crop ± 4 pixels.

- **`face_excluded` and `mask_excluded` are siblings**, both validators that check candidates against external constraints. Both return True for "passes", False for "reject". `face_excluded` is hard (binary, no threshold); `mask_excluded` is parameterized by an overlap fraction so the user can tune strictness.

### candidates/pose_anchored.py

- **`_VARIATION_TABLE` has 6 rows.** Earlier sketches had 5-8; settled on 6 because rows 7-8 produced near-duplicates after NMS. Single tuning knob for candidate diversity per preset.

- **Variations are applied in order:** padding → vertical offset → horizontal lead-room. Padding first so v_offset and h_lead are scaled to the padded box, not the tight anchor.

- **`generate_pose_candidates` takes `presets_to_try` rather than reading from `subject`.** The pipeline orchestrator decides whether the user picked specific presets or wants `auto`. Keeps the candidate generator dumb and testable.

- **Face-exclusion is enforced inside the generator**, not in a downstream filter. A face-exclude preset that can't satisfy its own contract returns an empty list cleanly.

### candidates/grid.py

- **5×5 grid by default**, with a balanced cell_spans table (square / landscape / portrait). 5×5 is in the sweet spot for typical 800-4000px images.

- **AR prefilter at the cell-span level.** Crops outside ±5% of any target AR are rejected before the slide loop.

- **No image data passed in.** Grid is purely geometric. Scorers do their own image reads from candidate boxes.

### scorers/composition.py

- **Four sub-scores, weights sum to 1.0:** thirds (0.30), headroom (0.25), leadroom (0.20), edgecut (0.25). Documented and balanced for portrait-heavy work.

- **Sub-scores return 0.5 (neutral) when not applicable** rather than 0.0. Headroom returns 0.5 for face-exclude presets and grid candidates; lead-room returns 0.5 for frontal/back/no-pose. A face-exclude crop shouldn't be penalized for not having headroom info.

- **Edge-cut penalizes joints inside the crop with edges close to them.** Joints outside the crop (i.e. cropped out entirely) are not penalized - that's the preset's job, not the scorer's.

- **`set_subject()` is mutable state on the scorer instance.** The pipeline updates it before scoring.

### scorers/composite.py

- **Min-max normalization is per-batch.** Makes scorers with different output ranges comparable. Downside: absolute scores not comparable across runs; for that, use `by_scorer` raw values.

- **All-equal raw scores from a scorer get normalized to 0.5** with a note in `ScoreReport.notes`.

- **NaN/Inf protection.** Any non-finite scorer output gets replaced with 0.0 + noted.

- **`CompositeScorer.score()` returns `list[ScoredCandidate]`** - different return type from individual scorers (`np.ndarray`). Intentional boundary: scorer-internal code is numeric, pipeline-facing code is rich-object.

### pipeline.py

- **Single function `compose_crop`** is the entry point for all callers (node now, CLI later, tests). No ComfyUI imports in this module - keeps it independently testable.

- **Returns `(best, top_k)` tuple** even though v1 nodes only consume the first. The second element is for v1.5's Candidates node and tests; including it now means v1.5 doesn't change the function signature.

- **exclude_mask filter applies between candidate generation and scoring.** Same architectural slot as `face_excluded` (which runs inside the candidate generator) but at pipeline level since it applies to both pose-anchored AND grid candidates.

### nodes/eric_compose_crop.py

- **Auto-discovery via `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`** at module level. Parent `AAA_Metadata_System/__init__.py` walks `nodes/` at startup.

- **Fallback to original image** when `compose_crop` returns None (no valid candidates). Keeps workflows unbroken; the `info` JSON output explains why. If you'd rather it raise, change the `if best is None:` block.

- **AR string parsing tolerant of whitespace and stray separators.** "1:1 , 4:5,9:16" parses the same as "1:1,4:5,9:16". Floats like "1.5" are accepted as a 1500:1000 ratio.

- **Composition sub-weights NOT exposed at node level.** Cluttering the UI with four FLOAT knobs that most users never touch is a poor trade. Tune by editing `scorers/composition.py` directly. May promote to optional inputs in v1.5.

---

## Body presets reference

| Preset | Face | Required keypoints | Use case |
|---|---|---|---|
| `head_only` | include | nose, both eyes | Tight head crop, head fills frame |
| `head_and_shoulders` | include | nose, both shoulders, both hips | Salvage from full-body when lower half is bad |
| `bust` | include | nose, both shoulders, both hips | Classic editorial portrait |
| `half_body` | include | nose, both shoulders, both hips | Editorial / catalog standard |
| `three_quarter` | include | nose, both hips, both knees | Fashion-shot standard |
| `full_body_loose` | include | nose, both hips, both ankles | Full body with breathing room |
| `full_body_tight` | include | nose, both hips, both ankles | Full body, minimal margin |
| `outfit_full` | **exclude** | both shoulders, hips, ankles | Outfit / style training, no identity |
| `torso_only` | **exclude** | both shoulders, both hips | Top / jacket training, no identity |
| `legs_only` | **exclude** | both hips, both ankles | Shoes / pants / skirts training, no identity |

**`auto`** preset (handled at the pipeline level, not in the registry) tries all presets whose required keypoints are visible, then lets the scorer pick.

---

## Composition sub-score reference

All four sub-scores produce a value in `[0, 1]`, where 1.0 is "best" and 0.5 is "neutral / not applicable."

| Sub-score | Weight | What it measures | When neutral (0.5) |
|---|---|---|---|
| Thirds | 0.30 | Distance of subject center to nearest thirds intersection | Never neutral; falls back to brightness center then geometric center |
| Headroom | 0.25 | Empty space above head matches optimum (0.40 head_heights) | Face-exclude preset, grid candidate, no head bbox |
| Lead-room | 0.20 | Ratio of space ahead vs behind in facing direction | Frontal / back / no subject |
| Edge-cut | 0.25 | Distance of joints inside crop from nearest crop edge | No subject, no joints inside crop |

---

## Exclusion regions (text overlays, watermarks, logos)

The `exclude_mask` input on the node lets you mark regions the crop must avoid. Two parameters:

- **`exclude_mask`** (MASK) - non-zero pixels are exclusion regions. None disables the filter.
- **`exclude_overlap_thresh`** (FLOAT in [0, 1]) - max fraction of crop area that may overlap the mask:
    - `0.0` (default, strictest) - any overlap rejects the candidate
    - `0.05` - allow up to 5% overlap (tolerates small edge watermarks)
    - `1.0` - mask ignored entirely (feature off)

### Example workflow (text overlay removal)

```
[Load Image] ──image──┬─> [Eric Compose Crop] ──cropped_image──> [Save]
                      │       ▲
                      │       │ exclude_mask
                      │       │
                      └──────►[Florence-2: "Detect all text" → bbox to mask]
                                                                 ▲
                                                                 │
                                          (or any other text detection / mask source)
```

Any node that outputs a MASK works as the exclusion source - Florence-2 with a text prompt, EasyOCR + bbox-to-mask conversion, manually painted in ComfyUI's mask editor, or an existing mask from another tool.

### Behavior when no candidate passes

If every candidate overlaps the mask above threshold, the node returns the original image with `status: "fallback"` and `reason` mentioning the mask. Check `info` output to confirm mask coverage isn't excessive.

### v1 limitations (deferred to v1.5)

- **Hard rejection only** - candidates above threshold are dropped. No soft-penalty mode where high-overlap-but-otherwise-great crops can still win. If real-photo testing shows the strict mode rejects too many otherwise-good candidates, soft-penalty (overlap as a sub-score in composition scorer) becomes a v1.5 priority.

- **Mask must match image dimensions** - mismatch produces nonsense exclusion. Upstream is expected to feed a mask derived from the same image.

- **Single mask per call** - if you want both "exclude text" AND "exclude watermark" use distinct upstream detectors and OR the masks together with an Image Composite or similar node.

---

## Tuning guide

When you want to change behavior, here's where to look:

| Goal | File | Knob |
|---|---|---|
| Tighter / looser body presets | `presets.py` | `_anchor_*` coefficients (documented inline) |
| More / fewer candidate variations | `candidates/pose_anchored.py` | `_VARIATION_TABLE` |
| More / fewer grid candidates | `candidates/grid.py` | `DEFAULT_GRID_SIZE`, `DEFAULT_CELL_SPANS` |
| Stricter AR matching for grid | `candidates/grid.py` | `DEFAULT_AR_TOLERANCE` |
| Composition sub-score weights | `scorers/composition.py` | `W_THIRDS`, `W_HEADROOM`, `W_LEADROOM`, `W_EDGECUT` |
| Headroom optimum | `scorers/composition.py` | `HEADROOM_OPTIMUM`, `HEADROOM_TOLERANCE` |
| Lead-room target ratio | `scorers/composition.py` | `LEADROOM_OPTIMUM`, `LEADROOM_FALLOFF` |
| Joint cut threshold | `scorers/composition.py` | `EDGECUT_KEYPOINTS`, `EDGECUT_THRESH_FRAC` |
| NMS aggressiveness | `selector.py` | `nms_candidates(iou_thresh=...)` |
| Min/max crop area | `selector.py` | `passes_size_bounds` defaults |
| Exclusion strictness | node input | `exclude_overlap_thresh` |

---

## Testing

### Quick smoke tests

These tests bypass ComfyUI and run the pipeline directly. From any directory:

**Imports + preset registry:**

```
A:\Comfy25\ComfyUI_windows_portable\python_embeded\python.exe -c "import sys; sys.path.insert(0, r'A:\Comfy25\ComfyUI_windows_portable\ComfyUI\custom_nodes\AAA_Metadata_System'); from eric_compose import PRESETS; print(list(PRESETS.keys()))"
```

Expected: 10 preset names.

**Synthetic pose → candidates → composition scoring → best crop:**

Pipeline test with a synthetic full-body subject. Should produce a single best ScoredCandidate plus a top-K list of 10:

```
A:\Comfy25\ComfyUI_windows_portable\python_embeded\python.exe -c "import sys; sys.path.insert(0, r'A:\Comfy25\ComfyUI_windows_portable\ComfyUI\custom_nodes\AAA_Metadata_System'); import numpy as np; from eric_compose.pipeline import compose_crop; kps=[0]*54; kps[0:3]=[400,200,0.9]; kps[3:6]=[400,300,0.9]; kps[6:9]=[350,310,0.9]; kps[15:18]=[450,310,0.9]; kps[24:27]=[370,500,0.9]; kps[33:36]=[430,500,0.9]; kps[30:33]=[365,800,0.9]; kps[39:42]=[435,800,0.9]; kps[42:45]=[420,190,0.9]; kps[45:48]=[380,190,0.9]; kps[48:51]=[430,180,0.9]; kps[51:54]=[370,180,0.9]; pk=[{'people':[{'pose_keypoints_2d':kps}],'canvas_width':800,'canvas_height':1000}]; img=(np.random.rand(1000,800,3)*255).astype(np.uint8); best, top = compose_crop(image=img, pose_keypoint=pk, preset='auto', aspect_ratios=[1.0, 0.8, 9/16]); print(f'best preset: {best.candidate.preset}'); print(f'best score:  {best.report.final:.3f}'); print(f'top-K count: {len(top)}')"
```

**Smoke test with exclude_mask** - same as above but with a mask covering the bottom 10% of the image (simulating a watermark band). Top crop should avoid the masked region:

```
A:\Comfy25\ComfyUI_windows_portable\python_embeded\python.exe -c "import sys; sys.path.insert(0, r'A:\Comfy25\ComfyUI_windows_portable\ComfyUI\custom_nodes\AAA_Metadata_System'); import numpy as np; from eric_compose.pipeline import compose_crop; kps=[0]*54; kps[0:3]=[400,200,0.9]; kps[3:6]=[400,300,0.9]; kps[6:9]=[350,310,0.9]; kps[15:18]=[450,310,0.9]; kps[24:27]=[370,500,0.9]; kps[33:36]=[430,500,0.9]; kps[30:33]=[365,800,0.9]; kps[39:42]=[435,800,0.9]; kps[42:45]=[420,190,0.9]; kps[45:48]=[380,190,0.9]; kps[48:51]=[430,180,0.9]; kps[51:54]=[370,180,0.9]; pk=[{'people':[{'pose_keypoints_2d':kps}],'canvas_width':800,'canvas_height':1000}]; img=(np.random.rand(1000,800,3)*255).astype(np.uint8); mask=np.zeros((1000,800),dtype=np.uint8); mask[900:,:]=1; best, top = compose_crop(image=img, pose_keypoint=pk, preset='auto', aspect_ratios=[1.0,0.8,9/16], exclude_mask=mask, exclude_overlap_thresh=0.0); print(f'best bbox: {best.candidate.to_xyxy()}'); print(f'mask region clear: y2={best.candidate.y2} (must be < 900)')"
```

### Known smoke test artifacts

- **Synthetic subject is centered and frontal-facing.** The composition scorer rewards centered subjects on the thirds-line and gives neutral 0.5 for lead-room. Real photos with off-center / directional subjects will produce different rankings - this is correct behavior, not a bug.

- **Tied scores between same-source candidates with different ARs** mean the AR conform produced effectively-identical framings for those ARs. Common when must_include is small relative to allowed AR range. NMS will dedupe to one survivor.

- **`tight_centered` variations win on synthetic data.** They lose on real photos with off-center subjects to `tight_thirds`, `medium_thirds`, and `lead_room` variations. Don't draw conclusions about scorer behavior from synthetic-test rankings.

---

## Third-party model attribution

**v1 has no third-party model dependencies** - composition scorer is pure Python, no weights downloaded, fully MIT-compatible.

When CLIP-aesthetic lands in v1.5, the LAION aesthetic predictor weights will be downloaded into `ComfyUI/models/aesthetic_crop/`. Those weights are MIT-licensed and won't pin the package to non-commercial.

GAIC and CACNet were considered and not pursued (see "Investigated and not pursued" above) - both their pretrained weights are research-non-commercial-only and require compiled CUDA extensions.

---

## Glossary

- **Subject** - one person extracted from a POSE_KEYPOINT input.
- **Anchor box** - the tight must-include region for a body preset, before variations are applied.
- **Variation** - one specific (padding, vertical offset, lead-room) configuration applied to an anchor box.
- **Candidate** - a finalized crop bbox after AR conform + clipping + validation, ready for scoring.
- **must_include** - anchor box stored on a Candidate; downstream operations must preserve it.
- **face_policy** - per-preset declaration of whether the subject's face must be included in or excluded from the crop.
- **face-exclude preset** - one of `outfit_full`, `torso_only`, `legs_only`. Used for clothing-style training data.
- **exclude_mask** - optional MASK input marking regions the crop must avoid (text, watermarks, logos). Hard filter in v1; soft-penalty in v1.5.
- **exclude_overlap_thresh** - max fraction of crop area allowed to overlap exclude_mask. 0.0 = strictest, 1.0 = mask ignored.

---

## Session log — 2026-05-07

### Bug fixed: `candidates_scored: 1` always showing 1

**Root cause**: The pipeline was returning a 2-tuple `(best, top_k)` but neither node was exposing any diagnostic counts in the `info` JSON. The user had no way to tell whether the pipeline was generating few candidates or NMS was collapsing them.

**Fix**: `pipeline.py` now returns a 3-tuple `(best, top_k, diag)`. `diag` is a dict with:
- `candidates_generated` — after no-crop added, before filters
- `candidates_after_filter` — after mask and area filters
- `candidates_after_nms` — what actually gets scored

Both `eric_compose_crop.py` and `eric_compose_crop_scored.py` unpack the 3-tuple and include all three counts in their `info` JSON output.

**NMS direction note (recorded for future reference):** LOWER IoU threshold = MORE aggressive suppression = FEWER candidates survive. HIGHER = LESS aggressive = more survive. Default of 0.7 is correct as-is. An earlier session accidentally changed this to 0.35 (wrong direction) and it was reverted. Tooltip on the `nms_iou` node input now reads "Higher = more candidates survive NMS" to prevent recurrence.

### Feature added: `offcenter_strength` influences candidate generation

**Prior behavior**: `offcenter_strength` was a scoring bonus only. It added up to `+0.30 × strength` to the final score for candidates where the subject was far from the crop center-line. But all candidates were still generated centered — only pre-existing off-center crops could win.

**New behavior**: When `offcenter_strength > 0`, the candidate generator now synthesizes dedicated left-third and right-third variants for every base variation in `_VARIATION_TABLE`. The horizontal offset magnitude scales linearly: at strength=1.0 the crop frame shifts exactly 1/6 of crop width, placing the subject precisely on a rule-of-thirds vertical line.

**Implementation**:
- `Variation` dataclass gained an `h_offset: float = 0.0` field (unconditional horizontal shift, vs. `h_lead` which is facing-direction-gated)
- `_apply_h_offset()` helper added alongside the existing `_apply_padding`, `_apply_v_offset`, `_apply_h_lead` helpers
- `_build_variation_box()` calls `_apply_h_offset` as its final step
- `generate_pose_candidates()` now accepts `offcenter_strength: float = 0.0`; when > 0 it builds a `variation_set` that is `_VARIATION_TABLE` plus left-third and right-third copies of each base row, then iterates over `variation_set` instead of `_VARIATION_TABLE`
- `pipeline.py` passes `offcenter_strength=offcenter_strength` through to `generate_pose_candidates()`

**Verified by smoke test**: strength=0.0 → 28 candidates generated; strength=0.5 → 70 candidates; `:left_third` and `:right_third` variants appear in top-5 sources at strength=0.5 and can win at strength=1.0.

---

## Future idea: diagonal composition / subject-axis-to-corner framing

### Concept

A classic photographic technique: align the subject's major body axis with the frame diagonal so the body line runs from one corner to the opposite corner. Adds dynamism and visual tension vs. the standard upright framing.

### Two possible implementations

**Option A — AR-matching (no rotation)**
Keep the crop rectangle unrotated. Instead, choose the AR such that `arctan(crop_height / crop_width)` matches the angle of the body axis from vertical. For a body tilted 20° from vertical, a crop of AR ≈ `tan(70°) ≈ 2.75` would make the body diagonal match the frame diagonal. Works without any image resampling.

*Limitations:* Only effective for meaningfully tilted subjects (> ~10°). For near-vertical bodies the required AR becomes extreme (very tall and narrow). Requires a new candidate generation path that reads the body axis angle and derives a target AR from it rather than selecting from a fixed AR set.

**Option B — Rotated crop extraction (affine transform)**
Actually rotate the crop rectangle to align with the body axis, then extract the image patch via an affine / perspective transform. The result is a frame where the body literally runs through two opposite corners.

*Requires:*
- A `rotation_angle` field on `Candidate` (currently all crops assume axis-aligned rects)
- Image extraction changed from simple slicing `image[y1:y2, x1:x2]` to `cv2.warpAffine` at the node output stage
- Handling of black triangular corners — either accept them (with a transparency/pad flag), or clip to the largest inscribed axis-aligned rectangle (loses some of the diagonal effect)
- Keypoint coordinates do NOT transform automatically — scoring would need to rotate keypoints too, or skip pose-based sub-scores for rotated candidates

*Status:* Deferred. Requires a larger refactor of the candidate/extraction layer than the payoff justifies until Option A is validated.

### Body axis definition options (best to worst reliability)

1. `mid_shoulder → mid_hip` — most stable; available whenever any torso preset fires; stable across 3/4 views
2. `mid_hip → mid_ankle` — good for standing full-body; feet are sometimes occluded
3. `nose → mid_hip` — full body including head; nose can be occluded or off-axis in 3/4 view
4. PCA over all confident keypoints — most robust to partial visibility; adds complexity

For v1 of this feature, use option 1 (`mid_shoulder → mid_hip`) as the primary and fall back to option 3 when shoulders aren't available.

### Suggested implementation path

1. Add `body_axis_angle()` method to `Subject` (degrees from vertical, signed: positive = top leans right)
2. **Option A first**: in `generate_pose_candidates`, when `diagonal_strength > 0`, generate a small set of AR-derived candidates where the AR is computed from the body angle. These are scored like any other candidate; the composition scorer will naturally rank them higher when the body does land near the frame diagonal.
3. If Option A proves effective in practice: consider Option B as a premium mode with an explicit `allow_rotated_crop: bool` flag on the node, clearly documented as producing non-axis-aligned output.

### New parameter proposed

`diagonal_strength: float` (0.0–1.0), default 0.0. At 0 this is a no-op (all existing behavior unchanged). At 1.0, the AR-derived diagonal candidates are generated at full weight and compete normally with the standard candidates. The composition scorer would benefit from a new "body-to-diagonal alignment" sub-score to reward these candidates appropriately.

### Open questions before building

- Should the diagonal sub-score replace one of the existing four sub-scores or be a fifth scorer requiring weight rebalancing?
- Is the useful case primarily "subject is already tilted and we want to lean into it" or "subject is upright and we want to pick an AR that makes the extremities touch corners"? These are different problems with different solutions.
- For Option B (rotated extraction): how does the downstream ControlNet / IP-Adapter pipeline handle non-upright people in training crops? If the answer is "badly," the feature may not be worth building at all for the training-data use case.
