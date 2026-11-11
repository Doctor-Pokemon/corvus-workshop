"""Viridian City's gym guard lets you in once you hold the seven other Kanto badges (owner report 2026-11-08: the guard stayed at the gym door after all seven badges).
Found: the guard (map 50, actor 0, sprite 330, script 4, standing on the only tile in front of the door at (1045,239)->the rebuilt Viridian Gym, map 579) ran a hard-coded placeholder: "The GYM is closed right now." with no badge test, no flag and no
hide flag, so no number of badges could ever open the gym.
Owner rule (2026-11-08): the gym is the finale, so it also needs the Rocket Hideout run (Giovanni's Silph Scope), the Pokemon Tower (Mr. Fuji's Poke Flute) and the Silph Co. takeover (Giovanni beaten) done first: flags 0xA6D, 0xA73, 0xA68.
Fix (a copy of the script, nothing else changes): talk to him; if the player has the three story flags AND ALL of the Boulder, Cascade, Thunder, Rainbow, Soul, Marsh and Volcano Badges (HeartGold Kanto badge ids 8-14: CheckBadge 294) he steps aside for good: SetFlag 0x95A + HidePerson, and the
actor's hide flag becomes 0x95A, so he stays away after the map reloads. Otherwise he still says the existing line (message 7, "The GYM is closed right now."). No new dialogue.
Flag 0x95A is a former Safari Zone item-ball flag; the Safari Zone is unreachable (dropped), the flag is referenced only by the Safari maps' own script bank/actors (checked on the owner's ROM).
Usage (from yellow-heartgold, PYTHONPATH=tools): viridian_guard.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, end, events_decode, events_encode, script_bank
from parcel_quest import split_bank
from viridian_tutorial import TABLE

MAP, NPC, GUARD_SCRIPT, HIDE = 50, 0, 4, 0x95A
BADGES = range(8, 15)                       # Boulder, Cascade, Thunder, Rainbow, Soul, Marsh, Volcano
STORY = (0xA6D, 0xA73, 0xA68)               # Rocket Hideout done (Giovanni gave the Silph Scope), Pokemon Tower done (Mr. Fuji gave the Poke Flute), Silph Co. done (Giovanni beaten): rocket_hideout.GIOVANNI_HIDE, tower_scenes.FUJI_FLAG, silph.GIOVANNI_DONE
CLOSED_MESSAGE = 7                          # the existing "The GYM is closed right now."


def guard_script():
    s = Script().emit(96).emit(104)
    for n, f in enumerate(STORY):                 # owner rule (2026-11-08): the finale needs the Hideout, the Tower and the Silph Co. takeover first
        s.emit(32, f).jump('story%d' % n, 1).jump('closed').label('story%d' % n)
    for b in BADGES:
        s.emit(294, b, 0x800C).compare(0x800C, 0).jump('closed', 1)
    s.emit(30, HIDE).emit(101, NPC)
    end(s)
    s.label('closed').msg(CLOSED_MESSAGE)
    end(s)
    return s.finish()


def patch(rom):
    main = rom.loadArm9()
    dd = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + MAP * 24
    sid = struct.unpack_from('<H', dd, rec + 6)[0]
    eid = struct.unpack_from('<H', dd, rec + 16)[0]
    assert not [m for m in range(540) if m != MAP and struct.unpack_from('<H', dd, TABLE + m * 24 + 16)[0] == eid], 'event file shared'
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    groups = events_decode(events.files[eid])
    row = struct.unpack_from('<7H', groups[1][NPC], 0)
    x, z = struct.unpack_from('<2H', groups[1][NPC], 24)
    assert row[1] == 330 and row[5] == GUARD_SCRIPT and row[4] == 0 and (x, z) == (1045, 240), (row, x, z)
    bank = split_bank(scripts.files[sid])
    old = bank[GUARD_SCRIPT - 1]
    assert old.hex(' ').startswith('60 00 68 00 be 00 00 bf 00 01 2d 00 07'), old.hex(' ')      # the placeholder: LockAll, FacePlayer, names, message 7
    idx = len(bank) + 1
    bank.append(guard_script())
    a = bytearray(groups[1][NPC])
    struct.pack_into('<H', a, 10, idx)
    struct.pack_into('<H', a, 8, HIDE)
    groups[1][NPC] = bytes(a)
    scripts.files.append(script_bank(bank))
    events.files.append(events_encode(groups))
    struct.pack_into('<H', dd, rec + 6, len(scripts.files) - 1)
    struct.pack_into('<H', dd, rec + 16, len(events.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.arm9 = main.save(compress=True)
    return dict(map=MAP, script=idx, hide_flag=hex(HIDE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
