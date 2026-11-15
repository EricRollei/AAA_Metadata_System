"""Print the static-trace record for every local fixture (developer aid)."""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aaa_meta import PromptGraph, build_record

SAVE_HINTS = ("MetadataAwareSaveImage", "SaveImage", "Image Save", "SaveImageHighPrec")

def find_anchor(graph):
    for node_id in graph.nodes:
        if any(h in graph.class_type(node_id) for h in SAVE_HINTS):
            return node_id
    return None

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    only = sys.argv[1:] 
    for path in sorted(glob.glob(os.path.join(here, "fixtures_local", "fixture_*.json"))):
        if only and not any(o in path for o in only):
            continue
        data = json.load(open(path, encoding="utf-8"))
        graph = PromptGraph.from_prompt(data["prompt"])
        anchor = find_anchor(graph)
        record = build_record(graph, anchor)
        print(f"===== {os.path.basename(path)}  anchor={anchor} ({graph.class_type(anchor)})")
        print(record.summary())
