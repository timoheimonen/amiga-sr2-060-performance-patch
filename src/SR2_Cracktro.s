; Camaro splash before img.cru. KS3.1/AGA, PAL 640x512, 16 colours.
; Intuition owns the display and input. No custom-chip/CIA takeover.
; A press AND release of Space or any mouse button dismisses the screen,
; so the same held button cannot also dismiss the following cracktro.
        section code,code
start:
        movem.l d2-d7/a2-a6,-(sp)
        moveq   #0,d5
        moveq   #0,d6
        moveq   #1,d7
        move.l  4.w,a6
        lea     intuition_name(pc),a1
        moveq   #39,d0
        jsr     -552(a6)               ; OpenLibrary
        move.l  d0,intuition_base
        beq     finish
        moveq   #2,d7
        lea     graphics_name(pc),a1
        moveq   #39,d0
        jsr     -552(a6)
        move.l  d0,graphics_base
        beq     cleanup
        moveq   #3,d7
        move.l  intuition_base,a6
        suba.l  a0,a0
        lea     screen_tags(pc),a1
        jsr     -612(a6)               ; OpenScreenTagList
        move.l  d0,screen
        bne.s   .screen_ok
        move.l  screen_error,d0
        add.b   #'0',d0
        move.b  d0,error_digit
        bra     cleanup
.screen_ok:
        move.l  screen,d0
        move.l  d0,window_screen
        moveq   #4,d7
        lea     new_window(pc),a0
        jsr     -204(a6)               ; OpenWindow
        move.l  d0,window
        beq     cleanup
        moveq   #0,d7
        move.l  d0,a0
        lea     blank_pointer,a1
        moveq   #1,d0
        moveq   #16,d1
        moveq   #0,d2
        moveq   #0,d3
        jsr     -270(a6)               ; SetPointer (transparent CHIP sprite)
        move.l  graphics_base,a6
        jsr     -228(a6)               ; WaitBlit before filling the bitmap
        move.l  screen,a0
        move.l  88(a0),a2              ; Screen.RastPort.BitMap (not obsolete BitMap)
        lea     8(a2),a3               ; BitMap.Planes[]
        lea     planar,a0
        moveq   #3,d3
.plane:
        move.l  (a3)+,a1
        move.w  #511,d2
.row:
        moveq   #19,d1                 ; 640 pixels = 80 bytes
.copy:
        move.l  (a0)+,(a1)+
        dbra    d1,.copy
        moveq   #0,d0
        move.w  (a2),d0                ; honour actual BitMap.BytesPerRow
        sub.w   #80,d0
        adda.l  d0,a1
        dbra    d2,.row
        dbra    d3,.plane
        move.l  screen,a0
        lea     44(a0),a0              ; Screen.ViewPort
        lea     colors,a1
        jsr     -882(a6)               ; LoadRGB32
        move.l  intuition_base,a6
        move.l  screen,a0
        jsr     -252(a6)               ; ScreenToFront, fully prepared
        move.l  window,a0
        move.l  86(a0),a4              ; Window.UserPort
        move.l  4.w,a6
wait_input:
        move.l  a4,a0
        jsr     -384(a6)               ; WaitPort, no busy loop
.messages:
        move.l  a4,a0
        jsr     -372(a6)               ; GetMsg
        tst.l   d0
        beq.s   wait_input
        move.l  d0,a1
        move.l  20(a1),d2              ; IntuiMessage.Class
        moveq   #0,d3
        move.w  24(a1),d3              ; IntuiMessage.Code
        jsr     -378(a6)               ; ReplyMsg before processing/closing
        tst.l   d6
        bne.s   .release
        cmp.l   #$400,d2               ; IDCMP_RAWKEY
        bne.s   .mouse
        cmp.w   #$40,d3                ; Space down
        bne.s   .messages
        bra.s   .pressed
.mouse:
        cmp.l   #8,d2                  ; IDCMP_MOUSEBUTTONS
        bne.s   .messages
        cmp.w   #$68,d3                ; left / right / middle down
        blo.s   .messages
        cmp.w   #$6a,d3
        bhi.s   .messages
.pressed:
        move.l  d2,d6
        move.w  d3,d5
        or.w    #$80,d5                ; corresponding release code
        bra.s   .messages
.release:
        cmp.l   d2,d6
        bne.s   .messages
        cmp.w   d3,d5
        bne.s   .messages
cleanup:
        move.l  intuition_base,a6
        move.l  window,d0
        beq.s   .no_window
        move.l  d0,a0
        jsr     -72(a6)                ; CloseWindow drains its private IDCMP port
.no_window:
        move.l  screen,d0
        beq.s   .no_screen
        move.l  d0,a0
        jsr     -66(a6)                ; CloseScreen frees display bitmap
.no_screen:
        move.l  4.w,a6
        move.l  graphics_base,d0
        beq.s   .no_graphics
        move.l  d0,a1
        jsr     -414(a6)
.no_graphics:
        move.l  intuition_base,a1
        jsr     -414(a6)
finish:
        tst.l   d7
        beq.s   .done
        move.l  4.w,a6
        lea     dos_name(pc),a1
        moveq   #0,d0
        jsr     -552(a6)
        tst.l   d0
        beq.s   .done
        move.l  d0,a6
        jsr     -60(a6)                ; Output
        move.l  d0,d1
        lea     error_texts(pc),a0
        subq.w  #1,d7
        lsl.w   #2,d7
        move.l  (a0,d7.w),d2
        move.l  d2,a0
        moveq   #0,d3
.length:
        tst.b   (a0)+
        beq.s   .write
        addq.l  #1,d3
        bra.s   .length
.write:
        jsr     -48(a6)                ; Write diagnostic, then continue boot
        move.l  a6,a1
        move.l  4.w,a6
        jsr     -414(a6)
.done:
        moveq   #0,d0                  ; continue startup even if screen open fails
        movem.l (sp)+,d2-d7/a2-a6
        rts

intuition_name: dc.b 'intuition.library',0
graphics_name:  dc.b 'graphics.library',0
dos_name: dc.b 'dos.library',0
error_intuition: dc.b 'SR2 splash: intuition.library unavailable.',10,0
error_graphics: dc.b 'SR2 splash: graphics.library unavailable.',10,0
error_screen: dc.b 'SR2 splash: cannot open screen (error '
error_digit: dc.b '0',').',10,0
error_window: dc.b 'SR2 splash: cannot open input window.',10,0
        even
error_texts: dc.l error_intuition,error_graphics,error_screen,error_window
screen_tags:
        dc.l    $8000002a,screen_error ; SA_ErrorCode
        dc.l    $80000023,640          ; SA_Width
        dc.l    $80000024,512          ; SA_Height
        dc.l    $80000025,4            ; SA_Depth
        dc.l    $80000032,$00008004    ; default monitor HIRESLACE (PAL boot)
        dc.l    $80000036,0            ; SA_ShowTitle
        dc.l    $80000037,1            ; SA_Behind
        dc.l    $80000038,1            ; SA_Quiet
        dc.l    $8000003e,0            ; SA_Draggable
        dc.l    0,0
new_window:
        dc.w    0,0,640,512
        dc.b    0,0
        dc.l    $408                  ; IDCMP_RAWKEY | IDCMP_MOUSEBUTTONS
        dc.l    $31940                ; BORDERLESS|ACTIVATE|BACKDROP|RMBTRAP|
                                      ; SIMPLE_REFRESH|NOCAREREFRESH
        dc.l    0,0,0
window_screen: dc.l 0
        dc.l    0
        dc.w    0,0,640,512,$f         ; CUSTOMSCREEN
intuition_base: dc.l 0
graphics_base: dc.l 0
screen: dc.l 0
screen_error: dc.l 0
window: dc.l 0
colors: incbin 'cracktro-colors.bin'
        section picture,data
planar: incbin 'cracktro-planar.bin'
        section sprite,data_c
blank_pointer: dcb.l 3,0
