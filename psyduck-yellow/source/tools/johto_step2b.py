"""Prototype 0213 (second part): the border map 31 no longer lowers the map level or plays the stale "first step into Kanto" scene (owner notes 2 and 4, 2026-11-09).
Map 31 (script bank 221, level script row type 2 -> script 4): its entry script ran script command 804 (Fly / Town Map unlock level) with argument 1 while flag 0x168 is clear, i.e. on every entry. The shared Fly / Town Map is level 2 (both pictures); this build now sets 2 there, so no Johto-side script lowers the map. (The map apps also repair the saved level to 2 whenever either opens, town_map_kanto_first.py, so a save that was lowered before heals.)
Map 31's only trigger (x 734, z 402, script 2, while variable 0x408A == 0) is the "Do you know what you just did! You've taken your first step into Kanto" scene; it is the wrong way round for a player who arrives from Kanto. Its required value becomes 0x7FFF (never reached), so it cannot fire. The actors stay.
Other 804 callers (read from the script banks, not changed): map 387 entry (level 2 + flag 0x998), map 500 (level 2). The earlier "map 280, level 0" entry was a byte match inside a movement table (ApplyMovement), not a level command.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step2b.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit

BORDER = 31
ENTRY_AT = 33                                           # ScrCmd_804 <level> at 33 in the bank's script 4 (hg_dis.py)
TRIGGER = (2, 734, 402, 1, 3, 0, 0, 0x408A)
NEVER = 0x7FFF


def patch(rom):
    e = MapEdit(rom, BORDER)
    assert bytes(e.bank[ENTRY_AT:ENTRY_AT + 3]) == struct.pack('<HB', 804, 1), 'map 31 entry command moved'
    bank = bytearray(e.bank)
    bank[ENTRY_AT + 2] = 2
    e.bank = bytes(bank)
    rows = e.groups[3]
    assert len(rows) == 1 and struct.unpack('<8H', rows[0]) == TRIGGER, [struct.unpack('<8H', r) for r in rows]
    row = bytearray(rows[0])
    struct.pack_into('<H', row, 12, NEVER)
    rows[0] = bytes(row)
    e.save()
    return dict(level=2, trigger_value=hex(NEVER))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
