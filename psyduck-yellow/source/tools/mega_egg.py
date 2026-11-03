"""The bedroom's Mega ON/OFF switch becomes a hidden Easter egg (owner 2026-11-03: "move the Mega Toggle flag item to the southeast corner of the player's room, still functional but not visible").
Map 506 (Red's bedroom, Pallet) had a visible object (actor script 6, sprite 400, the red banner at (8,5)) whose script toggles the Mega flag 0x9D6 with two messages. The object is removed and the same script (script 6 of the bank) is attached
to two invisible "sign" events (bg events) on the wall tiles beside the room's south-east corner floor tile (11,10): (12,10) east of it and (11,11) south of it. Stand in the corner and press toward the wall, then A: the old messages play and the flag toggles as before.
Usage (from yellow-heartgold, PYTHONPATH=tools): mega_egg.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode
from viridian_tutorial import TABLE

BEDROOM = 506
SWITCH_SCRIPT, SWITCH_SPRITE = 6, 400
EGG_TILES = ((12, 10), (11, 11))                      # wall tiles next to the south-east corner floor tile (11, 10)


def patch(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    at = TABLE + BEDROOM * 24 + 16
    groups = events_decode(events.files[struct.unpack_from('<H', d, at)[0]])
    switch = [row for row in groups[1] if struct.unpack_from('<HH', row)[1] == SWITCH_SPRITE and struct.unpack_from('<6H', row)[5] == SWITCH_SCRIPT]
    assert len(switch) == 1, 'expected exactly one Mega switch object in the bedroom'
    groups[1] = [row for row in groups[1] if row != switch[0]]
    template = groups[0][0]                            # an existing bg event: u32 script, x, z, height 0, 4 = any facing
    assert struct.unpack_from('<5I', template)[3:] == (0, 4), struct.unpack_from('<5I', template)
    groups[0] = list(groups[0]) + [struct.pack('<5I', SWITCH_SCRIPT, x, z, 0, 4) for x, z in EGG_TILES]
    events.files.append(events_encode(groups))
    struct.pack_into('<H', d, at, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(removed_object_at=struct.unpack_from('<2h', switch[0], 24), bg_events=len(groups[0]), egg_tiles=EGG_TILES)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
