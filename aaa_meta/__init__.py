"""
aaa_meta - v2 core of the AAA Metadata System.

Layout:
    shared.py        process-wide capture state (survives double package import)
    capture/         runtime hooks (node execution, model file lookups)
    graph.py         prompt graph helpers
    resolve.py       value resolution (captured runtime values, then static graph)
    models.py        model / LoRA file detection
    record.py        GenerationRecord dataclasses (the canonical record)
    builder.py       graph + captured values -> GenerationRecord
    hashing.py       cached model hashes
    runtime.py       glue used by nodes inside a running ComfyUI

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from .record import GenerationRecord, ModelRef, SamplingPass  # noqa: F401
from .builder import build_record  # noqa: F401
from .graph import PromptGraph  # noqa: F401

__version__ = "2.0.0a1"


def publish(**fields) -> bool:
    """
    Optional protocol for node authors: call from inside a node's execute
    function to state metadata explicitly, e.g.
        aaa_meta.publish(positive="...", seed=123, steps=30)
    Published values take priority over anything inferred for that node.
    Returns False when called outside node execution.
    """
    from .capture.exec_hook import publish_for_current_node
    return publish_for_current_node(fields)
