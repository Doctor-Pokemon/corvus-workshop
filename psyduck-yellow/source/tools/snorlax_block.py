"""Prototype 0193: the Route 12 Snorlax really blocks the path (owner 2026-11-08: "Snorlax isn't actually blocking the path by the eastern piers ... move the Snorlax probably one or two tiles east to block the path. I checked in-game.").
Measured (emulator walk tests): the walkway east of the Snorlax's room is THREE tiles tall (rows 304..306 for x = 1414..1417, walls above at row 303 and below at row 307) and leads to the eastern pier; his 2x2 body (actors 15-18 at (1411..1412,305..306)) always left a free row, so the player walked around him.
Fix: his four actors move two tiles east to (1413..1414,305..306), where the room's last column meets the walkway, and two more invisible body parts (copies of actor 16: sprite 315, hide flag 0xF9, Poke Flute script 7) stand on (1413,304) and (1414,304), so all three walkway rows are closed.
The extra parts behave exactly like the existing invisible parts 16-18 (same flag, same script). No new flag or variable. Usage (from yellow-heartgold, PYTHONPATH=tools): snorlax_block.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit

MAP, PARTS, SHIFT = 20, (15, 16, 17, 18), 2
EXTRA = ((1413, 304), (1414, 304))
TEMPLATE = 16


def patch(rom, source=None):
    edit = MapEdit(rom, MAP)
    taken = {struct.unpack_from('<H', a, 0)[0] for a in edit.groups[1]}
    moved = []
    for i, a in enumerate(edit.groups[1]):
        if struct.unpack_from('<H', a, 0)[0] in PARTS:
            b = bytearray(a)
            x, z = struct.unpack_from('<2H', b, 24)
            assert 1411 <= x <= 1412 and 305 <= z <= 306, (x, z)
            struct.pack_into('<H', b, 24, x + SHIFT)
            edit.groups[1][i] = bytes(b)
            moved.append(i)
    assert len(moved) == 4
    tpl = next(a for a in edit.groups[1] if struct.unpack_from('<H', a, 0)[0] == TEMPLATE)
    assert struct.unpack_from('<2H', tpl, 2)[0] == 315 and struct.unpack_from('<H', tpl, 8)[0] == 0xF9
    occupied = {struct.unpack_from('<2H', a, 24) for a in edit.groups[1]}
    ids = []
    for k, (x, z) in enumerate(EXTRA):
        assert (x, z) not in occupied, 'tile occupied'
        b = bytearray(tpl)
        struct.pack_into('<H', b, 0, max(taken) + 1 + k)
        struct.pack_into('<2H', b, 24, x, z)
        edit.groups[1].append(bytes(b))
        ids.append(max(taken) + 1 + k)
    edit.save()
    return dict(map=MAP, moved=moved, extra_actors=ids)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
