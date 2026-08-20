/* LVGL 9.3 Thai fallback for Even Realities G2 firmware 2.2.6.10. */
#include <stdbool.h>
#include <stdint.h>

#define THAI_START 0x0E00u
#define THAI_COUNT 0x80u
#define ALT_START 0xF700u
#define ALT_COUNT 4u
#define GLYPH_COUNT (THAI_COUNT + ALT_COUNT)
#define TONE_MARK_START 0x0E48u
#define SARA_AM 0x0E33u
#define SIZE_COUNT 8u
#define FONT_DSC_MAGIC 0xA11D0001u
#define FONT_BITMAP_MAGIC 0xA11D0002u
#define FONT_DATA_MAGIC 0xA11D0003u
#define LV_FONT_GLYPH_FORMAT_A8 0x08u
#define STOCK_CHAIN_BUILD_THUMB 0x0046CAE1u
#define STOCK_UTF8_NEXT_THUMB 0x00489DBDu
#define GLYPH_DSC_SIZE 32u
#define GLYPH_DSC_FORMAT_OFFSET 14u
#define GLYPH_DSC_GID_OFFSET 24u

typedef struct {
    uint32_t bitmap_offset;
    uint16_t advance;
    uint8_t box_w;
    uint8_t box_h;
    int8_t ofs_x;
    int8_t ofs_y;
    uint8_t row_bytes;
    uint8_t present;
} thai_glyph_t;

typedef void *(*stock_chain_build_fn)(void *configs, uint32_t count);
typedef uint32_t (*stock_utf8_next_fn)(const char *text, uint32_t *offset);
typedef void (*flush_cache_fn)(const void *draw_buf, const void *area);

/* Exact 32-bit lv_font_t word layout for the authenticated LVGL 9.3 build. */
#define FONT_WORDS(line_height, base_line, index) \
    {FONT_DSC_MAGIC, FONT_BITMAP_MAGIC, 0u, line_height, base_line, 0u, 0u, 0u, index}

__attribute__((used, aligned(4))) static const uint32_t thai_font_16[] = FONT_WORDS(25u, 8u, 0u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_20[] = FONT_WORDS(31u, 9u, 1u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_24[] = FONT_WORDS(37u, 11u, 2u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_28[] = FONT_WORDS(43u, 13u, 3u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_32[] = FONT_WORDS(49u, 15u, 4u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_36[] = FONT_WORDS(56u, 17u, 5u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_40[] = FONT_WORDS(61u, 18u, 6u);
__attribute__((used, aligned(4))) static const uint32_t thai_font_48[] = FONT_WORDS(73u, 22u, 7u);

__attribute__((used, section(".rodata.thai")))
static const volatile uint32_t thai_font_data_address = FONT_DATA_MAGIC;

static uint16_t read_u16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t read_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void write_u16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void write_u32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static const uint32_t *font_for_line_height(uint32_t height) {
    if(height < 28u) return thai_font_16;
    if(height < 34u) return thai_font_20;
    if(height < 40u) return thai_font_24;
    if(height < 46u) return thai_font_28;
    if(height < 53u) return thai_font_32;
    if(height < 59u) return thai_font_36;
    if(height < 67u) return thai_font_40;
    return thai_font_48;
}

static const thai_glyph_t *glyph_record(const uint32_t *font, uint32_t codepoint) {
    const uint8_t *data = (const uint8_t *)(uintptr_t)thai_font_data_address;
    uint32_t glyph_index;
    if(codepoint >= THAI_START && codepoint < THAI_START + THAI_COUNT) {
        glyph_index = codepoint - THAI_START;
    }
    else if(codepoint >= ALT_START && codepoint < ALT_START + ALT_COUNT) {
        glyph_index = THAI_COUNT + codepoint - ALT_START;
    }
    else {
        return 0;
    }
    uint32_t size_index = font[8];
    if(size_index >= SIZE_COUNT) return 0;
    uint32_t records_offset = read_u32(data + 12);
    uint32_t record_index = size_index * GLYPH_COUNT + glyph_index;
    return (const thai_glyph_t *)(data + records_offset + record_index * 12u);
}

__attribute__((used, noinline))
bool thai_get_glyph_dsc(const uint32_t *font, void *glyph_dsc,
                        uint32_t codepoint, uint32_t next_codepoint) {
    (void)next_codepoint;
    const thai_glyph_t *glyph = glyph_record(font, codepoint);
    if(!glyph || !glyph->present) return false;

    uint8_t *out = (uint8_t *)glyph_dsc;
    for(uint32_t i = 0; i < GLYPH_DSC_SIZE; i++) out[i] = 0;
    write_u32(out + 0, (uint32_t)(uintptr_t)font);
    write_u16(out + 4, glyph->advance);
    write_u16(out + 6, glyph->box_w);
    write_u16(out + 8, glyph->box_h);
    write_u16(out + 10, (uint16_t)(int16_t)glyph->ofs_x);
    write_u16(out + 12, (uint16_t)(int16_t)glyph->ofs_y);
    out[GLYPH_DSC_FORMAT_OFFSET] = LV_FONT_GLYPH_FORMAT_A8;
    write_u32(out + GLYPH_DSC_GID_OFFSET, codepoint);
    return true;
}

__attribute__((used, noinline))
const void *thai_get_glyph_bitmap(void *glyph_dsc, void *draw_buf) {
    if(!glyph_dsc || !draw_buf) return 0;
    uint8_t *dsc = (uint8_t *)glyph_dsc;
    const uint32_t *font = (const uint32_t *)(uintptr_t)read_u32(dsc);
    uint32_t codepoint = read_u32(dsc + GLYPH_DSC_GID_OFFSET);
    const thai_glyph_t *glyph = glyph_record(font, codepoint);
    if(!glyph || !glyph->present) return 0;

    const uint8_t *font_data = (const uint8_t *)(uintptr_t)thai_font_data_address;
    const uint8_t *source = font_data + glyph->bitmap_offset;
    uint8_t *draw = (uint8_t *)draw_buf;
    uint16_t stride = read_u16(draw + 8);
    uint8_t *target = (uint8_t *)(uintptr_t)read_u32(draw + 16);

    for(uint32_t y = 0; y < glyph->box_h; y++) {
        const uint8_t *row = source + y * glyph->row_bytes;
        uint8_t *out = target + y * stride;
        for(uint32_t x = 0; x < glyph->box_w; x++) {
            uint8_t packed = row[x >> 1];
            uint8_t alpha = (x & 1u) ? (packed & 0x0Fu) : (packed >> 4);
            out[x] = (uint8_t)(alpha * 17u);
        }
    }

    const uint32_t *handlers = (const uint32_t *)(uintptr_t)read_u32(draw + 24);
    if(handlers && handlers[4]) {
        ((flush_cache_fn)(uintptr_t)handlers[4])(draw_buf, 0);
    }
    return draw_buf;
}

__attribute__((used, noinline))
void thai_text_encoded_letter_next_2(const char *text, uint32_t *letter,
                                     uint32_t *letter_next, uint32_t *offset) {
    stock_utf8_next_fn stock_next = (stock_utf8_next_fn)(uintptr_t)STOCK_UTF8_NEXT_THUMB;
    uint32_t local_offset = 0;
    uint32_t *active_offset = offset ? offset : &local_offset;
    uint32_t current = stock_next(text, active_offset);
    uint32_t next = current ? stock_next(text + *active_offset, 0) : 0;
    if(current >= TONE_MARK_START && current < TONE_MARK_START + ALT_COUNT && next == SARA_AM) {
        current = ALT_START + current - TONE_MARK_START;
    }
    *letter = current;
    *letter_next = next;
}

__attribute__((used, noinline))
void *thai_chain_build(void *configs, uint32_t count) {
    stock_chain_build_fn stock = (stock_chain_build_fn)(uintptr_t)STOCK_CHAIN_BUILD_THUMB;
    uint8_t *chain = (uint8_t *)stock(configs, count);
    if(!chain) return 0;

    uint32_t *root = (uint32_t *)(uintptr_t)read_u32(chain);
    if(!root) return chain;
    uint32_t *last = root;
    for(uint32_t depth = 0; depth < 12u; depth++) {
        uint32_t next = last[7];
        if(!next) {
            last[7] = (uint32_t)(uintptr_t)font_for_line_height(root[3]);
            return chain;
        }
        last = (uint32_t *)(uintptr_t)next;
    }
    /* The authenticated chain has four entries. Preserve an unexpected longer
       chain instead of truncating it at the safety bound. */
    return chain;
}
