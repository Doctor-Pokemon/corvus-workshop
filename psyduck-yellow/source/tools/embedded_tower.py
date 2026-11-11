"""Prototype 0244: the FIRST (Kanto) Hall of Fame starts Mr. Pokemon's Orb chain (owner 2026-11-12: use the Embedded Tower for Kyogre / Groudon / Rayquaza; correction the same day: "we need this open after the Kanto League win... the FIRST Hall of Fame").
Built from ROM 0243. Findings (ROM 0243, scripts disassembled, then the chain walked in the emulator):
 - Hoenn progress variable 0x40F9 (16633): HeartGold's own chain. 1 = "Mr. Pokemon's Orb scene is due": entering map 143 (Mr. Pokemon's house) runs the scene (frame row 0x40F9 == 1 -> script 3:
   "A friend of mine from Hoenn came over to give this to me", the Blue Orb in HeartGold (item 535; item 534 Red Orb in SoulSilver), then 0x40F9 = 2). 2 = the Embedded Tower (Route 47, by Rock Climb) shows
   Kyogre in map 525 (Groudon in map 524 for SoulSilver; the version check at Route 47 script 1 and chamber scripts 133 / 134 is HeartGold's own), level 60 + 5 x Johto badges (the project's scaling), 4 = after the encounter,
   Oak's Jade Orb (item 536, script 755) then Rayquaza (map 526).
 - In the original the variable becomes 1 when the player takes a Kanto starter from Oak's lab (bank 740 scripts 8-10). The project replaced the starters (Psyduck / Togepi / Eevee), nothing sets it, and no script in the ROM
   gives items 534-536 outside the scene above. TESTED (emulator, fixture): variable 1 + entering the house -> the intro text and "put the Blue Orb in the KEY ITEMS Pocket"; variable 2 + Blue Orb in the bag, warp into map 525 ->
   Kyogre stands in the chamber (not shown: Rock Climb on Route 47, the fight itself, Rayquaza, Groudon).
 - This build: the league-ending script (bank 1309 script 1) writes HOFN = 1 on a KANTO win in one place (SetVar 0x413E 1, 6 bytes). It becomes `Call helper` (the same 6-byte hook pattern as tools/field_kit.py), where the
   helper does the same SetVar and then sets 0x40F9 = 1 if it was 0. So the first Hall of Fame makes Mr. Pokemon's house (Johto) hand out the orb on the next visit. Frame rows of map 143 run in order, so the orb scene precedes
   the house's first-visit scene (Mystery Egg errand, var 0x4107 == 0). OWNER 2026-11-12: "Scene order: after." So the header's two rows are SWAPPED (0x4107 == 0 -> script 2 before 0x40F9 == 1 -> script 3): the first visit
   runs the errand scene (it sets 0x4107 = 1), and the orb scene runs on the next entry. Saves made before this build are unsupported (the variable stays 0).
Not changed: the Johto win (HOFN = 2), the Route 47 warps (HeartGold: only Kyogre's door, Groudon's chamber stays hidden), Oak's Jade Orb chain.
Usage (from yellow-heartgold, PYTHONPATH=tools): embedded_tower.py <in 0243.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script
from parcel_quest import append_bank
from viridian_tutorial import TABLE

BANK = 1309
HOUSE = 143                                                   # Mr. Pokemon's house
ROW_ORB = struct.pack('<3H', 0x40F9, 1, 3)                    # frame row: Hoenn progress 1 -> script 3 (the Orb scene)
ROW_VISIT = struct.pack('<3H', 0x4107, 0, 2)                  # frame row: first visit -> script 2 (the Mystery Egg errand)
HOFN, HOENN = 0x413E, 0x40F9


def helper():
    s = Script()
    s.emit(41, HOFN, 1)                                     # the original statement
    s.compare(HOENN, 0).jump('done', 5)                     # already started: keep it
    s.emit(41, HOENN, 1)                                    # Mr. Pokemon's Orb scene is due
    s.label('done').emit(27)                                # Return
    return s.finish()


def patch(rom):
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    old = bytes(scripts.files[BANK])
    pattern = struct.pack('<3H', 41, HOFN, 1)
    sites, i = [], old.find(pattern)
    while i >= 0:
        sites.append(i)
        i = old.find(pattern, i + 1)
    assert len(sites) == 1, sites
    bank, count = append_bank(old, [helper()])
    bank = bytearray(bank)
    shift = 4
    target = count * 4 + 4 + struct.unpack_from('<I', bank, count * 4)[0]
    for f in sites:
        at = f + shift
        assert bytes(bank[at:at + 6]) == pattern
        bank[at:at + 6] = struct.pack('<Hi', 26, target - at - 6)
    scripts.files[BANK] = bytes(bank)
    main = rom.loadArm9()
    header = struct.unpack_from('<H', main.sections[0].data, TABLE + HOUSE * 24 + 8)[0]
    rows = bytes(scripts.files[header])
    assert rows.count(ROW_ORB + ROW_VISIT) == 1, rows.hex()                  # the orb row comes first in the original
    scripts.files[header] = rows.replace(ROW_ORB + ROW_VISIT, ROW_VISIT + ROW_ORB)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    return dict(bank=BANK, sites=sites, helper=count + 1, house_header=header)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
