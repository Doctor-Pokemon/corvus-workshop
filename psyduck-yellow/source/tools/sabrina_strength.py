"""Prototype 0177: Sabrina gives HM04 Strength, and the Marsh Badge (not the Rainbow Badge) unlocks Strength (owner orders 2026-11-04).
Why: the Safari Zone is dropped, so Strength (Yellow: the Warden's gift) was unobtainable; the owner moved it to Sabrina. Owner text: "This powerful HM was once given to me by the Karate King, but Psychic Pokemon have no such need for brute STRENGTH. You should take it."
Sabrina (Saffron Gym, map 410, actor 5, script 1 of bank file 829): the native script gives the Marsh Badge (GiveBadge 13) and her TM (flag 386), then ends; later talks end with her message 5. Both endings now jump to a helper
appended to a copy of the script: if the bag has no HM04 she says the owner's line, gives HM04 (fanfare + "received" line; bag-full line, the next talk tries again). If HM04 is already in the bag the first ending just ends
and the repeat ending keeps her message 5. "Already given" is derived from the item itself, so no flag or variable is used (HMs cannot be tossed).
Strength badge: kanto_strength_badge.py made the party-menu check (overlay 129 helper) and the boulder script's helper accept the Plain Badge (2) or the Rainbow Badge (11). The second badge becomes the Marsh Badge (13):
the helper's `movs r1,#11` becomes `movs r1,#13` and the std script's CheckBadge 11 becomes CheckBadge 13; Plain stays an alternative.
Usage (from yellow-heartgold, PYTHONPATH=tools): sabrina_strength.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from opening import Script, end, encode_text
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

MAP, NPC = 410, 5
HM_STRENGTH = 423
RAINBOW, MARSH = 11, 13
MENU_SITE = 0x020681DA                       # the party-menu badge check's bl (kanto_strength_badge.py)
STD_BANK_FIRST_ID, STD_BANK_TEXT = 10000, 211
AFTER_TM = (159, 167)                        # body offsets of "WaitButton, CloseMsg, ReleaseAll, End" after her TM message (4)
REPEAT = (188, 199)                          # body offsets of her repeat message (5) + the same ending
LINE = ("This powerful HM was once given to me by the Karate King, but Psychic Pokémon have no such need for brute STRENGTH. You should take it.")
GOT = '{PLAYER} received HM04!'
FULL = 'You have no room for this.'


def helper(first, repeat_message):
    s = Script()
    s.label('after').emit(128, HM_STRENGTH, 1, 0x800C).compare(0x800C, 1).jump('done', 1).jump('give')
    s.label('repeat').emit(128, HM_STRENGTH, 1, 0x800C).compare(0x800C, 1).jump('five', 1)
    s.label('give').msg(first).emit(125, HM_STRENGTH, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    s.emit(78, 1185).msg(first + 1).emit(79)
    end(s)
    s.label('full').msg(first + 2)
    end(s)
    s.label('five').msg(repeat_message)
    end(s)
    s.label('done')
    end(s)
    return s


def patch_sabrina(rom):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    from opening import events_decode, events_encode, script_bank
    groups = events_decode(events.files[eid])
    old = struct.unpack_from('<7H', groups[1][NPC], 0)
    assert old[1] == 369 and old[4] == 753, old
    bank = split_bank(scripts.files[sid])
    body = bytearray(bank[old[5] - 1])
    assert len(body) == 205, len(body)
    tail = bytes.fromhex('32 00 35 00 61 00 02 00')
    assert body[AFTER_TM[0]:AFTER_TM[1]] == tail and body[AFTER_TM[0] - 3:AFTER_TM[0]] == bytes.fromhex('2d 00 04'), body[AFTER_TM[0] - 3:AFTER_TM[1]].hex(' ')
    assert body[REPEAT[0]:REPEAT[1]] == bytes.fromhex('2d 00 05') + tail, body[REPEAT[0]:REPEAT[1]].hex(' ')
    key, lines = decode_messages(texts.files[tid])
    first = len(lines)
    lines.extend(decode_messages(encode_text([LINE, GOT, FULL], PH))[1])
    h = helper(first, 5)
    code = h.finish()
    start = len(body)
    for (a, b), label in ((AFTER_TM, 'after'), (REPEAT, 'repeat')):
        body[a:a + 6] = struct.pack('<Hi', 22, start + h.labels[label] - (a + 6))
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


def bl_target(data, site, base):
    h1, h2 = struct.unpack_from('<HH', data, site - base)
    assert h1 & 0xF800 == 0xF000 and h2 & 0xF800 == 0xF800, (hex(h1), hex(h2))
    off = ((h1 & 0x7FF) << 11) | (h2 & 0x7FF)
    if off & 0x200000:
        off -= 0x400000
    return site + 4 + (off << 1)


def patch_marsh(rom):
    main = rom.loadArm9()
    section = main.sections[0]
    hook = bl_target(bytes(section.data), MENU_SITE, section.ramAddress)
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    data = bytearray(perm.data)
    at = hook - perm.ramAddress
    region = bytes(data[at:at + 40])
    needle = bytes((RAINBOW, 0x21))                                  # movs r1,#11
    assert region.count(needle) == 1, region.hex(' ')
    i = at + region.index(needle)
    data[i] = MARSH
    perm.data = data
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    hits = [i for i in range(0, len(section.data) - 6, 2) if struct.unpack_from('<3H', section.data, i)[::2] == (STD_BANK_FIRST_ID, STD_BANK_TEXT)]
    assert len(hits) == 1, hits
    bank_file = struct.unpack_from('<H', section.data, hits[0] + 2)[0]
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    old = bytearray(scripts.files[bank_file])
    needle = struct.pack('<3H', 294, RAINBOW, 0x800C)
    assert old.count(bytes(needle)) == 1, old.count(bytes(needle))
    j = old.index(bytes(needle))
    struct.pack_into('<H', old, j + 2, MARSH)
    scripts.files[bank_file] = bytes(old)
    rom.setFileByName('a/0/1/2', scripts.save())
    return dict(menu_hook=hex(hook), std_bank_file=bank_file, badge=MARSH)


def fix_granddaughter(rom):
    """0176 bug found while testing this tool: the granddaughter's "teeth already in the bag" test used opcode 126, which is TakeItem (it removed the teeth); the HaveItem opcode is 128."""
    d = bytes(rom.loadArm9().sections[0].data)
    sid = struct.unpack_from('<3H', d, TABLE + 483 * 24 + 6)[0]
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    raw = bytes(scripts.files[sid])
    needle = struct.pack('<4H', 126, 877, 1, 0x800C)
    assert raw.count(needle) == 1, raw.count(needle)
    scripts.files[sid] = raw.replace(needle, struct.pack('<4H', 128, 877, 1, 0x800C))
    rom.setFileByName('a/0/1/2', scripts.save())
    return dict(script_file=sid)


def patch(rom, source=None):
    return dict(marsh=patch_marsh(rom), granddaughter=fix_granddaughter(rom), sabrina=patch_sabrina(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
