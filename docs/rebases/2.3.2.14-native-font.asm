; Authenticated stock SHA-256 26b6067665a441b779c47f6b95427b8b4bb5f502aaf527466dadce628aeb00b2
; native font dispatch
004716fe 3eb5       push     {r1, r2, r3, r4, r5, lr}
00471700 0400       movs     r4, r0
00471702 002c       cmp      r4, #0
00471704 01d1       bne      #0x47170a
00471706 0020       movs     r0, #0
00471708 d1e0       b        #0x4718ae
0047170a 2078       ldrb     r0, [r4]
0047170c 0028       cmp      r0, #0
0047170e 04d0       beq      #0x47171a
00471710 0228       cmp      r0, #2
00471712 00f08280   beq.w    #0x47181a
00471716 29d3       blo      #0x47176c
00471718 a3e0       b        #0x471862
0047171a 6068       ldr      r0, [r4, #4]
0047171c 0028       cmp      r0, #0
0047171e 01d0       beq      #0x471724
00471720 6068       ldr      r0, [r4, #4]
00471722 c4e0       b        #0x4718ae
; native outline font creation
0047176c 6068       ldr      r0, [r4, #4]
0047176e 0028       cmp      r0, #0
00471770 2fd0       beq      #0x4717d2
00471772 a37a       ldrb     r3, [r4, #0xa]
00471774 2289       ldrh     r2, [r4, #8]
00471776 0121       movs     r1, #1
00471778 6068       ldr      r0, [r4, #4]
0047177a 51f015fb   bl       #0x4c2da8
; outline factory entry
004c2da8 2de9f847   push.w   {r3, r4, r5, r6, r7, r8, sb, sl, lr}
004c2dac 8bb0       sub      sp, #0x2c
004c2dae 0400       movs     r4, r0
004c2db0 0e00       movs     r6, r1
004c2db2 1f00       movs     r7, r3
004c2db4 002c       cmp      r4, #0
004c2db6 15d1       bne      #0x4c2de4
004c2db8 dff8e005   ldr.w    r0, [pc, #0x5e0]
004c2dbc 0290       str      r0, [sp, #8]
004c2dbe dff8e005   ldr.w    r0, [pc, #0x5e0]
004c2dc2 0190       str      r0, [sp, #4]
004c2dc4 dff8bc05   ldr.w    r0, [pc, #0x5bc]
004c2dc8 0090       str      r0, [sp]
004c2dca dff8d835   ldr.w    r3, [pc, #0x5d8]
004c2dce 7422       movs     r2, #0x74
004c2dd0 dff8a415   ldr.w    r1, [pc, #0x5a4]
004c2dd4 0320       movs     r0, #3
004c2dd6 8df72ffa   bl       #0x450238
004c2dda 0020       movs     r0, #0
004c2ddc 5ff0ff31   movs.w   r1, #-1
