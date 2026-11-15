# eric_compose - Project History & Handoff Notes

Companion to `DEV_NOTES.md`. While `DEV_NOTES.md` documents the system as it currently exists (architecture, rationale per file, tuning knobs), this document captures:

- **Research history** - what models / approaches were surveyed and why each was or wasn't pursued
- **Decision log** - the debates we had and the conclusions we reached
- **Session state at handoff** - what's done, what's mid-flight, what's open
- **Immediate next steps** - what to pick up first when returning to this work

If `DEV_NOTES.md` answers "how does it work and how do I tune it?", this answers "how did we get here and what's next?"

---

## Origin

Started from a vague memory: a GitHub repo that "tried to crop images to improve their composition" but couldn't be found again. Initial scope question - is this a v0.1 toy or a real tool? - was resolved by Eric's stated requirements:

1. Both ComfyUI nodes AND CLI operation
2. Quality over speed (multiple high-VRAM GPUs available)
3. Both fixed AR and free-form AR support, plus subset-list selection
4. Subject-aware, including the ability to crop a full-body shot down to head-and-shoulders when the lower half is unflattering (e.g., bad lighting)

Use cases that emerged through discussion:

- **Aesthetic recomposition** of standard photos (the original ask)
- **Training-data preparation** for fashion / clothing / styling models, where the cropper should produce body-part-isolated crops with the subject's face deliberately *excluded* so the model can't learn identity. This was Eric's idea once we were discussing pose-keypoint-driven cropping - a real and somewhat unusual feature, not in any off-the-shelf tool.
- **Text/watermark exclusion** - real concern for editorial / magazine sources where overlays must not appear in the output crop.

---

## Models and approaches surveyed

Comprehensive survey of the cropping research landscape, organized by category. Each entry includes verdict and reasoning.

### Heuristic / saliency / energy-based (no ML model)

| Tool | Verdict | Reasoning |
|---|---|---|
| **smartcrop.js** (jwagner) | Not pursued | Energy-based with rule-of-thirds weight and face boost. Well-known but limited - no pose awareness, no subject-direction. We've effectively re-implemented the useful parts in `scorers/composition.py` with body-region awareness on top. |
| **smartcrop.py** | Not pursued | Python port of smartcrop.js. Same limitations. |
| **mandykoh/autocrop** (Go) | Not pursued | Energy-based with alpha-aware threshold. Wrong language ecosystem; same limitations as smartcrop. |

### Face / subject detection-based

| Tool | Verdict | Reasoning |
|---|---|---|
| **leblancfg/autocrop** | Not pursued | Face-centered crop, OpenCV cascades. Too narrow - face only, no body presets, no AR control beyond aspect parameter. |
| **lih627/autocrop** | Considered seriously | Hybrid: face detection + GAIC + ARs. Closest match to what we wanted, BUT bundles GAIC weights (non-commercial) and DSFD face detection (additional dependency). Decided to build native instead since pose keypoints from DWPose give richer information than face bbox alone. |
| **garystafford/ai-image-cropper** | Not pursued | YOLO + DETR + RT-DETR pipeline. Object-detection based, not aesthetic-trained. Modern stack but solving a different problem (find objects, crop to fit) vs aesthetic-aware composition. |

### Deep learning - aesthetic / composition models

| Model | Year | Verdict | Reasoning |
|---|---|---|---|
| **VFN** (View Finding Network) | 2017 | Not pursued | Pairwise aesthetic ranking from professional web photos. Older; superseded by GAIC architecturally. No clear advantage. |
| **GAIC** (Grid Anchor based Image Cropping) | 2019/2020 | **Investigated, then dropped** | The foundational benchmark; what most modern cropping work compares against. Both official (HuiZeng) and unofficial PyTorch port (bo-zhang-cs/GAIC-Pytorch) require **compiled CUDA C++ extensions** for RoIAlign and RoDAlign. RoDAlign is GAIC's distinguishing feature - it pools features from the *discarded* region, not just the kept one. **Blocker**: building these on Windows portable Python with sm_120 (Blackwell RTX PRO 6000) is a recurring pain point matching Eric's experience with sageattention/xformers/bitsandbytes. Pure-PyTorch reimplementation would likely produce numerical mismatches with the pretrained weights. License also non-commercial. Verdict: not worth the engineering investment when an alternative path (composition scorer + UniPercept rerank) exists. |
| **CACNet** (Composing Photos Like a Photographer) | 2021 | Not pursued | Predicts composition rule + crop in one feed-forward. Same lab as GAIC PyTorch port, same custom CUDA op problem expected. |
| **ASM-Net** | 2021 | Surveyed only | Aesthetic score map combining composition and saliency. No clear advantage over GAIC for our use; unclear weights availability. |
| **TransView** | 2022 | Surveyed only | Transformer-based crop ranking. Newer but not obviously better; same custom-op concerns as GAIC family if from same lineage. |
| **Human-Centric-Image-Cropping** (bcmi) | ECCV 2022 | **Investigated, then deferred** | Most relevant to our use case - explicitly handles humans with partition-aware features and direction-conditional content preservation. Paper example shows direction-aware lead-room (subject walks right-to-left, more space preserved on left side) - exactly the photographic principle our `lead_room` variation encodes as a hand-crafted heuristic. **However**: same lab as GAIC PyTorch port, same era (2022), strongly suggests same custom CUDA ops (not verified directly). What it would add: learned partition-aware features. What we already have: rule-based `Subject.facing()` + `_apply_h_lead`. **Decision**: defer until composition + UniPercept on real photos shows asymmetric framing handling is consistently weak. Then reconsider, but might prefer CLIP-aesthetic over fighting bcmi's CUDA build. |
| **CLIPCropping** | 2023 | Considered for v1.5 | CLIP embeddings for aesthetic scoring. No custom CUDA ops; just CLIP backbone + small head. Permissive licensing. **Likely path for v1.5 deep aesthetic scorer if needed.** |
| **S²CNet** | AAAI 2024 | Surveyed only | Spatial-Semantic Collaborative cropping; introduced UGCrop5K dataset. Newer but same family of architectures. |
| **Cropper** (VLM-based, Google) | 2024 | Not pursued | Iteratively refines crop candidates by scoring with a VLM. Relies on closed VLMs; paper only, no released code. Even with code, latency makes it impractical for batch use. |
| **AesCrop** (VMamba) | Oct 2025 | Not pursued | VMamba-based, claims SOTA. Paper only, no code I could find. |
| **ProCrop** | May 2025 | Not pursued | Retrieval-augmented (retrieves compositionally similar pro photos). Under review, dataset described but model not released yet. |

### Aesthetic scorers (separate from cropping models)

These were considered for the "score the candidates" role rather than the "propose the candidates" role.

| Tool | Verdict | Reasoning |
|---|---|---|
| **LAION aesthetic predictor** | Likely v1.5 | CLIP + small MLP. ~30MB, MIT-licensed, works with stock CLIP ViT-L/14. Drop-in if composition + UniPercept proves insufficient. |
| **UniPercept** (Eric's existing tool) | **CHOSEN as external reranker** | Already built and integrated into Eric's workflow. Outputs IAA / IQA / ISTA as integers (0-100 scale). Validated on Eric's photo collection. Lives in `Eric_image_classific` package. Decision was to leverage this as the "absolute aesthetic grader" rather than build a redundant internal deep scorer. |
| **pyiqa / TOPIQ / MUSIQ** (Eric's prior work) | Deferred (region_quality scorer) | Per-region image-quality scoring is the original "bad lighting → tighter crop" use case. Placeholder in roadmap; lower priority since UniPercept handles whole-image aesthetics. |

### Awesome-list reference

The canonical curated list for this space is **bcmi/Awesome-Aesthetic-Evaluation-and-Cropping**. Useful for tracking new papers, but most active research uses the GAIC custom-op lineage that we're avoiding.

---

## Key debates and conclusions

### Debate 1: extend existing nodes or new package?

Eric had two existing cropping-adjacent node sets:
- `AAA_Metadata_System/SmartImageCropper` - heuristic OpenCV, oriented toward extracting embedded photos from scans / magazine pages
- `PDF_tools/Florence2ImageCropper` - language-prompted region extraction
- `PDF_tools/Florence2RectangleDetector` - rectangle detection in scans

**Conclusion**: build new package alongside existing nodes. Existing nodes are *region-extraction* tools ("find the photo inside this image"); the new tool is *aesthetic recomposition* ("this IS the photo - make it better"). Different decision logic, different scoring, different subject-awareness model. Mixing turns a clean tool into a god-node. Placement in `AAA_Metadata_System` since it's general-purpose photo work and `SmartImageCropper` is already there.

### Debate 2: how to handle the "full-body, but lower half is bad" case?

This was the original use case that distinguished us from off-the-shelf croppers. Standard aesthetic croppers preserve the salient subject as much as possible - they don't proactively trim a person.

**Initial design**: combine pose keypoints (for body-part-aware candidate generation) + per-region image quality (IQA scoring of each candidate region) so a region with bad lighting tanks any crop containing it.

**Refined**: Eric pointed out that "bad lighting" is just one example; the broader concept is just "let the user pick a body region preset." Result: 10 explicit body presets in `presets.py`, each with documented coefficients. Per-region IQA was deferred to v2 as `scorers/region_quality.py`.

### Debate 3: face-include vs face-exclude presets

Eric raised this when discussing pose-keypoint-driven cropping. Some training use cases (clothing styles, outfit reference, garment isolation) explicitly DON'T want the face in the frame, so the model can't learn identity from training data.

**Conclusion**: split presets into two groups - face-include (head_only through full_body_tight) and face-exclude (outfit_full, torso_only, legs_only). The face-exclude presets are first-class features, not edge cases. Implementation has belt-and-suspenders enforcement: anchor functions position the box below the chin by construction, and `selector.face_excluded()` validates that no face keypoint exceeds min_conf in the final box.

### Debate 4: GAIC scorer - go or no-go?

**Original plan (early in chat)**: build GAIC + CACNet scorers as the deep aesthetic priors, with composition as a fast pre-rank.

**Pivot point**: investigation revealed all GAIC PyTorch implementations require compiled CUDA C++ extensions for RoIAlign / RoDAlign. Combined with:
- Eric already has UniPercept doing absolute aesthetic grading
- Building GAIC means another compile-from-source maintenance burden
- GAIC weights are non-commercial-licensed

**Conclusion**: drop GAIC and CACNet. Use composition scorer (rule-based, fast) for internal pre-rank and UniPercept (Eric's existing tool) for external rerank. Cleaner architecture, simpler maintenance, no license encumbrance.

### Debate 5: how to integrate UniPercept

Several approaches were debated:

- **Path A**: UniPercept as an internal scorer (single node, library import). Simplest UX; couples our package to Eric_image_classific.
- **Path B**: Candidates + Pick nodes (multi-node ComfyUI workflow with iteration). Decoupled; more wiring per use.
- **Path C** (what was actually proposed and is the current direction): two nodes - Candidates produces top-K crops as IMAGE batch + JSON; Pick takes IMAGE batch + JSON + iaa/iqa/ista INT inputs and selects winner.

**Conclusion**: Path C (Candidates + Pick with INT inputs). ComfyUI-idiomatic, no library coupling, works for any future scorer (not just UniPercept), and matches the screenshot Eric showed early in the chat where UniPercept's node output integers directly. Eric explicitly raised this when reviewing - "I thought you were going to just add integer inputs for iaa and iqa in the first flush" - confirming the right direction.

**Open sub-question**: how does Eric's UniPercept node handle a multi-image IMAGE batch? Does it score per-element or just the first? This determines whether the workflow needs an iteration node or one UniPercept call suffices. Needs empirical check before Pick is finalized.

### Debate 6: text overlay / watermark handling

User concern: real-world fashion / editorial photos have text overlays, watermarks, magazine-style typography that must be cropped out.

Two architectural options:
- **Built-in text detection** - bundle EasyOCR / PaddleOCR / Florence-2 inside the cropper
- **Exclusion mask input** - accept any MASK input; user generates it however they want

**Conclusion**: exclusion mask. Decoupled, future-proof, handles more than text (watermarks, logos, distracting backgrounds), matches Eric's stated preference for explicit/composable over magic. Implemented as `exclude_mask` (MASK) + `exclude_overlap_thresh` (FLOAT) inputs.

### Debate 7: should "no crop" be a candidate?

Surfaced when Eric noted "initial results not as expected" and asked whether the system considered the original image as the best possible crop.

**Diagnosis**: it didn't. The original was only returned as a fallback when all candidates failed validation, not as a competing candidate.

**Fix**: add `_add_no_crop_candidate()` to pipeline, gated by `allow_no_crop` BOOLEAN. When the original AR matches the allowed set, the full image becomes a candidate and competes on the same scoring as proposed crops. Default True.

This is also a good architectural sanity check - if composition scoring routinely picks the original over proposed crops, the proposals are bad. If it picks proposed crops over a clearly-better original, the scorer is bad. Either way the diagnostic value is clear.

---

## Session state at handoff

### What's done and working

- Foundation (types.py, subjects.py, presets.py, selector.py) - complete and tested
- Candidate generation (pose_anchored.py, grid.py) - complete and tested with synthetic pose
- Composition scorer (composition.py) - complete, four sub-scores, tested on synthetic data
- Composite scorer wrapper (composite.py) - complete, ready to accept additional scorers
- Pipeline orchestrator (pipeline.py) - complete with exclude_mask filter and no-crop candidate
- Single ComfyUI node (eric_compose_crop.py) - complete with full tooltips on every input
- Smoke tests pass for: import, applicable_presets, full pipeline, exclude_mask filter
- DEV_NOTES.md - architecture and tuning reference, comprehensive
- HISTORY_AND_HANDOFF.md (this file) - research notes and session state

### What's mid-flight (in progress when chat ended)

- **Candidates + Pick nodes** - design agreed (Path C with INT inputs), code not yet written.
  - `nodes/eric_compose_crop_candidates.py` - outputs IMAGE batch + STRING JSON of bbox/source/score per candidate
  - `nodes/eric_compose_crop_pick.py` - takes IMAGE batch + JSON + iaa/iqa/ista INT inputs + metric selector, returns single IMAGE
  - The Pick node should accept either single INT (case where UniPercept scores per element via batch loop) or comma-separated STRING-of-INTs (case where one UniPercept call handles a batch). Final decision pending empirical check of UniPercept batch behavior.

### What's open / unverified

- **Composition scorer quality on real photos** - Eric tested and reported "initial results not as expected or pleasing." This was the trigger for adding (a) the `allow_no_crop` candidate and (b) advancing the UniPercept rerank plan. Whether composition + UniPercept produces good crops on Eric's actual fashion / editorial photos is unverified.
- **UniPercept batch handling** - does Eric's UniPercept node score every IMAGE in a batch independently, or only the first? Determines Pick node input shape.
- **Real photo testing** - all testing to date has been on synthetic perfectly-centered subjects with random-noise pixel data. Real-photo behavior of the scorer is unknown.
- **Multi-person handling** - in v1, only the highest-confidence person is cropped around; others are ignored. Eric flagged this as "very complicated subject - when there is more than 1 person how do we know what's really the most important one? This will be experimental." V1 behavior is intentionally simple; refinement deferred until use cases emerge.

### What's deferred to v1.5 (next major work block)

- Candidates + Pick nodes (see "mid-flight" above) - this is the immediate next chunk
- CLIP-aesthetic scorer (`scorers/clip_aesthetic.py`) - if composition + UniPercept proves insufficient on real photos
- Soft-penalty mode for `exclude_mask` (currently hard-rejection only)
- Composition sub-weights as optional node inputs (currently editable only in source)

### What's deferred to v2 or beyond

- CLI entry point (need to confirm v1 produces good results before bothering)
- `candidates/saliency_anchored.py` for non-person images (currently grid-only fallback)
- `scorers/region_quality.py` for the per-region IQA "bad lighting" use case
- Pure-PyTorch RoDAlign reimplementation of GAIC - only if all other paths fail
- Human-Centric-Image-Cropping (bcmi) - only if asymmetric framing handling needs upgrading and CUDA build pain has been solved by then

---

## Immediate next steps when picking this back up

In priority order:

1. **Test the v0.2 pipeline on a few real photos in ComfyUI.** Confirm restart picked up the changes (allow_no_crop input visible, tooltips appearing on hover). Run on representative fashion / editorial photos. Note which crops are picked vs which the human would pick. This is critical signal for whether composition scoring alone is adequate or whether UniPercept rerank is essential.

2. **Verify UniPercept batch behavior.** Feed Eric's UniPercept Scorer node a 2-image IMAGE batch. Inspect the iaa / iqa / ista outputs. If they're scalar INT (UniPercept scored only the first image), Pick needs to support an external loop pattern. If they're per-element (somehow - maybe LIST or tensor or batched STRING), Pick can take a list/string. This determines the Pick node input shape.

3. **Implement Candidates and Pick nodes.** Based on the batch-behavior result. Plan:
   - `eric_compose_crop_candidates.py` outputs `(IMAGE batch, STRING json, INT count)`. The IMAGE batch is the K candidate crops stacked. JSON has per-index bbox, source, internal composition score. Count is K so downstream nodes know how many were produced.
   - `eric_compose_crop_pick.py` takes `(IMAGE batch, STRING json, INT iaa, INT iqa, INT ista, COMBO metric, FLOAT/list weights)` and returns `(IMAGE single, STRING bbox, STRING info)`. Picks the winner by the selected metric (or weighted blend of all three).
   - The metric selector COMBO should include: "iaa", "iqa", "ista", "average" (mean of all three), "weighted" (uses the weight inputs).

4. **Tune composition coefficients** if real-photo testing shows specific failure modes. Tunable defaults are in:
   - `presets.py` - body anchor coefficients
   - `scorers/composition.py` - W_THIRDS / W_HEADROOM / W_LEADROOM / W_EDGECUT and the per-sub-score constants

5. **Decide on CLIP-aesthetic** based on (1) results. If composition + UniPercept gives good crops, skip CLIP-aesthetic entirely. If gaps remain that UniPercept doesn't catch, CLIP-aesthetic is the v1.5 add.

---

## File map (current state)

```
AAA_Metadata_System/eric_compose/
├── __init__.py             - public exports for the subpackage
├── DEV_NOTES.md            - architecture and tuning reference (live)
├── HISTORY_AND_HANDOFF.md  - this file (research, debates, handoff)
├── types.py                - KP, ARSpec, Candidate, ScoreReport, Scorer protocol
├── subjects.py             - POSE_KEYPOINT parsing, Subject body measurements
├── presets.py              - 10 body presets with documented coefficients
├── selector.py             - geometry, AR conform, NMS, validators (face / mask)
├── pipeline.py             - end-to-end orchestrator with allow_no_crop
├── candidates/
│   ├── __init__.py
│   ├── pose_anchored.py    - 6-row variation table per (preset, AR)
│   └── grid.py             - GAIC-style anchor grid, AR-prefiltered
└── scorers/
    ├── __init__.py
    ├── base.py             - BaseScorer convenience class
    ├── composition.py      - 4 sub-scores: thirds, headroom, leadroom, edgecut
    └── composite.py        - weighted multi-scorer combiner with normalization

AAA_Metadata_System/nodes/
└── eric_compose_crop.py    - "Eric Compose Crop" node (only node in v0.2)
```

Pending file additions for v1.5:
```
AAA_Metadata_System/nodes/
├── eric_compose_crop_candidates.py   - top-K output for external rerank
└── eric_compose_crop_pick.py         - select winner from external scores
```

---

## Key smoke test commands (for quick verification when returning)

All commands run from any directory using Eric's embedded Python.

**Verify package imports cleanly:**

```
A:\Comfy25\ComfyUI_windows_portable\python_embeded\python.exe -c "import sys; sys.path.insert(0, r'A:\Comfy25\ComfyUI_windows_portable\ComfyUI\custom_nodes\AAA_Metadata_System'); from eric_compose import PRESETS; print(list(PRESETS.keys()))"
```

Expected: 10 preset names. If this fails, there's an import error somewhere - the assertion at the bottom of presets.py is the most likely culprit if anyone changed face_policy declarations.

**Full pipeline with synthetic pose:**

```
A:\Comfy25\ComfyUI_windows_portable\python_embeded\python.exe -c "import sys; sys.path.insert(0, r'A:\Comfy25\ComfyUI_windows_portable\ComfyUI\custom_nodes\AAA_Metadata_System'); import numpy as np; from eric_compose.pipeline import compose_crop; kps=[0]*54; kps[0:3]=[400,200,0.9]; kps[3:6]=[400,300,0.9]; kps[6:9]=[350,310,0.9]; kps[15:18]=[450,310,0.9]; kps[24:27]=[370,500,0.9]; kps[33:36]=[430,500,0.9]; kps[30:33]=[365,800,0.9]; kps[39:42]=[435,800,0.9]; kps[42:45]=[420,190,0.9]; kps[45:48]=[380,190,0.9]; kps[48:51]=[430,180,0.9]; kps[51:54]=[370,180,0.9]; pk=[{'people':[{'pose_keypoints_2d':kps}],'canvas_width':800,'canvas_height':1000}]; img=(np.random.rand(1000,800,3)*255).astype(np.uint8); best, top = compose_crop(image=img, pose_keypoint=pk, preset='auto', aspect_ratios=[1.0, 0.8, 9/16]); print(f'best preset: {best.candidate.preset}'); print(f'best score:  {best.report.final:.3f}'); print(f'top-K count: {len(top)}'); print(f'best source: {best.candidate.source}')"
```

Expected (or thereabouts):
```
best preset: half_body
best score:  0.796
top-K count: 10
best source: pose:half_body:tight_centered:ar1.000
```

If `best source: no_crop:original` shows up, that's actually expected when allow_no_crop=True (default in pipeline) and the random-pixel noise scores well. Either is valid.

---

## Lessons learned (for future sessions)

1. **Don't propose deep model integrations without checking the build situation.** Wasted time considering GAIC/CACNet before discovering both need compiled CUDA extensions. Should have checked the build dependencies upfront.

2. **Eric's existing tooling matters.** UniPercept was already there, validated, integrated. Designing around it (rather than building competing internal scorers) is the right move.

3. **Synthetic test data has limitations.** All early scoring tests used a perfectly-centered synthetic subject with random pixels. This made `tight_centered` variations always win, and lead-room (always frontal) and rule-of-thirds were both at neutral or low scores. Real-photo testing produces meaningfully different rankings - don't draw conclusions from synthetic-test results.

4. **Tooltips matter.** Initial node version was missing them on most inputs. Eric explicitly asked for them. Easy oversight; should be standard from the start on any future ComfyUI nodes.

5. **The "no crop" candidate is obvious in hindsight.** Should have been in v0.1 - any cropping system needs to consider not cropping. Don't repeat this kind of oversight on v1.5 nodes.

6. **Apply edits with str_replace / write_file, don't print whole files in chat.** Eric's preference, stated in user prefs and reinforced explicitly. Wastes chat budget. The existing files are on disk - editing them in place is the right pattern.
