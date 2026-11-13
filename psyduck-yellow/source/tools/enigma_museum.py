"""ROM 0278: the Pewter Museum's Enigma Stone scene (Steven Stone gives the SOUL DEW) restored (owner order 2026-11-13: "Restore the Steven chain inside Yellow's rebuilt Pewter", plan items 91-93).
HeartGold's museum (map 471, vanilla script bank 755) had: Steven "before the Latis" (actor 6, hide flag 0x308), an OnTransition start-up script that decides who is visible from variable 0x4083 / the Enigma Stone,
a trigger at (25, 6) that runs the scene when 0x4083 == 1 (Steven + the museum assistant, takes the ENIGMA STONE, gives the SOUL DEW, 0x4083 = 2, Steven leaves), and an OnResume script that puts Steven in place.
The Yellow rebuild removed all of it (ROM 0276 put back only the standard stage-5 Steven, flag 0x317). This tool puts the Enigma Stone side back into Yellow's museum bank (HeartGold's own bytes, copied):
 - the scene (vanilla script 17, 545 bytes with its movement blocks) and the OnResume script (vanilla script 19): copied byte for byte (their jumps are relative; the text indexes 14-19 and 21 are re-pointed at copies of HeartGold's own lines in Yellow's museum text bank);
 - a new OnTransition wrapper = the Enigma start-up logic (the Steven part of vanilla script 14, the photographer part is not needed) and then Yellow's own OnTransition script;
 - Steven (vanilla actor 6: sprite 421, flag 0x308, his talk script is HeartGold's empty script), the trigger now runs the new scene, the header gets the OnResume row.
 - ENIGMA GATE (found in the vanilla scripts): the scene only starts when script command 546 (mode 0) is true: variable 0x4043 must equal 0x06F2 (the value the retail Mystery Gift writes together with the stone). The Route 47 Hiker now writes it when he gives the stone.
Nothing needs a new flag or variable (0x4043 and 0x4083 are HeartGold's own, only used by these scenes).
Usage (from yellow-heartgold, PYTHONPATH=tools): enigma_museum.py <in.nds> <out.nds> <vanilla HeartGold.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from johto_step3d import starts
from johto_step3e import A
from map_edit import MapEdit
from opening import events_decode
from prototype import decode_messages
import enigma_hiker

MUSEUM, HIKER_MAP = 471, 151
VANILLA_BANK, VANILLA_TEXT, VANILLA_EVENT = 755, 464, 424
SCENE_ID, RESUME_ID, STEVEN_ACTOR = 17, 19, 6
STEVEN_BEFORE, STEVEN_AFTER, PEWTER_VAR = 0x308, 0x317, 0x4083
AUTH_VAR, AUTH_VALUE = 0x4043, 0x06F2
TEXT_ROWS = (14, 15, 16, 17, 18, 19, 21)


def align(n):
    return (n + 3) & ~3


def append_blob(bank, size, count_new):
    """Grow the header by count_new entries and append a zero blob of `size` bytes; returns (bank, base address of the blob, header entry index of the first new entry)."""
    count = next(i for i in range(400) if struct.unpack_from('<H', bank, 4 * i)[0] == 0xFD13)
    st = [i * 4 + 4 + struct.unpack_from('<I', bank, 4 * i)[0] for i in range(count)]
    old_header = min(st)
    out = bytearray(old_header + 4 * count_new) + bytearray(bank[old_header:])
    for i, at in enumerate(st):
        struct.pack_into('<I', out, i * 4, at + 4 * count_new - i * 4 - 4)
    base = align(len(out))
    out.extend(bytes(base - len(out)))
    out.extend(bytes(size))
    struct.pack_into('<H', out, (count + count_new) * 4, 0xFD13)
    return bytes(out), base, count


def set_entries(bank, first, bases):
    out = bytearray(bank)
    for k, at in enumerate(bases):
        struct.pack_into('<I', out, (first + k) * 4, at - (first + k) * 4 - 4)
    return bytes(out)


def start_logic(tail):
    """The Steven part of vanilla script 14: who is in the museum, from 0x4083 and the Enigma Stone (every branch ends in a jump to `tail`)."""
    a = A()
    a.compare(PEWTER_VAR, 5).jump('after', 4)                                   # >= 5
    a.compare(PEWTER_VAR, 4).jump('after', 1)
    a.compare(PEWTER_VAR, 3).jump('both', 1)
    a.compare(PEWTER_VAR, 2).jump('both', 1)
    a.compare(PEWTER_VAR, 1).jump('scene', 1)
    a.op(128, enigma_hiker.ENIGMA_STONE, 1, 0x800C).compare(0x800C, 0).jump('hide', 1)     # no stone: nothing to show
    a.raw(struct.pack('<H', 546) + bytes([0]) + struct.pack('<H', 0x800C)).compare(0x800C, 0).jump('hide', 1)   # the Mystery Gift check (0x4043 == 0x06F2)
    a.set_var(PEWTER_VAR, 1)
    a.label('scene').clear_flag(STEVEN_BEFORE).setf(STEVEN_AFTER).jump(tail)
    a.label('both').setf(STEVEN_BEFORE).setf(STEVEN_AFTER).jump(tail)
    a.label('after').setf(STEVEN_BEFORE).jump(tail)
    a.label('hide').setf(STEVEN_BEFORE).jump(tail)
    return a


def fix_hiker(rom):
    """The Route 47 Hiker also writes the Mystery Gift authenticity variable (0x4043 = 0x06F2) with the stone: install a new helper and re-point his two tails."""
    e = MapEdit(rom, HIKER_MAP)
    st0 = starts(e.bank)
    old_helper_index = len(st0)                                               # the 0277 helper is the last script of the bank
    msg_index = None
    # the owner's line is message 10 of the bank (ROM 0277)
    assert len(e.rows) > 10
    msg_index = 10

    def helper(base):
        a = A()
        a.raw(struct.pack('<2H', enigma_hiker.WAIT, enigma_hiker.CLOSE))
        a.op(128, enigma_hiker.ENIGMA_STONE, 1, 0x800C).compare(0x800C, 0).jump('nostone', 1)
        a.jump('done')
        a.label('nostone').compare(PEWTER_VAR, 0).jump('give', 1)
        a.jump('done')
        a.label('give').msg(msg_index)
        a.set_var(AUTH_VAR, AUTH_VALUE)
        a.set_var(0x8004, enigma_hiker.ENIGMA_STONE).set_var(0x8005, 1).op(20, enigma_hiker.STD_OBTAIN_ITEM)
        a.label('done').op(enigma_hiker.RELEASE).op(enigma_hiker.END)
        return a.build(base)
    bank, base, first = append_blob(e.bank, len(helper(0)), 1)
    bank = set_entries(bank, first, [base])
    code = helper(base)
    bank = bytearray(bank)
    bank[base:base + len(code)] = code
    st = starts(bytes(bank))
    old_helper = st[old_helper_index - 1]
    sid = struct.unpack_from('<H', e.groups[1][4], 10)[0]
    begin = st[sid - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    sites = []
    for p in range(begin, end - 5):
        if struct.unpack_from('<H', bank, p)[0] == 22 and p + 6 + struct.unpack_from('<i', bank, p + 2)[0] == old_helper:
            sites.append(p)
    assert len(sites) == 2, sites
    for p in sites:
        struct.pack_into('<i', bank, p + 2, base - (p + 6))
    e.bank = bytes(bank)
    e.save()
    return dict(map=HIKER_MAP, sites=sites, new_helper=first + 1)


def patch(rom, vanilla_path):
    hiker = fix_hiker(rom)
    vanilla = ndspy.rom.NintendoDSRom.fromFile(vanilla_path)
    vbank = bytes(ndspy.narc.NARC(vanilla.getFileByName('a/0/1/2')).files[VANILLA_BANK])
    vst = starts(vbank)
    order = sorted(set(vst))

    def region(sid):
        s = vst[sid - 1]
        later = [x for x in order if x > s]
        return s, (later[0] if later else len(vbank))
    vtext = ndspy.narc.NARC(vanilla.getFileByName('a/0/2/7'))
    _, vrows = decode_messages(vtext.files[VANILLA_TEXT])
    vevents = ndspy.narc.NARC(vanilla.getFileByName('a/0/3/2'))
    vactor = bytes(events_decode(bytes(vevents.files[VANILLA_EVENT]))[1][STEVEN_ACTOR])
    vw = struct.unpack('<16H', vactor)
    assert vw[0] == STEVEN_ACTOR and vw[1] == 421 and vw[4] == STEVEN_BEFORE, vw

    e = MapEdit(rom, MUSEUM)
    mapping = {}
    for vi in TEXT_ROWS:
        e.rows.append(list(vrows[vi]))
        mapping[vi] = len(e.rows) - 1
    assert len(e.rows) < 255
    s0, s1 = region(SCENE_ID)
    scene = bytearray(vbank[s0:s1])
    # re-point the scene's NPCMsg operands (op 45, u8 index) with the offsets the disassembler found
    from hg_dis import dis, load_table
    inc = sys.argv[4] if len(sys.argv) > 4 else None
    table = load_table(inc)
    for at, name, args in dis(vbank, vst, table, SCENE_ID):
        if name == 'NPCMsg':
            assert scene[at - s0 + 2] == args[0] and args[0] in mapping, (at, args)
            scene[at - s0 + 2] = mapping[args[0]]
    r0, r1 = region(RESUME_ID)
    resume = bytes(vbank[r0:r1])
    end_script = struct.pack('<H', 2)
    wrapper_size = len(start_logic('t').label('t').build(0)) + 6                # + the jump to Yellow's own OnTransition script
    parts = [('wrapper', wrapper_size, 0), ('scene', len(scene), s0 % 4), ('resume', len(resume), r0 % 4), ('end', len(end_script), 0)]
    offsets, at = {}, 0
    for name, size, rem in parts:                                               # the copies keep their position modulo 4: the movement blocks they contain must stay 4-byte aligned as in HeartGold's file
        at = at + ((rem - at) % 4)
        offsets[name] = at
        at += size
    total = align(at)
    assert offsets['scene'] % 4 == s0 % 4 and offsets['resume'] % 4 == r0 % 4
    header_id = struct.unpack_from('<H', e.d, e.at + 8)[0]
    py_start = starts(e.bank)
    bank, base, first = append_blob(e.bank, total, 4)
    bank = set_entries(bank, first, [base + offsets[n] for n in ('wrapper', 'scene', 'resume', 'end')])
    st = starts(bank)
    # Yellow's own OnTransition script is the one the current header row names
    h = bytearray(e.scripts.files[header_id])
    rows, i = [], 0
    while h[i] != 0:
        rows.append((h[i], struct.unpack_from('<I', h, i + 1)[0]))
        i += 5
    tail = bytes(h[i + 1:])
    transition = next(v for t, v in rows if t == 2)
    yellow_start = st[transition - 1]
    wrapper = start_logic('yellow')
    wrapper.label('yellow').jump(('abs', yellow_start))
    code = wrapper.build(base + offsets['wrapper'])
    assert len(code) == wrapper_size, (len(code), wrapper_size)
    out = bytearray(bank)
    out[base + offsets['wrapper']:base + offsets['wrapper'] + len(code)] = code
    out[base + offsets['scene']:base + offsets['scene'] + len(scene)] = scene
    out[base + offsets['resume']:base + offsets['resume'] + len(resume)] = resume
    out[base + offsets['end']:base + offsets['end'] + 2] = end_script
    e.bank = bytes(out)
    ids = dict(wrapper=first + 1, scene=first + 2, resume=first + 3, end=first + 4)
    # header rows: OnTransition -> wrapper, OnResume -> resume script, frame table kept
    new_rows = [(t, (ids['wrapper'] if t == 2 else v)) for t, v in rows]
    assert all(t != 3 for t, _ in rows)
    new_rows.insert(1, (3, ids['resume']))
    nh = bytearray()
    for t, v in new_rows:
        nh += bytes([t]) + struct.pack('<I', v)
    nh += b'\0' + tail
    e.scripts.files[header_id] = bytes(nh)
    # Steven (vanilla actor 6) with the empty talk script; the trigger runs the new scene
    record = bytearray(vactor)
    struct.pack_into('<H', record, 10, ids['end'])
    assert STEVEN_ACTOR not in [struct.unpack_from('<H', bytes(r), 0)[0] for r in e.groups[1]]
    e.groups[1].append(bytes(record))
    triggers = [k for k, r in enumerate(e.groups[3]) if struct.unpack_from('<H', bytes(r), 14)[0] == PEWTER_VAR]
    assert len(triggers) == 1, triggers
    trig = bytearray(e.groups[3][triggers[0]])
    old_script = struct.unpack_from('<H', trig, 0)[0]
    struct.pack_into('<H', trig, 0, ids['scene'])
    e.groups[3][triggers[0]] = bytes(trig)
    e.save()
    return dict(hiker=hiker, ids=ids, header=header_id, old_trigger_script=old_script, messages=mapping, scene_bytes=len(scene), resume_bytes=len(resume))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, sys.argv[3]))
    rom.saveToFile(sys.argv[2])
