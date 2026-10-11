; Stock SHA-256: 26b6067665a441b779c47f6b95427b8b4bb5f502aaf527466dadce628aeb00b2
; Thumb addresses are installed MRAM addresses, not OTA file offsets.

; OTA flag read
0044a8d6  dff89005   ldr.w    r0, [pc, #0x590]
0044a8da  0068       ldr      r0, [r0]
0044a8dc  b0f1553f   cmp.w    r0, #0x55555555
0044a8e0  08d1       bne      #0x44a8f4
0044a8e2  3cf0a7fc   bl       #0x487234

; MRAM settings write
00481a88  2e00       movs     r6, r5
00481a8a  3000       movs     r0, r6
00481a8c  baf72afb   bl       #0x43c0e4
00481a90  f8f7f2fa   bl       #0x47a078
00481a94  0600       movs     r6, r0
00481a96  2388       ldrh     r3, [r4]
00481a98  9bb2       uxth     r3, r3
00481a9a  9b08       lsrs     r3, r3, #2
00481a9c  9bb2       uxth     r3, r3
00481a9e  724a       ldr      r2, [pc, #0x1c8]
00481aa0  2900       movs     r1, r5
00481aa2  7248       ldr      r0, [pc, #0x1c8]
00481aa4  63f044fd   bl       #0x4e5530
00481aa8  0400       movs     r4, r0
00481aaa  3000       movs     r0, r6
00481aac  80f31088   msr      primask, r0

; OTA flag write
00481b40  38b5       push     {r3, r4, r5, lr}
00481b42  88b0       sub      sp, #0x20
00481b44  0500       movs     r5, r0
00481b46  4e4c       ldr      r4, [pc, #0x138]
00481b48  bbf76ffd   bl       #0x43d62a
00481b4c  8007       lsls     r0, r0, #0x1e
00481b4e  0cd5       bpl      #0x481b6a
00481b50  0395       str      r5, [sp, #0xc]
00481b52  2068       ldr      r0, [r4]
00481b54  0290       str      r0, [sp, #8]
00481b56  4b48       ldr      r0, [pc, #0x12c]
00481b58  0190       str      r0, [sp, #4]
00481b5a  d620       movs     r0, #0xd6
00481b5c  0090       str      r0, [sp]
00481b5e  4a4b       ldr      r3, [pc, #0x128]
00481b60  3c4a       ldr      r2, [pc, #0xf0]
00481b62  3d49       ldr      r1, [pc, #0xf4]
00481b64  0420       movs     r0, #4
00481b66  bcf707f8   bl       #0x43db78
00481b6a  bbf75efd   bl       #0x43d62a
00481b6e  c007       lsls     r0, r0, #0x1f
00481b70  03d4       bmi      #0x481b7a
00481b72  bbf75afd   bl       #0x43d62a
00481b76  4007       lsls     r0, r0, #0x1d
00481b78  07d5       bpl      #0x481b8a
00481b7a  4449       ldr      r1, [pc, #0x110]
00481b7c  0095       str      r5, [sp]
00481b7e  2368       ldr      r3, [r4]
00481b80  0a00       movs     r2, r1
00481b82  5ff08450   movs.w   r0, #0x10800000
00481b86  bbf79af9   bl       #0x43cebe
00481b8a  2023       movs     r3, #0x20
00481b8c  2200       movs     r2, r4
00481b8e  1021       movs     r1, #0x10
00481b90  3f48       ldr      r0, [pc, #0xfc]
00481b92  bcf79dfa   bl       #0x43e0d0
00481b96  2068       ldr      r0, [r4]
00481b98  8542       cmp      r5, r0
00481b9a  52d0       beq      #0x481c42
00481b9c  04a8       add      r0, sp, #0x10
00481b9e  3d49       ldr      r1, [pc, #0xf4]
00481ba0  1022       movs     r2, #0x10
00481ba2  b8f72ff8   bl       #0x439c04
00481ba6  0495       str      r5, [sp, #0x10]
00481ba8  bbf73ffd   bl       #0x43d62a
00481bac  8007       lsls     r0, r0, #0x1e
00481bae  0bd5       bpl      #0x481bc8
00481bb0  0395       str      r5, [sp, #0xc]
00481bb2  0294       str      r4, [sp, #8]
00481bb4  3848       ldr      r0, [pc, #0xe0]
00481bb6  0190       str      r0, [sp, #4]
00481bb8  dd20       movs     r0, #0xdd
00481bba  0090       str      r0, [sp]
00481bbc  324b       ldr      r3, [pc, #0xc8]
00481bbe  254a       ldr      r2, [pc, #0x94]
00481bc0  2549       ldr      r1, [pc, #0x94]
00481bc2  0420       movs     r0, #4
00481bc4  bbf7d8ff   bl       #0x43db78
00481bc8  bbf72ffd   bl       #0x43d62a
00481bcc  c007       lsls     r0, r0, #0x1f
00481bce  03d4       bmi      #0x481bd8
00481bd0  bbf72bfd   bl       #0x43d62a
00481bd4  4007       lsls     r0, r0, #0x1d
00481bd6  07d5       bpl      #0x481be8
00481bd8  304a       ldr      r2, [pc, #0xc0]
00481bda  0095       str      r5, [sp]
00481bdc  2300       movs     r3, r4
00481bde  1100       movs     r1, r2
00481be0  5ff08450   movs.w   r0, #0x10800000
00481be4  bbf76bf9   bl       #0x43cebe
00481be8  f8f746fa   bl       #0x47a078
00481bec  0500       movs     r5, r0
00481bee  0423       movs     r3, #4
00481bf0  2200       movs     r2, r4
00481bf2  04a9       add      r1, sp, #0x10
00481bf4  1d48       ldr      r0, [pc, #0x74]
00481bf6  63f09bfc   bl       #0x4e5530
00481bfa  0400       movs     r4, r0
00481bfc  2800       movs     r0, r5
00481bfe  80f31088   msr      primask, r0
00481c02  002c       cmp      r4, #0
00481c04  1dd0       beq      #0x481c42
00481c06  bbf710fd   bl       #0x43d62a
00481c0a  8007       lsls     r0, r0, #0x1e
00481c0c  0ad5       bpl      #0x481c24
00481c0e  0294       str      r4, [sp, #8]
00481c10  1748       ldr      r0, [pc, #0x5c]
00481c12  0190       str      r0, [sp, #4]
00481c14  e720       movs     r0, #0xe7
00481c16  0090       str      r0, [sp]
00481c18  1b4b       ldr      r3, [pc, #0x6c]
00481c1a  0e4a       ldr      r2, [pc, #0x38]
00481c1c  0e49       ldr      r1, [pc, #0x38]
00481c1e  0120       movs     r0, #1
00481c20  bbf7aaff   bl       #0x43db78
00481c24  bbf701fd   bl       #0x43d62a
00481c28  c007       lsls     r0, r0, #0x1f
00481c2a  03d4       bmi      #0x481c34
00481c2c  bbf7fdfc   bl       #0x43d62a
00481c30  4007       lsls     r0, r0, #0x1d
00481c32  06d5       bpl      #0x481c42
00481c34  1049       ldr      r1, [pc, #0x40]
00481c36  2300       movs     r3, r4
00481c38  0a00       movs     r2, r1
00481c3a  5ff08860   movs.w   r0, #0x4400000
00481c3e  bbf73ef9   bl       #0x43cebe
00481c42  09b0       add      sp, #0x24
00481c44  30bd       pop      {r4, r5, pc}
