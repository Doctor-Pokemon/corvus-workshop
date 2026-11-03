"""Prototype 0169: the Route 7 / Route 8 Underground Path doors are open and lead straight to each other (owner order 2026-11-03, option C: "a plain two-door shortcut").
Why: HeartGold's Route 7 and Route 8 buildings are the sealed Underground Path ("It won't open"); they have a door tile but no warp and no interior, and Saffron is closed by the thirsty guards, so nothing led from Lavender to Celadon (the drink, Erika, the Hideout and the Silph Scope are all in Celadon).
Now: each door tile (behaviour 0x8069, the same blocked door tile the native buildings use, e.g. Route 5's) gets a warp event pointing at the other route's landing tile; walking into the door takes the player through it and out of the other door, like a building entrance. The landing tile is the tile in front of the door, marked by a second, never-firing warp event (a plain tile does not fire warps; the first version landed the player ON the door tile and any sideways bump there fired the door's own warp: owner report 2026-11-03). No interior map is used (the extension header table is full), no land chunk is touched.
Route 8 (map 16) door (1354,237) <-> Route 7 (map 15) door (1261,247). The old "locked" door scripts and the notices stay in the maps but the doors now fire first.
Data files only (events a/0/3/2, changed in place).
Usage (from yellow-heartgold, PYTHONPATH=tools): route78_tunnel.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode
from viridian_tutorial import TABLE

ROUTE7, ROUTE8 = 15, 16
DOORS = {ROUTE8: (1354, 237), ROUTE7: (1261, 247)}
LANDING = {m: (x, z + 1) for m, (x, z) in DOORS.items()}      # the tile in front of the door


def patch(rom):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    eids = {m: struct.unpack_from('<H', d, TABLE + 24 * m + 16)[0] for m in DOORS}
    assert len(set(eids.values())) == 2, 'Routes 7 and 8 share an event file'
    shared = [m for m in range(540) if m not in DOORS and struct.unpack_from('<H', d, TABLE + 24 * m + 16)[0] in eids.values()]
    assert not shared, shared
    groups = {m: events_decode(events.files[eid]) for m, eid in eids.items()}
    door = {m: len(groups[m][2]) for m in DOORS}                    # the door warp's index in its own map; the landing warp follows it
    land = {m: door[m] + 1 for m in DOORS}
    other = {ROUTE7: ROUTE8, ROUTE8: ROUTE7}
    for m, (x, z) in DOORS.items():
        assert not any(struct.unpack_from('<2H', r, 0) == (x, z) for r in groups[m][2]), 'a warp already stands on the door'
        assert any(struct.unpack_from('<I2i', r, 0)[1:] == (x, z) for r in groups[m][0]), 'the old locked-door event is not on the door tile'
        groups[m][2].append(struct.pack('<4HI', x, z, other[m], land[other[m]], 0))
        groups[m][2].append(struct.pack('<4HI', *LANDING[m], other[m], door[other[m]], 0))      # arrival anchor only
    for m, eid in eids.items():
        events.files[eid] = events_encode(groups[m])
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    return dict(route8_door=(ROUTE8, door[ROUTE8], DOORS[ROUTE8]), route8_landing=(land[ROUTE8], LANDING[ROUTE8]), route7_door=(ROUTE7, door[ROUTE7], DOORS[ROUTE7]), route7_landing=(land[ROUTE7], LANDING[ROUTE7]))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
