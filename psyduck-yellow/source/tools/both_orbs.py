"""Prototype 0249 (part): Mr. Pokemon gives BOTH orbs (owner 2026-11-12: "Have Mr. Pokemon gift the player with BOTH orbs, Blue Orb AND Red Orb, instead of just the Blue Orb").
The orb scene (map 143's script 3, run by the frame row 0x40F9 == 1) chose ONE orb by the game version (version 7 = HeartGold -> item 535 Blue Orb, else item 534 Red Orb) and then CallStd 2033 (the "put the ... in the KEY ITEMS Pocket" gift message).
The 45 bytes from `GetGameVersion` to the end of that CallStd are rewritten in place as: SetVar 0x8004 535; SetVar 0x8005 1; CallStd 2033; SetVar 0x8004 534; SetVar 0x8005 1; CallStd 2033; then a harmless `CompareVarToValue 0x800C 0; GoToIf EQ +0` (13 bytes of padding that falls through).
Both orbs arrive in the KEY ITEMS pocket, one message each. The scene's own text (intro, "That Orb has something to do with ... the Embedded Tower") is unchanged.
Text (owner: 'Should be "Those Orbs..."'): the scene's rows 23 and 26 (map 143's text bank) now say "give these to me" and "Those Orbs have something to do with ... the mystery of the Orbs" (rewritten with the project's encoder, wrapped at 30 characters).
Usage (from yellow-heartgold, PYTHONPATH=tools): both_orbs.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

HOUSE = 143
TEXT = {
    23: "The thing is... A friend of mine from Hoenn came over to give these to me.",
    26: "Those Orbs have something to do with the ancient ruins located past Cianwood City, called the Embedded Tower.\rBut only a handful of Trainers can reach there...\rThat's where you come in.\rProfessor Oak thinks highly of you, and you are the proud Champion after all.\rI'm sure you can solve the mystery of the Orbs and the secret of the ruins.",
}
OLD_HEAD = struct.pack('<2H3H', 495, 0x800C, 17, 0x800C, 7)                        # GetGameVersion 0x800C; CompareVarToValue 0x800C 7
BLUE, RED = 535, 534


def new_code():
    code = b''
    for item in (BLUE, RED):
        code += struct.pack('<3H', 41, 0x8004, item) + struct.pack('<3H', 41, 0x8005, 1) + struct.pack('<2H', 20, 2033)
    code += struct.pack('<3H', 17, 0x800C, 0) + struct.pack('<HBi', 28, 1, 0)       # padding: compare + a never-needed GoToIf to the next instruction
    return code


def patch(rom):
    main = rom.loadArm9()
    sid = struct.unpack_from('<H', main.sections[0].data, TABLE + HOUSE * 24 + 6)[0]
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    bank = bytearray(scripts.files[sid])
    assert bank.count(OLD_HEAD) == 1, bank.count(OLD_HEAD)
    at = bank.find(OLD_HEAD)
    old = bytes(bank[at:at + 45])
    # the original tail: GoToIf NE .., SetVar 0x8004 535, GoTo, SetVar 0x8004 534, SetVar 0x8005 1, CallStd 2033
    assert old[17:23] == struct.pack('<3H', 41, 0x8004, BLUE) and old[29:35] == struct.pack('<3H', 41, 0x8004, RED) and old[-4:] == struct.pack('<2H', 20, 2033), old.hex()
    code = new_code()
    assert len(code) == 45, len(code)
    bank[at:at + 45] = code
    scripts.files[sid] = bytes(bank)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    tid = struct.unpack_from('<H', main.sections[0].data, TABLE + HOUSE * 24 + 10)[0]
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[tid])
    assert len(rows) > 26
    for index, text in TEXT.items():
        rows[index] = decode_messages(encode_text([text], PH))[1][0]
    texts.files[tid] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    return dict(bank=sid, at=at, text_bank=tid)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
