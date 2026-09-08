# 68000 DEFLATE decoder

Source: Keir Fraser, with Amiga assembler syntax adjustments by phx.
https://github.com/keirf/Amiga-Stuff/blob/master/inflate/inflate.asm
Retrieved 2026-09-08. Original file SHA-256:
`06dd711789cf93bcc95d6f9c698830941a04c70a77477bce6aeee31f866ccbe5`.

The author dedicates this code to the public domain (Unlicense); see the
notice in `inflate.asm` and https://unlicense.org/.

Local changes: removed the final assembler `end` directive so the routine
can be included before the loader metadata; stripped trailing whitespace.
The decompression algorithm and default optimization settings are unchanged.
The routine accepts trusted raw DEFLATE streams; SR2_ZlibLoader checks the
compressed Adler32 before calling it and checks the decoded Adler32 afterward.
