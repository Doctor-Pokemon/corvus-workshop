"""Cinnabar Island rebuilt, phase B2: events of map 57 for the new island (owner order 2026-11-08), Yellow's content.
Warps of map 57 (index = anchor used by the interiors): 0 Pokemon Center door (1039,502) -> map 508 (unchanged, so its exit still lands here), 1 arrival marker (1034,493) for the Pokemon Mansion's eight exit tiles (map 575 warps 8-15 point at map 57 anchor 1),
2 Mansion door (1034,492) -> map 575 anchor 1, 3 Gym door (1048,492) -> map 457 (Blaine's gym) anchor 0, whose own exit warp now returns to map 57 anchor 3. The Seafoam stand-in doors of that gym (map 146 warps 4 and 5, the last two) are removed, so the gym can only be entered from Cinnabar.
The step trigger that used to lead into the Mansion (1032,503) is gone. Yellow's script: Cinnabar Gym's door is locked without the SECRET KEY (item 872): a trigger on the tile in front of the door (1048,493) says "The door is locked..." and walks the player one step back (CinnabarIslandDefaultScript).
Signs (blocked tiles with a board model): town, Pokemon Center, Mart, Pokemon Lab, Gym with Yellow's texts; two talkers: the girl (sprite 319) and the gambler stand-in (balding man 342) with Yellow's lines. The native actors (Blue, Blaine, the unknown sprite-87 actor) keep their scripts and flags and are moved to
three blocked tiles inside the Mansion's footprint ((1032..1034,488)) so they cannot be reached (owner: Blue 'somewhere safe for now'). Usage (from yellow-heartgold, PYTHONPATH=tools): cinnabar_events.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import yellow_text
import cinnabar_town as town
from map_edit import MapEdit
from opening import Script, actor, end, events_decode, events_encode

MAP, GYM_MAP, SEAFOAM = 57, 457, 146
WORLD = (1024, 480)
SECRET_KEY = 872
SIGN_TEXT = {'mart': ("All your item needs fulfilled! POKEMON MART", ), 'center': ("Heal Your POKEMON! POKEMON CENTER", ), 'lab': ("POKEMON LAB", )}
GIRL, OLDMAN = 319, 342
SAFE = [(1032, 488), (1033, 488), (1034, 488)]          # inside the Mansion footprint (x 6..12, z 6..11 -> global 1030..1036, 486..491)


def g(tile):
    return WORLD[0] + tile[0], WORLD[1] + tile[1]


def patch(rom, source):
    edit = MapEdit(rom, MAP)
    text = lambda label: yellow_text.message(source, 'CinnabarIsland', label)
    msgs = {
        'town': edit.message(text('_CinnabarIslandSignText')),
        'center': edit.message('Heal Your POKEMON!\rPOKEMON CENTER'.replace('\r', ' ')),
        'mart': edit.message('All your item needs fulfilled! POKEMON MART'),
        'lab': edit.message('POKEMON LAB'),
        'gym': edit.message(text('_CinnabarIslandGymSignText')),
        'girl': edit.message(text('_CinnabarIslandGirlText')),
        'gambler': edit.message(text('_CinnabarIslandGamblerText')),
        'locked': edit.message(text('_CinnabarIslandDoorIsLockedText')),
    }
    sign = {k: edit.script(lambda add, m=msgs[k]: end(Script().emit(96).msg(m)).finish()) for k in ('town', 'center', 'mart', 'lab', 'gym')}
    girl = edit.script(lambda add: end(Script().emit(96).emit(104).msg(msgs['girl'])).finish())
    gambler = edit.script(lambda add: end(Script().emit(96).emit(104).msg(msgs['gambler'])).finish())

    def lock(add):
        s = Script().emit(96).emit(128, SECRET_KEY, 1, 0x800C).compare(0x800C, 1).jump('open', 1)
        s.msg(msgs['locked']).movement(255, 'back').emit(95)
        end(s)
        s.label('open')
        end(s)
        s.moves('back', [(13, 1)])
        return s.finish()
    lock_script = edit.script(lock)
    gm = edit.groups
    # signs
    gm[0] = [struct.pack('<I2iiI', sign[k], *g(town.SIGNS[k]), 0, 4) for k in ('town', 'center', 'mart', 'lab', 'gym')]
    # native actors to safe tiles, new talkers
    assert len(gm[1]) == 3
    for i, tile in enumerate(SAFE):
        a = bytearray(gm[1][i])
        struct.pack_into('<2H', a, 24, *tile)
        gm[1][i] = bytes(a)
    gm[1].append(actor(3, GIRL, girl, *g((17, 11)), 0, 1))
    gm[1].append(actor(4, OLDMAN, gambler, *g((15, 9)), 0, 1))
    # warps
    old = [struct.unpack_from('<4HI', w) for w in gm[2]]
    assert old[0][:4] == (1039, 502, 508, 0) and old[1][:4] == (1032, 506, 57, 1), old
    doors = {k: g(v) for k, v in town.build_layout()[3].items()}
    assert doors['center'] == (1039, 502)
    gm[2] = [struct.pack('<4HI', 1039, 502, 508, 0, 0),
             struct.pack('<4HI', doors['mansion'][0], doors['mansion'][1] + 1, 57, 1, 0),
             struct.pack('<4HI', *doors['mansion'], 575, 1, 0),
             struct.pack('<4HI', *doors['gym'], GYM_MAP, 0, 0)]
    # trigger in front of the gym door
    gm[3] = [struct.pack('<Hhh5H', lock_script, doors['gym'][0], doors['gym'][1] + 1, 1, 1, 0, 0, 0)]
    edit.save()
    # the gym: its exit now returns to Cinnabar (anchor 3 = the gym door); the Seafoam doors are gone
    gym = MapEdit(rom, GYM_MAP)
    w = struct.unpack_from('<4HI', gym.groups[2][0])
    assert w[:3] == (14, 25, SEAFOAM), w
    gym.groups[2][0] = struct.pack('<4HI', w[0], w[1], MAP, 3, 0)
    gym.save()
    sea = MapEdit(rom, SEAFOAM)
    ws = [struct.unpack_from('<4HI', x) for x in sea.groups[2]]
    assert [x[2] for x in ws[4:]] == [GYM_MAP, GYM_MAP], ws
    sea.groups[2] = sea.groups[2][:4]
    sea.save()
    return dict(map=MAP, signs=sign, girl=girl, gambler=gambler, lock=lock_script, doors=doors, gym_exit=(MAP, 3))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
