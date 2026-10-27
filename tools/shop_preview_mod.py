#!/usr/bin/env python3
"""Make the "shop-preview" asset mod from your own copy of the game.

    tools/shop_preview_mod.py GAME_DIR MODS_DIR

With the mod on, highlighting an entry in a shop menu (Barber Shop > Hair Style: Mohawk, Caesar, ...) shows
that entry's first item on the rider, as A then does; nothing is bought or equipped, and B puts the old look
back. Off (not in the launcher's mod list), the game plays as shipped.

The shop screens are EA APT movies (Flash-like bytecode) in data/fe/screens/screens.viv. The game opens
`screens.viv|<member>` as a loose file before the archive, so the mod holds patched copies of the three shop
screens under that name. The patch rewrites the input handler's dead debug branch (extern.Debug + CIRCLE) and
its default call, in place and the same size: the APT loader relocates each code stream in order, and a jump
out of the handler never ran. Each file's bytes are checked first; a shop that does not match is left out.
"""
import os
import shutil
import struct
import sys

SHOPS = ('beauty_shop', 'clothing_shop', 'gear_shop')
VIV = 'data/fe/screens/screens.viv'


# --- archives -------------------------------------------------------------------------------------

def big_read(d):
    """BIGF archive -> [(name, bytes)]."""
    n = struct.unpack('>I', d[8:12])[0]
    p, out = 16, []
    for _ in range(n):
        off, size = struct.unpack('>II', d[p:p + 8])
        if off + size > len(d):
            raise ValueError('member past the end of the archive')
        p += 8
        e = d.index(b'\0', p)
        out.append((d[p:e].decode('latin1'), d[off:off + size]))
        p = e + 1
    return out


def big_write(ents):
    """[(name, bytes)] -> BIGF archive, entries 128-byte aligned like the game's."""
    hdr = 16 + sum(8 + len(nm) + 1 for nm, _ in ents)
    first = (hdr + 127) & ~127
    body, offs = bytearray(), []
    for _, data in ents:
        offs.append(first + len(body))
        body += data + b'\0' * (-len(data) % 128)
    h = bytearray(b'BIGF') + struct.pack('<I', first + len(body)) + struct.pack('>II', len(ents), hdr)
    for (nm, data), o in zip(ents, offs):
        h += struct.pack('>II', o, len(data)) + nm.encode('latin1') + b'\0'
    return bytes(h + b'\0' * (first - len(h)) + body)


def refpack_unpack(d):
    assert d[1] == 0xFB, 'not RefPack'
    p = 2 + (3 if d[0] & 0x01 else 0)
    n = 4 if d[0] & 0x80 else 3
    size = int.from_bytes(d[p:p + n], 'big')
    p += n
    out = bytearray()
    while p < len(d):
        b0 = d[p]
        if b0 < 0x80:
            b1 = d[p + 1]; p += 2
            lit = b0 & 3; ln = ((b0 >> 2) & 7) + 3; off = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1, b2 = d[p + 1], d[p + 2]; p += 3
            lit = b1 >> 6; ln = (b0 & 0x3F) + 4; off = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1, b2, b3 = d[p + 1], d[p + 2], d[p + 3]; p += 4
            lit = b0 & 3; ln = ((b0 & 0x0C) << 6) + b3 + 5; off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            lit = ((b0 & 0x1F) << 2) + 4; p += 1
            out += d[p:p + lit]; p += lit
            continue
        else:
            lit = b0 & 3; p += 1
            out += d[p:p + lit]
            break
        out += d[p:p + lit]; p += lit
        s = len(out) - off
        for i in range(ln):
            out.append(out[s + i])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def refpack_pack(raw):
    """RefPack with literal blocks only: what the game's decoder reads, without a compressor."""
    out = bytearray([0x10, 0xFB]) + len(raw).to_bytes(3, 'big')
    p = 0
    while len(raw) - p >= 4:
        n = min(112, (len(raw) - p) & ~3)
        out.append(0xE0 + n // 4 - 1)
        out += raw[p:p + n]
        p += n
    out.append(0xFC + len(raw) - p)
    out += raw[p:]
    return bytes(out)


# --- APT --------------------------------------------------------------------------------------------

def const_names(c):
    """Apt constant file -> names (None for non-strings: registers, numbers)."""
    n, start = struct.unpack('<II', c[0x18:0x20])
    names = []
    for i in range(n):
        t, v = struct.unpack('<II', c[start + 8 * i:start + 8 * i + 8])
        names.append(c[v:c.index(b'\0', v)].decode('latin1') if t == 1 else None)
    return names


def handler_pool(a, names):
    """The constant pool (ActionConstantPool, 0x88) that names the shop's handler calls."""
    for i in range(len(a) - 12):
        if a[i] != 0x88:
            continue
        j = (i + 4) & ~3
        cnt, ptr = struct.unpack('<II', a[j:j + 8])
        if not 0 < cnt < 256 or ptr % 4 or ptr + 4 * cnt > len(a):
            continue
        idx = struct.unpack('<%dI' % cnt, a[ptr:ptr + 4 * cnt])
        if max(idx) >= len(names):
            continue
        pool = [names[k] for k in idx]
        if 'handleDefaultInputs' in pool and 'BrowseItem' in pool and 'GetNumEntries' in pool:
            return pool
    raise ValueError('no handler constant pool')


def assemble(start, prog, k):
    """Two passes over (op, arg) tuples and 'label:' strings; jumps are relative to the next instruction."""
    labels = {}
    for _ in (0, 1):
        out, pc = bytearray(), start
        for ins in prog:
            if isinstance(ins, str):
                labels[ins[:-1]] = pc
                continue
            op, arg = ins
            if op in (0xAE, 0xAF, 0xA2, 0xB2):            # PushVar, GetMember, PushConst, CallMethodPop: pool index
                b = bytes([op, k(arg)])
            elif op == 'raw':
                b = bytes(arg)
            elif op in (0x99, 0x9D, 0x96):                # jump, if, push: arguments 4-byte aligned
                j = (pc + 4) & ~3
                if op == 0x96:
                    tail = struct.pack('<II', 1, arg)
                else:
                    tail = struct.pack('<i', (labels.get(arg, pc) if isinstance(arg, str) else arg) - (j + 4))
                b = bytes([op]) + b'\0' * (j - pc - 1) + tail
            out += b
            pc += len(b)
    return bytes(out)


def push_before(a, i):
    """Start of the one-value push (0x96, padding to 4, count 1, pointer) that ends right at i."""
    for n in range(9, 13):
        p = i - n
        if a[p] == 0x96 and ((p + 4) & ~3) + 8 == i and struct.unpack('<I', a[i - 8:i - 4])[0] == 1:
            return p
    return None


def patch_shop(a, names):
    """Patched APT bytecode, or raise ValueError when the handler is not the one this was written for."""
    pool = handler_pool(a, names)
    k = pool.index
    a = bytearray(a)
    # The dead debug branch: if (extern.Debug == "1" && input == CIRCLE) load the CAC debug popup; then the
    # default, gFM.handleDefaultInputs(input), and the handler's end.
    dbg = bytes([0xAF, k('extern'), 0xAF, k('Debug'), 0xA2, k('1'), 0x49, 0x4C, 0x12, 0x9D])
    dflt = bytes([0x5A, 0xAE, k('gFM'), 0xB2, k('handleDefaultInputs')])
    i = a.find(dbg)
    if i < 0 or a.find(dbg, i + 1) >= 0:
        raise ValueError('debug branch not found once')
    start = push_before(a, i)                            # the branch starts with a push
    end = a.find(dflt, i)
    if start is None or end < 0 or end - i > 80:
        raise ValueError('handler layout differs')
    reg_push = push_before(a, end)                       # the default's push of the input register
    if reg_push is None:
        raise ValueError('default call differs')
    end += len(dflt)
    input_ptr = struct.unpack('<I', a[((reg_push + 4) & ~3) + 4:((reg_push + 4) & ~3) + 8])[0]

    H = [(0xAE, 'shop'), (0xAF, 'mScreen'), (0xAF, 'mInterface'), (0xAF, 'mItemGroup'), (0xAF, 'mHolder')]
    G = [('raw', [0x71]), (0xAF, 'FEShops')]           # _global.FEShops
    prog = [
        # mThisClass and its mType (item list 1, menu 0) wait under the shipped default call
        (0xAE, 'shop'), (0xAF, 'mThisClass'), ('raw', [0x4C]), (0xAF, 'mType'),
        (0x96, input_ptr), ('raw', [0x5A]), (0xAE, 'gFM'), (0xB2, 'handleDefaultInputs'),
        (0x9D, 'done'),                                  # an item list: as shipped
        # child = mEntries[mHolder.getSelectedIndex()]; an item screen when GetNumEntries(child).type is 1
        (0xAF, 'mEntries'), ('raw', [0x59]), *H, (0xA2, 'getSelectedIndex'), ('raw', [0x52, 0x4E]),
        ('raw', [0x4C, 0x5A]), *G, (0xA2, 'GetNumEntries'), ('raw', [0x52]), (0xAF, 'type'), ('raw', [0x12]),
        (0x9D, 'done'),
        # FEShops.BrowseItem(0, GetEntries(child).link): its first item, as A shows on entering it
        ('raw', [0x5A]), *G, (0xA2, 'GetEntries'), ('raw', [0x52]), (0xAF, 'link'),
        ('raw', [0x59, 0xB5, 2]), *G, (0xB2, 'BrowseItem'),
        (0x99, end),
        'done:', ('raw', [0x17]),
    ]
    code = assemble(start, prog, k)
    if len(code) > end - start:
        raise ValueError('patch is %d bytes, room for %d' % (len(code), end - start))
    # Left-over room: push 0, pop, after the last pop (stack-neutral; the loader walks every byte).
    room = end - start - len(code)
    if room % 2:
        raise ValueError('patch leaves an odd byte')
    a[start:end] = code + bytes([0x59, 0x17]) * (room // 2)

    # B leaving a menu clears the preview cache too (the shipped game does it only for item lists):
    # "mType == kItems" becomes "mType == mType".
    b = bytes([0xAE, k('shop'), 0xAF, k('mThisClass'), 0xAF, k('mType'),
               0xAE, k('shop'), 0xAF, k('mThisClass'), 0xAF, k('kItems'), 0x49, 0x12, 0x9D])
    j = a.find(b)
    if j < 0 or a.find(b, j + 1) >= 0 or a.find(bytes([0xB2, k('CachePolicy')]), j, j + 48) < 0:
        raise ValueError('B branch not found once')
    a[j + 11] = k('mType')
    return bytes(a)


def make_shop(big):
    ents = big_read(big)
    files = dict(ents)
    stem = next(nm[:-4] for nm, _ in ents if nm.endswith('.apt'))
    names = const_names(refpack_unpack(files[stem + '.const']))
    apt = patch_shop(refpack_unpack(files[stem + '.apt']), names)
    return big_write([(nm, refpack_pack(apt) if nm == stem + '.apt' else data) for nm, data in ents])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    game, mods = sys.argv[1:]
    out = os.path.join(mods, 'shop-preview')
    # Made fresh next to the old one and swapped in whole; on any failure no mod is left (a stale one would serve
    # screens made from other game files).
    new, old = out + '.new', out + '.old'
    for d in (new, old):
        shutil.rmtree(d, ignore_errors=True)
    try:
        viv = dict(big_read(open(os.path.join(game, VIV), 'rb').read()))
        made = 0
        for shop in SHOPS:
            member = 'data/fe/screens/ssx/fe/shops/%s.big' % shop
            try:
                data = make_shop(viv[member])
            except (KeyError, ValueError, AssertionError, IndexError, StopIteration) as e:
                print('%s: left out (%r)' % (shop, e))
                continue
            path = os.path.join(new, VIV + '|' + member)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
            print('%s: patched' % shop)
            made += 1
        if not made:
            raise ValueError('no shop screen matched')
        with open(os.path.join(new, 'mod.txt'), 'w') as f:
            f.write('Shop preview on highlight\n'
                    'Highlighting a shop menu entry shows its first item on the rider. Made from your game files.\n')
    except BaseException as e:
        shutil.rmtree(new, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)
        sys.exit('shop-preview not made, and any old one removed: %r' % e)
    if os.path.exists(out):
        os.rename(out, old)
    os.rename(new, out)
    shutil.rmtree(old, ignore_errors=True)
    print('wrote %s; turn it on in the launcher\'s Asset mods list' % out)


if __name__ == '__main__':
    main()
