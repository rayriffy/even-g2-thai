; Stock SHA-256: 363198f8d543a5c1181d8a213e9077285cb865700a1885c8dc7c1b9324fd0e05
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; font-manager background chain call
00476200  0421       movs     r1, #4
00476202  7648       ldr      r0, [pc, #0x1d8]
00476204  fff774fb   bl       #0x4758f0
00476208  2060       str      r0, [r4]
0047620a  2068       ldr      r0, [r4]
0047620c  0028       cmp      r0, #0
0047620e  05d0       beq      #0x47621c
00476210  2068       ldr      r0, [r4]
00476212  fff7a8fd   bl       #0x475d66
00476216  7249       ldr      r1, [pc, #0x1c8]
00476218  0860       str      r0, [r1]
0047621a  1fe0       b        #0x47625c

; font-manager foreground chain call
0047625e  0421       movs     r1, #4
00476260  6448       ldr      r0, [pc, #0x190]
00476262  fff745fb   bl       #0x4758f0
00476266  2060       str      r0, [r4]
00476268  2068       ldr      r0, [r4]
0047626a  0028       cmp      r0, #0
0047626c  05d0       beq      #0x47627a
0047626e  2068       ldr      r0, [r4]
00476270  fff779fd   bl       #0x475d66
00476274  6049       ldr      r1, [pc, #0x180]
00476276  0860       str      r0, [r1]
00476278  1fe0       b        #0x4762ba

; stock chain builder entry
004758f0  2de9fe4f   push.w   {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}
004758f4  0600       movs     r6, r0
004758f6  0f00       movs     r7, r1
004758f8  c7f797fe   bl       #0x43d62a
004758fc  8007       lsls     r0, r0, #0x1e
004758fe  0dd5       bpl      #0x47591c
00475900  dff8e008   ldr.w    r0, [pc, #0x8e0]
00475904  0190       str      r0, [sp, #4]
00475906  4120       movs     r0, #0x41
00475908  0090       str      r0, [sp]
0047590a  dff8dc38   ldr.w    r3, [pc, #0x8dc]
0047590e  dff8082a   ldr.w    r2, [pc, #0xa08]
00475912  dff8081a   ldr.w    r1, [pc, #0xa08]
00475916  0320       movs     r0, #3
00475918  c8f72ef9   bl       #0x43db78
0047591c  c7f785fe   bl       #0x43d62a
00475920  c007       lsls     r0, r0, #0x1f
00475922  03d4       bmi      #0x47592c
00475924  c7f781fe   bl       #0x43d62a
00475928  4007       lsls     r0, r0, #0x1d
0047592a  06d5       bpl      #0x47593a
0047592c  dff8bc18   ldr.w    r1, [pc, #0x8bc]
00475930  0a00       movs     r2, r1
00475932  5ff04060   movs.w   r0, #0xc000000
00475936  c7f7c2fa   bl       #0x43cebe

; allocator
00480876  70b5       push     {r4, r5, r6, lr}
00480878  0400       movs     r4, r0
0048087a  0025       movs     r5, #0
0048087c  824e       ldr      r6, [pc, #0x208]
0048087e  4ff47a71   mov.w    r1, #0x3e8
00480882  3068       ldr      r0, [r6]
00480884  c2f740fb   bl       #0x442f08
00480888  0028       cmp      r0, #0
0048088a  09d1       bne      #0x4808a0
0048088c  2100       movs     r1, r4
0048088e  7f48       ldr      r0, [pc, #0x1fc]
00480890  0068       ldr      r0, [r0]
00480892  74f062fe   bl       #0x4f555a
00480896  0500       movs     r5, r0
00480898  3068       ldr      r0, [r6]
0048089a  c2f768fb   bl       #0x442f6e
0048089e  0ae0       b        #0x4808b6
004808a0  7b48       ldr      r0, [pc, #0x1ec]
004808a2  fdf75cfc   bl       #0x47e15e
004808a6  40f23a42   movw     r2, #0x43a
004808aa  6a49       ldr      r1, [pc, #0x1a8]
004808ac  63a0       adr      r0, #0x18c
004808ae  74f09dff   bl       #0x4f57ec
004808b2  aff30080   nop.w    
004808b6  2800       movs     r0, r5
004808b8  70bd       pop      {r4, r5, r6, pc}

; XIP acquire and release guards
0047a9ee  80b5       push     {r7, lr}
0047a9f0  fff7a0ff   bl       #0x47a934
0047a9f4  dff8980c   ldr.w    r0, [pc, #0xc98]
0047a9f8  0078       ldrb     r0, [r0]
0047a9fa  0128       cmp      r0, #1
0047a9fc  01d0       beq      #0x47aa02
0047a9fe  fff75cff   bl       #0x47a8ba
0047aa02  01bd       pop      {r0, pc}
0047aa04  80b5       push     {r7, lr}
0047aa06  dff8880c   ldr.w    r0, [pc, #0xc88]
0047aa0a  0078       ldrb     r0, [r0]
0047aa0c  0128       cmp      r0, #1
0047aa0e  01d0       beq      #0x47aa14
0047aa10  fff743ff   bl       #0x47a89a
0047aa14  fff7bdff   bl       #0x47a992
0047aa18  01bd       pop      {r0, pc}

; bitmap dispatch
00508aaa  feb5       push     {r1, r2, r3, r4, r5, r6, r7, lr}
00508aac  0500       movs     r5, r0
00508aae  0e00       movs     r6, r1
00508ab0  2c68       ldr      r4, [r5]
00508ab2  002c       cmp      r4, #0
00508ab4  10d1       bne      #0x508ad8
00508ab6  8e48       ldr      r0, [pc, #0x238]
00508ab8  0290       str      r0, [sp, #8]
00508aba  8e48       ldr      r0, [pc, #0x238]
00508abc  0190       str      r0, [sp, #4]
00508abe  8e48       ldr      r0, [pc, #0x238]
00508ac0  0090       str      r0, [sp]
00508ac2  8e4b       ldr      r3, [pc, #0x238]
00508ac4  3622       movs     r2, #0x36
00508ac6  8e49       ldr      r1, [pc, #0x238]
00508ac8  0320       movs     r0, #3
00508aca  47f785fd   bl       #0x4505d8
00508ace  0020       movs     r0, #0
00508ad0  5ff0ff31   movs.w   r1, #-1
00508ad4  0860       str      r0, [r1]
00508ad6  fae7       b        #0x508ace
00508ad8  8a4f       ldr      r7, [pc, #0x228]
00508ada  a069       ldr      r0, [r4, #0x18]
00508adc  b842       cmp      r0, r7
00508ade  01d3       blo      #0x508ae4
00508ae0  71f785ff   bl       #0x47a9ee
00508ae4  3100       movs     r1, r6
00508ae6  2800       movs     r0, r5
00508ae8  6268       ldr      r2, [r4, #4]
00508aea  9047       blx      r2
00508aec  0500       movs     r5, r0
00508aee  a069       ldr      r0, [r4, #0x18]
00508af0  b842       cmp      r0, r7
00508af2  01d3       blo      #0x508af8
00508af4  71f786ff   bl       #0x47aa04
00508af8  2800       movs     r0, r5
00508afa  febd       pop      {r1, r2, r3, r4, r5, r6, r7, pc}

; glyph release
00508afc  7fb5       push     {r0, r1, r2, r3, r4, r5, r6, lr}
00508afe  0500       movs     r5, r0
00508b00  002d       cmp      r5, #0
00508b02  10d1       bne      #0x508b26
00508b04  7a48       ldr      r0, [pc, #0x1e8]
00508b06  0290       str      r0, [sp, #8]
00508b08  7f48       ldr      r0, [pc, #0x1fc]
00508b0a  0190       str      r0, [sp, #4]
00508b0c  7a48       ldr      r0, [pc, #0x1e8]
00508b0e  0090       str      r0, [sp]
00508b10  7e4b       ldr      r3, [pc, #0x1f8]
00508b12  4322       movs     r2, #0x43
00508b14  7a49       ldr      r1, [pc, #0x1e8]
00508b16  0320       movs     r0, #3
00508b18  47f75efd   bl       #0x4505d8
00508b1c  0020       movs     r0, #0
00508b1e  5ff0ff31   movs.w   r1, #-1
00508b22  0860       str      r0, [r1]
00508b24  fae7       b        #0x508b1c
00508b26  e869       ldr      r0, [r5, #0x1c]
00508b28  0028       cmp      r0, #0
00508b2a  14d0       beq      #0x508b56
00508b2c  2c68       ldr      r4, [r5]
00508b2e  002c       cmp      r4, #0
00508b30  11d0       beq      #0x508b56
00508b32  a068       ldr      r0, [r4, #8]
00508b34  0028       cmp      r0, #0
00508b36  0ed0       beq      #0x508b56
00508b38  724e       ldr      r6, [pc, #0x1c8]
00508b3a  a069       ldr      r0, [r4, #0x18]
00508b3c  b042       cmp      r0, r6
00508b3e  01d3       blo      #0x508b44
00508b40  71f755ff   bl       #0x47a9ee
00508b44  2900       movs     r1, r5
00508b46  2000       movs     r0, r4
00508b48  a268       ldr      r2, [r4, #8]
00508b4a  9047       blx      r2
00508b4c  a069       ldr      r0, [r4, #0x18]
00508b4e  b042       cmp      r0, r6
00508b50  01d3       blo      #0x508b56
00508b52  71f757ff   bl       #0x47aa04
00508b56  7fbd       pop      {r0, r1, r2, r3, r4, r5, r6, pc}

; glyph descriptor fallback dispatch
00508b58  2de9fe4f   push.w   {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}
00508b5c  0700       movs     r7, r0
00508b5e  9146       mov      sb, r2
00508b60  9846       mov      r8, r3
00508b62  002f       cmp      r7, #0
00508b64  10d1       bne      #0x508b88
00508b66  6248       ldr      r0, [pc, #0x188]
00508b68  0290       str      r0, [sp, #8]
00508b6a  6248       ldr      r0, [pc, #0x188]
00508b6c  0190       str      r0, [sp, #4]
00508b6e  6248       ldr      r0, [pc, #0x188]
00508b70  0090       str      r0, [sp]
00508b72  674b       ldr      r3, [pc, #0x19c]
00508b74  5a22       movs     r2, #0x5a
00508b76  6249       ldr      r1, [pc, #0x188]
00508b78  0320       movs     r0, #3
00508b7a  47f72dfd   bl       #0x4505d8
00508b7e  0020       movs     r0, #0
00508b80  5ff0ff31   movs.w   r1, #-1
00508b84  0860       str      r0, [r1]
00508b86  fae7       b        #0x508b7e
00508b88  0e00       movs     r6, r1
00508b8a  002e       cmp      r6, #0
00508b8c  10d1       bne      #0x508bb0
00508b8e  5848       ldr      r0, [pc, #0x160]
00508b90  0290       str      r0, [sp, #8]
00508b92  6048       ldr      r0, [pc, #0x180]
00508b94  0190       str      r0, [sp, #4]
00508b96  5848       ldr      r0, [pc, #0x160]
00508b98  0090       str      r0, [sp]
00508b9a  5d4b       ldr      r3, [pc, #0x174]
00508b9c  5b22       movs     r2, #0x5b
00508b9e  5849       ldr      r1, [pc, #0x160]
00508ba0  0320       movs     r0, #3
00508ba2  47f719fd   bl       #0x4505d8
00508ba6  0020       movs     r0, #0
00508ba8  5ff0ff31   movs.w   r1, #-1
00508bac  0860       str      r0, [r1]
00508bae  fae7       b        #0x508ba6
00508bb0  0024       movs     r4, #0
00508bb2  3d00       movs     r5, r7
00508bb4  2021       movs     r1, #0x20
00508bb6  3000       movs     r0, r6
00508bb8  fff736ff   bl       #0x508a28
00508bbc  25e0       b        #0x508c0a
00508bbe  dff844a1   ldr.w    sl, [pc, #0x144]
00508bc2  a869       ldr      r0, [r5, #0x18]
00508bc4  5045       cmp      r0, sl
00508bc6  01d3       blo      #0x508bcc
00508bc8  71f711ff   bl       #0x47a9ee
00508bcc  287d       ldrb     r0, [r5, #0x14]
00508bce  c0f38000   ubfx     r0, r0, #2, #1
00508bd2  c0b2       uxtb     r0, r0
00508bd4  0028       cmp      r0, #0
00508bd6  20d0       beq      #0x508c1a
00508bd8  0023       movs     r3, #0
00508bda  4a46       mov      r2, sb
00508bdc  3100       movs     r1, r6
00508bde  2800       movs     r0, r5
00508be0  d5f800c0   ldr.w    ip, [r5]
00508be4  e047       blx      ip
00508be6  8346       mov      fp, r0
00508be8  a869       ldr      r0, [r5, #0x18]
00508bea  5045       cmp      r0, sl
00508bec  01d3       blo      #0x508bf2
00508bee  71f709ff   bl       #0x47aa04
00508bf2  5ffa8bfb   uxtb.w   fp, fp
00508bf6  bbf1000f   cmp.w    fp, #0
00508bfa  05d0       beq      #0x508c08
00508bfc  f07b       ldrb     r0, [r6, #0xf]
00508bfe  c007       lsls     r0, r0, #0x1f
00508c00  0dd5       bpl      #0x508c1e
00508c02  002c       cmp      r4, #0
00508c04  00d1       bne      #0x508c08
00508c06  2c00       movs     r4, r5
00508c08  ed69       ldr      r5, [r5, #0x1c]
00508c0a  002d       cmp      r5, #0
00508c0c  0ad0       beq      #0x508c24
00508c0e  2868       ldr      r0, [r5]
00508c10  40f20111   movw     r1, #0x101
00508c14  8842       cmp      r0, r1
00508c16  d2d2       bhs      #0x508bbe
00508c18  fee7       b        #0x508c18
00508c1a  4346       mov      r3, r8
00508c1c  dde7       b        #0x508bda
00508c1e  3560       str      r5, [r6]
00508c20  0120       movs     r0, #1
00508c22  31e0       b        #0x508c88
00508c24  002c       cmp      r4, #0
00508c26  1bd0       beq      #0x508c60
00508c28  364d       ldr      r5, [pc, #0xd8]
00508c2a  a069       ldr      r0, [r4, #0x18]
00508c2c  a842       cmp      r0, r5
00508c2e  01d3       blo      #0x508c34
00508c30  71f7ddfe   bl       #0x47a9ee
00508c34  207d       ldrb     r0, [r4, #0x14]
00508c36  c0f38000   ubfx     r0, r0, #2, #1
00508c3a  c0b2       uxtb     r0, r0
00508c3c  0028       cmp      r0, #0
00508c3e  01d0       beq      #0x508c44
00508c40  0023       movs     r3, #0
00508c42  00e0       b        #0x508c46
00508c44  4346       mov      r3, r8
00508c46  4a46       mov      r2, sb
00508c48  3100       movs     r1, r6
00508c4a  2000       movs     r0, r4
00508c4c  2768       ldr      r7, [r4]
00508c4e  b847       blx      r7
00508c50  a069       ldr      r0, [r4, #0x18]
00508c52  a842       cmp      r0, r5
00508c54  01d3       blo      #0x508c5a
00508c56  71f7d5fe   bl       #0x47aa04
00508c5a  3460       str      r4, [r6]
00508c5c  0120       movs     r0, #1
00508c5e  13e0       b        #0x508c88
00508c60  0220       movs     r0, #2
00508c62  f080       strh     r0, [r6, #6]
00508c64  f088       ldrh     r0, [r6, #6]
00508c66  4000       lsls     r0, r0, #1
00508c68  b080       strh     r0, [r6, #4]
00508c6a  0020       movs     r0, #0
00508c6c  3060       str      r0, [r6]
00508c6e  f868       ldr      r0, [r7, #0xc]
00508c70  3081       strh     r0, [r6, #8]
00508c72  0020       movs     r0, #0
00508c74  7081       strh     r0, [r6, #0xa]
00508c76  0020       movs     r0, #0
00508c78  b081       strh     r0, [r6, #0xc]
00508c7a  0120       movs     r0, #1
00508c7c  b073       strb     r0, [r6, #0xe]
00508c7e  f07b       ldrb     r0, [r6, #0xf]
00508c80  50f00100   orrs     r0, r0, #1
00508c84  f073       strb     r0, [r6, #0xf]
00508c86  0020       movs     r0, #0
00508c88  bde8fe8f   pop.w    {r1, r2, r3, r4, r5, r6, r7, r8, sb, sl, fp, pc}
