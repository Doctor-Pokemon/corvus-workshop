"""Prototype 0215: the eight Kanto gyms and the S.S. Anne captain give the eight HMs, and each Kanto badge unlocks one HM (owner table 2026-11-10, JOHTO-POSTGAME-PLAN.md item 15).
badge -> unlocks -> gift:  Boulder -> Rock Smash -> Brock gives Rock Smash (HM06, item 425);  Cascade -> Cut -> the S.S. Anne captain (already built);
Thunder -> Fly -> Surge gives Fly (HM02, 421);  Rainbow -> Waterfall -> Misty gives Waterfall (HM07, 426);  Soul -> Surf -> Janine (built);  Marsh -> Strength -> Sabrina (built);
Volcano -> Whirlpool -> Blaine gives Rock Climb (HM08, 427);  Earth -> Rock Climb -> Giovanni gives Whirlpool (HM05, 424).  Erika gives none.

Gifts: each leader's native script ends its normal paths (TM given / repeat talk) with "WaitButton, CloseMsg, ReleaseAll, End". Every such tail inside the leader's own script becomes a jump to a helper:
WaitButton, CloseMsg; badge owned and HM not in the bag -> the leader's line, GiveItem, fanfare, "received HMxx!" (a bag-full line otherwise; the next talk retries); then ReleaseAll, End.
"Already given" is the item itself (HMs cannot be tossed): no flag, no variable. The lines are PLACEHOLDERS (no owner text exists for these five leaders yet).

Badges (found 2026-11-10 with TestBadge call scan + script scan): Fly has no badge check in this ROM (a party with no badges opens the Fly map); Rock Climb already needs the Earth Badge (15) in the party menu and in the shared obstacle script;
Rock Smash checked the Zephyr Badge (0), Waterfall the Rising Badge (7), Whirlpool the Glacier Badge (6). Each of those three now tests the Kanto badge (Boulder 8, Rainbow 11, Volcano 14): the party-menu check
(ARM9), Waterfall's field check (overlay 101) and the shared obstacle script's CheckBadge now test the Kanto badge instead (overlay 129 has no room for hooks; every Johto player owns all eight Kanto badges).

Usage (from yellow-heartgold, PYTHONPATH=tools): hm_gym_gifts.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
import map_header_extension as ext
from ext_edit import ExtEdit
from johto_step3d import install
from johto_step3d import starts as bank_starts
from johto_step3e import A
from kanto_strength_badge import _bl, STD_BANK_FIRST_ID, STD_BANK_TEXT, TEST_BADGE
from map_edit import MapEdit

TAIL = struct.pack('<4H', 50, 53, 97, 2)                # WaitButton, CloseMsg, ReleaseAll, End
FULL = 'You have no room for this.'
LINE = 'Take this HM, too.'

# (map, actor, badge, item, HM number)
GIFTS = [
    ('Brock', 473, 1, 8, 425, 6),
    ('Misty', 427, 3, 9, 426, 7),
    ('Surge', 365, 9, 10, 421, 2),
    ('Blaine', 457, 0, 14, 427, 8),
    ('Giovanni', 579, 8, 15, 424, 5),
]
# (ARM9 address of the "bl TestBadge", badge it tested, the Kanto badge it tests now)
ARM9_SITES = [(0x0206828A, 0, 8), (0x02068342, 7, 11), (0x02068886, 6, 14)]
OV101_SITE = (0x021F43D2, 7, 11)                        # Waterfall in the field-action chooser (overlay 101)
SCRIPT_SITES = [(0, 8), (7, 11), (6, 14)]               # CheckBadge sites in the shared obstacle bank: Rock Smash, Waterfall, Whirlpool


def patch_badges(rom):
    """Overlay 129 has no room left for hooks (16 bytes), so each check is repointed in place: the immediate loaded before the TestBadge call (or the CheckBadge operand in the script) becomes the Kanto badge.
    Every player who reaches Johto owns all eight Kanto badges (Johto is the postgame), so nothing is lost; Johto's own badge no longer opens these three moves."""
    ovs = rom.loadArm9Overlays()
    site, was, new = OV101_SITE
    o101 = ovs[101]
    o101.data = bytearray(o101.data)
    at = site - o101.ramAddress
    assert bytes(o101.data[at - 2:at]) == bytes((was, 0x21)) and bytes(o101.data[at:at + 4]) == _bl(site, TEST_BADGE), bytes(o101.data[at - 2:at + 4]).hex()
    o101.data[at - 2] = new
    rom.files[o101.fileID] = o101.save(compress=o101.compressed)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    main = rom.loadArm9()
    section = main.sections[0]
    section.data = bytearray(section.data)
    for site, was, new in ARM9_SITES:
        at = site - section.ramAddress
        assert bytes(section.data[at - 2:at]) == bytes((was, 0x21)) and bytes(section.data[at:at + 4]) == _bl(site, TEST_BADGE), hex(site)
        section.data[at - 2] = new
    hits = [i for i in range(0, len(section.data) - 6, 2) if struct.unpack_from('<3H', section.data, i)[::2] == (STD_BANK_FIRST_ID, STD_BANK_TEXT)]
    assert len(hits) == 1, hits
    bank_file = struct.unpack_from('<H', section.data, hits[0] + 2)[0]
    rom.arm9 = main.save(compress=True)
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    bank = bytearray(scripts.files[bank_file])
    for was, new in SCRIPT_SITES:
        needle = struct.pack('<3H', 294, was, 0x800C)
        assert bytes(bank).count(needle) == 1, (was, bytes(bank).count(needle))
        struct.pack_into('<H', bank, bytes(bank).index(needle) + 2, new)
    scripts.files[bank_file] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return dict(std_bank_file=bank_file, arm9=[hex(x[0]) for x in ARM9_SITES], overlay101=hex(OV101_SITE[0]))


def helper(base, badge, item, m_line, m_got, m_full):
    a = A()
    a.raw(struct.pack('<2H', 50, 53))                                # WaitButton, CloseMsg (the two commands the replaced tail started with)
    a.op(294, badge, 0x800C).compare(0x800C, 0).jump('done', 1)
    a.op(128, item, 1, 0x800C).compare(0x800C, 1).jump('done', 1)
    a.msg(m_line)
    a.op(125, item, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    a.op(78, 0x4A1).msg(m_got).op(79)
    a.label('done').raw(struct.pack('<2H', 97, 2))
    a.label('full').msg(m_full).raw(struct.pack('<2H', 97, 2))
    return a.build(base)


def patch_gift(rom, name, map_id, actor, badge, item, number):
    e = ExtEdit(rom, map_id) if map_id >= ext.NATIVE_COUNT else MapEdit(rom, map_id)
    sid = struct.unpack_from('<H', e.groups[1][actor], 10)[0]
    m_line, m_got, m_full = e.message(LINE), e.message('{PLAYER} received HM%02d!' % number), e.message(FULL)
    size = len(helper(0, badge, item, m_line, m_got, m_full))
    ids, addrs, _ = install(e, [size])
    code = helper(addrs[0], badge, item, m_line, m_got, m_full)
    assert len(code) == size
    bank = bytearray(e.bank)
    bank[addrs[0]:addrs[0] + size] = code
    st = bank_starts(bytes(bank))
    begin = st[sid - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    sites, p = [], bytes(bank).find(TAIL, begin, end)
    while p >= 0:
        sites.append(p)
        p = bytes(bank).find(TAIL, p + 1, end)
    assert sites, (name, begin, end)
    for p in sites:
        bank[p:p + 8] = struct.pack('<Hi', 22, addrs[0] - (p + 6)) + b'\0\0'
    e.bank = bytes(bank)
    e.save()
    return dict(map=map_id, script=sid, helper=ids[0], tails=sites, item=item)


def patch(rom):
    report = {'badges': patch_badges(rom)}
    for name, map_id, actor, badge, item, number in GIFTS:
        report[name] = patch_gift(rom, name, map_id, actor, badge, item, number)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
