# Street Rod 2 68060 performance patcher for Amiga

This is a small, self-contained Python patcher for the original Amiga release
of *Street Rod 2*. It is made for a specific setup: Kickstart 1.3, OCS and a
full MC68060. The patcher creates a new Disk 1 ADF and leaves the original
image untouched. Disk 2 does not need patching.

The whole game is still there, including the intros, menus, save support and
normal progression. You will need to provide your own legally obtained disk
images and Kickstart ROM; they are not included here.

## Supported disk images

Only this exact Disk 1 image is supported:

| Disk | Size | SHA-256 |
| --- | ---: | --- |
| Original Disk 1 | 901,120 bytes | `4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c` |

Use this unmodified Disk 2 with it:

| Disk | Size | SHA-256 |
| --- | ---: | --- |
| Original Disk 2 | 901,120 bytes | `32e15a76642f81d9b923fef5c94e35b55d78b193b8bdd7640a7cba276d83f0ec` |

With the correct source image, the patcher always produces this Disk 1:

| Disk | Size | SHA-256 |
| --- | ---: | --- |
| Patched Disk 1 | 901,120 bytes | `cbacc70089de79587d56194a57cbf94ed2ed57a944e3e37f9aa4a64429781bf1` |

The patcher checks the whole source image before doing any work. If you give it
a different release, crack, dump or previously modified image, it stops rather
than trying to patch unknown data.

A fixed AmigaDOS timestamp keeps the build reproducible: the same input creates
the same byte-for-byte output every time.

## Usage

Point the patcher at the supported original Disk 1 image:

```sh
python3 patch.py /path/to/SR2AMIGA_DISK1.adf
```

By default, the new image is written next to the source as
`StreetRod2-KS13-060-Disk1.adf`. To put it somewhere else, use `--output`:

```sh
python3 patch.py /path/to/SR2AMIGA_DISK1.adf \
  --output /path/to/StreetRod2-KS13-060-Disk1.adf
```

The patcher will not overwrite an existing file unless you add `--force`. When
it finishes, it prints the output hash so you can compare it with the value
above. Keep using the original Disk 2 when you play.

## Requirements

- Python 3
- an original Disk 1 ADF matching the size and SHA-256 above
- the original Disk 2 ADF
- FS-UAE with MC68060 emulation
- a 512 KiB Kickstart 1.3 ROM with SHA-256
  `1d68ba18412501d2a4b307a0a632b94a50b839c2c7c5ff2df6de2c38b99a921f`

Here is a known-good FS-UAE configuration. Replace the three file paths with
the ones on your system:

```ini
[fs-uae]
amiga_model = A500
cpu = 68060
fpu = 0
mmu = 0
accuracy = 1
jit_compiler = 0
uae_cpu_speed = real
chip_memory = 512
slow_memory = 512
fast_memory = 8192

kickstart_file = /path/to/Kickstart-1.3.rom
floppy_drive_count = 2
floppy_drive_0 = /path/to/StreetRod2-KS13-060-Disk1.adf
floppy_drive_1 = /path/to/SR2AMIGA_DISK2.adf

uae_sound_output = exact
```

This patch is deliberately limited to OCS; ECS and AGA are not supported. At
startup it checks for Kickstart 1.3 (Exec version 34) and an OCS Denise. Make
sure the emulator profile really provides an MC68060, because Kickstart 1.3
cannot identify it reliably. Leave the FPU and MMU disabled: the optimized
code uses integers, and Kickstart 1.3 does not manage native 68060 FPU task
contexts.

## What the patch changes

- Sets CIAA DDRA to the Amiga Hardware Reference Manual value `$03`
- Skips the manual protection after its original stack guard and returns the
  game routine's normal `D0=1` success result
- Adds a Kickstart 1.3 and OCS check at startup
- Installs the MC68060 covered-span line-drawing optimization

## Performance optimization

- Batched scratch RastPort, AreaInfo, and TmpRas setup.
- Batched `SetAPen(15)` calls.
- Inlined `graphics.library/Move` state updates.
- 68060-specific integer rendering path.
- FPU and MMU disabled to reduce unnecessary overhead.

## Tools used
Amitools, Ghidra, OpenAI

## Author

Timo Heimonen (timo.heimonen@proton.me)

## License

This patcher is released under the [MIT License](LICENSE).
