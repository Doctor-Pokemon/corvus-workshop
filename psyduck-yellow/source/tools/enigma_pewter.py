"""ROM 0279: the outdoor half of Steven Stone's Enigma Stone event restored in Yellow's Pewter City (owner order 2026-11-13: "Restore the Steven chain inside Yellow's rebuilt Pewter"; plan items 91-94).
HeartGold's Pewter City (map 51, vanilla script bank 750) ran: an OnTransition start-up script that shows Steven (and Latios in HeartGold / Latias in SoulSilver) from variable 0x4083, a frame-table scene when 0x4083 == 2
(Steven meets the player outside the museum: lines, 0x4083 = 3), an OnResume script that places Steven, an OnLoad script that hides the Lati@s after the battle, Steven's talk script and the Lati@s static battle script (ends in 0x4083 = 4/5, Steven's last lines and, when 0x4130 == 4, shows the museum Steven again).
The Yellow rebuild replaced the bank (1311) and the level-script file (1051: only an OnTransition row), so none of it could run. The scripts still sit in bank 750 of this ROM (with the earlier tool's scaled battle level: 60 + 5 per Johto badge), unused.
This tool copies bank 750's bytes from the OnResume script to the end of the file (ids 12, 14, 13, the movement blocks they share, 11 and 10; 926 contiguous bytes, copied at the same position modulo 4) into the Yellow bank, with HeartGold's own text rows 6-19 appended to Yellow's Pewter text bank,
a new OnTransition wrapper (the Steven / Lati@s visibility part of vanilla script 8, then Yellow's own OnTransition script), the OnLoad / OnResume / frame-table rows in the level-script file, and the vanilla actors 8 (Steven), 9 (Latios), 10 (Latias) with their hide flags (0x30C, 0x30D, 0x312).
Nothing new is allocated: the flags and variables are HeartGold's own (0x4083, 0x4043 from the Route 47 Hiker's gift).
Usage (from yellow-heartgold, PYTHONPATH=tools): enigma_pewter.py <in.nds> <out.nds> <vanilla HeartGold.nds> <pret script.inc>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from hg_dis import dis, load_table
from johto_step3d import starts
from johto_step3e import A
from map_edit import MapEdit
from opening import events_decode
from prototype import decode_messages
from enigma_museum import append_blob, set_entries

PEWTER, SRC_BANK, VANILLA_TEXT, VANILLA_EVENT = 51, 750, 460, 48
STEVEN_VAR = 0x4083
IDS = dict(resume=12, onload=14, scene=13, battle=11, talk=10)
ACTORS = (8, 9, 10)                       # Steven, Latios, Latias
HIDE = dict(steven=0x30C, latios=0x30D, latias=0x312)
GET_GAME_VERSION = None


def wrapper_logic(get_version_op):
    a = A()
    a.compare(STEVEN_VAR, 4).jump('lati', 1)
    a.compare(STEVEN_VAR, 2).jump('steven', 1)
    a.compare(STEVEN_VAR, 3).jump('steven', 1)
    a.jump('tail')
    a.label('steven').clear_flag(HIDE['steven'])
    # This ROM is HeartGold only (Latios, never Latias): no GetGameVersion here. Writing the work variable 0x800C from an
    # OnTransition script froze every battle started in Pewter afterwards (plan item 95, found 2026-11-13).
    a.label('lati').clear_flag(HIDE['latios'])
    a.label('tail')
    return a


def patch(rom, vanilla_path, inc_path):
    inc = open(inc_path).read()
    import re
    get_version = int(re.search(r'\.macro GetGameVersion[^\n]*\n\s*\.short (\d+)', inc).group(1))
    table = load_table(inc_path)
    src = bytes(ndspy.narc.NARC(rom.getFileByName('a/0/1/2')).files[SRC_BANK])
    sst = starts(src)
    s0 = min(sst[IDS[k] - 1] for k in IDS)
    assert s0 == sst[IDS['resume'] - 1], (s0, sst)
    region = bytearray(src[s0:])
    # re-point the NPCMsg operands (all reachable instructions of the five scripts must lie in the region)
    vanilla = ndspy.rom.NintendoDSRom.fromFile(vanilla_path)
    _, vrows = decode_messages(ndspy.narc.NARC(vanilla.getFileByName('a/0/2/7')).files[VANILLA_TEXT])
    e = MapEdit(rom, PEWTER)
    mapping, sites = {}, []
    for k in IDS:
        for at, name, args in dis(src, sst, table, IDS[k]):
            assert at >= s0, (k, at)
            if name == 'NPCMsg':
                if (at, args[0]) not in sites:
                    sites.append((at, args[0]))
    for _, idx in sites:
        if idx not in mapping:
            e.rows.append(list(vrows[idx]))
            mapping[idx] = len(e.rows) - 1
    assert len(e.rows) < 255
    for at, idx in sites:
        assert region[at - s0 + 2] == idx
        region[at - s0 + 2] = mapping[idx]
    entry = {k: sst[IDS[k] - 1] - s0 for k in IDS}                              # entry offsets inside the region
    hid = struct.unpack_from('<H', e.d, e.at + 8)[0]
    h = bytearray(e.scripts.files[hid])
    rows, i = [], 0
    while h[i] != 0:
        rows.append((h[i], struct.unpack_from('<I', h, i + 1)[0]))
        i += 5
    assert [t for t, _ in rows] == [2] and bytes(h[i + 1:]) == b'', (rows, bytes(h[i:]).hex())
    transition = rows[0][1]
    wsize = len(wrapper_logic(get_version).build(0)) + 6
    # layout: wrapper (any alignment), then the region at the same position modulo 4
    wr_off = 0
    reg_off = wsize + ((s0 - wsize) % 4)
    total = reg_off + len(region)
    bank, base, first = append_blob(e.bank, total, 6)
    offs = [wr_off, reg_off + entry['resume'], reg_off + entry['onload'], reg_off + entry['scene'], reg_off + entry['battle'], reg_off + entry['talk']]
    bank = set_entries(bank, first, [base + o for o in offs])
    st = starts(bank)
    yellow_start = st[transition - 1]
    w = wrapper_logic(get_version)
    w.jump(('abs', yellow_start))
    code = w.build(base + wr_off)
    assert len(code) == wsize
    out = bytearray(bank)
    out[base + wr_off:base + wr_off + len(code)] = code
    out[base + reg_off:base + reg_off + len(region)] = region
    assert (base + reg_off) % 4 == s0 % 4
    e.bank = bytes(out)
    ids = dict(wrapper=first + 1, resume=first + 2, onload=first + 3, scene=first + 4, battle=first + 5, talk=first + 6)
    nh = bytearray()
    for t, v in ((2, ids['wrapper']), (4, ids['onload']), (3, ids['resume']), (1, 1)):
        nh += bytes([t]) + struct.pack('<I', v)
    nh += b'\0' + struct.pack('<3H', STEVEN_VAR, 2, ids['scene']) + b'\0\0'
    e.scripts.files[hid] = bytes(nh)
    # actors: Steven talks (script talk), Latios and Latias run the battle script
    vevents = ndspy.narc.NARC(vanilla.getFileByName('a/0/3/2'))
    vg = events_decode(bytes(vevents.files[VANILLA_EVENT]))
    present = {struct.unpack_from('<H', bytes(r), 0)[0] for r in e.groups[1]}
    for actor, script in zip(ACTORS, (ids['talk'], ids['battle'], ids['battle'])):
        rec = bytearray(vg[1][actor])
        w16 = struct.unpack('<16H', bytes(rec))
        assert w16[0] == actor and actor not in present, (actor, w16)
        struct.pack_into('<H', rec, 10, script)
        e.groups[1].append(bytes(rec))
    e.save()
    return dict(ids=ids, header=hid, messages=mapping, region=(s0, len(region)), text_rows=len(e.rows))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3], sys.argv[4]))
    rom.saveToFile(sys.argv[2])
