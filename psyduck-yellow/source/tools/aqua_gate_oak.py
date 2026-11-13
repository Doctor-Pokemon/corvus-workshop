"""Prototype 0263 (owner bug report 2026-11-12, ROM 0262 softlock): the Olivine S.S. Aqua Gate Oak scene is removed.
CAUSE: HeartGold's S.S. Aqua Gate (map 240, script bank 152) has a frame row 'variable 0x411A == 1 -> script 3': Professor Oak's National Pokedex scene. 0x411A is set to 1 by the Champion room script (banks 824/1308), so
in our Kanto-first game it is still 1 when the player first reaches Olivine. The scene's movements are written for a player who enters from the FRONT door (Johto side); our player arrives from the pier (map 330) and is walked south OUT of the room.
WHY IT CAN GO: Oak already gives the National Pokedex at Mr. Pokemon's house (johto_step2.py, variable 8). Nothing else reads 0x411A (checked over every script bank).
FIX: script 3 keeps its id (the frame row and its header stay); its first bytes become: SetVar 0x411A = 0 (so the frame row never fires again: a frame-row script must change its own variable), SetFlag 593 (hides the Oak actor, which the scene would have hidden at its end),
then a jump to the scene's own tail (CompareVar 0x40D3 == 1 -> ClearFlag 691 (Oak at the Goldenrod Radio Tower), EnableMassOutbreaks, End). The rest of the old scene stays as dead code.
No LockAll, no movement, no message. Usage (from yellow-heartgold, PYTHONPATH=tools): aqua_gate_oak.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
import johto_step3d as j

MAP, SCRIPT, VAR, OAK_HIDE = 240, 3, 0x411A, 593
TAIL_SEQ = struct.pack('<3H', 17, 0x40D3, 1)             # CompareVarToValue 0x40D3, 1: the start of the scene's own tail (after its ReleaseAll)


def patch(rom):
    e = MapEdit(rom, MAP)
    bank = bytearray(e.bank)
    at = j.starts(bytes(bank))[SCRIPT - 1]
    assert bytes(bank[at:at + 4]) == bytes.fromhex('6102' '6000'), 'script 3 does not start with the Oak scene'   # ScrCmd_609, LockAll
    tail = bytes(bank).find(TAIL_SEQ, at)
    assert 0 < tail - at < 260 and bytes(bank).count(TAIL_SEQ) == 1, (at, tail)
    assert bytes(bank[tail - 2:tail]) == struct.pack('<H', 97), 'ReleaseAll expected before the tail'
    code = struct.pack('<3H', 41, VAR, 0) + struct.pack('<2H', 30, OAK_HIDE)
    code += struct.pack('<Hi', 22, tail - (at + len(code) + 6))
    bank[at:at + len(code)] = code
    e.bank = bytes(bank)
    e.save()
    return dict(map=MAP, script=SCRIPT, at=at, tail=tail, bytes=len(code))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
