"""ROM 0274: Field Kit lines are generic (owner 2026-11-13, option 2: "the Pokemon still animates, the line stops naming it").
Before: with the Field Kit and no Pokemon that knows the move, the lead Pokemon stands in (field_kit.py / field_kit2.py) and the game's own lines name it: "<Pokemon> used STRENGTH!", "<Pokemon>'s STRENGTH made it possible to push large boulders!".
Now: those lines are the same texts, but string buffer 0 (the {0} / Pokemon-name slot) holds the item name "Field Kit" when the Kit stands in: "Field Kit used STRENGTH!", "Field Kit's STRENGTH made it possible ...". A party Pokemon that knows the move is named as always.
How (script bank 1165 only):
 - seven new slot helpers (one per move: Cut 15, Rock Smash 249, Strength 70, Rock Climb 431, Surf 57, Waterfall 127, Whirlpool 250) replace the old ones at all twelve Call sites: same logic as before, plus work variable 0x800B = 1 when the Kit stands in, else 0;
 - at each of the eight places where the obstacle scripts do `BufferPartyMonNick 0,var ; NPCMsg n` (8 bytes) there is now `Call helper ; Noop`; the helper buffers the item name Field Kit (BufferItemName 0, item 1128 through work variable 0x800A) when 0x800B is 1, else the party Pokemon's nickname, then shows message n and returns.
No text row changes, no ARM9 or overlay change; the Pokemon's animation is untouched.
Usage (from yellow-heartgold, PYTHONPATH=tools): kit_generic.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import field_kit
from johto_step1b import script_ranges
from opening import Script
from parcel_quest import append_bank

BANK, KIT = 1165, field_kit.KIT
MODE, TMP = 0x800B, 0x800A
MOVES = (15, 249, 70, 431, 57, 127, 250)
BUF_NICK, BUF_ITEM, NPC_MSG, CALL, NOOP = 199, 194, 45, 26, 0


def slot_helper(move):
    s = Script()
    s.emit(141, 0x800C, move)
    s.compare(0x800C, 6).jump('kit', 1)
    s.emit(41, MODE, 0).jump('done')
    s.label('kit').emit(128, KIT, 1, 0x800C).compare(0x800C, 1).jump('have', 1)
    s.emit(41, 0x800C, 6).emit(41, MODE, 0).jump('done')
    s.label('have').emit(41, 0x800C, 0).emit(41, MODE, 1)
    s.label('done').emit(27)
    return s.finish()


def message_helper(var, idx):
    s = Script()
    s.compare(MODE, 1).jump('kit', 1)
    s.data.extend(struct.pack('<HBH', BUF_NICK, 0, var))
    s.jump('msg')
    s.label('kit').emit(41, TMP, KIT)
    s.data.extend(struct.pack('<HBH', BUF_ITEM, 0, TMP))
    s.label('msg')
    s.data.extend(struct.pack('<HB', NPC_MSG, idx))
    s.emit(27)
    return s.finish()


def patch(rom):
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    old = bytes(scripts.files[BANK])
    starts, _ = script_ranges(old)
    # old slot helpers: the scripts that begin with GetPartySlotWithMove 0x800C,<move> (appended by field_kit.py / field_kit2.py)
    helpers = {}
    for st in starts:
        for move in MOVES:
            if old[st:st + 6] == struct.pack('<3H', 141, 0x800C, move):
                helpers[move] = st
    assert set(helpers) == set(MOVES), sorted(helpers)
    call_sites = {m: [p for p in range(len(old) - 6) if struct.unpack_from('<H', old, p)[0] == CALL and p + 6 + struct.unpack_from('<i', old, p + 2)[0] == helpers[m]] for m in MOVES}
    assert [len(call_sites[m]) for m in MOVES] == [2, 1, 2, 2, 1, 2, 2], {m: len(v) for m, v in call_sites.items()}
    # message sites: BufferPartyMonNick 0,var ; NPCMsg n  with var 0x800C / 0x8004 (the menu scripts use 0x8000: left alone)
    msg_sites = []
    for p in range(len(old) - 8):
        if struct.unpack_from('<HBH', old, p) in ((BUF_NICK, 0, 0x800C), (BUF_NICK, 0, 0x8004)) and struct.unpack_from('<H', old, p + 5)[0] == NPC_MSG:
            msg_sites.append((p, struct.unpack_from('<H', old, p + 3)[0], old[p + 7]))
    assert len(msg_sites) == 8, msg_sites
    new_scripts = [slot_helper(m) for m in MOVES] + [message_helper(var, idx) for _, var, idx in msg_sites]
    bank, count = append_bank(old, new_scripts)
    bank = bytearray(bank)
    shift = 4 * len(new_scripts)
    target = lambda n: (count + n) * 4 + 4 + struct.unpack_from('<I', bank, (count + n) * 4)[0]
    report = {}
    for n, m in enumerate(MOVES):
        for p in call_sites[m]:
            at = p + shift
            assert struct.unpack_from('<H', bank, at)[0] == CALL
            struct.pack_into('<i', bank, at + 2, target(n) - (at + 6))
        report[m] = len(call_sites[m])
    for k, (p, var, idx) in enumerate(msg_sites):
        at = p + shift
        assert bytes(bank[at:at + 8]) == struct.pack('<HBH', BUF_NICK, 0, var) + struct.pack('<HB', NPC_MSG, idx)
        bank[at:at + 8] = struct.pack('<Hi', CALL, target(len(MOVES) + k) - (at + 6)) + struct.pack('<H', NOOP)
    scripts.files[BANK] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return dict(slot_calls=report, message_sites=[(p + shift, idx) for p, _, idx in msg_sites], first_new_script=count + 1)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
