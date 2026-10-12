"""Lossless full-resolution A1: raw rows, repeated rows, or row dictionaries."""
from __future__ import annotations


def encode_rows(pixels: bytes, width: int, height: int) -> bytes:
    if len(pixels) != width * height or any(p not in (0, 255) for p in pixels):
        raise ValueError("A1 input must contain exactly width*height binary pixels")
    rows = []
    for y in range(height):
        row = bytearray((width + 7) // 8)
        for x in range(width):
            if pixels[y * width + x]:
                row[x // 8] |= 0x80 >> (x % 8)
        rows.append(bytes(row))
    result = bytearray()
    index = 0
    while index < height:
        count = 1
        while index + count < height and rows[index + count] == rows[index] and count < 256:
            count += 1
        result.append(count - 1)
        result.extend(rows[index])
        index += count
    return bytes(result)


def encode_bitmap(pixels: bytes, width: int, height: int) -> bytes:
    runs = encode_rows(pixels, width, height)
    rows = []
    for y in range(height):
        row = bytearray((width + 7) // 8)
        for x in range(width):
            if pixels[y * width + x]:
                row[x // 8] |= 0x80 >> (x & 7)
        rows.append(bytes(row))
    dictionary = list(dict.fromkeys(rows))
    count = len(dictionary)
    bits = 1 if count <= 2 else 2 if count <= 4 else 4 if count <= 16 else 8
    indices = bytearray((height * bits + 7) // 8)
    for y, row in enumerate(rows):
        bit = y * bits
        indices[bit // 8] |= dictionary.index(row) << (8 - bits - bit % 8)
    candidates = (b"\0" + b"".join(rows), b"\1" + runs,
                  bytes([2, count]) + b"".join(dictionary) + indices)
    return min(candidates, key=len)


def decode_bitmap(blob: bytes, offset: int, width: int, height: int) -> bytes:
    if offset < 0 or offset >= len(blob) or width <= 0 or height <= 0:
        raise ValueError("invalid A1 bitmap bounds")
    codec = blob[offset]
    offset += 1
    if codec == 1:
        return decode_rows(blob, offset, width, height)
    row_bytes = (width + 7) // 8
    if codec == 0:
        if offset + row_bytes * height > len(blob):
            raise ValueError("raw A1 bitmap exceeds font blob")
        rows = [blob[offset + y * row_bytes:offset + (y + 1) * row_bytes] for y in range(height)]
    elif codec == 2:
        if offset >= len(blob) or not 1 <= blob[offset] <= height:
            raise ValueError("invalid A1 row dictionary")
        count = blob[offset]
        offset += 1
        bits = 1 if count <= 2 else 2 if count <= 4 else 4 if count <= 16 else 8
        indices = offset + count * row_bytes
        if indices + (height * bits + 7) // 8 > len(blob):
            raise ValueError("A1 row dictionary exceeds font blob")
        rows = []
        for y in range(height):
            bit = y * bits
            index = (blob[indices + bit // 8] >> (8 - bits - bit % 8)) & ((1 << bits) - 1)
            if index >= count:
                raise ValueError("invalid A1 row dictionary index")
            rows.append(blob[offset + index * row_bytes:offset + (index + 1) * row_bytes])
    else:
        raise ValueError("unknown A1 bitmap codec")
    return bytes(255 if row[x // 8] & (0x80 >> (x & 7)) else 0 for row in rows for x in range(width))


def tiles(pixels, width, height):
    """Exact 4x2 pixel chunks in column order, including zero edge padding."""
    return [sum(1 << (7 - yy * 4 - xx)
                for yy in range(2) for xx in range(4)
                if y + yy < height and x + xx < width and pixels[(y + yy) * width + x + xx])
            for x in range(0, width, 4) for y in range(0, height, 2)]


def encode_tiles(patterns, palette):
    result = bytearray([3])
    index = 0
    lookup = {tile: i for i, tile in enumerate(palette)}
    while index < len(patterns):
        tile = patterns[index]
        value = lookup[tile]
        result.extend([value] if value < 128 else [0x80, value])
        index += 1
        repeat = 0
        while index < len(patterns) and patterns[index] == tile:
            repeat += 1
            index += 1
        while repeat:
            count = min(repeat, 16)
            result.append(0xF0 + count - 1)
            repeat -= count
    return bytes(result)


def decode_tiles(blob, offset, width, height, palette_offset):
    if palette_offset < 0 or palette_offset + 2 > len(blob):
        raise ValueError("invalid A1 tile palette")
    count = int.from_bytes(blob[palette_offset:palette_offset + 2], "little")
    if not 1 <= count <= 256 or palette_offset + 2 + count > len(blob):
        raise ValueError("invalid A1 tile palette bounds")
    palette = blob[palette_offset + 2:palette_offset + 2 + count]
    result = bytearray(width * height)
    tile_rows, tile_count = (height + 1) // 2, ((width + 3) // 4) * ((height + 1) // 2)
    cursor, last = 0, None
    while cursor < tile_count:
        if not 0 <= offset < len(blob):
            raise ValueError("A1 tile stream exceeds font blob")
        token = blob[offset]
        offset += 1
        repeat = 1
        if token >= 0xF0:
            if last is None:
                raise ValueError("A1 tile repeat has no previous tile")
            repeat = (token & 15) + 1
            tile = last
        else:
            if token >= 128:
                if token != 128 or offset >= len(blob):
                    raise ValueError("invalid A1 tile index prefix")
                token = blob[offset]
                offset += 1
            if token >= count:
                raise ValueError("A1 tile index exceeds palette")
            tile = last = palette[token]
        if repeat > tile_count - cursor:
            raise ValueError("A1 tile run exceeds glyph")
        for _ in range(repeat):
            left, top = (cursor // tile_rows) * 4, (cursor % tile_rows) * 2
            for y in range(min(2, height - top)):
                for x in range(min(4, width - left)):
                    result[(top + y) * width + left + x] = 255 if tile & (0x80 >> (y * 4 + x)) else 0
            cursor += 1
    return bytes(result)


def decode_native_bitmap(blob, offset, width, height):
    if not 0 <= offset < len(blob):
        raise ValueError("invalid A1 bitmap offset")
    if blob[offset] == 3:
        if len(blob) < 24:
            raise ValueError("missing A1 palette metadata")
        palette_offset = int.from_bytes(blob[22:24], "little")
        return decode_tiles(blob, offset + 1, width, height, palette_offset)
    return decode_bitmap(blob, offset, width, height)


def decode_rows(blob: bytes, offset: int, width: int, height: int) -> bytes:
    result = bytearray()
    row_bytes = (width + 7) // 8
    rows = 0
    while rows < height:
        if offset < 0 or offset + 1 + row_bytes > len(blob):
            raise ValueError("A1 row exceeds font blob")
        count = blob[offset] + 1
        if count > height - rows:
            raise ValueError("A1 row run exceeds glyph height")
        offset += 1
        row = bytes(255 if blob[offset + x // 8] & (0x80 >> (x % 8)) else 0
                    for x in range(width))
        result.extend(row * count)
        offset += row_bytes
        rows += count
    return bytes(result)
