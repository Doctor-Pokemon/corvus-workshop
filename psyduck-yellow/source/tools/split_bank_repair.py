"""ROM 0275: repair the script ids that parcel_quest.split_bank damaged in six rebuilt native banks (plan item 81; memory split-bank-out-of-order-bug; same cause as tools/viridian_guide_fix.py).
Native HeartGold banks keep their scripts OUT of id order; split_bank cut each script at the next start in LIST order, so an id whose code lies earlier in the file came back empty and now starts at the same offset as the next id,
i.e. talking to its NPC / stepping on its trigger runs the neighbour's code. Found by comparing the six maps' banks with the vanilla ROM (duplicate script starts + first 14 bytes differ from the vanilla script of the same id):
 map 20  (bank 1332 / vanilla 199): ids 1 (the photographer NPC, sprite 328) and 4 (a trainer-tips signpost);
 map 56  (1289 / 807): ids 6 (signpost) and 7 (the photographer, sprite 328);
 map 381 (1318 / 803): ids 5 (NPC line, message 10) and 10 (message 19);
 map 398 (1313 / 832): id 3 (NPC line, message 3);
 map 410 (1316 / 829): id 4 (the warp-pad script: ScrCmd_609, fade, Warp 0x19A 0 15 23);
 map 480 (1317 / 809): ids 3 (the gym guide, sprite 168, CheckBadge 12) and 8 (the second badge-dependent line).
Fix (like the Viridian guide): the vanilla script's code (extent = start to the next larger start in the vanilla bank) is appended at the end of the current bank and the bank's header entry of that id is re-pointed at it, so every
reference (actors saved in a save file, triggers, rows) keeps working with the same id. Preconditions checked per script: every command reachable from the script, and every movement block it applies, lies inside the vanilla extent
(the copy is then self-contained: jumps and movement offsets are relative), and the copy keeps the vanilla start's offset modulo 4.
Usage (from yellow-heartgold, PYTHONPATH=tools): split_bank_repair.py <in.nds> <out.nds> <vanilla HeartGold.nds> <pret script.inc>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from hg_dis import dis, load_table
from viridian_tutorial import TABLE

VANILLA_TABLE = 0x020F6BE0 - 0x02000000
FIXES = {20: (1, 4), 56: (6, 7), 381: (5, 10), 398: (3,), 410: (4,), 480: (3, 8)}


def starts_of(bank):
    count = next(i for i in range(400) if struct.unpack_from('<H', bank, 4 * i)[0] == 0xFD13)
    return [struct.unpack_from('<I', bank, 4 * i)[0] + 4 * i + 4 for i in range(count)]


def extent(bank, number):
    starts = starts_of(bank)
    start = starts[number - 1]
    later = sorted(s for s in starts if s > start)
    return start, (later[0] if later else len(bank))


def movement_end(bank, at):
    while struct.unpack_from('<H', bank, at)[0] != 0xFE:
        at += 4
    return at + 4


def check_self_contained(bank, number, table):
    start, end = extent(bank, number)
    starts = starts_of(bank)
    lo, hi = start, start
    for at, name, args in dis(bank, starts, table, number):
        lo, hi = min(lo, at), max(hi, at + 2)
        if name == 'ApplyMovement':
            target = at + 8 + struct.unpack_from('<i', bank, at + 4)[0]
            lo = min(lo, target)
            hi = max(hi, movement_end(bank, target))
    assert start <= lo and hi <= end, ('script %d reaches outside its extent' % number, start, end, lo, hi)
    return start, end


def patch(rom, vanilla, table):
    cd = bytes(rom.loadArm9().sections[0].data)
    vd = bytes(vanilla.loadArm9().sections[0].data)
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    vscripts = ndspy.narc.NARC(vanilla.getFileByName('a/0/1/2'))
    report = {}
    for map_id, ids in FIXES.items():
        cb = struct.unpack_from('<H', cd, TABLE + 24 * map_id + 6)[0]
        vb = struct.unpack_from('<H', vd, VANILLA_TABLE + 24 * map_id + 6)[0]
        vbank, bank = bytes(vscripts.files[vb]), bytearray(scripts.files[cb])
        for number in ids:
            start, end = check_self_contained(vbank, number, table)
            original = vbank[start:end]
            cstarts = starts_of(bytes(bank))
            assert cstarts.count(cstarts[number - 1]) > 1 and bytes(bank[cstarts[number - 1]:cstarts[number - 1] + 14]) != original[:14], ('map %d id %d is not damaged' % (map_id, number))
            bank.extend(b'\0' * (-(len(bank) - start) % 4))
            at = len(bank)
            bank.extend(original)
            struct.pack_into('<I', bank, 4 * (number - 1), at - (4 * (number - 1) + 4))
            new = starts_of(bytes(bank))
            assert bytes(bank[new[number - 1]:new[number - 1] + len(original)]) == original and new.count(new[number - 1]) == 1
            report.setdefault(map_id, []).append((number, len(original), at))
        scripts.files[cb] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, ndspy.rom.NintendoDSRom.fromFile(sys.argv[3]), load_table(sys.argv[4])))
    rom.saveToFile(sys.argv[2])
