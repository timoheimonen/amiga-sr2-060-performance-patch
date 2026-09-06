***************************************************************************
* Street Rod 2 KS3.1/AGA/68060 covered-span entry
*
* Framebuffer-verified covered-span helper appended to its original HUNK.
* The marker lives in A3, so this hunk needs no cross-hunk relocation or
* private global state.  The original epilogue is patched to restore A3.
***************************************************************************

SR2_COVERED_MARKER_CLEAR = $53523230

        SECTION covered_span_entry,CODE

_covered_span_batch_entry
        move.l  (a7)+,a0
        movem.l d2-d3/d5-d7/a3,-(a7)
        movea.l #SR2_COVERED_MARKER_CLEAR,a3
        move.w  8(a5),d7
        addq.l  #4,a0
        jmp     (a0)

        CNOP    0,4
        END
