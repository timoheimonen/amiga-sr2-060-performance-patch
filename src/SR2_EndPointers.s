; Street Rod 2 1.7.0: original ending loader, HUNK 12 +$50 / +$64.
; Allocator returns a 32-bit address in D0. The original EXT.L D0
; incorrectly sign-extends its low word before storing the pointer.
; Each independent replacement occupies the original six bytes.
; MOVE.L preserves the pointer; TST.L leaves full-width N/Z, clears V/C,
; and preserves X. No registers, stack slots, or relocations are added.
; These two blocks are assembled and compared with patches.json by tests.
ending_records_pointer:
        move.l  d0,-$460(a4)
        tst.l   d0
ending_commands_pointer:
        move.l  d0,-$45c(a4)
        tst.l   d0
