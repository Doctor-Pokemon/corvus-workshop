"""Hideout arrows and Lift Key doors (and other trigger rows) that never fire (owner report 2026-11-08, found with the owner's save).
Cause: about 120 trigger rows (the Rocket Hideout's spinner tiles and lift doors, and many rows on other floors) use the 'dummy' work variables 0x4178 and 0x4179 as their condition ("fire while the variable is 0").
The save only holds 368 work variables (0x4000-0x416F); these ids lie past the end and alias event flags (0x4178 = flags 0x80-0x8F, 0x4179 = flags 0x90-0x9F). Once ANY of those flags is set (the owner's save has 0x89, 0x9A and 0x9C set) the
variable is no longer 0 and every one of those triggers stops firing.
Fix: those rows get a literal 0 in the variable field instead (like the Saffron gatehouse guards): the condition becomes a constant that is always true, no variable and no flag involved. Only trigger rows whose variable is 0x4178/0x4179 AND whose other
condition fields are 0 are changed (asserted); every other byte of the ROM is untouched. Works on any build; the story-state variables 0x4171-0x4177 are NOT touched here.
Usage (from yellow-heartgold, PYTHONPATH=tools): trigger_dummy_var.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode

DUMMIES = (0x4178, 0x4179)
FMT = '<Hhh5H'          # script, x, z, w, h, then three condition words; the last is the variable


def patch(rom):
    events = ndspy.narc.NARC(rom.getFileByName('a/0/3/2'))
    changed = {}
    for i, raw in enumerate(events.files):
        if not raw:
            continue
        try:
            g = events_decode(raw)
        except Exception:
            continue
        hit = [k for k, t in enumerate(g[3]) if struct.unpack(FMT, t)[7] in DUMMIES]
        if not hit:
            continue
        assert events_encode(g) == bytes(raw), ('event file does not round-trip', i)
        for k in hit:
            row = list(struct.unpack(FMT, g[3][k]))
            assert row[5] == 0 and row[6] == 0, (i, k, row)
            row[7] = 0
            g[3][k] = struct.pack(FMT, *row)
        events.files[i] = events_encode(g)
        changed[i] = len(hit)
    assert changed, 'nothing to change'
    rom.setFileByName('a/0/3/2', events.save())
    return dict(event_files=len(changed), rows=sum(changed.values()))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
