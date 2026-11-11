"""Prototype 0222: the Silph Co. FIELD KIT, first version (owner 2026-11-10: a competitive team is hard to build around keeping eight HMs on hand; plan "Silph Co. Field Kit" in CAMPAIGN-FIRST-PLAN.md).
SCOPE (scripts and item data only, no engine code): Cut trees, Rock Smash rocks and Strength boulders. NOT in this version: Surf, Fly, Flash, Waterfall, Whirlpool, Rock Climb (game code, not scripts).
 1. The item: Exp. Candy XL (id 1128, an item the owner dropped: nothing gives it) becomes the key item "Field Kit": the record and the icon of the Lift Key, the name in text bank 222, a description in bank 846 row 54 (id - 1074).
 2. The obstacles: the shared obstacle bank (std script bank 1165) asks "GetPartySlotWithMove var,move" and then checks the badge. Each such site (Cut: 2, Rock Smash: 1, Strength: 2) becomes a CALL to a small helper that returns the party slot as before, or slot 0 (the lead Pokemon stands in) when nobody knows the move but the bag holds the Kit, or 6 ("nobody") otherwise.
    The badge rules are untouched, so Cut still needs Cascade (or Hive), Rock Smash the Boulder Badge, Strength Marsh (or Plain). The confirm text still names the lead Pokemon ("... used CUT!"): a generic Kit text is a later polish.
 3. The reward: the Silph Co. President (map 574, script 9) gives the Kit once, right after the Master Ball (the ends of his two normal talks jump to a helper that gives it when the bag lacks it). The lines are placeholders.
Usage (from yellow-heartgold, PYTHONPATH=tools): field_kit.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from ext_edit import ExtEdit
from johto_step3d import install
from johto_step3d import starts as bank_starts
from johto_step3e import A
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages

KIT, LIFT_KEY = 1128, 878
STD_BANK = 1165
GET_SLOT = 141                                              # GetPartySlotWithMove (pret script.inc)
SITES = ((15, 'Cut'), (249, 'Rock Smash'), (70, 'Strength'))
PRESIDENT_MAP, TAIL = 574, struct.pack('<4H', 50, 53, 97, 2)  # WaitButton, CloseMsg, ReleaseAll, End
NAME = 'Field Kit'
DESCRIPTION = "A Silph Co. kit. With the right\nBADGE, it lets you use CUT, ROCK\nSMASH and STRENGTH without a Pokémon."
LINE = "Take this FIELD KIT, too! With the\nright BADGE, it lets you use CUT,\nROCK SMASH and STRENGTH on your own."
GOT = '{PLAYER} received the FIELD KIT!'
FULL = 'You have no room for this.'


def row(text):
    return decode_messages(encode_text([text], PH))[1][0]


def helper(move):
    s = Script()
    s.emit(GET_SLOT, 0x800C, move)
    s.compare(0x800C, 6).jump('done', 5)                    # slot != 6: a party Pokemon knows the move
    s.emit(128, KIT, 1, 0x800C).compare(0x800C, 1).jump('kit', 1)   # HaveItem Kit
    s.emit(41, 0x800C, 6).jump('done')                      # nobody, no Kit
    s.label('kit').emit(41, 0x800C, 0)                      # the lead Pokemon stands in
    s.label('done').emit(27)                                # Return
    return s.finish()


def patch_item(rom):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    items.files[KIT] = bytes(items.files[LIFT_KEY])
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    gfx.files[KIT * 2 + 2], gfx.files[KIT * 2 + 3] = bytes(gfx.files[LIFT_KEY * 2 + 2]), bytes(gfx.files[LIFT_KEY * 2 + 3])
    rom.setFileByName('a/0/1/8', gfx.save())
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[222])
    rows[KIT] = row(NAME)
    texts.files[222] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[846])
    rows[KIT - 1074] = row(DESCRIPTION)
    texts.files[846] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()


def patch_obstacles(rom):
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    old = bytes(scripts.files[STD_BANK])
    sites = []
    for move, name in SITES:
        pat = struct.pack('<3H', GET_SLOT, 0x800C, move)
        i = old.find(pat)
        found = []
        while i >= 0:
            found.append(i)
            i = old.find(pat, i + 1)
        assert found, name
        sites.append((move, name, found))
    bank, count = append_bank(old, [helper(m) for m, _ in SITES])
    shift = 4 * len(SITES)
    bank = bytearray(bank)
    report = {}
    for n, (move, name, found) in enumerate(sites):
        target = (count + n) * 4 + 4 + struct.unpack_from('<I', bank, (count + n) * 4)[0]
        for f in found:
            at = f + shift
            assert bytes(bank[at:at + 6]) == struct.pack('<3H', GET_SLOT, 0x800C, move), (name, at)
            bank[at:at + 6] = struct.pack('<Hi', 26, target - at - 6)
        report[name] = dict(sites=found, helper=count + n + 1)
    scripts.files[STD_BANK] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return report


def president_helper(base, m_line, m_got, m_full):
    a = A()
    a.raw(struct.pack('<2H', 50, 53))                       # WaitButton, CloseMsg
    a.op(128, KIT, 1, 0x800C).compare(0x800C, 1).jump('done', 1)
    a.msg(m_line)
    a.op(125, KIT, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    a.op(78, 0x4A1).msg(m_got).op(79)
    a.label('done').raw(struct.pack('<2H', 97, 2))
    a.label('full').msg(m_full).raw(struct.pack('<2H', 97, 2))
    return a.build(base)


def patch_president(rom):
    e = ExtEdit(rom, PRESIDENT_MAP)
    pat = struct.pack('<2H', 125, 1)                        # GiveItem Master Ball
    at = e.bank.find(pat)
    assert at >= 0
    offs = bank_starts(e.bank)
    script = max(j for j, x in enumerate(offs) if x <= at) + 1
    m_line, m_got, m_full = e.message(LINE), e.message(GOT), e.message(FULL)
    size = len(president_helper(0, m_line, m_got, m_full))
    ids, addrs, _ = install(e, [size])
    code = president_helper(addrs[0], m_line, m_got, m_full)
    assert len(code) == size
    bank = bytearray(e.bank)
    bank[addrs[0]:addrs[0] + size] = code
    st = bank_starts(bytes(bank))
    begin = st[script - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    sites, p = [], bytes(bank).find(TAIL, begin, end)
    while p >= 0:
        sites.append(p)
        p = bytes(bank).find(TAIL, p + 1, end)
    assert sites, (begin, end)
    gift = bytes(bank).find(pat, begin, end)
    # only the two ordinary endings AFTER the Master Ball ("NPCMsg 5"): not the early "not yet" talk (NPCMsg 6) and not the bag-full branch (NPCMsg 7)
    sites = [p for p in sites if p > gift and bytes(bank[p - 3:p]) == struct.pack('<HB', 45, 5)]
    assert len(sites) == 2, sites
    for p in sites:
        bank[p:p + 8] = struct.pack('<Hi', 22, addrs[0] - (p + 6)) + b'\0\0'
    e.bank = bytes(bank)
    e.save()
    return dict(map=PRESIDENT_MAP, script=script, helper=ids[0], tails=sites)


def patch(rom):
    patch_item(rom)
    return dict(obstacles=patch_obstacles(rom), president=patch_president(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
