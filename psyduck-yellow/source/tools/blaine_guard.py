"""Prototype 0192: the trainer outside Blaine's Cave Gym blocks the cave mouth until the first six Kanto badges are held (owner order 2026-11-08).
Owner text: "You don't even have 6 badges yet?" / "You're not ready to take on a master like Blaine yet." / "Scram, kid!". Once the six badges (HeartGold Kanto ids 8-13: Boulder, Cascade, Thunder, Rainbow, Soul, Marsh) are held, he stands where he stands now
(Route 20, map 92, actor 2 at (1129,503), the trainer the player must still beat on the way in). Owner order, same day: this guard REPLACES the Secret Key door check for now ("We'll go back to the Secret Key routine once we have rebuilt Cinnabar Island").
How: the cave mouth (1127,501 -> map 146) can be entered from (1127,502) (walking north) and from (1126,501) (walking east); both were tested live. Two blocker actors (sprite 346, his sprite) stand on those tiles; the original actor 2 gets a hide flag.
A map-entry script (level-script row type 2, map 92 had none) runs on every entry of Route 20 (also when walking out of the cave): all six CheckBadge 294 true -> blockers hidden (HB set), original shown (HO clear); otherwise the reverse.
HB/HO are 0xAAF/0xAB0: daily-range flags recomputed at every entry (grep of every script bank and actor list: unused). Blockers talk only (LockAll, FacePlayer, the three lines in three boxes).
Secret Key lock: map 146's six trigger rows (scripts 2-7 at (54..56,22..25), "The door is locked...") are removed from the event file; the scripts stay in the bank. RESTORE (later, with the rebuilt Cinnabar): put these rows back into the trigger group of map 146's events:
  02 00 36 00 17 00 01 00 01 00 00 00 00 00 00 00 / 03 00 36 00 18 00 ... / 04 00 38 00 17 00 ... / 05 00 38 00 18 00 ... / 06 00 37 00 16 00 ... / 07 00 37 00 19 00 ... (each "<Hhh5H": script, x, z, 1, 1, 0, 0, 0).
Usage (from yellow-heartgold, PYTHONPATH=tools): blaine_guard.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from opening import Script, actor, end

MAP, SPRITE, ORIGINAL = 92, 346, 2
SPOTS = ((1127, 502, 1), (1126, 501, 2))             # x, z, facing (1 = south, 2 = west)
HB, HO = 0xAAF, 0xAB0
BADGES = range(8, 14)
LINES = ["You don't even have 6 badges yet?", "You're not ready to take on a master like Blaine yet.", "Scram, kid!"]
SECRET_KEY_SCRIPTS = (2, 3, 4, 5, 6, 7)
CAVE_MAP = 146


def entry_script():
    s = Script()
    for b in BADGES:
        s.emit(294, b, 0x800C).compare(0x800C, 0).jump('locked', 1)
    s.emit(30, HB).emit(31, HO).emit(2)
    s.label('locked').emit(31, HB).emit(30, HO).emit(2)
    return s.finish()


def patch(rom, source=None):
    edit = MapEdit(rom, MAP)
    assert struct.unpack_from('<4B', bytes(edit.scripts.files[struct.unpack_from('<H', edit.d, edit.at + 8)[0]]), 0) == (0, 0, 0, 0), 'map 92 already has level scripts'
    orig = bytearray(edit.groups[1][ORIGINAL])
    assert struct.unpack_from('<2H', orig, 0) == (ORIGINAL, SPRITE) and struct.unpack_from('<2H', orig, 24) == (1129, 503), orig.hex(' ')
    assert struct.unpack_from('<H', orig, 8)[0] == 0, 'the trainer already has a hide flag'
    struct.pack_into('<H', orig, 8, HO)
    edit.groups[1][ORIGINAL] = bytes(orig)
    msgs = [edit.message(t) for t in LINES]
    talk = edit.script(lambda add: end(Script().emit(96).emit(104).msg(msgs[0]).msg(msgs[1]).msg(msgs[2])).finish())
    entry = edit.script(lambda add: entry_script())
    taken = {struct.unpack_from('<H', a, 0)[0] for a in edit.groups[1]}
    ids = []
    for k, (x, z, face) in enumerate(SPOTS):
        assert not any(struct.unpack_from('<2H', a, 24) == (x, z) for a in edit.groups[1]), 'tile already occupied'
        aid = max(taken) + 1 + k
        edit.groups[1].append(actor(aid, SPRITE, talk, x, z, HB, face))
        ids.append(aid)
    edit.scripts.files.append(b'\x02' + struct.pack('<I', entry) + b'\0\0\0')       # level-script header: one row (type 2, script id), terminator, padding
    struct.pack_into('<H', edit.d, edit.at + 8, len(edit.scripts.files) - 1)
    edit.save()
    cave = MapEdit(rom, CAVE_MAP)
    triggers = cave.groups[3]
    assert sorted(struct.unpack_from('<H', t, 0)[0] for t in triggers) == list(SECRET_KEY_SCRIPTS), [t.hex(' ') for t in triggers]
    cave.groups[3] = []
    cave.save()
    return dict(map=MAP, talk=talk, entry=entry, blockers=ids, hide_flags=(hex(HB), hex(HO)), removed_secret_key_triggers=len(triggers))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
