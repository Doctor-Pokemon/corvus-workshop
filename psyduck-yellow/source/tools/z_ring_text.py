"""ROM 0266: the Z-Ring's bag description is the owner's line (2026-11-12): "A device which allows Z-Move usage."
Replaces the placeholder of z_ring.py (text bank 842, row 797 - 776). Only that row changes (line break after "allows" for the description box).
Usage (from yellow-heartgold, PYTHONPATH=tools): z_ring_text.py <in.nds> <out.nds>"""
import sys
import ndspy.narc
import ndspy.rom
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages

RING, DESC_BANK, DESC_BASE = 797, 842, 776
TEXT = "A device which allows\nZ-Move usage."


def patch(rom):
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[DESC_BANK])
    assert rows[RING - DESC_BASE] != [65535], 'the Z-Ring has no description yet'
    rows[RING - DESC_BASE] = decode_messages(encode_text([TEXT], PH))[1][0]
    texts.files[DESC_BANK] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    patch(rom)
    rom.saveToFile(sys.argv[2])
