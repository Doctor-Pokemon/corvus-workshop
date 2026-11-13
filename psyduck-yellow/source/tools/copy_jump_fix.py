"""ROM 0264: the relocated native-script copies of johto_step1b.py / johto_step1c.py froze the player.

Found by a ferry return test (2026-11-12, ROM 0263): after the S.S. AQUA arrival the player talks to the Vermilion hall sailor (map 386) to get past him; the script froze with the player locked
(emulator: no text, no movement, LockAll forever). Pointing the sailor at the ORIGINAL native script (script 1, untouched in the same bank) works: the sailor steps aside and the player walks
out to Vermilion City.
Cause: johto_step1b / johto_step1c copied the native script into a new script behind a prelude. The copy keeps relative jumps but lands at an ODD distance from the original (595 / 597 bytes), so its
ApplyMovement data (referenced by a relative offset) now sits at an odd byte address; the movement reader needs 2-byte aligned data and never finishes.
Fix: the prelude's jump into the copy is repointed to the original script (the copy stays in the bank as dead code). Same fix for the Saffron Magnet Train attendant (map 400), whose copy has the same shift.
Usage (from yellow-heartgold, PYTHONPATH=tools): copy_jump_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from viridian_tutorial import TABLE

# (map id, original script start, copy start, bytes of the script block); verified below against the live bank
FIXES = ((386, 49, 644), (400, 163, 760))


def fix_bank(bank, orig, copy):
    from johto_step1b import script_ranges
    starts, ends = script_ranges(bank)
    length = ends[starts.index(orig)] - orig
    assert bytes(bank[orig:orig + length]) == bytes(bank[copy:copy + length]), 'the copy is not the original'
    hits = []
    for pos in range(len(bank) - 7):
        if struct.unpack_from('<H', bank, pos)[0] == 28 and pos + 7 + struct.unpack_from('<i', bank, pos + 3)[0] == copy and bank[pos + 2] <= 5:
            hits.append(pos)
    assert len(hits) == 1, hits
    pos = hits[0]
    struct.pack_into('<i', bank, pos + 3, orig - (pos + 7))
    return pos


def patch(rom):
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    d = bytes(rom.loadArm9().sections[0].data)
    report = {}
    for map_id, orig, copy in FIXES:
        bank_id = struct.unpack_from('<H', d, TABLE + 24 * map_id + 6)[0]
        bank = bytearray(scripts.files[bank_id])
        report[map_id] = fix_bank(bank, orig, copy)
        scripts.files[bank_id] = bytes(bank)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
