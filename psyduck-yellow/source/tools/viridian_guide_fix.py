"""Prototype 0204: the Viridian Gym's Gym Guide (the NPC in front of the door) talks again (owner report 2026-11-09, real 3DS: a save made inside the gym crashed with 'Error: Data Abort' on the first move; on turning right first the owner could play the whole gym).
Cause (found with the emulator): the native gym's script bank (743) keeps its scripts OUT OF ORDER (offsets 22, 107, 333, 401, 1152 for scripts 3, 1, 2, 4, 5). viridian_gym_yellow.py rebuilt the bank with parcel_quest.split_bank, which cuts each script at the NEXT START IN LIST ORDER, so script 2 (the guide's talk script, bytes 333-401) became EMPTY
and its bytes were glued onto the end of script 3. Script 2 then starts at the same offset as script 3, so pressing A on the guide ran script 3, the gym's ENTRY script (sets variables, hides things), and the emulator shows both sprites garbled afterwards; the real 3DS crashed in its player movement handler.
Fix: the original script 2 (68 bytes, ends with ReleaseAll/End, only a relative jump inside itself, messages 6 and 7 of the gym's own text bank, sets variable 0x4127 = 1 like the native one) is appended to map 579's bank and the bank's header entry for script 2 points at it. The actor keeps script id 2, which matters because a save keeps the map's NPC objects (script id included): an existing save is repaired too. Nothing else changes.
The same splitter damaged other rebuilt banks (see CAMPAIGN-FIRST-PLAN.md 2026-11-09): those are listed there, not touched here.
Usage (from yellow-heartgold, PYTHONPATH=tools): viridian_guide_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from ext_edit import ExtEdit
from viridian_tutorial import TABLE

NATIVE_MAP, GYM, GUIDE_SPRITE, GUIDE_SCRIPT = 496, 579, 168, 2


def script_extent(raw, number):
    """Real extent of script `number` of a bank: from its start to the next larger start (HeartGold banks are not stored in id order)."""
    count = next(i for i in range(400) if struct.unpack_from('<H', raw, 4 * i)[0] == 0xFD13)
    starts = [struct.unpack_from('<I', raw, 4 * i)[0] + 4 * i + 4 for i in range(count)]
    start = starts[number - 1]
    later = sorted(s for s in starts if s > start)
    return raw[start:later[0] if later else len(raw)], starts


def patch(rom):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    native_bank = struct.unpack_from('<H', d, TABLE + NATIVE_MAP * 24 + 6)[0]
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    original, _ = script_extent(bytes(scripts.files[native_bank]), GUIDE_SCRIPT)
    assert len(original) == 68 and original[:2] == b'\x49\x00' and original[-4:] == b'\x61\x00\x02\x00', original.hex(' ')
    edit = ExtEdit(rom, GYM)
    now, starts = script_extent(bytes(edit.bank), GUIDE_SCRIPT)
    assert starts[GUIDE_SCRIPT - 1] == starts[GUIDE_SCRIPT], ('the gym bank is not in the damaged state', starts[:4])
    # repair script 2 IN PLACE (a save keeps the map's NPC objects, script id included, so the guide in an existing save still says script 2):
    # the real code goes at the end of the bank and the bank's header entry for script 2 points at it
    bank = bytearray(edit.bank)
    bank.extend(b'\0' * (-len(bank) % 4))
    at = len(bank)
    bank.extend(original)
    struct.pack_into('<I', bank, 4 * (GUIDE_SCRIPT - 1), at - (4 * (GUIDE_SCRIPT - 1) + 4))
    edit.bank = bytes(bank)
    fixed, after = script_extent(edit.bank, GUIDE_SCRIPT)
    assert fixed == original and after[GUIDE_SCRIPT - 1] != after[GUIDE_SCRIPT], 'repair did not take'
    edit.save()
    return dict(map=GYM, script=GUIDE_SCRIPT, bytes=len(original), at=at)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
