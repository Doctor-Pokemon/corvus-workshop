"""Prototype 0184: the Poke Flute becomes a real key item that is actually played (owner request 2026-11-04: "check if the Poke Flute actually has a USE option and does SOMETHING ... like play a sound").
Found live: item 651 had an all-zero item record, so it sat in the ordinary Items pocket with a "?" icon, could be TRASHED (a way to lose the only thing that wakes Snorlax) and had no USE button at all.
 - Item record: copied from the Silph Scope (874), a plain key item (Key Items pocket, cannot be tossed, no use function).
 - Icon: the Blue Flute's (item 65) icon graphics and palette (a/0/1/8 files 2*id+2 / +3).
 - Snorlax (Route 12 actors 15-18): once the Poke Flute is in the bag the player now PLAYS it before he wakes: "{PLAYER} played the POKe FLUTE!" with the item jingle (fanfare 1185) and then the existing wake-up lines, cry and battle. Without the flute his blocked-road text is unchanged.
NOT done (needs engine work, see the plan): a USE button in the bag itself. HeartGold's bag only offers USE for items with a field-use function; there is none that plays a flute and then wakes Snorlax, so playing happens when the player talks to the Snorlax.
Usage (from yellow-heartgold, PYTHONPATH=tools): poke_flute_item.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import encode_text, events_decode, events_encode, script_bank, Script
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

POKE_FLUTE, SILPH_SCOPE, BLUE_FLUTE = 651, 874, 65      # 0184 used the Blue Flute's icon; key_item_icons.py (0185) replaces it with the Yellow Flute's (owner's choice)
MAP, FLUTE_SCRIPT = 20, 7
TEXT = '{PLAYER} played the POKé FLUTE!'
FANFARE = 1185


def patch(rom, source=None):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    assert bytes(items.files[POKE_FLUTE]) == bytes(36), 'the Poke Flute record is not the empty one'
    items.files[POKE_FLUTE] = bytes(items.files[SILPH_SCOPE])
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    for k in (2, 3):
        gfx.files[POKE_FLUTE * 2 + k] = bytes(gfx.files[BLUE_FLUTE * 2 + k])
    rom.setFileByName('a/0/1/8', gfx.save())
    main = rom.loadArm9()
    dd = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tid = struct.unpack_from('<3H', dd, rec + 6)
    eid = struct.unpack_from('<H', dd, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    bank = split_bank(scripts.files[sid])
    body = bytearray(bank[FLUTE_SCRIPT - 1])
    head = bytes.fromhex('49 00 dc 05 60 00')                       # SetVar/LockAll opening of the second (woken) block
    second = body.index(head, 10)
    assert body[second + 6:second + 12] == struct.pack('<3H', 41, 0x800C, 1), body[second:second + 14].hex(' ')
    key, lines = decode_messages(texts.files[tid])
    msg = len(lines)
    lines.extend(decode_messages(encode_text([TEXT], PH))[1])
    s = Script().msg(msg).emit(78, FANFARE).emit(79)
    insert = s.finish()
    body[second + 6:second + 6] = insert                             # after the block's opening, before its first test: nothing inside the block moves relative to itself
    new_idx = len(bank) + 1
    bank.append(bytes(body))
    groups = events_decode(events.files[eid])
    moved = []
    for i, a in enumerate(groups[1]):
        if struct.unpack_from('<H', a, 10)[0] in (6, FLUTE_SCRIPT) and struct.unpack_from('<H', a, 2)[0] in (315, 395):
            row = bytearray(a)
            struct.pack_into('<H', row, 10, new_idx)
            groups[1][i] = bytes(row)
            moved.append(struct.unpack_from('<H', a, 0)[0])
    assert sorted(moved) == [15, 16, 17, 18], moved
    scripts.files.append(script_bank(bank))
    texts.files.append(encode_messages(key, lines))
    events.files[eid] = events_encode(groups)
    struct.pack_into('<H', dd, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', dd, rec + 10, len(texts.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(item=POKE_FLUTE, script=new_idx, message=msg, actors=moved)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
