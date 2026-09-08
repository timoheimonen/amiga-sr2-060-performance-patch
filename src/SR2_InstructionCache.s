***************************************************************************
* Street Rod 2 direct-disk MC68060 instruction-cache wrapper
*
* The entry hook branches here after LoadSeg has populated the complete game
* image.  Replay the original MOVEM before calling exec.Supervisor so the
* program's stack layout remains unchanged.  The common exit hook restores
* the incoming CACR before the original register restore and RTS.
***************************************************************************

_LVOSupervisor         = -30
CACR_EIC               = $00008000
HUNK0_ORIGINAL_SIZE    = $334c
ORIGINAL_CONTINUE      = $0004

        SECTION cache,CODE

payload_begin
cache_entry
        movem.l d1-d6/a0-a6,-(a7)       * replay replaced entry instruction
        movem.l d0-d7/a0-a6,-(a7)       * make cache setup fully transparent
        movea.l 4.w,a6
        lea     enable_cache(pc),a5
        jsr     _LVOSupervisor(a6)
        movem.l (a7)+,d0-d7/a0-a6

        * BRA.W ORIGINAL_CONTINUE.  The payload is assembled from offset zero,
        * so include the original HUNK 0 size in the extension-word PC base.
        dc.w    $6000
entry_return_displacement
        dc.w    ORIGINAL_CONTINUE-HUNK0_ORIGINAL_SIZE-(entry_return_displacement-cache_entry)

cache_exit
        move.l  d0,-(a7)                 * preserve the program return value
        movea.l 4.w,a6
        lea     restore_cache(pc),a5
        jsr     _LVOSupervisor(a6)
        move.l  (a7)+,d0
        movem.l (a7)+,d1-d6/a0-a6       * replay replaced common epilogue
        rts

enable_cache
        lea     saved_cacr(pc),a0
        movec   cacr,d1
        move.l  d1,(a0)
        cinva   ic
        ori.l   #CACR_EIC,d1
        movec   d1,cacr
        rte

restore_cache
        lea     saved_cacr(pc),a0
        move.l  (a0),d1
        cinva   ic
        movec   d1,cacr
        rte

saved_cacr
        dc.l    0
        cnop    0,4

        INCLUDE "SR2_Startup.i"
        END
