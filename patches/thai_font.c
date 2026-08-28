/* LVGL 9.3 Thai fallback for Even Realities G2 firmware 2.2.9.22. */
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
#define STOCK_CHAIN_BUILD_THUMB 0x00470989u
#define LV_MALLOC_THUMB 0x00458383u
/* The stock letter helper loads its UTF-8 decoder through the double pointer
   at 0x00491F14 (slot address, then function pointer) so it always matches
   the firmware's active text encoder. Calling any hardcoded entry instead
   breaks that contract: the helper at 0x00491E24 dereferences its offset
   argument unconditionally and faults when the lookahead pass passes NULL,
   which is exactly how the stock helper invokes its decoder. */
#define STOCK_DECODE_SLOT_INDIRECT 0x00491F14u
#define WRITABLE_RAM_BASE 0x20000000u
#define WRITABLE_RAM_END 0x20080000u
#define GLYPH_DSC_SIZE 32u
#define GLYPH_DSC_FORMAT_OFFSET 14u
#define GLYPH_DSC_GID_OFFSET 24u
#define THAI_RUNTIME_MAGIC 0x43414854u
#define THAI_CACHE_SLOTS 4u
#define THAI_CACHE_BUDGET 8192u
#define FONT_WORD_COUNT 9u

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
typedef uint32_t (*stock_decode_fn)(const char *text, uint32_t *offset);
typedef void (*flush_cache_fn)(const void *draw_buf, const void *area);
typedef void *(*lv_malloc_fn)(uint32_t size);
typedef uint32_t alias_u32_t __attribute__((__may_alias__));

typedef struct {
    uint32_t codepoint;
    uint32_t stamp;
} thai_cache_slot_t;

typedef struct {
    uint32_t font[FONT_WORD_COUNT];
    uint32_t magic;
    uint32_t clock;
    uint16_t slot_bytes;
    uint8_t slot_count;
    uint8_t busy;
    thai_cache_slot_t slots[THAI_CACHE_SLOTS];
    uint8_t pixels[];
} thai_runtime_font_t;

static const uint8_t a4_to_a8[16] = {
    0u, 17u, 34u, 51u, 68u, 85u, 102u, 119u,
    136u, 153u, 170u, 187u, 204u, 221u, 238u, 255u,
};

#define A4_TO_A8_PAIR(first, second) \
    ((uint16_t)((uint16_t)(first) * 17u | ((uint16_t)(second) * 17u << 8)))
#define A4_TO_A8_PAIR_ROW(first) \
    A4_TO_A8_PAIR(first, 0u), A4_TO_A8_PAIR(first, 1u), \
    A4_TO_A8_PAIR(first, 2u), A4_TO_A8_PAIR(first, 3u), \
    A4_TO_A8_PAIR(first, 4u), A4_TO_A8_PAIR(first, 5u), \
    A4_TO_A8_PAIR(first, 6u), A4_TO_A8_PAIR(first, 7u), \
    A4_TO_A8_PAIR(first, 8u), A4_TO_A8_PAIR(first, 9u), \
    A4_TO_A8_PAIR(first, 10u), A4_TO_A8_PAIR(first, 11u), \
    A4_TO_A8_PAIR(first, 12u), A4_TO_A8_PAIR(first, 13u), \
    A4_TO_A8_PAIR(first, 14u), A4_TO_A8_PAIR(first, 15u)
static const uint16_t a4_to_a8_pair[256] = {
    A4_TO_A8_PAIR_ROW(0u), A4_TO_A8_PAIR_ROW(1u),
    A4_TO_A8_PAIR_ROW(2u), A4_TO_A8_PAIR_ROW(3u),
    A4_TO_A8_PAIR_ROW(4u), A4_TO_A8_PAIR_ROW(5u),
    A4_TO_A8_PAIR_ROW(6u), A4_TO_A8_PAIR_ROW(7u),
    A4_TO_A8_PAIR_ROW(8u), A4_TO_A8_PAIR_ROW(9u),
    A4_TO_A8_PAIR_ROW(10u), A4_TO_A8_PAIR_ROW(11u),
    A4_TO_A8_PAIR_ROW(12u), A4_TO_A8_PAIR_ROW(13u),
    A4_TO_A8_PAIR_ROW(14u), A4_TO_A8_PAIR_ROW(15u),
};
#undef A4_TO_A8_PAIR_ROW
#undef A4_TO_A8_PAIR

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

static int writable_ram_range(const void *pointer, uint32_t size) {
    uintptr_t address = (uintptr_t)pointer;
    uint32_t capacity = WRITABLE_RAM_END - WRITABLE_RAM_BASE;
    return size <= capacity && address >= WRITABLE_RAM_BASE &&
           address <= WRITABLE_RAM_END - size;
}

static void copy_bytes(uint8_t *destination, const uint8_t *source, uint32_t count) {
    if((((uintptr_t)destination | (uintptr_t)source) & 3u) == 0u) {
        while(count >= 4u) {
            *(alias_u32_t *)(uintptr_t)destination =
                *(const alias_u32_t *)(uintptr_t)source;
            destination += 4;
            source += 4;
            count -= 4u;
        }
    }
    while(count--) *destination++ = *source++;
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

static uint16_t cache_slot_bytes_for_font(const uint32_t *font) {
    const uint8_t *data = (const uint8_t *)(uintptr_t)thai_font_data_address;
    uint32_t size_index = font[8];
    if(size_index >= SIZE_COUNT) return 0;
    uint32_t records_offset = read_u32(data + 12);
    uint32_t largest = 0;
    for(uint32_t index = 0; index < GLYPH_COUNT; index++) {
        const thai_glyph_t *glyph = (const thai_glyph_t *)(
            data + records_offset + (size_index * GLYPH_COUNT + index) * 12u);
        if(!glyph->present) continue;
        uint32_t cache_stride = ((uint32_t)glyph->box_w + 3u) & ~3u;
        uint32_t bytes = cache_stride * glyph->box_h;
        if(bytes > largest) largest = bytes;
    }
    if(!largest || largest > THAI_CACHE_BUDGET || largest > 0xFFFFu) return 0;
    return (uint16_t)largest;
}

static thai_runtime_font_t *runtime_font_from(const uint32_t *font) {
    if(!writable_ram_range(font, sizeof(thai_runtime_font_t))) return 0;
    thai_runtime_font_t *runtime = (thai_runtime_font_t *)(uintptr_t)font;
    if(runtime->magic != THAI_RUNTIME_MAGIC || !runtime->slot_bytes ||
       !runtime->slot_count || runtime->slot_count > THAI_CACHE_SLOTS) return 0;
    uint32_t cache_bytes = (uint32_t)runtime->slot_bytes * runtime->slot_count;
    if(cache_bytes > THAI_CACHE_BUDGET ||
       !writable_ram_range(runtime, sizeof(thai_runtime_font_t) + cache_bytes)) return 0;
    return runtime;
}

static const uint32_t *runtime_font_create(const uint32_t *base_font) {
    uint16_t slot_bytes = cache_slot_bytes_for_font(base_font);
    if(!slot_bytes) return base_font;
    uint32_t slot_count = THAI_CACHE_BUDGET / slot_bytes;
    if(slot_count > THAI_CACHE_SLOTS) slot_count = THAI_CACHE_SLOTS;
    if(!slot_count) return base_font;
    uint32_t total = sizeof(thai_runtime_font_t) + slot_count * slot_bytes;
    lv_malloc_fn allocate = (lv_malloc_fn)(uintptr_t)LV_MALLOC_THUMB;
    thai_runtime_font_t *runtime = (thai_runtime_font_t *)allocate(total);
    if(!runtime || !writable_ram_range(runtime, total)) return base_font;
    uint8_t *bytes = (uint8_t *)runtime;
    for(uint32_t index = 0; index < total; index++) bytes[index] = 0;
    for(uint32_t index = 0; index < FONT_WORD_COUNT; index++) {
        runtime->font[index] = base_font[index];
    }
    runtime->magic = THAI_RUNTIME_MAGIC;
    runtime->slot_bytes = slot_bytes;
    runtime->slot_count = (uint8_t)slot_count;
    return runtime->font;
}

static uint8_t *cache_pixels(thai_runtime_font_t *runtime, uint32_t slot) {
    return runtime->pixels + slot * runtime->slot_bytes;
}

static uint32_t cache_tick(thai_runtime_font_t *runtime) {
    runtime->clock++;
    if(!runtime->clock) {
        runtime->clock = 1u;
        for(uint32_t index = 0; index < runtime->slot_count; index++) {
            runtime->slots[index].stamp = 0;
        }
    }
    return runtime->clock;
}

static int cache_restore(thai_runtime_font_t *runtime, const thai_glyph_t *glyph,
                         uint32_t codepoint, uint8_t *target, uint16_t stride) {
    if(!runtime || runtime->busy || stride < glyph->box_w) return 0;
    uint32_t cache_stride = ((uint32_t)glyph->box_w + 3u) & ~3u;
    if(cache_stride * glyph->box_h > runtime->slot_bytes) return 0;
    for(uint32_t slot = 0; slot < runtime->slot_count; slot++) {
        if(runtime->slots[slot].codepoint != codepoint) continue;
        runtime->busy = 1u;
        const uint8_t *source = cache_pixels(runtime, slot);
        for(uint32_t y = 0; y < glyph->box_h; y++) {
            copy_bytes(target + y * stride, source + y * cache_stride, glyph->box_w);
        }
        runtime->slots[slot].stamp = cache_tick(runtime);
        runtime->busy = 0u;
        return 1;
    }
    return 0;
}

static void cache_store(thai_runtime_font_t *runtime, const thai_glyph_t *glyph,
                        uint32_t codepoint, const uint8_t *source, uint16_t stride) {
    if(!runtime || runtime->busy || stride < glyph->box_w) return;
    uint32_t cache_stride = ((uint32_t)glyph->box_w + 3u) & ~3u;
    if(cache_stride * glyph->box_h > runtime->slot_bytes) return;
    uint32_t selected = 0;
    for(uint32_t slot = 0; slot < runtime->slot_count; slot++) {
        if(!runtime->slots[slot].codepoint) {
            selected = slot;
            break;
        }
        if(runtime->slots[slot].stamp < runtime->slots[selected].stamp) selected = slot;
    }
    runtime->busy = 1u;
    uint8_t *destination = cache_pixels(runtime, selected);
    for(uint32_t y = 0; y < glyph->box_h; y++) {
        copy_bytes(destination + y * cache_stride, source + y * stride, glyph->box_w);
        for(uint32_t x = glyph->box_w; x < cache_stride; x++) {
            destination[y * cache_stride + x] = 0;
        }
    }
    runtime->slots[selected].codepoint = codepoint;
    runtime->slots[selected].stamp = cache_tick(runtime);
    runtime->busy = 0u;
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
    if(!target || stride < glyph->box_w) return 0;

    thai_runtime_font_t *runtime = runtime_font_from(font);
    if(cache_restore(runtime, glyph, codepoint, target, stride)) {
        const uint32_t *handlers = (const uint32_t *)(uintptr_t)read_u32(draw + 24);
        if(handlers && handlers[4]) {
            ((flush_cache_fn)(uintptr_t)handlers[4])(draw_buf, 0);
        }
        return draw_buf;
    }

    for(uint32_t y = 0; y < glyph->box_h; y++) {
        const uint8_t *row = source + y * glyph->row_bytes;
        uint8_t *out = target + y * stride;
        uint32_t pairs = glyph->box_w >> 1;
        if(((uintptr_t)out & 1u) == 0u) {
            uint16_t *pair_out = (uint16_t *)(uintptr_t)out;
            while(pairs--) {
                *pair_out++ = a4_to_a8_pair[*row++];
            }
            out = (uint8_t *)(uintptr_t)pair_out;
        }
        else {
            while(pairs--) {
                uint8_t packed = *row++;
                *out++ = a4_to_a8[packed >> 4];
                *out++ = a4_to_a8[packed & 0x0Fu];
            }
        }
        if(glyph->box_w & 1u) {
            *out = a4_to_a8[*row >> 4];
        }
    }

    cache_store(runtime, glyph, codepoint, target, stride);

    const uint32_t *handlers = (const uint32_t *)(uintptr_t)read_u32(draw + 24);
    if(handlers && handlers[4]) {
        ((flush_cache_fn)(uintptr_t)handlers[4])(draw_buf, 0);
    }
    return draw_buf;
}

static stock_decode_fn stock_decoder(void) {
    uint32_t storage = read_u32((const uint8_t *)(uintptr_t)STOCK_DECODE_SLOT_INDIRECT);
    if(!storage) return 0;
    return (stock_decode_fn)(uintptr_t)read_u32((const uint8_t *)(uintptr_t)storage);
}

static int is_upper_mark(uint32_t codepoint) {
    return codepoint == 0x0E31u ||
           (codepoint >= 0x0E34u && codepoint <= 0x0E37u) ||
           codepoint == 0x0E47u || codepoint == 0x0E4Cu ||
           codepoint == 0x0E4Du || codepoint == 0x0E4Eu;
}

__attribute__((used, noinline))
void thai_text_encoded_letter_next_2(const char *text, uint32_t *letter,
                                     uint32_t *letter_next, uint32_t *offset) {
    stock_decode_fn decode = stock_decoder();
    uint32_t local_offset = 0;
    uint32_t *active_offset = offset ? offset : &local_offset;
    uint32_t current = 0;
    uint32_t next = 0;
    if(decode) current = decode(text, active_offset);
    if(decode && current) next = decode(text + *active_offset, 0);
    if(current >= TONE_MARK_START && current < TONE_MARK_START + ALT_COUNT) {
        int raise_tone = next == SARA_AM;
        if(!raise_tone && *active_offset >= 6u) {
            const uint8_t *previous = (const uint8_t *)text + *active_offset - 6u;
            if(previous[0] == 0xE0u &&
               previous[1] >= 0xB8u && previous[1] <= 0xB9u &&
               (previous[2] & 0xC0u) == 0x80u) {
                uint32_t codepoint = 0x0E00u +
                                     ((uint32_t)(previous[1] - 0xB8u) << 6) +
                                     (uint32_t)(previous[2] - 0x80u);
                raise_tone = is_upper_mark(codepoint);
            }
        }
        if(raise_tone) current = ALT_START + current - TONE_MARK_START;
    }
    *letter = current;
    *letter_next = next;
}

static int is_thai_font(const uint32_t *font) {
    if(font == thai_font_16 || font == thai_font_20 ||
           font == thai_font_24 || font == thai_font_28 ||
           font == thai_font_32 || font == thai_font_36 ||
           font == thai_font_40 || font == thai_font_48) return 1;
    return runtime_font_from(font) != 0;
}

static int writable_ram_node(const uint32_t *node) {
    return writable_ram_range(node, 32u);
}

/* Appending must be idempotent: the stock builder runs again whenever a new
   dashboard is created, and a previous append persists in the stock font
   objects. Walking into an injected Thai font and storing its fallback word
   would write into const firmware flash and reset the lens, so every node is
   checked before any mutation and cycles or over-long chains are left alone. */
__attribute__((used, noinline))
void *thai_chain_append(void *chain_ptr) {
    uint32_t *root = (uint32_t *)(uintptr_t)read_u32((const uint8_t *)chain_ptr);
    if(!root || is_thai_font(root)) return chain_ptr;
    uint32_t *last = root;
    for(uint32_t depth = 1u; depth < 12u; depth++) {
        uint32_t next = last[7];
        if(!next) {
            /* Only a verified writable stock node may receive the fallback
               pointer; XIP or flash tails are left untouched. */
            if(!writable_ram_node(last)) return chain_ptr;
            const uint32_t *base_font = font_for_line_height(root[3]);
            last[7] = (uint32_t)(uintptr_t)runtime_font_create(base_font);
            return chain_ptr;
        }
        if(is_thai_font((const uint32_t *)(uintptr_t)next)) return chain_ptr;
        last = (uint32_t *)(uintptr_t)next;
    }
    return chain_ptr;
}

__attribute__((used, noinline))
void *thai_chain_build(void *configs, uint32_t count) {
    stock_chain_build_fn stock = (stock_chain_build_fn)(uintptr_t)STOCK_CHAIN_BUILD_THUMB;
    uint8_t *chain = (uint8_t *)stock(configs, count);
    if(!chain) return 0;
    return thai_chain_append(chain);
}
