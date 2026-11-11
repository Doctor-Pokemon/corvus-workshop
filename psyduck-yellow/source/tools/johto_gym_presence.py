"""Prototype 0216: a Johto gym leader stays in his gym until the player holds his badge (owner report 2026-11-10: Morty was nowhere to be found).
Cause (hg_dis.py on ROM 0215): five Johto gyms (Azalea 180, Goldenrod 137, Olivine 138, Ecruteak 80, Mahogany 140) and their city maps run an on-load script that first asks "is the Hall of Fame flag 0x964 set?".
Clear: the leader is always in the gym (story mode). Set: HeartGold's postgame schedule: the leader is in the gym only on some weekdays (and depending on a registered phone number) and shows up in the city outside on the others.
This campaign sets 0x964 in Kanto, so Johto starts in the schedule mode and a leader can be missing on the day the player arrives (Morty hides on weekdays 1 and 2 without his number; today is a Tuesday).
Fix: in each of those on-load scripts the 11-byte "CheckFlag 0x964; GoToIf" is replaced by a jump to a small block: badge of THIS leader missing -> take the story-mode branch (the gym leader visible, the one in the city hidden); badge held -> the original test, so the weekday schedule resumes after the player has beaten the leader.
Not touched: Violet, Cianwood gym, Blackthorn (no schedule in their banks), everything else that checks 0x964. 0219 adds the last two city copies: Pryce (Mahogany, map 88) and Chuck (Cianwood, map 151).
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_gym_presence.py <in.nds> <out.nds> [new]   ('new' = only the two 0219 city copies, for a ROM that already has 0216)"""
import struct
import sys
import ndspy.rom
from johto_step3d import install, write_scripts
from johto_step3d import starts as bank_starts
from johto_step3e import A
from map_edit import MapEdit

HOF = 0x964
# (name, map, script number of the on-load script in that map's bank, badge, what the site is)
SITES = [
    ('Morty gym', 80, 1, 3), ('Morty city', 6, 1, 3),
    ('Bugsy gym', 180, 17, 1), ('Bugsy city', 96, 26, 1),
    ('Whitney gym', 137, 5, 2), ('Whitney city', 196, 7, 2),
    ('Jasmine gym', 138, 8, 5), ('Jasmine city', 231, 5, 5),
    ('Pryce gym', 140, 2, 6),
]
# 0219: the last two city copies, patched on top of 0216 (run with the argument 'new')
SITES_0219 = [
    ('Pryce city', 88, 1, 6),      # map 88 actor 20 (sprite 358, hide flag 0x2CC)
    ('Chuck city', 151, 1, 4),     # map 151 actor 12 (sprite 356, hide flag 0x304); Chuck's gym (139) has no schedule
]


def block(base, badge, pre, orig_target, cond, after):
    a = A()
    a.op(294, badge, 0x800C).compare(0x800C, 0).jump(('abs', pre), 1)
    a.check_flag(HOF).jump(('abs', orig_target), cond).jump(('abs', after))
    return a.build(base)


def patch_one(rom, name, map_id, script, badge):
    e = MapEdit(rom, map_id)
    probe = len(block(0, badge, 0, 0, 0, 0))
    ids, addrs, _ = install(e, [probe])
    st = bank_starts(e.bank)
    begin = st[script - 1]
    end = min([s for s in st if s > begin] + [len(e.bank)])
    bank = bytes(e.bank)
    pat = struct.pack('<2H', 32, HOF)
    site = bank.find(pat, begin, end)
    while site >= 0 and bank[site + 4:site + 6] != struct.pack('<H', 28):
        site = bank.find(pat, site + 1, end)
    assert site >= 0, (name, 'no "CheckFlag 0x964; GoToIf" in the on-load script')
    cond = bank[site + 6]
    assert cond in (0, 1), (name, cond)
    orig_target = site + 11 + struct.unpack_from('<i', bank, site + 7)[0]
    pre = orig_target if cond == 0 else site + 11              # GoToIf 0 jumps when the flag is clear, GoToIf 1 when it is set (then the fall-through is the story branch)
    code = block(addrs[0], badge, pre, orig_target, cond, site + 11)
    assert len(code) == probe
    write_scripts(e, addrs, [code])
    new = bytearray(e.bank)
    new[site:site + 6] = struct.pack('<Hi', 22, addrs[0] - (site + 6))
    e.bank = bytes(new)
    e.save()
    return dict(map=map_id, site=site, cond=cond, story_branch=pre, block=ids[0])


def patch(rom, sites=None):
    return {name: patch_one(rom, name, m, s, b) for name, m, s, b in (SITES if sites is None else sites)}


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    for k, v in patch(rom, SITES_0219 if sys.argv[3:] == ['new'] else None).items():
        print(k, v)
    rom.saveToFile(sys.argv[2])
