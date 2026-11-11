"""Prototype 0233: the Mega Stone shop (owner 2026-11-11: the non-starter stones are bought in the Pokemon League lobby shop, unlocked by JOHTO badges, priced by tier).
Built from ROM 0232. The League lobby shop (map 300, tools/league_shop.py: base vendor before the Hall of Fame flag 0x964, an extended vendor with 29 evolution items after it) gets a NEW extended vendor
whose stock depends on the number of JOHTO badges (CheckBadge 0..7; Kanto badges never count): 0 badges = the 7 base items + the 29 evolution items, no stone; 1..8 badges add one more TIER of stones each (cumulative).
The tiers: the 75 non-starter Mega Stones sorted by the BASE STAT TOTAL of their Mega form (personal row of the form, ties by item id), split into 8 groups of 9-10 (lowest first). Starter stones (STARTER_STONES of
stone_check.py: 19 items) are never sold. Floettite is left out: its Mega form (Floette form 86) has no row in the ROM's form table, so evolving into it could not work (reported to the owner).
Prices (owner: "priced by stage"; the ladder is my proposal, constants below): tier 1..8 = 5000, 7500, 10000, 12500, 15000, 20000, 30000, 40000, written into the stones' item records (price field, u16 at offset 0, was 0), so
selling a stone back pays half. The shop's catalog is a fixed list per stage (it cannot depend on which Pokemon you own); a new gate replaces the old one's target, the old vendors stay as dead code.
Usage (from yellow-heartgold, PYTHONPATH=tools): stone_shop.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import kanto_mart_shared as shared
import league_shop as ls
import mega_shop
from johto_step3d import Asm
from kanto_mart_inline import inline_catalog
from opening import Script
from stone_check import STARTER_STONES
from viridian_tutorial import TABLE

PRICES = (5000, 7500, 10000, 12500, 15000, 20000, 30000, 40000)           # tier 1..8
LEFT_OUT = {'Floettite'}                                                  # the Mega form has no form-table row
FLOETTE_STONE = 2579                                                      # Floettite item id (entry species 720, form 86)


def johto_count():
    s = Script().emit(41, 0x8004, 0)
    for badge in range(0, 8):                                             # CheckBadge 0..7 = the Johto badges (8..15 are Kanto's)
        s.emit(294, badge, 0x800C).emit(39, 0x8004, 0x800C)
    return s.finish()


def vendor(catalogs):
    """Copy of kanto_mart_shared.vendor_script with the stage chosen by the JOHTO badge count (0..8)."""
    assert len(catalogs) == 9
    s = Script().emit(73, 1500).emit(96).emit(104).emit(20, 2011).emit(54)
    s.label('menu').emit(746).emit(749)
    s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
    for message, value in ((321, 0), (322, 1), (323, 2)):
        s.emit(751, message, 255, value)
    s.emit(752).compare(0x800C, 0).jump('buy', 1).compare(0x800C, 1).jump('sell', 1).jump('exit')
    s.label('buy')
    s.data.extend(johto_count())
    s.emit(42, 0x8005, 0x8004).emit(41, 0x8004, 30)
    for count in range(8):
        s.compare(0x8005, count).jump('stage%d' % count, 1)
    s.jump('stage8')
    for k, items in enumerate(catalogs):
        s.label('stage%d' % k).emit(276, 0x8004)
        s.data.extend(inline_catalog(items))
        s.jump('return')
    s.label('sell').emit(782).jump('return')
    s.label('return').emit(438, 3, 0x800C).emit(440, 0x800C, 6).emit(54).jump('menu')
    s.label('exit').emit(747).emit(438, 3, 0x800C).emit(440, 0x800C, 1).emit(50).emit(53).emit(97).emit(2)
    return s.finish()


def mega_totals(rom):
    """item id -> (species, form, base stat total of the Mega form or None) for the first 106 table entries (every non-starter stone is among them)."""
    ovs = rom.loadArm9Overlays()
    battle, perm = ovs[130], ovs[129]
    table = struct.unpack_from('<I', battle.data, mega_shop.TABLE_SITE - battle.ramAddress)[0]
    holder = battle if battle.ramAddress <= table < battle.ramAddress + len(battle.data) else perm
    at = table - holder.ramAddress
    t = ndspy.narc.NARC(rom.getFileByName('a/0/2/8'))
    forms = bytes(t.files[11])
    personal = ndspy.narc.NARC(rom.getFileByName('a/0/0/2'))
    out = {}
    for k in range(mega_shop.ENTRIES):
        e = struct.unpack_from('<I', holder.data, at + 4 * k)[0]
        species, item, form = e & 0xFFF, (e >> 12) & 0xFFF, e >> 24
        slot = struct.unpack_from('<H', forms, species * 64 + 2 * (form - 1))[0] & 0x7FFF if form <= 32 else 0       # a form number above 32 has no slot
        bst = sum(bytes(personal.files[slot])[:6]) if slot else None
        old = out.get(item)
        if old is None or (bst or 0) > (old[2] or 0):
            out[item] = (species, form, bst)
    return out


def tiers(rom):
    totals = mega_totals(rom)
    sold = {i: v for i, v in totals.items() if i not in STARTER_STONES}
    assert len(sold) == 76, len(sold)
    missing = [i for i, v in sold.items() if v[2] is None]
    assert missing == [FLOETTE_STONE], missing
    ranked = sorted((i for i in sold if i != FLOETTE_STONE), key=lambda i: (sold[i][2], i))
    n = len(ranked)
    cuts = [round(n * k / 8) for k in range(9)]
    return [ranked[cuts[k]:cuts[k + 1]] for k in range(8)], sold


def patch(rom, source=None):
    groups, sold = tiers(rom)
    assert sum(len(g) for g in groups) == 75
    shared.IDS.update({'MAX_POTION': 24, 'FULL_RESTORE': 23})
    base = [shared.IDS[name] for name in ls.BASE] + list(ls.EXTRA)
    catalogs = [list(base)]
    for k in range(8):
        catalogs.append(catalogs[-1] + groups[k])
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    fid = rom.filenames.idOf('a/0/1/2')
    arc = ndspy.narc.NARC(rom.files[fid])
    bank_id = struct.unpack_from('<H', d, TABLE + 24 * ls.MAP + 6)[0]
    bank = bytearray(arc.files[bank_id])
    gate_head = bytes([32, 0]) + struct.pack('<H', ls.HOF) + bytes([28, 0, 1])                    # CheckFlag HOF; GoToIf 1 ...
    assert bank.count(gate_head) == 1, 'league gate not found'
    gate = bank.index(gate_head)
    assert bank[gate + 11:gate + 13] == bytes([22, 0]), 'league gate layout changed'
    base_entry = gate + 11 + 6 + struct.unpack_from('<i', bank, gate + 13)[0]                     # the base vendor's entry (past its prelude)
    sites = [a for a in range(len(bank) - 6) if bank[a:a + 2] == bytes([22, 0]) and a + 6 + struct.unpack_from('<i', bank, a + 2)[0] == gate]
    assert len(sites) == 1, sites
    raw = vendor(catalogs)
    assert raw[:ls.PRELUDE] == bytes.fromhex('4900dc0560006800'), 'unexpected vendor prelude'
    bank.extend(bytes(-len(bank) % 4))
    new_vendor = len(bank)
    bank.extend(raw)
    bank.extend(bytes(-len(bank) % 4))
    gate2 = len(bank)
    g = Asm()
    g.check_flag(ls.HOF).jump(('abs', new_vendor + ls.PRELUDE), 1).jump(('abs', base_entry))
    bank.extend(g.build(gate2))
    struct.pack_into('<Hi', bank, sites[0], 22, gate2 - (sites[0] + 6))
    arc.files[bank_id] = bytes(bank)
    rom.files[fid] = arc.save()
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    priced = {}
    for tier, group in enumerate(groups):
        for i in group:
            rec = bytearray(items.files[i])
            assert struct.unpack_from('<H', rec, 0)[0] == 0, i
            struct.pack_into('<H', rec, 0, PRICES[tier])
            items.files[i] = bytes(rec)
            priced[i] = PRICES[tier]
    rom.setFileByName('a/0/1/7', items.save())
    return dict(bank=bank_id, site=sites[0], vendor=new_vendor, gate=gate2, bank_bytes=len(bank), tiers=[len(g) for g in groups], stones=len(priced), stock=[len(c) for c in catalogs])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
