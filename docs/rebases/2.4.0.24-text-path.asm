; Stock SHA-256: 363198f8d543a5c1181d8a213e9077285cb865700a1885c8dc7c1b9324fd0e05
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; letter-pair helper and NULL-safe decoder
0049f1e4  2de9f041   push.w   {r4, r5, r6, r7, r8, lr}
0049f1e8  0500       movs     r5, r0
0049f1ea  0e00       movs     r6, r1
0049f1ec  1400       movs     r4, r2
0049f1ee  1f00       movs     r7, r3
0049f1f0  dff86083   ldr.w    r8, [pc, #0x360]
0049f1f4  3900       movs     r1, r7
0049f1f6  2800       movs     r0, r5
0049f1f8  d8f80020   ldr.w    r2, [r8]
0049f1fc  9047       blx      r2
0049f1fe  3060       str      r0, [r6]
0049f200  3068       ldr      r0, [r6]
0049f202  0028       cmp      r0, #0
0049f204  06d0       beq      #0x49f214
0049f206  0021       movs     r1, #0
0049f208  3868       ldr      r0, [r7]
0049f20a  2844       add      r0, r5
0049f20c  d8f80020   ldr.w    r2, [r8]
0049f210  9047       blx      r2
0049f212  00e0       b        #0x49f216
0049f214  0020       movs     r0, #0
0049f216  2060       str      r0, [r4]
0049f218  bde8f081   pop.w    {r4, r5, r6, r7, r8, pc}
0049f21c  0178       ldrb     r1, [r0]
0049f21e  0906       lsls     r1, r1, #0x18
0049f220  01d4       bmi      #0x49f226
0049f222  0120       movs     r0, #1
0049f224  15e0       b        #0x49f252
0049f226  0178       ldrb     r1, [r0]
0049f228  11f0e001   ands     r1, r1, #0xe0
0049f22c  c029       cmp      r1, #0xc0
0049f22e  01d1       bne      #0x49f234
0049f230  0220       movs     r0, #2
0049f232  0ee0       b        #0x49f252
0049f234  0178       ldrb     r1, [r0]
0049f236  11f0f001   ands     r1, r1, #0xf0
0049f23a  e029       cmp      r1, #0xe0
0049f23c  01d1       bne      #0x49f242
0049f23e  0320       movs     r0, #3
0049f240  07e0       b        #0x49f252
0049f242  0078       ldrb     r0, [r0]
0049f244  10f0f800   ands     r0, r0, #0xf8
0049f248  f028       cmp      r0, #0xf0
0049f24a  01d1       bne      #0x49f250
0049f24c  0420       movs     r0, #4
0049f24e  00e0       b        #0x49f252
0049f250  0020       movs     r0, #0
0049f252  7047       bx       lr
0049f254  81b0       sub      sp, #4
0049f256  8028       cmp      r0, #0x80
0049f258  16d3       blo      #0x49f288
0049f25a  b0f5006f   cmp.w    r0, #0x800
0049f25e  15d2       bhs      #0x49f28c
0049f260  0100       movs     r1, r0
0049f262  8909       lsrs     r1, r1, #6
0049f264  11f01f01   ands     r1, r1, #0x1f
0049f268  51f0c001   orrs     r1, r1, #0xc0
0049f26c  8df80010   strb.w   r1, [sp]
0049f270  6946       mov      r1, sp
0049f272  10f03f00   ands     r0, r0, #0x3f
0049f276  50f08000   orrs     r0, r0, #0x80
0049f27a  4870       strb     r0, [r1, #1]
0049f27c  0020       movs     r0, #0
0049f27e  8870       strb     r0, [r1, #2]
0049f280  0020       movs     r0, #0
0049f282  c870       strb     r0, [r1, #3]
0049f284  6846       mov      r0, sp
0049f286  0068       ldr      r0, [r0]
0049f288  01b0       add      sp, #4
0049f28a  7047       bx       lr
0049f28c  b0f5803f   cmp.w    r0, #0x10000
0049f290  17d2       bhs      #0x49f2c2
0049f292  0100       movs     r1, r0
0049f294  090b       lsrs     r1, r1, #0xc
0049f296  11f00f01   ands     r1, r1, #0xf
0049f29a  51f0e001   orrs     r1, r1, #0xe0
0049f29e  8df80010   strb.w   r1, [sp]
0049f2a2  6946       mov      r1, sp
0049f2a4  0200       movs     r2, r0
0049f2a6  9209       lsrs     r2, r2, #6
0049f2a8  12f03f02   ands     r2, r2, #0x3f
0049f2ac  52f08002   orrs     r2, r2, #0x80
0049f2b0  4a70       strb     r2, [r1, #1]
0049f2b2  10f03f00   ands     r0, r0, #0x3f
0049f2b6  50f08000   orrs     r0, r0, #0x80
0049f2ba  8870       strb     r0, [r1, #2]
0049f2bc  0020       movs     r0, #0
0049f2be  c870       strb     r0, [r1, #3]
0049f2c0  e0e7       b        #0x49f284
0049f2c2  b0f5881f   cmp.w    r0, #0x110000
0049f2c6  1cd2       bhs      #0x49f302
0049f2c8  0100       movs     r1, r0
0049f2ca  890c       lsrs     r1, r1, #0x12
0049f2cc  11f00701   ands     r1, r1, #7
0049f2d0  51f0f001   orrs     r1, r1, #0xf0
0049f2d4  8df80010   strb.w   r1, [sp]
0049f2d8  6946       mov      r1, sp
0049f2da  0200       movs     r2, r0
0049f2dc  120b       lsrs     r2, r2, #0xc
0049f2de  12f03f02   ands     r2, r2, #0x3f
0049f2e2  52f08002   orrs     r2, r2, #0x80
0049f2e6  4a70       strb     r2, [r1, #1]
0049f2e8  0200       movs     r2, r0
0049f2ea  9209       lsrs     r2, r2, #6
0049f2ec  12f03f02   ands     r2, r2, #0x3f
0049f2f0  52f08002   orrs     r2, r2, #0x80
0049f2f4  8a70       strb     r2, [r1, #2]
0049f2f6  10f03f00   ands     r0, r0, #0x3f
0049f2fa  50f08000   orrs     r0, r0, #0x80
0049f2fe  c870       strb     r0, [r1, #3]
0049f300  c0e7       b        #0x49f284
0049f302  0020       movs     r0, #0
0049f304  c0e7       b        #0x49f288
0049f306  81b0       sub      sp, #4
0049f308  0022       movs     r2, #0
0049f30a  0023       movs     r3, #0
0049f30c  0093       str      r3, [sp]
0049f30e  0029       cmp      r1, #0
0049f310  00d1       bne      #0x49f314
0049f312  6946       mov      r1, sp
0049f314  0028       cmp      r0, #0
0049f316  03d0       beq      #0x49f320
0049f318  0b68       ldr      r3, [r1]
0049f31a  c35c       ldrb     r3, [r0, r3]
0049f31c  002b       cmp      r3, #0
0049f31e  01d1       bne      #0x49f324
0049f320  1000       movs     r0, r2
0049f322  9de0       b        #0x49f460
0049f324  0b68       ldr      r3, [r1]
0049f326  c35c       ldrb     r3, [r0, r3]
0049f328  1b06       lsls     r3, r3, #0x18
0049f32a  05d4       bmi      #0x49f338
0049f32c  0a68       ldr      r2, [r1]
0049f32e  825c       ldrb     r2, [r0, r2]
0049f330  0868       ldr      r0, [r1]
0049f332  401c       adds     r0, r0, #1
0049f334  0860       str      r0, [r1]
0049f336  92e0       b        #0x49f45e
0049f338  0b68       ldr      r3, [r1]
0049f33a  c35c       ldrb     r3, [r0, r3]
0049f33c  13f0e003   ands     r3, r3, #0xe0
0049f340  c02b       cmp      r3, #0xc0
0049f342  18d1       bne      #0x49f376
0049f344  0a68       ldr      r2, [r1]
0049f346  835c       ldrb     r3, [r0, r2]
0049f348  13f01f03   ands     r3, r3, #0x1f
0049f34c  9b01       lsls     r3, r3, #6
0049f34e  0a68       ldr      r2, [r1]
0049f350  521c       adds     r2, r2, #1
0049f352  0a60       str      r2, [r1]
0049f354  0a68       ldr      r2, [r1]
0049f356  825c       ldrb     r2, [r0, r2]
0049f358  12f0c002   ands     r2, r2, #0xc0
0049f35c  802a       cmp      r2, #0x80
0049f35e  01d0       beq      #0x49f364
0049f360  0020       movs     r0, #0
0049f362  7de0       b        #0x49f460
0049f364  0a68       ldr      r2, [r1]
0049f366  825c       ldrb     r2, [r0, r2]
0049f368  12f03f02   ands     r2, r2, #0x3f
0049f36c  d218       adds     r2, r2, r3
0049f36e  0868       ldr      r0, [r1]
0049f370  401c       adds     r0, r0, #1
0049f372  0860       str      r0, [r1]
0049f374  73e0       b        #0x49f45e
0049f376  0b68       ldr      r3, [r1]
0049f378  c35c       ldrb     r3, [r0, r3]
0049f37a  13f0f003   ands     r3, r3, #0xf0
0049f37e  e02b       cmp      r3, #0xe0
0049f380  29d1       bne      #0x49f3d6
0049f382  0a68       ldr      r2, [r1]
0049f384  835c       ldrb     r3, [r0, r2]
0049f386  13f00f03   ands     r3, r3, #0xf
0049f38a  1b03       lsls     r3, r3, #0xc
0049f38c  0a68       ldr      r2, [r1]
0049f38e  521c       adds     r2, r2, #1
0049f390  0a60       str      r2, [r1]
0049f392  0a68       ldr      r2, [r1]
0049f394  825c       ldrb     r2, [r0, r2]
0049f396  12f0c002   ands     r2, r2, #0xc0
0049f39a  802a       cmp      r2, #0x80
0049f39c  01d0       beq      #0x49f3a2
0049f39e  0020       movs     r0, #0
0049f3a0  5ee0       b        #0x49f460
0049f3a2  0a68       ldr      r2, [r1]
0049f3a4  825c       ldrb     r2, [r0, r2]
0049f3a6  12f03f02   ands     r2, r2, #0x3f
0049f3aa  13eb8213   adds.w   r3, r3, r2, lsl #6
0049f3ae  0a68       ldr      r2, [r1]
0049f3b0  521c       adds     r2, r2, #1
0049f3b2  0a60       str      r2, [r1]
0049f3b4  0a68       ldr      r2, [r1]
0049f3b6  825c       ldrb     r2, [r0, r2]
0049f3b8  12f0c002   ands     r2, r2, #0xc0
0049f3bc  802a       cmp      r2, #0x80
0049f3be  01d0       beq      #0x49f3c4
0049f3c0  0020       movs     r0, #0
0049f3c2  4de0       b        #0x49f460
0049f3c4  0a68       ldr      r2, [r1]
0049f3c6  825c       ldrb     r2, [r0, r2]
0049f3c8  12f03f02   ands     r2, r2, #0x3f
0049f3cc  d218       adds     r2, r2, r3
0049f3ce  0868       ldr      r0, [r1]
0049f3d0  401c       adds     r0, r0, #1
0049f3d2  0860       str      r0, [r1]
0049f3d4  43e0       b        #0x49f45e
0049f3d6  0b68       ldr      r3, [r1]
0049f3d8  c35c       ldrb     r3, [r0, r3]
0049f3da  13f0f803   ands     r3, r3, #0xf8
0049f3de  f02b       cmp      r3, #0xf0
0049f3e0  3ad1       bne      #0x49f458
0049f3e2  0a68       ldr      r2, [r1]
0049f3e4  835c       ldrb     r3, [r0, r2]
0049f3e6  13f00703   ands     r3, r3, #7
0049f3ea  9b04       lsls     r3, r3, #0x12
0049f3ec  0a68       ldr      r2, [r1]
0049f3ee  521c       adds     r2, r2, #1
0049f3f0  0a60       str      r2, [r1]
0049f3f2  0a68       ldr      r2, [r1]
0049f3f4  825c       ldrb     r2, [r0, r2]
0049f3f6  12f0c002   ands     r2, r2, #0xc0
0049f3fa  802a       cmp      r2, #0x80
0049f3fc  01d0       beq      #0x49f402
0049f3fe  0020       movs     r0, #0
0049f400  2ee0       b        #0x49f460
0049f402  0a68       ldr      r2, [r1]
0049f404  825c       ldrb     r2, [r0, r2]
0049f406  12f03f02   ands     r2, r2, #0x3f
0049f40a  13eb0233   adds.w   r3, r3, r2, lsl #12
0049f40e  0a68       ldr      r2, [r1]
0049f410  521c       adds     r2, r2, #1
0049f412  0a60       str      r2, [r1]
0049f414  0a68       ldr      r2, [r1]
0049f416  825c       ldrb     r2, [r0, r2]
0049f418  12f0c002   ands     r2, r2, #0xc0
0049f41c  802a       cmp      r2, #0x80
0049f41e  01d0       beq      #0x49f424
0049f420  0020       movs     r0, #0
0049f422  1de0       b        #0x49f460
0049f424  0a68       ldr      r2, [r1]
0049f426  825c       ldrb     r2, [r0, r2]
0049f428  12f03f02   ands     r2, r2, #0x3f
0049f42c  13eb8213   adds.w   r3, r3, r2, lsl #6
0049f430  0a68       ldr      r2, [r1]
0049f432  521c       adds     r2, r2, #1
0049f434  0a60       str      r2, [r1]
0049f436  0a68       ldr      r2, [r1]
