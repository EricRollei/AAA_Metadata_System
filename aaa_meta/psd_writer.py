"""
psd_writer.py
Writes Photoshop layer data directly, for the two cases psd-tools does not cover:

  * a 16-bit layered PSD                      write_psd(...)
  * layers inside a TIFF that Photoshop opens  photoshop_tiff_block(...)
    (TIFF tag 37724 "ImageSourceData" - the same layer structure a PSD uses)

A layer is a dict:
    {"name": str, "pixels": float array H x W x 4 (RGBA, 0..1),
     "blend": "normal" | "multiply" | ... , "opacity": 0..255, "visible": bool}
Layers are listed bottom first. All layers cover the full canvas. Channel data
is stored uncompressed (valid for every Photoshop version; files are larger).

byte_order: ">" for PSD files and big-endian TIFFs, "<" for little-endian TIFFs
(inside a TIFF the layer data follows the TIFF's byte order, signatures reversed).

Author: Eric Hiss (GitHub: EricRollei)
License: Dual License (CC BY-NC 4.0 / Commercial) - see LICENSE
"""

import struct
from typing import Any, Dict, List, Optional

import numpy as np

BLEND_KEYS = {
    "normal": b"norm", "multiply": b"mul ", "screen": b"scrn", "overlay": b"over",
    "add": b"lddg", "linear_dodge": b"lddg", "subtract": b"fsub", "difference": b"diff",
    "darken": b"dark", "lighten": b"lite", "color_dodge": b"div ", "color_burn": b"idiv",
    "soft_light": b"sLit", "hard_light": b"hLit", "exclusion": b"smud", "hue": b"hue ",
    "saturation": b"sat ", "color": b"colr", "luminosity": b"lum ",
}
TIFF_BLOCK_HEADER = b"Adobe Photoshop Document Data Block\x00"
TIFF_TAG_IMAGE_SOURCE_DATA = 37724


def _key(key: bytes, byte_order: str) -> bytes:
    return key if byte_order == ">" else key[::-1]


def _plane(values: np.ndarray, depth: int) -> bytes:
    """One channel, float 0..1 -> raw samples. Pixel data is big-endian in PSD and
    in the TIFF layer block alike (only the structure around it follows the TIFF byte order)."""
    clipped = np.clip(values.astype(np.float64), 0.0, 1.0)
    if depth == 16:
        return np.round(clipped * 65535.0).astype(">u2").tobytes()
    return np.round(clipped * 255.0).astype(np.uint8).tobytes()


def _rgba(pixels: Any) -> np.ndarray:
    array = np.asarray(pixels, dtype=np.float32)
    if array.ndim == 2:
        array = array[..., None]
    if array.shape[-1] == 1:
        array = np.repeat(array, 3, axis=-1)
    if array.shape[-1] == 3:
        array = np.concatenate([array, np.ones(array.shape[:2] + (1,), dtype=np.float32)], axis=-1)
    return array[..., :4]


def _layer_record(layer: Dict[str, Any], height: int, width: int, plane_bytes: int, byte_order: str) -> bytes:
    bo = byte_order
    name = str(layer.get("name") or "Layer")
    record = struct.pack(bo + "4i", 0, 0, height, width)
    record += struct.pack(bo + "H", 4)
    for channel_id in (-1, 0, 1, 2):                         # transparency, R, G, B
        record += struct.pack(bo + "hI", channel_id, 2 + plane_bytes)
    record += _key(b"8BIM", bo) + _key(BLEND_KEYS.get(str(layer.get("blend", "normal")).lower(), b"norm"), bo)
    opacity = max(0, min(int(layer.get("opacity", 255)), 255))
    flags = 0x08 | (0 if layer.get("visible", True) else 0x02)
    record += struct.pack("4B", opacity, 0, flags, 0)

    legacy_name = name.encode("latin-1", "replace")[:255]
    pascal = bytes([len(legacy_name)]) + legacy_name
    pascal += bytes((4 - len(pascal) % 4) % 4)
    unicode_name = name.encode("utf-16-be" if bo == ">" else "utf-16-le")
    luni = struct.pack(bo + "I", len(unicode_name) // 2) + unicode_name
    luni += bytes((4 - len(luni) % 4) % 4)
    extra = struct.pack(bo + "I", 0) + struct.pack(bo + "I", 0) + pascal        # no layer mask, no blending ranges
    extra += _key(b"8BIM", bo) + _key(b"luni", bo) + struct.pack(bo + "I", len(luni)) + luni
    return record + struct.pack(bo + "I", len(extra)) + extra


def layer_info_bytes(layers: List[Dict[str, Any]], depth: int = 8, byte_order: str = ">") -> bytes:
    """The Photoshop "layer info" structure: layer count, layer records, channel image data."""
    if depth not in (8, 16):
        raise ValueError("depth must be 8 or 16")
    prepared = [(_rgba(layer["pixels"]), layer) for layer in layers]
    if not prepared:
        raise ValueError("no layers")
    height, width = prepared[0][0].shape[:2]
    plane_bytes = height * width * (depth // 8)
    out = [struct.pack(byte_order + "h", len(prepared))]
    for pixels, layer in prepared:
        if pixels.shape[:2] != (height, width):
            raise ValueError(f"layer {layer.get('name')!r} is {pixels.shape[1]}x{pixels.shape[0]}, canvas is {width}x{height}")
        out.append(_layer_record(layer, height, width, plane_bytes, byte_order))
    compression = struct.pack(byte_order + "H", 0)
    for pixels, _ in prepared:
        for channel in (3, 0, 1, 2):
            out.append(compression)
            out.append(_plane(pixels[..., channel], depth))
    data = b"".join(out)
    return data + bytes(len(data) % 2)


def photoshop_tiff_block(layers: List[Dict[str, Any]], depth: int = 8, byte_order: str = "<") -> bytes:
    """Value for TIFF tag 37724 (ImageSourceData) so Photoshop shows the layers of a TIFF."""
    info = layer_info_bytes(layers, depth, byte_order)
    info += bytes((4 - len(info) % 4) % 4)
    key = b"Layr" if depth == 8 else b"Lr16"
    block = (TIFF_BLOCK_HEADER + _key(b"8BIM", byte_order) + _key(key, byte_order)
             + struct.pack(byte_order + "I", len(info)) + info)
    # global layer mask info with Photoshop's default values (Photoshop writes this block too)
    user_mask = b"\xff\xff" + bytes(10) + b"\x80\x00"
    block += (_key(b"8BIM", byte_order) + _key(b"LMsk", byte_order)
              + struct.pack(byte_order + "I", len(user_mask)) + user_mask + bytes(2))
    return block


def _resource(resource_id: int, data: bytes) -> bytes:
    block = b"8BIM" + struct.pack(">H", resource_id) + b"\x00\x00" + struct.pack(">I", len(data)) + data
    return block + bytes(len(data) % 2)


def write_psd(path: str, composite: Any, layers: List[Dict[str, Any]], depth: int = 16,
              icc_profile: Optional[bytes] = None) -> None:
    """
    composite: float array H x W x 3 (the flattened picture other programs show).
    Layers as described in the module docstring. depth 8 or 16.
    """
    flat = np.asarray(composite, dtype=np.float32)[..., :3]
    height, width = flat.shape[:2]
    info = layer_info_bytes(layers, depth, ">")
    header = b"8BPS" + struct.pack(">H", 1) + bytes(6) + struct.pack(">HIIHH", 3, height, width, depth, 3)
    resources = _resource(0x040F, icc_profile) if icc_profile else b""
    if depth == 16:
        padded = info + bytes((4 - len(info) % 4) % 4)
        body = struct.pack(">II", 0, 0) + b"8BIM" + b"Lr16" + struct.pack(">I", len(padded)) + padded
    else:
        body = struct.pack(">I", len(info)) + info + struct.pack(">I", 0)
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack(">I", 0))                               # colour mode data
        handle.write(struct.pack(">I", len(resources)) + resources)
        handle.write(struct.pack(">I", len(body)) + body)
        handle.write(struct.pack(">H", 0))                               # composite: uncompressed
        for channel in range(3):
            handle.write(_plane(flat[..., channel], depth))


# ---------------------------------------------------------------------------
# reading the layer block back from a TIFF
# ---------------------------------------------------------------------------
def _unpackbits(data: bytes, expected: int) -> bytes:
    out = bytearray()
    position, size = 0, len(data)
    while position < size and len(out) < expected:
        header = data[position]
        position += 1
        if header < 128:
            out += data[position:position + header + 1]
            position += header + 1
        elif header > 128:
            out += data[position:position + 1] * (257 - header)
            position += 1
    return bytes(out[:expected])


def _decode_channel(raw: bytes, compression: int, rows: int, columns: int, depth: int, byte_order: str) -> np.ndarray:
    """Channel bytes -> float32 rows x columns in 0..1."""
    import zlib
    sample = depth // 8
    expected = rows * columns * sample
    if compression == 0:
        data = raw[:expected]
    elif compression == 1:                                   # PackBits, one byte count per row first
        counts = np.frombuffer(raw[:rows * 2], dtype=byte_order + "u2")
        data, position = bytearray(), rows * 2
        for count in counts:
            data += _unpackbits(raw[position:position + int(count)], columns * sample)
            position += int(count)
        data = bytes(data)
    elif compression in (2, 3):
        data = zlib.decompress(raw)
    else:
        raise ValueError(f"unknown channel compression {compression}")
    if len(data) < expected:
        data = data + bytes(expected - len(data))
    if depth == 16:
        values = np.frombuffer(data[:expected], dtype=">u2").reshape(rows, columns)
        if compression == 3:                                 # differences along each row
            values = np.cumsum(values.astype(np.uint32), axis=1).astype(np.uint16)
        return values.astype(np.float32) / 65535.0
    values = np.frombuffer(data[:expected], dtype=np.uint8).reshape(rows, columns)
    if compression == 3:
        values = np.cumsum(values.astype(np.uint32), axis=1).astype(np.uint8)
    return values.astype(np.float32) / 255.0


def parse_tiff_block(block: bytes, canvas_height: int, canvas_width: int) -> List[Dict[str, Any]]:
    """
    TIFF tag 37724 value -> layers (bottom first), each
    {"name", "pixels" (float32 H x W x 4 on the full canvas), "blend", "opacity", "visible"}.
    Layers without pixels (groups, adjustment layers) are left out. [] when there is no layer data.
    """
    if not block.startswith(TIFF_BLOCK_HEADER):
        return []
    position = len(TIFF_BLOCK_HEADER)
    info, depth, bo = None, 8, ">"
    while position + 12 <= len(block):
        signature, key = block[position:position + 4], block[position + 4:position + 8]
        if signature == b"8BIM":
            bo = ">"
        elif signature == b"MIB8":
            bo, key = "<", key[::-1]
        else:
            break
        length = struct.unpack(bo + "I", block[position + 8:position + 12])[0]
        if key in (b"Layr", b"Lr16"):
            info, depth = block[position + 12:position + 12 + length], (16 if key == b"Lr16" else 8)
            break
        position += 12 + length + ((4 - length % 4) % 4)
    if info is None or len(info) < 2:
        return []

    blend_names = {value: name for name, value in BLEND_KEYS.items() if name != "linear_dodge"}
    count = abs(struct.unpack(bo + "h", info[:2])[0])
    offset = 2
    records = []
    for _ in range(count):
        top, left, bottom, right = struct.unpack(bo + "4i", info[offset:offset + 16])
        channel_count = struct.unpack(bo + "H", info[offset + 16:offset + 18])[0]
        offset += 18
        channels = []
        for _ in range(channel_count):
            channel_id, size = struct.unpack(bo + "hI", info[offset:offset + 6])
            channels.append((channel_id, size))
            offset += 6
        blend_key = info[offset + 4:offset + 8]
        blend_key = blend_key if bo == ">" else blend_key[::-1]
        opacity, _clipping, flags, _filler = struct.unpack("4B", info[offset + 8:offset + 12])
        extra_length = struct.unpack(bo + "I", info[offset + 12:offset + 16])[0]
        extra = info[offset + 16:offset + 16 + extra_length]
        offset += 16 + extra_length
        mask_length = struct.unpack(bo + "I", extra[:4])[0]
        cursor = 4 + mask_length
        ranges_length = struct.unpack(bo + "I", extra[cursor:cursor + 4])[0]
        cursor += 4 + ranges_length
        name_length = extra[cursor]
        name = extra[cursor + 1:cursor + 1 + name_length].decode("latin-1", "replace")
        marker = extra.find((b"8BIM" if bo == ">" else b"MIB8") + (b"luni" if bo == ">" else b"inul"))
        if marker >= 0:
            characters = struct.unpack(bo + "I", extra[marker + 12:marker + 16])[0]
            raw_name = extra[marker + 16:marker + 16 + characters * 2]
            name = raw_name.decode("utf-16-be" if bo == ">" else "utf-16-le", "replace").rstrip("\x00") or name
        records.append({"rect": (top, left, bottom, right), "channels": channels, "name": name,
                        "blend": blend_names.get(blend_key, "normal"), "opacity": opacity,
                        "visible": not (flags & 0x02)})

    layers: List[Dict[str, Any]] = []
    for record in records:
        top, left, bottom, right = record["rect"]
        rows, columns = bottom - top, right - left
        planes: Dict[int, np.ndarray] = {}
        for channel_id, size in record["channels"]:
            chunk = info[offset:offset + size]
            offset += size
            if channel_id < -1 or rows <= 0 or columns <= 0 or size < 2:
                continue                                     # layer masks use their own rectangle; not needed here
            compression = struct.unpack(bo + "H", chunk[:2])[0]
            try:
                planes[channel_id] = _decode_channel(chunk[2:], compression, rows, columns, depth, bo)
            except Exception:
                planes = {}
                break
        if not all(channel in planes for channel in (0, 1, 2)):
            continue
        pixels = np.zeros((canvas_height, canvas_width, 4), dtype=np.float32)
        y0, x0 = max(top, 0), max(left, 0)
        y1, x1 = min(bottom, canvas_height), min(right, canvas_width)
        if y1 <= y0 or x1 <= x0:
            continue
        window = (slice(y0 - top, y1 - top), slice(x0 - left, x1 - left))
        for index, channel in enumerate((0, 1, 2)):
            pixels[y0:y1, x0:x1, index] = planes[channel][window]
        pixels[y0:y1, x0:x1, 3] = planes[-1][window] if -1 in planes else 1.0
        layers.append({"name": record["name"], "pixels": pixels, "blend": record["blend"],
                       "opacity": record["opacity"], "visible": record["visible"]})
    return layers


def read_tiff_layers(path: str) -> List[Dict[str, Any]]:
    """Photoshop layers stored in a TIFF (written by Photoshop or by this pack). [] when none."""
    import tifffile
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        tag = page.tags.get(TIFF_TAG_IMAGE_SOURCE_DATA)
        if tag is None:
            return []
        value = tag.value
        block = bytes(value) if not isinstance(value, bytes) else value
        return parse_tiff_block(block, int(page.imagelength), int(page.imagewidth))
