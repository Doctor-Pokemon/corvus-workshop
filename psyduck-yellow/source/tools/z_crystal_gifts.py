"""Prototype 0260 (owner order 2026-11-12): each Johto Gym Leader gives ONE Z-Crystal of the leader's specialty type (Z-Moves phase 4, JOHTO-POSTGAME-PLAN.md items 53-58).
Falkner Flyinium Z (785), Bugsy Buginium Z (787), Whitney Normalium Z (776), Morty Ghostium Z (789), Chuck Fightinium Z (782), Jasmine Steelium Z (792), Pryce Icium Z (781), Clair Dragonium Z (790).
The item ids are the HELD versions (776..): hg-engine keeps a second run (807..) for the bag versions; the Z-Move hook of z_swap/z_power accepts both runs. The names are the ROM's own ("Ghostium Z", not "Ghostinium").
Method = hm_gym_gifts.py: each leader's own script ends its normal paths (after the TM, and the repeat talk) with "WaitButton, CloseMsg, ReleaseAll, End"; every such tail inside the leader's script becomes a jump to a helper:
WaitButton, CloseMsg; the leader's badge owned and the leader's gift flag clear -> the leader's line, GiveItem, the gift flag set, fanfare, "received <crystal>!" (a bag-full line otherwise, the flag stays clear so the next talk retries); ReleaseAll, End.
CLAIR does not give her badge in her gym: in HeartGold she awards the Rising Badge in the Dragon's Den shrine (map 288, bank 112, script 4: GiveBadge 7). There the "WaitButton, CloseMsg, ReleaseAll" right after the badge (6 bytes, followed by more script) becomes a jump to a helper that
does the same and then continues at the next instruction (SetFlag 0x998 ...). Bag full there = no retry (known gap: the Den scene runs once).
FLAGS: 0x9DB-0x9DF and 0x9E1-0x9E3 (one gift flag per leader, found free with an opcode + literal + event + list-neighbour scan of ROM 0259; the project's old strict scan finds none left). The lines are PLACEHOLDERS (no owner text exists for these gifts).
Usage (from yellow-heartgold, PYTHONPATH=tools): z_crystal_gifts.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
import map_header_extension as ext
from ext_edit import ExtEdit
from johto_step3d import install
from johto_step3d import starts as bank_starts
from johto_step3e import A
from map_edit import MapEdit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages

TAIL = struct.pack('<4H', 50, 53, 97, 2)                # WaitButton, CloseMsg, ReleaseAll, End
TAIL3 = struct.pack('<3H', 50, 53, 97)                  # the same without End (Clair's scene continues)
FULL = 'You have no room for this.'
LINE = 'Take this Z-Crystal, too.'

# (name, map, actor, badge index, item id, crystal name, gift flag)
GIFTS = [
    ('Falkner', 135, 0, 0, 785, 'Flyinium Z', 0x9DB),
    ('Bugsy', 180, 5, 1, 787, 'Buginium Z', 0x9DC),
    ('Whitney', 137, 0, 2, 776, 'Normalium Z', 0x9DD),
    ('Morty', 80, 1, 3, 789, 'Ghostium Z', 0x9DE),
    ('Chuck', 139, 0, 4, 782, 'Fightinium Z', 0x9DF),
    ('Jasmine', 138, 0, 5, 792, 'Steelium Z', 0x9E1),
    ('Pryce', 140, 0, 6, 781, 'Icium Z', 0x9E2),
]
CLAIR = ('Clair', 288, 7, 790, 'Dragonium Z', 0x9E3)     # Dragon's Den, script 4, the first tail after GiveBadge 7


def helper(base, badge, item, flag, m_line, m_got, m_full, after=None):
    a = A()
    a.raw(struct.pack('<2H', 50, 53))                                # WaitButton, CloseMsg (the two commands the replaced tail started with)
    a.op(294, badge, 0x800C).compare(0x800C, 0).jump('done', 1)
    a.check_flag(flag).jump('done', 1)
    a.msg(m_line)
    a.op(125, item, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    a.op(30, flag)
    a.op(78, 0x4A1).msg(m_got).op(79)
    a.label('done').raw(struct.pack('<H', 97))                       # ReleaseAll
    if after is None:
        a.raw(struct.pack('<H', 2))                                  # End
    else:
        a.jump(('abs', after))
    a.label('full').msg(m_full).raw(struct.pack('<H', 97))
    if after is None:
        a.raw(struct.pack('<H', 2))
    else:
        a.jump(('abs', after))
    return a.build(base)


def open_map(rom, map_id):
    return ExtEdit(rom, map_id) if map_id >= ext.NATIVE_COUNT else MapEdit(rom, map_id)


def patch_leader(rom, name, map_id, actor, badge, item, crystal, flag):
    e = open_map(rom, map_id)
    sid = struct.unpack_from('<H', e.groups[1][actor], 10)[0]
    m_line, m_got, m_full = e.message(LINE), e.message('{PLAYER} received %s!' % crystal), e.message(FULL)
    size = len(helper(0, badge, item, flag, m_line, m_got, m_full))
    ids, addrs, _ = install(e, [size])
    code = helper(addrs[0], badge, item, flag, m_line, m_got, m_full)
    assert len(code) == size
    bank = bytearray(e.bank)
    bank[addrs[0]:addrs[0] + size] = code
    st = bank_starts(bytes(bank))
    begin = st[sid - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    assert bytes(bank).find(struct.pack('<2H', 295, badge), begin, end) >= 0, (name, 'the actor script does not give the badge')
    sites, p = [], bytes(bank).find(TAIL, begin, end)
    while p >= 0:
        sites.append(p)
        p = bytes(bank).find(TAIL, p + 1, end)
    assert sites, (name, begin, end)
    for p in sites:
        bank[p:p + 8] = struct.pack('<Hi', 22, addrs[0] - (p + 6)) + b'\0\0'
    e.bank = bytes(bank)
    e.save()
    return dict(map=map_id, script=sid, helper=ids[0], tails=sites, item=item, flag=hex(flag))


def patch_clair(rom):
    name, map_id, badge, item, crystal, flag = CLAIR
    e = open_map(rom, map_id)
    m_line, m_got, m_full = e.message(LINE), e.message('{PLAYER} received %s!' % crystal), e.message(FULL)
    size = len(helper(0, badge, item, flag, m_line, m_got, m_full, after=0))
    ids, addrs, _ = install(e, [size])                       # install() may move script offsets: every offset below is found AFTER it
    bank = bytearray(e.bank)
    badge_at = bytes(bank).find(struct.pack('<2H', 295, badge))
    assert badge_at >= 0 and bytes(bank).count(struct.pack('<2H', 295, badge)) == 1
    site = bytes(bank).find(TAIL3, badge_at)
    assert site >= 0 and site - badge_at < 400, (badge_at, site)
    code = helper(addrs[0], badge, item, flag, m_line, m_got, m_full, after=site + 6)
    assert len(code) == size
    bank[addrs[0]:addrs[0] + size] = code
    bank[site:site + 6] = struct.pack('<Hi', 22, addrs[0] - (site + 6))
    e.bank = bytes(bank)
    e.save()
    return dict(map=map_id, helper=ids[0], tail=site, after_badge=site - badge_at, item=item, flag=hex(flag))


TYPES = ['Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dragon', 'Dark', 'Steel', 'Fairy']
DESC_BANK, DESC_BASE = 842, 776                          # items 776-1073 read their description from text bank 842 (row = id - 776, see item_description_banks2.py)


def patch_descriptions(rom):
    """The 18 Z-Crystals (held ids 776-793 and bag ids 807-824) had BLANK descriptions: each gets three lines (the bag window fits 36 characters per line)."""
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[DESC_BANK])
    done = 0
    for first in (776, 807):
        for i, t in enumerate(TYPES):
            text = "A crystal for a Pok\u00e9mon to hold.\nIt turns the holder's %s-type\nmove into a Z-Move once per battle." % t
            assert max(len(l) for l in text.split('\n')) <= 36, text
            row = first - DESC_BASE + i
            assert rows[row] == [65535], ('description row not blank', first + i)
            rows[row] = decode_messages(encode_text([text], PH))[1][0]
            done += 1
    texts.files[DESC_BANK] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    return done


def patch(rom):
    report = {'descriptions': patch_descriptions(rom)}
    for gift in GIFTS:
        report[gift[0]] = patch_leader(rom, *gift)
    report['Clair'] = patch_clair(rom)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
