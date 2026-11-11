"""Prototype 0214: New Bark Town's west exit (Route 29) no longer lets the player skip the Johto opening (owner note 5, 2026-11-09).
Cause (hg_dis.py + emulator on 0213): the west trigger (map 60, x 676, script 3, while variable 0x407E == 0) starts with "CheckFlag 0x9C (Pokegear)". Flag set -> Elm runs up ("Wait one second! ... Here, I'll give you my number") and the player walks on; flag clear -> an NPC stops the player with HeartGold's own lines ("It's dangerous to go out without a Pokemon", or "Did you leave your Pokegear at home" once the starter is taken). Our save already has the Pokegear from Kanto, so the scene let the player out before Elm's lab, the starter and Mr. Pokemon.
Fix: the 11-byte "CheckFlag 0x9C; GoToIf EQ elm" is replaced by a jump to a small block: Pokegear flag set AND the postgame counter 0x4128 > 6 (our starter has been given: Elm's menu sets 7) -> the native Elm scene as before; otherwise the native "stopped" branch (the vanilla no-Pokemon line, nothing new is said). Nothing is added to the save; no frame rows.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step2c.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from johto_step3d import install, write_scripts
from johto_step3e import A

NEW_BARK = 60
POKEGEAR, STARTER_GIVEN = 0x9C, 0x4128
PAT = struct.pack('<2H', 32, POKEGEAR) + struct.pack('<HBi', 28, 1, 0x3FC)


def block(base, elm, stopped):
    a = A()
    a.check_flag(POKEGEAR).jump('geared', 1).jump(('abs', stopped))
    a.label('geared').compare(STARTER_GIVEN, 6).jump(('abs', elm), 2).jump(('abs', stopped))
    return a.build(base)


def patch(rom):
    e = MapEdit(rom, NEW_BARK)
    assert e.bank.count(PAT) == 1, 'the west-exit check was not found exactly once'
    size = len(block(0, 0, 0))
    ids, addrs, starts = install(e, [size])
    at = e.bank.find(PAT)
    stopped, elm = at + 11, at + 11 + 0x3FC
    code = block(addrs[0], elm, stopped)
    assert len(code) == size
    write_scripts(e, addrs, [code])
    bank = bytearray(e.bank)
    bank[at:at + 6] = struct.pack('<Hi', 22, addrs[0] - (at + 6))
    e.bank = bytes(bank)
    e.save()
    return dict(block=ids[0])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
