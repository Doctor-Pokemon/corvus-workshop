"""Prototype 0178: the Fuchsia Gym leader gives HM03 Surf after the first win (owner order 2026-11-04; the Safari Zone is dropped, so Surf (Yellow: the Fishing Guru) was unobtainable).
Owner text: "Some people don't like Poison Pokemon that much. Here, you can use this HM to SURF above the pools of poison your journey may throw your way."
Fuchsia Gym (map 480): the leader is actor 2 (sprite 372, script 2 of bank file 809). Its native script: CheckBadge 12 (Soul), battle, GiveBadge 12, her TM (flag 301), then her TM message (4) and the ending
"WaitButton, CloseMsg, ReleaseAll, End"; every later talk reaches the same message 4 and ending. That ending now jumps to a helper appended to a copy of the script: if the bag has no HM03 she says the owner's line,
gives HM03 (fanfare + "received" line; a bag-full line, the next talk tries again); if HM03 is already in the bag it just ends. "Already given" comes from the item itself (HMs cannot be tossed): no flag, no variable.
Surf is unlocked by the Soul Badge (12) or the Fog Badge in this project (kanto_surf_badge.py), and the leader gives the Soul Badge in the same script.
Opcodes: 125 GiveItem, 126 TakeItem, 128 HaveItem.
Usage (from yellow-heartgold, PYTHONPATH=tools): janine_surf.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, end, encode_text, events_decode, events_encode, script_bank
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

MAP, NPC = 480, 2
HM_SURF = 422
TAIL = (178, 186)                           # body offsets of "WaitButton, CloseMsg, ReleaseAll, End" after her TM message (4)
LINE = "Some people don't like Poison Pokémon that much. Here, you can use this HM to SURF above the pools of poison your journey may throw your way."
GOT = '{PLAYER} received HM03!'
FULL = 'You have no room for this.'


def helper(first):
    s = Script()
    s.emit(128, HM_SURF, 1, 0x800C).compare(0x800C, 1).jump('done', 1)
    s.msg(first).emit(125, HM_SURF, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    s.emit(78, 1185).msg(first + 1).emit(79)
    end(s)
    s.label('full').msg(first + 2)
    end(s)
    s.label('done')
    end(s)
    return s


def patch(rom, source=None):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    old = struct.unpack_from('<7H', groups[1][NPC], 0)
    assert old[1] == 372 and old[4] == 755 and old[5] == 2, old
    bank = split_bank(scripts.files[sid])
    body = bytearray(bank[old[5] - 1])
    assert len(body) == 202, len(body)
    tail = bytes.fromhex('32 00 35 00 61 00 02 00')
    assert body[TAIL[0] - 3:TAIL[1]] == bytes.fromhex('2d 00 04') + tail, body[TAIL[0] - 3:TAIL[1]].hex(' ')
    key, lines = decode_messages(texts.files[tid])
    first = len(lines)
    lines.extend(decode_messages(encode_text([LINE, GOT, FULL], PH))[1])
    h = helper(first)
    code = h.finish()
    a, b = TAIL
    body[a:a + 6] = struct.pack('<Hi', 22, len(body) - (a + 6))
    body[a + 6:b] = bytes(b - a - 6)
    body.extend(code)
    idx = len(bank) + 1
    bank.append(bytes(body))
    row = bytearray(groups[1][NPC])
    struct.pack_into('<H', row, 10, idx)
    groups[1][NPC] = bytes(row)
    scripts.files.append(script_bank(bank))
    texts.files.append(encode_messages(key, lines))
    events.files.append(events_encode(groups))
    dd = main.sections[0].data = bytearray(main.sections[0].data)
    struct.pack_into('<H', dd, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', dd, rec + 10, len(texts.files) - 1)
    struct.pack_into('<H', dd, rec + 16, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(map=MAP, script=idx, first_message=first)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
