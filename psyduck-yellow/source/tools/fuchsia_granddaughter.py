"""Fuchsia: the Warden's granddaughter hands over his GOLD TEETH (owner order 2026-11-04; the Safari Zone is dropped, the teeth no longer lie in it).
She is the girl in the house with the blue door east of the Warden's house (map 483, actor 0 = script 1). Her existing line (message 0: "My grandpa closed the Safari Zone ...") stays; after it she says the owner's line
"If you happen to see him around anywhere, could you give his GOLD TEETH back to him for me? He can't talk straight without them. Teehee." and gives the Gold Teeth (item 877) unless the Warden has already been helped
(his flag 0xA6C, set by safari_yellow's Warden script when he gives HM04 Strength) or the teeth are already in the bag. Then the Warden (map 481) takes the teeth and gives Strength as safari_yellow.py built it.
No new flag or variable. Usage (from yellow-heartgold, PYTHONPATH=tools): fuchsia_granddaughter.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import yellow_text
from opening import Script, end, events_decode, events_encode, script_bank, encode_text
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

MAP, NPC = 483, 0
GOLD_TEETH, WARDEN_GIVEN = 877, 0xA6C
ASK = "If you happen to see him around anywhere, could you give his GOLD TEETH back to him for me? He can't talk straight without them. Teehee."
GOT = '{PLAYER} received the GOLD TEETH!'


def girl_script(first, full_msg):
    s = Script().emit(73, 1500).emit(96).emit(104)
    s.emit(32, WARDEN_GIVEN).jump('plain', 1)
    s.msg(0).msg(first)
    s.emit(128, GOLD_TEETH, 1, 0x800C).compare(0x800C, 0).jump('give', 1)       # 128 = HaveItem (126 would TAKE the teeth)
    end(s)                                                   # the teeth are already in the bag
    s.label('give').emit(125, GOLD_TEETH, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    s.emit(78, 1185).msg(first + 1).emit(79)
    end(s)
    s.label('full').msg(full_msg)
    end(s)
    s.label('plain').msg(0)
    end(s)
    return s.finish()


def patch(rom, source):
    full = yellow_text.message(source, 'WardensHouse', '_WardensHouseWardenHM04NoRoomText')
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    bank = split_bank(scripts.files[sid])
    key, lines = decode_messages(texts.files[tid])
    groups = events_decode(events.files[eid])
    old = struct.unpack_from('<7H', groups[1][NPC], 0)
    assert old[1] == 319 and old[5] == 1, old
    first = len(lines)
    lines.extend(decode_messages(encode_text([ASK, GOT, full], PH))[1])
    idx = len(bank) + 1
    bank.append(girl_script(first, first + 2))
    row = bytearray(groups[1][NPC])
    struct.pack_into('<H', row, 10, idx)
    groups[1][NPC] = bytes(row)
    scripts.files.append(script_bank(bank))
    texts.files.append(encode_messages(key, lines))
    events.files.append(events_encode(groups))
    struct.pack_into('<H', d, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', d, rec + 10, len(texts.files) - 1)
    struct.pack_into('<H', d, rec + 16, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(map=MAP, script=idx, first_message=first)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
