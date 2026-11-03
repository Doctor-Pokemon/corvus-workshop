"""Prototype 0171: Celadon's Game Corner can be entered from the street, and Mr. Game's room moves behind the prize building's door (owner order 2026-11-03, from photos).
Why: HeartGold's Celadon door at (1218,249) leads to Mr. Game's small room (map 537); the Game Corner (map 381: the Rocket guard, the poster to the Rocket Hideout) has no door from the street, so the Hideout, the Silph Scope and everything after it could not be reached (the base game is the same).
Layout now (owner: "Da" and "Db"):
 - Celadon door (1218,249), the left building with the blue arched door, leads to the Game Corner (381 warp 0); the Game Corner's exit warp already returns to that door (Celadon warp 3).
 - Celadon door (1223,249), the right building with the red door, leads to Mr. Game's room (537), entering at its south door (warp 0); that door now exits to Celadon warp 4 (the red door).
 - Mr. Game's room gets a door in the centre of its north wall: the wall tile (7,2) becomes a door tile (behaviour 0x8069, the blocked door tile the native buildings use) with a warp to the Prize room (382) south door (warp 0); the Prize room's south door now leads to a landing warp on the floor tile in front of that north door (7,3), so the arrival is not ON the door tile (0170 lesson: a sideways bump on an arrival door tile fires its warp).
 - The Prize room has no street door any more (its building is the red door, which leads to Mr. Game's room first).
Mr. Game's room shares its land chunk (381) with map 536, so it gets its own chunk copy and matrix copy. Maps, scripts and texts of the three rooms are otherwise unchanged. The extension header table is full, so no new map is added.
Usage (from yellow-heartgold, PYTHONPATH=tools): celadon_game_corner.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode
from viridian_tutorial import TABLE

CELADON, GAME_CORNER, MR_GAME, PRIZE = 55, 381, 537, 382
STREET_LEFT, STREET_RIGHT = 3, 4         # Celadon warp indices: door (1218,249) and door (1223,249)
NORTH_DOOR, NORTH_LANDING = (7, 2), (7, 3)
DOOR_TILE = 0x8069
ROW = struct.Struct('<4HI')              # x, z, destination map, destination warp, padding


def event_file(d, m):
    return struct.unpack_from('<H', d, TABLE + 24 * m + 16)[0]


def point(group, index, dest, anchor):
    row = bytearray(group[2][index])
    struct.pack_into('<2H', row, 4, dest, anchor)
    group[2][index] = bytes(row)


def patch(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    mats = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/4/1')])
    lands = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/6/5')])
    for m in (CELADON, MR_GAME, PRIZE):
        assert not [x for x in range(540) if x != m and event_file(d, x) == event_file(d, m)], 'event file shared: %d' % m
    g = {m: events_decode(events.files[event_file(d, m)]) for m in (CELADON, GAME_CORNER, MR_GAME, PRIZE)}
    cel = [ROW.unpack(w) for w in g[CELADON][2]]
    assert cel[STREET_LEFT][:3] == (1218, 249, MR_GAME) and cel[STREET_RIGHT][:3] == (1223, 249, PRIZE), cel
    assert [ROW.unpack(w)[:4] for w in g[GAME_CORNER][2]] == [(10, 16, CELADON, STREET_LEFT)], 'the Game Corner exit is not the expected one'
    assert [ROW.unpack(w)[:4] for w in g[MR_GAME][2]] == [(7, 12, CELADON, STREET_LEFT)], 'Mr. Game warps changed'
    assert [ROW.unpack(w)[:4] for w in g[PRIZE][2]] == [(4, 7, CELADON, STREET_RIGHT)], 'prize room warps changed'
    # Mr. Game's own land chunk and matrix (the chunk is shared with map 536)
    rec = TABLE + 24 * MR_GAME
    old_matrix = struct.unpack_from('<H', d, rec + 4)[0]
    mx = bytearray(mats.files[old_matrix])
    w, h, has_headers, has_alt, name_len = mx[0], mx[1], mx[2], mx[3], mx[4]
    assert (w, h) == (1, 1)
    at = 5 + name_len + (2 * w * h if has_headers else 0) + (w * h if has_alt else 0)
    chunk = struct.unpack_from('<H', mx, at)[0]
    raw = bytearray(lands.files[chunk])
    tile = 20 + 2 * (NORTH_DOOR[1] * 32 + NORTH_DOOR[0])
    assert struct.unpack_from('<H', raw, tile)[0] == 0x8000, 'the north wall tile is not a plain wall'
    assert struct.unpack_from('<H', raw, 20 + 2 * (NORTH_LANDING[1] * 32 + NORTH_LANDING[0]))[0] == 0, 'the landing tile is not plain floor'
    struct.pack_into('<H', raw, tile, DOOR_TILE)
    lands.files.append(bytes(raw))
    struct.pack_into('<H', mx, at, len(lands.files) - 1)
    mats.files.append(bytes(mx))
    struct.pack_into('<H', d, rec + 4, len(mats.files) - 1)
    # warps
    point(g[CELADON], STREET_LEFT, GAME_CORNER, 0)
    point(g[CELADON], STREET_RIGHT, MR_GAME, 0)
    point(g[MR_GAME], 0, CELADON, STREET_RIGHT)
    g[MR_GAME][2].append(ROW.pack(*NORTH_DOOR, PRIZE, 0, 0))
    g[MR_GAME][2].append(ROW.pack(*NORTH_LANDING, PRIZE, 0, 0))          # arrival anchor only
    point(g[PRIZE], 0, MR_GAME, 2)
    for m in (CELADON, MR_GAME, PRIZE):
        events.files[event_file(d, m)] = events_encode(g[m])
    rom.files[rom.filenames.idOf('a/0/3/2')] = events.save()
    rom.files[rom.filenames.idOf('a/0/4/1')] = mats.save()
    rom.files[rom.filenames.idOf('a/0/6/5')] = lands.save()
    rom.arm9 = main.save(compress=True)
    return dict(chunk=len(lands.files) - 1, matrix=len(mats.files) - 1, north_door=NORTH_DOOR, north_landing=NORTH_LANDING, mr_game_warps=len(g[MR_GAME][2]))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
