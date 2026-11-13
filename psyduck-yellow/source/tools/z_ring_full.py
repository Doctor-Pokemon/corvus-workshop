"""ROM 0270: Mom's "your bag is full" line (Z-Ring gift) is HeartGold's default bag-full message (owner 2026-11-12: "If the bag is full, use the default 'Too bad. Your BAG is full.' message").
The default is row 27 of the standard text bank 40 (the message of std script 2009: "Too bad! ... BAG is full ..."). The two map text rows that z_ring.py wrote as my placeholder (Pallet house map 503, New Bark house map 63) are replaced by an exact copy of that row.
Usage (from yellow-heartgold, PYTHONPATH=tools): z_ring_full.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE
import z_ring

STD_TEXT_BANK, STD_ROW = 40, 27


def patch(rom):
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    _, std = decode_messages(texts.files[STD_TEXT_BANK])
    default = std[STD_ROW]
    mine = decode_messages(encode_text([z_ring.FULL_LINE], PH))[1][0]
    d = bytes(rom.loadArm9().sections[0].data)
    done = {}
    for map_id in (z_ring.PALLET_HOUSE, z_ring.NEW_BARK_HOUSE):
        tid = struct.unpack_from('<H', d, TABLE + 24 * map_id + 10)[0]
        key, rows = decode_messages(texts.files[tid])
        hits = [i for i, r in enumerate(rows) if r == mine]
        assert len(hits) == 1, (map_id, hits)
        rows[hits[0]] = list(default)
        texts.files[tid] = encode_messages(key, rows)
        done[map_id] = (tid, hits[0])
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    return done


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
