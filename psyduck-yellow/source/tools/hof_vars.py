"""READ-ONLY AUDIT (2026-11-12): which story variables do the Champion room, Hall of Fame room, Indigo lobby and E4 scripts SET, and which frame rows elsewhere react to those values (the coupling that fired the Olivine Oak scene).
Usage (from yellow-heartgold): PYTHONPATH=tools python hof_vars.py <pret script.inc> <scenes.json from scene_scan.py>   (the ROM path inside is build/0263-aqua-oak/s.nds)"""
import sys, json, struct, collections
sys.path.insert(0,'tools')
import ndspy.rom, ndspy.narc, hg_dis
from viridian_tutorial import TABLE
import johto_step3d as j
rom = ndspy.rom.NintendoDSRom.fromFile('build/0263-aqua-oak/s.nds')
d = bytes(rom.loadArm9().sections[0].data)
table = hg_dis.load_table(sys.argv[1])
scripts = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/1/2')).files]
setv = collections.defaultdict(set)
for mid in (298,299,300,301,302,303,304,305,306,439,440,441,442,443,444,445,446,447):
    sid = struct.unpack_from('<H', d, TABLE + 24 * mid + 6)[0]
    bank = scripts[sid]
    try: st = j.starts(bank)
    except StopIteration: continue
    for n in range(1, len(st) + 1):
        try: ins = hg_dis.dis(bank, st, table, n)
        except Exception: continue
        for at, nm, a in ins:
            if nm in ('SetVar',) and a and 0x4000 <= a[0] < 0x4200: setv[a[0]].add((a[1], mid, n))
for v in sorted(setv): print(hex(v), sorted(setv[v])[:6])
sc = json.load(open(sys.argv[2]))
print('--- frame rows elsewhere that match a value set above')
for r in sc:
    if r['kind'] == 'frame':
        v = int(r['var'], 16)
        if v in setv and any(val == r['val'] for val, _, _ in setv[v]):
            print('  MATCH map', r['map'], r['var'], '==', r['val'], 'script', r['script'], 'moves player' if r.get('player_moves') else '', r.get('warps'))
