"""Prototype 0202: the Silph Co. Card Key (item 876) becomes a real key item (same defect the Secret Key had, see secret_key_fix.py).
Item 876 (given by the Silph 5F ball, tested by every Silph door with HaveItem) had an ALL-ZERO item record and no icon, so the engine filed it in the ordinary Items pocket with a '?' icon (and it could be tossed).
It now gets the record and icon of the native Card Key (475: Key Items pocket, no toss, no use). Item 876 stays a separate id on purpose: the native Card Key 475 belongs to Johto's Radio Tower scripts and must not open Silph (or vice versa).
Saves that already hold item 876 in the Items pocket: HaveItem now looks in the Key Items pocket, so such a key would not be found (the owner's Silph progress was still clear when this was written).
For PKHeX: inject item id 876 (named 'Card Key', as is 475) into the KEY ITEMS pocket.
Usage (from yellow-heartgold, PYTHONPATH=tools): card_key_item.py <in.nds> <out.nds>"""
import sys
import ndspy.narc
import ndspy.rom

SILPH_KEY, NATIVE_KEY = 876, 475


def patch(rom, source=None):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    assert bytes(items.files[SILPH_KEY]) == bytes(36), 'the Silph Card Key already has a record'
    assert bytes(items.files[NATIVE_KEY]) != bytes(36), 'the native Card Key has no record'
    items.files[SILPH_KEY] = bytes(items.files[NATIVE_KEY])
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    for k in (2, 3):
        gfx.files[SILPH_KEY * 2 + k] = bytes(gfx.files[NATIVE_KEY * 2 + k])
    rom.setFileByName('a/0/1/8', gfx.save())
    return dict(item=SILPH_KEY, copied_from=NATIVE_KEY)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
