; Stock SHA-256: 26b6067665a441b779c47f6b95427b8b4bb5f502aaf527466dadce628aeb00b2
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; font-manager background chain call
00471bc4  0421       movs     r1, #4
00471bc6  7748       ldr      r0, [pc, #0x1dc]
00471bc8  fff736fb   bl       #0x471238
00471bcc  2060       str      r0, [r4]
00471bce  2068       ldr      r0, [r4]
00471bd0  0028       cmp      r0, #0
00471bd2  05d0       beq      #0x471be0
00471bd4  2068       ldr      r0, [r4]
00471bd6  fff76afd   bl       #0x4716ae
00471bda  7349       ldr      r1, [pc, #0x1cc]
00471bdc  0860       str      r0, [r1]
00471bde  1fe0       b        #0x471c20

; font-manager foreground chain call
00471c22  0421       movs     r1, #4
00471c24  6548       ldr      r0, [pc, #0x194]
00471c26  fff707fb   bl       #0x471238
00471c2a  2060       str      r0, [r4]
00471c2c  2068       ldr      r0, [r4]
00471c2e  0028       cmp      r0, #0
00471c30  05d0       beq      #0x471c3e
00471c32  2068       ldr      r0, [r4]
00471c34  fff73bfd   bl       #0x4716ae
00471c38  6149       ldr      r1, [pc, #0x184]
00471c3a  0860       str      r0, [r1]
00471c3c  1fe0       b        #0x471c7e

; stock chain builder entry
00471238  2de9fe4f   push.w   {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}
0047123c  0600       movs     r6, r0
0047123e  0f00       movs     r7, r1
00471240  ccf7f3f9   bl       #0x43d62a
00471244  8007       lsls     r0, r0, #0x1e
00471246  0dd5       bpl      #0x471264
00471248  dff85009   ldr.w    r0, [pc, #0x950]
0047124c  0190       str      r0, [sp, #4]
0047124e  4120       movs     r0, #0x41
00471250  0090       str      r0, [sp]
00471252  dff84c39   ldr.w    r3, [pc, #0x94c]
00471256  dff87c2a   ldr.w    r2, [pc, #0xa7c]
0047125a  dff87c1a   ldr.w    r1, [pc, #0xa7c]
0047125e  0320       movs     r0, #3
00471260  ccf78afc   bl       #0x43db78
00471264  ccf7e1f9   bl       #0x43d62a
00471268  c007       lsls     r0, r0, #0x1f
0047126a  03d4       bmi      #0x471274
0047126c  ccf7ddf9   bl       #0x43d62a
00471270  4007       lsls     r0, r0, #0x1d
00471272  06d5       bpl      #0x471282
00471274  dff82c19   ldr.w    r1, [pc, #0x92c]
00471278  0a00       movs     r2, r1
0047127a  5ff04060   movs.w   r0, #0xc000000
0047127e  cbf71efe   bl       #0x43cebe

; allocator
0047ec6a  70b5       push     {r4, r5, r6, lr}
0047ec6c  0400       movs     r4, r0
0047ec6e  0025       movs     r5, #0
0047ec70  824e       ldr      r6, [pc, #0x208]
0047ec72  4ff47a71   mov.w    r1, #0x3e8
0047ec76  3068       ldr      r0, [r6]
0047ec78  c4f738f9   bl       #0x442eec
0047ec7c  0028       cmp      r0, #0
0047ec7e  09d1       bne      #0x47ec94
0047ec80  2100       movs     r1, r4
0047ec82  7f48       ldr      r0, [pc, #0x1fc]
0047ec84  0068       ldr      r0, [r0]
0047ec86  66f0cefa   bl       #0x4e5226
0047ec8a  0500       movs     r5, r0
0047ec8c  3068       ldr      r0, [r6]
0047ec8e  c4f760f9   bl       #0x442f52
0047ec92  0ae0       b        #0x47ecaa
0047ec94  7b48       ldr      r0, [pc, #0x1ec]
0047ec96  faf746ff   bl       #0x479b26
0047ec9a  40f23a42   movw     r2, #0x43a
0047ec9e  6a49       ldr      r1, [pc, #0x1a8]
0047eca0  63a0       adr      r0, #0x18c
0047eca2  66f009fc   bl       #0x4e54b8
0047eca6  aff30080   nop.w    
0047ecaa  2800       movs     r0, r5
0047ecac  70bd       pop      {r4, r5, r6, pc}

; XIP acquire and release guards
004763b6  80b5       push     {r7, lr}
004763b8  fff7a0ff   bl       #0x4762fc
004763bc  dff8980c   ldr.w    r0, [pc, #0xc98]
004763c0  0078       ldrb     r0, [r0]
004763c2  0128       cmp      r0, #1
004763c4  01d0       beq      #0x4763ca
004763c6  fff75cff   bl       #0x476282
004763ca  01bd       pop      {r0, pc}
004763cc  80b5       push     {r7, lr}
004763ce  dff8880c   ldr.w    r0, [pc, #0xc88]
004763d2  0078       ldrb     r0, [r0]
004763d4  0128       cmp      r0, #1
004763d6  01d0       beq      #0x4763dc
004763d8  fff743ff   bl       #0x476262
004763dc  fff7bdff   bl       #0x47635a
004763e0  01bd       pop      {r0, pc}

; bitmap dispatch
004eb33e  feb5       push     {r1, r2, r3, r4, r5, r6, r7, lr}
004eb340  0500       movs     r5, r0
004eb342  0e00       movs     r6, r1
004eb344  2c68       ldr      r4, [r5]
004eb346  002c       cmp      r4, #0
004eb348  10d1       bne      #0x4eb36c
004eb34a  8e48       ldr      r0, [pc, #0x238]
004eb34c  0290       str      r0, [sp, #8]
004eb34e  8e48       ldr      r0, [pc, #0x238]
004eb350  0190       str      r0, [sp, #4]
004eb352  8e48       ldr      r0, [pc, #0x238]
004eb354  0090       str      r0, [sp]
004eb356  8e4b       ldr      r3, [pc, #0x238]
004eb358  3622       movs     r2, #0x36
004eb35a  8e49       ldr      r1, [pc, #0x238]
004eb35c  0320       movs     r0, #3
004eb35e  64f76bff   bl       #0x450238
004eb362  0020       movs     r0, #0
004eb364  5ff0ff31   movs.w   r1, #-1
004eb368  0860       str      r0, [r1]
004eb36a  fae7       b        #0x4eb362
004eb36c  8a4f       ldr      r7, [pc, #0x228]
004eb36e  a069       ldr      r0, [r4, #0x18]
004eb370  b842       cmp      r0, r7
004eb372  01d3       blo      #0x4eb378
004eb374  8bf71ff8   bl       #0x4763b6
004eb378  3100       movs     r1, r6
004eb37a  2800       movs     r0, r5
004eb37c  6268       ldr      r2, [r4, #4]
004eb37e  9047       blx      r2
004eb380  0500       movs     r5, r0
004eb382  a069       ldr      r0, [r4, #0x18]
004eb384  b842       cmp      r0, r7
004eb386  01d3       blo      #0x4eb38c
004eb388  8bf720f8   bl       #0x4763cc
004eb38c  2800       movs     r0, r5
004eb38e  febd       pop      {r1, r2, r3, r4, r5, r6, r7, pc}

; glyph release
004eb390  7fb5       push     {r0, r1, r2, r3, r4, r5, r6, lr}
004eb392  0500       movs     r5, r0
004eb394  002d       cmp      r5, #0
004eb396  10d1       bne      #0x4eb3ba
004eb398  7a48       ldr      r0, [pc, #0x1e8]
004eb39a  0290       str      r0, [sp, #8]
004eb39c  7f48       ldr      r0, [pc, #0x1fc]
004eb39e  0190       str      r0, [sp, #4]
004eb3a0  7a48       ldr      r0, [pc, #0x1e8]
004eb3a2  0090       str      r0, [sp]
004eb3a4  7e4b       ldr      r3, [pc, #0x1f8]
004eb3a6  4322       movs     r2, #0x43
004eb3a8  7a49       ldr      r1, [pc, #0x1e8]
004eb3aa  0320       movs     r0, #3
004eb3ac  64f744ff   bl       #0x450238
004eb3b0  0020       movs     r0, #0
004eb3b2  5ff0ff31   movs.w   r1, #-1
004eb3b6  0860       str      r0, [r1]
004eb3b8  fae7       b        #0x4eb3b0
004eb3ba  e869       ldr      r0, [r5, #0x1c]
004eb3bc  0028       cmp      r0, #0
004eb3be  14d0       beq      #0x4eb3ea
004eb3c0  2c68       ldr      r4, [r5]
004eb3c2  002c       cmp      r4, #0
004eb3c4  11d0       beq      #0x4eb3ea
004eb3c6  a068       ldr      r0, [r4, #8]
004eb3c8  0028       cmp      r0, #0
004eb3ca  0ed0       beq      #0x4eb3ea
004eb3cc  724e       ldr      r6, [pc, #0x1c8]
004eb3ce  a069       ldr      r0, [r4, #0x18]
004eb3d0  b042       cmp      r0, r6
004eb3d2  01d3       blo      #0x4eb3d8
004eb3d4  8af7efff   bl       #0x4763b6
004eb3d8  2900       movs     r1, r5
004eb3da  2000       movs     r0, r4
004eb3dc  a268       ldr      r2, [r4, #8]
004eb3de  9047       blx      r2
004eb3e0  a069       ldr      r0, [r4, #0x18]
004eb3e2  b042       cmp      r0, r6
004eb3e4  01d3       blo      #0x4eb3ea
004eb3e6  8af7f1ff   bl       #0x4763cc
004eb3ea  7fbd       pop      {r0, r1, r2, r3, r4, r5, r6, pc}

; glyph descriptor fallback dispatch
004eb3ec  2de9fe4f   push.w   {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}
004eb3f0  0700       movs     r7, r0
004eb3f2  9146       mov      sb, r2
004eb3f4  9846       mov      r8, r3
004eb3f6  002f       cmp      r7, #0
004eb3f8  10d1       bne      #0x4eb41c
004eb3fa  6248       ldr      r0, [pc, #0x188]
004eb3fc  0290       str      r0, [sp, #8]
004eb3fe  6248       ldr      r0, [pc, #0x188]
004eb400  0190       str      r0, [sp, #4]
004eb402  6248       ldr      r0, [pc, #0x188]
004eb404  0090       str      r0, [sp]
004eb406  674b       ldr      r3, [pc, #0x19c]
004eb408  5a22       movs     r2, #0x5a
004eb40a  6249       ldr      r1, [pc, #0x188]
004eb40c  0320       movs     r0, #3
004eb40e  64f713ff   bl       #0x450238
004eb412  0020       movs     r0, #0
004eb414  5ff0ff31   movs.w   r1, #-1
004eb418  0860       str      r0, [r1]
004eb41a  fae7       b        #0x4eb412
004eb41c  0e00       movs     r6, r1
004eb41e  002e       cmp      r6, #0
004eb420  10d1       bne      #0x4eb444
004eb422  5848       ldr      r0, [pc, #0x160]
004eb424  0290       str      r0, [sp, #8]
004eb426  6048       ldr      r0, [pc, #0x180]
004eb428  0190       str      r0, [sp, #4]
004eb42a  5848       ldr      r0, [pc, #0x160]
004eb42c  0090       str      r0, [sp]
004eb42e  5d4b       ldr      r3, [pc, #0x174]
004eb430  5b22       movs     r2, #0x5b
004eb432  5849       ldr      r1, [pc, #0x160]
004eb434  0320       movs     r0, #3
004eb436  64f7fffe   bl       #0x450238
004eb43a  0020       movs     r0, #0
004eb43c  5ff0ff31   movs.w   r1, #-1
004eb440  0860       str      r0, [r1]
004eb442  fae7       b        #0x4eb43a
004eb444  0024       movs     r4, #0
004eb446  3d00       movs     r5, r7
004eb448  2021       movs     r1, #0x20
004eb44a  3000       movs     r0, r6
004eb44c  fff736ff   bl       #0x4eb2bc
004eb450  25e0       b        #0x4eb49e
004eb452  dff844a1   ldr.w    sl, [pc, #0x144]
004eb456  a869       ldr      r0, [r5, #0x18]
004eb458  5045       cmp      r0, sl
004eb45a  01d3       blo      #0x4eb460
004eb45c  8af7abff   bl       #0x4763b6
004eb460  287d       ldrb     r0, [r5, #0x14]
004eb462  c0f38000   ubfx     r0, r0, #2, #1
004eb466  c0b2       uxtb     r0, r0
004eb468  0028       cmp      r0, #0
004eb46a  20d0       beq      #0x4eb4ae
004eb46c  0023       movs     r3, #0
004eb46e  4a46       mov      r2, sb
004eb470  3100       movs     r1, r6
004eb472  2800       movs     r0, r5
004eb474  d5f800c0   ldr.w    ip, [r5]
004eb478  e047       blx      ip
004eb47a  8346       mov      fp, r0
004eb47c  a869       ldr      r0, [r5, #0x18]
004eb47e  5045       cmp      r0, sl
004eb480  01d3       blo      #0x4eb486
004eb482  8af7a3ff   bl       #0x4763cc
004eb486  5ffa8bfb   uxtb.w   fp, fp
004eb48a  bbf1000f   cmp.w    fp, #0
004eb48e  05d0       beq      #0x4eb49c
004eb490  f07b       ldrb     r0, [r6, #0xf]
004eb492  c007       lsls     r0, r0, #0x1f
004eb494  0dd5       bpl      #0x4eb4b2
004eb496  002c       cmp      r4, #0
004eb498  00d1       bne      #0x4eb49c
004eb49a  2c00       movs     r4, r5
004eb49c  ed69       ldr      r5, [r5, #0x1c]
004eb49e  002d       cmp      r5, #0
004eb4a0  0ad0       beq      #0x4eb4b8
004eb4a2  2868       ldr      r0, [r5]
004eb4a4  40f20111   movw     r1, #0x101
004eb4a8  8842       cmp      r0, r1
004eb4aa  d2d2       bhs      #0x4eb452
004eb4ac  fee7       b        #0x4eb4ac
004eb4ae  4346       mov      r3, r8
004eb4b0  dde7       b        #0x4eb46e
004eb4b2  3560       str      r5, [r6]
004eb4b4  0120       movs     r0, #1
004eb4b6  31e0       b        #0x4eb51c
004eb4b8  002c       cmp      r4, #0
004eb4ba  1bd0       beq      #0x4eb4f4
004eb4bc  364d       ldr      r5, [pc, #0xd8]
004eb4be  a069       ldr      r0, [r4, #0x18]
004eb4c0  a842       cmp      r0, r5
004eb4c2  01d3       blo      #0x4eb4c8
004eb4c4  8af777ff   bl       #0x4763b6
004eb4c8  207d       ldrb     r0, [r4, #0x14]
004eb4ca  c0f38000   ubfx     r0, r0, #2, #1
004eb4ce  c0b2       uxtb     r0, r0
004eb4d0  0028       cmp      r0, #0
004eb4d2  01d0       beq      #0x4eb4d8
004eb4d4  0023       movs     r3, #0
004eb4d6  00e0       b        #0x4eb4da
004eb4d8  4346       mov      r3, r8
004eb4da  4a46       mov      r2, sb
004eb4dc  3100       movs     r1, r6
004eb4de  2000       movs     r0, r4
004eb4e0  2768       ldr      r7, [r4]
004eb4e2  b847       blx      r7
004eb4e4  a069       ldr      r0, [r4, #0x18]
004eb4e6  a842       cmp      r0, r5
004eb4e8  01d3       blo      #0x4eb4ee
004eb4ea  8af76fff   bl       #0x4763cc
004eb4ee  3460       str      r4, [r6]
004eb4f0  0120       movs     r0, #1
004eb4f2  13e0       b        #0x4eb51c
004eb4f4  0220       movs     r0, #2
004eb4f6  f080       strh     r0, [r6, #6]
004eb4f8  f088       ldrh     r0, [r6, #6]
004eb4fa  4000       lsls     r0, r0, #1
004eb4fc  b080       strh     r0, [r6, #4]
004eb4fe  0020       movs     r0, #0
004eb500  3060       str      r0, [r6]
004eb502  f868       ldr      r0, [r7, #0xc]
004eb504  3081       strh     r0, [r6, #8]
004eb506  0020       movs     r0, #0
004eb508  7081       strh     r0, [r6, #0xa]
004eb50a  0020       movs     r0, #0
004eb50c  b081       strh     r0, [r6, #0xc]
004eb50e  0120       movs     r0, #1
004eb510  b073       strb     r0, [r6, #0xe]
004eb512  f07b       ldrb     r0, [r6, #0xf]
004eb514  50f00100   orrs     r0, r0, #1
004eb518  f073       strb     r0, [r6, #0xf]
004eb51a  0020       movs     r0, #0
004eb51c  bde8fe8f   pop.w    {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, pc}
