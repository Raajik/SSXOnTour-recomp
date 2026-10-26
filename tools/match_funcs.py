"""Find functions of one XBE in another by their bytes, with addresses masked.

    python3 -I tools/match_funcs.py OLD.xbe OLD_functions.json NEW.xbe VA [VA ...]

For each VA (a function start in OLD), takes its bytes up to the end that
OLD_functions.json gives, and wildcards every rel32 branch and every 32-bit
immediate or displacement inside the image, so code that only moved still
matches. Prints each match in NEW's sections ("none" or several are worth a
look by hand). Used to carry SSX 3's library overrides to SSX On Tour: both
link the same XDK libraries.
"""
import json
import re
import struct
import sys

import capstone
from capstone import x86


def sections(xbe):
    base = struct.unpack_from("<I", xbe, 0x104)[0]
    n, at = struct.unpack_from("<II", xbe, 0x11C)
    out = []
    for i in range(n):
        _, va, vsize, raw, rsize, name_va = struct.unpack_from("<IIIIII", xbe, at - base + i * 56)
        o = name_va - base
        out.append((xbe[o:xbe.index(b"\0", o)].decode(), va, xbe[raw:raw + rsize]))
    return out


def in_image(v):
    return 0x10000 <= v < 0x00800000


def pattern(code, va):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    mask = bytearray(len(code))
    for ins in md.disasm(code, va):
        o = ins.address - va
        if ins.size >= 5 and (ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL)) \
                and ins.operands and ins.operands[0].type == x86.X86_OP_IMM:
            mask[o + ins.size - 4:o + ins.size] = b"\1" * 4
            continue
        for op in ins.operands:
            if op.type == x86.X86_OP_IMM and ins.imm_offset and ins.imm_size == 4 and in_image(op.imm & 0xFFFFFFFF):
                mask[o + ins.imm_offset:o + ins.imm_offset + 4] = b"\1" * 4
            if op.type == x86.X86_OP_MEM and ins.disp_offset and ins.disp_size == 4 \
                    and in_image(op.mem.disp & 0xFFFFFFFF):
                mask[o + ins.disp_offset:o + ins.disp_offset + 4] = b"\1" * 4
    return re.compile(b"".join(b"." if m else re.escape(bytes([c])) for c, m in zip(code, mask)), re.S)


def main():
    old = open(sys.argv[1], "rb").read()
    funcs = {int(f["start"], 16): int(f["end"], 16) for f in json.load(open(sys.argv[2]))}
    new = open(sys.argv[3], "rb").read()
    old_secs, new_secs = sections(old), sections(new)
    for arg in sys.argv[4:]:
        va = int(arg, 16)
        end = funcs.get(va)
        if end is None:
            print(f"{va:08X}: not a function start in {sys.argv[2]}")
            continue
        name, sva, data = next(s for s in old_secs if s[1] <= va < s[1] + len(s[2]))
        code = data[va - sva:end - sva]
        pat = pattern(code, va)
        hits = [f"{nsva + m.start():08X} ({nname})" for nname, nsva, ndata in new_secs
                for m in pat.finditer(ndata)]
        print(f"{va:08X} ({name}, {len(code)} bytes): {', '.join(hits) if hits else 'none'}")


if __name__ == "__main__":
    main()
