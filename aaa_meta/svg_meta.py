"""
svg_meta.py
Puts metadata into an SVG without disturbing the drawing.

The <metadata> element is inserted as text right after the opening <svg ...>
tag (or replaces an existing <metadata> element). Nothing else in the file is
re-written, so text spacing, CDATA sections, comments and namespace prefixes
stay exactly as the generator produced them. The content is the RDF of a
standard XMP packet - the form exiftool, Inkscape and other tools read from SVG files.

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import re
from typing import Tuple

from .xmp_packet import _strip_packet_wrapper

_SVG_OPEN = re.compile(r"<svg\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>", re.IGNORECASE)
_METADATA = re.compile(r"<metadata\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*(?:/>|>.*?</metadata\s*>)", re.IGNORECASE | re.DOTALL)


_WRAPPED = re.compile(r"<x:xmpmeta([^>]*)>\s*<rdf:RDF([^>]*)>(.*)</rdf:RDF>\s*</x:xmpmeta>", re.DOTALL)


def _rdf_only(body: str) -> str:
    """<x:xmpmeta ...><rdf:RDF>...</rdf:RDF></x:xmpmeta>  ->  <rdf:RDF ...>...</rdf:RDF>
    Inside an SVG <metadata> element, tools (exiftool, Inkscape) expect the rdf:RDF element itself;
    with the x:xmpmeta wrapper around it the values are not recognised as title, keywords and so on."""
    match = _WRAPPED.match(body.strip())
    if match is None:
        return body
    declarations = match.group(1).replace(' xmlns:x="adobe:ns:meta/"', "")
    return f"<rdf:RDF{declarations}{match.group(2)}>{match.group(3)}</rdf:RDF>"


def embed_xmp(svg_text: str, packet: bytes) -> Tuple[str, bool]:
    """(svg with the packet in its <metadata> element, True) or (unchanged svg, False)."""
    body = _rdf_only(_strip_packet_wrapper(packet))
    if not svg_text or not body:
        return svg_text, False
    opening = _SVG_OPEN.search(svg_text)
    if opening is None or opening.group(0).rstrip().endswith("/>"):
        return svg_text, False
    block = f"<metadata>\n{body}\n</metadata>"
    existing = _METADATA.search(svg_text, opening.end())
    if existing is not None:
        return svg_text[:existing.start()] + block + svg_text[existing.end():], True
    return svg_text[:opening.end()] + "\n" + block + svg_text[opening.end():], True
