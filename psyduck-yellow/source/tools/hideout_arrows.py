"""Visible spinner arrows for the Rocket Hideout (owner order 2026-11-03: "I can't see the floor tiles which propel the player across the screen ... I'd also need to see which direction the propulsion goes").
Yellow's B2F and B3F are arrow-tile mazes. hideout_yellow.py (0099) made every arrow tile a one-tile slide trigger, but the floor under it was plain, so the player could not see where the arrows are or which way they push.
Now each arrow tile (a SCALE x SCALE block, one Yellow step) gets a flat red pad with a white arrow pointing the way the slide starts (the first move of pokeyellow's own list for that tile), drawn the same way facility_markers.py draws the blue/orange stair pads.
The stored floor models (with the stair markers) and the texture bank are regenerated and compared byte for byte first, so the patch only runs on a floor it reproduces exactly; the four arrow textures and materials are appended after the existing ones, so every existing model keeps working.
Usage (from yellow-heartgold, PYTHONPATH=tools): hideout_arrows.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import ndspy.texture
import cave_floor as cf
import cave_ladders as cl
import facility_markers as fm
import hideout_yellow as hy
import map_header_extension as ext
import spin_tiles
import yellow_3d
import yellow_imd

SCALE, CHUNK = cf.SCALE, cf.CHUNK
DIRS = {12: 'up', 13: 'down', 14: 'left', 15: 'right'}                # spin_tiles.CODE
PALETTE = [(10, 0, 0), (27, 3, 3), (31, 31, 31), (18, 1, 1)]           # dark red edge, red pad, white arrow, inner edge (5-bit RGB)


def arrow_texture(direction):
    grid = [[1] * 16 for _ in range(16)]
    for i in range(16):
        for x, y in ((i, 0), (i, 15), (0, i), (15, i)):
            grid[y][x] = 0
        for x, y in ((i, 1), (i, 14), (1, i), (14, i)):
            if grid[y][x] == 1:
                grid[y][x] = 3
    rows = [(r, 7 - (r - 3), 8 + (r - 3)) for r in range(3, 9)] + [(r, 6, 9) for r in range(9, 13)]
    for r, lo, hi in rows:
        for x in range(lo, hi + 1):
            if direction == 'up':
                grid[r][x] = 2
            elif direction == 'down':
                grid[15 - r][x] = 2
            elif direction == 'left':
                grid[x][r] = 2
            else:
                grid[x][15 - r] = 2
    return dict(name='Spin' + direction.capitalize(), fmt=3, w=16, h=16, pixels=fm._pack4(grid), palette=PALETTE)


def patch_floor(rom, spec, spin):
    """spec: a facility_markers.hideout_specs entry; spin: {(step x, step y): first move code}"""
    mapid, OX, OZ = spec['map'], spec['OX'], spec['OZ']
    mats_n = ndspy.narc.NARC(rom.getFileByName('a/0/4/1'))
    lands = ndspy.narc.NARC(rom.getFileByName('a/0/6/5'))
    areas = ndspy.narc.NARC(rom.getFileByName('a/0/4/2'))
    banks = ndspy.narc.NARC(rom.getFileByName('a/0/4/4'))
    rec = ext.records(rom)[mapid - ext.NATIVE_COUNT]
    bank_id = struct.unpack_from('<H', areas.files[rec[1]], 2)[0]
    src = ndspy.texture.NSBTX(banks.files[struct.unpack_from('<H', areas.files[spec['area']], 2)[0]])
    tx, pl = dict(src.textures), dict(src.palettes)
    textures = [dict(name=new, fmt=int(tx[t].format), w=tx[t].width, h=tx[t].height, pixels=bytes(tx[t].data1), palette=[(c.r, c.g, c.b) for c in pl[p].colors]) for t, p, new in spec['tex']]
    mats = list(spec['mats'])
    yellow_3d.VISIBLE_DEPTH = 2
    mat = bytes(mats_n.files[struct.unpack_from('<H', rec, 4)[0]])
    w, h, hd, ht, n = mat[:5]
    land_ids = struct.unpack_from('<%dH' % (w * h), mat, 5 + n + w * h * (2 * hd + ht))
    parts = {(i % w, i // w): list(cl.parse(bytes(lands.files[lid]))) for i, lid in enumerate(land_ids)}
    walk = [[not parts[((OX + SCALE * sx) // CHUNK, (OZ + SCALE * sy) // CHUNK)][0][(((OZ + SCALE * sy) % CHUNK) * CHUNK + (OX + SCALE * sx) % CHUNK) * 2 + 1] & 0x80 for sx in range(spec['W'] * 2)] for sy in range(spec['H'] * 2)]
    tk = cf.tile_grid(cf.classify(walk, set()))

    def chunk_quads(cx, cz):
        kc = {(OX + a - cx * CHUNK, OZ + b - cz * CHUNK): k for (a, b), k in tk.items() if (OX + a) // CHUNK == cx and (OZ + b) // CHUNK == cz}
        full = {(OX + a - cx * CHUNK, OZ + b - cz * CHUNK): k for (a, b), k in tk.items()}
        return yellow_3d.geometry_sloped(kc, full, -4.0, -4.0)

    def model(quads, cx, cz, texs, ms):
        return yellow_imd.convert(yellow_imd.imd_multi(texs, ms, quads, -4.0, -4.0, 4.0, 4.0, yellow_3d.WALL_H), f"{spec['name']}c{cx}{cz}")[0]
    extras = fm.marker_textures(rom)
    textures_all = textures + extras
    mats_all = mats + [(f'm_{k}', len(textures) + fm.KIND_TEXTURE[k], f'm_{k}') for k in fm.KIND_TEXTURE]
    arrows = [arrow_texture(d) for d in ('up', 'down', 'left', 'right')]
    textures_new = textures_all + arrows
    mats_new = mats_all + [(f'm_spin_{d}', len(textures_all) + i, f'm_spin_{d}') for i, d in enumerate(('up', 'down', 'left', 'right'))]
    dummy = {m[2]: [((0, 0, 0, 0, 0, 0, 1, 0), (0, 0, 0.01, 0, 1, 0, 1, 0), (0.01, 0, 0.01, 1, 1, 0, 1, 0), (0.01, 0, 0, 1, 0, 0, 1, 0))] for m in mats_new}

    def bank(texs, ms):
        return yellow_imd.convert(yellow_imd.imd_multi(texs, ms, {m[2]: dummy[mats[0][2]] for m in ms}, -4.0, -4.0, 4.0, 4.0, 0.1), f"{spec['name']}tex")[1]
    assert bank(textures_all, mats_all) == bytes(banks.files[bank_id]), (spec['name'], 'the regenerated texture bank (with the stair markers) differs from the stored one')
    # the stored chunk models: floor + the existing stair/elevator markers
    blocks = [{(sx * SCALE + dx, sy * SCALE + dz) for dx in range(SCALE) for dz in range(SCALE)} for sx, sy, _ in spec['warps']]
    marker_art = {}
    for (sx, sy, kind), b in zip(spec['warps'], blocks):          # warp_tiles.py: one tile of art on each warp block's firing tile (lowest x, highest z)
        gx, gz = OX + min(a for a, _ in b), OZ + max(c for _, c in b)
        cx, cz = gx // CHUNK, gz // CHUNK
        x0, z0 = -4.0 + (gx - cx * CHUNK) * cl.TILE, -4.0 + (gz - cz * CHUNK) * cl.TILE
        marker_art.setdefault((cx, cz), {}).setdefault(f'm_{kind}', []).append(cl._quad(x0, z0, x0 + cl.TILE, z0 + cl.TILE, cl.PAD_Y))
    arrow_art = {}
    for (sx, sy), code in sorted(spin.items()):
        gx, gz = OX + SCALE * sx, OZ + SCALE * sy
        cx, cz = gx // CHUNK, gz // CHUNK
        assert (gx + 1) // CHUNK == cx and (gz + 1) // CHUNK == cz and all(tk.get((gx - OX + a, gz - OZ + c)) == 'floor' for a in range(SCALE) for c in range(SCALE)), (spec['name'], sx, sy, 'arrow block is not plain floor in one chunk')
        x0, z0 = -4.0 + (gx - cx * CHUNK) * cl.TILE, -4.0 + (gz - cz * CHUNK) * cl.TILE
        arrow_art.setdefault((cx, cz), {}).setdefault(f'm_spin_{DIRS[code]}', []).append(cl._quad(x0, z0, x0 + SCALE * cl.TILE, z0 + SCALE * cl.TILE, cl.PAD_Y))
    for (cx, cz), (perm, blds, old_model, bdhc) in parts.items():
        quads = chunk_quads(cx, cz)
        if (cx, cz) in marker_art:
            for key, qs in marker_art[(cx, cz)].items():
                quads.setdefault(key, []).extend(qs)
            assert model(quads, cx, cz, textures_all, mats_all) == old_model, (spec['name'], cx, cz, 'the regenerated chunk (with markers) differs from the stored one')
        elif any(quads.values()):
            assert model(quads, cx, cz, textures, mats) == old_model, (spec['name'], cx, cz, 'the regenerated chunk differs from the stored one')
    # add the arrows
    for (cx, cz), art in arrow_art.items():
        quads = chunk_quads(cx, cz)
        for more in (marker_art.get((cx, cz), {}), art):
            for key, qs in more.items():
                quads.setdefault(key, []).extend(qs)
        parts[(cx, cz)][2] = model(quads, cx, cz, textures_new, mats_new)
    for (cx, cz), (perm, blds, mdl, bdhc) in parts.items():
        lands.files[land_ids[cz * w + cx]] = cl.pack(bytes(perm), bytes(blds), mdl, bdhc)
    banks.files[bank_id] = bank(textures_new, mats_new)
    rom.setFileByName('a/0/6/5', lands.save())
    rom.setFileByName('a/0/4/4', banks.save())
    return dict(name=spec['name'], arrows=len(spin), chunks=sorted(arrow_art), directions={d: sum(1 for c in spin.values() if DIRS[c] == d) for d in ('up', 'down', 'left', 'right')})


def patch(rom, source):
    specs = fm.hideout_specs(source)
    report = []
    for f, name in sorted(hy.SPIN.items()):
        tiles = spin_tiles.load(source, name)
        spin = {xy: moves[0][0] for xy, moves in tiles.items()}
        report.append(patch_floor(rom, specs[f - 1], spin))
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
