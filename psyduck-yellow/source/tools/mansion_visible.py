"""Prototype 0198: the Pokemon Mansion's gates and switches become VISIBLE (owner report 2026-11-08: closed gates were invisible silent step-backs, the switch statues invisible talk events; owner order: statues for the switches, visible solid barriers for the gates).
Before: each gate was a 4x4-tile trigger that pushed the player back when the switch variable (0x406D) was at the gate's closed value. Now:
 - GATES: barrier actors (sprite 85, the round rock nobody can push or smash, same as Victory Road's barriers) on the block's edge tiles next to every open neighbour step (2 tiles per open step), so a closed gate is sealed from every side, solid like any object. Gates that are closed at switch 0 hide when the switch is 1 (hide flag HA), gates closed at 1 hide when it is 0 (HB).
   HA/HB are DAILY-range flags (>= 0xAA0, recomputed, never persistent): a map-entry script on each floor sets them from the switch variable, so every floor always shows the state the variable says. Two flags serve all four floors.
 - SWITCHES: the hidden talk events on the statue tiles are replaced by two statue actors (sprite STATUE_SPRITE) on the same two tiles. Pressing A on a statue runs Yellow's yes/no question as before; on YES the variable flips, HA/HB flip and the barriers appear/disappear on the spot (script commands 100/101).
 - The old gate trigger rows (4x4) are removed from every floor's event file; their scripts stay in the bank, unused.
Usage (from yellow-heartgold, PYTHONPATH=tools): mansion_visible.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.rom
import cave_floor as cf
import hideout_yellow as hy
import mansion_yellow as my
import trainer_alloc
from ext_edit import ExtEdit
from opening import Script, actor, end

HA, HB = 0xAB1, 0xAB2
ROCK = 85
STATUE_SPRITE = 1023
FIRST_MAP = 575
OX, OZ, SC = hy.OX, hy.OZ, cf.SCALE
VAR = my.SWITCH_VAR


def entry_script():
    s = Script().compare(VAR, 0).jump('zero', 1)
    s.emit(30, HA).emit(31, HB).emit(2)
    s.label('zero').emit(31, HA).emit(30, HB).emit(2)
    return s.finish()


def statue_script(lines, closed0, closed1):
    ask, pressed, not_pressed = lines
    s = Script().emit(96).msg(ask).emit(63, 0x800C).compare(0x800C, 0).jump('yes', 1)
    s.msg(not_pressed)
    end(s)
    s.label('yes').msg(pressed).compare(VAR, 0).jump('on', 1)
    s.emit(41, VAR, 0).emit(31, HA).emit(30, HB)
    for o in closed0:
        s.emit(100, o)
    for o in closed1:
        s.emit(101, o)
    end(s)
    s.label('on').emit(41, VAR, 1).emit(30, HA).emit(31, HB)
    for o in closed0:
        s.emit(101, o)
    for o in closed1:
        s.emit(100, o)
    end(s)
    return s.finish()


def patch(rom, source):
    assert (OX, OZ) == (18, 20), (OX, OZ)
    trainer_alloc.assert_flags_free(rom, [HA, HB])
    switch_lines = [my.flat(source, 'PokemonMansion2F', '_PokemonMansion2F' + k) for k in ('SwitchText', 'SwitchPressedText', 'SwitchNotPressedText')]
    switch_lines[0] = switch_lines[0].replace('\x00', '')
    report = {}
    for f in my.NAMES:
        edit = ExtEdit(rom, FIRST_MAP + f - 1)
        W, H = my.BLOCKS[f]
        _, walk = cf.load(source, my.NAMES[f], W, H, 'facility', cf.FACILITY_COLL, {(bx, by): my.EMPTY for by, bx, _ in my.GATES[f]})
        taken = {struct.unpack_from('<H', a, 0)[0] for a in edit.groups[1]}
        used = {struct.unpack_from('<2H', a, 24) for a in edit.groups[1]}
        nxt = max(taken) + 1
        closed0, closed1, gate_tiles = [], [], []
        for by, bx, closed in my.GATES[f]:
            h, w = len(walk), len(walk[0])
            ok = lambda sx, sy: 0 <= sx < w and 0 <= sy < h and walk[sy][sx]
            x0, z0 = OX + SC * 2 * bx, OZ + SC * 2 * by
            edge = set()                                   # the block's own edge tiles next to every open neighbour step: nothing can get in from any side
            for i in range(2):
                if ok(2 * bx + i, 2 * by - 1): edge |= {(x0 + 2 * i + d, z0) for d in range(SC)}
                if ok(2 * bx + i, 2 * by + 2): edge |= {(x0 + 2 * i + d, z0 + 3) for d in range(SC)}
                if ok(2 * bx + 2, 2 * by + i): edge |= {(x0 + 3, z0 + 2 * i + d) for d in range(SC)}
                if ok(2 * bx - 1, 2 * by + i): edge |= {(x0, z0 + 2 * i + d) for d in range(SC)}
            tiles, axis = sorted(edge), 'edge'
            for tile in tiles:
                assert tile not in used, (f, tile, 'occupied')
                used.add(tile)
                edit.groups[1].append(actor(nxt, ROCK, 0, tile[0], tile[1], HA if closed == 0 else HB, 0))
                (closed0 if closed == 0 else closed1).append(nxt)
                nxt += 1
            gate_tiles.append(((x0, z0), axis))
        # the old gate triggers (4x4) go
        before = len(edit.groups[3])
        edit.groups[3] = [t for t in edit.groups[3] if struct.unpack_from('<2h2H', t, 2) not in {(x, z, SC * 2, SC * 2) for (x, z), _ in gate_tiles}]
        removed = before - len(edit.groups[3])
        assert removed == len(my.GATES[f]), (f, removed)
        # the statues: talk events -> actors on the same tiles
        spots = {(OX + SC * sx + dx, OZ + SC * sy + 1) for sx, sy in my.STATUES[f] for dx in range(SC)}
        old = [b for b in edit.groups[0] if struct.unpack_from('<2i', b, 4) in spots]
        assert len(old) == len(spots), (f, len(old), len(spots))
        edit.groups[0] = [b for b in edit.groups[0] if b not in old]
        first = edit.message(switch_lines[0])
        edit.message(switch_lines[1])
        edit.message(switch_lines[2])
        script = edit.script(lambda add: statue_script((first, first + 1, first + 2), closed0, closed1))
        for tile in sorted(spots):
            assert tile not in used, (f, tile, 'occupied')
            edit.groups[1].append(actor(nxt, STATUE_SPRITE, script, tile[0], tile[1], 0, 1))
            nxt += 1
        edit.set_level_script(edit.script(lambda add: entry_script()))
        edit.save()
        report[f] = dict(rocks0=len(closed0), rocks1=len(closed1), statues=len(spots), triggers_removed=removed, actors=len(edit.groups[1]))
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
