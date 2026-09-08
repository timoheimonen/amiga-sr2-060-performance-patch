# Street Rod 2 — KS3.1 / AGA / 68060 patcher

**Version 1.7.0** fixes end-scene data loading. Includes a startup menu
with driving limits of approximately **16.7, 12.5, 10 or 8.3 FPS**, joystick
input fixes, drawing optimizations, instruction-cache support, and audio,
display and manual-protection compatibility fixes.

## Requirements

- Python 3.10+; no extra packages or assembler required.
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
[FS-UAE settings](FS-UAE.md). In the startup menu, press **1–4** to select
a limit, or **Enter** for the 16.7 FPS default. The selection lasts until
restart. Intros, menus and the original save are preserved.

## Performance

Stationary Mulholland benchmark in FS-UAE 3.2.35 (PAL):

| Metric | Original (A500) | 1.2.0 (68060) | 1.3.0 (68060) | 1.4.0 (68060) |
| --- | ---: | ---: | ---: | ---: |
| Mean frame time | 579.56 ms | 80.13 ms | 70.28 ms | 70.28 ms |
| FPS | 1.73 | 12.48 | 14.23 | 14.23 |

Original: 68000/OCS, Kickstart 1.3, 512 KiB Chip + 512 KiB Slow RAM.
Versions 1.2.0–1.4.0 use the A1200/68060 configuration listed above.
**1.4.0 retains 1.3.0's performance in this scene**, about 14% higher FPS
than 1.2.0 and 724.6% higher than the original A500 configuration.
The selected cap limits faster scenes to one frame per 3–6 PAL fields;
slower frames receive no extra cap delay.

[Changelog](CHANGELOG.md) · [Checksums](FS-UAE.md#checksums) · [Patch details](PATCH.md) · [Patch source](src)

Timo Heimonen (timo.heimonen@proton.me) · [MIT License](LICENSE)

Tools: Amitools, FS-UAE, Ghidra, OpenAI.
