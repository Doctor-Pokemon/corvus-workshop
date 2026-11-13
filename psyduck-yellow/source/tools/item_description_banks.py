"""Prototype 0217: HeartGold's own descriptions for items 1-536 come back (owner report 2026-11-10: most bag items had no description, some showed NPC text; plan item 22).
The engine (overlay 129, 0x23D8BE8 / 0x23D8E9C) reads an item's description from a text bank chosen by item id: ids 1-536 -> bank 830 (row = id), 537-638 -> 834, 639-775 -> 838, 776-1073 -> 842, 1074-1828 -> 846, 1829-2684 -> 850, 2685+ -> bank 221.
In this ROM bank 830 held leftover map text (the Pallet bedroom hint), so every original item showed nothing. Nobody's map header points at bank 830 (checked 2026-11-10 over all native and extension maps).
This tool rewrites bank 830 with 537 rows: HeartGold's own text (its bank 221, one row per item) for every original id whose item is unchanged, our own custom rows 113-123 (taken from our bank 221, same ids), and for the two TMs whose move changed
(items 361 and 385 = TM034 Moonblast, TM058 Dazzling Gleam) the move's description from our move description bank 749. Ids that were renamed cosmetically (same item, modern name) keep the vanilla text.
NOT touched: banks 834-850 (items 537+: no source text exists, they stay as they are, so e.g. Eviolite still shows wrong text) and bank 221 (ids 2685+).
Usage (from yellow-heartgold, PYTHONPATH=tools): item_description_banks.py <in.nds> <out.nds> <vanilla HeartGold.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from prototype import decode_messages, encode_messages

BANK, DESC, NAMES, MOVE_DESC, VANILLA_COUNT = 830, 221, 222, 749, 537
CUSTOM_ROWS = range(113, 124)                       # our reused item slots (bank 221 rows 113-123 hold our own text)
RENAMED = {22, 34, 58, 61, 83, 86, 213, 222, 226, 227, 240, 246, 248, 252, 259, 433, 434, 436, 450, 453, 464, 469, 471, 473, 477, 482, 483, 486, 487, 488, 489, 490, 491, 504}
CHANGED_TMS = {361: 33, 385: 57}                    # item id -> slot in the machine table (the moves differ from HeartGold's)
TMS = set(range(328, 420)) - set(CHANGED_TMS)
HM_TABLE = struct.pack('<8H', 15, 19, 57, 70, 250, 249, 127, 431)


def patch(rom, vanilla):
    ours = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    van = ndspy.narc.NARC(vanilla.files[vanilla.filenames.idOf('a/0/2/7')])
    key, _ = decode_messages(ours.files[BANK])
    _, own = decode_messages(ours.files[DESC])
    _, vrows = decode_messages(van.files[DESC])
    _, names = decode_messages(ours.files[NAMES])
    _, vnames = decode_messages(van.files[NAMES])
    _, moves = decode_messages(ours.files[MOVE_DESC])
    arm9 = bytes(rom.loadArm9().sections[0].data)
    at = arm9.find(HM_TABLE)
    assert at > 0 and arm9.count(HM_TABLE) == 1
    table = struct.unpack_from('<92H', arm9, at - 184)
    assert len(vrows) == VANILLA_COUNT and len(vnames) == VANILLA_COUNT
    rows = [[65535] for _ in range(VANILLA_COUNT)]
    rows[0] = list(vrows[0])
    copied, custom, skipped = 0, [], []
    for i in range(1, VANILLA_COUNT):
        if i in CUSTOM_ROWS and len(own[i]) > 1:
            rows[i] = list(own[i])
            custom.append(i)
        elif i in CHANGED_TMS:
            rows[i] = list(moves[table[CHANGED_TMS[i]]])
            copied += 1
        elif len(vrows[i]) > 1 and (names[i] == vnames[i] or i in RENAMED or i in TMS):
            rows[i] = list(vrows[i])
            copied += 1
        else:
            skipped.append(i)
    ours.files[BANK] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = ours.save()
    return dict(copied=copied, custom=custom, left_blank=skipped, rows=len(rows))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, ndspy.rom.NintendoDSRom.fromFile(sys.argv[3])))
    rom.saveToFile(sys.argv[2])
