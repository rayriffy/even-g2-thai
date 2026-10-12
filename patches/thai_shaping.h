/* Finite Maitree ExtraLight GSUB/GPOS selections; see tools/maitree_shaping.py. */
#define NATIVE_COUNT 87u
#define ALT_COUNT 51u
#define GLYPH_COUNT (NATIVE_COUNT + ALT_COUNT)
#define TAG_START 0xF0000u
#define TAG_END 0xF1000u

static int glyph_index_for(uint32_t cp) {
    if(cp >= TAG_START && cp < TAG_END) {
        uint32_t index = (cp - TAG_START) & 255u;
        return index < GLYPH_COUNT ? (int)index : -1;
    }
    if(cp >= 0x0E01u && cp <= 0x0E3Au) return (int)(cp - 0x0E01u);
    if(cp == 0x0E3Fu) return 58;
    if(cp >= 0x0E40u && cp <= 0x0E5Bu) return (int)(cp - 0x0E40u + 59u);
    if(cp >= ALT_START && cp < ALT_START + ALT_COUNT) return (int)(NATIVE_COUNT + cp - ALT_START);
    return -1;
}

static int rounded_units(int value, uint32_t size) {
    int rounded = ((value < 0 ? -value : value) * (int)size + 500) / 1000;
    return value < 0 ? -rounded : rounded;
}

static int is_upper_mark(uint32_t cp) {
    return cp == 0x0E31u || (cp >= 0x0E34u && cp <= 0x0E37u) ||
           cp == 0x0E47u || (cp >= 0x0E4Cu && cp <= 0x0E4Eu);
}

static int is_combining_mark(uint32_t cp) {
    return is_upper_mark(cp) || (cp >= 0x0E38u && cp <= 0x0E3Au) ||
           (cp >= 0x0E48u && cp <= 0x0E4Bu);
}

static uint32_t previous_thai(const char *text, uint32_t end) {
    if(end < 3u) return 0;
    const uint8_t *p = (const uint8_t *)text + end - 3u;
    if(p[0] != 0xE0u || p[1] < 0xB8u || p[1] > 0xB9u || (p[2] & 0xC0u) != 0x80u) return 0;
    return 0x0E00u + ((uint32_t)(p[1] - 0xB8u) << 6) + (uint32_t)(p[2] - 0x80u);
}

static uint32_t shape_thai(const char *text, uint32_t cp, uint32_t next, uint32_t end) {
    if(cp < 0x0E01u || cp > 0x0E5Bu || end < 3u) return cp;
    uint32_t previous = previous_thai(text, end - 3u);
    uint32_t base = is_combining_mark(previous) && end >= 6u ? previous_thai(text, end - 6u) : previous;
    int tall = base == 0x0E1Bu || base == 0x0E1Du || base == 0x0E1Fu;
    uint32_t selected = cp, y_class = 0, x_class = 0;
    if((cp == 0x0E0Du || cp == 0x0E10u) && next >= 0x0E38u && next <= 0x0E3Au) {
        selected = ALT_START + (cp == 0x0E0Du ? 24u : 25u);
    }
    else if((cp == 0x0E0Eu || cp == 0x0E0Fu) && next >= 0x0E38u && next <= 0x0E3Au) {
        selected = ALT_START + (cp == 0x0E0Eu ? 44u : 45u);
    }
    else if(cp == 0x0E2Cu && (is_upper_mark(next) || (next >= 0x0E48u && next <= 0x0E4Bu) || next == SARA_AM)) {
        /* A known three-byte Thai tone permits the following scalar probe.
           previous_thai checks the first byte before reading past a NUL. */
        if(!(next >= 0x0E48u && next <= 0x0E4Bu && previous_thai(text, end + 6u) == 0x0E4Du)) {
            selected = ALT_START + 50u;
        }
    }
    else if(cp >= 0x0E38u && cp <= 0x0E3Au && (base == 0x0E0Eu || base == 0x0E0Fu)) {
        selected = ALT_START + 21u + cp - 0x0E38u;
    }
    else if(cp == SARA_AM) {
        if(tall) selected = ALT_START + 26u;
        else if(base == 0x0E09u) selected = ALT_START + 27u;
        else if(base == 0x0E13u || base == 0x0E19u) selected = ALT_START + 28u;
    }
    else if(cp == 0x0E4Du && previous >= 0x0E48u && previous <= 0x0E4Bu) {
        selected = ALT_START + 43u;
    }
    else if(cp >= 0x0E48u && cp <= 0x0E4Bu) {
        uint32_t tone = cp - 0x0E48u;
        if(next == 0x0E4Du) selected = ALT_START + (tall ? 39u : 35u) + tone;
        else if(next == SARA_AM) {
            selected = ALT_START + (tall ? 31u : 0u) + tone;
            y_class = 2;
        }
        else if(is_upper_mark(previous)) {
            selected = ALT_START + (tall ? (previous == 0x0E31u ? 46u : previous == 0x0E4Du ? 31u : 8u) : 0u) + tone;
            y_class = previous == 0x0E34u ? 1u : (previous == 0x0E36u || previous == 0x0E4Du) ? 2u : 0u;
        }
        else if(tall) selected = ALT_START + 4u + tone;
    }
    else if(cp == 0x0E4Cu && is_upper_mark(previous)) {
        selected = ALT_START + (tall ? 30u : 29u);
        y_class = previous == 0x0E34u ? 1u : (previous == 0x0E36u || previous == 0x0E4Du) ? 2u : 0u;
    }
    else if(tall && is_upper_mark(cp)) {
        static const uint16_t upper[] = {0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E47, 0x0E4C, 0x0E4D, 0x0E4E};
        for(uint32_t i = 0; i < 9u; i++) if(cp == upper[i]) selected = ALT_START + 12u + i;
    }
    if(is_combining_mark(cp) && selected != ALT_START + 43u) {
        x_class = base == 0x0E09u ? 1u : (base == 0x0E13u || base == 0x0E19u) ? 2u : 0u;
        if(base == 0x0E23u && cp >= 0x0E38u && cp <= 0x0E3Au) x_class = 3;
    }
    uint32_t group = x_class * 4u + y_class;
    if(group) selected = TAG_START + group * 256u + (uint32_t)glyph_index_for(selected);
    return selected;
}
