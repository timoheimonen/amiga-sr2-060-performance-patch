; KS3.1 PAL driving display: recycle road buffers outside their DMA scan.
; The verified Copper loads the top pointers at line 42, displays the road
; on 44..143, and loads independent cockpit pointers at line 144.
; Keep margins on both sides, and publish each image for at least one scan.
; Appended to HUNK 10. Original WaitBlit and buffer-index toggle precede us;
; original descriptor exchange and register restoration follow us.
HUNK_SIZE       = $5f0
COPY_OFFSET     = $554           ; original $9b6c
RESUME_OFFSET   = $578           ; original $9b90
_LVODisable     = -120
_LVOEnable      = -126
_LVOWaitTOF     = -270
        SECTION swap,CODE
swap_wait
        lea     swap_state(pc),a3
        tst.w   -$408a(a4)
        beq.w   swap_fallback
swap_poll
        ; At the end of a PAL field, sleep instead of polling across wrap.
        move.l  $dff004,d0
        lsr.l   #8,d0
        andi.w  #$1ff,d0
        cmpi.w  #300,d0
        bls.b   .check
        movea.l -$63a8(a4),a6
        jsr     _LVOWaitTOF(a6)
.check
        bsr.w   eligible
        tst.w   d0
        beq.b   swap_poll
        movea.l 4.w,a6
        jsr     _LVODisable(a6)
        ; Recheck after masking interrupts: a preemption may have consumed
        ; the safe interval. Never wait with interrupts disabled.
        bsr.w   eligible
        tst.w   d0
        beq.b   swap_unlock_retry
        add.l   d7,d1           ; late publish is first displayed next field
        move.l  d1,4(a3)
        move.w  #1,(a3)
        move.w  -$4064(a4),d0
        muls.w  #48,d0
        lea     -$4062(a4),a0
        adda.l  d0,a0
        movea.l -$464(a4),a1
publish_begin
        moveq   #11,d0
.copy
        move.l  (a0)+,(a1)+
        dbf     d0,.copy
publish_end
        jsr     _LVOEnable(a6)
        dc.w    $6000
.resume
        dc.w    RESUME_OFFSET-HUNK_SIZE-(.resume-swap_wait)
swap_unlock_retry
        jsr     _LVOEnable(a6)
        bra.b   swap_poll
swap_fallback
        clr.w   (a3)
        movea.l -$63a8(a4),a6
        jsr     _LVOWaitTOF(a6)
        dc.w    $6000
.old_copy
        dc.w    COPY_OFFSET-HUNK_SIZE-(.old_copy-swap_wait)

; D0=1 if safe; D1=current VBlank count; D7=0 early / 1 late.
; first_display_field records when the last published image first reaches
; the road. Early in that field it must not be replaced; late is safe.
; Signed modular differences also handle the 32-bit counter wrapping.
eligible
        move.l  $dff004,d0
        lsr.l   #8,d0
        andi.w  #$1ff,d0
        cmpi.w  #8,d0           ; exclude the VBlank interrupt boundary
        blo.b   .no
        moveq   #0,d7
        cmpi.w  #30,d0
        bls.b   .field
        cmpi.w  #150,d0
        blo.b   .no
        cmpi.w  #300,d0
        bhi.b   .no
        moveq   #1,d7
.field
        move.l  -$20b6(a4),d1
        tst.w   (a3)
        beq.b   .yes
        move.l  d1,d0
        sub.l   4(a3),d0
        bmi.b   .no
        bne.b   .yes
        tst.w   d7
        beq.b   .no
.yes
        moveq   #1,d0
        rts
.no
        moveq   #0,d0
        rts

reset_swap
        lea     swap_state(pc),a0
        clr.w   (a0)
        clr.w   -$4064(a4)      ; replay original $96d2
        rts
        cnop    0,4
swap_state
        dc.w    0,0
first_display_field
        dc.l    0
        END
