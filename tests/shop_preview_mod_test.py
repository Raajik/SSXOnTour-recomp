"""tools/shop_preview_mod.py: archives round-trip, and with the game's files (game/) each shop screen is patched
in place, the same size, only in the handler, and a patched file is refused a second time."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import shop_preview_mod as m

fails = 0
def check(ok, what):
    global fails
    if not ok:
        print('FAIL', what); fails += 1

rnd = random.Random(1)
for n in (0, 1, 3, 4, 111, 112, 113, 5000):
    raw = bytes(rnd.randrange(256) for _ in range(n))
    check(m.refpack_unpack(m.refpack_pack(raw)) == raw, 'refpack round trip %d' % n)
ents = [('a.apt', b'x' * 300), ('a.const', b'yz')]
check(m.big_read(m.big_write(ents)) == ents, 'BIG round trip')
try:
    m.big_read(m.big_write(ents)[:300])
    check(False, 'a member past the end is refused')
except ValueError:
    pass

# A run that makes nothing leaves no mod behind, not the one made before (screens from other game files).
import shutil, subprocess, tempfile
tmp = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp, 'game', os.path.dirname(m.VIV)))
open(os.path.join(tmp, 'game', m.VIV), 'wb').write(m.big_write([('data/x.big', b'x')]))
stale = os.path.join(tmp, 'mods', 'shop-preview')
os.makedirs(stale)
open(os.path.join(stale, 'mod.txt'), 'w').write('old')
r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), '..', 'tools', 'shop_preview_mod.py'),
                    os.path.join(tmp, 'game'), os.path.join(tmp, 'mods')], capture_output=True)
check(r.returncode != 0, 'a run that makes nothing fails')
check(os.listdir(os.path.join(tmp, 'mods')) == [], 'a failed run leaves no mod (%s)' % os.listdir(os.path.join(tmp, 'mods')))
shutil.rmtree(tmp)

viv = os.path.join(os.path.dirname(__file__), '..', 'game', m.VIV)
if os.path.exists(viv):
    members = dict(m.big_read(open(viv, 'rb').read()))
    for shop in m.SHOPS:
        ents = dict(m.big_read(members['data/fe/screens/ssx/fe/shops/%s.big' % shop]))
        stem = shop
        names = m.const_names(m.refpack_unpack(ents[stem + '.const']))
        apt = m.refpack_unpack(ents[stem + '.apt'])
        new = m.patch_shop(apt, names)
        diff = [i for i in range(len(apt)) if apt[i] != new[i]]
        check(len(new) == len(apt), shop + ': same size')
        check(diff and diff[-1] - diff[0] < 1000, shop + ': changes stay in the handler (%s)' % (diff[:1] + diff[-1:]))
        try:
            m.patch_shop(new, names)
            check(False, shop + ': a patched file is refused')
        except ValueError:
            pass
        big = m.make_shop(members['data/fe/screens/ssx/fe/shops/%s.big' % shop])
        check(m.refpack_unpack(dict(m.big_read(big))[stem + '.apt']) == new, shop + ': the mod file holds the patch')
else:
    print('no game/%s: shop patch not checked' % m.VIV)

print('shop_preview_mod_test:', 'FAIL' if fails else 'ok')
sys.exit(1 if fails else 0)
