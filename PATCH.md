# Street Rod 2 1.7.0 — assembly patch details

These five 68k assembly helpers implement the audio-timer fix, road-buffer
timing and frame cap, covered-span drawing optimization and MC68060
instruction-cache management in release 1.7.0. The startup menu is included
in the instruction-cache and road-buffer payloads. They target PAL A1200/AGA
with Kickstart 3.1 A1200 rev 40.68 and an MC68060.

The helpers are appended to the original executable's HUNK code segments.
Patched `BRA.W` or `BSR.W` instructions redirect execution into them; the
helpers replay displaced instructions as needed and rejoin the original
code. PC-relative references and branches back into the same HUNK keep the
helpers independent of the segment's load address.

[patch.py](patch.py) embeds the assembled payloads, so applying the release
does not require an assembler. [src/patches.json](src/patches.json) records
the HUNK numbers, patch offsets, expected and replacement bytes, payload
sizes and hashes. The manual-protection bypass and AGA bitplane-selection
fix are direct instruction patches recorded there, rather than separate
assembly helpers.

## SR2_AudioTimerSoftint.s — defer the music tick

Source: [src/SR2_AudioTimerSoftint.s](src/SR2_AudioTimerSoftint.s), appended
to HUNK 23.

The original CIA-B music callback runs at CPU interrupt level 6. Its audio
I/O path can need Paula's level-4 interrupt to complete DMA-start
bookkeeping during `BeginIO()`. Level 4 cannot interrupt level 6, creating
an interrupt-priority deadlock.

`queue_tick` saves CIA-B Timer A's control register at `$bfde00` and clears
bit 0 to stop the timer. It then queues an Exec software interrupt through
`Cause()` and returns from the CIA callback. The embedded `Interrupt`
structure has node priority 0; the music body now runs at software-interrupt
level 1, where Paula's level-4 interrupt can preempt it.

The software callback replays the displaced `LINK A5,#-12` and branches
into the original handler immediately after that instruction. Both
original `BeginIO()` calls and the sample data remain in use. When the
handler returns, the wrapper ORs the saved control value with `$11`:
bit 4 force-loads the timer counter from its latch, and bit 0 restarts it.
Restarting after the handler makes the next timer period begin after that
tick's processing finishes.

## SR2_RoadSwap.s — safe buffer publication and driving frame cap

Source: [src/SR2_RoadSwap.s](src/SR2_RoadSwap.s), appended to HUNK 10.

Release 1.6.0 provides selectable driving caps of approximately
**16.7, 12.5, 10 and 8.3 FPS**, extending the cap introduced in 1.4.0
and the buffer-timing change introduced in 1.3.0. The PAL Copper list
loads the road bitplane pointers at line 42, displays the road on lines
44–143, and switches to independent cockpit bitplanes at line 144. The
helper uses this split to let drawing into the old road buffer start while
the cockpit is being displayed.

It reads a longword from `$dff004`, covering `VPOSR` and `VHPOSR`, shifts
right by eight and masks with `$1ff` to extract the nine-bit raster line.
Two inclusive windows permit publication:

| Raster lines | Publication timing |
| --- | --- |
| 8–30 | Before the Copper loads the road pointers for the current field. |
| 150–300 | After the road scan; the new pointers take effect next field. |

The `eligible` routine also checks the game's 32-bit VBlank counter against
`first_display_field`, which records when the previous publication first
reaches the road. An early publication records the current field; a late
one records the next field. Replacing that image is allowed only after
its road scan: in the late window of its first display field, or in a
later field. Signed modular subtraction handles counter wraparound.

The cap separately tracks `last_publish_field` and `last_publish_beam`.
`cap_due` requires the selected 3–6 complete PAL fields since the previous
publication: at exactly that field difference, the beam must also
have reached the saved position. The longword read from `$dff004`, masked
with `$1ffff`, includes both vertical and horizontal beam position. The
VBlank counter is sampled around the beam read; a changed counter rejects
that snapshot. This prevents a late-to-early raster transition from
releasing a frame before the full interval has elapsed.

`WaitTOF()` sleeps over whole fields still owed to the cap; the final field
is checked at beam precision. Frames that already took longer than the
interval receive no extra cap delay. Each successful publication starts a
new interval, so a slow frame cannot accumulate fast catch-up frames.

Once eligible, the helper calls Exec `Disable()` and checks the raster
position, publication history and cap again. An interrupt could have consumed
the safe window between the first check and `Disable()`. A failed recheck
calls `Enable()` before retrying; the helper never waits with interrupts
disabled.

On success, it records the new publication's first display field and
copies **12 longwords (48 bytes)** of bitplane-pointer data into the Copper
list. It samples the beam after this copy and rounds it up by one hardware
quantum before saving the cap timestamp, then calls `Enable()`. This
updates display pointers, not framebuffer pixels. The original `WaitBlit()`
and buffer-index toggle precede the helper; the original buffer-descriptor
exchange follows it. The helper saves `D2` on entry and restores it before
either return path, preserving the original caller's registers and stack.

After raster line 300, `WaitTOF()` sleeps across the end of the field.
Outside the driving display, the helper invalidates its publication and
cap history and uses the original `WaitTOF()` and pointer-copy path.
`reset_swap` also invalidates the history when a driving display is
initialized and replays the original buffer-index reset, so the first frame
has no previous cap deadline. The selected `minimum_fields` value is kept
separate from that history and survives both paths. These raster windows depend on the target
PAL Copper layout.

## SR2_CoveredSpanEntry.s — mark a covered-span batch

Source: [src/SR2_CoveredSpanEntry.s](src/SR2_CoveredSpanEntry.s), appended
to HUNK 42.

This entry trampoline establishes the state used by the clipped-line
helper below. It pops the hook's `BSR` return address into `A0`, saves
`D2–D3/D5–D7/A3`, and sets `A3` to `$53523230`, the ASCII marker `SR20`.
It then replays the original argument load into `D7` and jumps back past
the displaced entry instructions.

`SR20` means that a covered-span batch is active but its colour-15 drawing
state is not yet prepared. Keeping the marker in `A3` lets the two helpers
share this state without a private global variable or a cross-HUNK
relocation. A companion patch to the original epilogue adds `A3` to the
register-restore mask, preserving the caller's value on return.

## SR2_ClippedLineTail.s — avoid repeated line setup

Source: [src/SR2_ClippedLineTail.s](src/SR2_ClippedLineTail.s), appended
to HUNK 45.

The dispatcher recognizes `SR20` and `SR21` (`$53523231`) in `A3`. The
first accepted colour-15 line in a batch takes the original RastPort
preparation and `SetAPen()` path, setting the marker to `SR21`. Subsequent
colour-15 lines reuse that preparation. A different pen resets the marker
to `SR20` and takes the original setup path; calls outside a marked batch
also use the original path.

For a reusable colour-15 setup, the helper replaces the `Move()` library
call with the four RastPort writes made by the target Kickstart's
`graphics.library` 40.24 implementation:

| RastPort offset | Update |
| --- | --- |
| 36, word | Write `D7` to `CP_X`. |
| 38, word | Write `D6` to `CP_Y`. |
| 32, word | OR in the `FRST_DOT` mask `$0001`. |
| 30, byte | Set the line-pattern counter to 15. |

The RastPort is addressed through `A4-$4d0`. Execution then rejoins the
original `Draw()` path, retaining the game's line rendering while avoiding
redundant setup and library-call overhead. The direct state updates match
`Move()` at ROM address `$f86fbc` in A1200 Kickstart 40.68; the byte at
offset 30 is part of that ROM-specific contract.

## SR2_InstructionCache.s — manage the MC68060 I-cache

Source: [src/SR2_InstructionCache.s](src/SR2_InstructionCache.s), appended
to HUNK 0.

The entry hook runs after `LoadSeg` has loaded the game. It first replays
the original `MOVEM` prologue to preserve the expected stack layout, then
saves the working registers around an Exec `Supervisor()` call. The
supervisor routine performs the privileged cache operations:

1. Read `CACR` with `MOVEC` and save the incoming value.
2. Invalidate the instruction cache with `CINVA IC`.
3. OR in `$00008000`, the MC68060 instruction-cache enable bit.
4. Write `CACR` and return from the supervisor routine with `RTE`.

The wrapper restores its working registers and branches back to the
original entry code. On the common normal-exit path, it preserves the
game's return value in `D0`, enters supervisor mode again, invalidates the
I-cache and restores the saved `CACR`. Finally, it replays the original
register restore and returns with `RTS`.

Only the instruction-cache enable bit is added during setup. The helper
leaves the incoming data-cache configuration unchanged and restores the
incoming cache-control value on normal exit.

## Startup FPS selection

[src/SR2_Startup.i](src/SR2_Startup.i) is included in the HUNK 0 payload.
A `BSR.W` at original entry offset `$4` calls this dispatcher after cache
setup. It preserves all working registers and follows ten `LoadSeg` BPTR
links to HUNK 10, so the segments need not be contiguous. On return, it
replays the original argument setup and continues at entry offset `$8`.

[src/SR2_StartupMenu.i](src/SR2_StartupMenu.i) is included in HUNK 10 at
offset `$780`. It opens the current `CONSOLE:` through `dos.library` and
uses raw input to accept one key. Keys 1–4 select 3, 4, 5 or 6 PAL fields;
Enter selects 3. Other keys are ignored, including the numeric parts of
cursor and function-key escape sequences. The console returns to cooked
mode before the file handle and library are closed.

The menu stores the choice in `minimum_fields`. Both scheduler comparisons
read this value. A valid `FPS=1` through `FPS=4` command-line argument sets
the same value without opening the menu. Missing console support uses the
default. No settings file or separate launcher is needed.

To assemble the sources with `vasmm68k_mot`, add `-Isrc` to the command so
that the two include files can be resolved, for example:

```sh
vasmm68k_mot -m68060 -Fbin -nosym -Isrc -o /tmp/SR2_RoadSwap.bin src/SR2_RoadSwap.s
```

## Joystick fire-button input

Release 1.5.0 changes `ori.w #$80,d0` to `andi.w #$7f,d0` in the
joystick routine before it writes CIAA DDRA (`$BFE201`). Bit 7 is cleared
to select input mode for the fire button read from CIAA PRA (`$BFE001`);
all other direction bits are preserved. The following button test remains
active-low.

The four-byte replacement is `0040 0080` → `0240 007f`, at original
executable file offset `0x11746` (HUNK 24, offset `0x4e2`). It does not
change executable size or the assembly helper payloads.

## End-scene data loading

Release 1.7.0 preserves the full 32-bit addresses returned by the allocator
for the 504-byte record table and 732-byte animation command stream.
In HUNK 12, offsets `$50` and `$64`, the original `EXT.L D0` truncated each
address to a signed 16-bit value before the store.

Each six-byte replacement stores D0 with `MOVE.L D0,d16(A4)` followed by
`TST.L D0`. The destinations are `-$460(A4)` and `-$45c(A4)`. Registers and
the stack are preserved; N/Z reflect the full address, V/C are cleared,
and X is preserved. HUNK sizes and relocations remain unchanged.

[src/SR2_EndPointers.s](src/SR2_EndPointers.s) contains both replacement
blocks, embedded in `PROGRAM_PATCHES` at original executable offsets
`0xb750` and `0xb764`.
