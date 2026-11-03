"""Prototype 0163: both clerks sell in every Kanto Mart (owner order 2026-11-03: "Supplies down. Balls up.").
Until 0162 the Viridian, Cerulean and Pewter Marts had one working shop (the other clerk only said "speak to the clerk at the upper counter", wrong for Cerulean), and Saffron, Lavender and Fuchsia gave supplies/balls by script order, so Fuchsia was upside down against Vermilion.
Now, as in Vermilion (entry 0 at z6 supplies, entry 1 at z4 balls): the lower clerk (x2,z6) sells the supplies and the upper clerk (x2,z4) the Poke Balls, chosen by the clerk's position in the map's actor list.
 - a clerk whose script already has a shop call: that call is re-pointed to the new vendor;
 - a talking clerk: its script entry is re-pointed to the new vendor (the native talk script stays as dead code), or in the Viridian Mart, where the shop is closed until Oak's parcel is delivered (var 0x416A == 2), to a gate that jumps to the vendor when the parcel is delivered and falls back to the native talk script otherwise.
The hidden escort cashier's own shop call in the Viridian Mart is left alone. Vermilion (360) already has this layout.
Usage (from yellow-heartgold, PYTHONPATH=tools): mart_clerks.py <in.nds> <out.nds>"""
import json
import struct
import sys
from pathlib import Path
import ndspy.narc
import ndspy.rom
import johto_step3b as s3b
from kanto_mart_shared import vendor_script
from opening import events_decode
from viridian_tutorial import TABLE

CLERK_SPRITE, CLERK_X = 334, 2
LOWER_Z, UPPER_Z = 6, 4
VENDOR_AT = {LOWER_Z: 'supplies', UPPER_Z: 'balls'}
PRELUDE_BYTES = bytes.fromhex('4900dc0560006800')
GATES = {500: (0x416A, 2)}          # Viridian: the shop opens when Oak's parcel has been delivered


def clerks(rom, d, m):
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    found = {}
    for row in events_decode(events.files[struct.unpack_from('<H', d, TABLE + 24 * m + 16)[0]])[1]:
        _, sprite, _, _, flag, script, _ = struct.unpack_from('<7H', row, 0)
        x, z = struct.unpack_from('<2H', row, 24)
        if sprite == CLERK_SPRITE and x == CLERK_X and z in VENDOR_AT and flag == 0:
            assert z not in found, (m, z)
            found[z] = script
    assert set(found) == set(VENDOR_AT), (m, found)
    return found


def header(bank):
    """The script entry offsets, as read by script_dis.py (entries end at the 0x13FD marker)."""
    ptrs, i = [], 0
    while struct.unpack_from('<I', bank, i)[0] & 0xFFFF != 0xFD13:
        ptrs.append(i + 4 + struct.unpack_from('<I', bank, i)[0])
        i += 4
    return ptrs


def shop_sites(bank):
    sites = []
    for p in range(0, len(bank) - 6):
        if struct.unpack_from('<H', bank, p)[0] == 0x16:
            t = p + 6 + struct.unpack_from('<i', bank, p + 2)[0]
            if 8 <= t < len(bank) and bank[t - 8:t] == PRELUDE_BYTES:
                sites.append(p)
    return sites


def goto(op, at, target, cond=None):
    """A GoTo (0x16) or GoToIf (0x1C, cond) instruction placed at `at`, jumping to `target`."""
    if cond is None:
        return struct.pack('<Hi', op, target - (at + 6))
    return struct.pack('<HBi', op, cond, target - (at + 7))


def patch(rom, repo='.'):
    stages = json.loads((Path(repo) / 'data/kanto-mart-inventory.json').read_text())['verified_stages']
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    fid = rom.filenames.idOf('a/0/1/2')
    arc = ndspy.narc.NARC(rom.files[fid])
    report = {}
    for m in s3b.MARTS:
        found = clerks(rom, d, m)
        bank_id = struct.unpack_from('<H', d, TABLE + 24 * m + 6)[0]
        bank = bytearray(arc.files[bank_id])
        ptrs = header(bank)
        owner = {}
        for site in shop_sites(bank):
            n = max((ptr, k) for k, ptr in enumerate(ptrs, 1) if ptr <= site)[1]
            assert n not in owner, (m, n, 'two shop calls in one clerk script')
            owner[n] = site
        done = {}
        for z, vendor in VENDOR_AT.items():
            n = found[z]
            bank.extend(bytes(-len(bank) % 4))
            if n in owner:
                start = len(bank)
                assert start % 4 == 0, (m, start)
                bank.extend(vendor_script(stages, vendor, ()))
                bank[owner[n]:owner[n] + 6] = goto(0x16, owner[n], start + s3b.PRELUDE)
                done[z] = (n, 'shop call', owner[n])
            elif m in GATES:
                var, value = GATES[m]
                gate = len(bank)
                size = 6 + 7 + 6 + 1                               # CompareVarValue, GoToIf EQ, GoTo native, one pad byte: the shop reads its inline catalog with aligned loads, so every vendor script must start on a 4-byte boundary
                bank.extend(bytes(size))
                start = len(bank)
                assert start % 4 == 0, (m, start)
                bank.extend(vendor_script(stages, vendor, ()))
                bank[gate:gate + size] = struct.pack('<HHH', 0x11, var, value) + goto(0x1C, gate + 6, start, 1) + goto(0x16, gate + 13, ptrs[n - 1]) + b'\0'
                assert len(bank[gate:gate + size]) == size
                struct.pack_into('<I', bank, 4 * (n - 1), gate - (4 * (n - 1) + 4))
                done[z] = (n, 'gated entry', gate)
            else:
                start = len(bank)
                assert start % 4 == 0, (m, start)
                bank.extend(vendor_script(stages, vendor, ()))
                at = ptrs[n - 1]
                bank[at:at + 6] = goto(0x16, at, start)
                done[z] = (n, 'entry', at)
        arc.files[bank_id] = bytes(bank)
        report[m] = done
    rom.files[fid] = arc.save()
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
