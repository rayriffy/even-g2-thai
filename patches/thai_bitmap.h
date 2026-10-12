/* All codecs preserve full-resolution A1 pixels and write caller-owned A8. */
static int decode_a1(const uint8_t *font_data, const thai_glyph_t *glyph,
                     uint8_t *target, uint16_t stride) {
    const uint8_t *source = font_data + glyph->bitmap_offset;
    uint32_t codec = *source++;
    if(codec == 3u) {
        const uint8_t *palette = font_data + read_u16(font_data + 22);
        uint32_t count = read_u16(palette);
        if(!count || count > 256u) return 0;
        palette += 2;
        uint32_t rows = ((uint32_t)glyph->box_h + 1u) / 2u;
        uint32_t total = (((uint32_t)glyph->box_w + 3u) / 4u) * rows;
        uint32_t cursor = 0, last = 0, have_last = 0;
        while(cursor < total) {
            uint32_t token = *source++, repeat = 1, tile;
            if(token >= 0xF0u) {
                if(!have_last) return 0;
                repeat = (token & 15u) + 1u;
                tile = last;
            }
            else {
                if(token >= 128u) {
                    if(token != 128u) return 0;
                    token = *source++;
                }
                if(token >= count) return 0;
                last = tile = palette[token];
                have_last = 1;
            }
            if(repeat > total - cursor) return 0;
            while(repeat--) {
                uint32_t left = (cursor / rows) * 4u, top = (cursor % rows) * 2u;
                for(uint32_t y = 0; y < 2u && top + y < glyph->box_h; y++) {
                    for(uint32_t x = 0; x < 4u && left + x < glyph->box_w; x++) {
                        target[(top + y) * stride + left + x] =
                            (tile & (0x80u >> (y * 4u + x))) ? 255u : 0u;
                    }
                }
                cursor++;
            }
        }
        return 1;
    }
    uint32_t row_bytes = ((uint32_t)glyph->box_w + 7u) / 8u;
    uint32_t count = 0, bits = 0;
    const uint8_t *dictionary = 0, *indices = 0;
    if(codec == 2u) {
        count = *source++;
        if(!count || count > glyph->box_h) return 0;
        bits = count <= 2u ? 1u : count <= 4u ? 2u : count <= 16u ? 4u : 8u;
        dictionary = source;
        indices = source + count * row_bytes;
    }
    else if(codec > 1u) return 0;
    for(uint32_t y = 0; y < glyph->box_h;) {
        uint32_t repeat = 1;
        const uint8_t *row = source;
        if(codec == 1u) {
            repeat = (uint32_t)*source++ + 1u;
            if(repeat > glyph->box_h - y) return 0;
            row = source;
        }
        else if(codec == 2u) {
            uint32_t bit = y * bits;
            uint32_t index = (indices[bit / 8u] >> (8u - bits - bit % 8u)) & ((1u << bits) - 1u);
            if(index >= count) return 0;
            row = dictionary + index * row_bytes;
        }
        uint8_t *out = target + y * stride;
        for(uint32_t x = 0; x < glyph->box_w; x++) {
            out[x] = (row[x / 8u] & (0x80u >> (x & 7u))) ? 255u : 0u;
        }
        if(codec != 2u) source += row_bytes;
        for(uint32_t i = 1; i < repeat; i++) copy_bytes(out + i * stride, out, glyph->box_w);
        y += repeat;
    }
    return 1;
}
