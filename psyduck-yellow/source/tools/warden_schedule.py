"""Prototype 0180: the Fuchsia Warden is at home only in the DAY and EVENING once he has his teeth back (owner spec 2026-11-04: "he appears in that house ... only during periods Day and Evening, repeating every day").
Before his GOLD TEETH are returned (flag 0xA6C clear) he is always at home, so the quest can be done at any hour. After that a map-entry script (level-script row type 2) on map 481 runs each time the house is entered:
it reads the time of day (script command 379: MORN 4-9, DAY 10-16, EVE 17-19, NITE 20-23, LATE 0-3) and clears or sets the Warden's hide flag 0xAAD (DAY or EVE: clear = he is there; otherwise set = he is out).
The flag is a daily-range flag (>= 0xAA0, cleared by the game at midnight): that is fine, it is recomputed at every entry, so it never has to persist. 0xAAD is unused (checked in every script bank and actor list); no variable is used.
The Warden's actor (the one with the highest script id, as fuchsia_warden_nugget.py picked it) gets 0xAAD as its hide flag. His daily NUGGET routine (flag 0xAAC) is unchanged.
SHOW is a test hook: the time-of-day values that count as "at home" (default (1, 2) = DAY, EVENING).
Usage (from yellow-heartgold, PYTHONPATH=tools): warden_schedule.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from opening import Script

MAP, WARDEN_GIVEN, HIDE = 481, 0xA6C, 0xAAD
SHOW = (1, 2)


def entry_script(show=SHOW):
    s = Script().emit(32, WARDEN_GIVEN).jump('timed', 1)
    s.label('home').emit(31, HIDE).emit(2)
    s.label('timed').emit(379, 0x800C)
    for t in show:
        s.compare(0x800C, t).jump('home', 1)
    s.emit(30, HIDE).emit(2)
    return s.finish()


def patch(rom, source=None, show=SHOW):
    edit = MapEdit(rom, MAP)
    assert struct.unpack_from('<4B', bytes(edit.scripts.files[struct.unpack_from('<H', edit.d, edit.at + 8)[0]]), 0) == (0, 0, 0, 0), 'map 481 already has level scripts'
    idx = edit.script(lambda add: entry_script(show))
    i = max(range(len(edit.groups[1])), key=lambda k: struct.unpack_from('<H', edit.groups[1][k], 10)[0])
    row = bytearray(edit.groups[1][i])
    assert struct.unpack_from('<H', row, 8)[0] == 0, 'the Warden already has a hide flag'
    struct.pack_into('<H', row, 8, HIDE)
    edit.groups[1][i] = bytes(row)
    edit.scripts.files.append(b'\x02' + struct.pack('<I', idx) + b'\0\0\0')          # level-script header: one row (type 2, script id), terminator, padding
    struct.pack_into('<H', edit.d, edit.at + 8, len(edit.scripts.files) - 1)
    edit.save()
    return dict(map=MAP, script=idx, actor=i, hide_flag=hex(HIDE), show=show)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
