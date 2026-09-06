# FS-UAE setup for version 1.3.0

Use FS-UAE 3.2.35 with PAL A1200/AGA and an MC68060. This image is not for
stock 68020, KS1.3 or OCS configurations. Physical hardware is unverified.

Save this as a `.fs-uae` profile, replace the three paths and open it in FS-UAE:

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

Select PAL. The patcher does not check the emulator's CPU or chipset settings.

## Checksums

All ADFs are 901,120 bytes. The Kickstart ROM is 512 KiB.

| File | SHA-256 |
| --- | --- |
| Original Disk 1 | `4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c` |
| Original Disk 2 | `32e15a76642f81d9b923fef5c94e35b55d78b193b8bdd7640a7cba276d83f0ec` |
| Patched Disk 1 (1.3.0) | `5bbd2f0c2c883e1fdc66f70e59bb85ba36162d6c9fa564b6db8416a70802b2e9` |
| Kickstart 3.1 A1200 rev 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |

The patcher verifies Disk 1, original instructions, HUNK sizes, the resulting
executable and ADF, and file read-back. Fixed filesystem timestamps make the
output reproducible. Disk 2 and the ROM are not read or verified by the patcher.
