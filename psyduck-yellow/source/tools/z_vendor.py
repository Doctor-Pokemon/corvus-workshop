"""Prototype 0262 (owner order 2026-11-12): the TEN Z-Crystals the Johto gym leaders do not give are sold by a stall keeper outside the Johto Safari Zone gate.
Owner: "There are already NPCs manning stalls outside the Safari Zone gate ... they don't DO anything except talk. Can we use one of them?" (the outdoor map is 174; the gate building is 173; the Kanto Safari Zone was dropped).
THE KEEPER: map 174 actor 3 (sprite 1022 at (97,299), script 3 = the silent man with the Kangaskhan, whose only text is "..................\n(I am not a talker.)"). His actor now runs a new script: the same line (message 3, unchanged), then the shared Kanto Mart vendor
(kanto_mart_shared.vendor_script: Buy / Sell / See ya, native sell, the inline catalog) with exactly the ten crystals. The two real shops of that street (the drink vendors, scripts 7 and 8) are untouched.
THE TEN: Fire 777, Water 778, Electric 779, Grass 780, Poison 783, Ground 784, Psychic 786, Rock 788, Dark 791, Fairy 793 (held ids; the gifts of tools/z_crystal_gifts.py cover Normal, Ice, Fighting, Flying, Bug, Ghost, Dragon, Steel).
PRICE: the shop uses the item record's own price and these records were all zero (no price): the ten get 10000 each (ASSUMPTION: the owner did not pick a price; the League's stone shop is tiered 5000 to 40000). The eight gift crystals keep price 0.
No flag: Johto is only reachable after the Hall of Fame. No Z-Ring check at the stall (the ring only gates the battle button).
Usage (from yellow-heartgold, PYTHONPATH=tools): z_vendor.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import kanto_mart_shared as shared
from map_edit import MapEdit
from johto_step3d import install, write_scripts
from johto_step3e import A

MAP, ACTOR, GREETING_MSG = 174, 3, 3
TEN = (777, 778, 779, 780, 783, 784, 786, 788, 791, 793)
PRICE = 10000
PRELUDE = 8                                           # PlaySE 1500 + LockAll + FacePlayer at the start of the vendor script


def patch(rom):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    for i in TEN:
        assert bytes(items.files[i]) == bytes(36), ('item has a record already', i)
        items.files[i] = struct.pack('<H', PRICE) + bytes(34)
    rom.setFileByName('a/0/1/7', items.save())
    e = MapEdit(rom, MAP)
    actor = bytearray(e.groups[1][ACTOR])
    old_script = struct.unpack_from('<H', actor, 10)[0]
    assert struct.unpack_from('<2H', actor, 0) == (ACTOR, 1022) and old_script == 3, struct.unpack_from('<8H', actor, 0)
    raw = shared.vendor_script([{'badges': n, 'v': []} for n in range(9)], 'v', TEN)
    assert raw[:PRELUDE] == bytes.fromhex('4900dc0560006800'), 'unexpected vendor prelude'
    def greeting(base, target):                              # LockAll, FacePlayer, the keeper's original line, then into the vendor body (past its own prelude)
        a = A()
        a.raw(struct.pack('<H', 96)).raw(struct.pack('<H', 104))
        a.msg(GREETING_MSG)
        a.jump(('abs', target + PRELUDE))
        return a.build(base)
    ids, addrs, _ = install(e, [len(raw), len(greeting(0, 0))])
    assert addrs[0] % 4 == 0, 'the vendor body must start 4-aligned (its inline catalog is read as halfwords)'
    write_scripts(e, [addrs[0], addrs[1]], [raw, greeting(addrs[1], addrs[0])])
    new_id = ids[1]
    struct.pack_into('<H', actor, 10, new_id)
    e.groups[1][ACTOR] = bytes(actor)
    e.save()
    return dict(map=MAP, actor=ACTOR, old_script=old_script, new_script=new_id, items=len(TEN), price=PRICE, vendor_script=ids[0])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
