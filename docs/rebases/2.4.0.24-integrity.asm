; Stock SHA-256: 363198f8d543a5c1181d8a213e9077285cb865700a1885c8dc7c1b9324fd0e05
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; OTA flag read
0044ac68  dff8a405   ldr.w    r0, [pc, #0x5a4]
0044ac6c  0068       ldr      r0, [r0]
0044ac6e  b0f1553f   cmp.w    r0, #0x55555555
0044ac72  08d1       bne      #0x44ac86
0044ac74  47f010fc   bl       #0x492498

; MRAM settings write
00483650  2e00       movs     r6, r5
00483652  3000       movs     r0, r6
00483654  b8f746fd   bl       #0x43c0e4
00483658  fbf726f8   bl       #0x47e6a8
0048365c  0600       movs     r6, r0
0048365e  2388       ldrh     r3, [r4]
00483660  9bb2       uxth     r3, r3
00483662  9b08       lsrs     r3, r3, #2
00483664  9bb2       uxth     r3, r3
00483666  724a       ldr      r2, [pc, #0x1c8]
00483668  2900       movs     r1, r5
0048366a  7248       ldr      r0, [pc, #0x1c8]
0048366c  72f0faf8   bl       #0x4f5864
00483670  0400       movs     r4, r0
00483672  3000       movs     r0, r6
00483674  80f31088   msr      primask, r0

; OTA flag write
00483708  38b5       push     {r3, r4, r5, lr}
0048370a  88b0       sub      sp, #0x20
0048370c  0500       movs     r5, r0
0048370e  4e4c       ldr      r4, [pc, #0x138]
00483710  b9f78bff   bl       #0x43d62a
00483714  8007       lsls     r0, r0, #0x1e
00483716  0cd5       bpl      #0x483732
00483718  0395       str      r5, [sp, #0xc]
0048371a  2068       ldr      r0, [r4]
0048371c  0290       str      r0, [sp, #8]
0048371e  4b48       ldr      r0, [pc, #0x12c]
00483720  0190       str      r0, [sp, #4]
00483722  d620       movs     r0, #0xd6
00483724  0090       str      r0, [sp]
00483726  4a4b       ldr      r3, [pc, #0x128]
00483728  3c4a       ldr      r2, [pc, #0xf0]
0048372a  3d49       ldr      r1, [pc, #0xf4]
0048372c  0420       movs     r0, #4
0048372e  baf723fa   bl       #0x43db78
00483732  b9f77aff   bl       #0x43d62a
00483736  c007       lsls     r0, r0, #0x1f
00483738  03d4       bmi      #0x483742
0048373a  b9f776ff   bl       #0x43d62a
0048373e  4007       lsls     r0, r0, #0x1d
00483740  07d5       bpl      #0x483752
00483742  4449       ldr      r1, [pc, #0x110]
00483744  0095       str      r5, [sp]
00483746  2368       ldr      r3, [r4]
00483748  0a00       movs     r2, r1
0048374a  5ff08450   movs.w   r0, #0x10800000
0048374e  b9f7b6fb   bl       #0x43cebe
00483752  2023       movs     r3, #0x20
00483754  2200       movs     r2, r4
00483756  1021       movs     r1, #0x10
00483758  3f48       ldr      r0, [pc, #0xfc]
0048375a  baf7b9fc   bl       #0x43e0d0
0048375e  2068       ldr      r0, [r4]
00483760  8542       cmp      r5, r0
00483762  52d0       beq      #0x48380a
00483764  04a8       add      r0, sp, #0x10
00483766  3d49       ldr      r1, [pc, #0xf4]
00483768  1022       movs     r2, #0x10
0048376a  b6f74bfa   bl       #0x439c04
0048376e  0495       str      r5, [sp, #0x10]
00483770  b9f75bff   bl       #0x43d62a
00483774  8007       lsls     r0, r0, #0x1e
00483776  0bd5       bpl      #0x483790
00483778  0395       str      r5, [sp, #0xc]
0048377a  0294       str      r4, [sp, #8]
0048377c  3848       ldr      r0, [pc, #0xe0]
0048377e  0190       str      r0, [sp, #4]
00483780  dd20       movs     r0, #0xdd
00483782  0090       str      r0, [sp]
00483784  324b       ldr      r3, [pc, #0xc8]
00483786  254a       ldr      r2, [pc, #0x94]
00483788  2549       ldr      r1, [pc, #0x94]
0048378a  0420       movs     r0, #4
0048378c  baf7f4f9   bl       #0x43db78
00483790  b9f74bff   bl       #0x43d62a
00483794  c007       lsls     r0, r0, #0x1f
00483796  03d4       bmi      #0x4837a0
00483798  b9f747ff   bl       #0x43d62a
0048379c  4007       lsls     r0, r0, #0x1d
0048379e  07d5       bpl      #0x4837b0
004837a0  304a       ldr      r2, [pc, #0xc0]
004837a2  0095       str      r5, [sp]
004837a4  2300       movs     r3, r4
004837a6  1100       movs     r1, r2
004837a8  5ff08450   movs.w   r0, #0x10800000
004837ac  b9f787fb   bl       #0x43cebe
004837b0  faf77aff   bl       #0x47e6a8
004837b4  0500       movs     r5, r0
004837b6  0423       movs     r3, #4
004837b8  2200       movs     r2, r4
004837ba  04a9       add      r1, sp, #0x10
004837bc  1d48       ldr      r0, [pc, #0x74]
004837be  72f051f8   bl       #0x4f5864
004837c2  0400       movs     r4, r0
004837c4  2800       movs     r0, r5
004837c6  80f31088   msr      primask, r0
004837ca  002c       cmp      r4, #0
004837cc  1dd0       beq      #0x48380a
004837ce  b9f72cff   bl       #0x43d62a
004837d2  8007       lsls     r0, r0, #0x1e
004837d4  0ad5       bpl      #0x4837ec
004837d6  0294       str      r4, [sp, #8]
004837d8  1748       ldr      r0, [pc, #0x5c]
004837da  0190       str      r0, [sp, #4]
004837dc  e720       movs     r0, #0xe7
004837de  0090       str      r0, [sp]
004837e0  1b4b       ldr      r3, [pc, #0x6c]
004837e2  0e4a       ldr      r2, [pc, #0x38]
004837e4  0e49       ldr      r1, [pc, #0x38]
004837e6  0120       movs     r0, #1
004837e8  baf7c6f9   bl       #0x43db78
004837ec  b9f71dff   bl       #0x43d62a
004837f0  c007       lsls     r0, r0, #0x1f
004837f2  03d4       bmi      #0x4837fc
004837f4  b9f719ff   bl       #0x43d62a
004837f8  4007       lsls     r0, r0, #0x1d
004837fa  06d5       bpl      #0x48380a
004837fc  1049       ldr      r1, [pc, #0x40]
004837fe  2300       movs     r3, r4
00483800  0a00       movs     r2, r1
00483802  5ff08860   movs.w   r0, #0x4400000
00483806  b9f75afb   bl       #0x43cebe
0048380a  09b0       add      sp, #0x24
0048380c  30bd       pop      {r4, r5, pc}
