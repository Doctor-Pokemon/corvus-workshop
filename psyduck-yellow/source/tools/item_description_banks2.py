"""Prototype 0220: descriptions for the EXTRA items (ids 537+) the owner carries, and no more wrong text for the rest (plan item 22, owner OK 2026-11-10 "sounds good"; research: ITEMS-RESEARCH.md, Serebii.net).
The engine (overlay 129, 0x23D8BE8) reads an item's description from a text bank chosen by id range: 537-638 -> bank 834 (row = id - 537), 639-775 -> 838 (id - 639), 776-1073 -> 842 (id - 776), 1074-1828 -> 846 (id - 1074),
1829-2684 -> 850 (id - 1829), 2685+ -> bank 221 (id - 2685, left alone: the Mega Stones and the Stellar Sandwich). These five banks held leftover MAP text, so every extra item showed Oak's lines, the bedroom hint, ... .
Fix: (1) the only map that still points at one of these banks, map 527 (header text id 846), gets its one row copied to a NEW bank appended to the text archive and its header repointed; (2) each of the five banks is rebuilt with one BLANK row per id of its range,
the researched descriptions filled in, and row 1 of bank 850 (id 1830, the project's Sandwich, written by sandwich_desc.py) kept. Items without a description now show nothing instead of unrelated text. No code or overlay changes.
Description lines use the engine's line break (0xE000 via '\n'); the bag window fits three lines.
Usage (from yellow-heartgold, PYTHONPATH=tools): item_description_banks2.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

# bank -> (first id, last id)
RANGES = {834: (537, 638), 838: (639, 775), 842: (776, 1073), 846: (1074, 1828), 850: (1829, 2684)}
MAP_527 = 527
KEEP = {(850, 1): 'the Sandwich (id 1830) description written by sandwich_desc.py'}

MEMORY_TYPES = {904: 'Fighting', 905: 'Flying', 906: 'Poison', 907: 'Ground', 908: 'Rock', 909: 'Bug', 910: 'Ghost', 911: 'Steel', 912: 'Fire',
                913: 'Water', 914: 'Grass', 915: 'Electric', 916: 'Psychic', 917: 'Ice', 918: 'Dragon', 919: 'Dark', 920: 'Fairy'}
TEXT = {
    539: "An item to be held by a Pokémon.\nIt halves the holder's weight for\nweight-based moves.",
    576: "A special Poké Ball. It gives a\nbonus when catching a Pokémon\nthat is asleep.",
    581: "A big nugget of pure gold. It can\nbe sold for a large amount of money.",
    646: "An item to be held by a Pokémon.\nIt makes certain Pokémon evolve\nwhen they are traded.",
    647: "An item to be held by a Pokémon.\nIt makes Spritzee evolve when it\nis traded.",
    651: "A flute with a melody that wakes\nsleeping Pokémon.",
    696: "A ring that lets a Pokémon holding\na Mega Stone Mega Evolve in battle.",
    847: "A cube that stores Zygarde Cells\nand Cores. It lets Zygarde change\nits Forme.",
    849: "A peculiar stone that makes certain\nspecies of Pokémon evolve. It is\nicy and cold.",
    851: "A special Poké Ball for catching\nUltra Beasts. It works very poorly\non other Pokémon.",
    874: "A scope that makes unseeable\nghosts visible.",
    878: "A key for the elevator in the\nTeam Rocket hideout.",
    1105: "A fossil piece. It can be combined\nwith a Drake or a Dino fossil.",
    1106: "A fossil piece. It can be combined\nwith a Drake or a Dino fossil.",
    1107: "A fossil piece. It can be combined\nwith a Bird or a Fish fossil.",
    1108: "A fossil piece. It can be combined\nwith a Bird or a Fish fossil.",
    1109: "An item to be held by Milcery.\nSpinning on the spot makes it evolve\ninto Alcremie.",
    1116: "A sweet apple. It makes Applin\nevolve into Appletun.",
    1117: "A tart apple. It makes Applin\nevolve into Flapple.",
    2402: "A syrupy apple. It makes Applin\nevolve into Dipplin.",
    1253: "A cracked pot. It makes Sinistea\nevolve.",
    1254: "A chipped pot. It makes Sinistea\nevolve.",
    1611: "A cord that makes Kadabra, Machoke,\nGraveler or Haunter evolve.",
    1777: "An item to be held by Dialga. It\nchanges its Forme and boosts Dragon\nand Steel moves by 20%.",
    1778: "An item to be held by Palkia. It\nchanges its Forme and boosts Dragon\nand Water moves by 20%.",
    1779: "An item to be held by Giratina. It\nchanges its Forme and boosts Dragon\nand Ghost moves by 20%.",
    1904: "A rare herb used for making\nSandwiches during Picnics.",
    1905: "A rare herb used for making\nSandwiches during Picnics.",
    1906: "A rare herb used for making\nSandwiches during Picnics.",
    1907: "A rare herb used for making\nSandwiches during Picnics.",
    1908: "A rare herb used for making\nSandwiches during Picnics.",
    2401: "An item to be held by a Pokémon.\nIt boosts the power of Fairy-type\nmoves by 20%.",
    2403: "A teacup that makes Poltchageist\nevolve into Sinistcha.",
    2404: "A teacup that makes Poltchageist\nevolve into Sinistcha.",
    2684: "A bun made to look like Canari's\nface. It restores 100 HP to a\nPokémon.",
}
for _id, _type in MEMORY_TYPES.items():
    TEXT[_id] = "An item to be held by Silvally.\nIt makes Silvally and its Multi-\nAttack move %s type." % _type


def row_for(text):
    return decode_messages(encode_text([text], PH))[1][0]


def patch(rom):
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    main = rom.loadArm9()
    s = main.sections[0]
    s.data = bytearray(s.data)
    # 1. map 527 keeps its text: copy bank 846 to a new bank and repoint the header (text id at +10)
    at = TABLE + MAP_527 * 24 + 10
    assert struct.unpack_from('<H', s.data, at)[0] == 846
    texts.files.append(bytes(texts.files[846]))
    new_id = len(texts.files) - 1
    struct.pack_into('<H', s.data, at, new_id)
    # no other native map may still use these banks
    users = [m for m in range(540) if struct.unpack_from('<H', s.data, TABLE + m * 24 + 10)[0] in RANGES]
    assert users == [], users
    placed = {}
    for bank, (lo, hi) in RANGES.items():
        key, old = decode_messages(texts.files[bank])
        rows = [[65535] for _ in range(hi - lo + 1)]
        for (b, r), why in KEEP.items():
            if b == bank:
                rows[r] = list(old[r])
        for item, text in TEXT.items():
            if lo <= item <= hi:
                rows[item - lo] = row_for(text)
                placed[item] = (bank, item - lo)
        texts.files[bank] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.arm9 = main.save(compress=True)
    return dict(map_527_text_bank=new_id, items_described=len(placed), missing=sorted(set(TEXT) - set(placed)))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
