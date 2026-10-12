"""Finite Thai shaping for the pinned Maitree ExtraLight font.

Selections and font-unit offsets were checked against HarfBuzz 14.4.0.
Internal PUA glyphs never alter the input UTF-8 bytes or its advances.
"""
from font_blob import ALT_START, COMBINING_MARKS, UPPER_MARKS, VALID_CODEPOINTS

NATIVE = tuple(sorted(VALID_CODEPOINTS))
TALL = {0x0E1B, 0x0E1D, 0x0E1F}
UPPER = (0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37,
         0x0E47, 0x0E4C, 0x0E4D, 0x0E4E)
# glyph ID, x offset in font units; AM and blank are synthesized.
ALIASES = [(g, 0) for g in (722, 724, 727, 730)]
ALIASES += [(g, 15) for g in (756, 725, 728, 757)]
ALIASES += [(g, -89) for g in (722, 724, 727, 730)]
ALIASES += list(zip((720, 738, 740, 742, 744, 735, 733, 758, 736),
                   (38, 15, 15, 15, 15, 15, 15, 53, -89)))
ALIASES += [(g, 0) for g in (753, 755, 751, 442, 466)]
ALIASES += [("am", 1), ("am", 2), ("am", 3), (732, 0), (732, -89)]
ALIASES += [(g, -154) for g in (722, 724, 727, 730)]
ALIASES += [(g, 0) for g in (746, 747, 748, 749)]
ALIASES += [(g, 53) for g in (759, 760, 761, 762)]
ALIASES += [("blank", 0)]
ALIASES += [(436, 0), (438, 0)]  # Lower-vowel forms of ฎ and ฏ.
ALIASES += [(g, -189) for g in (722, 724, 727, 730)]  # Above tall MAI HAN-AKAT.
ALIASES += [(480, 0)]  # Short right finial of ฬ beneath upper marks.
ALT_COUNT = len(ALIASES)
GLYPH_COUNT = len(NATIVE) + ALT_COUNT
TAG_START, TAG_END = 0xF0000, 0xF1000


def record_index(cp):
    if TAG_START <= cp < TAG_END:
        index = (cp - TAG_START) & 255
        if index >= GLYPH_COUNT:
            raise ValueError("invalid contextual glyph index")
        return index
    if cp in VALID_CODEPOINTS:
        return NATIVE.index(cp)
    if ALT_START <= cp < ALT_START + ALT_COUNT:
        return len(NATIVE) + cp - ALT_START
    raise ValueError(f"unsupported Thai codepoint U+{cp:04X}")


def untag(cp):
    index = record_index(cp)
    return NATIVE[index] if index < len(NATIVE) else ALT_START + index - len(NATIVE)


def adjustment(cp):
    if not TAG_START <= cp < TAG_END:
        return 0, 0
    group = (cp - TAG_START) >> 8
    return (0, -38, -17, -25)[group >> 2], (0, -20, 10, 0)[group & 3]


def rounded_units(value, size):
    scaled = abs(value) * size
    return (1 if value >= 0 else -1) * ((scaled + 500) // 1000)


def shape_for_preview(text):
    raw = [ord(c) for c in text]
    result = []
    for i, current in enumerate(raw):
        previous = raw[i - 1] if i else 0
        following = raw[i + 1] if i + 1 < len(raw) else 0
        base = raw[i - 2] if previous in COMBINING_MARKS and i >= 2 else previous
        tall = base in TALL
        selected = current
        y_class = 0
        if current in (0x0E0D, 0x0E10) and 0x0E38 <= following <= 0x0E3A:
            selected = ALT_START + (24 if current == 0x0E0D else 25)
        elif current in (0x0E0E, 0x0E0F) and 0x0E38 <= following <= 0x0E3A:
            selected = ALT_START + (44 if current == 0x0E0E else 45)
        elif current == 0x0E2C and (following in UPPER_MARKS or 0x0E48 <= following <= 0x0E4B or following == 0x0E33):
            # The tone+nikhahit ligature precedes Maitree's short-finial lookup.
            after_next = raw[i + 2] if i + 2 < len(raw) else 0
            if not (0x0E48 <= following <= 0x0E4B and after_next == 0x0E4D):
                selected = ALT_START + 50
        elif 0x0E38 <= current <= 0x0E3A and base in (0x0E0E, 0x0E0F):
            selected = ALT_START + 21 + current - 0x0E38
        elif current == 0x0E33:
            if tall:
                selected = ALT_START + 26
            elif base == 0x0E09:
                selected = ALT_START + 27
            elif base in (0x0E13, 0x0E19):
                selected = ALT_START + 28
        elif current == 0x0E4D and 0x0E48 <= previous <= 0x0E4B:
            selected = ALT_START + 43
        elif 0x0E48 <= current <= 0x0E4B:
            tone = current - 0x0E48
            if following == 0x0E4D:
                selected = ALT_START + (39 if tall else 35) + tone
            elif following == 0x0E33:
                selected = ALT_START + (31 if tall else 0) + tone
                y_class = 2
            elif previous in UPPER_MARKS:
                selected = ALT_START + (46 if tall and previous == 0x0E31 else 31 if tall and previous == 0x0E4D else 8 if tall else 0) + tone
                y_class = 1 if previous == 0x0E34 else 2 if previous in (0x0E36, 0x0E4D) else 0
            elif tall:
                selected = ALT_START + 4 + tone
        elif current == 0x0E4C and previous in UPPER_MARKS:
            selected = ALT_START + (30 if tall else 29)
            y_class = 1 if previous == 0x0E34 else 2 if previous in (0x0E36, 0x0E4D) else 0
        elif tall and current in UPPER:
            selected = ALT_START + 12 + UPPER.index(current)
        x_class = 0
        # AM's nikhahit moves independently of its following SARA AA.
        if current in COMBINING_MARKS and selected != ALT_START + 43:
            x_class = 1 if base == 0x0E09 else 2 if base in (0x0E13, 0x0E19) else 0
            if base == 0x0E23 and 0x0E38 <= current <= 0x0E3A:
                x_class = 3
        group = x_class * 4 + y_class
        if group:
            selected = TAG_START + group * 256 + record_index(selected)
        result.append(selected)
    return result
