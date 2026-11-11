"""Prototype 0218: the 404-byte table buffer of the battle-transition lookup comes from a healthy heap (owner crash 2026-11-10, 3DS photo: Data Abort PC 0206FD5C ADDR 000000F0 right after Morty's talk, before the battle transition).
Cause found in the owner's nds-bootstrap RAM dump: ARM9 0x0206FD30 allocates a 0x194-byte table from heap id 0 (the small system heap, 0x226EFD0-0x227C198, 53,704 bytes) and then reads entry r5 of it. In the dump that heap's FREE LIST is corrupted:
the heap header lists only a 156-byte free block, while the 51,492 free bytes behind it are not linked (a 156-byte block FREE, then a 51,492-byte block FREE, their prev/next fields inconsistent), so the request found nothing, returned NULL and `ldr r5,[r4,r0]` read address 0xF0.
The emulator's heap 0 at the same place is healthy (one 51,664-byte free block), so the emulator never crashes. WHO damages the list is NOT found yet.
Workaround (symptom only): `movs r0,#0` at 0x0206FD48 (heap id) becomes `movs r0,#3` (heap id 3: 1.1 MB, 59,624 bytes free in the dump, a consistent block list). The temporary buffer is freed through the block's own heap id, so nothing else changes.
Usage (from yellow-heartgold, PYTHONPATH=tools): battle_table_heap.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom

SITE = 0x0206FD48
OLD, NEW = 0x2000, 0x2003            # movs r0,#0 -> movs r0,#3
CONTEXT = bytes.fromhex('6521 8900 0020'.replace(' ', ''))   # not used for matching (kept for reading): movs r1,#0x65; lsls r1,r1,#2 around the site


def patch(rom):
    main = rom.loadArm9()
    s = main.sections[0]
    s.data = bytearray(s.data)
    at = SITE - s.ramAddress
    assert struct.unpack_from('<H', s.data, at)[0] == OLD, hex(struct.unpack_from('<H', s.data, at)[0])
    assert struct.unpack_from('<H', s.data, at - 2)[0] == 0x2165 and struct.unpack_from('<H', s.data, at + 2)[0] == 0x0089, 'not the expected movs r1,#0x65 ; movs r0,#0 ; lsls r1,r1,#2 shape'
    struct.pack_into('<H', s.data, at, NEW)
    rom.arm9 = main.save(compress=True)
    return dict(site=hex(SITE), heap_id=3)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
