"""Cinnabar Island rebuilt, phase B3: Mart and Lab interiors (owner order 2026-11-08).
The extension header table is full (47 of 47), so the two interiors reuse two unreachable native Kanto headers that no warp leads to and that have no events (maps 401 and 406, both mapsec 148, 0 warps, 0 actors):
- map 401 becomes a clone of the Vermilion Mart's header (360: same matrix, area, script bank, text bank, level script), with its own copy of the event file whose exit warp (4,11) returns to Cinnabar (map 57 anchor 4 = the Mart door (1047,502)); mapsec 146 (Cinnabar Island);
  the clerks keep their shared-stock vendor scripts (both clerks sell, kanto_mart_shared.py / mart_clerks.py).
- map 406 becomes a clone of Oak's Lab header (505: matrix 288, area, bank, text) with an empty level script (Oak's intro runs there on flags) and a fresh event file: exit warp (8,13) -> map 57 anchor 5 (the Lab door (1031,501)), Yellow's Cinnabar Lab guru
  (CinnabarLabFishingGuruText, sprite 342) at (9,8) and the photo (CinnabarLabPhotoText) as a bg event at (9,3).
Map 57 gets the two door warps (index 4 Mart -> map 401 anchor 0, index 5 Lab -> map 406 anchor 0).
Usage (from yellow-heartgold, PYTHONPATH=tools): cinnabar_interiors.py <in.nds> <out.nds> <pokeyellow source>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import yellow_text
import cinnabar_town as town
from map_edit import MapEdit
from opening import Script, actor, end
from viridian_tutorial import TABLE

MART_SRC, LAB_SRC = 360, 505
MART, LAB, CINNABAR = 401, 406, 57
MAPSEC = 146
GURU = 342


def clone(rom, src, dst):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    old = bytes(d[TABLE + dst * 24:TABLE + dst * 24 + 24])
    assert old[1] in (0x28, 0x30) and old[18] == 148, old.hex(' ')                         # the unreachable placeholder headers
    rec = bytearray(d[TABLE + src * 24:TABLE + src * 24 + 24])
    rec[18] = MAPSEC
    d[TABLE + dst * 24:TABLE + dst * 24 + 24] = rec
    rom.arm9 = main.save(compress=True)


def empty_level_script(rom):
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    return next(i for i, f in enumerate(scripts.files) if bytes(f) == b'\0\0\0\0')


def patch(rom, source):
    clone(rom, MART_SRC, MART)
    clone(rom, LAB_SRC, LAB)
    mart = MapEdit(rom, MART)
    w = struct.unpack_from('<4HI', mart.groups[2][0])
    assert w[:3] == (4, 11, 54) and len(mart.groups[2]) == 1, w
    mart.groups[2][0] = struct.pack('<4HI', 4, 11, CINNABAR, 4, 0)
    mart.save()
    # the Lab: fresh events, empty level script
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    level = empty_level_script(rom)
    struct.pack_into('<H', d, TABLE + LAB * 24 + 8, level)
    rom.arm9 = main.save(compress=True)
    lab = MapEdit(rom, LAB)
    text = lambda label: yellow_text.message(source, 'CinnabarLab', label)
    guru_msg = lab.message(text('_CinnabarLabFishingGuruText'))
    photo_msg = lab.message(text('_CinnabarLabPhotoText'))
    guru = lab.script(lambda add: end(Script().emit(96).emit(104).msg(guru_msg)).finish())
    photo = lab.script(lambda add: end(Script().emit(96).msg(photo_msg)).finish())
    lab.groups = [[struct.pack('<I2iiI', photo, 9, 3, 0, 4)], [actor(0, GURU, guru, 9, 8, 0, 1)], [struct.pack('<4HI', 8, 13, CINNABAR, 5, 0)], []]
    lab.save()
    # Cinnabar: two more doors
    cin = MapEdit(rom, CINNABAR)
    doors = {k: town.WORLD_DOOR(v) for k, v in town.build_layout()[3].items()}
    cin.groups[2] = list(cin.groups[2]) + [struct.pack('<4HI', *doors['mart'], MART, 0, 0), struct.pack('<4HI', *doors['lab'], LAB, 0, 0)]
    assert len(cin.groups[2]) == 6
    cin.save()
    return dict(mart=MART, lab=LAB, level_script_file=level, doors={k: doors[k] for k in ('mart', 'lab')})


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
