# Street Rod 2 — KS3.1 / AGA / 68060 patcher

**Version 1.3.0** improves drawing and frame timing, enables the instruction
cache, and fixes audio, display and manual-protection compatibility.

## Requirements

- Python 3.10+; no extra packages or assembler required.
- PAL A1200/AGA, MC68060, 2 MiB Chip RAM, 8 MiB Fast RAM and Kickstart 3.1
  A1200 rev 40.68. Tested with FS-UAE 3.2.35; physical hardware is unverified.
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
[FS-UAE settings](FS-UAE.md). Intros, menus and the original save are preserved.

## Performance

Stationary Mulholland benchmark in FS-UAE 3.2.35, PAL/AGA/68060:

| Metric | 1.2.0 | 1.3.0 |
| --- | ---: | ---: |
| Mean frame time | 80.13 ms | 70.28 ms |
| FPS | 12.48 | 14.23 |

**14% higher FPS** in this scene from reduced buffer-swap waiting.
Moving gameplay and hardware performance remain unverified.

[Changelog](CHANGELOG.md) · [Checksums](FS-UAE.md#checksums) · [Patch source](src)

Timo Heimonen (timo.heimonen@proton.me) · [MIT License](LICENSE)

Tools: Amitools, FS-UAE, Ghidra, OpenAI.
