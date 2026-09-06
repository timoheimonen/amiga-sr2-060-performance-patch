# Changelog

Changes to the standalone Street Rod 2 Kickstart 3.1 / PAL AGA / MC68060 patcher.
Release 1.3.0 improves the road-buffer timing of version 1.2.0.

## 1.3.0 — 2026-09-06

- Reduce road-buffer swap waiting with safe PAL raster timing and buffer-reuse protection.
- Achieve **14% higher FPS** (12.48 → 14.23) in the stationary Mulholland
  [FS-UAE benchmark](README.md#performance). Moving gameplay and hardware remain unverified.
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
in 1.2.0 or 1.3.0.
