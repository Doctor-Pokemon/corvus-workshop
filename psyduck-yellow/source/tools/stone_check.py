"""Prototype 0231: the Kanto starter stone check (owner design 2026-11-11, plan item 40).

Built from ROM 0230. Four parts:
1. Origin game and ball for created Pokemon (found by tracing the engine; every address below was verified on a scratch ROM):
   A ARM9 0x02072178: the pointer literal in the "trainer memo" setter (0x0207213C) now points at a word holding 254 (Psyduck Yellow) instead of the global game
     version word 0x020F566C (=7, used by many other routines, left alone). Gifts and captures pass through this setter.
   B overlay 129 0x023DA8FA / 0x023DA900: hg-engine's creator (0x023DA8F4) stores the origin as a literal 7 and derives the language as 7-5; both instructions change
     together (254 and 254-252) so the language stays 2. Covers eggs, NPC trades and every other created Pokemon.
   C overlay 129 0x023DA9C2: the creator's default ball 4 -> 16 (Cherish Ball). Captures overwrite it with the ball thrown (checked with a Master Ball).
   D ARM9 0x0206C8EC: SetEggStats' ball (movs r1,#4 -> #16): GiveEgg and the Togepi egg.
   E overlay 129 0x023DA820: hg-engine's gift function passes the ball to the memo setter as `movs r2,#4`; -> #16 (script command 137 gifts).
   The 254 word lives in a zero gap of overlay 129 (0x023DE780, whole 4 bytes asserted zero inside a longer run).
   Day Care egg balls stay Poke Balls on purpose (0x0206CA20 untouched).
2. Classic Ribbon (ribbon 78) on the three Kanto gift Pokemon: Bulbasaur (Cerulean, map 431 script 1), Charmander (Route 24, map 28 script 2), Squirtle (Vermilion,
   map 54 script 15). Each success tail (SetFlag ... ReleaseAll, End) is replaced in place by `GoTo helper`; the helper (appended to the bank) gives the ribbon to the
   last party slot (GetPartyCount - 1) and then runs the original tail bytes unchanged.
3. NO toss lock (tried and removed, 2026-11-11): item bit 5 (the "prevent toss" bit the Silph Scope has) hides TRASH but also GIVE, and the party menu then says
   "can't be held", so a locked stone could never be held for Mega Evolution; bit 6 swaps TRASH for REGISTER (a registered stone has no field use: crash risk). The item
   data has no toss-only bit; hiding TRASH for the starter stones would need a bag-menu code patch (not done). What IS kept: every starter stone's buy price must be 0
   (asserted), which the Mart's SELL refuses (checked in the emulator), and the 19 stones of STARTER_STONES are listed here for that and for later work.
4. The stone check: the Pokemon Lab aide at (6,10) (map 505, script 2) now, after his own line, looks through the party for a Bulbasaur/Charmander/Squirtle line
   FULLY EVOLVED (Venusaur 3, Charizard 6, Blastoise 9) with friendship 255 and the Classic Ribbon, and gives Venusaurite (659), Charizardite X (660) + Y (678) or
   Blastoisinite (661). One flag per stone (0xA54..0xA57, grepped free in every script bank, actor list and tool source) is set only after a successful give; a full
   bag keeps the flag clear (retry). The three new lines are PLACEHOLDERS (no owner text yet) and avoid the word Mega.
Usage (from yellow-heartgold, PYTHONPATH=tools): stone_check.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages
from viridian_tutorial import TABLE
import mega_shop

CLASSIC = 78
ORIGIN, CHERISH = 254, 16
WORD_AT = 0x23DE780                         # new u32 = 254, inside the zero run 0x23DE6FE..0x23DE807 of overlay 129
FLAG_V, FLAG_X, FLAG_Y, FLAG_B = 0xA54, 0xA55, 0xA56, 0xA57
STONES = ((3, ((659, FLAG_V),)), (6, ((660, FLAG_X), (678, FLAG_Y))), (9, ((661, FLAG_B),)))      # species, (item, flag)
GIFTS = (dict(name='Bulbasaur', map=431, species=1, hook=145, end=180), dict(name='Charmander', map=28, species=4, hook=912, end=947),
         dict(name='Squirtle', map=54, species=7, hook=2396, end=2436))
STARTER_STONES = (659, 660, 678, 661,                   # Gen 1: Venusaurite, Charizardite X / Y, Blastoisinite
                  2563, 2564, 3148,                      # Gen 2: Meganiumite, Feraligite, Typhlosionite
                  753, 664, 752,                         # Gen 3: Sceptilite, Blazikenite, Swampertite
                  2635, 2636,                            # Yellow's own starter: Raichunite X / Y (Pikachu line)
                  2569,                                  # Gen 5: Emboarite
                  2575, 2576, 2577,                      # Gen 6: Chesnaughtite, Delphoxite, Greninjite
                  3145, 3146, 3147)                      # this game's starters: Eonite (Eevee line), Psyduckite, Stellareonite
LAB, AIDE = 505, 2                          # Pokemon Lab, the aide at (6,10) (actor 1, script 2)
AIDE_TAIL = 777                             # offset of "WaitButton, CloseMsg, ReleaseAll, End" in the lab bank (8 bytes)
LINES = ['That POKéMON adores you! Please take this rare stone as a keepsake.', '{PLAYER} received a rare stone!', 'You have no room for this. Come back with space in your pack.']
WALK = {30: [2], 76: [2, 2], 77: [], 78: [2], 79: [], 45: [1], 50: [], 53: [], 97: [], 2: [], 190: [1], 191: [1], 101: [2]}     # opcodes allowed in a gift success tail


def u16(d, at):
    return struct.unpack_from('<H', d, at)[0]


def walk(bank, start, end):
    """Walk commands from start; they must be plain (no jumps) and end exactly at `end` with End."""
    at = start
    while at < end:
        op = u16(bank, at)
        assert op in WALK, (at, op)
        at += 2 + sum(WALK[op])
        if op == 2:
            break
    assert at == end, (at, end)


def first_flag_check(scripts, texts_events, flags):
    for f in flags:
        assert not any(struct.pack('<HH', op, f) in bytes(raw) for raw in scripts.files for op in (30, 31, 32)), f'flag {f:#x} is used in a script'
        for raw in texts_events.files:
            try:
                from opening import events_decode
                groups = events_decode(bytes(raw))
            except Exception:
                continue
            assert not any(struct.unpack_from('<H', row, 8)[0] == f for row in groups[1]), f'flag {f:#x} is an actor flag'


def stamp(main, ovs):
    d = main.sections[0].data
    base = main.ramAddress
    perm = ovs[129]
    pb = perm.ramAddress

    def a9(addr, old, new):
        o = addr - base
        assert bytes(d[o:o + len(old)]) == old, (hex(addr), bytes(d[o:o + len(old)]).hex())
        d[o:o + len(new)] = new

    def o129(addr, old, new):
        o = addr - pb
        assert bytes(perm.data[o:o + len(old)]) == old, (hex(addr), bytes(perm.data[o:o + len(old)]).hex())
        perm.data[o:o + len(new)] = new

    zero_run = bytes(perm.data[0x23DE6FE - pb:0x23DE808 - pb])
    assert zero_run == bytes(len(zero_run)) and 0x23DE6FE <= WORD_AT and WORD_AT + 4 <= 0x23DE808, 'the 254 word gap is not free'
    o129(WORD_AT, bytes(4), struct.pack('<I', ORIGIN))
    a9(0x2072178, struct.pack('<I', 0x20F566C), struct.pack('<I', WORD_AT))                      # A
    o129(0x23DA8FA, bytes.fromhex('0723'), bytes([ORIGIN, 0x23]))                                # B: movs r3,#7 -> #254
    o129(0x23DA900, bytes.fromhex('053b'), bytes([ORIGIN - 2, 0x3B]))                            # B: subs r3,#5 -> subs r3,#252 (language stays 2)
    o129(0x23DA9C2, bytes.fromhex('0423'), bytes([CHERISH, 0x23]))                               # C
    a9(0x206C8EC, bytes.fromhex('0421'), bytes([CHERISH, 0x21]))                                 # D
    o129(0x23DA820, bytes.fromhex('0422'), bytes([CHERISH, 0x22]))                               # E


def hook(bank, tail_at, tail, helper):
    """Append `helper` to the bank and turn the 6 bytes at tail_at into GoTo helper; return the new bank."""
    out, count = append_bank(bank, [helper])
    helper_at = struct.unpack_from('<I', out, count * 4)[0] + count * 4 + 4
    pos = tail_at + 4                                                  # the header grew by one entry
    assert bytes(out[pos:pos + len(tail)]) == tail, 'bank shifted unexpectedly'
    out[pos:pos + 6] = struct.pack('<Hi', 22, helper_at - (pos + 6))
    return bytes(out)


def ribbon_helper(tail):
    s = Script().emit(332, 0x800C).emit(40, 0x800C, 1).emit(481, 0x800C, CLASSIC)               # slot = party count - 1, GiveRibbon slot CLASSIC
    s.data.extend(tail)
    return s.finish()


def lab_helper(first):
    s = Script().emit(50).emit(53)                                                                # WaitButton, CloseMsg (his own line was shown)
    s.emit(332, 0x800D)                                                                           # party count
    for n, (species, stones) in enumerate(STONES):
        nxt = f'start{n + 1}'
        s.label(f'start{n}')
        s.emit(32, stones[0][1]).jump(f'chk{n}', 1) if len(stones) > 1 else s.emit(32, stones[0][1]).jump(nxt, 1)
        if len(stones) > 1:
            s.jump(f'slot{n}_0')
            s.label(f'chk{n}')
            s.emit(32, stones[1][1]).jump(nxt, 1)
        for slot in range(6):
            s.label(f'slot{n}_{slot}')
            after = f'slot{n}_{slot + 1}' if slot < 5 else nxt
            s.compare(0x800D, slot + 1).jump(nxt, 0)                                              # fewer party members than this slot
            s.emit(354, slot, 0x800C).compare(0x800C, species).jump(after, 5)                      # GetPartyMonSpecies slot -> var, must be the species
            s.emit(382, 0x800C, slot).compare(0x800C, 255).jump(after, 5)                          # MonGetFriendship var, slot
            s.emit(480, 0x800C, slot, CLASSIC).compare(0x800C, 1).jump(after, 5)                   # MonHasRibbon var, slot, ribbon (handler 0x0204E26C)
            s.jump(f'give{n}')
        s.label(f'give{n}')
        s.msg(first)
        for i, (item, flag) in enumerate(stones):
            s.emit(32, flag).jump(f'skip{n}_{i}', 1)
            s.emit(125, item, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
            s.emit(30, flag).emit(78, 1185).msg(first + 1).emit(79)
            s.label(f'skip{n}_{i}')
        s.jump(nxt)
    s.label(f'start{len(STONES)}')
    s.jump('finish')
    s.label('full')
    s.msg(first + 2)
    s.label('finish')
    s.emit(97).emit(2)
    return s.finish()


def patch(rom, source=None):
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d = main.sections[0].data
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    events = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/3/2')])
    items = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/7')])      # read only: prices are asserted, nothing is written
    first_flag_check(scripts, events, (FLAG_V, FLAG_X, FLAG_Y, FLAG_B))
    stamp(main, ovs)
    report = dict(flags=[hex(f) for f in (FLAG_V, FLAG_X, FLAG_Y, FLAG_B)])
    for g in GIFTS:
        sid = u16(d, TABLE + g['map'] * 24 + 6)
        bank = bytes(scripts.files[sid])
        give = struct.pack('<7H', 137, g['species'], 10, 0, 0, 0, 0x800C)
        assert bank.count(give) == 1, g['name']
        at = bank.index(give)
        assert at + 27 == g['hook'], (g['name'], at)
        tail = bank[g['hook']:g['end']]
        assert tail.endswith(bytes.fromhex('61000200')), g['name']
        walk(bank, g['hook'], g['end'])
        scripts.files[sid] = hook(bank, g['hook'], tail, ribbon_helper(tail))
        report[g['name']] = dict(file=sid, hook=g['hook'])
    table_stones = mega_shop.mega_stones(rom)[0]
    assert len(table_stones) == 94 and set(STARTER_STONES) - {3148} <= set(table_stones)   # the first 106 table entries; Typhlosionite (3148) was added later
    for i in STARTER_STONES:
        assert struct.unpack_from('<H', items.files[i], 0)[0] == 0, i                            # price 0: the Mart refuses to buy it back
    report['starter_stones_price0'] = len(STARTER_STONES)
    rec = TABLE + LAB * 24
    sid, _, tid = struct.unpack_from('<3H', d, rec + 6)
    bank = bytes(scripts.files[sid])
    assert bank[AIDE_TAIL:AIDE_TAIL + 8] == bytes.fromhex('32003500610002 00'.replace(' ', '')), bank[AIDE_TAIL:AIDE_TAIL + 8].hex()
    key, lines = decode_messages(texts.files[tid])
    first = len(lines)
    lines.extend(decode_messages(encode_text(LINES, PH))[1])
    scripts.files[sid] = hook(bank, AIDE_TAIL, bank[AIDE_TAIL:AIDE_TAIL + 8], lab_helper(first))
    texts.files.append(encode_messages(key, lines))
    struct.pack_into('<H', d, rec + 10, len(texts.files) - 1)
    report['lab'] = dict(script_file=sid, first_message=first, text_file=len(texts.files) - 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    rom.arm9 = main.save(compress=True)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
