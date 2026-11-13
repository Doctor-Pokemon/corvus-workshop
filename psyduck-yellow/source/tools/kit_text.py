"""ROM 0272: the Field Kit's bag description names what it does now (owner "Yes", 2026-11-12). Old text (field_kit.py): "...CUT, ROCK SMASH and STRENGTH without a Pokemon." The Kit now also stands in for Surf, Waterfall, Whirlpool and Rock Climb (phase 2a); Fly moved to the Taxi Pager and Flash was dropped. Wording is mine (placeholder). Bank 846 row 54 (item 1128 - 1074) only.
Usage (from yellow-heartgold, PYTHONPATH=tools): kit_text.py <in.nds> <out.nds>"""
import sys
import ndspy.narc
import ndspy.rom
import field_kit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages

TEXT = "A Silph Co. kit. With the right\nBADGE, it stands in for most HM\nfield moves, no Pokémon needed."


def patch(rom):
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[846])
    at = field_kit.KIT - 1074
    assert rows[at] == decode_messages(encode_text([field_kit.DESCRIPTION], PH))[1][0], 'unexpected old text'
    rows[at] = decode_messages(encode_text([TEXT], PH))[1][0]
    texts.files[846] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    patch(rom)
    rom.saveToFile(sys.argv[2])
