"""Standard-library-only Amiga HUNK self-extractor using Python zlib.

The embedded code is our SR2_ZlibLoader.s and Keir Fraser's public-domain
inflate routine. It contains no game bytes. Rebuild with vasm -m68000 -Fbin.
CODE/DATA/BSS with long or short RELOC32 records are accepted; symbols and
debug records are omitted. Other formats fail closed.
"""
from dataclasses import dataclass
import struct
import zlib

LOADER = bytes.fromhex(
    "598f48e7fffe47fa048c2f6b0018003c2c780004201372014eaeff3a4a80670000922840222b001041f31800202b0004"
    "6100008ab0ab0008666c222b00104bf3180061000408204c20136170b0ab000c665445eb00182e2b00142007e5884bf2"
    "0800204c225a201d670622d8538066fa226afffc241d6714201d221d4deb001822361800d3b10800538266ec538766d4"
    "2c780004224c20134eaeff2e4eaefd844cdf7fff4e752c780004224c20134eaeff2e4cdf7fff588f70144e7572017400"
    "4a80672876001618d283b2bc0000fff1650692bc0000fff1d481b4bc0000fff1650694bc0000fff1538066d848423401"
    "20024e75ff5b006c0336dbb66ddbb66ddbb6cddbb66ddbb66ddba86dce8b6d3b48e7ff00720874002f0251c9fffc5340"
    "32002448141ad4025277200051c9fff6244f720f74003e82d452d44234c251c9fff83200787f24487a001a1a67745345"
    "3c05dc4636376000527760003c057400e24be35251cefffa1602d6433c009c41bc6f002a6302e54eba3c0008641ee74e"
    "8c05740054050bc23e024447ce7c01ff864733863000964264f86026e04a510547f130003e13660a52443e0408c7000f"
    "3687e20adf47de4747f1700051cdffe6368651c9ff844fef00244cdf00ff4e757000bc01640a101deda88a80500660f0"
    "03c05340c045e2ad9c014e75e64e9ac67a007c00721061d8544d600218dd51c8fffc4e7548e706047a007c004bfafee6"
    "303c027d6004303c028072002f0151c8fffc720561aad07c01013f00720561a052403f0072046198564043fa01fd41ef"
    "0004740036007203618614191180200051cbfff443ef01447013727f6100feb2342f0002d45753422448204970007207"
    "bc01620a101ded688a40500670001005d040303000006a1ae04d5106530664041a1d7c07e24dd140d040303000006bec"
    "600ac2005201e26d9c01e648b03c00106532671ab03c0011670a72076100ff125040600672036100ff087200600a7202"
    "6100fefe122affff5440944014c151c8fffc600214c051caff847000323c008920c051c9fffc41ef0004302f0002323c"
    "010038016100fe0ad0c043ef07a0301772006100fdfc4aaf0a0467064cef206009fc41ef014470007207bc01620a101d"
    "ed688a40500670001005d040303000006a1ae04d5106530664041a1d7c07e24dd140d040303000006bec600ac2005201"
    "e26d9c01e648b044640a18c060b84fef0a084e7567f845ef0684d4c0321a7000bc01640a101deda88a80500660f003c0"
    "5340c045e2ad9c01d052360041ef07a070007207bc01620a101ded688a40500670001005d040303000006a1ae04d5106"
    "530664041a1d7c07e24dd140d040303000006bec600ac2005201e26d9c01e64845ef0a10d4c0321a7000bc01640a101d"
    "eda88a80500660f003c05340c045e2ad9c01d052204c90c0e24b6504534318d818d851cbfffa6000ff0a205f3600e86b"
    "534364027600720007c194413f023f0351c8ffea4ed000182a10111200080709060a050b040c030d020e010f48e7fefc"
    "243c000001022f025242701b780261ba343c8001701d780161b07a007c0072036100fd5e2f00e208103b00bc41fafd6e"
    "4eb00000201fe20864e44fef00ec4cdf3f7f4e75"
)


def longs(*values):
    return struct.pack('>' + 'I' * len(values), *values)


@dataclass
class Hunk:
    allocation: int
    kind: int
    size: int
    data: bytes
    relocations: list


def parse(data):
    pos = 0

    def word():
        nonlocal pos
        if pos + 4 > len(data):
            raise ValueError('Truncated HUNK file')
        value = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        return value

    if word() != 1011 or word() != 0:
        raise ValueError('Expected HUNK_HEADER without resident libraries')
    count, first, last = word(), word(), word()
    if not 1 <= count <= 1024 or first != 0 or last != count - 1:
        raise ValueError('Unsupported HUNK table')
    allocations = [word() for _ in range(count)]
    if any(a >> 30 == 3 for a in allocations):
        raise ValueError('Extended allocation flags are unsupported')
    hunks = []
    for allocation in allocations:
        kind, size = word() & 0x3fffffff, word()
        if kind not in (1001, 1002, 1003):
            raise ValueError('Unsupported HUNK type')
        if size > allocation & 0x3fffffff:
            raise ValueError('HUNK exceeds allocation')
        length = 0 if kind == 1003 else size * 4
        if pos + length > len(data):
            raise ValueError('Truncated HUNK contents')
        contents = data[pos:pos + length]
        pos += length
        relocations = []
        while True:
            tag = word()
            if tag == 1010:
                break
            if tag in (1004, 1015, 1020):
                short = tag != 1004

                def relocation_word():
                    nonlocal pos
                    if not short:
                        return word()
                    if pos + 2 > len(data):
                        raise ValueError('Truncated short relocation')
                    value = struct.unpack_from('>H', data, pos)[0]
                    pos += 2
                    return value

                while True:
                    n = relocation_word()
                    if not n:
                        break
                    target = relocation_word()
                    if target >= count or n > len(data) // 2:
                        raise ValueError('Invalid relocation target/count')
                    for _ in range(n):
                        offset = relocation_word()
                        if offset & 1 or offset + 4 > length:
                            raise ValueError('Invalid relocation offset')
                        relocations.append((offset, target))
                if short:
                    pos = (pos + 3) & ~3
            elif tag == 1008:  # Symbols do not participate in loading.
                while True:
                    n = word()
                    if not n:
                        break
                    pos += n * 4
                    word()  # symbol value, with bounds check
            elif tag == 1009:  # Debug information, not loaded into the HUNK.
                n = word()
                pos += n * 4
                if pos > len(data):
                    raise ValueError('Truncated debug record')
            else:
                raise ValueError(f'Unsupported HUNK record {tag}')
        if len({off for off, _ in relocations}) != len(relocations):
            raise ValueError('Duplicate relocation')
        hunks.append(Hunk(allocation, kind, size, contents, relocations))
    if pos != len(data):
        raise ValueError('Trailing HUNK data')
    if hunks[0].kind != 1001 or len(hunks[0].data) < 8:
        raise ValueError('First HUNK must contain an executable entry')
    return hunks


def pack(data):
    hunks = parse(data)
    flat = b''.join(h.data for h in hunks)
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    compressed = compressor.compress(flat) + compressor.flush()
    if zlib.decompress(compressed, -15) != flat:
        raise ValueError('DEFLATE round-trip failed')
    descriptors = b''.join(
        longs(len(h.data) // 4, len(h.relocations)) +
        b''.join(longs(offset, target * 4) for offset, target in h.relocations)
        for h in hunks)
    offset = 24 + len(hunks) * 4 + len(descriptors)
    metadata = longs(len(flat), len(compressed), zlib.adler32(compressed),
                     zlib.adler32(flat), offset, len(hunks))
    code = LOADER + metadata + bytes(len(hunks) * 4) + descriptors + compressed
    # Inflate may read a lookahead word beyond the DEFLATE end.
    code += bytes(4 + (-len(code) % 4))
    result = longs(1011, 0, len(hunks) + 1, 0, len(hunks))
    result += longs(*(h.allocation for h in hunks), len(code) // 4)
    # DOS loads an entry JMP in original HUNK 0, the others start zeroed.
    result += longs(1001, 2) + bytes.fromhex('4ef9000000004e71')
    result += longs(1004, 1, len(hunks), 2, 0, 1010)
    for h in hunks[1:]:
        result += longs(1003, h.allocation & 0x3fffffff, 1010)
    result += longs(1001, len(code) // 4) + code + longs(1004)
    for index in range(len(hunks)):
        result += longs(1, index, len(LOADER) + 24 + index * 4)
    result += longs(0, 1010)
    parsed = parse(result)
    if [h.allocation for h in parsed[:-1]] != [h.allocation for h in hunks]:
        raise ValueError('Original allocation table changed')
    return result
