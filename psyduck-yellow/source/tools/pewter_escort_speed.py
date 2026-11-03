"""Prototype 0164: the Pewter guide's Brock escort is faster and ends cleanly (owner orders 2026-11-03).
 - Speed: 2x on the straights (movement "fast" 16-19, 8 frames per tile) and normal speed (12-15, 16 frames) around every corner: the tile before the turn, the turn itself and the tile after. Guide and player use the same speed on every step.
 - The old script gave one movement command per tile; each command costs a few frames, which cancelled most of a speed-up. The route is now one run-length encoded movement list per actor.
 - After "go take on BROCK!" the guide walks back along the escort route; the script waits while he leaves the screen at the same speeds as on the way (2x on straights, normal around corners), then control returns to the player, so the player cannot catch up with him, and he hurries the rest of the way to his post at the fastest step (84-87, 2 frames per tile) without being waited for. He keeps guiding on every try to leave east until Brock is beaten (as in Yellow, where he is put back on his post).
 - The hide flag 0xA7E (switched off, not deleted: his actor, script and position stay in the map) is set by the map-load script only once the Boulder Badge is owned and cleared otherwise.
0xA7E was unused in every script bank and actor list of the ROM and in the tools (checked 2026-11-03).
Usage (from yellow-heartgold, PYTHONPATH=tools): pewter_escort_speed.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, end, events_decode, events_encode, script_bank
from parcel_quest import split_bank
from viridian_tutorial import TABLE
import pewter_guide_fix as P

MAP = 51
GUIDE = 12                    # the guide's actor id in the map's event file
HIDE = 0xA7E                  # set = the guide is switched off
NORMAL, FAST = 12, 16         # first movement code of the 4-direction groups (N, S, W, E): 16 frames and 8 frames per tile
FASTEST = 84                  # the 2-frames-per-tile group, for the guide's walk home
OFF_X, OFF_Z = 12, 10         # tiles from the player at the Gym at which the guide is certainly off the 16x12-tile screen

ROUTE = P.PATH['escort']
BACK = P.PATH['return']
FINISH = P.PATH['player_finish']


def corner(path, i):
    return i >= 2 and P.step(path[i - 1], path[i]) != P.step(path[i - 2], path[i - 1])


def base(path, i):
    """Normal speed from the tile before a turn to the tile after it, fast on the straights."""
    return NORMAL if any(corner(path, j) for j in (i - 1, i, i + 1) if 1 <= j < len(path)) else FAST


def rle(codes):
    out = []
    for c in codes:
        if out and out[-1][0] == c:
            out[-1] = (c, out[-1][1] + 1)
        else:
            out.append((c, 1))
    return out


def leave_steps():
    for i, tile in enumerate(BACK):
        if abs(tile[0] - FINISH[0]) >= OFF_X or abs(tile[1] - FINISH[1]) >= OFF_Z:
            return i
    raise ValueError('the return path never leaves the screen')


def lists():
    n = leave_steps()
    lead = rle([base(ROUTE, i) + P.step(ROUTE[i - 1], ROUTE[i]) - 12 for i in range(1, len(ROUTE))])
    follow = rle([base(ROUTE, i) + (14 if i == 1 else P.step(ROUTE[i - 2], ROUTE[i - 1])) - 12 for i in range(1, len(ROUTE))])
    leave = rle([base(BACK, i) + P.step(BACK[i - 1], BACK[i]) - 12 for i in range(1, n + 1)])
    home = rle([FASTEST + P.step(BACK[i - 1], BACK[i]) - 12 for i in range(n + 1, len(BACK))])
    return lead, follow, leave, home


def escort():
    lead, follow, leave, home = lists()
    s = Script().emit(96).emit(294, 8, 0x800C).compare(0x800C, 1).jump('open', 1)
    s.msg(0).emit(105, 0x4000, 0x4001)
    # Manual interaction can originate on any side of the guide. Move onto
    # the east lane before joining the same single-file escort.
    s.compare(0x4000, 1084).jump('from_west', 1)
    s.compare(0x4000, 1085).jump('from_vertical', 1)
    for z in range(101, 107): s.compare(0x4001, z).jump(f'lane{z}', 1)
    s.jump('lane104')
    for z in range(101, 107): s.label(f'lane{z}').movement(255, f'align{z}').emit(95).jump('walk')
    s.label('from_west').movement(255, 'align_west').emit(95).jump('walk')
    s.label('from_vertical').compare(0x4001, 103).jump('from_north', 1)
    s.movement(255, 'align_south').emit(95).jump('walk')
    s.label('from_north').movement(255, 'align_north').emit(95).jump('walk')
    s.label('walk')
    s.movement(GUIDE, 'lead_all').movement(255, 'follow_all').emit(95)
    s.movement(GUIDE, 'face').movement(255, 'face').emit(95).msg(1)
    s.movement(GUIDE, 'leave').emit(95)                 # control stays locked until he is off the screen
    s.movement(GUIDE, 'home')                           # no WaitMovement: he hurries home by himself
    end(s)
    s.label('open').msg(2); end(s)
    s.moves('align_west', [(13, 1), (15, 2), (12, 1)])
    s.moves('align_north', [(15, 1), (13, 1)])
    s.moves('align_south', [(15, 1), (12, 1)])
    for z in range(101, 107): s.moves(f'align{z}', [(13, 104 - z)] if z < 104 else [(12, z - 104)] if z > 104 else [(2, 1)])
    s.moves('lead_all', lead)
    s.moves('follow_all', follow)
    s.moves('face', [(0, 1)])
    s.moves('leave', leave)
    s.moves('home', home)
    return s.finish()


def init(badge_hides):
    """The map-load script of pewter_guide_fix.patch, plus (new) the hide flag that follows the Boulder Badge."""
    s = Script().emit(31, P.TICKET).emit(294, 8, P.STATE).compare(P.STATE, 1).jump('after', 1).emit(41, P.STATE, 0)
    if badge_hides: s.emit(31, HIDE)
    s.jump('done').label('after').emit(41, P.STATE, 1)
    if badge_hides: s.emit(30, HIDE)
    return s.label('done').emit(2).finish()


def patch(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    fid, eid_file = rom.filenames.idOf('a/0/1/2'), rom.filenames.idOf('a/0/3/2')
    scripts, events = ndspy.narc.NARC(rom.files[fid]), ndspy.narc.NARC(rom.files[eid_file])
    rec = TABLE + MAP * 24
    sid = struct.unpack_from('<H', d, rec + 6)[0]
    eid = struct.unpack_from('<H', d, rec + 16)[0]
    bank = split_bank(scripts.files[sid])
    assert bank[0] == P.escort(), 'map 51 script 1 is not the escort written by pewter_guide_fix.py'
    old_init = init(False)
    assert bank[-1].startswith(old_init) and not any(bank[-1][len(old_init):]), 'map 51 map-load script is not the one written by pewter_guide_fix.py'   # split_bank pads each script to 4 bytes
    bank[0], bank[-1] = escort(), init(True)
    scripts.files.append(script_bank(bank))
    struct.pack_into('<H', d, rec + 6, len(scripts.files) - 1)
    groups = events_decode(events.files[eid])
    rows = [i for i, row in enumerate(groups[1]) if struct.unpack_from('<H', row)[0] == GUIDE]
    assert len(rows) == 1 and struct.unpack_from('<7H', groups[1][rows[0]], 0)[4] == 0, 'the guide actor already has a flag'
    row = bytearray(groups[1][rows[0]])
    struct.pack_into('<H', row, 8, HIDE)
    groups[1][rows[0]] = bytes(row)
    events.files.append(events_encode(groups))
    struct.pack_into('<H', d, rec + 16, len(events.files) - 1)
    rom.files[fid], rom.files[eid_file] = scripts.save(), events.save()
    rom.arm9 = main.save(compress=True)
    lead, follow, leave, home = lists()
    return dict(map=MAP, script=len(scripts.files) - 1, event=len(events.files) - 1, flag=hex(HIDE), lead_runs=len(lead), follow_runs=len(follow), leave_steps=leave_steps(), leave_runs=len(leave), home_steps=len(BACK) - 1 - leave_steps(), home_runs=len(home))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
