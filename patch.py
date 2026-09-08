#!/usr/bin/env python3
# Copyright (c) 2026 Timo Heimonen
# SPDX-License-Identifier: MIT

"""Patch an original Street Rod 2 Disk 1 ADF for KS3.1/AGA/MC68060.

This file is intentionally self-contained and uses only the Python standard
library.  It verifies the complete source and result images, edits the Amiga
Old File System directly, and never writes to the source ADF.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile


VERSION = "1.6.0"

BLOCK_SIZE = 512
BLOCK_LONGS = BLOCK_SIZE // 4
ADF_BLOCKS = 1760
ADF_SIZE = BLOCK_SIZE * ADF_BLOCKS
ROOT_BLOCK = 880
RESERVED_BLOCKS = 2
OFS_DATA_SIZE = BLOCK_SIZE - 24
HASH_SIZE = BLOCK_LONGS - 56
POINTERS_PER_BLOCK = BLOCK_LONGS - 56

T_HEADER = 2
T_DATA = 8
T_LIST = 16
ST_ROOT = 1
ST_USERDIR = 2
ST_FILE = 0xFFFFFFFD

SOURCE_ADF_SHA256 = (
    "4444796c1c9337baf16dffa982f1e66dc579a04d3e80a8ffa6a483b648e7bb1c"
)
PATCHED_ADF_SHA256 = (
    "b96bec56cbced4f6e620f107a7f5e08878fa831f1c94da2d509f47473b0d49de"
)
SOURCE_PROGRAM_SHA256 = (
    "a345fb91144d1ee577dcd5c80a8a8aa3b0a4e777ed9b5b4308d3a2b36d8df3a8"
)
PATCHED_PROGRAM_SHA256 = (
    "29669144cefc0753d4798c3f60f812e2cbc2e6326f82f4f12a9f2dec740a3415"
)
TRAINER_SHA256 = (
    "648dbe599570549aea8dd7793d4d405db7f81eb96793e45e52dc22bc575f8e92"
)

# Reproducible AmigaDOS modification time of the reference release:
# 8 September 2026 00:00:00, represented as days, minutes and 1/50 s ticks
# since the Amiga epoch.  Fixed metadata makes every patched ADF identical.
RELEASE_TIMESTAMP = (17782, 0, 0)

STARTUP_SEQUENCE = b""";c:SetPatch >NIL: r ;patch system functions
img.cru
Echo ""
Echo "KS3.1/AGA/060 patch 1.6.0 by Timo Heimonen"
Echo "(timo.heimonen@proton.me) - 08.09.2026"
Stack 6000
SetMap usa1
SetClock >NIL: Opt load
Addbuffers df0: 20
Street_Rod
LOADWB
endcli > nil:
"""

# Embedded 1.6.0 helpers; no assembler or external packages required.
PAYLOAD_10 = bytes.fromhex(
    "2f0247fa01344a6cbf766700009c4a536710202cdf4a90ab0008b0ab"
    "00106d00007c203900dff004e088024001ff0c40012c620000686100"
    "00804a406700ffd02c7800044eaeff886100006e4a40674427410008"
    "d2872741000436bc0001302cbf9cc1fc003041ecbf9ed1c0226cfb9c"
    "700b22d851c8fffc203900dff00402800001ffff52802740000c4eae"
    "ff82241f6000fef64eaeff826000ff742c6c9c584eaefef26000ff68"
    "42532c6c9c584eaefef2241f6000feae222cdf4a243900dff0040282"
    "0001ffffb2acdf4a663c2002e088024001ff0c400008652e7e000c40"
    "001e630e0c40009665200c40012c621a7e014a536710200190ab0004"
    "6b0c66044a476706600870014e7570004e75200190ab0008b0ab0010"
    "6d0c6e06b4ab000c650470014e7570004e7541fa000c4250426cbf9c"
    "4e754e71000000000000000000000000000000000000000300000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000000000000000000000000000000000000000000"
    "00000000000000000c800000000666260c904650533d661e0c28000a"
    "00056616700010280004610001024a80670841faff9020804e757e03"
    "2c78000443fa011a70244eaefdd84a80670000de2c4041fa01142208"
    "243c000003ed4eaeffe22c00670000bc220674014eaefe564a806700"
    "00a8220641fa00f72408263c000000854eaeffd07a00220641fa0180"
    "240876014eaeffd60c800000000166487000103a016a4a0567200c05"
    "0001660a0c00005b66107a0260d00c00004065ca0c00007e62c47a00"
    "60c00c00001b66047a0160b60c00009b66047a0260ac6100004e4a80"
    "67a42e0041fafeda208720075780c0fc000541fa00fed1c022062408"
    "76054eaeffd0220641fa0100240876044eaeffd0220674004eaefe56"
    "22064eaeffdc224e2c7800044eaefe624e750c00000d67200c00000a"
    "671a0c00003165180c00003462120280000000ff04800000002e4e75"
    "70034e7570004e75646f732e6c69627261727900434f4e534f4c453a"
    "000a53656c6563742064726976696e6720465053206c696d69743a0a"
    "0a20203120202031362e372046505320202864656661756c74290a20"
    "203220202031322e35204650530a20203320202031302e3020465053"
    "0a20203420202020382e33204650530a0a507265737320312d342c20"
    "6f7220454e54455220666f722064656661756c743a2031362e372031"
    "322e352031302e3020382e3320204650530a0000"
)

PAYLOAD_23 = bytes.fromhex(
    "2f0e41fa004c10b900bfde0008b9000000bfde0043fa003e4aa900126608"
    "41fa0014234800122c7800044eaeff4c2c5f70004e756112103a00180000"
    "001113c000bfde0070004e754e55fff46000fd5a00004e71000000000000"
    "000002000000000000000000000000004e71"
)

PAYLOAD_0 = bytes.fromhex(
    "48e77efe48e7fffe2c7800044bfa00244eaeffe24cdf7fff6000cc9e"
    "2f002c7800044bfa00264eaeffe2201f4cdf7f7e4e7541fa00244e7a"
    "10022081f4980081000080004e7b10024e7341fa000c2210f4984e7b"
    "10024e73000000000000000048e7fffe41fafffa41e8cc5070092210"
    "e589204151c8fff845e807842017206f00204e924cdf7fff24482400"
    "4e754e71"
)

PAYLOAD_42 = bytes.fromhex(
    "205f48e73710267c535232303e2d000858884ed0"
)

PAYLOAD_45 = bytes.fromhex(
    "205f5488b7fc535232306708b7fc53523231661e0c6d000f00106610b7fc"
    "535232316720267c535232316006267c535232302f0841e8321a4e90205f"
    "302d001054884ed043ecfb303347002433460026006900010020137c000f"
    "001e41e800244ed04e71"
)

PROGRAM_PATCHES = (
    # Original file offset, expected bytes, replacement bytes.
    # Select the driving FPS limit in the current console before original runtime initialization; replay argument setup
    (0x14c, bytes.fromhex("24482400"), bytes.fromhex("610033a6")),
    # Clear CIAA DDRA bit 7 before reading joystick fire; preserve all other port directions
    (0x11746, bytes.fromhex("00400080"), bytes.fromhex("0240007f")),
    # Keep LINK and the original stack guard, then return D0=1 success from the manual check, as in the user-supplied patch
    (0x35bf8, bytes.fromhex("48e72300554f"), bytes.fromhex("70014e5d4e75")),
    # Queue original music tick at level 1 so Paula level 4 can interrupt BeginIO
    (0x10fac, bytes.fromhex("4e55fff4"), bytes.fromhex("6000025a")),
    # Select the first active BPLCON0 in the KS3.1 AGA Copper list for four-plane road; retain six-plane cockpit at the split
    (0xa3a4, bytes.fromhex("6706"), bytes.fromhex("671a")),
    # Apply the selected 3/4/5/6 complete PAL-field minimum interval with beam phase and safe raster publication
    (0xa4a6, bytes.fromhex("4eaefe802e00"), bytes.fromhex("600000ac4e71")),
    # Clear publication history when initializing a driving display and replay original buffer-index reset
    (0xa01e, bytes.fromhex("426cbf9c"), bytes.fromhex("6100065e")),
    # Enable the MC68060 instruction cache after LoadSeg through exec.Supervisor
    (0x148, bytes.fromhex("48e77efe"), bytes.fromhex("6000334a")),
    # Restore the incoming CACR before returning to Kickstart 3.1
    (0x32c, bytes.fromhex("4cdf7f7e"), bytes.fromhex("60003182")),
    # Enter the framebuffer-verified 68060 covered-span optimization
    (0x1ce74, bytes.fromhex("48e737003e2d"), bytes.fromhex("6100419e4e71")),
    # Restore the A3 batch marker with the original saved registers
    (0x1d02a, bytes.fromhex("00ec"), bytes.fromhex("08ec")),
    # Use the KS3.1 graphics.library 40.24 Move-compatible tail inside covered-span batches
    (0x2192a, bytes.fromhex("4eba321e302d"), bytes.fromhex("610032b44e71")),
)

HUNK_SIZE_PATCHES = (
    (0x3c, 0x17c, 0x261),
    (0x9f60, 0x17c, 0x261),
    (0x70, 0x6c4, 0x6df),
    (0xf6f4, 0x6c4, 0x6df),
    (0x14, 0xcd3, 0xcf7),
    (0x144, 0xcd3, 0xcf7),
    (0xbc, 0x1711, 0x1716),
    (0x1b3cc, 0x1711, 0x1716),
    (0xc8, 0xd8c, 0xda5),
    (0x215ac, 0xd8c, 0xda5),
)

HUNK_PAYLOADS = (
    # Descending original file offsets keep earlier insertion points stable.
    (0x24be0, PAYLOAD_45),
    (0x21014, PAYLOAD_42),
    (0x11208, PAYLOAD_23),
    (0xa554, PAYLOAD_10),
    (0x3494, PAYLOAD_0),
)


class PatchError(RuntimeError):
    """A source validation or patching error safe to show to the user."""


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def _long_offset(index: int) -> int:
    if index < 0:
        index += BLOCK_LONGS
    if not 0 <= index < BLOCK_LONGS:
        raise PatchError(f"invalid OFS longword index: {index}")
    return index * 4


def _get_long(block: bytes | bytearray, index: int) -> int:
    return struct.unpack_from(">I", block, _long_offset(index))[0]


def _put_long(block: bytearray, index: int, value: int) -> None:
    struct.pack_into(">I", block, _long_offset(index), value & 0xFFFFFFFF)


def _get_bstr(block: bytes | bytearray, index: int, maximum: int) -> bytes:
    offset = _long_offset(index)
    length = block[offset]
    if length > maximum:
        raise PatchError("invalid OFS BSTR length")
    return bytes(block[offset + 1 : offset + 1 + length])


def _put_bstr(block: bytearray, index: int, value: bytes, maximum: int) -> None:
    if len(value) > maximum:
        raise PatchError(f"OFS name is longer than {maximum} bytes")
    offset = _long_offset(index)
    block[offset : offset + 1 + maximum] = bytes(1 + maximum)
    block[offset] = len(value)
    block[offset + 1 : offset + 1 + len(value)] = value


def _put_timestamp(block: bytearray, index: int) -> None:
    for position, value in enumerate(RELEASE_TIMESTAMP):
        _put_long(block, index + position, value)


def _block_sum(block: bytes | bytearray) -> int:
    return sum(struct.unpack(">128I", block)) & 0xFFFFFFFF


def _set_checksum(block: bytearray, index: int = 5) -> None:
    _put_long(block, index, 0)
    _put_long(block, index, (-_block_sum(block)) & 0xFFFFFFFF)


def _name_hash(name: bytes) -> int:
    value = len(name)
    for character in name.upper():
        value = ((value * 13) + character) & 0x7FF
    return value % HASH_SIZE


def patch_program(source: bytes) -> bytes:
    """Apply the verified MC68060 HUNK changes to STREET_ROD."""
    if len(source) != 270116 or sha256(source) != SOURCE_PROGRAM_SHA256:
        raise PatchError("STREET_ROD does not match the supported original")

    result = bytearray(source)
    for offset, expected, replacement in PROGRAM_PATCHES:
        actual = bytes(result[offset : offset + len(expected)])
        if actual != expected:
            raise PatchError(
                f"unexpected STREET_ROD bytes at file offset {offset:#x}"
            )
        result[offset : offset + len(expected)] = replacement

    for offset, expected, replacement in HUNK_SIZE_PATCHES:
        actual = int.from_bytes(result[offset : offset + 4], "big")
        if actual != expected:
            raise PatchError(
                f"unexpected HUNK size at STREET_ROD file offset {offset:#x}"
            )
        result[offset : offset + 4] = replacement.to_bytes(4, "big")

    # Insert in descending order so all offsets refer to the original HUNK
    # executable, even when several earlier hunks grow.
    for offset, payload in HUNK_PAYLOADS:
        result[offset:offset] = payload

    if len(result) != 271404 or sha256(result) != PATCHED_PROGRAM_SHA256:
        raise PatchError("internal STREET_ROD result verification failed")
    return bytes(result)


@dataclass(frozen=True)
class EntryLocation:
    block_number: int
    parent_number: int
    hash_index: int
    previous_number: int | None


@dataclass(frozen=True)
class FileRecord:
    location: EntryLocation
    data: bytes
    data_blocks: tuple[int, ...]
    extension_blocks: tuple[int, ...]

    @property
    def all_blocks(self) -> tuple[int, ...]:
        return (
            (self.location.block_number,)
            + self.extension_blocks
            + self.data_blocks
        )


class OFSImage:
    """Minimal reader/writer for the exact DOS0/OFS operations used here."""

    def __init__(self, source: bytes):
        if len(source) != ADF_SIZE:
            raise PatchError(
                f"source ADF is {len(source):,} bytes; expected {ADF_SIZE:,}"
            )
        self.image = bytearray(source)
        if self.image[:4] != b"DOS\0":
            raise PatchError("source is not an Amiga DOS0/OFS disk image")

        root = self._read_block(ROOT_BLOCK)
        self._validate_block(root, T_HEADER, ST_ROOT, "root")
        if _get_long(root, 3) != HASH_SIZE:
            raise PatchError("unsupported OFS root hash-table size")
        self.bitmap_block_number = _get_long(root, -49)
        if self.bitmap_block_number == 0:
            raise PatchError("OFS root block has no bitmap")
        self.bitmap = self._read_block(self.bitmap_block_number)
        if _block_sum(self.bitmap) != 0:
            raise PatchError("invalid OFS bitmap checksum")

    def _read_block(self, number: int) -> bytearray:
        if not 0 <= number < ADF_BLOCKS:
            raise PatchError(f"OFS block number is out of range: {number}")
        start = number * BLOCK_SIZE
        return bytearray(self.image[start : start + BLOCK_SIZE])

    def _write_block(self, number: int, block: bytearray) -> None:
        if len(block) != BLOCK_SIZE:
            raise PatchError("attempted to write a non-512-byte OFS block")
        start = number * BLOCK_SIZE
        self.image[start : start + BLOCK_SIZE] = block

    @staticmethod
    def _validate_block(
        block: bytes | bytearray,
        expected_type: int,
        expected_subtype: int | None,
        description: str,
    ) -> None:
        if _get_long(block, 0) != expected_type:
            raise PatchError(f"invalid {description} block type")
        if expected_subtype is not None and _get_long(block, -1) != expected_subtype:
            raise PatchError(f"invalid {description} block subtype")
        if _block_sum(block) != 0:
            raise PatchError(f"invalid {description} block checksum")

    def _write_standard_block(self, number: int, block: bytearray) -> None:
        _set_checksum(block)
        self._write_block(number, block)

    def _directory_hash_size(self, parent_number: int, parent: bytearray) -> int:
        if parent_number == ROOT_BLOCK:
            size = _get_long(parent, 3)
        else:
            self._validate_block(parent, T_HEADER, ST_USERDIR, "directory")
            size = HASH_SIZE
        if size != HASH_SIZE:
            raise PatchError("unsupported OFS directory hash-table size")
        return size

    def find_entry(self, parent_number: int, name: bytes) -> EntryLocation:
        parent = self._read_block(parent_number)
        self._directory_hash_size(parent_number, parent)
        hash_index = _name_hash(name)
        current = _get_long(parent, 6 + hash_index)
        previous: int | None = None
        seen: set[int] = set()

        while current:
            if current in seen:
                raise PatchError("cyclic OFS directory hash chain")
            seen.add(current)
            entry = self._read_block(current)
            if _get_long(entry, 0) != T_HEADER or _block_sum(entry) != 0:
                raise PatchError("invalid OFS directory entry")
            if _get_long(entry, -3) != parent_number:
                raise PatchError("OFS directory entry has the wrong parent")
            entry_name = _get_bstr(entry, -20, 30)
            if entry_name.upper() == name.upper():
                return EntryLocation(
                    current, parent_number, hash_index, previous
                )
            previous = current
            current = _get_long(entry, -4)

        display_name = name.decode("ascii", errors="replace")
        raise PatchError(f"required file or directory not found: {display_name}")

    def find_path(self, path: str) -> EntryLocation:
        parent = ROOT_BLOCK
        location: EntryLocation | None = None
        for component in path.split("/"):
            if not component:
                raise PatchError(f"invalid OFS path: {path}")
            location = self.find_entry(parent, component.encode("ascii"))
            parent = location.block_number
        assert location is not None
        return location

    def read_file(self, path: str) -> FileRecord:
        location = self.find_path(path)
        header = self._read_block(location.block_number)
        self._validate_block(header, T_HEADER, ST_FILE, f"{path} header")
        if _get_long(header, 1) != location.block_number:
            raise PatchError(f"{path} header has the wrong own-key")

        data_blocks: list[int] = []
        extension_blocks: list[int] = []

        def add_pointers(block: bytearray) -> None:
            count = _get_long(block, 2)
            if count > POINTERS_PER_BLOCK:
                raise PatchError(f"{path} has too many pointers in a file block")
            for index in range(count):
                pointer = _get_long(block, -51 - index)
                if pointer == 0:
                    raise PatchError(f"{path} contains a null data-block pointer")
                data_blocks.append(pointer)

        add_pointers(header)
        extension = _get_long(header, -2)
        seen = {location.block_number}
        while extension:
            if extension in seen:
                raise PatchError(f"{path} has a cyclic extension chain")
            seen.add(extension)
            block = self._read_block(extension)
            self._validate_block(block, T_LIST, ST_FILE, f"{path} extension")
            if _get_long(block, 1) != extension:
                raise PatchError(f"{path} extension has the wrong own-key")
            if _get_long(block, -3) != location.block_number:
                raise PatchError(f"{path} extension has the wrong parent")
            extension_blocks.append(extension)
            add_pointers(block)
            extension = _get_long(block, -2)

        byte_size = _get_long(header, -47)
        expected_blocks = (byte_size + OFS_DATA_SIZE - 1) // OFS_DATA_SIZE
        if len(data_blocks) != expected_blocks:
            raise PatchError(f"{path} has an inconsistent data-block count")

        contents = bytearray()
        for index, number in enumerate(data_blocks):
            block = self._read_block(number)
            self._validate_block(block, T_DATA, None, f"{path} data")
            # The supported original ADF contains a stale hdr_key in this
            # file's OFS data blocks.  AmigaDOS follows the header's pointer
            # table and the next-data chain, so validate those authoritative
            # links instead.  Newly written blocks receive the correct key.
            if _get_long(block, 2) != index + 1:
                raise PatchError(f"{path} data block has the wrong sequence number")
            expected_next = data_blocks[index + 1] if index + 1 < len(data_blocks) else 0
            if _get_long(block, 4) != expected_next:
                raise PatchError(f"{path} data chain is inconsistent")
            size = _get_long(block, 3)
            if size > OFS_DATA_SIZE:
                raise PatchError(f"{path} data block is too large")
            contents += block[24 : 24 + size]

        if len(contents) != byte_size:
            raise PatchError(f"{path} byte size does not match its data blocks")
        return FileRecord(
            location,
            bytes(contents),
            tuple(data_blocks),
            tuple(extension_blocks),
        )

    def _bitmap_position(self, number: int) -> tuple[int, int]:
        if not RESERVED_BLOCKS <= number < ADF_BLOCKS:
            raise PatchError(f"invalid allocatable OFS block: {number}")
        relative = number - RESERVED_BLOCKS
        return relative // 32, relative % 32

    def _is_free(self, number: int) -> bool:
        long_index, bit_index = self._bitmap_position(number)
        value = _get_long(self.bitmap, 1 + long_index)
        return bool(value & (1 << bit_index))

    def _set_free(self, number: int, is_free: bool) -> None:
        long_index, bit_index = self._bitmap_position(number)
        value = _get_long(self.bitmap, 1 + long_index)
        mask = 1 << bit_index
        if is_free:
            value |= mask
        else:
            value &= ~mask
        _put_long(self.bitmap, 1 + long_index, value)

    def _allocate(self, count: int) -> list[int]:
        result: list[int] = []
        bitmap_longs = ((ADF_BLOCKS - RESERVED_BLOCKS) + 31) // 32
        start_long = (ROOT_BLOCK - RESERVED_BLOCKS) // 32
        for step in range(bitmap_longs):
            long_index = (start_long + step) % bitmap_longs
            base = RESERVED_BLOCKS + long_index * 32
            limit = min(32, ADF_BLOCKS - base)
            for bit_index in range(limit):
                number = base + bit_index
                if self._is_free(number):
                    self._set_free(number, False)
                    result.append(number)
                    if len(result) == count:
                        return result
        raise PatchError(f"not enough free blocks in source ADF (need {count})")

    def _update_parent_and_disk_time(self, parent_number: int) -> None:
        parent = self._read_block(parent_number)
        _put_timestamp(parent, -23)
        self._write_standard_block(parent_number, parent)
        root = self._read_block(ROOT_BLOCK)
        _put_timestamp(root, -10)
        self._write_standard_block(ROOT_BLOCK, root)

    def delete_file(self, path: str) -> FileRecord:
        record = self.read_file(path)
        location = record.location
        header = self._read_block(location.block_number)
        next_entry = _get_long(header, -4)

        if location.previous_number is None:
            parent = self._read_block(location.parent_number)
            _put_long(parent, 6 + location.hash_index, next_entry)
            self._write_standard_block(location.parent_number, parent)
        else:
            previous = self._read_block(location.previous_number)
            _put_long(previous, -4, next_entry)
            self._write_standard_block(location.previous_number, previous)

        for number in record.all_blocks:
            if self._is_free(number):
                raise PatchError(f"{path} references an already-free OFS block")
            self._set_free(number, True)
        self._update_parent_and_disk_time(location.parent_number)
        return record

    def create_file(self, parent_number: int, name: bytes, contents: bytes) -> None:
        try:
            self.find_entry(parent_number, name)
        except PatchError as error:
            if not str(error).startswith("required file or directory not found:"):
                raise
        else:
            display_name = name.decode("ascii", errors="replace")
            raise PatchError(f"OFS entry already exists: {display_name}")

        data_count = (len(contents) + OFS_DATA_SIZE - 1) // OFS_DATA_SIZE
        extension_count = max(
            0,
            (data_count - POINTERS_PER_BLOCK + POINTERS_PER_BLOCK - 1)
            // POINTERS_PER_BLOCK,
        )
        allocated = self._allocate(1 + extension_count + data_count)
        header_number = allocated[0]
        extension_numbers = allocated[1 : 1 + extension_count]
        data_numbers = allocated[1 + extension_count :]

        parent = self._read_block(parent_number)
        self._directory_hash_size(parent_number, parent)
        hash_index = _name_hash(name)
        old_hash_head = _get_long(parent, 6 + hash_index)

        header_pointers = data_numbers[:POINTERS_PER_BLOCK]
        header = bytearray(BLOCK_SIZE)
        _put_long(header, 0, T_HEADER)
        _put_long(header, 1, header_number)
        _put_long(header, 2, len(header_pointers))
        _put_long(header, 4, data_numbers[0] if data_numbers else 0)
        for index, number in enumerate(header_pointers):
            _put_long(header, -51 - index, number)
        _put_long(header, -48, 0)
        _put_long(header, -47, len(contents))
        _put_timestamp(header, -23)
        _put_bstr(header, -20, name, 30)
        _put_long(header, -4, old_hash_head)
        _put_long(header, -3, parent_number)
        _put_long(header, -2, extension_numbers[0] if extension_numbers else 0)
        _put_long(header, -1, ST_FILE)
        self._write_standard_block(header_number, header)

        pointer_offset = POINTERS_PER_BLOCK
        for index, number in enumerate(extension_numbers):
            pointers = data_numbers[
                pointer_offset : pointer_offset + POINTERS_PER_BLOCK
            ]
            next_extension = (
                extension_numbers[index + 1]
                if index + 1 < len(extension_numbers)
                else 0
            )
            block = bytearray(BLOCK_SIZE)
            _put_long(block, 0, T_LIST)
            _put_long(block, 1, number)
            _put_long(block, 2, len(pointers))
            for pointer_index, pointer in enumerate(pointers):
                _put_long(block, -51 - pointer_index, pointer)
            _put_long(block, -3, header_number)
            _put_long(block, -2, next_extension)
            _put_long(block, -1, ST_FILE)
            self._write_standard_block(number, block)
            pointer_offset += POINTERS_PER_BLOCK

        for index, number in enumerate(data_numbers):
            start = index * OFS_DATA_SIZE
            chunk = contents[start : start + OFS_DATA_SIZE]
            next_data = data_numbers[index + 1] if index + 1 < data_count else 0
            block = bytearray(BLOCK_SIZE)
            _put_long(block, 0, T_DATA)
            _put_long(block, 1, header_number)
            _put_long(block, 2, index + 1)
            _put_long(block, 3, len(chunk))
            _put_long(block, 4, next_data)
            block[24 : 24 + len(chunk)] = chunk
            self._write_standard_block(number, block)

        _put_long(parent, 6 + hash_index, header_number)
        _put_timestamp(parent, -23)
        self._write_standard_block(parent_number, parent)
        root = self._read_block(ROOT_BLOCK)
        _put_timestamp(root, -10)
        self._write_standard_block(ROOT_BLOCK, root)

    def finish(self) -> bytes:
        _set_checksum(self.bitmap, 0)
        self._write_block(self.bitmap_block_number, self.bitmap)
        # amitools writes the root block whenever it flushes a dirty bitmap.
        # Normalize the BSTR padding as amitools does, then recalculate it as
        # the final reproducible filesystem operation.
        root = self._read_block(ROOT_BLOCK)
        root_name = _get_bstr(root, -20, 30)
        _put_bstr(root, -20, root_name, 30)
        _set_checksum(root)
        self._write_block(ROOT_BLOCK, root)
        return bytes(self.image)


def build_patched_adf(source: bytes) -> bytes:
    if len(source) != ADF_SIZE or sha256(source) != SOURCE_ADF_SHA256:
        actual = sha256(source)
        raise PatchError(
            "unsupported Disk 1 image: expected SHA-256 "
            f"{SOURCE_ADF_SHA256}, got {actual}"
        )

    ofs = OFSImage(source)
    original_program = ofs.delete_file("STREET_ROD")
    patched_program = patch_program(original_program.data)
    ofs.create_file(ROOT_BLOCK, b"STREET_ROD", patched_program)

    original_startup = ofs.delete_file("s/startup-sequence")
    if sha256(original_startup.data) != (
        "ea12869fb12ec9175f235d658150ee92d426f431e0f1d04103bd3e93e329fe65"
    ):
        raise PatchError("startup-sequence does not match the supported original")
    startup_directory = ofs.find_path("s").block_number
    ofs.create_file(startup_directory, b"startup-sequence", STARTUP_SEQUENCE)

    trainer = ofs.read_file("StreetRodA.sav")
    if len(trainer.data) != 304 or sha256(trainer.data) != TRAINER_SHA256:
        raise PatchError("trainer save changed unexpectedly")

    result = ofs.finish()
    actual_result_hash = sha256(result)
    if actual_result_hash != PATCHED_ADF_SHA256:
        raise PatchError(
            "internal patched ADF verification failed: expected SHA-256 "
            f"{PATCHED_ADF_SHA256}, got {actual_result_hash}"
        )

    # Verify the logical files from the completed image as well as its hash.
    check = OFSImage(result)
    if check.read_file("STREET_ROD").data != patched_program:
        raise PatchError("patched STREET_ROD read-back verification failed")
    if check.read_file("s/startup-sequence").data != STARTUP_SEQUENCE:
        raise PatchError("startup-sequence read-back verification failed")
    return result


def default_output_path(source: Path) -> Path:
    return source.with_name("StreetRod2-KS31-AGA-060-Disk1.adf")


def write_atomic(path: Path, data: bytes, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise PatchError(f"output already exists: {path} (use --force to replace it)")

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Patch an original Street Rod 2 Amiga Disk 1 ADF for "
            f"Kickstart 3.1, PAL AGA and an MC68060 (version {VERSION})."
        )
    )
    parser.add_argument("source", type=Path, help="original Disk 1 ADF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output ADF (default: StreetRod2-KS31-AGA-060-Disk1.adf beside source)",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="replace an existing output file"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else default_output_path(source)
    )

    try:
        if source == output:
            raise PatchError("source and output paths must be different")
        try:
            source_data = source.read_bytes()
        except OSError as error:
            raise PatchError(f"cannot read source ADF {source}: {error}") from error

        result = build_patched_adf(source_data)
        write_atomic(output, result, args.force)
    except PatchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: cannot write output ADF {output}: {error}", file=sys.stderr)
        return 1

    print(f"Source verified: {source}")
    print(f"Patched ADF:     {output}")
    print(f"SHA-256:         {PATCHED_ADF_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
