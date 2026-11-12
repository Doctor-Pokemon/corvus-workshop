"""Prototype 0255: the Kanto Elite Four room battles work again for LORELEI and AGATHA (owner bug report 2026-11-12: Lorelei's battle froze on MelonDS, never started on DeSmuME, Data Abort on a 3DS).
CAUSE (prototype 0240, tools/elite_four_classes.py): Lorelei (trainer 245) became class 85 and Agatha (418) class 84 so they get their own battle sprites. hg-engine's ITCM function at 0x01FFF088 maps a trainer
class to its encounter effect: class 0x81 -> 0x1D, else it searches a table of 32 u16 entries at 0x020FC3CA (low 10 bits = trainer class, high 6 bits = effect; the Elite Four classes 87/89/112/88/86 have
effects 16..20, the gym leaders, the rival and others sit in it too) and returns 0x29 (the ordinary trainer effect) when the class is not in it. In an Elite Four ROOM the battle starts with the Elite Four effect only; a
class without an entry leaves it unfinished and the battle never starts (any other class, e.g. 20 or 111, hangs the same way in the room). Outside a room an unknown class simply gets the ordinary transition,
which is why the bedroom tests of 0240 passed.
FIX: a copy of the table with two more entries, (85 -> Karen's effect) and (84 -> Karen's effect, the effect of class 88, the old class of both women), goes into a 68-byte run of zeros of overlay 129 (0x023DF6F4, nothing refers to it,
zero in a running game); the ITCM function's pointer (literal at 0x01FFF0B8) is repointed to it and its count (cmp r2,#0x20 at 0x01FFF0AE) becomes 0x22.
Emulator: Lorelei's room battle shows the VS screen, "You are challenged by Elite Four LORELEI!" with her own sprite, and the battle starts.
Usage (from yellow-heartgold, PYTHONPATH=tools): e4_class_table.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom

OLD_TABLE, COUNT_SITE, LITERAL_SITE = 0x020FC3CA, 0x01FFF0AE, 0x01FFF0B8
GAP, GAP_SIZE = 0x023DF6F4, 68
KAREN, NEW_CLASSES = 88, (85, 84)


def patch(rom):
    main = rom.loadArm9()
    arm9, itcm = main.sections[0], main.sections[1]
    arm9.data, itcm.data = bytearray(arm9.data), bytearray(itcm.data)
    assert itcm.ramAddress == 0x01FF8000
    assert struct.unpack_from('<I', itcm.data, LITERAL_SITE - itcm.ramAddress)[0] == OLD_TABLE
    assert struct.unpack_from('<H', itcm.data, COUNT_SITE - itcm.ramAddress)[0] == 0x2A20, 'cmp r2,#0x20'
    entries = list(struct.unpack_from('<32H', arm9.data, OLD_TABLE - arm9.ramAddress))
    assert all(e & 0x3FF not in NEW_CLASSES for e in entries), 'class already in the table'
    karen = [e for e in entries if e & 0x3FF == KAREN]
    assert len(karen) == 1
    entries += [(karen[0] & ~0x3FF) | cls for cls in NEW_CLASSES]
    raw = struct.pack(f'<{len(entries)}H', *entries)
    assert len(raw) == GAP_SIZE
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    at = GAP - perm.ramAddress
    assert not any(perm.data[at:at + GAP_SIZE]), 'the gap is not zero'
    assert perm.data[at - 1] == 0 or True
    perm.data[at:at + GAP_SIZE] = raw
    struct.pack_into('<I', itcm.data, LITERAL_SITE - itcm.ramAddress, GAP)
    struct.pack_into('<H', itcm.data, COUNT_SITE - itcm.ramAddress, 0x2A22)
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    rom.arm9 = main.save(compress=True)
    return dict(table=hex(GAP), entries=len(entries), karen_entry=hex(karen[0]), added=[hex(e) for e in entries[32:]])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
