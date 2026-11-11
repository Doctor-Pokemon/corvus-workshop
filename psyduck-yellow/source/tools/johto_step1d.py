"""Prototype 0213: the way back to Kanto stays shut until the Johto opening is done, and the first arrival at Olivine's pier lands SOUTH of the sailor (owner notes 1 and 2, 2026-11-09).
Milestone = HeartGold's own lab story variable 0x4108 >= 4 (the police / stolen-starter scene in Elm's lab has run; after the starter 0x4108 is 1-2, after Mr. Pokemon 3, after that scene 4 and higher).
 - Arrival: the Vermilion hall sailor's first crossing (johto_step1b.py) warped to map 330 at (27,21), between the pier sailor (27,22) and the ship. It now warps to (27,23), south of him.
 - Olivine pier sailor (map 330, native script 1): a wrapper script: milestone not reached -> "not in service" line; reached -> the native script, unchanged.
 - Vermilion hall sailor (map 386): after the first arrival (ARRIVED) the same wrapper in front of johto_step1b's script; a player who has not arrived yet crosses as before.
 - Route 22 gate (map 299, script 9, the south arm check of johto_step1c.py) and the Saffron Magnet Train attendant (map 400): their "has arrived" test becomes the milestone test (gate: the 11-byte flag test is replaced by a jump to a small block that compares the variable).
Nothing is added to the save; no frame rows.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step1d.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from johto_step3d import install, write_scripts
from johto_step3e import A

PIER, HALL, GATE, STATION = 330, 386, 299, 400
STORY, ARRIVED = 0x4108, 0xA6B
GT_3 = 2                                              # GoToIf condition: greater than; with 3 this means "variable >= 4"
FACE, LOCK, RELEASE = 104, 96, 97
OLD_WARP = struct.pack('<6H', 176, PIER, 0, 27, 21, 1)
NEW_WARP = struct.pack('<6H', 176, PIER, 0, 27, 23, 1)


def closed(a, msg):
    a.raw(struct.pack('<H', LOCK)).raw(struct.pack('<H', FACE))
    a.msg(msg)
    a.raw(struct.pack('<H', RELEASE)).end()
    return a


def wrapper_build(base, native, msg, need_arrived=False):
    a = A()
    if need_arrived:
        a.check_flag(ARRIVED).jump('gate', 1).jump(('abs', native))
        a.label('gate')
    a.compare(STORY, 3).jump(('abs', native), GT_3)
    closed(a, msg)
    return a.build(base)


def wrap_actor(e, group_row, text, need_arrived=False):
    """Appends a wrapper in front of the script the actor now runs; returns the wrapper's id."""
    row = bytearray(e.groups[1][group_row])
    native_id = struct.unpack_from('<H', row, 10)[0]
    msg = e.message(text)
    size = len(wrapper_build(0, 0, msg, need_arrived))
    ids, addrs, starts = install(e, [size])
    code = wrapper_build(addrs[0], starts[native_id - 1], msg, need_arrived)
    assert len(code) == size
    write_scripts(e, addrs, [code])
    struct.pack_into('<H', row, 10, ids[0])
    e.groups[1][group_row] = bytes(row)
    return ids[0]


def patch(rom):
    report = {}
    # 1. arrival tile (the warp sits in the hall sailor's first-crossing script, bank 154 / map 386)
    e = MapEdit(rom, HALL)
    n = e.bank.count(OLD_WARP)
    assert n == 1, ('first-crossing warp found %d times' % n)
    e.bank = e.bank.replace(OLD_WARP, NEW_WARP)
    report['hall_wrapper'] = wrap_actor(e, 0, 'The S.S. AQUA is not in service right now.', need_arrived=True)
    e.save()
    # 2. the pier sailor
    e = MapEdit(rom, PIER)
    report['pier_wrapper'] = wrap_actor(e, 0, 'The S.S. AQUA is not in service right now.')
    e.save()
    # 3. Magnet Train attendant (his script already has the ARRIVED prelude from johto_step1c.py; the wrapper adds the milestone in front)
    e = MapEdit(rom, STATION)
    report['station_wrapper'] = wrap_actor(e, 0, 'The MAGNET TRAIN is not running right now.')
    e.save()
    # 4. the gate's south arm: replace "CheckFlag ARRIVED; GoToIf EQ open" (4 + 7 bytes) by a jump to a variable test
    e = MapEdit(rom, GATE)
    pat = struct.pack('<2H', 32, ARRIVED) + struct.pack('<HB', 28, 1)
    assert e.bank.count(pat) == 1, 'the gate check was not found exactly once'
    probe = A().compare(STORY, 3).jump(('abs', 0), GT_3).jump(('abs', 0))
    size = len(probe.build(0))
    ids, addrs, starts = install(e, [size])
    at = e.bank.find(pat)
    open_to = at + 11 + struct.unpack_from('<i', e.bank, at + 7)[0]
    closed_to = at + 11
    code = A().compare(STORY, 3).jump(('abs', open_to), GT_3).jump(('abs', closed_to)).build(addrs[0])
    assert len(code) == size
    write_scripts(e, addrs, [code])
    bank = bytearray(e.bank)
    bank[at:at + 6] = struct.pack('<Hi', 22, addrs[0] - (at + 6))
    e.bank = bytes(bank)
    e.save()
    report['gate_block'] = ids[0]
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
