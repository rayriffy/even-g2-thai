/* Stock 2.3.0.24 lv_font_get_glyph_dsc entry is exactly one PUSH.W.
   Replay it, then resume at +4 without changing arguments or the return LR.
   The generator authenticates the complete entry anchor before hooking it. */
__attribute__((used, naked, noinline))
static bool stock_font_get_glyph_dsc(const uint32_t *font, void *glyph_dsc,
                                    uint32_t codepoint, uint32_t next_codepoint) {
    __asm volatile(
        "push.w {r1-r11, lr}\n"
        "movw r12, #0xa36d\n"
        "movt r12, #0x004e\n"
        "bx r12\n");
}

/* Patched to the exact injected descriptor callback, identifying both our
   immutable fonts and runtime clones with one load/compare per chain node. */
__attribute__((used))
static const volatile uint32_t thai_dsc_callback_address = 0xA11D0004u;

__attribute__((used, noinline))
static bool thai_lookup_covered(const uint32_t *font, void *glyph_dsc,
                                uint32_t codepoint, uint32_t next_codepoint) {
    /* Only covered Thai/alternate glyphs in a chain containing our font
       bypass native font misses. All other requests retain the stock path,
       including placeholders, kerning, release ownership and assertions. */
    if(glyph_dsc) {
        const uint32_t *candidate = font;
        for(uint32_t depth = 0; candidate && depth < 12u; depth++) {
            if(candidate[0] == thai_dsc_callback_address) {
                if(thai_get_glyph_dsc(candidate, glyph_dsc, codepoint, next_codepoint)) {
                    return true;
                }
                break;
            }
            candidate = (const uint32_t *)(uintptr_t)candidate[7];
        }
    }
    return stock_font_get_glyph_dsc(font, glyph_dsc, codepoint, next_codepoint);
}

/* Most labels contain ASCII. Tail-dispatch before a C prologue so they pay
   only the range guard and trampoline, with no extra saved-register frame. */
__attribute__((used, naked, noinline))
bool thai_font_get_glyph_dsc(const uint32_t *font, void *glyph_dsc,
                            uint32_t codepoint, uint32_t next_codepoint) {
    __asm volatile(
        "cmp r2, #0x80\n"
        "bhs 1f\n"
        "b.w stock_font_get_glyph_dsc\n"
        "1: lsr.w r12, r2, #7\n"
        "cmp r12, #0x1c\n"
        "beq 2f\n"
        "movw r12, #0xf700\n"
        "eor.w r12, r12, r2\n"
        "cmp r12, #4\n"
        "blo 2f\n"
        "b.w stock_font_get_glyph_dsc\n"
        "2: b.w thai_lookup_covered\n");
}
