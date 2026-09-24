# FS-UAE setup for version 1.8.2

Use FS-UAE 3.2.35 with PAL A1200/AGA and an MC68060. This image is not for
stock 68020, KS1.3 or OCS configurations.

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

## Startup FPS menu

The menu appears in the AmigaDOS window before the game's own intros.
Press a number key; no Enter is required after it:

| Key | Driving limit, approximately |
| --- | ---: |
| 1 or Enter | 16.7 FPS |
| 2 | 12.5 FPS |
| 3 | 10 FPS |
| 4 | 8.3 FPS |

The menu waits for your choice without a timeout. The selection remains
active until restart. Lower limits also slow the frame-based driving and
steering updates; the display remains PAL.

From AmigaDOS, `Street_Rod FPS=2` selects 12.5 FPS directly. `FPS=1` through
`FPS=4` use the same choices as the menu. Without a console, the default
limit is used.

## Checksums

All ADFs are 901,120 bytes. The Kickstart ROM is 512 KiB.

| File | SHA-256 |
| --- | --- |
| Original Disk 1 | `4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c` |
| Original Disk 2 | `32e15a76642f81d9b923fef5c94e35b55d78b193b8bdd7640a7cba276d83f0ec` |
| Patched Disk 1 (1.8.2) | `2a40b6fcfcb365a5a4c20dfe1bec06876218ec011764b0277126402c9036a8d0` |
| Kickstart 3.1 A1200 rev 40.68 | `6d43840d4099a74170ea0f0425b6257c3891ebcaa39c4d1840075a9ab22b5707` |

The patcher verifies Disk 1, original instructions, HUNK sizes, the resulting
executable, final ADF, and file read-back. Fixed filesystem timestamps make the
output reproducible. Disk 2 and the ROM are not read or verified by the patcher.
