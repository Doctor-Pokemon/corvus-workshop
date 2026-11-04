"""Prototype 0181: the Warden's full-bag dead end (owner order 2026-11-04: "mark the teeth as returned as soon as he takes them").
Bug: in his first-return branch he TAKES the GOLD TEETH (opcode 126) and only then checks that the NUGGET fits; with a full bag the "no room" line played, the teeth were gone and flag 0xA6C (teeth returned) was never set,
so he only mumbled from then on. Fix: that branch's bag-full jump now goes to a small trailer that sets flag 0xA6C and then continues to the same "no room" line. Next time he is spoken to he is in the "helped" branch and gives the
daily NUGGET (owner's line) when the bag has room. The first-return lines, the daily flag (0xAAC) and every other path are unchanged. Done as a copy of his script with one jump retargeted (no bytes inserted).
Usage (from yellow-heartgold, PYTHONPATH=tools): warden_fullbag.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode, script_bank
from parcel_quest import split_bank
from viridian_tutorial import TABLE

MAP, WARDEN_GIVEN, NUGGET = 481, 0xA6C, 92


def patch(rom, source=None):
    main = rom.loadArm9()
    dd = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid = struct.unpack_from('<H', dd, rec + 6)[0]
    eid = struct.unpack_from('<H', dd, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    i = max(range(len(groups[1])), key=lambda k: struct.unpack_from('<H', groups[1][k], 10)[0])
    old = struct.unpack_from('<H', groups[1][i], 10)[0]
    bank = split_bank(scripts.files[sid])
    body = bytearray(bank[old - 1])
    needle = struct.pack('<4H', 125, NUGGET, 1, 0x800C)
    at = body.index(needle)                                       # the first one: the first-return branch (the daily branch has the second)
    assert body.count(needle) == 2, body.count(needle)
    c = at + 8
    assert bytes(body[c:c + 6]) == struct.pack('<3H', 17, 0x800C, 0), bytes(body[c:c + 6]).hex(' ')
    j = c + 6
    assert body[j:j + 3] == struct.pack('<HB', 28, 1), bytes(body[j:j + 3]).hex(' ')
    rel = struct.unpack_from('<i', body, j + 3)[0]
    full = j + 7 + rel                                             # the existing "no room" label
    trailer = len(body)
    struct.pack_into('<i', body, j + 3, trailer - (j + 7))
    body.extend(struct.pack('<HH', 30, WARDEN_GIVEN))             # SetFlag 0xA6C
    here = len(body) + 6
    body.extend(struct.pack('<Hi', 22, full - here))              # GoTo the old "no room" label
    idx = len(bank) + 1
    bank.append(bytes(body))
    row = bytearray(groups[1][i])
    struct.pack_into('<H', row, 10, idx)
    groups[1][i] = bytes(row)
    scripts.files.append(script_bank(bank))
    events.files.append(events_encode(groups))
    struct.pack_into('<H', dd, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', dd, rec + 16, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(map=MAP, actor=i, script=idx)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
