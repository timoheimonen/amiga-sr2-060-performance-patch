# Street Rod 2 — KS3.1 / AGA / 68060 patcher

**Version 1.8.0** fills the road polygons with the CPU, reaching the
16.7 FPS limit in the heavy Mulholland scene. Includes the Camaro opening
picture, zlib compression, the startup FPS menu and the KS3.1/AGA/68060
compatibility and performance fixes.

## Requirements

- Python 3.10+; no extra packages, compressor or assembler required.
- PAL A1200/AGA, MC68060, 2 MiB Chip RAM, 8 MiB Fast RAM and Kickstart 3.1
  A1200 rev 40.68.
- Original Disk 1 and Disk 2 from [Street Rod Online](https://www.streetrodonline.com/downloads/)
  (**Street Rod 2**, **Amiga**). Supply your own Kickstart ROM.

## Usage

```sh
python3 patch.py /path/to/SR2AMIGA_DISK1.adf
```

Creates `StreetRod2-KS31-AGA-060-Disk1.adf` beside the original.
Use `--output /path/to/output.adf` to choose a location and `--force` to replace
an existing output. The original disk is never overwritten.

Boot the patched Disk 1 with the **original Disk 2** using the
[FS-UAE settings](FS-UAE.md). Press and release **Space or a mouse button**
to close the Camaro picture and continue to the original cracktro.
In the startup menu, press **1–4** to select
a limit, or **Enter** for the 16.7 FPS default. The selection lasts until
restart. Intros, menus and the original save are preserved.

## Performance

Stationary Mulholland benchmark in FS-UAE 3.2.35 (PAL):

| Metric | Original (A500) | 1.2.0 (68060) | 1.3.0 (68060) | 1.8.0 (68060) |
| --- | ---: | ---: | ---: | ---: |
| Mean frame time | 579.56 ms | 80.13 ms | 70.28 ms | 60.04 ms |
| FPS | 1.73 | 12.48 | 14.23 | 16.65 |

Original: 68000/OCS, Kickstart 1.3, 512 KiB Chip + 512 KiB Slow RAM.
Versions 1.2.0–1.8.0 use the A1200/68060 configuration listed above.
In 1.8.0 drawing takes 50.47 ms (1.7.1: 69.25 ms), so this scene runs at
the default 16.7 FPS limit: 17% higher FPS than 1.3.0–1.7.1.
The selected cap limits faster scenes to one frame per 3–6 PAL fields;
slower frames receive no extra cap delay.

[Changelog](CHANGELOG.md) · [Checksums](FS-UAE.md#checksums) · [Patch details](PATCH.md) · [Patch source](src)

Timo Heimonen (timo.heimonen@proton.me) · [MIT License](LICENSE)

Tools: Amitools, FS-UAE, Ghidra, Codex, Claude.
