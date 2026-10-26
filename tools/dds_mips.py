"""Join single-level BC7 DDS files into one DDS with a mip chain.

    python3 dds_mips.py OUT.dds LEVEL0.dds LEVEL1.dds ...

Each input is a DX10 DDS (bc7enc's output) of one level, each half the size
of the one before (rounded down, at least 1). The output has LEVEL0's header
with the mip count set, then every level's block data in order -- what the
HD texture loader (src/vk/vkr_hdtex.c) reads.
"""
import struct
import sys

DDSD_MIPMAPCOUNT = 0x20000
DDSCAPS_COMPLEX, DDSCAPS_MIPMAP = 0x8, 0x400000
HEADER = 4 + 124 + 20                      # magic, DDS_HEADER, DDS_HEADER_DXT10
BC7 = (98, 99)


def read_level(path):
    d = open(path, "rb").read()
    if len(d) < HEADER:
        raise SystemExit(f"{path}: too short for a DDS")
    if d[:4] != b"DDS " or d[84:88] != b"DX10" or struct.unpack_from("<I", d, 128)[0] not in BC7:
        raise SystemExit(f"{path}: not a DX10 BC7 DDS")
    h, w = struct.unpack_from("<II", d, 12)
    if struct.unpack_from("<I", d, 28)[0] > 1:
        raise SystemExit(f"{path}: has a mip chain already; give one level per file")
    want = HEADER + ((w + 3) // 4) * ((h + 3) // 4) * 16
    if len(d) != want:
        raise SystemExit(f"{path}: {len(d)} bytes, a {w}x{h} BC7 level is {want}")
    return d, w, h


def join(levels):
    """levels: [(bytes, w, h)] -> one DDS with the mip count set."""
    base, w, h = levels[0]
    for i, (_, lw, lh) in enumerate(levels[1:], 1):
        want = (max(1, w >> i), max(1, h >> i))
        if (lw, lh) != want:
            raise SystemExit(f"level {i} is {lw}x{lh}, expected {want[0]}x{want[1]}")
    head = bytearray(base[:HEADER])
    flags = struct.unpack_from("<I", head, 8)[0] | DDSD_MIPMAPCOUNT
    caps = struct.unpack_from("<I", head, 108)[0] | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    struct.pack_into("<I", head, 8, flags)
    struct.pack_into("<I", head, 28, len(levels))
    struct.pack_into("<I", head, 108, caps)
    return bytes(head) + b"".join(d[HEADER:] for d, _, _ in levels)


if __name__ == "__main__":
    out, *paths = sys.argv[1:]
    if not paths:
        raise SystemExit(__doc__)
    open(out, "wb").write(join([read_level(p) for p in paths]))
