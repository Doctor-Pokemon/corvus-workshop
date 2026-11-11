"""Cinnabar Island rebuilt (owner order 2026-11-08: "rebuild Cinnabar Island to look more like the one from the original Yellow ... layout, buildings, NPCs, scripting ... the graphics to LOOK good").
Phase A (this module): a new terrain chunk for the matrix-0 cell (32,15) (global tiles x 1024..1055, z 480..511; header 57, area 18, texture bank 18) laid out like Yellow's Cinnabar Island (pokeyellow maps/CinnabarIsland.blk, 20 x 18 steps):
Mansion top left, Gym top right, Lab left, Pokemon Center bottom centre, Mart bottom right, a road network between the doors, beaches and sea all round. Ground, road, beach and sea use HeartGold's own textures from texture bank 18 (the bank the neighbouring sea chunks use),
so no area or bank is added and the seam to the neighbouring chunks is plain water.
The chunk's native terrain (a baked hilly maze) is replaced; the native building entries (signboards 29/31, Center 40, door 15) are rewritten by the later phases.
LAYOUT below is the tile map of the chunk (32 x 32): ~ sea, b beach, g grass, r road, # building footprint (grass, blocked), f fence/hedge (blocked), t tree (blocked).
Usage (from yellow-heartgold, PYTHONPATH=tools): cinnabar_terrain.py <in.nds> <out.nds>"""
import re
import struct
import sys
import ndspy.narc
import ndspy.rom
import ndspy.texture
import yellow_imd
from viridian_tutorial import TABLE

CELL = (32, 15)
WORLD = (1024, 480)
SEA_BANK = 18
LAND_Y, SEA_Y = 0.0, 0.0
TILE = 0.25
HALF = 4.0
LAYOUT = [
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "......bbbbbbbbbbbbbbbbbbbbb.....",
    ".....bbggggggggggggggggggggb....",
    ".....bgggggggggggggggggggggb....",
    ".....bgggggggggggggggggggggb....",
    ".....bgggggggggggggggggggggb....",
    ".....bgggggggggggggggggggggb....",
    ".....bggggggrrgggggggrrgggb.....",
    ".....bgggggggrgggggggrggggb.....",
    ".....bggrrrrrrrrrrrrrrrrrgb.....",
    ".....bgggggggrgggggggggggggb....",
    ".....bgggggggrgggggggggggggb....",
    ".....bgggggggrgggggggggggggb....",
    ".....bgggggggrgggggggggggggb....",
    ".....bggggggggrgggggggggggb.....",
    ".....bggggggggrgggggggggggb.....",
    ".....bggggggggrgggggggggggb.....",
    ".....bggggggggrgggggggggggb.....",
    ".....bggggggggrrrrrrrrrrrgb.....",
    ".....bggggggggrgggggggggggb.....",
    ".....bbggggggggggggggggggbb.....",
    "......bbbbbbbbbbbbbbbbbbb.......",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
]
LAYOUT = [row.replace('.', '~') for row in LAYOUT]
NORTH_EXT = [(x, z, 'b' if x in (21, 27) else 'g') for z in (-3, -2, -1) for x in range(21, 28)]      # land drawn past the chunk's top edge (global z 477-479) toward the raised brown plateau behind the Gym (neighbour chunk, blocked tiles x 22-26, z 473-476); the neighbour's walkable data is edited in cinnabar_polish.py
TEXTURES = {'ground': ('grass01_a', 'grass01_a'), 'road': ('road01', 'road01'), 'beach': ('beach01', 'beach01_pl'), 'sea': ('sea_on', 'sea_f02_pl'),
            'foam': ('swave_un', 'swave_un_pl'), 'flower': ('flower01', 'flower01'), 'flower2': ('flower02', 'flower02')}
TRANSP = {'flower', 'flower2', 'tree'}       # textures whose colour 0 is see-through (flower tiles over grass, the tree sprite)
OWN = {'ground': 'cn_grass', 'road': 'cn_road', 'beach': 'cn_beach', 'sea': 'cn_sea', 'foam': 'cn_foam', 'flower': 'cn_flower', 'flower2': 'cn_flower2', 'tree': 'cn_tree'}        # copies under new names (cave_floor does the same): the model must not share names with the stock banks
UV = {'ground': 1.0, 'road': 0.5, 'beach': 0.5}


SWAPPED = set()      # was {'grass01_a', 'grass01gs'}: that 'fix' came from ds_session.shot(), which decodes RGB565 as 1555 and shows true green as pink; in TRUE colours (shot_true / 'tshot') the swapped grass is reddish-brown, the plain palette is green (found 2026-11-08)
SWAPPED_OLD = {'grass01_a', 'grass01gs'}      # tested live: with plain (r, g, b) these two palettes came out pink instead of green while sea, road and beach were right; red and green swapped fixes them
PALETTE_OF = {'a17_gt01': 'a17_gt01_pl', 'allpeak_pgs': 'apeak', 'allpeakgs': 'apeak', 'beach01': 'beach01_pl', 'beach01_r2': 'beach01_r2_pl', 'cliff01gs': 'cliff01', 'etc_a': 'etc_a_pl',
              'fence_a': 'fence_a_pl', 'grass01_a': 'grass01_a', 'grass01gs': 'grass01', 'pond_line': 'pond_line', 'road01': 'road01', 'road01_r': 'road01_r', 'road01_sub': 'road01_sub_pl', 'rock01': 'rock01',
              'sea_on': 'sea_f02_pl', 'sea_rock': 'sea_rock_pl', 'sea_rock_m': 'sea_rock_m_pl', 'sea_un': 'sea_un', 'swave_p': 'swave_p_pl', 'swave_un': 'swave_un_pl', 'tree01_un': 'tree01_un',
              'wall01_d': 'wall01_d', 'wall01_g': 'wall01_g', 'wall01_h': 'wall01_h_pl', 'cavehole': 'cavehole_pl', 'egrass': 'egrass_pl', 'egrass_ro': 'egrass_ro_pl', 'flower01': 'flower01',
              'flower02': 'flower02', 'flower03': 'flower03', 'slope': 'slope_pl', 'grass02': 'grass02_pl', 'grass02_r': 'grass02_r_pl', 'r_climb': 'r_climb_pl', 'road05': 'road05', 'fence_b': 'fence_b_pl'}


TREE_PALETTE = [(0, 0, 0), (3, 6, 3), (5, 12, 6), (8, 18, 8), (12, 24, 11), (17, 28, 14), (7, 4, 2), (13, 8, 4)] + [(3, 6, 3)] * 8


def tree_texture():
    """A round-canopied tree drawn here (32x32, 16 colours, colour 0 see-through): dark outline, three greens, highlights, a trunk. Two of these as crossed upright quads make a tree."""
    from PIL import Image, ImageDraw
    im = Image.new('P', (32, 32), 0)
    d = ImageDraw.Draw(im)
    d.rectangle([14, 22, 17, 30], fill=6)
    d.rectangle([15, 22, 16, 30], fill=7)
    d.ellipse([2, 1, 29, 25], fill=1)
    d.ellipse([3, 2, 28, 24], fill=2)
    for box, col in (([4, 3, 20, 17], 3), ([9, 5, 26, 21], 3), ([6, 4, 17, 13], 4), ([10, 7, 22, 17], 4), ([7, 5, 13, 10], 5), ([13, 6, 19, 10], 5)):
        d.ellipse(box, fill=col)
    d.arc([3, 2, 28, 24], 20, 160, fill=1)
    flat = [c * 8 for rgb in TREE_PALETTE for c in rgb]
    im.putpalette(flat + [0] * (768 - len(flat)))
    px = im.load()
    data = bytearray()
    for y in range(32):
        for x in range(0, 32, 2):
            data.append(px[x, y] | (px[x + 1, y] << 4))
    return dict(name=OWN['tree'], fmt=3, w=32, h=32, pixels=bytes(data), palette=list(TREE_PALETTE), transp=True)


def volcanic(c):
    """Cinnabar's ground (owner 2026-11-08: 'it's at the base of a volcano', so brown): the grass tile's own palette with its hues replaced by a dull volcanic-soil brown at the same lightness, so the tile keeps its texture detail."""
    r, g, b = c
    lum = (0.30 * r + 0.59 * g + 0.11 * b)
    return (min(31, round(lum * 1.22)), min(31, round(lum * 0.92)), min(31, round(lum * 0.66)))


def grab_textures(rom, area=18):
    """Every 4/16-colour texture of the area's land bank (names and palette names kept), mine first. Returns (textures, {texture name: palette name})."""
    areas = ndspy.narc.NARC(rom.getFileByName('a/0/4/2'))
    banks = ndspy.narc.NARC(rom.getFileByName('a/0/4/4'))
    bank = ndspy.texture.NSBTX(banks.files[struct.unpack_from('<H', areas.files[area], 2)[0]])
    tx, pl = dict(bank.textures), dict(bank.palettes)
    order = [TEXTURES[k][0] for k in TEXTURES] + [n for n in PALETTE_OF if n not in {v[0] for v in TEXTURES.values()}]
    out = []
    for tname in order:
        pname = PALETTE_OF[tname]
        t = tx[tname]
        assert int(t.format) in (2, 3), (tname, t.format)
        out.append(dict(name=tname, fmt=int(t.format), w=t.width, h=t.height, pixels=bytes(t.data1), palette=[((c.g, c.r, c.b) if tname in SWAPPED else (c.r, c.g, c.b)) for c in pl[pname].colors]))
    own = []
    for key, (tname, pname) in TEXTURES.items():
        t = dict(next(x for x in out if x['name'] == tname))
        t['name'] = OWN[key]
        t['transp'] = key in TRANSP
        if key == 'ground':
            t['palette'] = [volcanic(c) for c in t['palette']]
        own.append(t)
    own.append(tree_texture())
    pal = {n: PALETTE_OF[n] for n in order}
    pal.update({OWN[k]: OWN[k] for k in OWN})
    return own + out, pal


HILL_X, HILL_Z = (15, 28), (0, 6)       # vertex ranges of the raised land behind the Gym (tile units inside the chunk): zero height on the whole rim, so it meets the beach and the grass (z 6), the chunk edge (z 0) and the fringe (x 15, 28) level
HILL_PEAK = 2.0                          # tiles; tested walkable (the engine accepts the 1/8-tile steps between neighbouring flat plates this gives)


def hill_height(vx, vz):
    """Terrain height in TILES at tile-corner (vx, vz) of the island chunk: 0 everywhere except a bumpy hill behind the Gym (owner 2026-11-08: 'supposed to be raised up a bit; not flat, and walkable')."""
    import math
    if not (HILL_X[0] <= vx <= HILL_X[1] and HILL_Z[0] <= vz <= HILL_Z[1]):
        return 0.0
    base = math.sin(math.pi * (vx - HILL_X[0]) / (HILL_X[1] - HILL_X[0])) * math.sin(math.pi * ((vz - HILL_Z[0]) / (HILL_Z[1] - HILL_Z[0])) ** 0.8)
    bump = 1 + 0.30 * math.sin(vx * 0.95 + 1.0) * math.cos(vz * 1.4 + 0.5)
    return round(HILL_PEAK * base * bump * 8) / 8        # quarter-tile steps: the plate planes and the model stay in step


def in_hill(lx, lz):
    return HILL_X[0] <= lx < HILL_X[1] and HILL_Z[0] <= lz < HILL_Z[1]


def tile_height(c, r):
    """Height of tile (c, r) for walking: the average of its four corners (flat plates only; see build_bdhc)."""
    return (hill_height(c, r) + hill_height(c + 1, r) + hill_height(c, r + 1) + hill_height(c + 1, r + 1)) / 4


def build_bdhc():
    """The chunk's height table (see bdhc.py), in the STOCK convention read from the Cinnabar chunk: a flat plate at height H tiles has slope vector (0, 1/16, 0) and constant -H (the Pokemon Center stands at y = 1.0 on a plate with constant -1.0).
    One flat plate per run of tiles with the same height, a strip per tile row. (Sloped plates exist in the stock data (normals (0, .0442, .0442) for 45 degrees) but their formula is not decoded yet.)"""
    import bdhc
    F = lambda v: int(round(v * 65536))
    points, slopes, consts, plates, strips, access = [], [], [], [], [], []

    def idx(lst, v):
        if v not in lst:
            lst.append(v)
        return lst.index(v)
    for r in range(32):
        runs = []
        for c in range(32):
            h = round(tile_height(c, r) * 8) / 8
            if runs and runs[-1][2] == h:
                runs[-1][1] = c + 1
            else:
                runs.append([c, c + 1, h])
        first = len(access)
        for c0_, c1_, h in runs:
            points.append((F(c0_ - 16), F(r - 16)))
            points.append((F(c1_ - 16), F(r + 1 - 16)))
            plates.append((len(points) - 2, len(points) - 1, idx(slopes, (0, 4096, 0)), idx(consts, F(-h))))
            access.append(len(plates) - 1)
        strips.append((F(r + 1 - 16), len(runs), first))
    return bdhc.build(points, slopes, consts, plates, strips, access)


def quads_for(layout):
    X = lambda lx: -HALF + lx * TILE
    Z = lambda lz: -HALF + lz * TILE
    quads = {'ground': [], 'road': [], 'beach': [], 'sea': [], 'foam': [], 'flower': [], 'flower2': [], 'tree': []}
    e = 0.08                                   # the sea plane reaches past the chunk edge and sits a hair lower: the neighbouring chunks' water wins where they overlap, and no black gap shows at the seams (found 2026-11-08 on the north and east edges)
    lo, hi = -HALF - e, HALF + e
    st = lambda v: 8 * (v + HALF) / (2 * HALF)
    quads['sea'].append(((lo, SEA_Y - 0.004, lo, st(lo), st(lo), 0, 1, 0), (lo, SEA_Y - 0.004, hi, st(lo), st(hi), 0, 1, 0), (hi, SEA_Y - 0.004, hi, st(hi), st(hi), 0, 1, 0), (hi, SEA_Y - 0.004, lo, st(hi), st(lo), 0, 1, 0)))
    at = lambda lx, lz: layout[lz][lx] if 0 <= lz < len(layout) and 0 <= lx < len(layout[lz]) else '~'
    KEYS = {'g': 'ground', '#': 'ground', 'f': 'ground', 't': 'ground', 'T': 'ground', 'o': 'ground', 'p': 'ground', 'r': 'road', 'b': 'beach'}
    for lz, row in enumerate(layout):      # ground, road and beach: runs of identical tiles in a row become ONE quad (the DS draws at most ~2000 polygons a frame across every loaded chunk; one quad per tile blanked the neighbouring chunks)
        lx = 0
        while lx < len(row):
            key = KEYS.get(row[lx])
            if not key or in_hill(lx, lz):
                lx += 1
                continue
            end = lx
            while end + 1 < len(row) and KEYS.get(row[end + 1]) == key and not in_hill(end + 1, lz):
                end += 1
            u = UV[key]
            run = end - lx + 1
            quads[key].append(((X(lx), LAND_Y + 0.02, Z(lz), 0, 0, 0, 1, 0), (X(lx), LAND_Y + 0.02, Z(lz + 1), 0, u, 0, 1, 0), (X(end + 1), LAND_Y + 0.02, Z(lz + 1), u * run, u, 0, 1, 0), (X(end + 1), LAND_Y + 0.02, Z(lz), u * run, 0, 0, 1, 0)))
            lx = end + 1
    for lz, row in enumerate(layout):
        for lx, c in enumerate(row):
            if c in 'op':                      # flower beds: a see-through flower tile just above the grass
                k = 'flower' if c == 'o' else 'flower2'
                quads[k].append(((X(lx), LAND_Y + 0.03, Z(lz), 0, 0, 0, 1, 0), (X(lx), LAND_Y + 0.03, Z(lz + 1), 0, 1, 0, 1, 0), (X(lx + 1), LAND_Y + 0.03, Z(lz + 1), 1, 1, 0, 1, 0), (X(lx + 1), LAND_Y + 0.03, Z(lz), 1, 0, 0, 1, 0)))
            if c == 'T':                       # a tree: one quad leaning back toward the north so it faces the (south, ~50 degrees up) camera; its foot sits on the tile's south half
                cx, cz = X(lx) + TILE / 2, Z(lz) + TILE * 0.8
                w, hgt, y0 = 0.40, 0.44, LAND_Y + 0.03
                rise, back = hgt * 0.64, hgt * 0.77
                quads['tree'].append(((cx - w / 2, y0, cz, 0, 1, 0, 1, 0), (cx - w / 2, y0 + rise, cz - back, 0, 0, 0, 1, 0), (cx + w / 2, y0 + rise, cz - back, 1, 0, 0, 1, 0), (cx + w / 2, y0, cz, 1, 1, 0, 1, 0)))
            if c == '~':                       # shoreline foam on the water tile next to a beach tile: the tile's sand edge faces the beach
                for dx, dz, uv in ((0, -1, 'N'), (0, 1, 'S'), (-1, 0, 'W'), (1, 0, 'E')):
                    if at(lx + dx, lz + dz) == 'b':
                        y = SEA_Y + 0.01
                        t_ = {'N': lambda p: p[1], 'S': lambda p: 1 - p[1], 'W': lambda p: p[0], 'E': lambda p: 1 - p[0]}[uv]
                        corners = [(0, 0), (0, 1), (1, 1), (1, 0)]
                        pts = [(X(lx + a), Z(lz + b)) for a, b in corners]
                        if uv in 'NS':
                            quads['foam'].append(tuple((px_, y, pz_, a, t_((a, b)), 0, 1, 0) for (px_, pz_), (a, b) in zip(pts, corners)))
                        else:
                            quads['foam'].append(tuple((px_, y, pz_, b, t_((a, b)), 0, 1, 0) for (px_, pz_), (a, b) in zip(pts, corners)))
                        break
    for lz in range(HILL_Z[0], HILL_Z[1]):          # the raised land: one quad per tile with the tile's corner heights (tile units * TILE = model units), lit by its own slope
        for lx in range(HILL_X[0], HILL_X[1]):
            key = KEYS.get(layout[lz][lx])
            if not key:
                continue
            u = UV[key]
            hs = [hill_height(lx, lz), hill_height(lx, lz + 1), hill_height(lx + 1, lz + 1), hill_height(lx + 1, lz)]
            a = (hs[3] - hs[0] + hs[2] - hs[1]) / 2          # rise per tile along x
            b = (hs[1] - hs[0] + hs[2] - hs[3]) / 2          # rise per tile along z
            ln = (a * a + b * b + 1) ** 0.5
            nx, ny, nz = -a / ln, 1 / ln, -b / ln
            pts = [(lx, lz, 0, 0), (lx, lz + 1, 0, u), (lx + 1, lz + 1, u, u), (lx + 1, lz, u, 0)]
            quads[key].append(tuple((X(px), LAND_Y + 0.02 + h * TILE, Z(pz), s_, t_, nx, ny, nz) for (px, pz, s_, t_), h in zip(pts, hs)))
    for lx, lz, c in NORTH_EXT:
        key = {'g': 'ground', 'b': 'beach'}[c]
        u = UV[key]
        quads[key].append(((X(lx), LAND_Y + 0.02, Z(lz), 0, 0, 0, 1, 0), (X(lx), LAND_Y + 0.02, Z(lz + 1), 0, u, 0, 1, 0), (X(lx + 1), LAND_Y + 0.02, Z(lz + 1), u, u, 0, 1, 0), (X(lx + 1), LAND_Y + 0.02, Z(lz), u, 0, 0, 1, 0)))
    return quads


def perm_for(layout):
    perm = bytearray()
    for row in layout:
        for c in row:
            if c in '#ftT':
                perm += bytes([0, 0x80])
            elif c == '~':
                perm += bytes([0x15, 0])
            else:
                perm += bytes([0, 0])
    assert len(perm) == 2048
    return bytes(perm)


def build_model(rom, layout=LAYOUT):
    textures, pal = grab_textures(rom)
    names = [t['name'] for t in textures]
    mats = [(key, names.index(OWN[key]), key) for key in [*TEXTURES, 'tree']]

    def fix(text):
        for tname, pname in pal.items():
            text = text.replace(f'palette_name="{tname}"', f'palette_name="{pname}"')
            text = re.sub(r'(<tex_palette [^>]*name=")%s(")' % re.escape(tname), r'\g<1>%s\g<2>' % pname, text)
        return text
    model, _ = yellow_imd.convert(fix(yellow_imd.imd_multi(textures, mats, quads_for(layout), -HALF - 0.1, -HALF - 0.1, HALF + 0.1, HALF + 0.1, 0.1)), 'cinnabar_terrain')
    dummy_mats = [(n, i, n) for i, n in enumerate(names)]
    dummy = {n: [((0, 0, 0, 0, 0, 0, 1, 0), (0, 0, 0.01, 0, 1, 0, 1, 0), (0.01, 0, 0.01, 1, 1, 0, 1, 0), (0.01, 0, 0, 1, 0, 0, 1, 0))] for n in names}
    _, bank = yellow_imd.convert(fix(yellow_imd.imd_multi(textures, dummy_mats, dummy, -HALF, -HALF, HALF, HALF, 0.1)), 'cinnabar_textures')
    return model, bank


def parse_native(land):
    ps, bs, ms, bd = struct.unpack_from('<4I', land, 0)
    bgs = 4 + struct.unpack_from('<H', land, 18)[0] if land[16:18] == b'\x34\x12' else 0
    at = 16 + bgs
    return land[at:at + ps], land[at + ps:at + ps + bs], land[at + ps + bs:at + ps + bs + ms], land[at + ps + bs + ms:], land[16:16 + bgs]


def pack(perm, blds, model, bdhc):
    return struct.pack('<4I', len(perm), len(blds), len(model), len(bdhc)) + bytes.fromhex('34120000') + perm + blds + model + bdhc


def patch(rom, source=None, layout=LAYOUT, blds=b'', group=None, perm=None):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    rec = TABLE + 57 * 24
    assert d[rec + 1] == 18
    mats = ndspy.narc.NARC(rom.getFileByName('a/0/4/1'))
    lands = ndspy.narc.NARC(rom.getFileByName('a/0/6/5'))
    areas = ndspy.narc.NARC(rom.getFileByName('a/0/4/2'))
    banks = ndspy.narc.NARC(rom.getFileByName('a/0/4/4'))
    m0 = bytearray(mats.files[0])
    w, h, hd, ht, n = m0[:5]
    at = 5 + n + w * h * (2 * hd + ht) + 2 * (CELL[1] * w + CELL[0])
    old = struct.unpack_from('<H', m0, at)[0]
    assert old == 205, old
    bdhc = parse_native(bytes(lands.files[209]))[3]
    model, bank = build_model(rom, layout)
    land = pack(perm or perm_for(layout), blds, model, bdhc)
    new = len(lands.files)
    lands.files.append(land)
    struct.pack_into('<H', m0, at, new)
    mats.files[0] = bytes(m0)
    area = bytearray(areas.files[18])
    new_bank = len(banks.files)
    banks.files.append(bank)
    struct.pack_into('<H', area, 2, new_bank)
    if group is not None:
        struct.pack_into('<H', area, 0, group)        # building group: model set (a/0/4/3) AND building texture bank
    new_area = len(areas.files)
    assert new_area < 256
    areas.files.append(bytes(area))
    d[rec + 1] = new_area
    for p, a in (('a/0/4/1', mats), ('a/0/6/5', lands), ('a/0/4/2', areas), ('a/0/4/4', banks)):
        rom.setFileByName(p, a.save())
    rom.arm9 = main.save(compress=True)
    return dict(cell=CELL, old_land=old, new_land=new, area=new_area, bank=new_bank, model_bytes=len(land))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
