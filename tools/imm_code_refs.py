"""List code addresses a title stores as immediates that the function list lacks.

    python3 -I tools/imm_code_refs.py XBE FUNCTIONS_JSON [LO HI]

A callback registered in code (`mov [reg+n], offset fn`, `push offset fn`)
is reached only through a pointer, and the disassembler's data-table pass
never sees it. Prints each target in [LO, HI) (default: .text) that is not
a function start, with the instructions that mention it. Candidates still
need a look: an immediate can be a constant that happens to fall in .text.
"""
import json
import struct
import sys

import capstone
from capstone import x86


def main():
    d = open(sys.argv[1], "rb").read()
    starts = {int(f["start"], 16) for f in json.load(open(sys.argv[2]))}
    base = struct.unpack_from("<I", d, 0x104)[0]
    n, at = struct.unpack_from("<II", d, 0x11C)
    _, va, vsize, raw, rsize, _ = struct.unpack_from("<IIIIII", d, at - base)
    lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else va
    hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else va + rsize
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    md.skipdata = True
    refs = {}
    for ins in md.disasm(d[raw:raw + rsize], va):
        if ins.id == 0 or ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL):
            continue
        for op in ins.operands:
            if op.type == x86.X86_OP_IMM:
                v = op.imm & 0xFFFFFFFF
                if lo <= v < hi and v not in starts:
                    refs.setdefault(v, []).append(ins.address)
    for v in sorted(refs):
        print(f"{v:08X} from {' '.join(f'{a:08X}' for a in refs[v][:3])}")


if __name__ == "__main__":
    main()
