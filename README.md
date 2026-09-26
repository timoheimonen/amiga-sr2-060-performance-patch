# Street Rod 2 — KS3.1 / AGA / 68060 patcher

**Version 1.8.2**. A performance patch intended primarily for playing
Street Rod 2 in an emulator.

## Requirements

- Python 3.10+; no extra packages or assembler required.
- PAL A1200/AGA, MC68060, 2 MiB Chip RAM, at least 2 MiB Fast RAM and Kickstart 3.1
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


## Checksums (SHA-256)

| File | SHA-256 |
| --- | --- |
| Original Disk 1 | `4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c` |
| Original Disk 2 | `32e15a76642f81d9b923fef5c94e35b55d78b193b8bdd7640a7cba276d83f0ec` |
| Patched Disk 1 (1.8.2) | `2a40b6fcfcb365a5a4c20dfe1bec06876218ec011764b0277126402c9036a8d0` |
| Kickstart 3.1 A1200 rev 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |

[Changelog](CHANGELOG.md) · [Patch details](PATCH.md) · [Patch source](src)

Timo Heimonen (timo.heimonen@proton.me) · [MIT License](LICENSE)
