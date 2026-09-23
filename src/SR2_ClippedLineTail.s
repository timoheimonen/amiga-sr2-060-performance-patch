***************************************************************************
* Street Rod 2 KS3.1/68060 clipped-line tail
*
* The first accepted colour-15 line keeps the original RastPort preparation
* and SetAPen.  Later colour-15 lines in the same covered-span batch replay
* Kickstart 3.1 graphics.library 40.24 Move's four RastPort state writes and
* retain the original Draw call. Other callers use the original setup path.
***************************************************************************

SR2_COVERED_MARKER_CLEAR = $53523230
SR2_COVERED_MARKER_READY = $53523231

RP_LINPATCNT = 30
RP_FLAGS     = 32
RP_CP_X      = 36
RP_CP_Y      = 38
FRST_DOT     = 1

        SECTION clipped_line_tail,CODE

_clipped_line_tail_dispatch
        move.l  (a7)+,a0
        addq.l  #2,a0
        cmpa.l  #SR2_COVERED_MARKER_CLEAR,a3
        beq.b   .inside_batch
        cmpa.l  #SR2_COVERED_MARKER_READY,a3
        bne.b   .prepare

.inside_batch
        cmpi.w  #15,16(a5)
        bne.b   .other_pen
        cmpa.l  #SR2_COVERED_MARKER_READY,a3
        beq.b   .move
        movea.l #SR2_COVERED_MARKER_READY,a3
        bra.b   .prepare

.other_pen
        movea.l #SR2_COVERED_MARKER_CLEAR,a3

.prepare
        move.l  a0,-(a7)
        lea     $321a(a0),a0
        jsr     (a0)
        move.l  (a7)+,a0
        move.w  16(a5),d0
        addq.l  #2,a0
        jmp     (a0)

.move
        * KS3.1 A1200 40.68 Move at ROM $f86fbc writes CP_X,
        * CP_Y, FRST_DOT and the byte at RastPort offset 30.
        * Verified from the running ROM; do not reuse the KS1.3 offset 31.
        lea     -$4d0(a4),a1
        move.w  d7,RP_CP_X(a1)
        move.w  d6,RP_CP_Y(a1)
        ori.w   #FRST_DOT,RP_FLAGS(a1)
        move.b  #15,RP_LINPATCNT(a1)
        lea     $24(a0),a0
        jmp     (a0)

        CNOP    0,4

        * Entry offset $64 of this HUNK 45 payload.
        INCLUDE "SR2_AreaFill.s"

        END
