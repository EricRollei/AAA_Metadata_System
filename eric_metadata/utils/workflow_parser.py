"""Modern workflow parser façade used across metadata tooling."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    from PIL import Image
except ImportError:  # pragma: no cover - runtime dependency enforced elsewhere
    Image = None  # type: ignore[assignment]

from ..workflow.generation import extract_generation_parameters
from ..workflow.parsing import WorkflowParsingService

logger = logging.getLogger(__name__)


class WorkflowParser:
    """High-level helper that wraps :class:`WorkflowParsingService`."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._parsing = WorkflowParsingService(debug=debug)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_to_metadata_format(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured ``ai_info`` payload for ``workflow_data``."""

        if not workflow_data:
            return {}

        if not self._looks_like_comfy(workflow_data):
            return self._convert_simple_payload(workflow_data)

        try:
            generation = extract_generation_parameters(
                workflow_data,
                parsing_service=self._parsing,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._log_debug(f"generation extraction failed: {exc}")
            generation = {}

        prompts = self._parsing.parse_prompts(workflow_data)
        positive_text = [entry.text for entry in prompts.positive if entry.text]
        negative_text = [entry.text for entry in prompts.negative if entry.text]

        if positive_text and "prompt" not in generation:
            generation["prompt"] = "\n".join(positive_text)
        if negative_text:
            generation["negative_prompt"] = "\n".join(negative_text)

        assets_payload = self._build_assets_payload(workflow_data)

        generation.setdefault(
            "timestamp",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        ai_info: Dict[str, Any] = {
            "generation": _strip_blank(generation),
            "workflow": workflow_data,
        }

        if assets_payload:
            ai_info["assets"] = assets_payload

        workflow_info = self._build_workflow_info(workflow_data)
        if workflow_info:
            ai_info["workflow_info"] = workflow_info

        return {"ai_info": ai_info}

    def extract_and_convert_to_ai_metadata(
        self,
        source: Any,
        source_type: str = "file",
    ) -> Dict[str, Any]:
        """Load workflow data from ``source`` and convert to metadata."""

        workflow = self._load_workflow(source, source_type)
        if not workflow:
            return {}
        return self.convert_to_metadata_format(workflow)

    # ------------------------------------------------------------------
    # Workflow loading helpers
    # ------------------------------------------------------------------

    def _load_workflow(self, source: Any, source_type: str) -> Optional[Dict[str, Any]]:
        try:
            if source_type == "dict" and isinstance(source, dict):
                return source
            if source_type == "file":
                return self._load_from_file(Path(source))
            if source_type == "image":
                return self._extract_from_pil(source)
            if source_type == "json" and isinstance(source, (str, Path)):
                return self._load_json(Path(source))
            if source_type == "tensor":
                self._log_debug("tensor workflow sources are not yet supported")
        except Exception as exc:  # pragma: no cover - defensive logging
            self._log_debug(f"workflow load failed ({source_type}): {exc}")
        return None

    def _load_from_file(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            self._log_debug(f"workflow source missing: {path}")
            return None

        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._load_json(path)

        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            if Image is None:
                self._log_debug("PIL not available; cannot parse image metadata")
                return None
            try:
                with Image.open(path) as image:
                    return self._extract_from_pil(image)
            except Exception as exc:  # pragma: no cover - defensive logging
                self._log_debug(f"failed to open image {path}: {exc}")
                return None

        self._log_debug(f"unhandled workflow suffix: {suffix}")
        return None

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive logging
            self._log_debug(f"JSON load failed for {path}: {exc}")
            return None

    def _extract_from_pil(self, image: Any) -> Optional[Dict[str, Any]]:
        info = getattr(image, "info", {}) or {}

        for key in ("workflow", "prompt"):
            if key not in info:
                continue
            value = _normalise_text(info[key])
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                parsed = _try_parse_json(value)
                if parsed:
                    return parsed

        parameters = _normalise_text(info.get("parameters"))
        if isinstance(parameters, str):
            parsed = self._parse_a1111_parameters(parameters)
            if parsed:
                return parsed

        return None

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def _convert_simple_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        generation: Dict[str, Any] = {}

        for key in (
            "prompt",
            "negative_prompt",
            "sampler",
            "scheduler",
            "steps",
            "cfg_scale",
            "seed",
            "model",
            "width",
            "height",
        ):
            if key in record:
                generation[key] = record[key]

        generation.setdefault(
            "timestamp",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        return {
            "ai_info": {
                "generation": _strip_blank(generation),
                "workflow": record,
            }
        }

    def _build_assets_payload(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        assets = self._parsing.discover_assets(workflow)
        payload: Dict[str, Any] = {}

        if assets.loras:
            lora_entries = []
            for record in assets.loras:
                entry = {"name": record.name, "source": record.source}
                for key, value in (record.extra or {}).items():
                    if value is not None:
                        entry[key] = value
                lora_entries.append(entry)
            if lora_entries:
                payload["loras"] = lora_entries

        if assets.embeddings:
            embedding_entries = [
                {"name": record.name, "source": record.source}
                for record in assets.embeddings
            ]
            if embedding_entries:
                payload["embeddings"] = embedding_entries

        return payload

    def _build_workflow_info(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        node_count = self._count_nodes(workflow)
        if node_count is not None:
            info["node_count"] = node_count
        link_count = self._count_links(workflow)
        if link_count is not None:
            info["link_count"] = link_count
        return info

    def _count_nodes(self, workflow: Dict[str, Any]) -> Optional[int]:
        prompt_section = workflow.get("prompt")
        if isinstance(prompt_section, dict) and isinstance(prompt_section.get("nodes"), dict):
            return len(prompt_section["nodes"])
        nodes = workflow.get("nodes")
        if isinstance(nodes, dict):
            return len(nodes)
        return None

    def _count_links(self, workflow: Dict[str, Any]) -> Optional[int]:
        prompt_section = workflow.get("prompt")
        if isinstance(prompt_section, dict):
            links = prompt_section.get("links") or prompt_section.get("connections")
            if isinstance(links, list):
                return len(links)
        links = workflow.get("links") or workflow.get("connections")
        if isinstance(links, list):
            return len(links)
        return None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _looks_like_comfy(self, workflow: Dict[str, Any]) -> bool:
        if "prompt" in workflow and isinstance(workflow["prompt"], dict):
            return True
        if "nodes" in workflow and isinstance(workflow["nodes"], dict):
            return True
        return False

    def _parse_a1111_parameters(self, params_text: str) -> Dict[str, Any]:
        if not params_text:
            return {}

        result: Dict[str, Any] = {"type": "automatic1111"}

        split = params_text.split("Negative prompt:", 1)
        if len(split) == 2:
            result["prompt"] = split[0].strip()
            remainder = split[1]
            param_start = remainder.find("Steps:")
            if param_start >= 0:
                result["negative_prompt"] = remainder[:param_start].strip()
                param_text = remainder[param_start:]
            else:
                result["negative_prompt"] = remainder.strip()
                param_text = ""
        else:
            result["prompt"] = params_text.strip()
            param_text = ""

        for part in [segment.strip() for segment in param_text.split(",") if segment.strip()]:
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            coerced = _coerce_number(value)
            result[key] = coerced if coerced is not None else value

        return result

    def _log_debug(self, message: str) -> None:
        if self.debug:
            logger.debug("WorkflowParser: %s", message)


# ----------------------------------------------------------------------
# Module helpers
# ----------------------------------------------------------------------


def _normalise_text(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return None
    return value


def _try_parse_json(payload: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _strip_blank(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value is not None and value != ""
    }


def _coerce_number(value: str) -> Optional[Union[int, float]]:
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return None
