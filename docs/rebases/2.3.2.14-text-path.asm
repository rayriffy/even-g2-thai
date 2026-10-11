; Stock SHA-256: 26b6067665a441b779c47f6b95427b8b4bb5f502aaf527466dadce628aeb00b2
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; letter-pair helper and NULL-safe decoder
00493fc0  2de9f041   push.w   {r4, r5, r6, r7, r8, lr}
00493fc4  0500       movs     r5, r0
00493fc6  0e00       movs     r6, r1
00493fc8  1400       movs     r4, r2
00493fca  1f00       movs     r7, r3
00493fcc  dff86083   ldr.w    r8, [pc, #0x360]
00493fd0  3900       movs     r1, r7
00493fd2  2800       movs     r0, r5
00493fd4  d8f80020   ldr.w    r2, [r8]
00493fd8  9047       blx      r2
00493fda  3060       str      r0, [r6]
00493fdc  3068       ldr      r0, [r6]
00493fde  0028       cmp      r0, #0
00493fe0  06d0       beq      #0x493ff0
00493fe2  0021       movs     r1, #0
00493fe4  3868       ldr      r0, [r7]
00493fe6  2844       add      r0, r5
00493fe8  d8f80020   ldr.w    r2, [r8]
00493fec  9047       blx      r2
00493fee  00e0       b        #0x493ff2
00493ff0  0020       movs     r0, #0
00493ff2  2060       str      r0, [r4]
00493ff4  bde8f081   pop.w    {r4, r5, r6, r7, r8, pc}
00493ff8  0178       ldrb     r1, [r0]
00493ffa  0906       lsls     r1, r1, #0x18
00493ffc  01d4       bmi      #0x494002
00493ffe  0120       movs     r0, #1
00494000  15e0       b        #0x49402e
00494002  0178       ldrb     r1, [r0]
00494004  11f0e001   ands     r1, r1, #0xe0
00494008  c029       cmp      r1, #0xc0
0049400a  01d1       bne      #0x494010
0049400c  0220       movs     r0, #2
0049400e  0ee0       b        #0x49402e
00494010  0178       ldrb     r1, [r0]
00494012  11f0f001   ands     r1, r1, #0xf0
00494016  e029       cmp      r1, #0xe0
00494018  01d1       bne      #0x49401e
0049401a  0320       movs     r0, #3
0049401c  07e0       b        #0x49402e
0049401e  0078       ldrb     r0, [r0]
00494020  10f0f800   ands     r0, r0, #0xf8
00494024  f028       cmp      r0, #0xf0
00494026  01d1       bne      #0x49402c
00494028  0420       movs     r0, #4
0049402a  00e0       b        #0x49402e
0049402c  0020       movs     r0, #0
0049402e  7047       bx       lr
00494030  81b0       sub      sp, #4
00494032  8028       cmp      r0, #0x80
00494034  16d3       blo      #0x494064
00494036  b0f5006f   cmp.w    r0, #0x800
0049403a  15d2       bhs      #0x494068
0049403c  0100       movs     r1, r0
0049403e  8909       lsrs     r1, r1, #6
00494040  11f01f01   ands     r1, r1, #0x1f
00494044  51f0c001   orrs     r1, r1, #0xc0
00494048  8df80010   strb.w   r1, [sp]
0049404c  6946       mov      r1, sp
0049404e  10f03f00   ands     r0, r0, #0x3f
00494052  50f08000   orrs     r0, r0, #0x80
00494056  4870       strb     r0, [r1, #1]
00494058  0020       movs     r0, #0
0049405a  8870       strb     r0, [r1, #2]
0049405c  0020       movs     r0, #0
0049405e  c870       strb     r0, [r1, #3]
00494060  6846       mov      r0, sp
00494062  0068       ldr      r0, [r0]
00494064  01b0       add      sp, #4
00494066  7047       bx       lr
00494068  b0f5803f   cmp.w    r0, #0x10000
0049406c  17d2       bhs      #0x49409e
0049406e  0100       movs     r1, r0
00494070  090b       lsrs     r1, r1, #0xc
00494072  11f00f01   ands     r1, r1, #0xf
00494076  51f0e001   orrs     r1, r1, #0xe0
0049407a  8df80010   strb.w   r1, [sp]
0049407e  6946       mov      r1, sp
00494080  0200       movs     r2, r0
00494082  9209       lsrs     r2, r2, #6
00494084  12f03f02   ands     r2, r2, #0x3f
00494088  52f08002   orrs     r2, r2, #0x80
0049408c  4a70       strb     r2, [r1, #1]
0049408e  10f03f00   ands     r0, r0, #0x3f
00494092  50f08000   orrs     r0, r0, #0x80
00494096  8870       strb     r0, [r1, #2]
00494098  0020       movs     r0, #0
0049409a  c870       strb     r0, [r1, #3]
0049409c  e0e7       b        #0x494060
0049409e  b0f5881f   cmp.w    r0, #0x110000
004940a2  1cd2       bhs      #0x4940de
004940a4  0100       movs     r1, r0
004940a6  890c       lsrs     r1, r1, #0x12
004940a8  11f00701   ands     r1, r1, #7
004940ac  51f0f001   orrs     r1, r1, #0xf0
004940b0  8df80010   strb.w   r1, [sp]
004940b4  6946       mov      r1, sp
004940b6  0200       movs     r2, r0
004940b8  120b       lsrs     r2, r2, #0xc
004940ba  12f03f02   ands     r2, r2, #0x3f
004940be  52f08002   orrs     r2, r2, #0x80
004940c2  4a70       strb     r2, [r1, #1]
004940c4  0200       movs     r2, r0
004940c6  9209       lsrs     r2, r2, #6
004940c8  12f03f02   ands     r2, r2, #0x3f
004940cc  52f08002   orrs     r2, r2, #0x80
004940d0  8a70       strb     r2, [r1, #2]
004940d2  10f03f00   ands     r0, r0, #0x3f
004940d6  50f08000   orrs     r0, r0, #0x80
004940da  c870       strb     r0, [r1, #3]
004940dc  c0e7       b        #0x494060
004940de  0020       movs     r0, #0
004940e0  c0e7       b        #0x494064
004940e2  81b0       sub      sp, #4
004940e4  0022       movs     r2, #0
004940e6  0023       movs     r3, #0
004940e8  0093       str      r3, [sp]
004940ea  0029       cmp      r1, #0
004940ec  00d1       bne      #0x4940f0
004940ee  6946       mov      r1, sp
004940f0  0028       cmp      r0, #0
004940f2  03d0       beq      #0x4940fc
004940f4  0b68       ldr      r3, [r1]
004940f6  c35c       ldrb     r3, [r0, r3]
004940f8  002b       cmp      r3, #0
004940fa  01d1       bne      #0x494100
004940fc  1000       movs     r0, r2
004940fe  9de0       b        #0x49423c
00494100  0b68       ldr      r3, [r1]
00494102  c35c       ldrb     r3, [r0, r3]
00494104  1b06       lsls     r3, r3, #0x18
00494106  05d4       bmi      #0x494114
00494108  0a68       ldr      r2, [r1]
0049410a  825c       ldrb     r2, [r0, r2]
0049410c  0868       ldr      r0, [r1]
0049410e  401c       adds     r0, r0, #1
00494110  0860       str      r0, [r1]
00494112  92e0       b        #0x49423a
00494114  0b68       ldr      r3, [r1]
00494116  c35c       ldrb     r3, [r0, r3]
00494118  13f0e003   ands     r3, r3, #0xe0
0049411c  c02b       cmp      r3, #0xc0
0049411e  18d1       bne      #0x494152
00494120  0a68       ldr      r2, [r1]
00494122  835c       ldrb     r3, [r0, r2]
00494124  13f01f03   ands     r3, r3, #0x1f
00494128  9b01       lsls     r3, r3, #6
0049412a  0a68       ldr      r2, [r1]
0049412c  521c       adds     r2, r2, #1
0049412e  0a60       str      r2, [r1]
00494130  0a68       ldr      r2, [r1]
00494132  825c       ldrb     r2, [r0, r2]
00494134  12f0c002   ands     r2, r2, #0xc0
00494138  802a       cmp      r2, #0x80
0049413a  01d0       beq      #0x494140
0049413c  0020       movs     r0, #0
0049413e  7de0       b        #0x49423c
00494140  0a68       ldr      r2, [r1]
00494142  825c       ldrb     r2, [r0, r2]
00494144  12f03f02   ands     r2, r2, #0x3f
00494148  d218       adds     r2, r2, r3
0049414a  0868       ldr      r0, [r1]
0049414c  401c       adds     r0, r0, #1
0049414e  0860       str      r0, [r1]
00494150  73e0       b        #0x49423a
00494152  0b68       ldr      r3, [r1]
00494154  c35c       ldrb     r3, [r0, r3]
00494156  13f0f003   ands     r3, r3, #0xf0
0049415a  e02b       cmp      r3, #0xe0
0049415c  29d1       bne      #0x4941b2
0049415e  0a68       ldr      r2, [r1]
00494160  835c       ldrb     r3, [r0, r2]
00494162  13f00f03   ands     r3, r3, #0xf
00494166  1b03       lsls     r3, r3, #0xc
00494168  0a68       ldr      r2, [r1]
0049416a  521c       adds     r2, r2, #1
0049416c  0a60       str      r2, [r1]
0049416e  0a68       ldr      r2, [r1]
00494170  825c       ldrb     r2, [r0, r2]
00494172  12f0c002   ands     r2, r2, #0xc0
00494176  802a       cmp      r2, #0x80
00494178  01d0       beq      #0x49417e
0049417a  0020       movs     r0, #0
0049417c  5ee0       b        #0x49423c
0049417e  0a68       ldr      r2, [r1]
00494180  825c       ldrb     r2, [r0, r2]
00494182  12f03f02   ands     r2, r2, #0x3f
00494186  13eb8213   adds.w   r3, r3, r2, lsl #6
0049418a  0a68       ldr      r2, [r1]
0049418c  521c       adds     r2, r2, #1
0049418e  0a60       str      r2, [r1]
00494190  0a68       ldr      r2, [r1]
00494192  825c       ldrb     r2, [r0, r2]
00494194  12f0c002   ands     r2, r2, #0xc0
00494198  802a       cmp      r2, #0x80
0049419a  01d0       beq      #0x4941a0
0049419c  0020       movs     r0, #0
0049419e  4de0       b        #0x49423c
004941a0  0a68       ldr      r2, [r1]
004941a2  825c       ldrb     r2, [r0, r2]
004941a4  12f03f02   ands     r2, r2, #0x3f
004941a8  d218       adds     r2, r2, r3
004941aa  0868       ldr      r0, [r1]
004941ac  401c       adds     r0, r0, #1
004941ae  0860       str      r0, [r1]
004941b0  43e0       b        #0x49423a
004941b2  0b68       ldr      r3, [r1]
004941b4  c35c       ldrb     r3, [r0, r3]
004941b6  13f0f803   ands     r3, r3, #0xf8
004941ba  f02b       cmp      r3, #0xf0
004941bc  3ad1       bne      #0x494234
004941be  0a68       ldr      r2, [r1]
004941c0  835c       ldrb     r3, [r0, r2]
004941c2  13f00703   ands     r3, r3, #7
004941c6  9b04       lsls     r3, r3, #0x12
004941c8  0a68       ldr      r2, [r1]
004941ca  521c       adds     r2, r2, #1
004941cc  0a60       str      r2, [r1]
004941ce  0a68       ldr      r2, [r1]
004941d0  825c       ldrb     r2, [r0, r2]
004941d2  12f0c002   ands     r2, r2, #0xc0
004941d6  802a       cmp      r2, #0x80
004941d8  01d0       beq      #0x4941de
004941da  0020       movs     r0, #0
004941dc  2ee0       b        #0x49423c
004941de  0a68       ldr      r2, [r1]
004941e0  825c       ldrb     r2, [r0, r2]
004941e2  12f03f02   ands     r2, r2, #0x3f
004941e6  13eb0233   adds.w   r3, r3, r2, lsl #12
004941ea  0a68       ldr      r2, [r1]
004941ec  521c       adds     r2, r2, #1
004941ee  0a60       str      r2, [r1]
004941f0  0a68       ldr      r2, [r1]
004941f2  825c       ldrb     r2, [r0, r2]
004941f4  12f0c002   ands     r2, r2, #0xc0
004941f8  802a       cmp      r2, #0x80
004941fa  01d0       beq      #0x494200
004941fc  0020       movs     r0, #0
004941fe  1de0       b        #0x49423c
00494200  0a68       ldr      r2, [r1]
00494202  825c       ldrb     r2, [r0, r2]
00494204  12f03f02   ands     r2, r2, #0x3f
00494208  13eb8213   adds.w   r3, r3, r2, lsl #6
0049420c  0a68       ldr      r2, [r1]
0049420e  521c       adds     r2, r2, #1
00494210  0a60       str      r2, [r1]
00494212  0a68       ldr      r2, [r1]
