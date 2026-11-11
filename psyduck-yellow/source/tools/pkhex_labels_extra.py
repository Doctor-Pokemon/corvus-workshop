"""Append labels for the Psyduck Yellow flags and variables that flags_py_en.txt / const_py_en.txt did not name yet (2026-11-03, phase A of the PKHeX label work).
Never touches an existing line (an id that already has an entry is skipped), so it can be re-run. Item-ball flags are labelled by area for now (phase B will name the item).
Usage (from yellow-heartgold): pkhex_labels_extra.py <PKHeX.Core/Resources/text/script/gen4 directory>"""
import sys

def rng(lo, hi): return list(range(lo, hi + 1))

AREA_ITEMS = {                                  # flag id -> (category, label)
    **{f: ('h', 'Pokémon Tower: Item ball') for f in (0xA1F, 0xA20, 0xA23, 0xA24, 0xA25, 0xA27, 0xA29)},
    **{f: ('h', 'Rocket Hideout: Item ball') for f in (0x9EF, 0x9F0, 0x9F1, 0x9F3, 0x9F5, 0x9F7, 0x9FC, 0x9FD, 0xA2B, 0xA2C)},
    **{f: ('h', 'Victory Road: Item ball') for f in (0xA2D, 0xA2F, 0xA30, 0xA31, 0xA35, 0xA37)},
    **{f: ('h', 'Silph Co.: Item ball') for f in (0xA38, 0xA39, 0xA3C, 0xA3D, 0xA3F, 0xA43, 0xA44, 0xA45, 0xA5B, 0xA5C, 0xA5F, 0xA61)},
    **{f: ('h', 'Safari Zone: Item ball') for f in (0x95A, 0x95B, 0x95D, 0x95E, 0x95F, 0x961, 0x962, 0x963, 0x965, 0x967)},
    **{f: ('h', 'Pokémon Mansion / Rocket Hideout: Item ball') for f in (0x954, 0x95C, 0x960, 0x968, 0x970, 0x974, 0x97C, 0x98C, 0x99C, 0x9A0)},
    **{f: ('h', 'Mt. Moon: Item ball') for f in (0xB2C, 0xB2D, 0xB2E, 0xB2F, 0xB30, 0xB31, 0xB32, 0xB35, 0xB38)},
    **{f: ('h', 'Viridian Forest: Item ball / event') for f in (0xB25, 0xB26, 0xB27, 0xB2A, 0xB2B)},
}
FLAGS = {
    **AREA_ITEMS,
    0x956: ('s', 'Victory Road: Barrier 1 open'), 0x957: ('s', 'Victory Road: Barrier 2 open'),
    0x958: ('s', 'Victory Road: Barrier 3 open'), 0x959: ('s', 'Victory Road: Barrier 4 open'),
    0x93D: ('s', 'Silph Co.: Event flag'), 0xA64: ('s', 'Silph Co.: Event flag (1)'), 0xA65: ('s', 'Silph Co.: Event flag (2)'), 0xA68: ('s', 'Silph Co.: Event flag (3)'),
    0x9BB: ('f', 'Fly point: New Bark Town unlocked'),
    0x9F9: ('h', 'Rocket Hideout: Lift Key taken'),
    0xA63: ('s', 'Route 22: Second rival battle done'),
    0xA6B: ('s', 'Johto: First S.S. Aqua arrival reached'),
    0xA6C: ('g', 'Fuchsia Warden: HM given'),
    0xA6D: ('s', 'Rocket Hideout: Event flag (1)'), 0xA71: ('s', 'Rocket Hideout: Event flag (2)'),
    0xA75: ('s', 'Pokémon Tower: Scene flag'),
    0xA7E: ('s', 'Pewter: Guide hidden (Boulder Badge owned)'),
    0xA8C: ('m', 'Bedroom PC: Initialised'), 0xB3B: ('m', 'Bedroom PC: Item taken'),
    0xA8D: ('s', 'Route 24: Nugget Bridge event'), 0xA94: ('s', 'Route 25: Bill event'),
}
WORK = {                                         # var id -> (category, label, value labels)
    0x4059: ('s', 'Silph Co.: State', ''),
    0x406D: ('s', 'Pokémon Mansion: State (1)', ''), 0x406E: ('s', 'Pokémon Mansion: State (2)', ''), 0x406F: ('s', 'Pokémon Mansion: State (3)', ''),
    0x4128: ('s', 'Johto postgame: Progress', '0:Not started,6:Elm has called (Johto unlocked),7:Mr. Pokémon met'),
    0x413C: ('s', 'Johto postgame: bonus Pokémon state', ''),
    0x4168: ('s', 'Oak escort: State', ''),
    }

def pid(s): return int(s, 16) if s.lower().startswith('0x') else int(s, 10)

def main(d):
    for name, table, fmt in (('flags_py_en.txt', FLAGS, lambda i, v: '0x%X\t%s\t%s' % (i, v[0], v[1])),
                              ('const_py_en.txt', WORK, lambda i, v: '0x%X\t%s\t%s%s' % (i, v[0], v[1], ('\t' + v[2]) if v[2] else ''))):
        path = d + '/' + name
        text = open(path, encoding='utf-8').read()
        have = {pid(l.split('\t')[0]) for l in text.split('\n') if '\t' in l and l.lower().startswith('0x')}
        add = [fmt(i, v) for i, v in sorted(table.items()) if i not in have]
        if add:
            open(path, 'w', encoding='utf-8', newline='').write(text.rstrip('\n') + '\n' + '\n'.join(add) + '\n')
        print(name, 'added', len(add), 'skipped', len(table) - len(add))

if __name__ == '__main__':
    main(sys.argv[1])
