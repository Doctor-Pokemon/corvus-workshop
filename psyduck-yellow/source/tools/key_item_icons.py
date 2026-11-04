"""Prototype 0185: real bag icons for the Running Shoes and the Silph Scope (owner 2026-11-04: the Running Shoes' "?" icon has bugged them since day one of playtesting).
The Poke Flute (651) gets the Yellow Flute's icon (item 66) instead of the Blue Flute's (owner's choice). Both key items showed the engine's "?" placeholder icon (item 113 and item 874; the whole imported Gen 5-9 item range uses the same placeholder, but these two are the Kanto progression items; the Poke Flute got the Blue Flute's icon in 0184).
Icons are item graphics (a/0/1/8 files 2*id+2 = NCGR, 2*id+3 = NCLR): 32x32, 4 bits per pixel, 4x4 tiles of 8x8 in row order (two pixels per byte, low nibble = left), a 16-colour BGR555 palette at TTLP+0x18, index 0 transparent.
Drawn with PIL on a 32x32 indexed canvas and written into copies of the engine's own icon containers (same headers and sizes as every other icon), so no other file changes.
Usage (from yellow-heartgold, PYTHONPATH=tools): key_item_icons.py <in.nds> <out.nds> [preview.png]"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from PIL import Image, ImageDraw

SHOES, SILPH_SCOPE, TEMPLATE = 113, 874, 65
POKE_FLUTE, YELLOW_FLUTE = 651, 66                 # the Poke Flute wears the Yellow Flute's icon (owner 2026-11-04; 0184 had used the Blue Flute's)

SHOE_PALETTE = [None, (46, 26, 34), (222, 52, 52), (255, 120, 108), (150, 24, 40), (250, 250, 250), (186, 196, 214), (255, 255, 236), (252, 214, 60), (84, 44, 58), (120, 120, 140), None, None, None, None, None]
SCOPE_PALETTE = [None, (30, 30, 44), (88, 96, 120), (140, 150, 176), (52, 58, 80), (70, 150, 255), (170, 220, 255), (255, 255, 255), (196, 60, 52), (230, 200, 70), None, None, None, None, None, None]


def canvas():
    im = Image.new('P', (32, 32), 0)
    return im, ImageDraw.Draw(im)


def outline(im):
    px = im.load()
    keep = [[px[x, y] for x in range(32)] for y in range(32)]
    for y in range(32):
        for x in range(32):
            if keep[y][x] == 0 and any(0 <= x + dx < 32 and 0 <= y + dy < 32 and keep[y + dy][x + dx] != 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = 1


def shoes():
    im, d = canvas()
    d.polygon([(4, 21), (4, 13), (6, 10), (10, 9), (13, 9), (15, 12), (19, 15), (25, 16), (28, 19), (28, 21)], fill=2)       # the red upper, heel left, toe right
    d.polygon([(8, 10), (12, 9), (13, 10), (11, 12), (8, 12)], fill=9)                                                       # the dark opening
    d.polygon([(4, 14), (6, 11), (7, 12), (6, 20), (4, 20)], fill=4)                                                         # heel shading
    d.line([(20, 16), (25, 17), (27, 19)], fill=3)                                                                           # toe highlight
    d.line([(14, 11), (17, 10)], fill=7)                                                                                     # laces
    d.line([(15, 13), (18, 12)], fill=7)
    d.line([(17, 15), (20, 14)], fill=7)
    d.line([(6, 19), (12, 17), (18, 18), (24, 19)], fill=8)                                                                  # the stripe
    d.line([(6, 18), (12, 16), (18, 17), (24, 18)], fill=8)
    d.polygon([(3, 21), (28, 21), (29, 23), (28, 25), (4, 25), (3, 23)], fill=5)                                             # the white sole
    d.line([(4, 25), (28, 25)], fill=6)
    d.line([(3, 23), (29, 23)], fill=6)
    for x in range(6, 28, 4):                                                                                                # tread marks
        d.point((x, 24), fill=10)
    d.line([(1, 14), (3, 14)], fill=6)                                                                                       # speed lines behind the heel
    d.line([(0, 17), (3, 17)], fill=6)
    d.line([(1, 20), (2, 20)], fill=6)
    outline(im)
    return im


def scope():
    """Binoculars: two grey barrels with blue lenses on top, a bridge with a red focus wheel between them."""
    im, d = canvas()
    for x0 in (4, 18):
        d.rounded_rectangle((x0, 9, x0 + 9, 27), radius=3, fill=2)                                                           # the barrel
        d.line([(x0 + 1, 12), (x0 + 1, 24)], fill=3)                                                                         # barrel highlight
        d.line([(x0 + 8, 12), (x0 + 8, 25)], fill=4)                                                                         # barrel shadow
        d.rectangle((x0 + 1, 24, x0 + 8, 26), fill=4)                                                                        # the eyepiece cap
        d.ellipse((x0 - 1, 3, x0 + 10, 12), fill=4)                                                                          # the lens ring
        d.ellipse((x0 + 1, 4, x0 + 8, 10), fill=5)                                                                           # the lens
        d.line([(x0 + 2, 5), (x0 + 4, 5)], fill=6)                                                                           # lens glint
        d.point((x0 + 2, 6), fill=7)
    d.rectangle((13, 14, 18, 20), fill=3)                                                                                    # the bridge
    d.line([(13, 14), (18, 14)], fill=7)
    d.rectangle((14, 16, 17, 19), fill=8)                                                                                    # the red focus wheel
    d.line([(14, 16), (17, 16)], fill=9)
    outline(im)
    return im


def encode(im, palette, template_ncgr, template_nclr):
    ncgr = bytearray(template_ncgr)
    base = bytes(ncgr).find(b'RAHC') + 0x20
    px = im.load()
    t = 0
    for ty in range(4):
        for tx in range(4):
            for y in range(8):
                for x in range(4):
                    a, b = px[tx * 8 + x * 2, ty * 8 + y], px[tx * 8 + x * 2 + 1, ty * 8 + y]
                    ncgr[base + t * 32 + y * 4 + x] = a | (b << 4)
            t += 1
    nclr = bytearray(template_nclr)
    at = bytes(nclr).find(b'TTLP') + 0x18
    for i in range(16):
        rgb = palette[i] if i < len(palette) and palette[i] else (0, 0, 0)
        struct.pack_into('<H', nclr, at + 2 * i, (rgb[0] * 31 // 255) | ((rgb[1] * 31 // 255) << 5) | ((rgb[2] * 31 // 255) << 10))
    return bytes(ncgr), bytes(nclr)


def preview(images, path):
    sheet = Image.new('RGBA', (160 * len(images), 160), (110, 130, 150, 255))
    for i, (im, pal) in enumerate(images):
        rgba = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        p, o = im.load(), rgba.load()
        for y in range(32):
            for x in range(32):
                if p[x, y]:
                    o[x, y] = tuple(pal[p[x, y]]) + (255,)
        sheet.alpha_composite(rgba.resize((128, 128), Image.NEAREST), (i * 160 + 16, 16))
    sheet.save(path)


def patch(rom, source=None):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    tn, tc = bytes(items.files[TEMPLATE * 2 + 2]), bytes(items.files[TEMPLATE * 2 + 3])
    for item, im, pal in ((SHOES, shoes(), SHOE_PALETTE), (SILPH_SCOPE, scope(), SCOPE_PALETTE)):
        items.files[item * 2 + 2], items.files[item * 2 + 3] = encode(im, pal, tn, tc)
    for k in (2, 3):
        items.files[POKE_FLUTE * 2 + k] = bytes(items.files[YELLOW_FLUTE * 2 + k])
    rom.setFileByName('a/0/1/8', items.save())
    return dict(shoes=SHOES, silph_scope=SILPH_SCOPE, poke_flute_icon_from=YELLOW_FLUTE)


if __name__ == '__main__':
    if len(sys.argv) > 3:
        preview([(shoes(), SHOE_PALETTE), (scope(), SCOPE_PALETTE)], sys.argv[3])
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
