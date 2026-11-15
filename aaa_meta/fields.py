"""
fields.py
Maps a GenerationRecord (plus what the user typed and any measurements) onto
the standard metadata fields catalog software reads. The mapping follows the
Phase 0 acceptance test in Lightroom Classic, XnView MP and Capture One:

    dc:description            prompt the image model received      (searchable in all three)
    dc:subject                model / LoRA / sampler / user keywords
    lr:hierarchicalSubject    AI|Model|..., AI|LoRA|..., AI|Sampler|...
    photoshop:Headline        base model
    photoshop:Instructions    one-line settings summary incl. seed
    dc:title, dc:creator, dc:rights   user fields

Old-style IPTC (IIM) is deliberately not produced: Capture One shows it in
place of the XMP description on JPEG/TIFF when both are present.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .record import GenerationRecord, SamplingPass

DIGITAL_SOURCE_TYPE_AI = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
KEYWORD_ROOT = "AI"


@dataclass
class UserFields:
    """What the user typed on the save node. Everything optional."""
    title: str = ""
    keywords: List[str] = field(default_factory=list)
    creator: str = ""
    copyright: str = ""


@dataclass
class StandardFields:
    title: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    hierarchical_keywords: List[str] = field(default_factory=list)
    creator: str = ""
    rights: str = ""
    headline: str = ""
    instructions: str = ""
    creator_tool: str = ""
    digital_source_type: str = DIGITAL_SOURCE_TYPE_AI
    create_date: str = ""


def _number_text(value: Any) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def pass_summary(sampling: SamplingPass) -> str:
    bits: List[str] = []
    if sampling.steps is not None:
        bits.append(f"Steps {sampling.steps}")
    if sampling.sampler or sampling.scheduler:
        bits.append("/".join(part for part in (sampling.sampler, sampling.scheduler) if part))
    if sampling.cfg is not None:
        bits.append(f"CFG {_number_text(sampling.cfg)}")
    if sampling.guidance is not None:
        bits.append(f"Guidance {_number_text(sampling.guidance)}")
    if sampling.denoise is not None and sampling.denoise != 1:
        bits.append(f"Denoise {_number_text(sampling.denoise)}")
    if sampling.start_step is not None or sampling.end_step is not None:
        start = sampling.start_step if sampling.start_step is not None else 0
        end = sampling.end_step if sampling.end_step is not None else "end"
        bits.append(f"steps {start}-{end}")
    if sampling.seed is not None:
        bits.append(f"Seed {sampling.seed}")
    return ", ".join(bits)


def settings_summary(record: GenerationRecord) -> str:
    """One line for photoshop:Instructions, e.g. 'Steps 30, lcm/beta, CFG 1, Seed 123, 1536x2048'."""
    if not record.passes:
        parts: List[str] = []
    elif len(record.passes) == 1:
        parts = [pass_summary(record.passes[0])]
    else:
        parts = [f"Pass {p.index + 1}: {pass_summary(p)}" for p in record.passes]
    text = "; ".join(part for part in parts if part)
    if record.width and record.height:
        text = f"{text}, {record.width}x{record.height}" if text else f"{record.width}x{record.height}"
    return text


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        clean = " ".join(str(item).split())
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out


def _safe_leaf(text: str) -> str:
    """Hierarchy levels are separated by '|', so a leaf must not contain one."""
    return text.replace("|", "/").strip()


def build_standard_fields(record: GenerationRecord, user: Optional[UserFields] = None,
                          creator_tool: str = "ComfyUI") -> StandardFields:
    user = user or UserFields()
    out = StandardFields()
    out.title = user.title.strip()
    out.description = record.positive.strip() or record.positive_source.strip()
    out.creator = user.creator.strip()
    out.rights = user.copyright.strip()
    out.creator_tool = creator_tool
    out.create_date = record.created or ""

    base_stems = [m.stem for m in record.base_models if m.stem]
    lora_stems = [m.stem for m in record.loras if m.stem]
    samplers = [p.sampler for p in record.passes if p.sampler]

    out.keywords = _unique(base_stems + lora_stems + samplers + list(user.keywords))
    hierarchy: List[str] = []
    hierarchy += [f"{KEYWORD_ROOT}|Model|{_safe_leaf(s)}" for s in base_stems]
    hierarchy += [f"{KEYWORD_ROOT}|LoRA|{_safe_leaf(s)}" for s in lora_stems]
    hierarchy += [f"{KEYWORD_ROOT}|Sampler|{_safe_leaf(s)}" for s in samplers]
    out.hierarchical_keywords = _unique(hierarchy)

    out.headline = ", ".join(_unique(base_stems))
    out.instructions = settings_summary(record)
    return out
