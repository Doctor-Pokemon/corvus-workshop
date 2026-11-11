"""Prototype 0227 (replaces 0226): the Linking Cord works on the trade evolutions that lacked a cord entry, and Spritzee / Swirlix need their real held item (owner 2026-11-10).
FACTS (hg-engine data/Evolutions.c and src/individual/GetMonEvolutionInternal.c, then ROM tests): the cord evolves (a) "method 7 + item 1611" entries and (b) EVO_TRADE_ITEM (method 6) entries when the Pokemon HOLDS the item (tested on ROM 0224: Onix holding a Metal Coat, Poliwhirl holding a King's Rock). Method 5 (plain trade) entries need a separate cord entry:
Kadabra, Machoke, Graveler, Haunter, Boldore, Gurdurr already have one. Karrablast / Shelmet have "method 21, level up with the partner in the party" next to the trade entry, so they need nothing.
Changes: (1) Spritzee (id 732) and Swirlix (id 734) are plain trades in hg-engine, but in the games Spritzee needs a held Sachet (item 647) and Swirlix a held Whipped Dream (item 646): their method 5 entry becomes method 6 with that item (a real trade or the cord, with the item held).
(2) Every other method 5 entry without a "method 7, Linking Cord" entry (Phantump, Pumpkaboo and their forms) gets one in the first free slot; the trade entry stays. Nothing else changes (no item records, no other methods).
Evolution file a/0/3/4: 9 entries of (method u16, param u16, target u16) per species/form.
Usage (from yellow-heartgold, PYTHONPATH=tools): evolution_items.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom

LINKING_CORD = 1611
TRADE, TRADE_ITEM, STONE = 5, 6, 7
HELD_ITEM = {732: (733, 647), 734: (735, 646)}      # species id -> (target, required held item): Spritzee/Sachet, Swirlix/Whipped Dream


def patch(rom):
    evo = ndspy.narc.NARC(rom.getFileByName('a/0/3/4'))
    files = [bytearray(f) for f in evo.files]
    added, full, converted = [], [], []
    for s, f in enumerate(files):
        entries = [struct.unpack_from('<3H', f, 6 * k) for k in range(9)]
        for m, p, t in list(entries):
            if m == TRADE and s in HELD_ITEM:
                assert (p, t) == (0, HELD_ITEM[s][0]), (s, p, t)
                struct.pack_into('<3H', f, 6 * entries.index((m, p, t)), TRADE_ITEM, HELD_ITEM[s][1], t)
                converted.append((s, HELD_ITEM[s]))
                continue
            if m == TRADE:
                want = (STONE, LINKING_CORD, t)
            else:
                continue
            if want in entries:
                continue
            slot = next((k for k, e in enumerate(entries) if e[0] == 0), None)
            if slot is None:
                full.append((s, want))
                continue
            struct.pack_into('<3H', f, 6 * slot, *want)
            entries[slot] = want
            added.append((s, want))
    evo.files = [bytes(f) for f in files]
    rom.setFileByName('a/0/3/4', evo.save())
    return dict(added=len(added), no_free_slot=full, held_item=converted, sample=added[:6])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
