"""Cinnabar Island rebuilt, phase B: buildings on the phase A terrain (owner order 2026-11-08).
Layout (Yellow: Mansion top left, Gym top right, Lab left, Pokemon Center bottom centre, Mart bottom right) with HeartGold's own building models from the Celadon building group 14 (it has the Pokemon Center 40, Mart 39, gym 245 + gym_door 16, mansion 244, houses 236-238, p_door 15, wk_door1 24, boards 29-34),
so the island's area uses group 14 (textures AND model set). Door rules measured on vanilla Kanto towns (Pallet, Celadon): the warp tile is the door tile in front of the building; p_door sits at (wx + 0.5, wz + 0.61 (Center, Mart) or 0.07 (Mansion)), gym_door at (wx + 0.5, wz + 0.4), wk_door1 at (wx + 1.12, wz + 0.12);
the building origin is (wx + 0.5, wz - 1) (Center, Mart, Gym), (wx - 1, wz - 1.19) (Mansion), (wx + 1, wz - 1) (house). Door tile perm = behaviour 0x69 + blocked flag 0x80; footprints are blocked (rules from Pallet's blocked tiles).
All positions below are tiles inside the chunk (global = 1024 + x, 480 + z)."""
import struct
import sys
import ndspy.rom
import cinnabar_terrain as ct

GROUP = 14
# name: (model, door model, door kind, warp tile (x, z), footprint x range, footprint z range relative to floor(origin))
BUILDINGS = {
    'center': dict(model=40, door=15, kind='pc', warp=(15, 22), fx=(-3, 3), fz=(-4, 1)),
    'mart': dict(model=39, door=15, kind='pc', warp=(23, 22), fx=(-2, 3), fz=(-3, 1)),
    'gym': dict(model=245, door=16, kind='gym', warp=(24, 12), fx=(-3, 3), fz=(-4, 1)),
    'mansion': dict(model=244, door=15, kind='mansion', warp=(10, 12), fx=(-3, 3), fz=(-5, 1)),
    'lab': dict(model=238, door=24, kind='house', warp=(7, 21), fx=(-3, 2), fz=(-5, 1)),
}
SIGNS = {'town': (11, 16), 'center': (17, 23), 'mart': (25, 23), 'lab': (9, 22), 'gym': (22, 13)}      # sign tiles (a board model stands on each, the tile is blocked)
BOARD = 31
DOOR_Y = {'pc': 0.12, 'gym': 0.0, 'mansion': 0.12, 'house': 0.19}


def WORLD_DOOR(t):
    return 1024 + t[0], 480 + t[1]


def origin_and_door(b):
    wx, wz = b['warp']
    k = b['kind']
    if k == 'pc':
        return (wx + 0.5, wz - 1.0), (wx + 0.5, wz + 0.61)
    if k == 'gym':
        return (wx + 0.5, wz - 1.0), (wx + 0.5, wz + 0.4)
    if k == 'mansion':
        return (wx - 1.0, wz - 1.19), (wx + 0.5, wz + 0.07)
    return (wx + 1.0, wz - 1.0), (wx + 1.12, wz + 0.12)


def building_entry(model, x, y, z):
    xf, xp = ct_fx(x)
    yf, yp = ct_fx(y)
    zf, zp = ct_fx(z)
    return struct.pack('<IHhHhHh', model, xf, xp, yf, yp, zf, zp) + bytes.fromhex('0000000000000000000000000010000000100000001000000000000000000000')


def ct_fx(v):
    raw = round(v * 65536)
    return raw & 0xFFFF, raw >> 16


TREES = [(5, 8), (5, 11), (14, 7), (17, 9), (19, 6), (15, 11), (28, 8), (28, 11), (27, 15), (24, 16), (28, 19), (28, 22), (6, 23)]      # no two within 2 tiles in x AND 3 in z: a tree's see-through texels still block the tree behind it where their quads overlap on screen
FLOWERS = [(14, 15), (16, 16), (17, 15), (23, 15), (26, 16), (6, 12), (8, 12), (16, 9), (18, 11), (28, 13)]
FLOWERS2 = [(15, 15), (14, 16), (18, 16), (25, 15), (22, 16), (7, 12), (9, 12), (17, 10), (15, 9), (28, 14)]


def build_layout():
    """-> (layout rows, perm bytes, building entries, door tiles)."""
    rows = [list('~' * 32) for _ in range(32)]
    for z in range(5, 27):
        for x in range(4, 30):
            rows[z][x] = 'b' if z in (5, 26) or x in (4, 29) else 'g'
    for z in (4, 27):
        for x in range(6, 28):
            rows[z][x] = 'b'
    for z in range(0, 4):                 # the land north (owner 2026-11-08: 'the back of the island connects to the raised land behind it, roughly where the volcano is' / 'the brown land mass behind the Gym'): one broad brown plain with a beach fringe across the back, up to the chunk edge; cinnabar_terrain.NORTH_EXT continues it 3 tiles into the neighbour's water toward the plateau behind the Gym
        for x in range(15, 28):
            rows[z][x] = 'b' if x in (15, 27) else 'g'
    blocked, doors, blds = set(), {}, b''
    for name, b in BUILDINGS.items():
        (ox, oz), (dx, dz) = origin_and_door(b)
        fx0, fx1 = b['fx']
        fz0, fz1 = b['fz']
        for z in range(int(oz) + fz0, int(oz) + fz1 + 1):
            for x in range(int(ox) + fx0, int(ox) + fx1 + 1):
                blocked.add((x, z))
        doors[name] = b['warp']
        blds += building_entry(b['model'], ox - 16, 0.0, oz - 16) + building_entry(b['door'], dx - 16, DOOR_Y[b['kind']], dz - 16)
    for t in doors.values():
        blocked.add(t)
    for (x, z) in SIGNS.values():
        blocked.add((x, z))
        blds += building_entry(BOARD, x + 0.5 - 16, 0.0, z + 0.5 - 16)
    # roads: two E-W roads (north: z 13-14, south: z 24-25), one N-S corridor between the Center and the Mart (x 19-20), a stub in front of every door
    roads = set()
    for z in (13, 14):
        roads |= {(x, z) for x in range(8, 26)}
    for z in (24, 25):
        roads |= {(x, z) for x in range(7, 25)}
    roads |= {(x, z) for x in (19, 20) for z in range(13, 26)}
    for name, (wx, wz) in doors.items():
        if wz > 20:
            roads |= {(wx, z) for z in range(wz + 1, 25)}
        else:
            roads |= {(wx, z) for z in range(wz + 1, 14)}
    sign_tiles = set(SIGNS.values())
    roads -= sign_tiles
    assert not (roads & (blocked - set(doors.values()))), sorted(roads & (blocked - set(doors.values())))
    for (x, z) in roads:
        if rows[z][x] == 'g' and (x, z) not in blocked:
            rows[z][x] = 'r'
    for (x, z) in blocked:
        if rows[z][x] in 'gr':
            rows[z][x] = '#'
    for (x, z) in sign_tiles:
        rows[z][x] = '#'
    for t in doors.values():
        rows[t[1]][t[0]] = 'r'
    for i, (x, z) in enumerate(TREES):
        for (x2, z2) in TREES[:i]:
            assert abs(x - x2) >= 2 or abs(z - z2) >= 3, ((x, z), (x2, z2))
    for (x, z) in TREES:                  # polish (2026-11-08): trees (blocked) and flower beds (walkable) on free grass only
        assert rows[z][x] == 'g', (x, z, rows[z][x])
        rows[z][x] = 'T'
    for (x, z) in FLOWERS:
        assert rows[z][x] == 'g', (x, z, rows[z][x])
        rows[z][x] = 'o'
    for (x, z) in FLOWERS2:
        assert rows[z][x] == 'g', (x, z, rows[z][x])
        rows[z][x] = 'p'
    layout = [''.join(r) for r in rows]
    perm = bytearray()
    for z, row in enumerate(layout):
        for x, c in enumerate(row):
            if (x, z) in doors.values():
                perm += bytes([0x69, 0x80])
            elif c in '#T':
                perm += bytes([0, 0x80])
            elif c == '~':
                perm += bytes([0x15, 0])
            else:
                perm += bytes([0, 0])
    return layout, bytes(perm), blds, doors


def patch(rom, source=None):
    layout, perm, blds, doors = build_layout()
    report = ct.patch(rom, layout=layout, blds=blds, group=GROUP, perm=perm)
    report['doors'] = {k: (1024 + x, 480 + z) for k, (x, z) in doors.items()}
    return report


if __name__ == '__main__':
    layout, perm, blds, doors = build_layout()
    print('\n'.join(layout))
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
