"""Prototype 0228: the Pokemon League lobby shop sells the evolution items nobody hands out (owner 2026-11-10: "Add them to the Pokemon League HQ Shop?", plan item 34).
The lobby is map 300 (script bank 1303). Its shop clerk is actor 4 at (16,19), local script 5: native shop call "CallStd 2011; cmd 0x36; SetVar 0x8004 13; CallStd 0x804" (mart 13 = HeartGold's Indigo Plateau stock: Ultra Ball, Max Repel, Hyper Potion, Max Potion, Full Restore, Revive, Full Heal).
The two attendants at (3,13) and (19,13) are the Union Room / Colosseum desks, not the shop. Same method as johto_step3b.py: the 6-byte greeting+command at the site becomes a GoTo into script code appended to the bank (the native tail stays as dead code).
The new code is a gate: Hall of Fame flag 0x964 clear -> the vendor with the original seven items; set -> the same vendor plus the 29 items below (the owner's "no source found" list). Vendors are kanto_mart_shared.vendor_script (menu with Buy / Sell / See ya, native sell, inline catalog hook already in the ROM); prices are the items' own records. The two Scrolls (1857/1858, Kubfu's evolution items) were Key Items with no use and price 0: their records become copies of the Fire Stone's (items pocket, usable on a Pokemon, price 3000).
Usage (from yellow-heartgold, PYTHONPATH=tools): league_shop.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import kanto_mart_shared as shared
from johto_step3d import Asm
from viridian_tutorial import TABLE

MAP, MART_ID, HOF = 300, 13, 0x964
GREETING = bytes([0x14, 0, 0xDB, 7])
PRELUDE = 8                                           # PlaySE 1500 + LockAll + FacePlayer: the native script has done them
BASE = ('ULTRA_BALL', 'MAX_REPEL', 'HYPER_POTION', 'MAX_POTION', 'FULL_RESTORE', 'REVIVE', 'FULL_HEAL')
EXTRA = (82, 84, 83, 85, 107, 108, 109, 849,           # Fire, Water, Thunder, Leaf, Shiny, Dusk, Dawn, Ice Stone
         321, 324, 325, 537,                           # Protector, Dubious Disc, Reaper Cloth, Prism Scale
         646, 647, 1611,                               # Whipped Dream, Sachet, Linking Cord
         1116, 1117, 2402, 1253, 1254,                 # Sweet / Tart / Syrupy Apple, Cracked / Chipped Pot
         1582, 1592, 1691, 1692,                       # Galarica Cuff / Wreath, Black Augurite, Peat Block
         1857, 1858, 1861, 2344, 2482)                 # Scroll of Darkness / Waters, Malicious / Auspicious Armor, Metal Alloy


SCROLLS, FIRE_STONE = (1857, 1858), 82


def stages():
    return [{'badges': n, 'v': list(BASE)} for n in range(9)]


def patch(rom):
    shared.IDS.update({'MAX_POTION': 24, 'FULL_RESTORE': 23})
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    fid = rom.filenames.idOf('a/0/1/2')
    arc = ndspy.narc.NARC(rom.files[fid])
    bank_id = struct.unpack_from('<H', d, TABLE + 24 * MAP + 6)[0]
    bank = bytearray(arc.files[bank_id])
    sites = []
    at = bank.find(GREETING)
    while at >= 0:
        if struct.unpack_from('<H', bank, at + 4)[0] in (0x32, 0x36) and struct.unpack_from('<3H', bank, at + 6) == (41, 0x8004, MART_ID):
            sites.append(at)
        at = bank.find(GREETING, at + 1)
    assert len(sites) == 1, sites
    site = sites[0]
    out = {}
    for name, extra in (('base', ()), ('extended', EXTRA)):
        raw = shared.vendor_script(stages(), 'v', extra)
        assert raw[:PRELUDE] == bytes.fromhex('4900dc0560006800'), 'unexpected vendor prelude'
        bank.extend(bytes(-len(bank) % 4))
        out[name] = len(bank)
        bank.extend(raw)
    bank.extend(bytes(-len(bank) % 4))
    gate = len(bank)
    g = Asm()
    g.check_flag(HOF).jump(('abs', out['extended'] + PRELUDE), 1).jump(('abs', out['base'] + PRELUDE))
    bank.extend(g.build(gate))
    bank[site:site + 6] = struct.pack('<Hi', 0x16, gate - (site + 6))
    arc.files[bank_id] = bytes(bank)
    rom.files[fid] = arc.save()
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    records = [bytearray(f) for f in items.files]
    for i in SCROLLS:                                  # the two Scrolls were Key Items without a use: make them stone-type items (Fire Stone record, price 3000) so Kubfu can use them
        records[i][:] = records[FIRE_STONE]
    items.files = [bytes(f) for f in records]
    rom.setFileByName('a/0/1/7', items.save())
    return dict(map=MAP, bank=bank_id, site=site, base=out['base'], extended=out['extended'], gate=gate, extra_items=len(EXTRA), bank_bytes=len(bank))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
