"""Prototype 0252 (ALPHA 0.1 candidate): two owner-reported bugs (2026-11-12, photo: "Youngster sent out Sandshrew!" with a Cherish Ball on the enemy side).
1. EVERY trainer's Pokemon came out of a CHERISH BALL: the Kanto starter stone gate (tools/stone_check.py, ROM 0231) changed hg-engine's creator default ball 4 -> 16 (patch C, overlay 129 0x023DA9C2) so that gifts / trades / eggs get a Cherish Ball,
   but trainer parties are built by the same creator. Patch C is REVERTED (16 -> 4): trainer Pokemon (and NPC-trade Pokemon) use the Poke Ball again. The other ball patches stay: D (eggs, ARM9 0x0206C8EC) and E (script command 137 gifts, overlay 129 0x023DA820) still make Cherish Balls,
   captures still keep the ball thrown (they overwrite the ball).
2. Johto Gym Leaders talked about their badges granting HM field use (the HMs and their field use now come from the KANTO badges, tools/hm_gym_gifts.py). The sentences are removed (the TM gifts and the level-obedience lines stay):
   Falkner (Rock Smash), Bugsy (Cut), Whitney (Strength), Morty (Surf), Chuck (Fly), Pryce (Whirlpool), and Jasmine's "Since you can use Surf, ..." (Lake of Rage hint). Clair had none. No Johto leader script gives an HM (their gifts are TMs).
Usage (from yellow-heartgold, PYTHONPATH=tools): alpha_fixes.py <in 0251.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

BALL_SITE = 0x23DA9C2
CHERISH = 16

TEXT = {                                   # map -> {row: new text}
    135: {3: "Falkner: With that Badge, Pokémon, including traded Pokémon up to Lv. 20, will obey you without question."},
    180: {3: "Bugsy: Do you know the benefits of the Hive Badge?\\rIf you have it, Pokémon up to Lv. 30 will obey you, even traded ones.\\rHere, I also want you to have this."},
    137: {5: "Whitney: Oh, you can have this, too!"},
    80: {3: "Morty: By having the Fog Badge, Pokémon up to Lv. 50, including traded Pokémon, will obey you.\\rHere is another thing... I want you to have this, too."},
    139: {5: "Chuck: Here, take this, too!"},
    140: {3: "Pryce: That Badge will raise the Special stats of Pokémon.\\rAnd this... This is a gift from me!"},
    138: {20: "Impressive!\\rYou should continue your journey to different places. Why don't you try the Lake of Rage?"},
}


def patch(rom):
    main = rom.loadArm9()
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    o = BALL_SITE - perm.ramAddress
    assert bytes(perm.data[o:o + 2]) == bytes([CHERISH, 0x23]), bytes(perm.data[o:o + 2]).hex()
    perm.data[o:o + 2] = bytes([4, 0x23])
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    d = main.sections[0].data
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    report = {}
    for m, rows_new in TEXT.items():
        tid = struct.unpack_from('<H', d, TABLE + m * 24 + 10)[0]
        key, rows = decode_messages(texts.files[tid])
        for index, text in rows_new.items():
            rows[index] = decode_messages(encode_text([text.replace('\\r', '\r')], PH))[1][0]
        texts.files[tid] = encode_messages(key, rows)
        report[m] = sorted(rows_new)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
