"""Prototype 0238: the CARD ALBUM with rematches, three rarities, card pictures and the ELITE FOUR (owner 2026-11-12: "three tiers: Common gray, Rare purple, Legendary gold; add ALL of the Elite Four, Kanto AND Johto").
Built from ROM 0235 (the safe Card Album build); it REPLACES tools/card_rematch.py + tools/card_art.py (0236 / 0237), whose rematch counters used work variables that the game's own scripts also use (found 2026-11-12:
9 of the 16 were referenced by real script instructions, one of them Pokemon Tower scene state 0x4093): do not use those two ROMs.
 - 24 entries: the 8 Kanto and 8 Johto Gym Leaders (unlocked by badge, as before), the 4 Kanto Elite Four (Lorelei, Bruno, Agatha, Lance; trainers 245 247 418 246; unlocked when a league was won: HOFN var 0x413E >= 1)
   and the 4 Johto Elite Four (Will, Koga, Bruno, Karen; trainers 997 998 1000 1001 = HeartGold's level-100 teams; HOFN >= 2). Menu: KANTO LEADERS / JOHTO LEADERS / KANTO ELITE 4 / JOHTO ELITE 4 / CLOSE.
 - Rematch: unlocked entry -> blurb -> RARITY -> "Challenge this TRAINER to a rematch?" -> TrainerBattle with the entry's own trainer id -> win = +1 on its counter (cap 3), loss = WhiteOut. The card (80x80 picture, opcode 452 / 453)
   is shown for the entry's tier and again, upgraded, after a win.
 - Rarity from REMATCH wins: 0 = COMMON (gray border), 1-2 = RARE (purple), 3 = LEGENDARY (gold; the whole card is in gold tones). The list shows no suffix / " +" / " ++".
 - Counters: 2 bits per entry (cap 3) packed 8 to a variable: entry e lives in VARS[e // 8], digit e % 8 (base 4). Reading a digit uses the shared subroutines dig_0..dig_7 (compare / SubVar loops: scripts have no divide).
   VARS = 0x4044, 0x4049, 0x4034: the only work variables in 0x4030-0x416F that no script instruction, no event field, no 32-bit constant in the ARM9 / overlays and no tool mentions (the project's flag_alloc method plus an
   instruction-level scan with hg_dis); none of the 16 variables of 0236/0237 is used.
 - Pictures: the leader's / Elite Four member's battle sprite (a/0/5/8, class * 5 + 4 / + 1; the Johto Will and Koga use HeartGold's own classes 87 and 89, Bruno 112 and Karen 88 as the sprites they share), 21 distinct sprites.
   Lorelei and Agatha use owner-supplied pixel art (build/card-art-src: lorelei.png, agatha.gif; 23 distinct sprites instead of 21; 35 of the 40 slots).
   Slots (the 40 blank species slots 494-499, 510-543): sprite d -> slot SLOTS[d] with COMMON (gender 0) and RARE (gender 1) sharing a 16-colour palette (0 transparent, 1 cream, 2 gray, 3 purple, 4-15 sprite);
   LEGENDARY pictures of two sprites share one slot (gender 0 / 1) in a common gold ramp: slot SLOTS[len(SPRITES) + d // 2]. The encoder (Pt/HGSS pokepic cipher) is in tools/card_art.py.
Usage (from yellow-heartgold, PYTHONPATH=tools): card_book.py <in 0235.nds> <out.nds> [<preview.png>]"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from PIL import Image
import card_album as ca
import card_art as art
from pathlib import Path
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages

VARS = [0x4044, 0x4049, 0x4034]
HOFN = 0x413E
STUB_LITERAL = 0x02065620
OLD_ID, NEW_ID = 10024, 10025
TIERS = ['COMMON', 'RARE', 'LEGENDARY']
SUFFIX = ['', ' +', ' ++']
COLORS = {'gray': (150, 150, 162), 'purple': (150, 70, 200), 'gold': (245, 190, 40)}
SLOTS = art.SLOTS
PROMPT, WON = 'Challenge this TRAINER to a rematch?', 'You won the rematch!'
TOP = ['KANTO LEADERS', 'JOHTO LEADERS', 'KANTO ELITE 4', 'JOHTO ELITE 4', 'CLOSE']
PAGE = 4

# (name, group, unlock, trainer, art class, place, type)   unlock: ('badge', id) or ('hofn', n)
ENTRIES = (
    [(n, 'k', ('badge', b), t, c, p, k) for (n, b, p, k), t, c in zip(ca.KANTO, (757, 781, 255, 256, 257, 258, 259, 261), (98, 103, 104, 105, 106, 107, 108, 124))] +
    [(n, 'j', ('badge', b), t, c, p, k) for (n, b, p, k), t, c in zip(ca.JOHTO, (20, 21, 30, 31, 34, 33, 32, 35), (66, 67, 70, 72, 75, 74, 73, 76))] +
    [('LORELEI', 'ke', ('hofn', 1), 245, 'lorelei', 'Kanto', 'Ice'), ('BRUNO', 'ke', ('hofn', 1), 247, 112, 'Kanto', 'Fighting'),
     ('AGATHA', 'ke', ('hofn', 1), 418, 'agatha', 'Kanto', 'Ghost'), ('LANCE', 'ke', ('hofn', 1), 246, 86, 'Kanto', 'Dragon'),
     ('WILL', 'je', ('hofn', 2), 997, 87, 'Johto', 'Psychic'), ('KOGA', 'je', ('hofn', 2), 998, 89, 'Johto', 'Poison'),
     ('BRUNO', 'je', ('hofn', 2), 1000, 112, 'Johto', 'Fighting'), ('KAREN', 'je', ('hofn', 2), 1001, 88, 'Johto', 'Dark')])
assert len(ENTRIES) == 24
SPRITES = list(dict.fromkeys(e[4] for e in ENTRIES))                          # distinct art classes in order of first use
assert len(SPRITES) == 23
GROUPS = [('k', 'kanto'), ('j', 'johto'), ('ke', 'kelite'), ('je', 'jelite')]


CUSTOM = {'lorelei': ('lorelei.png', None), 'agatha': ('agatha.gif', (40, 272, 86, 340))}      # owner-supplied pixel art in build/card-art-src (ignored, never published): (file, crop box of the small native sprite)
ART_DIR = Path(__file__).resolve().parents[1] / 'build/card-art-src'


def custom_sprite(name):
    """Owner-supplied native pixel sprite -> 72 x 72 RGBA (background colour keyed out, scaled once to 72 px tall, bottom centred)."""
    file, box = CUSTOM[name]
    im = Image.open(ART_DIR / file).convert('RGB')
    if box:
        im = im.crop(box)
    bg = im.getpixel((0, 0))
    rgba = Image.new('RGBA', im.size)
    px, out = im.load(), rgba.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y] != bg:
                out[x, y] = px[x, y] + (255,)
    rgba = rgba.crop(rgba.getbbox())
    big = rgba.resize((rgba.width * 8, rgba.height * 8), Image.NEAREST)                        # exact pixel art, then one smooth reduction
    scale = min(72 / big.width, 72 / big.height)
    small = big.resize((max(1, round(big.width * scale)), max(1, round(big.height * scale))), Image.LANCZOS)
    card = Image.new('RGBA', (72, 72))
    card.alpha_composite(small, ((72 - small.width) // 2, 72 - small.height))
    return card


def blurb(e):
    name, group, _, _, _, place, kind = e
    if group in ('k', 'j'):
        return f'{name}\n{place} GYM LEADER.\r{kind}-type specialist.\r(placeholder text)'
    return f'{name}\n{place} ELITE FOUR.\r{kind}-type specialist.\r(placeholder text)'


def new_rows():
    rows, index = [], {}

    def add(key, text):
        index[key] = len(rows)
        rows.append(text)
    for i, t in enumerate(TOP):
        add(('top', i), t)
    for key, text in (('back', 'BACK'), ('next', 'NEXT PAGE'), ('prev', 'PREVIOUS PAGE'), ('unknown', '???'), ('locked', 'You have not beaten this\nTRAINER yet.'),
                      ('prompt', PROMPT), ('won', WON)):
        add(key, text)
    for t, name in enumerate(TIERS):
        add(('tier', t), f'RARITY: {name}')
    for n, e in enumerate(ENTRIES):
        for t in range(3):
            add(('name', n, t), e[0] + SUFFIX[t])
        add(('blurb', n), blurb(e))
    return rows, index


def pics_of(e_index):
    """-> function tier -> (species slot, gender) for entry e_index."""
    d = SPRITES.index(ENTRIES[e_index][4])
    return lambda t: (SLOTS[d], t) if t < 2 else (SLOTS[len(SPRITES) + d // 2], d % 2)


def script(base, ix):
    m = lambda key: base + ix[key]
    s = Script().emit(96)                                                                   # LockAll
    s.label('top')
    s.emit(746).emit(750)
    s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
    for i in range(5):
        s.emit(751, m(('top', i)), 255, i)
    s.emit(752)
    for i, (_, label) in enumerate(GROUPS):
        s.compare(0x800C, i).jump(label, 1)
    s.jump('exit')

    def arith(op, var, value):
        """AddVar / SubVar take 'var or addend': a literal of 0x4000 or more would be read as a variable id, so 16384 is applied as 2 x 8192."""
        for _ in range(2 if value >= 0x4000 else 1):
            s.emit(op, var, value // 2 if value >= 0x4000 else value)

    def digit(n):
        """digit of entry n -> 0x8006 (CopyVar into 0x8004, then the shared subroutine)."""
        s.emit(42, 0x8004, VARS[n // 8])
        s.emit(26)
        s.relative(f'dig{n % 8}')

    def tier_branch(n, targets):
        digit(n)
        s.compare(0x8006, 3).jump(targets[2], 4)
        s.compare(0x8006, 1).jump(targets[1], 4)
        s.jump(targets[0])

    def unlocked(n, yes):
        kind, arg = ENTRIES[n][2]
        if kind == 'badge':
            s.emit(294, arg, 0x800C).compare(0x800C, 1).jump(yes, 1)
        else:
            s.compare(HOFN, arg).jump(yes, 4)

    for tag, label in GROUPS:
        members = [n for n, e in enumerate(ENTRIES) if e[1] == tag]
        pages = [members[i:i + PAGE] for i in range(0, len(members), PAGE)]
        for p, page in enumerate(pages):
            s.label(label if p == 0 else f'{label}{p}')
            s.emit(750)
            s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
            for n in page:
                unlocked(n, f'have{n}')
                s.emit(751, m('unknown'), 255, n).jump(f'next{n}')
                s.label(f'have{n}')
                tier_branch(n, [f'nm{n}_{t}' for t in range(3)])
                for t in range(3):
                    s.label(f'nm{n}_{t}')
                    s.emit(751, m(('name', n, t)), 255, n).jump(f'next{n}')
                s.label(f'next{n}')
            if p + 1 < len(pages):
                s.emit(751, m('next'), 255, 90)
            if p > 0:
                s.emit(751, m('prev'), 255, 91)
            s.emit(751, m('back'), 255, 92).emit(752)
            for n in page:
                s.compare(0x800C, n).jump(f'pick{n}', 1)
            if p + 1 < len(pages):
                s.compare(0x800C, 90).jump(f'{label}{p + 1}', 1)
            if p > 0:
                s.compare(0x800C, 91).jump(label if p == 1 else f'{label}{p - 1}', 1)
            s.jump('top')
        for p, page in enumerate(pages):
            here = label if p == 0 else f'{label}{p}'
            for n in page:
                e, pic = ENTRIES[n], pics_of(n)
                s.label(f'pick{n}')
                unlocked(n, f'show{n}')
                s.msg(m('locked')).jump(here)
                s.label(f'show{n}')
                tier_branch(n, [f'r{n}_{t}' for t in range(3)])
                for t in range(3):
                    s.label(f'r{n}_{t}')
                    s.emit(452, *pic(t))
                    s.msg(m(('blurb', n)))
                    s.msg(m(('tier', t)))
                    s.jump(f'ask{n}')
                s.label(f'ask{n}')
                s.emit(45)
                s.data.append(m('prompt'))
                s.emit(63, 0x800C)
                s.emit(53)
                s.compare(0x800C, 0).jump(f'go{n}', 1)
                s.emit(453)
                s.jump(here)
                s.label(f'go{n}')
                s.emit(453)
                s.emit(213, e[3], 0, 0)                                                    # TrainerBattle
                s.emit(220, 0x800C).compare(0x800C, 1).jump('lost', 5)                      # CheckBattleWon
                digit(n)
                s.compare(0x8006, 3).jump(f'cap{n}', 4)
                arith(39, VARS[n // 8], 4 ** (n % 8))                                       # one more rematch win
                s.label(f'cap{n}')
                s.msg(m('won'))
                tier_branch(n, [f'w{n}_{t}' for t in range(3)])
                for t in range(3):
                    s.label(f'w{n}_{t}')
                    s.emit(452, *pic(t))
                    s.msg(m(('tier', t)))
                    s.emit(453)
                    s.jump(here)
    s.label('lost')
    s.emit(219).emit(97).emit(2)                                                           # WhiteOut, ReleaseAll, End
    s.label('exit')
    s.emit(747).emit(97).emit(2)
    for k in range(8):                                                                      # dig_k: 0x8004 = packed value -> 0x8006 = base-4 digit k
        s.label(f'dig{k}')
        for j in range(7, k, -1):
            for rep in range(3):
                s.compare(0x8004, 4 ** j).jump(f'd{k}_{j}_{rep}', 0)
                arith(40, 0x8004, 4 ** j)
                s.label(f'd{k}_{j}_{rep}')
        s.emit(41, 0x8006, 0)
        for rep in range(3):
            s.compare(0x8004, 4 ** k).jump(f'e{k}_{rep}', 0)
            arith(40, 0x8004, 4 ** k)
            s.emit(39, 0x8006, 1)
            s.label(f'e{k}_{rep}')
        s.emit(27)                                                                          # Return
    return s.finish()


def gold_body(spr):
    """Gold-toned card body: dark background (index 1), the sprite as a 13-step gold ramp (indices 3-15)."""
    body = Image.new('P', (80, 80), 1)
    small = spr if spr.size == (72, 72) else spr.resize((72, 72), Image.LANCZOS)
    px = body.load()
    sp = small.load()
    for y in range(72):
        for x in range(72):
            r, g, b, a = sp[x, y]
            if a > 127:
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                px[x + 4, y + 4] = 3 + min(12, int(lum ** 0.8 * 13))
    return body


GOLD_PALETTE = [(0, 0, 0), (28, 22, 38), COLORS['gold']] + [(int(70 + 185 * i / 12), int(44 + 186 * i / 12), int(10 + 140 * (i / 12) ** 1.5)) for i in range(13)]


def build_art(sprites_narc, template_ncgr, template_nclr):
    out, preview = {}, Image.new('RGB', (3 * 84 + 4, len(SPRITES) * 84 + 4), (60, 60, 70))
    gold_bodies = {}
    for d, cls in enumerate(SPRITES):
        spr = custom_sprite(cls) if isinstance(cls, str) else art.sprite(sprites_narc.files, cls)
        pal, body = art.palette_and_body(spr)
        pal_rgb = list(pal)
        pal_rgb[2], pal_rgb[3] = COLORS['gray'], COLORS['purple']
        files = {4: art.palette_file(template_nclr, pal_rgb)}
        for t, index in ((0, 2), (1, 3)):
            files[3 if t == 0 else 2] = art.convert(template_ncgr, art.card(body, index), pal_rgb)          # gender 0 -> file 3, gender 1 -> file 2
            prev = art.card(body, index)
            prev.putpalette([c for rgb in pal_rgb for c in rgb] + [0] * (768 - 3 * len(pal_rgb)))
            preview.paste(prev.convert('RGB'), (2 + t * 84, 2 + d * 84))
        out[SLOTS[d]] = files
        gold_bodies[d] = gold_body(spr)
    for j in range((len(SPRITES) + 1) // 2):
        slot = SLOTS[len(SPRITES) + j]
        files = {4: art.palette_file(template_nclr, GOLD_PALETTE)}
        for g in (0, 1):
            d = 2 * j + g
            if d >= len(SPRITES):
                continue
            card = art.card(gold_bodies[d], 2)
            files[3 if g == 0 else 2] = art.convert(template_ncgr, card, GOLD_PALETTE)
            card.putpalette([c for rgb in GOLD_PALETTE for c in rgb] + [0] * (768 - 3 * len(GOLD_PALETTE)))
            preview.paste(card.convert('RGB'), (2 + 2 * 84, 2 + d * 84))
        out[slot] = files
    return out, preview


def patch(rom, preview_path=None):
    sprites = ndspy.narc.NARC(rom.getFileByName('a/0/5/8'))
    pg = ndspy.narc.NARC(rom.getFileByName('a/0/0/4'))
    placeholder = {k: bytes(pg.files[6 * 494 + k]) for k in range(6)}
    files_art, preview = build_art(sprites, placeholder[3], placeholder[4])
    for slot, files in files_art.items():
        assert slot in SLOTS
        for k in range(6):
            assert bytes(pg.files[6 * slot + k]) == placeholder[k], (slot, k)
        for k, data in files.items():
            pg.files[6 * slot + k] = data
        pg.files[6 * slot + 5] = files[4]
    rom.setFileByName('a/0/0/4', pg.save())
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[ca.STD_TEXT])
    base = len(rows)
    assert base == 75, base                                                                 # 0235: 35 original rows + the album's 40
    extra, ix = new_rows()
    assert base + len(extra) < 250, base + len(extra)
    rows.extend(decode_messages(encode_text(extra, PH))[1])
    texts.files[ca.STD_TEXT] = encode_messages(key, rows)
    bank, count = append_bank(bytes(scripts.files[ca.STD_BANK]), [script(base, ix)])
    assert ca.STD_BASE + count == NEW_ID, count
    scripts.files[ca.STD_BANK] = bytes(bank)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d, ram = main.sections[0].data, main.sections[0].ramAddress
    at = STUB_LITERAL - ram
    assert struct.unpack_from('<I', d, at)[0] == OLD_ID
    struct.pack_into('<I', d, at, NEW_ID)
    rom.arm9 = main.save(compress=True)
    if preview_path:
        preview.save(preview_path)
    return dict(script_id=NEW_ID, rows=(base, len(extra)), slots=sorted(files_art), entries=len(ENTRIES), sprites=len(SPRITES))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[2 + 1] if len(sys.argv) > 3 else None))
    rom.saveToFile(sys.argv[2])
