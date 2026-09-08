; Called once from HUNK 0 before the original runtime initializes graphics.
; D0/A0 retain the AmigaDOS argument length/string. Caller saves registers.
_LVOOpenLibrary = -552
_LVOCloseLibrary = -414
_LVOOpen        = -30
_LVOClose       = -36
_LVORead        = -42
_LVOWrite       = -48
_LVOSetMode     = -426

startup_menu
        ; Explicit FPS=1..4 also lets diagnostic builds run unattended.
        cmpi.l  #6,d0
        bne.b   .interactive
        cmpi.l  #$4650533d,(a0) ; "FPS="
        bne.b   .interactive
        cmpi.b  #10,5(a0)
        bne.b   .interactive
        moveq   #0,d0
        move.b  4(a0),d0
        bsr.w   menu_key
        tst.l   d0
        beq.b   .interactive
        lea     minimum_fields(pc),a0
        move.l  d0,(a0)
        rts
.interactive
        moveq   #3,d7
        movea.l 4.w,a6
        lea     dos_name(pc),a1
        moveq   #36,d0
        jsr     _LVOOpenLibrary(a6)
        tst.l   d0
        beq.w   .done
        movea.l d0,a6
        lea     console_name(pc),a0
        move.l  a0,d1
        move.l  #1005,d2       ; MODE_OLDFILE, current console (also in script)
        jsr     _LVOOpen(a6)
        move.l  d0,d6
        beq.w   .library
        move.l  d6,d1
        moveq   #1,d2          ; one key, no mandatory Enter
        jsr     _LVOSetMode(a6)
        tst.l   d0
        beq.w   .close
        move.l  d6,d1
        lea     menu_text(pc),a0
        move.l  a0,d2
        move.l  #menu_text_end-menu_text,d3
        jsr     _LVOWrite(a6)
        moveq   #0,d5          ; escape-sequence state
.read
        move.l  d6,d1
        lea     key_buffer(pc),a0
        move.l  a0,d2
        moveq   #1,d3
        jsr     _LVORead(a6)
        cmpi.l  #1,d0
        bne.b   .selected      ; EOF/error uses the default
        moveq   #0,d0
        move.b  key_buffer(pc),d0
        ; Ignore cursor/function-key sequences, including their digits.
        tst.b   d5
        beq.b   .plain
        cmpi.b  #1,d5
        bne.b   .csi
        cmpi.b  #'[',d0
        bne.b   .escape_end
        moveq   #2,d5
        bra.b   .read
.csi
        cmpi.b  #$40,d0
        blo.b   .read
        cmpi.b  #$7e,d0
        bhi.b   .read
.escape_end
        moveq   #0,d5
        bra.b   .read
.plain
        cmpi.b  #27,d0
        bne.b   .check_csi
        moveq   #1,d5
        bra.b   .read
.check_csi
        cmpi.b  #$9b,d0
        bne.b   .key
        moveq   #2,d5
        bra.b   .read
.key
        bsr.w   menu_key
        tst.l   d0
        beq.b   .read
        move.l  d0,d7
.selected
        lea     minimum_fields(pc),a0
        move.l  d7,(a0)
        ; Each choice occupies exactly five bytes in this display table.
        move.l  d7,d0
        subq.l  #3,d0
        mulu.w  #5,d0
        lea     fps_labels(pc),a0
        adda.l  d0,a0
        move.l  d6,d1
        move.l  a0,d2
        moveq   #5,d3
        jsr     _LVOWrite(a6)
        move.l  d6,d1
        lea     selected_suffix(pc),a0
        move.l  a0,d2
        moveq   #selected_suffix_end-selected_suffix,d3
        jsr     _LVOWrite(a6)
        move.l  d6,d1
        moveq   #0,d2
        jsr     _LVOSetMode(a6) ; restore cooked console before game/CLI
.close
        move.l  d6,d1
        jsr     _LVOClose(a6)
.library
        movea.l a6,a1
        movea.l 4.w,a6
        jsr     _LVOCloseLibrary(a6)
.done
        rts

; Pure input mapping, used by the native audit. D0=0 means keep waiting.
menu_key
        cmpi.b  #13,d0
        beq.b   .default
        cmpi.b  #10,d0
        beq.b   .default
        cmpi.b  #'1',d0
        blo.b   .invalid
        cmpi.b  #'4',d0
        bhi.b   .invalid
        andi.l  #$ff,d0
        subi.l  #'1'-3,d0
        rts
.default
        moveq   #3,d0
        rts
.invalid
        moveq   #0,d0
        rts

dos_name        dc.b 'dos.library',0
console_name    dc.b 'CONSOLE:',0
menu_text
        dc.b 10,'Select driving FPS limit:',10,10
        dc.b '  1   16.7 FPS  (default)',10
        dc.b '  2   12.5 FPS',10
        dc.b '  3   10.0 FPS',10
        dc.b '  4    8.3 FPS',10,10
        dc.b 'Press 1-4, or ENTER for default: '
menu_text_end
fps_labels      dc.b '16.7 ','12.5 ','10.0 ','8.3  '
selected_suffix dc.b 'FPS',10
selected_suffix_end
key_buffer      dc.b 0
        cnop    0,4
