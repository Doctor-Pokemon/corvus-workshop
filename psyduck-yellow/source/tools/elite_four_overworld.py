"""Prototype 0241: the Kanto Elite Four rooms show the RIGHT people (owner 2026-11-12: "can we replace their overworld sprites, too?").
Built from ROM 0240. Facts: the Indigo Plateau rooms 301-304 hold ONE trainer actor each (script 2), with HeartGold's Johto sprite: Will 360, Koga 361, Bruno 362, Karen 363 (champion room 305: Blue 375 / Lance 364 already
come as TWO actors hidden by the league-mode flags). So in the Kanto league you met Will's, Koga's, Bruno's and Karen's sprites as Lorelei, Bruno, Agatha and Lance.
 - Overworld sprites: a/0/8/1 member = the file named by the engine's table in overlay 131 at 0x023CA660 (6-byte entries: sprite id, file, params; ended by 0xFFFF). The table has no entry to spare, so two UNUSED person sprites
   are borrowed: id 130 (file 219, Sinnoh "leader5") becomes LORELEI and id 131 (file 220, "leader6") becomes AGATHA. Each is a 16-texture 32 x 32 model (rows up / down / left / right, four frames each) with ONE 15-colour palette; both ids
   are checked unused by every actor in every event file and their files are referenced by exactly one table entry.
 - The art: the owner's two overworld sheets (build/card-art-src/lorelei-ow.png, agatha-ow.jpg: 4 x 4 frames at twice the size, rows down / left / right / up) downscaled, bottom aligned, quantised to 15 colours + transparent.
 - The rooms: in 301-304 the existing actor (the Johto person) gets the hide flag 0x9D8 (set in Kanto league mode) and a COPY gets the hide flag 0x9FC (set in Johto mode) with the Kanto person's sprite:
   301 Lorelei (id 130), 302 Bruno (362, HeartGold's Bruno), 303 Agatha (id 131), 304 Lance (364, HeartGold's Lance). The same pattern the champion room already uses (flags 0x9FC / 0x9D8, obj id shared).
Not changed: battle sprites (tools/elite_four_classes.py), the Elite Four VS banner, Johto's people.
Usage (from yellow-heartgold, PYTHONPATH=tools): elite_four_overworld.py <in 0240.nds> <out.nds> [<preview.png>]"""
import collections
import struct
import sys
from pathlib import Path
import ndspy.color
import ndspy.narc
import ndspy.rom
import ndspy.texture
from PIL import Image
from map_edit import MapEdit
from mtmoon_art import indexed, linear
from opening import events_decode

ART = Path(__file__).resolve().parents[1] / 'build/card-art-src'
TABLE = 0x23CA660
SPRITES = {'lorelei': (130, 219), 'agatha': (131, 220)}                            # name -> (sprite id, a/0/8/1 file)
ROOMS = {301: ('lorelei', None), 302: (None, 362), 303: ('agatha', None), 304: (None, 364)}      # room -> (new art name or None, existing sprite id for the Kanto person)
KANTO_FLAG, JOHTO_FLAG = 0x9D8, 0x9FC                                              # hide flags: the actor is hidden when its flag is set
ENGINE_ROWS = (3, 0, 1, 2)                                                         # engine row (up, down, left, right) <- owner row (down, left, right, up)


def flood_background(im, threshold=236):
    """RGBA copy of an RGB cell where the background (near white, connected to the border) is transparent."""
    w, h = im.size
    px = im.load()
    seen = set()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        if min(px[x, y][:3]) < threshold:
            continue
        seen.add((x, y))
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    out = Image.new('RGBA', im.size)
    po = out.load()
    for y in range(h):
        for x in range(w):
            if (x, y) not in seen:
                po[x, y] = px[x, y][:3] + (255,)
    return out


def place(cell):
    """RGBA cell at twice the final size -> 32 x 32 RGBA frame (content halved, centred, bottom on row 30)."""
    box = cell.getchannel('A').point(lambda v: 255 if v > 127 else 0).getbbox()
    frame = Image.new('RGBA', (32, 32))
    if not box:
        return frame
    content = cell.crop(box)
    small = content.resize((max(1, round(content.width / 2)), max(1, round(content.height / 2))), Image.BOX)
    alpha = small.getchannel('A').point(lambda v: 255 if v > 127 else 0)
    small.putalpha(alpha)
    x = min(max(0, 16 - small.width // 2), 32 - small.width)
    y = min(max(0, 31 - small.height), 32 - small.height)
    frame.alpha_composite(small, (x, y))
    return frame


def sheet_frames(name):
    """-> 4 x 4 grid of 32 x 32 RGBA frames in the OWNER's row order (down, left, right, up)."""
    if name == 'lorelei':
        im = Image.open(ART / 'lorelei-ow.png').convert('RGBA')
        cells = [[im.crop((64 * c, 64 * r, 64 * c + 64, 64 * r + 64)) for c in range(4)] for r in range(4)]
    else:
        im = Image.open(ART / 'agatha-ow.jpg').convert('RGB')
        xs, ys = (0, 64, 132, 204, 272), (0, 76, 148, 220, 288)
        cells = [[flood_background(im.crop((xs[c], ys[r], xs[c + 1], ys[r + 1]))) for c in range(4)] for r in range(4)]
    return [[place(cell) for cell in row] for row in cells]


def engine_sheet(name):
    grid = sheet_frames(name)
    sheet = Image.new('RGBA', (128, 128))
    for er, orow in enumerate(ENGINE_ROWS):
        for c in range(4):
            sheet.alpha_composite(grid[orow][c], (c * 32, er * 32))
    return sheet


def model_bytes(template, sheet):
    tex = ndspy.texture.NSBTX(template)
    pixels, words = indexed(sheet)
    tex.palettes[0][1].colors = [ndspy.color.unpack(v) for v in words]
    for label, texture in tex.textures:
        n = int(label.split('.')[-1]) - 1
        x, y = n % 4 * 32, n // 4 * 32
        frame = b''.join(pixels[(y + z) * 128 + x:(y + z) * 128 + x + 32] for z in range(32))
        texture.data1 = linear(frame)
        texture.isColor0Transparent = True
    return tex.save(), pixels, words


def patch(rom, preview=None):
    overlays = rom.loadArm9Overlays()
    table = overlays[131]
    at = TABLE - table.ramAddress
    rows = []
    while True:
        r = struct.unpack_from('<3H', table.data, at + 6 * len(rows))
        if r[0] == 0xFFFF:
            break
        rows.append(r)
    by_id = {r[0]: r for r in rows}
    refs = collections.Counter(r[1] for r in rows)
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    used = collections.Counter()
    for f in events.files:
        try:
            groups = events_decode(bytes(f))
        except ValueError:
            continue
        for row in groups[1]:
            used[struct.unpack_from('<H', row, 2)[0]] += 1
    models_id = rom.filenames.idOf('a/0/8/1')
    models = ndspy.narc.NARC(rom.files[models_id])
    report, sheets = {}, []
    for name, (sprite, model) in SPRITES.items():
        assert by_id[sprite][1] == model and refs[model] == 1 and used[sprite] == 0, (name, by_id[sprite], refs[model], used[sprite])
        data, pixels, words = model_bytes(bytes(models.files[model]), engine_sheet(name))
        models.files[model] = data
        report[name] = dict(sprite=sprite, model=model)
        if preview:
            im = Image.new('RGBA', (128, 128), (110, 110, 120, 255))
            pal = [tuple(((w >> s) & 31) * 255 // 31 for s in (0, 5, 10)) for w in words]
            frame = Image.new('RGBA', (128, 128))
            frame.putdata([(0, 0, 0, 0) if v == 0 else pal[v] + (255,) for v in pixels])
            im.alpha_composite(frame)
            sheets.append(im.resize((256, 256), Image.NEAREST))
    rom.files[models_id] = models.save()
    for room, (art, existing) in ROOMS.items():
        sprite = SPRITES[art][0] if art else existing
        e = MapEdit(rom, room)
        actors = e.groups[1]
        old = bytearray(actors[0])
        assert struct.unpack_from('<H', old, 8)[0] == 0 and struct.unpack_from('<H', old, 10)[0] == 2         # the trainer actor: no flag, talk script 2
        new = bytearray(old)
        struct.pack_into('<H', new, 2, sprite)
        struct.pack_into('<H', new, 8, JOHTO_FLAG)                                                           # the Kanto person: hidden in Johto mode
        struct.pack_into('<H', old, 8, KANTO_FLAG)                                                           # the Johto person: hidden in Kanto mode
        actors[0] = bytes(old)
        actors.append(bytes(new))
        e.save()
        report[room] = dict(kanto_sprite=sprite, johto_sprite=struct.unpack_from('<H', old, 2)[0], actors=len(actors))
    if preview and sheets:
        out = Image.new('RGBA', (256 * len(sheets), 256))
        for i, s in enumerate(sheets):
            out.paste(s, (256 * i, 0))
        out.save(preview)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
