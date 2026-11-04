"""Prototype 0183: the Route 12 Snorlax is there from the start (owner report 2026-11-04: "I walked south, and then went west, straight to Fuchsia without a sleeping Snorlax in sight"; Yellow has a Snorlax on Route 12 woken with the Poke Flute).
Why it was missing: HeartGold hides the Route 12 Snorlax (map 20: actors 15-18, sprites 395 + 315) with flag 795, set at game start and cleared only by the Pokemon League's postgame script (map 306), unless flag 0xF9 is set. Flag 0xF9 is the Snorlax's own
"dealt with" flag: his battle script (script 6 of map 20) sets it after a win or a catch (not after a loss or a flee). The four actors' hide flag becomes 0xF9 instead of 795, so he is visible from the start of the game (existing saves too, as long as he has not been beaten) and
disappears for good once defeated or caught, exactly like his own scripts expect. snorlax.py already made him wake to the Poke Flute (item 651) and gave the Yellow blocked-road text without it.
He stays where HeartGold put him: the west end of the Route 12 side pier at (1411..1412, 305..306) where it meets Route 11, not on the main north-south pier (which is 3 tiles wide everywhere, wider than his 2x2 body, so he could not block it). The Route 11 Snorlax (map 19, flag 609) is untouched (still postgame).
The three visible body parts (actors 16-18) now run the Poke Flute script 7 too (found live 2026-11-04: talking to the body gave HeartGold's 'sleeping peacefully' text, never the flute test). No new flag or variable. Usage (from yellow-heartgold, PYTHONPATH=tools): snorlax_visible.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode
from viridian_tutorial import TABLE

MAP, OLD_FLAG, NEW_FLAG = 20, 795, 0xF9
NATIVE_SCRIPT, FLUTE_SCRIPT = 6, 7          # the body parts (sprite 315) still ran HeartGold's radio-tune script 6; snorlax.py's Poke Flute version (script 7) only sat on the hidden part 15, which no one can stand next to


def patch(rom, source=None):
    d = bytes(rom.loadArm9().sections[0].data)
    eid = struct.unpack_from('<H', d, TABLE + MAP * 24 + 16)[0]
    assert not [m for m in range(540) if m != MAP and struct.unpack_from('<H', d, TABLE + m * 24 + 16)[0] == eid], 'event file shared'
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    changed = []
    for i, a in enumerate(groups[1]):
        if struct.unpack_from('<H', a, 8)[0] == OLD_FLAG:
            row = bytearray(a)
            struct.pack_into('<H', row, 8, NEW_FLAG)
            groups[1][i] = bytes(row)
            if struct.unpack_from('<H', a, 10)[0] == NATIVE_SCRIPT:
                struct.pack_into('<H', row, 10, FLUTE_SCRIPT)
                groups[1][i] = bytes(row)
            changed.append((struct.unpack_from('<H', a, 0)[0], struct.unpack_from('<H', a, 2)[0]))
    assert sorted(changed) == [(15, 395), (16, 315), (17, 315), (18, 315)], changed
    events.files[eid] = events_encode(groups)
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    return dict(map=MAP, actors=changed, hide_flag=hex(NEW_FLAG))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
