"""READ-ONLY AUDIT (2026-11-12): every native map (0-539) with scenes that fire by themselves (level-script rows, frame rows, trigger rows) and whether the scene moves the player (ApplyMovement on object 255) or warps.
Usage (from yellow-heartgold): PYTHONPATH=tools python scene_scan.py <rom> <pret script.inc> <out.json>   (needs pret/pokeheartgold asm/macros/script.inc)"""
import sys, json, struct, collections
sys.path.insert(0,'tools')
import ndspy.rom, ndspy.narc, hg_dis
from viridian_tutorial import TABLE
from opening import events_decode
import johto_step3d as j
rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
d = bytes(rom.loadArm9().sections[0].data)
table = hg_dis.load_table(sys.argv[2])
scripts = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/1/2')).files]
events = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/3/2')).files]
MOVE = {'ApplyMovement','ApplyMovementWithOverride'}
WARP = {'Warp','WarpToMap','WarpToWorldMap','FlyWarp','SetWarp'}
def summarize(bank, starts, n):
    try: ins = hg_dis.dis(bank, starts, table, n)
    except Exception as ex: return None
    mv = any(nm.startswith('ApplyMovement') and a and a[0] == 255 for _, nm, a in ins)
    wp = [nm for _, nm, a in ins if nm.startswith('Warp') or nm in WARP]
    ch = [nm for _, nm, a in ins if 'Battle' in nm]
    return dict(player_moves=mv, warps=sorted(set(wp)), battles=len(ch), n=len(ins))
out = []
for mid in range(540):
    at = TABLE + 24 * mid
    sid, hid, eid = struct.unpack_from('<H', d, at + 6)[0], struct.unpack_from('<H', d, at + 8)[0], struct.unpack_from('<H', d, at + 16)[0]
    if sid >= len(scripts) or hid >= len(scripts): continue
    bank = scripts[sid]; h = scripts[hid]
    try: starts = j.starts(bank)
    except StopIteration: continue
    i = 0; rows = []
    while i + 5 <= len(h) and h[i] != 0:
        rows.append((h[i], struct.unpack_from('<H', h, i + 1)[0])); i += 5
    i += 1
    frames = []
    while i + 6 <= len(h) and struct.unpack_from('<H', h, i)[0] != 0:
        frames.append(struct.unpack_from('<3H', h, i)); i += 6
    for t, s in rows:
        if 1 <= s <= len(starts): out.append(dict(map=mid, kind='lvl%d' % t, script=s, **(summarize(bank, starts, s) or {})))
    for v, val, s in frames:
        if 1 <= s <= len(starts): out.append(dict(map=mid, kind='frame', var=hex(v), val=val, script=s, **(summarize(bank, starts, s) or {})))
    try: groups = events_decode(events[eid])
    except Exception: groups = []
    if groups:
        for r in groups[0]:
            w = struct.unpack_from('<%dH' % (len(r) // 2), r, 0)
            if len(w) >= 6 and 0 < w[0] < 8000 and w[0] <= len(starts):
                out.append(dict(map=mid, kind='trigger', var=hex(w[4]) if False else None, raw=list(w), script=w[0], **(summarize(bank, starts, w[0]) or {})))
json.dump(out, open(sys.argv[3], 'w'))
c = collections.Counter((o['kind'][:3], o.get('player_moves')) for o in out)
print(len(out), dict(c))
