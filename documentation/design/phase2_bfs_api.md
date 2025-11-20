# Phase 2 BFS & Text Discovery API Design

## Context
- Phase 1 landed graph-normalisation, inline asset aggregation, and sampler fallbacks. Tests confirm breadth-first traversal is stable for string-id graphs.
- Phase 2 targets richer discovery (sampler prioritisation + prompt/text harvesting) without introducing runtime hooks.
- `WorkflowParsingService` already exposes:
  - `WorkflowGraph.bfs(start_node, direction="backward", max_depth=None)` returning `{node_id: distance}`
  - `find_sampler_candidates(workflow, start_node, max_depth=6)` returning ordered `SamplerCandidate` objects
  - `discover_prompt_nodes(workflow, start_node, max_depth=5, min_length=5)` returning `PromptNodeRef` dataclasses
- `WorkflowMetadataProcessor` consumes the service to populate `generation.samplers`, `prompts`, and inline asset metadata.

## Goals
1. Surface a reusable traversal API that captures both distance and class metadata for arbitrary nodes.
2. Provide a text discovery helper that works with any node exposing strings (inputs or widgets), ranked by graph distance.
3. Keep outputs serialisable (plain dict / list) so downstream consumers (save nodes, telemetry) can attach to metadata without new dependencies.
4. Avoid regressions for workflows that still use integer node identifiers or sparse link definitions.

## Proposed Additions
### 1. `WorkflowParsingService.trace_from_node`
```python
class WorkflowParsingService:
    def trace_from_node(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        direction: str = "backward",
        max_depth: Optional[int] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Return node_id -> payload with distance, class_type, and parent ids."""
```
- Wrapper over `WorkflowGraph.bfs` that enriches entries with:
  - `distance` (int)
  - `class_type` (string, default "")
  - `parents` (list of upstream node ids when `direction="backward"`)
- Guarantees node ids are strings.
- Internally builds a `WorkflowGraph` once per call.

### 2. `WorkflowParsingService.discover_text_nodes`
```python
class WorkflowParsingService:
    def discover_text_nodes(
        self,
        workflow: RawWorkflow,
        start_node: str,
        *,
        max_depth: int = 5,
        min_length: int = 8,
    ) -> List[PromptNodeRef]:
        """Breadth-first search for text-bearing nodes near start_node."""
```
- Returns a list of dataclass instances (new `TextNodeRef`) or plain dicts aligning with existing `PromptNodeRef` structure:
  - `node_id`, `class_type`, `distance`, `is_negative` (best-effort via `_infer_negative_flag`), `texts` (mapping field -> string), `source` ("input" or "widget").
- Collects strings from:
  - Node `inputs` where value is `str` and `len(value) >= min_length`.
  - Node `widgets_values` when present.
- Traversal respects `max_depth`; nodes at greater depth are skipped.
- Deduplicates fields per node; multiple fields per node remain in `texts` dict.
- Internally uses `_coerce_mapping` and the normalized adjacency graph, so integer ids remain supported.

### 3. Metadata Processor Integration
- Enhance `_extract_detailed_prompts` to:
  1. Call `trace_from_node` to record traversal info for debugging (`workflow_info.node_distances`).
  2. Call `discover_text_nodes` anchored at the resolved sampler node.
  3. Populate `generation["prompt_nodes"]` with ordered text node payloads (closest first).
  4. Fallback to existing parsed prompts when traversal finds none.
- Add optional `discovery_mode` handling: when enabled, append a short log entry for each text node discovered (node id, distance, text length) to `self.discovery_log`.

### 4. Data Contracts
- New dataclass (in `eric_metadata/workflow/parsing.py`) for richer text discovery:
```python
@dataclass
class TextNodeRef:
    node_id: str
    class_type: str
    distance: int
    is_negative: bool
    texts: Dict[str, str]
    sources: Dict[str, str]  # field -> "input" | "widget"
```
- `PromptNodeRef` can either extend or alias `TextNodeRef`; alternatively consolidate into one dataclass with optional fields to minimise duplication.
- Serialized form (dict) used by metadata processor to keep outputs JSON-friendly.

## Edge Cases & Safeguards
- Non-dict `workflow["prompt"]["nodes"]`: continue to normalise via `_coerce_mapping`.
- Cyclic graphs: BFS visited set prevents infinite traversal.
- Multi-sampler workflows: `find_sampler_candidates` still the entry point; traversal kicks off using the chosen candidate `node_id`.
- Negative detection heuristic: reuse `_infer_negative_flag` on each node’s inputs and class type.
- Min length guard prevents capturing short numeric tokens (`len < min_length`).

## Testing Plan
1. **Unit Tests (`tests/prep/test_module_boundaries.py` additions):**
   - `test_trace_from_node_returns_parents_and_distance()`
   - `test_discover_text_nodes_collects_inputs_and_widgets()`
   - `test_discover_text_nodes_respects_depth_limit()`
   - `test_metadata_processor_populates_prompt_nodes_from_discovery()`
2. **Regression Scenarios:**
   - Workflows with integer node ids (already covered; extend tests to cover new APIs).
   - Multi-sampler graph ensuring closest sampler wins.
   - Nodes without text values should yield empty discovery results without errors.
3. **Performance Check:** ensure traversal on mid-sized workflow (<150 nodes) completes <50ms in debug runs.

## Open Questions
- Do we want to expose parent link indices (slot numbers) in `trace_from_node` for richer diagnostics? (Default: no; can be added later.)
- Should `discover_text_nodes` allow custom filters (e.g., include numeric fields)? (Default: keep minimal; extend if user feedback demands.)
- Where should we persist traversal traces when not in discovery mode? (`workflow_info` vs dedicated `analysis.trace` bucket.)

## Next Actions
1. Implement dataclasses and helper APIs in `eric_metadata/workflow/parsing.py` per above.
2. Wire new helpers into `_extract_detailed_prompts` in `workflow_metadata_processor.py`.
3. Extend boundary tests and any downstream save-node formatting reliant on `generation["prompt_nodes"]` ordering.
4. Update documentation (`plan-metadataEnhancementImplementation.prompt.md`) with status once code lands.
