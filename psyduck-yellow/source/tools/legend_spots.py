"""Prototype 0245: themed legendary spots in EXISTING native Johto maps (owner 2026-11-12: "go ahead with choosing and implementing themed spots first... I like the ideas... especially Celebi at Ilex Shrine"; Mew and Arceus wait).
Built from ROM 0244. No new maps: each legendary is ONE extra overworld actor in a map HeartGold already has.
 - Spots: see SPOTS (species, map, tile, Johto badges needed). Unlocked when the first Hall of Fame is done (HOFN var 0x413E >= 1) AND the player has that many Johto badges AND the species is NOT already registered as caught
   (CheckMonCaught, script command 336 of ROM 0243). So a legendary you caught never shows up again, and one you only met / fled from / knocked out comes back the next time you enter the map.
 - Map entry: the map header's map-entry script (type 2 row; added when the map has none) is replaced by a small script that counts the Johto badges, decides, sets / clears the actor's hide flag and then continues
   with the map's original entry script (GoTo, so its End still ends it). Hide flags 0xAC0.. (free: no script argument, event field or ARM word uses them; recomputed on every map entry, so the daily-flag range is harmless).
 - Talk script: cry, then WildBattle at level 60 + 5 x Johto badges (the Embedded Tower's own formula), then: caught -> the actor is hidden for good (the Pokedex check keeps it away), anything else -> the actor leaves for now (it is back next time the map is entered).
   A lost fight is the usual white-out.
 - Overworld sprites: none of these species has an overworld model in HeartGold (only the Hoenn trio, Lugia, Ho-Oh, the beasts, ... do), so each gets a 32 x 32 person-style model made from its own party / menu ICON (owner 2026-11-12: "we can't just use their Pokemon menu screen icons in the overworld?"; the first version scaled the 80 x 80 battle fronts down),
   its two icon frames alternating in every row, borrowed onto an UNUSED
   person sprite id (the same method as Lorelei / Agatha, tools/elite_four_overworld.py): the id is unused by every actor in every event file and its model file is referenced by one table entry only.
Usage (from yellow-heartgold, PYTHONPATH=tools): legend_spots.py <in 0244.nds> <out.nds> [<preview.png>]"""
import collections
import os
import struct
import sys
import ndspy.color
import ndspy.narc
import ndspy.rom
import ndspy.texture
from PIL import Image
from elite_four_overworld import TABLE as SPRITE_TABLE, model_bytes
from map_edit import MapEdit
from opening import Script, events_decode
from viridian_tutorial import TABLE

HOFN = 0x413E
FIRST_FLAG = 0xAC0
FOLLOWER_BASE = 2500                             # overworld sprite id of a species' FOLLOWER model = 2500 + species (HeartGold has one for every species 1-493; overlay 131 table rows 2501-2993)
LEVEL_BASE, LEVEL_PER_BADGE = 60, 5
COUNT = 0x8005                                   # talk script: Johto badge count (script-local variable)
E_COUNT, E_TMP = 0x4001, 0x4002                  # map-entry script: the same, in work variables (0x8005 / 0x800C froze the entry context)

# name -> species, map, tile (x, z), badges needed
SPOTS = {
    'celebi':    dict(species=251, map=117, tile=(15, 56),   badges=2),         # Ilex Forest, in front of the shrine
    'regirock':  dict(species=377, map=154, tile=(26, 15),   badges=4),       # Union Cave
    'regice':    dict(species=378, map=239, tile=(23, 11),   badges=5),      # Ice Path, deepest floor
    'registeel': dict(species=379, map=251, tile=(26, 55),   badges=6),      # Mt. Mortar
    'uxie':      dict(species=480, map=113, tile=(437, 267), badges=6),         # Ruins of Alph, outside the ruin door
    'mesprit':   dict(species=481, map=88,  tile=(505, 60),  badges=7),         # Lake of Rage
    'azelf':     dict(species=482, map=154, tile=(9, 27),    badges=8),         # Union Cave
}


def icon_frames(rom, species):
    """The species' party / menu icon: two 32 x 32 RGBA frames (a/0/2/0 file 7 + species = 16 tiles of 8 x 8 per frame, low nibble first; palette = one of the three 16-colour banks of file 0 chosen by a/0/2/8 file 9 [species])."""
    icons = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/0')])
    banks = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/8')]).files[9]
    raw = struct.unpack_from('<48H', icons.files[0], 16 + 0x18)
    bank = banks[species]
    pal = [tuple(((c >> sh) & 31) * 255 // 31 for sh in (0, 5, 10)) for c in raw[bank * 16:(bank + 1) * 16]]
    f = bytes(icons.files[7 + species])
    assert f[:4] == b'RGCN' and len(f) == 16 + 0x20 + 1024, (species, len(f))
    data = f[16 + 0x20:]
    frames = []
    for fr in range(2):
        im = Image.new('RGBA', (32, 32))
        px = im.load()
        for t in range(16):
            for y in range(8):
                for x in range(8):
                    i = fr * 512 + t * 32 + y * 4 + x // 2
                    n = (data[i] >> 4) if x & 1 else (data[i] & 15)
                    if n:
                        px[(t % 4) * 8 + x, (t // 4) * 8 + y] = pal[n] + (255,)
        frames.append(im)
    return frames


def borrowable(rom, count):
    """Unused person-model sprite ids: -> [(sprite id, model file)] whose model is 16 textures of 32 x 32 with one palette."""
    overlays = rom.loadArm9Overlays()
    table = overlays[131]
    at = SPRITE_TABLE - table.ramAddress
    rows = []
    while True:
        r = struct.unpack_from('<3H', table.data, at + 6 * len(rows))
        if r[0] == 0xFFFF:
            break
        rows.append(r)
    refs = collections.Counter(r[1] for r in rows)
    used = collections.Counter()
    for f in ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')]).files:
        try:
            for a in events_decode(bytes(f))[1]:
                used[struct.unpack_from('<H', a, 2)[0]] += 1
        except ValueError:
            continue
    models = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/8/1')])
    out = []
    for sprite, model, _ in rows:
        if sprite < 126 or sprite > 300 or used[sprite] or refs[model] != 1:       # the Sinnoh leader / trainer block 126-300 holds the unused person models
            continue
        try:
            tex = ndspy.texture.NSBTX(bytes(models.files[model]))
        except Exception:
            continue
        if len(tex.textures) == 16 and len(tex.palettes) == 1 and all((t.width, t.height) == (32, 32) for _, t in tex.textures):
            out.append((sprite, model))
        if len(out) == count:
            return out
    raise ValueError('not enough unused person models')


def sheet_of(frames):
    """4 x 4 grid of 32 x 32 frames: every row (up / down / left / right) the icon's two frames alternating, so a walking cycle bobs."""
    sheet = Image.new('RGBA', (128, 128))
    for r in range(4):
        for c in range(4):
            sheet.alpha_composite(frames[c % 2], (c * 32, r * 32))
    return sheet


def entry_script(spot, flag, with_goto):
    """Map-entry script: set / clear the hide flag; with_goto -> ends in `GoTo <placeholder rel32>` (patched by the caller), else End."""
    stage = int(os.environ.get('LEGEND_STAGE', '9'))                              # test switch: bisect a hang (9 = everything)
    s = Script()
    if stage >= 3:
        s.emit(41, E_COUNT, 0)
        for badge in range(8):
            s.emit(294, badge, E_TMP).emit(39, E_COUNT, E_TMP)                     # CheckBadge, AddVar
    if stage >= 2:
        s.compare(HOFN, 1).jump('hide', 0)                                         # no Hall of Fame yet (< 1)
    if stage >= 3:
        s.compare(E_COUNT, spot['badges']).jump('hide', 0)                           # not enough Johto badges
    if stage >= 4:
        s.emit(336, spot['species'], E_TMP).compare(E_TMP, 1).jump('hide', 1)    # already caught
    if stage >= 1:
        s.emit(31, flag).jump('done')                                              # show
        s.label('hide').emit(30, flag)
        s.label('done')
    if with_goto:
        s.emit(22)
        s.data.extend(bytes(4))                                                    # relative target, patched later
    else:
        s.emit(2)
    return s


def talk_script(spot, flag, actor_id):
    s = Script()
    s.emit(96).emit(104)                                                           # LockAll, FacePlayer
    s.emit(76, spot["species"], 0).emit(77)                                        # PlayCry, WaitCry (no text: several of these maps have a full 255-row text bank)
    s.emit(41, 0x8004, LEVEL_BASE)
    s.emit(41, COUNT, 0)
    for badge in range(8):
        s.emit(294, badge, 0x800C).emit(39, COUNT, 0x800C)
    for _ in range(LEVEL_PER_BADGE):
        s.emit(39, 0x8004, COUNT)                                                  # level = 60 + 5 x badges
    s.emit(589, spot['species'], 0x8004).data.append(0)                           # WildBattle
    s.emit(220, 0x800C).compare(0x800C, 0).jump('lost', 1)                         # CheckBattleWon
    s.emit(30, flag).emit(101, actor_id)                                           # SetFlag hide, HidePerson (caught: the entry script keeps it away; otherwise it is back on the next entry)
    s.emit(97).emit(2)
    s.label('lost')
    s.emit(219).emit(97).emit(2)
    return s


def script_start(bank, n):
    return struct.unpack_from('<I', bank, 4 * (n - 1))[0] + 4 * (n - 1) + 4


def patch(rom, preview=None):
    report = {}
    if os.environ.get('LEGEND_SPRITES') == 'icons':                                # the 0246 variant: borrowed person models with the menu icons
        pool = borrowable(rom, len(SPOTS))
        models_id = rom.filenames.idOf('a/0/8/1')
        models = ndspy.narc.NARC(rom.files[models_id])
        for k, (name, spot) in enumerate(SPOTS.items()):
            sprite, model = pool[k]
            data, pixels, words = model_bytes(bytes(models.files[model]), sheet_of(icon_frames(rom, spot['species'])))
            models.files[model] = data
            spot.update(sprite=sprite, model=model, flag=FIRST_FLAG + k)
            report[name] = dict(sprite=sprite, model=model, flag=spot['flag'])
        rom.files[models_id] = models.save()
    else:                                                                          # the species' own follower model, nothing borrowed
        for k, (name, spot) in enumerate(SPOTS.items()):
            spot.update(sprite=FOLLOWER_BASE + spot['species'], flag=FIRST_FLAG + k)
            report[name] = dict(sprite=spot['sprite'], flag=spot['flag'])
    for name, spot in SPOTS.items():
        e = MapEdit(rom, spot['map'])
        actors = e.groups[1]
        actor_id = max(struct.unpack_from('<H', a, 0)[0] for a in actors) + 1
        talk = e.script(lambda add: talk_script(spot, spot['flag'], actor_id).finish())
        rec = bytearray(32)
        struct.pack_into('<7H', rec, 0, actor_id, spot['sprite'], 0, 0, spot['flag'], talk, 1)
        struct.pack_into('<HH', rec, 24, *spot['tile'])
        if not os.environ.get('LEGEND_NOACTOR'):                               # test switch: bisect a hang
            actors.append(bytes(rec))
        # map-entry script: ours first, then the map's original one (when it has one)
        header_id = struct.unpack_from('<H', e.d, e.at + 8)[0]
        header = bytes(e.scripts.files[header_id])
        rows, at = [], 0
        while header[at] != 0:
            rows.append((header[at], struct.unpack_from('<I', header, at + 1)[0]))
            at += 5
        tail = header[at:]
        original = next((v for t, v in rows if t == 2), None)
        built = entry_script(spot, spot['flag'], original is not None)
        code = built.finish()
        entry = e.script(lambda add: code)
        if original is not None:
            new_start, old_start = script_start(e.bank, entry), script_start(e.bank, original)
            fix = new_start + len(code) - 4                           # the rel32 of the final GoTo
            struct.pack_into('<i', e.bank, fix, old_start - (fix + 4))
            rows = [(2, entry) if t == 2 else (t, v) for t, v in rows]
        else:
            rows = sorted(rows + [(2, entry)])
        if not os.environ.get('LEGEND_NOENTRY'):                               # test switch: bisect a hang
            e.scripts.files.append(b''.join(struct.pack('<BI', t, v) for t, v in rows) + tail)
            struct.pack_into('<H', e.d, e.at + 8, len(e.scripts.files) - 1)
        e.save()
        report[name].update(actor=actor_id, talk=talk, entry=entry, map=spot['map'], original_entry=original)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
