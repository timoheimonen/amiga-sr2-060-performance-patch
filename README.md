# Street Rod 2 — Kickstart 3.1 / AGA / 68060 patcher

Version **1.2.0** patches *Street Rod 2* for Kickstart 3.1,
AGA and an MC68060. It combines the drawing optimization and instruction-cache
helper with the audio, display and manual-protection fixes.

The self-contained Python script creates a new Disk 1 ADF without modifying
the original. Use the original Disk 2. Intros, menus, saves and normal game
progression remain available. Supply your own legally obtained disk images
and Kickstart ROM; none are included in this repository.

## Requirements

- Python 3.10 or newer; no third-party Python packages or assembler needed.
- The original Disk 1 and Disk 2 images listed below.
- FS-UAE 3.2.35, configured as A1200/AGA with an MC68060, 2 MiB Chip RAM and
  8 MiB Fast RAM.
- A 512 KiB Kickstart 3.1 A1200 rev 40.68 ROM, SHA-256
  `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707`.

This release targets the tested 68060 emulator configuration. Its cache helper
contains 040/060-class instructions: do not use this exact image on a stock
68020 A1200. The drawing optimization itself does not require a 68060, but
other CPU configurations need a different cache helper. Physical Amiga
hardware has not been validated.


## Supported images and reproducible output

The original Amiga disk images can be downloaded from the official
[Street Rod Online website](https://www.streetrodonline.com/). On the
[Downloads page](https://www.streetrodonline.com/downloads/), choose
**Street Rod 2** in the **Amiga** row.

All ADFs below are 901,120 bytes.

| Image | SHA-256 |
| --- | --- |
| Original Disk 1 | `4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c` |
| Original Disk 2 | `32e15a76642f81d9b923fef5c94e35b55d78b193b8bdd7640a7cba276d83f0ec` |
| Patched Disk 1 | `c635266ba140dfae3fa78c04bbe9ac7ee7fb23c61591632e98e23748ad24c3c3` |

The script accepts only the exact original Disk 1. It checks the source hash,
original instruction bytes, HUNK sizes, final executable hash, final ADF hash
and file read-back. Fixed filesystem timestamps make the output reproducible.
Disk 2 is not an input to the script and is not modified or verified by it.

The patched `STREET_ROD` executable has SHA-256:
`38c419ece1d5bacef7dfc9dae785ebd19b2f6d076453f9abe9c0c26d7bfdd497`.

## Usage

```sh
python3 patch.py /path/to/SR2AMIGA_DISK1.adf
```

This writes `StreetRod2-KS31-AGA-060-Disk1.adf` beside the original. To choose
another location:

```sh
python3 patch.py /path/to/SR2AMIGA_DISK1.adf \
  --output /path/to/StreetRod2-KS31-AGA-060-Disk1.adf
```

Use `--force` to replace an existing output. The script always rejects using
the source path as the output, including with `--force`.

## FS-UAE configuration

Replace the three paths with files on your system:

```ini
[fs-uae]
amiga_model = A1200
cpu = 68060
fpu = 0
mmu = 0
accuracy = 1
jit_compiler = 0
uae_cpu_speed = real
chip_memory = 2048
slow_memory = 0
fast_memory = 8192

kickstart_file = /path/to/Kickstart-3.1-A1200-40.68.rom
floppy_drive_count = 2
floppy_drive_0 = /path/to/StreetRod2-KS31-AGA-060-Disk1.adf
floppy_drive_1 = /path/to/SR2AMIGA_DISK2.adf

uae_sound_output = exact
```

The patcher does not install a CPU or chipset compatibility check, so select
the required hardware in the emulator configuration before starting.

## What the patch changes

- Defers the CIA-B audio timer handler to an Exec software interrupt so Paula
  audio interrupts can run during audio requests.
- Fixes the KS3.1 AGA Copper-list selection: four road bitplanes and six cockpit
  bitplanes remain correctly separated.
- Swaps road buffers at vertical blank to prevent road flicker at the start line.
- Batches covered-span drawing setup and pen selection, with inlined
  `graphics.library/Move` updates adapted to KS3.1.
- Enables the MC68060 instruction cache and restores the incoming cache-control
  register on normal exit. It does not enable the data cache or add FPU code.
- Bypasses the manual question by returning the routine's normal success value
  after its original stack guard.

## Performance

From bad case ~1-5 fps to ~10-15 fps.

## Patch source

The [`src`](src) directory contains the four assembler helpers embedded in
`patch.py`. [`src/patches.json`](src/patches.json) records the original
instruction replacements, HUNK offsets, helper sizes and hashes. It also
includes the manual-protection bypass and the two display fixes.

To assemble a helper with vasm:

```sh
vasmm68k_mot -m68060 -Fbin -nosym -o /tmp/SR2_InstructionCache.bin \
  src/SR2_InstructionCache.s
```

All four assembled helpers have been checked byte-for-byte against the
Python payloads. The Python patcher does not read these source files at runtime.

## Tools used

Amitools, FS-UAE, Ghidra, OpenAI. 

## Author

Timo Heimonen (timo.heimonen@proton.me)

## License

[MIT License](LICENSE).
