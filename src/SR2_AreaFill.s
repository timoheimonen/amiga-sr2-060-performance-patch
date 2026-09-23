***************************************************************************
* Street Rod 2 KS3.1/AGA CPU fill for draw_area_polygon
*
* The game fills convex, view-clipped polygons with AreaMove/AreaDraw/AreaEnd
* and AOlPen equal to the fill pen.  With AREAOUTLINE set, each row is
* covered from the leftmost to the rightmost outline pixel.  The outline
* follows the blitter line algorithm of graphics.library Draw: one pixel per
* major step, and a minor step whenever the error term is non-negative.
*
* The CPU writes wait for the blitter first, so earlier Draw lines stay
* underneath the polygon as in the original painter order.
*
* Entered by BSR.W from $22450 after the original SetAPen, AOlPen and
* AREAOUTLINE writes.  Returns to $22454, which branches to the original
* epilogue.  Any RastPort or BitMap state outside the verified game setup
* replays the original instructions and continues with AreaMove at $22458.
* The fill leaves the RastPort pen position, FRST_DOT, line-pattern counter
* and AreaInfo first point as AreaEnd's Move and outline Draws would.
***************************************************************************

AF_VERTICES     = $2410
AF_COUNT        = $2450
AF_PEN          = $2452
AF_RASTPORT     = -$4d0
AF_MAX_ROWS     = 128
AF_STACK_LIMIT  = -$ed4                 ; lowest SP accepted by the game
AF_STACK_MARGIN = 256                   ; also covers the plane lists
AF_LISTS        = 2*4*9                 ; two lists of up to 8 planes + 0

* Update the row limits at A3 with the x coordinate in D0.
AF_LIMIT        MACRO
        cmp.w   (a3),d0
        bge.b   .left\@
        move.w  d0,(a3)
.left\@
        cmp.w   2(a3),d0
        ble.b   .right\@
        move.w  d0,2(a3)
.right\@
        ENDM

RP_LAYER        = 0
RP_BITMAP       = 4
RP_AREAPTRN     = 8
RP_MASK         = 24
RP_AREAINFO     = 16
RP_DRAWMODE     = 28
* RP_LINPATCNT, RP_FLAGS and RP_CP_X come from SR2_ClippedLineTail.s.
FRST_DOT_BIT    = 0

AI_FIRSTX       = 20

LR_CLIPRECT     = 8
LR_BOUNDS       = 16
LR_SUPERBITMAP  = 32
LR_SCROLL_X     = 44
LR_CLIPREGION   = 126

CR_NEXT         = 0
CR_LOBS         = 8
CR_BOUNDS       = 16

AF_GFXBASE      = -$63a8
_LVOWaitBlit    = -228

BM_BYTESPERROW  = 0
BM_ROWS         = 2
BM_DEPTH        = 5
BM_PLANES       = 8

_area_fill
        movem.l d2-d3/a2-a3,-(a7)
        lea     AF_RASTPORT(a4),a1
        tst.l   RP_AREAPTRN(a1)
        bne.w   .fallback
        tst.b   RP_DRAWMODE(a1)
        bne.w   .fallback
        movea.l RP_BITMAP(a1),a0
        move.w  BM_BYTESPERROW(a0),d4
        moveq   #3,d0
        and.w   d4,d0
        bne.w   .fallback
        move.w  BM_ROWS(a0),d5
        cmpi.w  #AF_MAX_ROWS,d5
        bhi.w   .fallback
        moveq   #0,d0
        move.b  BM_DEPTH(a0),d0
        subq.w  #1,d0
        bmi.w   .fallback
        cmpi.w  #7,d0
        bhi.w   .fallback
        lea     BM_PLANES(a0),a2
.align
        move.l  (a2)+,d1
        andi.w  #3,d1
        bne.w   .fallback
        dbra    d0,.align

        * Bounds and vertical extent.  D4 = width in pixels, D5 = rows.
        lsl.w   #3,d4

        * A layer is accepted only when drawing is unclipped and unshifted:
        * origin (0,0), no scroll, super bitmap or region, and one visible
        * ClipRect that covers the whole BitMap.
        move.l  RP_LAYER(a1),d0
        beq.b   .no_layer
        movea.l d0,a0
        tst.l   LR_BOUNDS(a0)
        bne.w   .fallback
        tst.l   LR_SCROLL_X(a0)
        bne.w   .fallback
        tst.l   LR_SUPERBITMAP(a0)
        bne.w   .fallback
        tst.l   LR_CLIPREGION(a0)
        bne.w   .fallback
        move.l  LR_CLIPRECT(a0),d0
        beq.w   .fallback
        movea.l d0,a0
        tst.l   CR_NEXT(a0)
        bne.w   .fallback
        tst.l   CR_LOBS(a0)
        bne.w   .fallback
        tst.l   CR_BOUNDS(a0)
        bne.w   .fallback
        move.w  CR_BOUNDS+4(a0),d0      ; MaxX + 1 >= width
        addq.w  #1,d0
        cmp.w   d4,d0
        blt.w   .fallback
        move.w  CR_BOUNDS+6(a0),d0      ; MaxY + 1 >= rows
        addq.w  #1,d0
        cmp.w   d5,d0
        blt.w   .fallback
.no_layer
        move.w  AF_COUNT(a4),d3
        subq.w  #1,d3
        lea     AF_VERTICES(a4),a2
        move.w  #$7fff,d6               ; top row
        moveq   #-1,d7                  ; bottom row
.bounds
        move.w  (a2)+,d0
        cmp.w   d4,d0
        bhs.w   .fallback               ; unsigned: also rejects x < 0
        move.w  (a2)+,d1
        cmp.w   d5,d1
        bhs.w   .fallback
        cmp.w   d6,d1
        bge.b   .not_top
        move.w  d1,d6
.not_top
        cmp.w   d7,d1
        ble.b   .not_bottom
        move.w  d1,d7
.not_bottom
        dbra    d3,.bounds

        * Row limits live on the stack: 4 bytes per covered row, at most
        * 512.  Keep a margin above the game's stack-check limit.
        move.w  d7,d3
        sub.w   d6,d3                   ; rows - 1
        move.w  d3,d0
        addq.w  #1,d0
        lsl.w   #2,d0
        ext.l   d0
        move.l  a7,d1
        sub.l   d0,d1
        subi.l  #AF_STACK_MARGIN,d1
        cmp.l   AF_STACK_LIMIT(a4),d1
        bcs.w   .fallback
        suba.w  d0,a7
        movea.l a7,a3                   ; limits of the top row
        move.w  d6,d0
        lsl.w   #2,d0
        movea.l a7,a2
        suba.w  d0,a2                   ; A2 + 4 * y addresses row y
        move.l  #$7fffffff,d0           ; left $7fff, right -1 after swap
        move.w  #-1,d0
.reset
        move.l  d0,(a3)+
        dbra    d3,.reset
        movem.w d6-d7,-(a7)             ; keep the row range
        clr.w   -(a7)                   ; sum of Draw major lengths

        * Outline: edge i runs from vertex i to vertex i+1 (last to first).
        move.w  AF_COUNT(a4),d3
        subq.w  #1,d3
        lea     AF_VERTICES(a4),a6
.edge
        move.w  (a6),d0                 ; x0
        move.w  2(a6),d1                ; y0
        addq.l  #4,a6
        tst.w   d3
        bne.b   .next_vertex
        lea     AF_VERTICES(a4),a0
        bra.b   .have_end
.next_vertex
        movea.l a6,a0
.have_end
        move.w  (a0),d4                 ; dx
        sub.w   d0,d4
        move.w  2(a0),d5                ; dy
        sub.w   d1,d5
        moveq   #1,d6                   ; x step
        tst.w   d4
        bge.b   .dx_positive
        neg.w   d4
        moveq   #-1,d6
.dx_positive
        moveq   #1,d7                   ; y step
        tst.w   d5
        bge.b   .dy_positive
        neg.w   d5
        moveq   #-1,d7
.dy_positive
        move.w  d3,-(a7)
        cmp.w   d5,d4
        blt.w   .y_major

        * X-major: D4 = major, D5 = minor.  Only the first and the last
        * pixel of each horizontal run can be a row limit.
        move.w  d4,d3                   ; pixels - 1
        add.w   d4,2(a7)
        add.w   d5,d5                   ; 2 * minor
        move.w  d5,d2
        sub.w   d4,d2                   ; error = 2 * minor - major
        add.w   d4,d4                   ; 2 * major
        sub.w   d5,d4
        neg.w   d4                      ; 2 * minor - 2 * major
.x_run
        lea     (a2,d1.w*4),a3
        AF_LIMIT
.x_pixel
        tst.w   d2
        bmi.b   .x_same_row
        AF_LIMIT                        ; last pixel of the run
        add.w   d7,d1
        add.w   d4,d2
        add.w   d6,d0
        dbra    d3,.x_run
        bra.b   .edge_done
.x_same_row
        add.w   d5,d2
        add.w   d6,d0
        dbra    d3,.x_pixel
        sub.w   d6,d0                   ; last pixel of the edge
        AF_LIMIT
        bra.b   .edge_done

        * Y-major: D5 = major, D4 = minor.  Every pixel starts a row.
.y_major
        move.w  d5,d3
        add.w   d5,2(a7)
        add.w   d4,d4
        move.w  d4,d2
        sub.w   d5,d2
        add.w   d5,d5
        sub.w   d4,d5
        neg.w   d5
.y_pixel
        lea     (a2,d1.w*4),a3
        AF_LIMIT
        tst.w   d2
        bmi.b   .y_no_minor
        add.w   d6,d0
        add.w   d5,d2
        add.w   d7,d1
        dbra    d3,.y_pixel
        bra.b   .edge_done
.y_no_minor
        add.w   d4,d2
        add.w   d7,d1
        dbra    d3,.y_pixel

.edge_done
        move.w  (a7)+,d3
        dbra    d3,.edge

        * RastPort state left by AreaEnd's Move(first) and outline Draws.
        lea     AF_RASTPORT(a4),a1
        moveq   #15,d0
        sub.w   (a7)+,d0
        move.b  d0,RP_LINPATCNT(a1)
        bclr    #FRST_DOT_BIT,RP_FLAGS+1(a1)
        move.l  AF_VERTICES(a4),d0      ; first x and y
        move.l  d0,RP_CP_X(a1)
        move.l  RP_AREAINFO(a1),d1
        beq.b   .no_areainfo
        movea.l d1,a0
        move.l  d0,AI_FIRSTX(a0)
.no_areainfo
        * Earlier Draw lines may still be in the blitter.
        movea.l AF_GFXBASE(a4),a6
        jsr     _LVOWaitBlit(a6)

        * Fill.  Masks are computed once per row; every plane enabled by
        * the RastPort mask then gets its pen bit (JAM1).  Two zero-ended
        * lists on the stack hold the planes to set and to clear.
        movem.w (a7)+,d6-d7
        sub.w   d6,d7                   ; rows - 1
        lea     (a2,d6.w*4),a3          ; limits of the top row
        lea     AF_RASTPORT(a4),a1
        movea.l RP_BITMAP(a1),a6
        moveq   #0,d5
        move.w  BM_BYTESPERROW(a6),d5
        mulu.w  d5,d6                   ; byte offset of the top row
        move.w  d7,-(a7)
        lea     -AF_LISTS(a7),a7
        movea.l a7,a0                   ; planes to set
        lea     AF_LISTS/2(a7),a2       ; planes to clear
        move.b  RP_MASK(a1),d1
        move.w  AF_PEN(a4),d2
        moveq   #0,d4
.list
        cmp.b   BM_DEPTH(a6),d4
        bhs.b   .lists_done
        btst    d4,d1
        beq.b   .list_next
        move.w  d4,d0
        lsl.w   #2,d0
        move.l  BM_PLANES(a6,d0.w),d0
        btst    d4,d2
        beq.b   .list_clear
        move.l  d0,(a0)+
        bra.b   .list_next
.list_clear
        move.l  d0,(a2)+
.list_next
        addq.w  #1,d4
        bra.b   .list
.lists_done
        clr.l   (a0)
        clr.l   (a2)
        movea.l a7,a0
        lea     AF_LISTS/2(a7),a2
        move.w  d7,d3

.row
        move.w  (a3)+,d0                ; left x
        move.w  (a3)+,d1                ; right x
        move.w  d0,d4
        lsr.w   #5,d4                   ; first long
        andi.w  #31,d0
        moveq   #-1,d2
        lsr.l   d0,d2                   ; left mask
        move.w  d1,d0
        lsr.w   #5,d0
        sub.w   d4,d0                   ; longs after the first
        not.w   d1
        andi.w  #31,d1                  ; 31 - (right & 31)
        moveq   #-1,d7
        lsl.l   d1,d7
        move.l  d7,d1                   ; right mask
        lsl.w   #2,d4
        ext.l   d4
        add.l   d6,d4                   ; offset of the first long
        tst.w   d0
        bne.b   .wide

        and.l   d1,d2                   ; one long: combined mask
        movea.l a0,a6
.one_set
        move.l  (a6)+,d7
        beq.b   .one_clear_start
        movea.l d7,a1
        or.l    d2,(a1,d4.l)
        bra.b   .one_set
.one_clear_start
        not.l   d2
        movea.l a2,a6
.one_clear
        move.l  (a6)+,d7
        beq.b   .next_row
        movea.l d7,a1
        and.l   d2,(a1,d4.l)
        bra.b   .one_clear

.wide
        subq.w  #1,d0                   ; whole longs between the edges
        movea.l a0,a6
.wide_set
        move.l  (a6)+,d7
        beq.b   .wide_clear_start
        movea.l d7,a1
        adda.l  d4,a1
        or.l    d2,(a1)+
        move.w  d0,d7
        bra.b   .set_test
.set_middle
        move.l  #-1,(a1)+
.set_test
        dbra    d7,.set_middle
        or.l    d1,(a1)
        bra.b   .wide_set
.wide_clear_start
        not.l   d1
        not.l   d2
        movea.l a2,a6
.wide_clear
        move.l  (a6)+,d7
        beq.b   .next_row
        movea.l d7,a1
        adda.l  d4,a1
        and.l   d2,(a1)+
        move.w  d0,d7
        bra.b   .clear_test
.clear_middle
        clr.l   (a1)+
.clear_test
        dbra    d7,.clear_middle
        and.l   d1,(a1)
        bra.b   .wide_clear

.next_row
        add.l   d5,d6
        dbra    d3,.row

        lea     AF_LISTS(a7),a7
        move.w  (a7)+,d7                ; rows - 1
        addq.w  #1,d7
        lsl.w   #2,d7
        adda.w  d7,a7                   ; release the row limits
        movem.l (a7)+,d2-d3/a2-a3
        rts

.fallback
        * Replay the patched instructions and continue with AreaMove.
        movem.l (a7)+,d2-d3/a2-a3
        move.w  AF_VERTICES(a4),d6
        move.l  d6,d0
        ext.l   d0
        addq.l  #4,(a7)
        rts

        CNOP    0,4
