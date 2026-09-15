; Stock SHA-256: 927879057685a4147c6ba1fe33e5f3740d3cc48f87141a9039204d94516e65b8
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; font-manager background chain call
004718f8  0421       movs     r1, #4
004718fa  7748       ldr      r0, [pc, #0x1dc]
004718fc  fff736fb   bl       #0x470f6c
00471900  2060       str      r0, [r4]
00471902  2068       ldr      r0, [r4]
00471904  0028       cmp      r0, #0
00471906  05d0       beq      #0x471914
00471908  2068       ldr      r0, [r4]
0047190a  fff76afd   bl       #0x4713e2
0047190e  7349       ldr      r1, [pc, #0x1cc]
00471910  0860       str      r0, [r1]
00471912  1fe0       b        #0x471954

; font-manager foreground chain call
00471956  0421       movs     r1, #4
00471958  6548       ldr      r0, [pc, #0x194]
0047195a  fff707fb   bl       #0x470f6c
0047195e  2060       str      r0, [r4]
00471960  2068       ldr      r0, [r4]
00471962  0028       cmp      r0, #0
00471964  05d0       beq      #0x471972
00471966  2068       ldr      r0, [r4]
00471968  fff73bfd   bl       #0x4713e2
0047196c  6149       ldr      r1, [pc, #0x184]
0047196e  0860       str      r0, [r1]
00471970  1fe0       b        #0x4719b2

; XIP acquire and release guards
004760ea  80b5       push     {r7, lr}
004760ec  fff7a0ff   bl       #0x476030
004760f0  dff8980c   ldr.w    r0, [pc, #0xc98]
004760f4  0078       ldrb     r0, [r0]
004760f6  0128       cmp      r0, #1
004760f8  01d0       beq      #0x4760fe
004760fa  fff75cff   bl       #0x475fb6
004760fe  01bd       pop      {r0, pc}
00476100  80b5       push     {r7, lr}
00476102  dff8880c   ldr.w    r0, [pc, #0xc88]
00476106  0078       ldrb     r0, [r0]
00476108  0128       cmp      r0, #1
0047610a  01d0       beq      #0x476110
0047610c  fff743ff   bl       #0x475f96
00476110  fff7bdff   bl       #0x47608e
00476114  01bd       pop      {r0, pc}

; bitmap dispatch
004e8ce2  feb5       push     {r1, r2, r3, r4, r5, r6, r7, lr}
004e8ce4  0500       movs     r5, r0
004e8ce6  0e00       movs     r6, r1
004e8ce8  2c68       ldr      r4, [r5]
004e8cea  002c       cmp      r4, #0
004e8cec  10d1       bne      #0x4e8d10
004e8cee  8e48       ldr      r0, [pc, #0x238]
004e8cf0  0290       str      r0, [sp, #8]
004e8cf2  8e48       ldr      r0, [pc, #0x238]
004e8cf4  0190       str      r0, [sp, #4]
004e8cf6  8e48       ldr      r0, [pc, #0x238]
004e8cf8  0090       str      r0, [sp]
004e8cfa  8e4b       ldr      r3, [pc, #0x238]
004e8cfc  3622       movs     r2, #0x36
004e8cfe  8e49       ldr      r1, [pc, #0x238]
004e8d00  0320       movs     r0, #3
004e8d02  67f7c3f8   bl       #0x44fe8c
004e8d06  0020       movs     r0, #0
004e8d08  5ff0ff31   movs.w   r1, #-1
004e8d0c  0860       str      r0, [r1]
004e8d0e  fae7       b        #0x4e8d06
004e8d10  8a4f       ldr      r7, [pc, #0x228]
004e8d12  a069       ldr      r0, [r4, #0x18]
004e8d14  b842       cmp      r0, r7
004e8d16  01d3       blo      #0x4e8d1c
004e8d18  8df7e7f9   bl       #0x4760ea
004e8d1c  3100       movs     r1, r6
004e8d1e  2800       movs     r0, r5
004e8d20  6268       ldr      r2, [r4, #4]
004e8d22  9047       blx      r2
004e8d24  0500       movs     r5, r0
004e8d26  a069       ldr      r0, [r4, #0x18]
004e8d28  b842       cmp      r0, r7
004e8d2a  01d3       blo      #0x4e8d30
004e8d2c  8df7e8f9   bl       #0x476100
004e8d30  2800       movs     r0, r5
004e8d32  febd       pop      {r1, r2, r3, r4, r5, r6, r7, pc}

; glyph release
004e8d34  7fb5       push     {r0, r1, r2, r3, r4, r5, r6, lr}
004e8d36  0500       movs     r5, r0
004e8d38  002d       cmp      r5, #0
004e8d3a  10d1       bne      #0x4e8d5e
004e8d3c  7a48       ldr      r0, [pc, #0x1e8]
004e8d3e  0290       str      r0, [sp, #8]
004e8d40  7f48       ldr      r0, [pc, #0x1fc]
004e8d42  0190       str      r0, [sp, #4]
004e8d44  7a48       ldr      r0, [pc, #0x1e8]
004e8d46  0090       str      r0, [sp]
004e8d48  7e4b       ldr      r3, [pc, #0x1f8]
004e8d4a  4322       movs     r2, #0x43
004e8d4c  7a49       ldr      r1, [pc, #0x1e8]
004e8d4e  0320       movs     r0, #3
004e8d50  67f79cf8   bl       #0x44fe8c
004e8d54  0020       movs     r0, #0
004e8d56  5ff0ff31   movs.w   r1, #-1
004e8d5a  0860       str      r0, [r1]
004e8d5c  fae7       b        #0x4e8d54
004e8d5e  e869       ldr      r0, [r5, #0x1c]
004e8d60  0028       cmp      r0, #0
004e8d62  14d0       beq      #0x4e8d8e
004e8d64  2c68       ldr      r4, [r5]
004e8d66  002c       cmp      r4, #0
004e8d68  11d0       beq      #0x4e8d8e
004e8d6a  a068       ldr      r0, [r4, #8]
004e8d6c  0028       cmp      r0, #0
004e8d6e  0ed0       beq      #0x4e8d8e
004e8d70  724e       ldr      r6, [pc, #0x1c8]
004e8d72  a069       ldr      r0, [r4, #0x18]
004e8d74  b042       cmp      r0, r6
004e8d76  01d3       blo      #0x4e8d7c
004e8d78  8df7b7f9   bl       #0x4760ea
004e8d7c  2900       movs     r1, r5
004e8d7e  2000       movs     r0, r4
004e8d80  a268       ldr      r2, [r4, #8]
004e8d82  9047       blx      r2
004e8d84  a069       ldr      r0, [r4, #0x18]
004e8d86  b042       cmp      r0, r6
004e8d88  01d3       blo      #0x4e8d8e
004e8d8a  8df7b9f9   bl       #0x476100
004e8d8e  7fbd       pop      {r0, r1, r2, r3, r4, r5, r6, pc}

; glyph descriptor fallback dispatch
004e8d90  2de9fe4f   push.w   {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}
004e8d94  0700       movs     r7, r0
004e8d96  9146       mov      sb, r2
004e8d98  9846       mov      r8, r3
004e8d9a  002f       cmp      r7, #0
004e8d9c  10d1       bne      #0x4e8dc0
004e8d9e  6248       ldr      r0, [pc, #0x188]
004e8da0  0290       str      r0, [sp, #8]
004e8da2  6248       ldr      r0, [pc, #0x188]
004e8da4  0190       str      r0, [sp, #4]
004e8da6  6248       ldr      r0, [pc, #0x188]
004e8da8  0090       str      r0, [sp]
004e8daa  674b       ldr      r3, [pc, #0x19c]
004e8dac  5a22       movs     r2, #0x5a
004e8dae  6249       ldr      r1, [pc, #0x188]
004e8db0  0320       movs     r0, #3
004e8db2  67f76bf8   bl       #0x44fe8c
004e8db6  0020       movs     r0, #0
004e8db8  5ff0ff31   movs.w   r1, #-1
004e8dbc  0860       str      r0, [r1]
004e8dbe  fae7       b        #0x4e8db6
004e8dc0  0e00       movs     r6, r1
004e8dc2  002e       cmp      r6, #0
004e8dc4  10d1       bne      #0x4e8de8
004e8dc6  5848       ldr      r0, [pc, #0x160]
004e8dc8  0290       str      r0, [sp, #8]
004e8dca  6048       ldr      r0, [pc, #0x180]
004e8dcc  0190       str      r0, [sp, #4]
004e8dce  5848       ldr      r0, [pc, #0x160]
004e8dd0  0090       str      r0, [sp]
004e8dd2  5d4b       ldr      r3, [pc, #0x174]
004e8dd4  5b22       movs     r2, #0x5b
004e8dd6  5849       ldr      r1, [pc, #0x160]
004e8dd8  0320       movs     r0, #3
004e8dda  67f757f8   bl       #0x44fe8c
004e8dde  0020       movs     r0, #0
004e8de0  5ff0ff31   movs.w   r1, #-1
004e8de4  0860       str      r0, [r1]
004e8de6  fae7       b        #0x4e8dde
004e8de8  0024       movs     r4, #0
004e8dea  3d00       movs     r5, r7
004e8dec  2021       movs     r1, #0x20
004e8dee  3000       movs     r0, r6
004e8df0  fff736ff   bl       #0x4e8c60
004e8df4  25e0       b        #0x4e8e42
004e8df6  dff844a1   ldr.w    sl, [pc, #0x144]
004e8dfa  a869       ldr      r0, [r5, #0x18]
004e8dfc  5045       cmp      r0, sl
004e8dfe  01d3       blo      #0x4e8e04
004e8e00  8df773f9   bl       #0x4760ea
004e8e04  287d       ldrb     r0, [r5, #0x14]
004e8e06  c0f38000   ubfx     r0, r0, #2, #1
004e8e0a  c0b2       uxtb     r0, r0
004e8e0c  0028       cmp      r0, #0
004e8e0e  20d0       beq      #0x4e8e52
004e8e10  0023       movs     r3, #0
004e8e12  4a46       mov      r2, sb
004e8e14  3100       movs     r1, r6
004e8e16  2800       movs     r0, r5
004e8e18  d5f800c0   ldr.w    ip, [r5]
004e8e1c  e047       blx      ip
004e8e1e  8346       mov      fp, r0
004e8e20  a869       ldr      r0, [r5, #0x18]
004e8e22  5045       cmp      r0, sl
004e8e24  01d3       blo      #0x4e8e2a
004e8e26  8df76bf9   bl       #0x476100
004e8e2a  5ffa8bfb   uxtb.w   fp, fp
004e8e2e  bbf1000f   cmp.w    fp, #0
004e8e32  05d0       beq      #0x4e8e40
004e8e34  f07b       ldrb     r0, [r6, #0xf]
004e8e36  c007       lsls     r0, r0, #0x1f
004e8e38  0dd5       bpl      #0x4e8e56
004e8e3a  002c       cmp      r4, #0
004e8e3c  00d1       bne      #0x4e8e40
004e8e3e  2c00       movs     r4, r5
004e8e40  ed69       ldr      r5, [r5, #0x1c]
004e8e42  002d       cmp      r5, #0
004e8e44  0ad0       beq      #0x4e8e5c
004e8e46  2868       ldr      r0, [r5]
004e8e48  40f20111   movw     r1, #0x101
004e8e4c  8842       cmp      r0, r1
004e8e4e  d2d2       bhs      #0x4e8df6
004e8e50  fee7       b        #0x4e8e50
004e8e52  4346       mov      r3, r8
004e8e54  dde7       b        #0x4e8e12
004e8e56  3560       str      r5, [r6]
004e8e58  0120       movs     r0, #1
004e8e5a  31e0       b        #0x4e8ec0
004e8e5c  002c       cmp      r4, #0
004e8e5e  1bd0       beq      #0x4e8e98
004e8e60  364d       ldr      r5, [pc, #0xd8]
004e8e62  a069       ldr      r0, [r4, #0x18]
004e8e64  a842       cmp      r0, r5
004e8e66  01d3       blo      #0x4e8e6c
004e8e68  8df73ff9   bl       #0x4760ea
004e8e6c  207d       ldrb     r0, [r4, #0x14]
004e8e6e  c0f38000   ubfx     r0, r0, #2, #1
004e8e72  c0b2       uxtb     r0, r0
004e8e74  0028       cmp      r0, #0
004e8e76  01d0       beq      #0x4e8e7c
004e8e78  0023       movs     r3, #0
004e8e7a  00e0       b        #0x4e8e7e
004e8e7c  4346       mov      r3, r8
004e8e7e  4a46       mov      r2, sb
004e8e80  3100       movs     r1, r6
004e8e82  2000       movs     r0, r4
004e8e84  2768       ldr      r7, [r4]
004e8e86  b847       blx      r7
004e8e88  a069       ldr      r0, [r4, #0x18]
004e8e8a  a842       cmp      r0, r5
004e8e8c  01d3       blo      #0x4e8e92
004e8e8e  8df737f9   bl       #0x476100
004e8e92  3460       str      r4, [r6]
004e8e94  0120       movs     r0, #1
004e8e96  13e0       b        #0x4e8ec0
004e8e98  0220       movs     r0, #2
004e8e9a  f080       strh     r0, [r6, #6]
004e8e9c  f088       ldrh     r0, [r6, #6]
004e8e9e  4000       lsls     r0, r0, #1
004e8ea0  b080       strh     r0, [r6, #4]
004e8ea2  0020       movs     r0, #0
004e8ea4  3060       str      r0, [r6]
004e8ea6  f868       ldr      r0, [r7, #0xc]
004e8ea8  3081       strh     r0, [r6, #8]
004e8eaa  0020       movs     r0, #0
004e8eac  7081       strh     r0, [r6, #0xa]
004e8eae  0020       movs     r0, #0
004e8eb0  b081       strh     r0, [r6, #0xc]
004e8eb2  0120       movs     r0, #1
004e8eb4  b073       strb     r0, [r6, #0xe]
004e8eb6  f07b       ldrb     r0, [r6, #0xf]
004e8eb8  50f00100   orrs     r0, r0, #1
004e8ebc  f073       strb     r0, [r6, #0xf]
004e8ebe  0020       movs     r0, #0
004e8ec0  bde8fe8f   pop.w    {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, pc}
