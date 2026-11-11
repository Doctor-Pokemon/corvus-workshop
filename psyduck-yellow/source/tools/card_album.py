"""Prototype 0235: the CARD ALBUM (owner 2026-11-11 night: a Pokedex-like collection of the notable NPCs; "see what you can get working on a separate ROM").
Built from ROM 0233 (stone shop). FIRST VERSION: text only, 16 entries (the 8 Kanto and 8 Johto GYM LEADERS), no pictures, no win counters.
 1. The item: item 465 (Vs. Recorder, a Platinum key item that is still in the item table; its field-use id 0x1d runs the battle-video app) becomes the key item "Card Album": name bank 222, description bank 830 row 465.
    Its REGISTER bit (bit 6 of the u16 at offset 8) is cleared so the Select-button shortcut cannot start the old app.
 2. The "use" action: ItemMenuUseFunc_VSRecorder (ARM9 0x02065614, 0x34 bytes, only called from the bag) is replaced by a tail call into the vanilla routine that the bag uses for the Ruins of Alph item reactions
    (ARM9 0x02064A8C: "close the bag menu, then QueueScript(scriptNo)"). The script number is a STANDARD script id: 10000 + index in the shared bank 1165 (id table at ARM9 0x020FA4DA: ids >= 10000 -> script file 1165, text bank 211).
 3. The script: ONE new script appended to the shared bank 1165, messages appended to text bank 211 (35 rows before, indices are bytes). Menu 1 = Kanto / Johto / Close; menu 2 = the 8 entries (name, or "???" until the badge is owned) + Back;
    choosing an entry shows its blurb, or "not met yet". An entry unlocks when the matching badge is owned (CheckBadge 8-15 Kanto, 0-7 Johto): no new flag, no new variable, old saves unlock retroactively.
 4. Delivery (prototype): the Oak's Lab aide (map 505, the script that gives the starter stones) first checks "no album in the bag" and gives it, then continues into the stone check unchanged (one GoTo is re-pointed).
 All blurbs and lines are PLACEHOLDERS (the owner writes the real ones). No flag or variable is allocated.
Usage (from yellow-heartgold, PYTHONPATH=tools): card_album.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE

ALBUM = 465
NAME_BANK, DESC_BANK = 222, 830
STD_BANK, STD_TEXT, STD_BASE = 1165, 211, 10000
OLD_FUNC, ALPH_FUNC = 0x02065614, 0x02064A8C
OLD_FUNC_BYTES = bytes.fromhex('38b5041c2068')                         # push {r3,r4,r5,lr}; adds r4,r0,#0; ldr r0,[r4]  (checked before patching)
LAB, AIDE_TAIL = 505, 777                                              # the lab map and the aide's tail offset used by stone_check.py (the GoTo sits 4 bytes later once the header grew)
NAME = 'Card Album'
DESCRIPTION = "A collection of the notable\nTRAINERS you have beaten."
# (name, badge id, place, type) - badge ids: Kanto 8-15 (Boulder..Earth), Johto 0-7 (Zephyr..Rising)
KANTO = [('BROCK', 8, 'Pewter City', 'Rock'), ('MISTY', 9, 'Cerulean City', 'Water'), ('LT. SURGE', 10, 'Vermilion City', 'Electric'),
         ('ERIKA', 11, 'Celadon City', 'Grass'), ('KOGA', 12, 'Fuchsia City', 'Poison'), ('SABRINA', 13, 'Saffron City', 'Psychic'),
         ('BLAINE', 14, 'Cinnabar Island', 'Fire'), ('GIOVANNI', 15, 'Viridian City', 'Ground')]
JOHTO = [('FALKNER', 0, 'Violet City', 'Flying'), ('BUGSY', 1, 'Azalea Town', 'Bug'), ('WHITNEY', 2, 'Goldenrod City', 'Normal'),
         ('MORTY', 3, 'Ecruteak City', 'Ghost'), ('CHUCK', 4, 'Cianwood City', 'Fighting'), ('JASMINE', 5, 'Olivine City', 'Steel'),
         ('PRYCE', 6, 'Mahogany Town', 'Ice'), ('CLAIR', 7, 'Blackthorn City', 'Dragon')]
TOP_LABELS = ['KANTO LEADERS', 'JOHTO LEADERS', 'CLOSE']
BACK, UNKNOWN, NEXT, PREV = 'BACK', '???', 'NEXT PAGE', 'PREVIOUS PAGE'
PAGE = 4                                                              # leaders per page: the touch menu holds 8 buttons (2 x 4) at most and B selects the LAST one
LOCKED = 'You have not beaten this\nTRAINER yet.'
LAB_LINES = ["Oh, and I found this in the lab!\rTake this CARD ALBUM. It records the notable TRAINERS you beat.", '{PLAYER} received the CARD ALBUM!', 'You have no room for this. Come back with space in your pack.']


def blurb(entry):
    name, _, place, kind = entry
    return f'{name}\n{place} GYM LEADER.\r{kind}-type specialist.\r(placeholder text)'


def messages():
    """The text rows appended to bank 211, in order, and the index of each."""
    rows, index = [], {}

    def add(key, text):
        index[key] = len(rows)
        rows.append(text)
    for i, t in enumerate(TOP_LABELS):
        add(('top', i), t)
    add('back', BACK)
    add('next', NEXT)
    add('prev', PREV)
    add('unknown', UNKNOWN)
    add('locked', LOCKED)
    for tag, entries in (('k', KANTO), ('j', JOHTO)):
        for i, e in enumerate(entries):
            add((tag, 'name', i), e[0])
            add((tag, 'blurb', i), blurb(e))
    return rows, index


def album_script(base):
    """base = how many rows bank 211 already has (message ids are base + index)."""
    _, ix = messages()
    m = lambda key: base + ix[key]
    s = Script().emit(96)                                                                   # LockAll
    s.label('top')
    s.emit(746)                                                                             # TouchscreenMenuHide (the field menu is still drawn when the item runs the script)
    s.emit(750)
    s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))                           # MenuInit x, y, 0, 1, result var
    for i in range(3):
        s.emit(751, m(('top', i)), 255, i)
    s.emit(752)
    s.compare(0x800C, 0).jump('kanto', 1).compare(0x800C, 1).jump('johto', 1)
    s.jump('exit')
    for tag, label, entries in (('k', 'kanto', KANTO), ('j', 'johto', JOHTO)):
        pages = [list(range(i, min(i + PAGE, len(entries)))) for i in range(0, len(entries), PAGE)]
        for n, page in enumerate(pages):
            s.label(label if n == 0 else f'{label}{n}')
            s.emit(750)
            s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
            for i in page:
                e = entries[i]
                s.emit(294, e[1], 0x800C).compare(0x800C, 1).jump(f'{tag}_have{i}', 1)
                s.emit(751, m('unknown'), 255, i).jump(f'{tag}_next{i}')
                s.label(f'{tag}_have{i}').emit(751, m((tag, 'name', i)), 255, i)
                s.label(f'{tag}_next{i}')
            if n + 1 < len(pages):
                s.emit(751, m('next'), 255, 20)
            if n > 0:
                s.emit(751, m('prev'), 255, 21)
            s.emit(751, m('back'), 255, 8).emit(752)                                       # BACK is the last button: B selects it
            for i in page:
                s.compare(0x800C, i).jump(f'{tag}_pick{i}', 1)
            if n + 1 < len(pages):
                s.compare(0x800C, 20).jump(f'{label}{n + 1}', 1)
            if n > 0:
                s.compare(0x800C, 21).jump(label if n == 1 else f'{label}{n - 1}', 1)
            s.jump('top')
        for n, page in enumerate(pages):
            for i in page:
                here = label if n == 0 else f'{label}{n}'
                e = entries[i]
                s.label(f'{tag}_pick{i}')
                s.emit(294, e[1], 0x800C).compare(0x800C, 1).jump(f'{tag}_show{i}', 1)
                s.msg(m('locked')).jump(here)
                s.label(f'{tag}_show{i}')
                s.msg(m((tag, 'blurb', i))).jump(here)
    s.label('exit')
    s.emit(747).emit(97).emit(2)                                                                      # ReleaseAll, End
    return s.finish()


def lab_script(first, h1_abs, here):
    """Runs where the aide's tail used to continue: give the album once, then jump into the old helper (skipping its WaitButton, CloseMsg)."""
    s = Script().emit(50).emit(53)
    s.emit(128, ALBUM, 1, 0x800C).compare(0x800C, 1).jump('go', 1)                           # HaveItem
    s.msg(first)
    s.emit(125, ALBUM, 1, 0x800C).compare(0x800C, 0).jump('full', 1)                         # GiveItem
    s.emit(78, 1185).msg(first + 1).emit(79)
    s.label('go')
    s.emit(22)
    s.relative('target')
    s.label('full')
    s.msg(first + 2).emit(97).emit(2)
    s.labels['target'] = None
    raw = bytearray(s.data)
    at = s.fixups[-1][0]
    # the last fixup is the absolute jump into the old helper; resolve it by hand, the others normally
    s.fixups = [f for f in s.fixups if f[1] != 'target']
    s.labels.pop('target')
    code = bytearray(s.finish())
    struct.pack_into('<i', code, at, (h1_abs + 4) - (here + at + 4))
    return bytes(code)


def patch_arm(rom):
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d = main.sections[0].data
    base = main.sections[0].ramAddress
    off = OLD_FUNC - base
    assert bytes(d[off:off + len(OLD_FUNC_BYTES)]) == OLD_FUNC_BYTES, bytes(d[off:off + 8]).hex()
    # table check: the use-function table entry 0x1d (Vs. Recorder) must point at the old function
    table = 0x020FE264 - base
    assert struct.unpack_from('<I', d, table + 12 * 0x1D)[0] == OLD_FUNC + 1
    return main, d, off


def patch(rom):
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    items = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/7')])
    # --- item record, name, description
    rec = bytearray(items.files[ALBUM])
    flags = struct.unpack_from('<H', rec, 8)[0]
    assert (flags >> 7) & 15 == 7 and rec[10] == 0x1D, (hex(flags), rec[10])               # Key Items pocket, field-use id 0x1d
    struct.pack_into('<H', rec, 8, flags & ~0x40)                                           # not registrable
    items.files[ALBUM] = bytes(rec)
    row = lambda text: decode_messages(encode_text([text], PH))[1][0]
    key, rows = decode_messages(texts.files[NAME_BANK])
    rows[ALBUM] = row(NAME)
    texts.files[NAME_BANK] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[DESC_BANK])
    rows[ALBUM] = row(DESCRIPTION)
    texts.files[DESC_BANK] = encode_messages(key, rows)
    # --- the album script in the shared bank 1165, its messages in bank 211
    key, rows = decode_messages(texts.files[STD_TEXT])
    base = len(rows)
    new_rows, _ = messages()
    assert base + len(new_rows) < 250, (base, len(new_rows))
    rows.extend(decode_messages(encode_text(new_rows, PH))[1])
    texts.files[STD_TEXT] = encode_messages(key, rows)
    bank = bytes(scripts.files[STD_BANK])
    bank, count = append_bank(bank, [album_script(base)])
    scripts.files[STD_BANK] = bytes(bank)
    script_id = STD_BASE + count
    # --- ARM9: ItemMenuUseFunc_VSRecorder -> tail call into the Alph item-reaction routine with our script id
    main, d, off = patch_arm(rom)
    code = struct.pack('<6H', 0x4A02, 0x4B03, 0x4718, 0x46C0, 0x46C0, 0x46C0) + struct.pack('<2I', script_id, ALPH_FUNC + 1)
    d[off:off + len(code)] = code                                                           # ldr r2,[pc,#8]; ldr r3,[pc,#12]; bx r3; nops; .word id; .word func|1
    # --- delivery: the Oak's Lab aide
    lrec = TABLE + LAB * 24
    sid, _, tid = struct.unpack_from('<3H', d, lrec + 6)
    lab = bytes(scripts.files[sid])
    pos = AIDE_TAIL + 4
    assert struct.unpack_from('<H', lab, pos)[0] == 22, lab[pos:pos + 6].hex()               # the GoTo stone_check.py left
    h1_abs = pos + 6 + struct.unpack_from('<i', lab, pos + 2)[0]
    key, lrows = decode_messages(texts.files[tid])
    first = len(lrows)
    assert first + len(LAB_LINES) < 250
    lrows.extend(decode_messages(encode_text(LAB_LINES, PH))[1])
    texts.files[tid] = encode_messages(key, lrows)
    # append the new lab script (the header grows by 4, every old address moves by 4, relative jumps stay valid)
    probe, n = append_bank(lab, [b''])
    here = struct.unpack_from('<I', probe, n * 4)[0] + n * 4 + 4
    new_h = lab_script(first, h1_abs + 4, here)
    out, n = append_bank(lab, [new_h])
    here = struct.unpack_from('<I', out, n * 4)[0] + n * 4 + 4
    assert bytes(out[here:]) == new_h
    new_pos = pos + 4
    assert struct.unpack_from('<H', out, new_pos)[0] == 22
    struct.pack_into('<i', out, new_pos + 2, here - (new_pos + 6))
    scripts.files[sid] = bytes(out)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[rom.filenames.idOf('a/0/1/7')] = items.save()
    rom.arm9 = main.save(compress=True)
    return dict(script_id=script_id, std_messages=(base, len(new_rows)), lab_messages=first, lab_script_file=sid, arm9_patch=hex(OLD_FUNC))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
