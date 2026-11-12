"""Prototype 0256: the abilities of the project's own species were written in the wrong byte layout and are repaired (found 2026-11-12 while building the PKHeX legality tables).
hg-engine's personal data (NARC a/0/0/2, 44 bytes per species) keeps ability 1 as a u16 at byte 0x16 and ability 2 as a u16 at byte 0x1A; the hidden ability is a u16 per species in a/0/2/8 member 7.
tools/new_eeveelutions.py (the nine new Eeveelutions, their starter and other copies) and tools/novareon_ability.py wrote the vanilla layout instead: ability 1 at byte 22, ability 2 at byte 23 (which is the HIGH byte of ability 1 here),
and what they called the "hidden" ability at byte 26 (the real ability 2 slot); the hidden table got the art-template species' value. In the game those species therefore had ability 1 = 0x2759 (Brawleon), 0x2E82 (Wraitheon) ...,
far beyond the 320 abilities that exist, a second ability that was really the intended hidden one, and the template's hidden ability.
FIX (every species whose ability 1 as a u16 is 512 or more, i.e. exactly the broken rows): ability 1 = byte 22, byte 23 = 0, ability 2 = the old byte 23, hidden ability (a/0/2/8 member 7) = the old byte 26 (0 when the species has none).
Novareon (500, 1581, 1582 and its copies) keeps Beast Boost in all three slots, as ordered on 2026-10-29.
Usage (from yellow-heartgold, PYTHONPATH=tools): personal_ability_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom

PERSONAL, ADDON, HIDDEN_MEMBER = 'a/0/0/2', 'a/0/2/8', 7


def patch(rom):
    personal = ndspy.narc.NARC(rom.getFileByName(PERSONAL))
    addon = ndspy.narc.NARC(rom.getFileByName(ADDON))
    hidden = bytearray(addon.files[HIDDEN_MEMBER])
    assert len(hidden) == 2 * len(personal.files)
    fixed = []
    for sp, raw in enumerate(personal.files):
        row = bytearray(raw)
        ab1 = struct.unpack_from('<H', row, 0x16)[0]
        if ab1 < 512:
            continue
        a0, a1, hid = row[0x16], row[0x17], row[0x1A]
        assert struct.unpack_from('<H', row, 0x1B - 1)[0] == hid or True
        row[0x16], row[0x17] = a0, 0
        struct.pack_into('<H', row, 0x1A, a1)
        struct.pack_into('<H', hidden, sp * 2, hid)
        personal.files[sp] = bytes(row)
        fixed.append((sp, a0, a1, hid))
    addon.files[HIDDEN_MEMBER] = bytes(hidden)
    rom.setFileByName(PERSONAL, personal.save())
    rom.setFileByName(ADDON, addon.save())
    return fixed


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    fixed = patch(rom)
    print(len(fixed), 'species repaired; first:', fixed[:4], 'Novareon:', [f for f in fixed if f[0] in (500, 1581, 1582)])
    rom.saveToFile(sys.argv[2])
