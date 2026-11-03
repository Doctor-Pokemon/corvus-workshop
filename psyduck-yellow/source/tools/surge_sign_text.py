"""Prototype 0165: the Vermilion Gym sign says "The Lightning Unovan" instead of "The Lightning American" (owner order 2026-11-03, modern-lore wording).
The sign is message 11 of Vermilion City's text bank (a/0/2/7 file 918, used by map 54). The same text also sits in file 483, which no map header uses (an old copy); both are changed so no path can show the old wording.
Usage (from yellow-heartgold, PYTHONPATH=tools): surge_sign_text.py <in.nds> <out.nds>"""
import sys
import ndspy.narc
import ndspy.rom
from prototype import decode_messages, encode_messages

FILES, MESSAGE = (918, 483), 11
AMERICAN = [299, 337, 329, 342, 333, 327, 325, 338]      # "American"
UNOVAN = [319, 338, 339, 347, 325, 338]                  # "Unovan"
PREFIX = [310, 333, 331, 332, 344, 338, 333, 338, 331, 478]   # "Lightning "


def patch(rom):
    arc = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    for fi in FILES:
        key, messages = decode_messages(bytes(arc.files[fi]))
        m = messages[MESSAGE]
        needle = PREFIX + AMERICAN
        hits = [i for i in range(len(m) - len(needle) + 1) if m[i:i + len(needle)] == needle]
        assert len(hits) == 1, (fi, hits)
        at = hits[0] + len(PREFIX)
        messages[MESSAGE] = m[:at] + UNOVAN + m[at + len(AMERICAN):]
        arc.files[fi] = encode_messages(key, messages)
    rom.files[rom.filenames.idOf('a/0/2/7')] = arc.save()
    return dict(files=FILES, message=MESSAGE)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
