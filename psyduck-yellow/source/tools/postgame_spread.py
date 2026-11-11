"""Prototype 0224: the rule-based National Dex spread (owner 2026-11-10, plan item 30, owner rules: regional species on their region's routes, Gen 3-9 spread by type/habitat, Legendaries/Mythicals/Ultra Beasts/Paradox kept for postgame events, rule-based not hand-picked).
Works on the POSTGAME copies of the wild tables (members 256 + bank, see postgame_encounters.py): after the first Hall of Fame every map reads its postgame copy, so Johto (postgame only) and Kanto share one merged pool.
STEPS
 1. Obtainable now (C): species in any wild table a map uses, the known gifts (starters, Eevee, fossils, ...), and every species reachable from those by LEVEL / HAPPINESS evolution (methods 1-4, 8-12). Item/trade/other evolutions do NOT count: those targets are placed too.
 2. Event species (not placed, postgame events later): Legendaries, Mythicals, Ultra Beasts, Paradox, Ruinous, box legendaries (explicit dex ranges below). Alternate forms (species ids >= 1076) are not handled yet.
 3. Placement set: every remaining species with no reliable pre-evolution. Each goes to PLACES tables, by type affinity with the table's native species, region (Gen 1 -> Kanto tables first, Gen 2 -> Johto tables first), the water/land habitat (any Water type -> surf/rods), time of day (Ghost/Dark -> night only), a level floor from base stat total, and a load limit.
 4. Guest slots only: land slots 5-11 (the 10% and rarer slots) of each period; surf/rod slots 2-4. The common slots (the first five land slots, surf/rod slots 0-1) keep their native species. Guest species take the slot's own level.
Report: a JSON file of species -> [(bank, kind, period or rod, slot)]; land periods: 'dn' = all three lists, 'n' = night only, and the leftovers that did not fit.
Usage (from yellow-heartgold, PYTHONPATH=tools): postgame_spread.py <in.nds> <out.nds> <report.json>"""
import collections
import json
import struct
import sys
import ndspy.narc
import ndspy.rom
import map_header_extension as ext
from postgame_names import species_name
from prototype import decode_messages

POSTGAME, PLACES = 256, 2
RELIABLE = {1, 2, 3, 4, 8, 9, 10, 11, 12}
GIVEN = 'BULBASAUR CHARMANDER SQUIRTLE CHIKORITA CYNDAQUIL TOTODILE EEVEE PSYDUCK HITMONLEE HITMONCHAN SNORLAX OMANYTE KABUTO AERODACTYL LAPRAS PORYGON TOGEPI TENTACOOL'.split()
WATER, GHOST, DARK = 11, 7, 17
GUEST_LAND, GUEST_WATER = range(5, 12), range(2, 5)
MAP_TABLE = 0x020F6BE0


def rng(a, b):
    return set(range(a, b + 1))


EVENT = (rng(144, 146) | {150, 151} | {243, 244, 245, 249, 250, 251} | rng(377, 386) | rng(480, 494) | rng(638, 649) | rng(716, 721) | rng(772, 773) | rng(785, 809)
         | rng(888, 898) | rng(984, 1025))
FLOORS = ((320, 1), (400, 12), (450, 20), (500, 28), (550, 36), (10000, 44))


def dexnum(s):
    return s if s <= 493 else (s - 50 if 544 <= s <= 1075 else None)


def species_of(f):
    out = set()
    if f[0]:
        out |= {struct.unpack_from('<H', f, 20 + 2 * k)[0] & 0x7FF for k in range(36)}
    for rate, at, n in ((f[1], 100, 5), (f[2], 120, 2), (f[3], 128, 5), (f[4], 148, 5), (f[5], 168, 5)):
        if rate:
            out |= {struct.unpack_from('<H', f, at + 4 * k + 2)[0] & 0x7FF for k in range(n)}
    out.discard(0)
    return out


def load(rom):
    texts = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
    _, rows = decode_messages(texts.files[237])
    d = {}
    d['name'] = {i: species_name(r) for i, r in enumerate(rows)}
    d['pers'] = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/0/2')).files]
    d['evo'] = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/3/4')).files]
    d['files'] = [bytes(f) for f in ndspy.narc.NARC(rom.getFileByName('a/0/3/7')).files]
    arm9 = bytes(rom.loadArm9().sections[0].data)
    t = MAP_TABLE - 0x02000000
    used = {arm9[t + 24 * m] for m in range(540)} | {r[0] for r in ext.records(rom)}
    used.discard(255)
    d['used'] = sorted(used)
    return d


def analyse(d):
    dex = [s for s in range(1, 1076) if dexnum(s)]
    base = set()
    for b in d['used']:
        base |= species_of(d['files'][b])
    succ, pre = collections.defaultdict(list), collections.defaultdict(list)
    for s in range(1, 1076):
        for k in range(9):
            m, p, t = struct.unpack_from('<3H', d['evo'][s], 6 * k)
            if m and t and (t & 0x7FF) < 1076:
                succ[s].append((m, t & 0x7FF))
                pre[t & 0x7FF].append((m, s))
    by_name = {}
    for s in dex:
        by_name.setdefault(d['name'][s], s)
    c = set(base) | {by_name[n] for n in GIVEN if n in by_name}
    stack = list(c)
    while stack:
        s = stack.pop()
        for m, t in succ[s]:
            if m in RELIABLE and t not in c:
                c.add(t)
                stack.append(t)
    event = {s for s in dex if dexnum(s) in EVENT}
    need = {s for s in dex if s not in c and s not in event}
    place = [s for s in sorted(need) if not any(m in RELIABLE and p in (need | c) for m, p in pre[s])]
    return dict(dex=dex, base=base, obtainable=c, event=event, need=need, place=place)


def types(d, s):
    return {d['pers'][s][6], d['pers'][s][7]}


def floor_level(d, s):
    bst = sum(d['pers'][s][:6])
    return next(level for cap, level in FLOORS if bst <= cap)


def tables(d):
    """One record per used bank: guest slots per kind and the native type histogram."""
    out = {}
    for b in d['used']:
        f = d['files'][b]
        hist = collections.Counter()
        for sp in species_of(f):
            for t in types(d, sp):
                hist[t] += 1
        land = [(part, k, f[8 + k]) for part in ('d', 'n') for k in GUEST_LAND] if f[0] else []    # 'd' = morning + day lists, 'n' = night list
        water = []
        for kind, rate, at in (('surf', f[1], 100), ('old', f[3], 128), ('good', f[4], 148), ('super', f[5], 168)):
            if rate:
                water += [(kind, k, f[at + 4 * k + 1]) for k in GUEST_WATER]
        out[b] = dict(hist=hist, land=land, water=water, kanto=b >= 142, natives=species_of(f))
    return out


def spread(d, a):
    tabs = tables(d)
    free = {b: {'land': list(t['land']), 'water': list(t['water'])} for b, t in tabs.items()}
    placed = collections.defaultdict(list)
    leftovers = []
    count = collections.Counter()
    for s in sorted(a['place'], key=lambda x: (-floor_level(d, x), x)):
        ty = types(d, s)
        water = WATER in ty
        night = bool(ty & {GHOST, DARK}) and not water
        home_kanto = dexnum(s) <= 151
        home_johto = 152 <= dexnum(s) <= 251
        want = floor_level(d, s)
        for n in range(PLACES):
            best = None
            for need_level in [level for _, level in FLOORS if level <= want][::-1]:    # the species' level floor first, then lower tiers until a slot is found
                best = best_slot(d, s, tabs, free, placed, count, ty, water, night, home_kanto, home_johto, n, need_level)
                if best:
                    break
            if best is None:
                break
            _, b, unit = best
            pool = free[b]['water' if water else 'land']
            pool.remove(unit)
            if not water and not night:
                pool.remove(('n', unit[1], unit[2]))
            count[b] += 1
            placed[s].append((b, 'water', unit[0], unit[1]) if water else (b, 'land', 'n' if night else 'dn', unit[1]))
        if not placed[s]:
            leftovers.append(s)
    return placed, leftovers


def best_slot(d, s, tabs, free, placed, count, ty, water, night, home_kanto, home_johto, n, need_level):
    """The best table (type affinity, home region for the first copy, fewest guests so far) with a free slot at or above need_level; (score, bank, unit) or None."""
    best = None
    for b, t in tabs.items():
        pool = free[b]['water' if water else 'land']
        if not pool or s in t['natives'] or any(p[0] == b for p in placed[s]):
            continue
        if water:
            choices = [u for u in pool if u[2] >= need_level]
        elif night:
            choices = [u for u in pool if u[2] >= need_level and u[0] == 'n']
        else:                                   # a day species needs the same slot free in both the day and the night list
            choices = [u for u in pool if u[0] == 'd' and u[2] >= need_level and ('n', u[1], u[2]) in pool]
        if not choices:
            continue
        affinity = sum(t['hist'][x] for x in ty)
        home = (home_kanto and t['kanto']) or (home_johto and not t['kanto'])
        score = affinity * 2 + (30 if home and n == 0 else 0) - count[b]
        if best is None or score > best[0]:
            best = (score, b, max(choices, key=lambda u: u[2]))
    return best


def write(d, placed):
    files = {b: bytearray(d['files'][b]) for b in d['used']}
    for s, places in placed.items():
        for p in places:
            b, kind = p[0], p[1]
            f = files[b]
            if kind == 'land':
                for period in ((2,) if p[2] == 'n' else (0, 1, 2)):
                    struct.pack_into('<H', f, 20 + 24 * period + 2 * p[3], s)
            else:
                at = {'surf': 100, 'old': 128, 'good': 148, 'super': 168}[p[2]]
                struct.pack_into('<H', f, at + 4 * p[3] + 2, s)
    return files


def patch(rom, report_path=None):
    d = load(rom)
    a = analyse(d)
    placed, left = spread(d, a)
    narc = ndspy.narc.NARC(rom.getFileByName('a/0/3/7'))
    files = write(d, placed)
    members = [bytes(f) for f in narc.files]
    for b, f in files.items():
        members[POSTGAME + b] = bytes(f)
    narc.files = members
    rom.setFileByName('a/0/3/7', narc.save())
    check = set()
    for b in d['used']:
        check |= species_of(members[POSTGAME + b])
    summary = dict(to_place=len(a['place']), placed=len(placed), leftovers=[d['name'][s] for s in left], event=len(a['event']), obtainable_before=len(a['obtainable']), species_in_postgame_tables=len(check))
    if report_path:
        json.dump(dict(summary=summary, placed={d['name'][s]: v for s, v in placed.items()}, event=sorted(d['name'][s] for s in a['event'])), open(report_path, 'w'), indent=1)
    return summary


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
