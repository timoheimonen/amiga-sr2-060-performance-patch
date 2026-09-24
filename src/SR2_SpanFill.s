***************************************************************************
* Street Rod 2 KS3.1/AGA span fill for the covered-span helpers
*
* Same result as the original FUN_00001798: fill the rectangle x1..x2,
* y1..y2 (words at 4..10(SP), colour at 12(SP)) in the four road planes.
* x is ordered and clamped to the view (A4-$28f6/-$28f0), y1 is clamped to
* the top and y2 to the bottom limit (A4-$28f4/-$28f2).  Rows are 40 bytes
* and planes 4000 bytes apart from Planes[0] of the BitMap at 4(-$46c(A4)),
* exactly as in the original.  Colour bits 0..3 set or clear each plane.
*
* The original calls two subroutines and a computed jump for every row and
* plane.  Here the masks are computed once and every plane has one direct
* row loop.  Called by JSR (d16,PC) from draw_covered_span_frame and
* draw_covered_span_cap; clobbers only D0/D1/A0/A1 like the original.
* The game's view limits keep x in 0..319 and y in 0..99: at most 9 longs
* follow the first one (within the original's eight-long middle table) and
* the original 16-bit row-offset arithmetic cannot wrap.
***************************************************************************

SF_XMIN         = -$28f6
SF_YMIN         = -$28f4
SF_YMAX         = -$28f2
SF_XMAX         = -$28f0
SF_RASTPORT_PTR = -$46c
SF_ROW_BYTES    = 40
SF_PLANE_BYTES  = 4000

_span_fill
        movem.l d2-d7/a2-a3,-(a7)
        movem.w 36(a7),d2-d6            ; x1, x2, y1, y2, colour
        cmp.w   d3,d2
        blt.b   .ordered
        exg     d2,d3                   ; D2 = left, D3 = right
.ordered
        cmp.w   SF_XMIN(a4),d2
        bge.b   .left_ok
        move.w  SF_XMIN(a4),d2
.left_ok
        cmp.w   SF_XMAX(a4),d3
        ble.b   .right_ok
        move.w  SF_XMAX(a4),d3
.right_ok
        cmp.w   d2,d3
        blt.w   .done
        cmp.w   SF_YMIN(a4),d4
        bge.b   .top_ok
        move.w  SF_YMIN(a4),d4
.top_ok
        cmp.w   SF_YMAX(a4),d5
        ble.b   .bottom_ok
        move.w  SF_YMAX(a4),d5
.bottom_ok
        cmp.w   d4,d5
        blt.w   .done
        sub.w   d4,d5
        mulu.w  #SF_ROW_BYTES,d5        ; offset of the last row
        mulu.w  #SF_ROW_BYTES,d4
        movea.l SF_RASTPORT_PTR(a4),a3
        movea.l 4(a3),a3
        movea.l 8(a3),a3
        adda.l  d4,a3                   ; plane 0, first row

        move.w  d2,d7
        lsr.w   #5,d7                   ; first long
        move.w  d3,d0
        lsr.w   #5,d0
        sub.w   d7,d0
        movea.w d0,a1                   ; longs after the first
        lsl.w   #2,d7                   ; byte offset of the first long
        andi.w  #31,d2
        moveq   #-1,d0
        lsr.l   d2,d0
        move.l  d0,d2                   ; left mask
        not.w   d3
        andi.w  #31,d3
        moveq   #-1,d0
        lsl.l   d3,d0
        move.l  d0,d3                   ; right mask
        move.w  a1,d0
        bne.b   .masks_done
        and.l   d3,d2                   ; one long: combined mask
.masks_done
        moveq   #3,d4                   ; planes - 1

.plane
        move.w  d5,d0
        lsr.b   #1,d6                   ; next colour bit
        bcc.b   .clear_plane
.set_row
        lea     (a3,d0.w),a0
        adda.w  d7,a0
        or.l    d2,(a0)+
        move.w  a1,d1
        beq.b   .set_next
        subq.w  #1,d1
        bra.b   .set_test
.set_middle
        move.l  #-1,(a0)+
.set_test
        dbra    d1,.set_middle
        or.l    d3,(a0)
.set_next
        subi.w  #SF_ROW_BYTES,d0
        bpl.b   .set_row
        bra.b   .plane_done

.clear_plane
        not.l   d2
        not.l   d3
.clear_row
        lea     (a3,d0.w),a0
        adda.w  d7,a0
        and.l   d2,(a0)+
        move.w  a1,d1
        beq.b   .clear_next
        subq.w  #1,d1
        bra.b   .clear_test
.clear_middle
        clr.l   (a0)+
.clear_test
        dbra    d1,.clear_middle
        and.l   d3,(a0)
.clear_next
        subi.w  #SF_ROW_BYTES,d0
        bpl.b   .clear_row
        not.l   d2
        not.l   d3

.plane_done
        lea     SF_PLANE_BYTES(a3),a3
        dbra    d4,.plane
.done
        movem.l (a7)+,d2-d7/a2-a3
        rts
