"""Prototype 0240: LORELEI and AGATHA get their own trainer classes, so they no longer share Karen's battle sprite (owner 2026-11-12: "It's really bugging me there's three Karens in this game").
Built from ROM 0239 (card book 2). Findings (emulator, scratch ROMs): the battle shows the class' STATIC sprite = a/0/5/8 member class * 5 + 4 (two 80x80 frames, linear 4-bit, DP pokepic cipher) with the class palette (member class * 5 + 1);
CORRECTION found when the first version showed Karen's silhouette in new colours: the battle intro actually draws the class' ANIMATED sprite: member +0 (three 80 x 80 tile blocks of 3200 bytes, OBJ 1D-64K layout) assembled by the
cells of member +2 (6 OBJ parts per cell, all cells use tiles 0-49; the animation swaps the blocks), with the palette of member +1. The static +4 is written too (consistency) but is not what the battle shows. The class name text (banks 730 / 731, row = class) gives "Elite Four" in "You are challenged by Elite Four LORELEI!".
A class that has no entry in the VS-banner effect table gets the ordinary battle transition: the Elite Four VS banner (with Karen's portrait) is NOT shown for these two classes.
 - Lorelei (trainer 245, Kanto first-visit record) -> class 85 (unused HeartGold "Idol", female); Agatha (trainer 418) -> class 84 (unused "Reporter", female). Both classes are checked unused by every trainer record.
 - Their members: +0 / +2 / +3 copied from class 88, +1 palette = the new art's 16 colours (the rest of the 256-entry palette is class 88's), +4 = the owner's pixel art (build/card-art-src: lorelei.png, agatha.gif; ignored, never published) scaled to 80 px,
   bottom centred, quantised to 15 colours + transparent, in both frames; name rows 730 / 731 copied from class 88.
 Not changed: the in-room overworld sprites, the Elite Four VS banner portraits, prize money (class based; not measured for the new classes), Johto's Will / Koga / Bruno / Karen (their own classes).
Usage (from yellow-heartgold, PYTHONPATH=tools): elite_four_classes.py <in 0239.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from PIL import Image
import card_book as cb
from prototype import decode_messages, encode_messages

SOURCE_CLASS = 88
TARGETS = {245: ('lorelei', 85), 418: ('agatha', 84)}                       # trainer id -> (art name, new class)
KEY = 0x5A3C


def scramble_dp(raw):
    """DP pokepic cipher, encode side: the LAST u16 is the key and must be 0 in the picture."""
    r = list(struct.unpack('<3200H', raw))
    assert r[3199] == 0
    e = [0] * 3200
    e[3199] = KEY
    seed = KEY
    for i in range(3198, -1, -1):
        seed = (seed * 1103515245 + 24691) & 0xFFFFFFFF
        e[i] = r[i] ^ (seed & 0xFFFF)
    return struct.pack('<3200H', *e)


def unscramble_dp(data):
    a = list(struct.unpack('<3200H', data))
    seed = a[3199]
    for i in range(3199, -1, -1):
        a[i] ^= seed & 0xFFFF
        seed = (seed * 1103515245 + 24691) & 0xFFFFFFFF
    return struct.pack('<3200H', *a)


def battle_sprite(name):
    """-> (80 x 80 P image with indices 0-15, 16 RGB colours)."""
    file, box = cb.CUSTOM[name]
    im = Image.open(cb.ART_DIR / file).convert('RGB')
    if box:
        im = im.crop(box)
    bg = im.getpixel((0, 0))
    mask = Image.new('L', im.size, 0)
    px, mp = im.load(), mask.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] != bg:
                mp[x, y] = 255
    bb = mask.getbbox()
    im, mask = im.crop(bb), mask.crop(bb)
    big = im.resize((im.width * 8, im.height * 8), Image.NEAREST)
    bigm = mask.resize(big.size, Image.NEAREST)
    scale = min(80 / big.width, 80 / big.height)
    size = (max(1, round(big.width * scale)), max(1, round(big.height * scale)))
    rgb = big.resize(size, Image.BOX)
    alpha = bigm.resize(size, Image.BOX).point(lambda v: 255 if v > 127 else 0)
    flat = Image.new('RGB', size, (255, 0, 255))
    flat.paste(rgb, mask=alpha)
    q = flat.quantize(colors=15, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qp = q.getpalette()[:45]
    pal = [(0, 0, 0)] + [tuple(qp[3 * i:3 * i + 3]) for i in range(15)]
    out = Image.new('P', (80, 80), 0)
    qpx, apx = list(q.getdata()), list(alpha.getdata())
    idx = Image.new('P', size, 0)
    idx.putdata([0 if a == 0 else v + 1 for v, a in zip(qpx, apx)])
    out.paste(idx, ((80 - size[0]) // 2, 80 - size[1]))
    return out, pal


SIZES = {0: [(8, 8), (16, 16), (32, 32), (64, 64)], 1: [(16, 8), (32, 8), (32, 16), (64, 32)], 2: [(8, 16), (8, 32), (16, 32), (32, 64)]}


def parse_cells(ncer):
    """NCER cell bank -> list of cells, each a list of OBJ parts (x, y, w, h, tile number); x, y relative to the 80 x 80 picture's centre."""
    assert ncer[16:20] == b'KBEC'
    n, attr, off = struct.unpack_from('<HHI', ncer, 24)
    start, stride = 24 + off, (16 if attr == 1 else 8)
    base = start + n * stride
    cells = []
    for i in range(n):
        num, _, o = struct.unpack_from('<HHI', ncer, start + i * stride)
        parts = []
        for k in range(num):
            a0, a1, a2 = struct.unpack_from('<3H', ncer, base + o + 6 * k)
            y, x = a0 & 0xFF, a1 & 0x1FF
            y, x = y - 256 if y >= 128 else y, x - 512 if x >= 256 else x
            w, h = SIZES[a0 >> 14][a1 >> 14]
            parts.append((x, y, w, h, a2 & 0x3FF))
        cells.append(parts)
    return cells


def tile_block(cells, img):
    """80 x 80 P image (indices 0-15) -> one 3200-byte block of OBJ tiles laid out as the cells expect (all cells share the tile layout)."""
    assert all(c == cells[0] for c in cells)
    block = bytearray(3200)
    px = list(img.getdata())
    for x, y, w, h, tile in cells[0]:
        at = tile * 64
        for ty in range(h // 8):
            for tx in range(w // 8):
                for row in range(8):
                    for xb in range(4):
                        X, Y = x + 40 + tx * 8 + xb * 2, y + 40 + ty * 8 + row
                        lo, hi = px[Y * 80 + X] & 15, px[Y * 80 + X + 1] & 15
                        block[at + (ty * (w // 8) + tx) * 32 + row * 4 + xb] = lo | (hi << 4)
    return bytes(block)


def animated_file(template_ncgr, ncer, img):
    assert template_ncgr[:4] == b'RGCN' and len(template_ncgr) == 48 + 9600
    block = tile_block(parse_cells(ncer), img)
    return template_ncgr[:48] + block * 3


def static_file(template, img):
    px = list(img.getdata())
    raw = bytearray()
    for y in range(80):
        row = px[y * 80:(y + 1) * 80]
        for _ in range(2):
            for x in range(0, 80, 2):
                raw.append((row[x] & 15) | ((row[x + 1] & 15) << 4))
    raw = bytes(raw)
    assert len(raw) == 6400 and raw[-2:] == b'\0\0'
    data = scramble_dp(raw)
    assert unscramble_dp(data) == raw
    assert template[:4] == b'RGCN' and len(template) == 6448
    return template[:48] + data


def palette_file(template, pal):
    assert template[:4] == b'RLCN' and len(template) == 552
    colors = [sum((c * 31 // 255) << s for c, s in zip(rgb, (0, 5, 10))) for rgb in pal]
    return template[:0x28] + struct.pack('<16H', *colors) + template[0x28 + 32:]


def patch(rom, preview=None):
    trainers = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/5/5')])
    sprites = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/5/8')])
    used = {bytes(r)[1] for r in trainers.files if len(r) > 1}
    report = {}
    donor = bytes(sprites.files[SOURCE_CLASS * 5])
    raw = unscramble_dp(bytes(sprites.files[SOURCE_CLASS * 5 + 4])[48:])                      # layout check on Karen's own art: block 0 of +0 == her static frame 1
    frame = Image.new('P', (80, 80), 0)
    frame.putdata([(raw[y * 80 + x // 2] >> (4 * (x & 1))) & 15 for y in range(80) for x in range(80)])
    assert tile_block(parse_cells(bytes(sprites.files[SOURCE_CLASS * 5 + 2])), frame) == donor[48:48 + 3200]
    sheet = Image.new('RGB', (96 * len(TARGETS), 96), (90, 90, 100))
    for k, (tid, (name, cls)) in enumerate(TARGETS.items()):
        assert cls not in used, cls                                                          # the new class is used by no trainer
        assert bytes(trainers.files[tid])[1] == SOURCE_CLASS
        img, pal = battle_sprite(name)
        for m in range(5):
            sprites.files[cls * 5 + m] = bytes(sprites.files[SOURCE_CLASS * 5 + m])
        sprites.files[cls * 5] = animated_file(bytes(sprites.files[SOURCE_CLASS * 5]), bytes(sprites.files[SOURCE_CLASS * 5 + 2]), img)
        sprites.files[cls * 5 + 4] = static_file(bytes(sprites.files[SOURCE_CLASS * 5 + 4]), img)
        sprites.files[cls * 5 + 1] = palette_file(bytes(sprites.files[SOURCE_CLASS * 5 + 1]), pal)
        rec = bytearray(trainers.files[tid])
        rec[1] = cls
        trainers.files[tid] = bytes(rec)
        report[name] = dict(trainer=tid, new_class=cls)
        if preview:
            prev = img.copy()
            prev.putpalette([c for rgb in pal for c in rgb] + [0] * (768 - 48))
            tile = Image.new('RGB', (96, 96), (90, 90, 100))
            rgba = prev.convert('RGBA')
            rgba.putdata([(0, 0, 0, 0) if v == 0 else px for v, px in zip(img.getdata(), rgba.getdata())])
            tile.paste(rgba.convert('RGB'), (8, 8), rgba.getchannel('A'))
            sheet.paste(tile, (96 * k, 0))
    rom.files[rom.filenames.idOf('a/0/5/5')] = trainers.save()
    rom.files[rom.filenames.idOf('a/0/5/8')] = sprites.save()
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    for bank in (730, 731):
        key, rows = decode_messages(texts.files[bank])
        for _, cls in TARGETS.values():
            rows[cls] = list(rows[SOURCE_CLASS])
        texts.files[bank] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    if preview:
        sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(preview)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
