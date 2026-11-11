"""EXPERIMENT, DOES NOT TAKE EFFECT (tested 2026-11-08): the edited file is saved correctly (pixels and palettes verified by reloading), but in game sprite id 1023 still draws its original Pokemon, even with a striped test pattern in every frame: the sprite id is NOT simply the file index into a/0/8/1 (or another table/cache is used). Not in the build chain. Needs the id -> graphics table reverse-engineered first.
Prototype 0198 idea: a placeable STATUE object sprite (owner request 2026-11-08: "use the Gym Statue visual to create a new NPC to use as placeable statues which could run scripts like other NPCs/props"; the gym statues themselves are baked into the gym floor models, so this is a redraw).
Overworld sprites live in a/0/8/1: one NSBTX per sprite id (the Pokemon-style ones, 4544 bytes, are eight 32x32 4-bit frames 'tsure_poke.N' and two 16-colour palettes, index 0 transparent). A slot nothing uses (default 1023, unused by every actor in the ROM)
is overwritten: the same statue picture in all eight frames, in both palettes. Place it like any NPC: actor(obj, STATUE_SPRITE, script, x, z, flag, facing); it blocks, runs its script, can be hidden by a flag.
The art is drawn with PIL (a stone figure with a horn on a blue pedestal with a gold plaque) and is a stand-in until a better picture is drawn.
Usage (from yellow-heartgold, PYTHONPATH=tools): statue_sprite.py <in.nds> <out.nds> [preview.png]"""
import sys
import ndspy.narc
import ndspy.rom
import ndspy.texture
from PIL import Image, ImageDraw

SLOT = 1023
PALETTE = [(255, 0, 255), (36, 36, 52), (150, 152, 164), (210, 212, 224), (92, 94, 112), (72, 104, 176), (124, 156, 226), (40, 62, 116), (236, 196, 72)] + [(36, 36, 52)] * 7


def art():
    im = Image.new('P', (32, 32), 0)
    d = ImageDraw.Draw(im)
    # pedestal
    d.rectangle([4, 22, 27, 30], fill=1)
    d.rectangle([5, 23, 26, 29], fill=5)
    d.rectangle([5, 23, 26, 24], fill=6)
    d.rectangle([5, 28, 26, 29], fill=7)
    d.rectangle([13, 25, 18, 27], fill=8)
    # figure: body, head, horn, arms, tail
    d.ellipse([8, 10, 23, 23], fill=1)
    d.ellipse([9, 11, 22, 22], fill=2)
    d.ellipse([11, 12, 18, 19], fill=3)
    d.rectangle([9, 20, 22, 22], fill=4)
    d.ellipse([10, 3, 21, 13], fill=1)
    d.ellipse([11, 4, 20, 12], fill=2)
    d.polygon([(15, 0), (13, 5), (18, 5)], fill=1)
    d.polygon([(15, 1), (14, 5), (17, 5)], fill=3)
    d.rectangle([13, 7, 14, 8], fill=1)
    d.rectangle([17, 7, 18, 8], fill=1)
    d.rectangle([14, 10, 17, 10], fill=4)
    d.rectangle([5, 13, 9, 19], fill=1)
    d.rectangle([6, 14, 8, 18], fill=2)
    d.rectangle([22, 13, 26, 19], fill=1)
    d.rectangle([23, 14, 25, 18], fill=2)
    flat = [c for rgb in PALETTE for c in rgb]
    im.putpalette(flat + [0] * (768 - len(flat)))
    return im


def encode(im):
    px = im.load()
    out = bytearray()
    for y in range(32):
        for x in range(0, 32, 2):
            out.append(px[x, y] | (px[x + 1, y] << 4))               # low nibble = left pixel
    return bytes(out)


def patch(rom, source=None, slot=SLOT, preview=None):
    narc = ndspy.narc.NARC(rom.getFileByName('a/0/8/1'))
    tex = ndspy.texture.NSBTX(narc.files[slot])
    assert len(tex.textures) == 8 and len(tex.palettes) == 2 and all((t.width, t.height, int(t.format)) == (32, 32, 3) for _, t in tex.textures), 'not a Pokemon-style sprite slot'
    im = art()
    data = encode(im)
    for _, t in tex.textures:
        t.data1 = bytearray(data)
    for _, p in tex.palettes:
        cls = type(p.colors[0])
        p.colors = [cls(r=r >> 3, g=g >> 3, b=b >> 3, a=0) for r, g, b in PALETTE]
    narc.files[slot] = tex.save()
    rom.setFileByName('a/0/8/1', narc.save())
    if preview:
        rgba = im.convert('RGBA')
        px = rgba.load()
        for y in range(32):
            for x in range(32):
                if im.getpixel((x, y)) == 0:
                    px[x, y] = (0, 0, 0, 0)
        rgba.resize((256, 256), Image.NEAREST).save(preview)
    return dict(slot=slot, bytes=len(narc.files[slot]))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, preview=sys.argv[3] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
