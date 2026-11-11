"""WARNING (2026-11-12): do NOT use the ROM built by this tool (0236). Its rematch counters use work variables 0x407A.. that the game's own scripts also use (9 of 16 are referenced by real script instructions, e.g. 0x4093 = Pokemon Tower scene state). Superseded by tools/card_book.py (ROM 0238). The picture/cipher helpers below are still imported by card_book.py.
Prototype 0236: REMATCHES and RARITY for the Card Album (owner 2026-11-11 night: "1. Rematch wins" sets the rarity; build from the Card Album build 0235).
Built from ROM 0235. The album script (shared bank 1165, id 10024) is left in the ROM as dead data; a NEW script (id 10025) replaces it and the ARM9 stub's script id (u32 literal at 0x02065620) is changed.
 - Choosing an unlocked leader shows the blurb, then the card's RARITY, then asks "Challenge this TRAINER to a rematch?". Yes = TrainerBattle with the leader's own trainer id (the same record as the first fight: Kanto = Yellow's team,
   Johto = the badge-scaled team), win = +1 to that leader's counter (one work variable each, capped at 30), loss = WhiteOut like any battle. The rematch is available anywhere (it runs from the bag), after the badge is owned.
 - Rarity by REMATCH wins (constants below, the owner's numbers to choose): 0 COMMON, 1-2 UNCOMMON, 3-5 RARE, 6+ LEGENDARY. The list buttons show the tier as a suffix (none, +, ++, +++).
 - Counters = 16 work variables that no script bank, event table, ARM9/overlay word literal or tool mentions (VAR_UNK_* in pret's vars.h): see VARS. PKHeX labels are a separate step.
Usage (from yellow-heartgold, PYTHONPATH=tools): card_rematch.py <in 0235.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import card_album as ca
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages

VARS = [0x407A, 0x407F, 0x4084, 0x408A, 0x408B, 0x408F, 0x4093, 0x40A0,        # Kanto leaders in order (Brock .. Giovanni)
        0x40A3, 0x40A4, 0x40A6, 0x40C2, 0x40C7, 0x40CC, 0x40CF, 0x40D2]        # Johto leaders in order (Falkner .. Clair)
TRAINERS = [757, 781, 255, 256, 257, 258, 259, 261,                           # Brock, Misty, Lt. Surge, Erika, Koga, Sabrina, Blaine, Giovanni (read from the gym scripts)
            20, 21, 30, 31, 34, 33, 32, 35]                                   # Falkner, Bugsy, Whitney, Morty, Chuck, Jasmine, Pryce, Clair (tools/johto_step5.py)
TIERS = ['COMMON', 'UNCOMMON', 'RARE', 'LEGENDARY']
THRESHOLDS = (1, 3, 6)                                                        # rematch wins needed for tier 1, 2, 3
SUFFIX = ['', ' +', ' ++', ' +++']
CAP = 30
STUB_LITERAL = 0x02065620                                                     # u32 script id read by the stub at 0x02065614
OLD_ID = ca.STD_BASE + 24
PROMPT = 'Challenge this TRAINER to a rematch?'
WON = 'You won the rematch!'
DECLINE_NONE = None


def entries():
    return [('k', i, e) for i, e in enumerate(ca.KANTO)] + [('j', i, e) for i, e in enumerate(ca.JOHTO)]


def new_messages(old_rows):
    """Extra rows appended after the album's own rows; returns (rows, index of each) with indices relative to old_rows."""
    rows, index = [], {}

    def add(key, text):
        index[key] = old_rows + len(rows)
        rows.append(text)
    for tag, i, e in entries():
        for t in (1, 2, 3):
            add((tag, 'name', i, t), e[0] + SUFFIX[t])
    for t, name in enumerate(TIERS):
        add(('tier', t), f'RARITY: {name}')
    add('prompt', PROMPT)
    add('won', WON)
    return rows, index


def script(base_std, ix_old, ix_new, pics=None):
    """base_std = 35 (the row count of bank 211 before the album); message ids are absolute row numbers.
    pics (ROM 0237, tools/card_art.py): optional function (tag, i, tier) -> (species slot, gender) of the card picture; the 80x80 picture (opcode 452) is shown from the blurb until the answer, and again for the new tier after a win (453 hides it)."""
    old = lambda key: base_std + ix_old[key]
    new = lambda key: ix_new[key]
    s = Script().emit(96)                                                                   # LockAll
    s.label('top')
    s.emit(746).emit(750)
    s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
    for i in range(3):
        s.emit(751, old(('top', i)), 255, i)
    s.emit(752)
    s.compare(0x800C, 0).jump('kanto', 1).compare(0x800C, 1).jump('johto', 1)
    s.jump('exit')

    def tier_branch(prefix, var, targets):
        """Jump to targets[t] where t = tier of the counter in `var` (compares from the top)."""
        s.compare(var, THRESHOLDS[2]).jump(targets[3], 4)
        s.compare(var, THRESHOLDS[1]).jump(targets[2], 4)
        s.compare(var, THRESHOLDS[0]).jump(targets[1], 4)
        s.jump(targets[0])

    for tag, label, group in (('k', 'kanto', ca.KANTO), ('j', 'johto', ca.JOHTO)):
        base = 0 if tag == 'k' else 8
        pages = [list(range(i, min(i + ca.PAGE, len(group)))) for i in range(0, len(group), ca.PAGE)]
        for n, page in enumerate(pages):
            s.label(label if n == 0 else f'{label}{n}')
            s.emit(750)
            s.data.extend(bytes((1, 1, 0, 1)) + struct.pack('<H', 0x800C))
            for i in page:
                e, var = group[i], VARS[base + i]
                s.emit(294, e[1], 0x800C).compare(0x800C, 1).jump(f'{tag}_have{i}', 1)
                s.emit(751, old('unknown'), 255, i).jump(f'{tag}_next{i}')
                s.label(f'{tag}_have{i}')
                tier_branch(f'{tag}{i}', var, [f'{tag}_n{i}_{t}' for t in range(4)])
                for t in range(4):
                    s.label(f'{tag}_n{i}_{t}')
                    s.emit(751, old((tag, 'name', i)) if t == 0 else new((tag, 'name', i, t)), 255, i).jump(f'{tag}_next{i}')
                s.label(f'{tag}_next{i}')
            if n + 1 < len(pages):
                s.emit(751, old('next'), 255, 20)
            if n > 0:
                s.emit(751, old('prev'), 255, 21)
            s.emit(751, old('back'), 255, 8).emit(752)
            for i in page:
                s.compare(0x800C, i).jump(f'{tag}_pick{i}', 1)
            if n + 1 < len(pages):
                s.compare(0x800C, 20).jump(f'{label}{n + 1}', 1)
            if n > 0:
                s.compare(0x800C, 21).jump(label if n == 1 else f'{label}{n - 1}', 1)
            s.jump('top')
        for n, page in enumerate(pages):
            here = label if n == 0 else f'{label}{n}'
            for i in page:
                e, var, trainer = group[i], VARS[base + i], TRAINERS[base + i]
                s.label(f'{tag}_pick{i}')
                s.emit(294, e[1], 0x800C).compare(0x800C, 1).jump(f'{tag}_show{i}', 1)
                s.msg(old('locked')).jump(here)
                s.label(f'{tag}_show{i}')
                if pics is None:
                    s.msg(old((tag, 'blurb', i)))
                tier_branch(f'{tag}{i}', var, [f'{tag}_r{i}_{t}' for t in range(4)])
                for t in range(4):
                    s.label(f'{tag}_r{i}_{t}')
                    if pics is not None:
                        s.emit(452, *pics(tag, i, t))                                      # ShowPokepic: the card picture for this tier
                        s.msg(old((tag, 'blurb', i)))
                    s.msg(new(('tier', t)))
                    s.jump(f'{tag}_ask{i}')
                s.label(f'{tag}_ask{i}')
                s.emit(45)
                s.data.append(new('prompt') - 0)                                           # NPCMsg: the id is a byte (index < 250)
                s.emit(63, 0x800C)                                                         # YesNo
                s.emit(53)
                s.compare(0x800C, 0).jump(f'{tag}_go{i}', 1)
                if pics is not None:
                    s.emit(453)                                                            # hide the picture
                s.jump(here)
                s.label(f'{tag}_go{i}')
                if pics is not None:
                    s.emit(453)
                s.emit(213, trainer, 0, 0)                                                 # TrainerBattle
                s.emit(220, 0x800C).compare(0x800C, 1).jump('lost', 5)                      # CheckBattleWon
                s.compare(var, CAP).jump(f'{tag}_cap{i}', 4)
                s.emit(39, var, 1)                                                         # AddVar: one more rematch win
                s.label(f'{tag}_cap{i}')
                s.msg(new('won'))
                tier_branch(f'{tag}{i}', var, [f'{tag}_w{i}_{t}' for t in range(4)])
                for t in range(4):
                    s.label(f'{tag}_w{i}_{t}')
                    if pics is not None:
                        s.emit(452, *pics(tag, i, t))
                    s.msg(new(('tier', t)))
                    if pics is not None:
                        s.emit(453)
                    s.jump(here)
    s.label('lost')
    s.emit(219).emit(97).emit(2)                                                           # WhiteOut, ReleaseAll, End (as in the gym scripts)
    s.label('exit')
    s.emit(747).emit(97).emit(2)
    return s.finish()


def patch(rom):
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[ca.STD_TEXT])
    old_rows_msgs, ix_old = ca.messages()
    base_std = len(rows) - len(old_rows_msgs)
    assert base_std == 35, base_std                                                        # the album's rows must be the last ones
    extra, ix_new = new_messages(len(rows))
    assert len(rows) + len(extra) < 250, len(rows) + len(extra)
    assert len(set(VARS)) == 16 and all(0x4000 <= v <= 0x416F for v in VARS)
    rows.extend(decode_messages(encode_text(extra, PH))[1])
    texts.files[ca.STD_TEXT] = encode_messages(key, rows)
    bank = bytes(scripts.files[ca.STD_BANK])
    bank, count = append_bank(bank, [script(base_std, ix_old, ix_new)])
    assert count == 25, count
    scripts.files[ca.STD_BANK] = bytes(bank)
    new_id = ca.STD_BASE + count
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d, base = main.sections[0].data, main.sections[0].ramAddress
    at = STUB_LITERAL - base
    assert struct.unpack_from('<I', d, at)[0] == OLD_ID, hex(struct.unpack_from('<I', d, at)[0])
    struct.pack_into('<I', d, at, new_id)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.arm9 = main.save(compress=True)
    return dict(script_id=new_id, rows=(base_std, len(rows), len(extra)), vars=[hex(v) for v in VARS])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
