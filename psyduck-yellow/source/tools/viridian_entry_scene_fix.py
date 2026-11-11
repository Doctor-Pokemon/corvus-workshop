"""Prototype 0205: the Viridian Gym's entrance scene is removed (owner report 2026-11-09, real 3DS: 'Error: Data Abort' every time the owner walks between the crates and the guide at the entrance; the rest of the gym is fine).
The scene is the NATIVE HeartGold gym's (script 4, trigger row z=51 x=47..55 right in front of the guide): it asks GetPlayerPos for the player's absolute X and compares it with 1-6 and 8 (the native gym's own small coordinates), then moves the guide (actor 4) and the PLAYER with
scripted movement lists written for that layout and shows message 8. The rebuilt gym (Yellow's layout, extension map 579) puts the player at X 47-55, so only the fall-through branch ever runs: movement lists made for another place.
Yellow's Viridian Gym has no entrance scene, and nothing depends on it (flag 0x13a and variable 0x4127 are used only by this scene and by the guide's own talk script, which sets 0x4127 itself; Giovanni's script 1 references neither), so the trigger row is deleted. The guide and his talk script (repaired in 0204) stay.
Not reproduced in DeSmuME (the scene never fires there, the base save has flag 0x13a set); the 3DS crash is hardware only.
Usage (from yellow-heartgold, PYTHONPATH=tools): viridian_entry_scene_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from ext_edit import ExtEdit

GYM, SCENE_SCRIPT, SCENE_VAR = 579, 4, 0x4127


def patch(rom):
    edit = ExtEdit(rom, GYM)
    keep = [t for t in edit.groups[3] if not (struct.unpack_from('<H', t, 0)[0] == SCENE_SCRIPT and struct.unpack_from('<H', t, 14)[0] == SCENE_VAR)]
    assert len(edit.groups[3]) - len(keep) == 1, (len(edit.groups[3]), len(keep))
    edit.groups[3] = keep
    edit.save()
    return dict(map=GYM, triggers_left=len(keep))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
