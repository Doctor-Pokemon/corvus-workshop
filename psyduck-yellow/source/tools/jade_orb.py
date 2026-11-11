"""Prototype 0253: the JADE ORB is obtainable again (owner 2026-11-12: "go ahead and look into that Jade Orb investigation"; the owner's lead: in vanilla you show Prof. Oak a Groudon AND a Kyogre caught within the Embedded Tower, Serebii).
FINDINGS: (1) Oak's Jade Orb scene is script 1 of script bank 740 (item 532 Jade Orb, then the Hoenn progress variable 0x40F9 = 5), and NO map uses bank 740 any more: this project's Oak lives in the Pokemon Lab (map 505), whose scripts do not contain it, so the Jade Orb was UNOBTAINABLE.
(2) Even if reachable, the original check (script command 836 CheckKyogreGroudonInParty, ARM code in overlay 1 at 0x02202834) wants a KYOGRE whose Met Game is 7 (HeartGold) AND a GROUDON whose Met Game is 8 (SoulSilver) in the party, i.e. a trade between the two game versions; every Pokemon caught or given in this ROM carries Met Game 254 (tools/stone_check.py), and HeartGold hides Groudon's chamber anyway.
(3) The Jade Orb only gates the Rayquaza chamber through the progress variable (Oak sets 0x40F9 = 5; the Route 47 door script then opens the Rayquaza chamber).
FIX: Oak's two actors in the Pokemon Lab (map 505, script 1) get a new front script. When the Hoenn progress variable is 4 (the Kyogre chamber was done), KYOGRE and GROUDON are both registered as CAUGHT in the Pokedex (CheckMonCaught, command 336; both only come from the Embedded Tower here: Kyogre's chamber and the Red Orb encounter) and the Jade Orb is not owned yet:
Oak says so, gives the Jade Orb (the standard item-gift message), the variable becomes 5. Otherwise the new script jumps to Oak's original script 1 unchanged. The party/Met Game requirement of the original is replaced by the Pokedex, the same rule the whole legendary system uses.
Usage (from yellow-heartgold, PYTHONPATH=tools): jade_orb.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from legend_spots import script_start
from map_edit import MapEdit
from opening import Script

LAB, OAK_SPRITE, OAK_SCRIPT = 505, 366, 1
PROGRESS, JADE, KYOGRE, GROUDON = 0x40F9, 532, 382, 383
TEXT = dict(
    thanks="{PLAYER}! I have heard the most amazing news from the Embedded Tower. You have both KYOGRE and GROUDON in your Pokédex!\\rRemarkable! Please take this. It is the Jade Orb. They say it calls the third legend of that ancient place!",
    after="Show that orb to the tower, {PLAYER}. I am sure RAYQUAZA will answer.",
    full="Your Bag is full, {PLAYER}. Make some room and come back for the Jade Orb.",
)


def front_script(msg, original_id):
    s = Script()
    s.compare(PROGRESS, 4).jump('orig', 5)
    s.emit(336, KYOGRE, 0x800C).compare(0x800C, 1).jump('orig', 5)
    s.emit(336, GROUDON, 0x800C).compare(0x800C, 1).jump('orig', 5)
    s.emit(96).emit(104)                                                        # LockAll, FacePlayer
    s.emit(41, 0x8004, JADE).emit(41, 0x8005, 1)
    s.emit(127, 0x8004, 0x8005, 0x800C).compare(0x800C, 0).jump("full", 1)      # HasSpaceForItem
    s.msg(msg['thanks'])
    s.emit(20, 2033)                                                            # CallStd 2033: "... put the Jade Orb in the KEY ITEMS Pocket"
    s.emit(41, PROGRESS, 5)
    s.msg(msg['after'])
    s.emit(97).emit(2)
    s.label('full')
    s.msg(msg['full'])
    s.emit(97).emit(2)
    s.label('orig')
    s.emit(22)
    s.data.extend(bytes(4))                                                     # GoTo Oak's original script (patched by the caller)
    return s


def patch(rom):
    e = MapEdit(rom, LAB)
    msg = {k: e.message(v.replace('\\r', '\r')) for k, v in TEXT.items()}
    s = front_script(msg, OAK_SCRIPT)
    code = s.finish()
    new_id = e.script(lambda add: code)
    fix = script_start(e.bank, new_id) + len(code) - 4
    struct.pack_into('<i', e.bank, fix, script_start(e.bank, OAK_SCRIPT) - (fix + 4))
    changed = []
    for i, a in enumerate(e.groups[1]):
        if struct.unpack_from('<H', a, 2)[0] == OAK_SPRITE and struct.unpack_from('<H', a, 10)[0] == OAK_SCRIPT:
            rec = bytearray(a)
            struct.pack_into('<H', rec, 10, new_id)
            e.groups[1][i] = bytes(rec)
            changed.append(i)
    assert changed, 'no Oak actor found'
    e.save()
    return dict(map=LAB, script=new_id, actors=changed)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
