; Appended to HUNK 0 in every patched build. Keep this entry at +$60,
; after either cache wrapper, so all variants share the original +4 hook.
        dcb.b   $60-(*-payload_begin),0
startup_dispatch
        movem.l d0-d7/a0-a6,-(sp)
        ; LoadSeg links sit four bytes before each segment's code. Follow
        ; ten BPTR links, rather than assuming contiguous allocations.
        lea     startup_dispatch(pc),a0
        suba.l  #$334c+$60+4,a0
        moveq   #9,d0
.next
        move.l  (a0),d1
        lsl.l   #2,d1
        movea.l d1,a0
        dbf     d0,.next
        lea     $784(a0),a2     ; HUNK 10 + $780: startup_menu
        move.l  (sp),d0        ; original command-line length and pointer
        movea.l 32(sp),a0
        jsr     (a2)
        movem.l (sp)+,d0-d7/a0-a6
        movea.l a0,a2          ; replay original HUNK 0 +4..+7
        move.l  d0,d2
        rts
        cnop    0,4
