"""Prototype 0199: Cinnabar Island visual polish, applied IN PLACE to a ROM that already has the rebuilt island (cinnabar_terrain.patch + cinnabar_town) (owner 2026-11-08: "start on the visual polish").
Re-renders the island's terrain model from cinnabar_town.build_layout() (which now also lists TREES, FLOWERS, FLOWERS2) and replaces the chunk's model and permission bytes and the area's texture bank in their existing files:
 - shoreline foam: HeartGold's own wave tile (swave_un: sand, white wave, blue) on every water tile next to a beach tile, its sand edge toward the beach;
 - flower beds: HeartGold's flower01/flower02 tiles over the grass with colour 0 see-through (the earlier build could not use them: colour 0 is grey);
 - trees: a round-canopy tree drawn here, two crossed upright quads per tree, blocked tiles ('T').
Buildings, doors, warps, events and the rest of the ROM are untouched (the building entries are rewritten identically).
Usage (from yellow-heartgold, PYTHONPATH=tools): cinnabar_polish.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import cinnabar_terrain as ct
import cinnabar_town as town
from viridian_tutorial import TABLE


def patch(rom, source=None):
    layout, perm, blds, doors = town.build_layout()
    main = rom.loadArm9()
    d = main.sections[0].data
    area_id = d[TABLE + 57 * 24 + 1]
    mats = ndspy.narc.NARC(rom.getFileByName('a/0/4/1'))
    lands = ndspy.narc.NARC(rom.getFileByName('a/0/6/5'))
    areas = ndspy.narc.NARC(rom.getFileByName('a/0/4/2'))
    banks = ndspy.narc.NARC(rom.getFileByName('a/0/4/4'))
    m0 = bytes(mats.files[0])
    w, h, hd, ht, n = m0[:5]
    at = 5 + n + w * h * (2 * hd + ht) + 2 * (ct.CELL[1] * w + ct.CELL[0])
    cur = struct.unpack_from('<H', m0, at)[0]
    assert cur != 205, 'the island has not been rebuilt in this ROM'
    bdhc = ct.build_bdhc()
    model, bank = ct.build_model(rom, layout)
    bank_id = struct.unpack_from('<H', areas.files[area_id], 2)[0]
    assert bank_id > 18 and area_id > 18, (area_id, bank_id)
    lands.files[cur] = ct.pack(perm, blds, model, bdhc)
    # the neighbour north of the island (cell (32,14)): its sea tiles under NORTH_EXT become walkable ground, so the new land can be walked on up to the plateau's foot
    nat = 5 + n + w * h * (2 * hd + ht) + 2 * ((ct.CELL[1] - 1) * w + ct.CELL[0])
    north = struct.unpack_from('<H', m0, nat)[0]
    nl = bytearray(lands.files[north])
    off = 16 + (4 + struct.unpack_from('<H', nl, 18)[0] if nl[16:18] == b'\x34\x12' else 0)
    ps = struct.unpack_from('<I', nl, 0)[0]
    assert ps == 2048, ps
    for lx, lz, c in ct.NORTH_EXT:
        at2 = off + ((32 + lz) * 32 + lx) * 2
        assert nl[at2] in (0x15, 0) and nl[at2 + 1] & 0x80 == 0, (lx, lz, nl[at2:at2 + 2].hex())
        nl[at2:at2 + 2] = bytes([0, 0])
    lands.files[north] = bytes(nl)
    banks.files[bank_id] = bank
    rom.setFileByName('a/0/6/5', lands.save())
    rom.setFileByName('a/0/4/4', banks.save())
    return dict(land=cur, area=area_id, bank=bank_id, north_chunk=north, land_bytes=len(lands.files[cur]), trees=len(town.TREES), flowers=len(town.FLOWERS) + len(town.FLOWERS2))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
