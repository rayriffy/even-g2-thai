"""Six-byte disk records; LVGL's 32-byte descriptor is unchanged."""
import struct
from maitree_shaping import record_index, GLYPH_COUNT

RECORD_SIZE = 6


def pack_record(blob, address, offset, advance, width, height, x, y):
    if not (0 <= offset < 65536 and 0 <= advance < 64 and 0 < width < 64 and
            0 < height < 64 and -32 <= x < 32 and -64 <= y < 64):
        raise ValueError("native glyph exceeds six-byte metric bounds")
    metrics = advance | (width << 6) | (height << 12) | ((x & 63) << 18) | ((y & 127) << 24)
    struct.pack_into("<HI", blob, address, offset, metrics)


def unpack_record(blob, address):
    offset, metrics = struct.unpack_from("<HI", blob, address)
    x, y = (metrics >> 18) & 63, (metrics >> 24) & 127
    return offset, metrics & 63, (metrics >> 6) & 63, (metrics >> 12) & 63, x - 64 if x >= 32 else x, y - 128 if y >= 64 else y


def glyph_record(blob, size_index, codepoint):
    return unpack_record(blob, 80 + (size_index * GLYPH_COUNT + record_index(codepoint)) * RECORD_SIZE)
