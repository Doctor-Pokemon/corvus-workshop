"""WARNING (2026-11-12): do NOT use the ROM built by this tool (0237). Its rematch counters use work variables 0x407A.. that the game's own scripts also use (9 of 16 are referenced by real script instructions, e.g. 0x4093 = Pokemon Tower scene state). Superseded by tools/card_book.py (ROM 0238). The picture/cipher helpers below are still imported by card_book.py.
Prototype 0237: CARD PICTURES for the Card Album (owner 2026-11-11 night: the Gym Leader's battle sprite on a card, a different colour border for each rarity).
Built from ROM 0236 (rematches + rarity). Everything is data plus the album script; no ARM9 or overlay byte changes except the one script-id literal of the album stub.
 - The picture: script opcode 452 (species slot, gender) draws an 80x80 framed picture on the top screen (453 hides it). The art of a "species" is its pokegra sprite (a/0/0/4, files slot*6+k: 2 = front, gender 1;
   3 = front, gender 0/none; 4 = normal palette, 5 = shiny palette; checked in the emulator on slot 494). The 40 blank dex-gap slots (494-499, 510-543: placeholder sprites, empty personal data, no form-table reference)
   carry the cards: each slot holds TWO pictures (gender 0 and gender 1) that share ONE 16-colour palette, so a slot = two tiers of one leader: slot = SLOTS[2 * leader + tier // 2], gender = tier % 2.
 - The picture is the leader's own battle sprite (trainer class static NCGR in a/0/5/8 = class * 5 + 4, palette class * 5 + 1; the data is scrambled with the "DP" pokepic cipher: seed = last u16, walk backwards, state * 1103515245 + 24691),
   frame 1 (standing pose), scaled to 72 x 72 on a cream card with a 3-pixel border in the tier colour. Palette: 0 transparent (corners), 1 cream, 2 = border of the even tier, 3 = border of the odd tier, 4-15 = the sprite's 12 colours.
 - Tier colours (TIER_COLORS): COMMON grey, UNCOMMON green, RARE blue, LEGENDARY gold. Two tiers per slot, 16 leaders x 4 tiers = 32 of the 40 slots; a fifth tier needs 48 slots (not available).
 - Encoding: nitrogfx cannot round-trip an image without empty tiles, so the NCGR is written here: raw linear 160 x 80 4-bit bitmap (80 bytes per row, low nibble = left pixel, frame 2 = the same picture), scrambled with the Pt/HGSS pokepic\n   cipher (u16 key first, e[i] = raw[i] ^ state_i, state_{i+1} = state_i * 1103515245 + 24691; the first u16 of the picture must therefore be 0 = four transparent pixels), header = the placeholder's.\n   Palette file = the placeholder's 72-byte NCLR with the 16 colours replaced. Both are decoded back with the game's own algorithm and compared.\nUsage (from yellow-heartgold, PYTHONPATH=tools): card_art.py <in 0236.nds> <out.nds> [<preview.png>]"""
import struct
import sys
from pathlib import Path
from PIL import Image
import ndspy.narc
import ndspy.rom
import card_album as ca
import card_rematch as cr
from parcel_quest import append_bank
from prototype import decode_messages

KEY = 0x6C4D                                                                # the first u16 of the scrambled data (any value)
SLOTS = list(range(494, 500)) + list(range(510, 544))                       # the 40 placeholder slots
CLASSES = [98, 103, 104, 105, 106, 107, 108, 124,                           # Brock, Misty, Lt. Surge, Erika, Koga, Sabrina, Blaine, Giovanni (trainer record byte 1)
           66, 67, 70, 72, 75, 74, 73, 76]                                  # Falkner, Bugsy, Whitney, Morty, Chuck, Jasmine, Pryce, Clair
TIER_COLORS = [(150, 150, 162), (70, 190, 90), (60, 120, 230), (245, 190, 40)]
CREAM, OUTLINE = (252, 246, 228), (40, 40, 56)
OLD_ID = 10025
NEW_ID = 10026


def unscan_dp(raw):
    a = list(struct.unpack('<3200H', raw))
    seed = a[3199]
    for i in range(3199, -1, -1):
        a[i] ^= seed & 0xFFFF
        seed = (seed * 1103515245 + 24691) & 0xFFFFFFFF
    return struct.pack('<3200H', *a)


def sprite(files, cls):
    """Frame 1 of the class' static battle sprite as RGBA 80 x 80."""
    ncgr, nclr = bytes(files[cls * 5 + 4]), bytes(files[cls * 5 + 1])
    assert ncgr[:4] == b'RGCN' and len(ncgr) == 6448 and nclr[:4] == b'RLCN'
    raw = unscan_dp(ncgr[48:48 + 6400])
    pal = [tuple(((c >> s) & 31) * 255 // 31 for s in (0, 5, 10)) for c in struct.unpack_from('<16H', nclr, 0x28)]
    im = Image.new('RGBA', (160, 80))
    px = []
    for y in range(80):
        for x in range(80):
            b = raw[y * 80 + x]
            for n in (b & 15, b >> 4):
                px.append((0, 0, 0, 0) if n == 0 else pal[n] + (255,))
    im.putdata(px)
    return im.crop((0, 0, 80, 80))


def palette_and_body(spr):
    """The 12-colour sprite on the cream card: returns (palette list of 16 RGB, 80x80 index image with border pixels left as 1)."""
    card = Image.new('RGB', (80, 80), CREAM)
    small = spr if spr.size == (72, 72) else spr.resize((72, 72), Image.LANCZOS)
    card.paste(small, (4, 4), small.getchannel('A').point(lambda v: 255 if v > 127 else 0))
    inner = card.crop((3, 3, 77, 77))
    q = inner.quantize(colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    qp = q.getpalette()[:36]
    pal = [(0, 0, 0), CREAM, (0, 0, 0), (0, 0, 0)] + [tuple(qp[3 * i:3 * i + 3]) for i in range(12)]
    body = Image.new('P', (80, 80), 1)
    body.paste(Image.frombytes('P', inner.size, bytes(i + 4 for i in q.tobytes())), (3, 3))
    return pal, body


def card(body, border_index):
    im = body.copy()
    px = im.load()
    for y in range(80):
        for x in range(80):
            ring = min(x, y, 79 - x, 79 - y)
            if ring < 3:
                px[x, y] = border_index
    for dy, width in ((0, 4), (1, 2), (2, 1)):                               # rounded corners (the first four pixels of the picture must be 0 for the cipher)
        for dx in range(width):
            for x, y in ((dx, dy), (79 - dx, dy), (dx, 79 - dy), (79 - dx, 79 - dy)):
                px[x, y] = 0
    return im


def scramble(raw):
    """Pt/HGSS pokepic cipher, encode side: raw (6400 bytes, first u16 == 0) -> scrambled data."""
    r = list(struct.unpack('<3200H', raw))
    assert r[0] == 0
    e, seed = [KEY], KEY
    for i in range(1, 3200):
        seed = (seed * 1103515245 + 24691) & 0xFFFFFFFF
        e.append(r[i] ^ (seed & 0xFFFF))
    return struct.pack('<3200H', *e)


def unscramble(data):
    """The game's UnscanPokepic_PtHGSS."""
    a = list(struct.unpack('<3200H', data))
    seed = a[0]
    for i in range(3200):
        a[i] ^= seed & 0xFFFF
        seed = (seed * 1103515245 + 24691) & 0xFFFFFFFF
    return struct.pack('<3200H', *a)


def bitmap(front):
    """80 x 80 P image (indices 0-15) -> the raw 160 x 80 two-frame 4-bit bitmap (both frames the same picture)."""
    px = list(front.getdata())
    raw = bytearray()
    for y in range(80):
        row = px[y * 80:(y + 1) * 80]
        for _ in range(2):
            for x in range(0, 80, 2):
                raw.append((row[x] & 15) | ((row[x + 1] & 15) << 4))
    return bytes(raw)


def convert(template, front, pal_rgb):
    """-> (NCGR bytes, raw bitmap) for the picture `front` on the placeholder's NCGR header."""
    raw = bitmap(front)
    data = scramble(raw)
    assert unscramble(data) == raw                                          # round trip with the game's own algorithm
    assert template[:4] == b'RGCN' and len(template) == 6448
    return template[:48] + data


def palette_file(template, pal_rgb):
    assert template[:4] == b'RLCN' and len(template) == 72
    colors = [sum((c * 31 // 255) << s for c, s in zip(rgb, (0, 5, 10))) for rgb in pal_rgb]
    return template[:0x28] + struct.pack('<16H', *colors)


def slot_of(leader, tier):
    return SLOTS[2 * leader + tier // 2], tier % 2


def pics(tag, i, tier):
    return slot_of(i + (0 if tag == 'k' else 8), tier)


def build_art(sprites_narc, template_ncgr, template_nclr):
    """-> {slot: {2: NCGR (gender 1), 3: NCGR (gender 0), 4: NCLR}} and a preview image."""
    out, preview = {}, Image.new('RGB', (4 * 84 + 4, 16 * 84 + 4), (60, 60, 70))
    for leader, cls in enumerate(CLASSES):
        pal, body = palette_and_body(sprite(sprites_narc.files, cls))
        for pair in range(len(TIER_COLORS) // 2):
            tiers = (2 * pair, 2 * pair + 1)
            pal_rgb = list(pal)
            pal_rgb[2], pal_rgb[3] = TIER_COLORS[tiers[0]], TIER_COLORS[tiers[1]]
            slot, _ = slot_of(leader, tiers[0])
            files = {4: palette_file(template_nclr, pal_rgb)}
            for tier, index in zip(tiers, (2, 3)):
                files[3 if tier % 2 == 0 else 2] = convert(template_ncgr, card(body, index), pal_rgb)       # gender 0 -> file 3, gender 1 -> file 2
                prev = card(body, index)
                prev.putpalette([c for rgb in pal_rgb for c in rgb] + [0] * (768 - 3 * len(pal_rgb)))
                preview.paste(prev.convert('RGB'), (2 + tier * 84, 2 + leader * 84))
            out[slot] = files
    return out, preview


def patch(rom, preview_path=None):
    sprites = ndspy.narc.NARC(rom.getFileByName('a/0/5/8'))
    pg = ndspy.narc.NARC(rom.getFileByName('a/0/0/4'))
    placeholder = {k: bytes(pg.files[6 * 494 + k]) for k in range(6)}
    art, preview = build_art(sprites, placeholder[3], placeholder[4])
    for slot, files in art.items():
        assert slot in SLOTS
        for k in range(6):
            assert bytes(pg.files[6 * slot + k]) == placeholder[k], (slot, k)               # still the untouched placeholder
        for k, data in files.items():
            pg.files[6 * slot + k] = data
        pg.files[6 * slot + 5] = files[4]                                                    # shiny palette = normal
    rom.setFileByName('a/0/0/4', pg.save())
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    rows = decode_messages(texts.files[ca.STD_TEXT])[1]
    old_msgs, ix_old = ca.messages()
    base_std = len(rows) - len(old_msgs) - 54
    assert base_std == 35, base_std
    ix_new = cr.new_messages(base_std + len(old_msgs))[1]
    bank, count = append_bank(bytes(scripts.files[ca.STD_BANK]), [cr.script(base_std, ix_old, ix_new, pics=pics)])
    assert ca.STD_BASE + count == NEW_ID, count
    scripts.files[ca.STD_BANK] = bytes(bank)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d, base = main.sections[0].data, main.sections[0].ramAddress
    at = cr.STUB_LITERAL - base
    assert struct.unpack_from('<I', d, at)[0] == OLD_ID
    struct.pack_into('<I', d, at, NEW_ID)
    rom.arm9 = main.save(compress=True)
    if preview_path:
        preview.save(preview_path)
    return dict(script_id=NEW_ID, slots=sorted(art), pictures=sum(len(f) - 1 for f in art.values()))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
