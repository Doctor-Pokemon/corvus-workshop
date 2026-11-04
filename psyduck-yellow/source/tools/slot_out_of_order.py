"""Prototype 0179: the Celadon Game Corner's slot machines say they are out of order (owner order 2026-11-04).
Why: pressing A at a slot machine in the Game Corner (map 381) hangs the game (blank dialogue, then a Data Abort on leaving: found 2026-11-03, bisected to a regression between ROM 0040 and 0105; the slot minigame is final polish).
The owner chose a message instead of a repair. The map's 15 machine bg events (x 3/4/16/17: script ids 10-24 of bank file 1238; the two poster events with script 9 stay) now run one new script that shows
"This machine is out of order." and ends; the old machine scripts stay in the bank, unused. No flag or variable.
Usage (from yellow-heartgold, PYTHONPATH=tools): slot_out_of_order.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, end, encode_text, events_decode, events_encode, script_bank
from parcel_quest import PH, split_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

MAP = 381
MACHINE_SCRIPTS = range(10, 25)
TEXT = 'This machine is out of order.'


def patch(rom, source=None):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    bank = split_bank(scripts.files[sid])
    key, lines = decode_messages(texts.files[tid])
    idx = len(bank) + 1
    msg = len(lines)
    lines.extend(decode_messages(encode_text([TEXT], PH))[1])
    s = Script().emit(73, 1500).emit(96).msg(msg)          # same opening as the map's poster scripts
    end(s)
    bank.append(s.finish())
    changed = []
    for i, raw in enumerate(groups[0]):
        script = struct.unpack_from('<I', raw, 0)[0]
        if script in MACHINE_SCRIPTS:
            row = bytearray(raw)
            struct.pack_into('<I', row, 0, idx)
            groups[0][i] = bytes(row)
            changed.append(script)
    assert len(changed) == 15 and sorted(changed) == list(MACHINE_SCRIPTS), sorted(changed)
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
    return dict(map=MAP, script=idx, message=msg, machines=len(changed))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
