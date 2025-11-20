"""Lightweight protocol definitions shared across metadata modules."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class MetadataExtractor(Protocol):
    """Protocol for components that extract metadata from workflows."""

    def extract(self, workflow: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...


class TraversalHelper(Protocol):
    """Protocol for components that offer workflow traversal data."""

    def trace_from_node(
        self,
        node_id: str,
        workflow: Dict[str, Any],
        *,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        ...
