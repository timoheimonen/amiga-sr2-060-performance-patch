# Changelog

Changes to the standalone Street Rod 2 Kickstart 3.1 / PAL AGA / MC68060 patcher.

## 1.6.0 — 2026-09-08

- Add a startup FPS menu: approximately 16.7, 12.5, 10 or 8.3 FPS; Enter selects 16.7 FPS.
- Keep the selected limit across driving-view changes, using the existing safe raster timing.
- Support `Street_Rod FPS=1` through `FPS=4` to select the limit directly.

## 1.5.0 — 2026-09-08

- Fix joystick fire-button input by clearing CIAA DDRA bit 7 while preserving the other port directions.

## 1.4.0 — 2026-09-06

- Cap driving at approximately 16.7 FPS using three complete PAL fields between road-buffer publications.
- Wait only for the remaining interval; slower frames receive no extra cap delay and cannot build up catch-up frames.
- Update the embedded helper, assembly source, manifest, startup banner and reproducible output hashes.

## 1.3.0 — 2026-09-06

- Reduce road-buffer swap waiting with safe PAL raster timing and buffer-reuse protection.
- Achieve **14% higher FPS** (12.48 → 14.23) in the stationary Mulholland
  [FS-UAE benchmark](README.md#performance).
- Update the patcher, assembler source, startup banner and reproducible output hashes.

## 1.2.0

- Move the standalone patcher from the earlier KS1.3/OCS target to Kickstart 3.1,
  AGA and MC68060.
- Include the covered-span drawing optimization and instruction-cache helper,
  with restoration of the incoming cache-control register on normal exit.
- Include the deferred audio timer handler, corrected road/cockpit bitplanes,
  vertical-blank road-buffer swap and manual-protection bypass.
- Remove the earlier KS1.3/OCS startup gate and CIAA DDRA change.
- Provide a self-contained Python patcher with reproducible Disk 1 output and
  verification of source images, instruction bytes, HUNK sizes and output hashes.

## Earlier KS1.3/OCS release

The previous target used a KS1.3/OCS startup gate and CIAA DDRA change. It was
replaced by the KS3.1/AGA/MC68060 release; those earlier changes are not included
in releases 1.2.0–1.4.0.
