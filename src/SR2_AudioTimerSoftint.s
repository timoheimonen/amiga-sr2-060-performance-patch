; Run the original CIA-B music tick at Exec software-interrupt level.
; The level-6 CIA callback only queues work. Paula level 4 can therefore
; complete DMA-start bookkeeping during both unchanged BeginIO calls.
; No sample delay, request replacement or ROM patch is involved.
;
; Appended to original HUNK 23, with only the original LINK at $12af0
; replaced. The original handler establishes its own A4 and saves registers.
HUNK_SIZE       = $1b10
HANDLER_OFFSET  = $18b4
_LVOCause       = -180
        SECTION timer,CODE
queue_tick
        move.l  a6,-(sp)
        lea     saved_cra(pc),a0
        move.b  $bfde00,(a0)
        bclr    #0,$bfde00
        lea     softint(pc),a1
        tst.l   18(a1)
        bne.b   .ready
        lea     original_tick(pc),a0
        move.l  a0,18(a1)
.ready
        movea.l 4.w,a6
        jsr     _LVOCause(a6)
        movea.l (sp)+,a6
        moveq   #0,d0
        rts
original_tick
        bsr.b   tick_body
        move.b  saved_cra(pc),d0
        ori.b   #$11,d0            ; force-load new latch and restart timer A
        move.b  d0,$bfde00
        moveq   #0,d0
        rts
tick_body
        link    a5,#-12
        dc.w    $6000
.continue
        dc.w    HANDLER_OFFSET+4-HUNK_SIZE-(.continue-queue_tick)
saved_cra
        dc.b    0
        cnop    0,4
softint
        dc.l    0,0
        dc.b    2,0              ; NT_INTERRUPT, priority 0
        dc.l    0                ; ln_Name
        dc.l    0                ; is_Data (original handler loads A4 itself)
        dc.l    0                ; is_Code (initialized before first Cause)
        cnop    0,4
        END
