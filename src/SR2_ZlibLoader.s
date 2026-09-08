; Self-extracting HUNK entry, assembled once and embedded by zlib_hunk.py.
; Python supplies raw DEFLATE, original allocation words and relocation records.
; DOS allocates all original hunks plus this loader, and frees them on UnLoadSeg.
; Preserve ALL entry registers including D0/A0 CLI arguments. KS3.1 required.
        section code,code
start:
        subq.l  #4,sp                 ; final target for RTS, above saved registers
        movem.l d0-d7/a0-a6,-(sp)
        lea     metadata(pc),a3
        move.l  24(a3),60(sp)          ; first original HUNK address (DOS relocates)
        move.l  4.w,a6
        move.l  (a3),d0               ; flat output size
        moveq   #1,d1                 ; MEMF_PUBLIC, executable stays OS-owned
        jsr     -198(a6)              ; AllocMem
        tst.l   d0
        beq     failure
        move.l  d0,a4
        ; Input checksum protects the unchecked inflate routine from disk damage.
        move.l  16(a3),d1             ; packed offset, relative to metadata
        lea     (a3,d1.l),a0
        move.l  4(a3),d0
        bsr     adler32
        cmp.l   8(a3),d0
        bne     free_failure
        move.l  16(a3),d1
        lea     (a3,d1.l),a5
        bsr     inflate
        move.l  a4,a0
        move.l  (a3),d0
        bsr     adler32
        cmp.l   12(a3),d0
        bne     free_failure
        lea     24(a3),a2             ; relocated original HUNK base table
        move.l  20(a3),d7             ; original HUNK count
        move.l  d7,d0
        lsl.l   #2,d0
        lea     (a2,d0.l),a5          ; per-HUNK copy and relocation descriptors
        move.l  a4,a0                 ; flat unrelocated bytes
copy_hunk:
        move.l  (a2)+,a1
        move.l  (a5)+,d0              ; initialized length in longwords
        beq.s   reloc_begin
copy_long:
        move.l  (a0)+,(a1)+
        subq.l  #1,d0
        bne.s   copy_long
reloc_begin:
        move.l  -4(a2),a1
        move.l  (a5)+,d2              ; relocation count
        beq.s   next_hunk
relocate:
        move.l  (a5)+,d0              ; source offset in bytes
        move.l  (a5)+,d1              ; target index times four
        lea     24(a3),a6
        move.l  (a6,d1.l),d1
        add.l   d1,(a1,d0.l)
        subq.l  #1,d2
        bne.s   relocate
next_hunk:
        subq.l  #1,d7
        bne.s   copy_hunk
        move.l  4.w,a6
        move.l  a4,a1
        move.l  (a3),d0
        jsr     -210(a6)              ; FreeMem temporary flat output
        jsr     -636(a6)              ; CacheClearU before executing restored code
        movem.l (sp)+,d0-d7/a0-a6
        rts                           ; enter original HUNK 0, original stack
free_failure:
        move.l  4.w,a6
        move.l  a4,a1
        move.l  (a3),d0
        jsr     -210(a6)
failure:
        movem.l (sp)+,d0-d7/a0-a6
        addq.l  #4,sp
        moveq   #20,d0                ; RETURN_FAIL, never run partial output
        rts

; Adler32, A0 bytes, D0 length -> D0 checksum. Clobbers D1-D3/A0 only.
; Reducing each byte is small and avoids division/68060 emulation traps.
adler32:
        moveq   #1,d1
        moveq   #0,d2
        tst.l   d0
        beq.s   adler_done
adler_byte:
        moveq   #0,d3
        move.b  (a0)+,d3
        add.l   d3,d1
        cmp.l   #65521,d1
        blo.s   adler_s2
        sub.l   #65521,d1
adler_s2:
        add.l   d1,d2
        cmp.l   #65521,d2
        blo.s   adler_next
        sub.l   #65521,d2
adler_next:
        subq.l  #1,d0
        bne.s   adler_byte
adler_done:
        swap    d2
        move.w  d1,d2
        move.l  d2,d0
        rts
        include 'inflate/inflate.asm'
        cnop 0,4
metadata:
; size, packed size, packed Adler32, output Adler32, packed offset, count,
; count DOS-relocated pointers, then [copy longs, reloc count, (offset,index*4)*]
