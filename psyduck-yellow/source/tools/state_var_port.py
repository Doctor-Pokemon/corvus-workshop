"""Port of state_var_range.py (ROM 0186) onto ANY build (owner order 2026-11-08: the owner's current 0-1-6-10 branch never got the 0186 fix).
Moves the six story-state variables that lie beyond the save's 368 work variables (0x4000-0x416F) into six variables found unused:
 0x4171->0x401B, 0x4172->0x401C, 0x4173->0x401D, 0x4174->0x401E, 0x4176->0x401F, 0x4177->0x4022 (Pokemon Tower scene states 1-3, Rocket Hideout state, Silph Co. state (2), Route 22 rival state).
NOTE (2026-11-08): ROM 0186's block 0x4038-0x403D was NOT all free: the owner's save holds 0xD921 in 0x403C and the engine code (ARM9/overlays) contains 0x4038, 0x403C and 0x403D as 32-bit constants. The six above were chosen by audit: no occurrence in any script bank or trigger row, no 32-bit constant in ARM9/overlays, value 0 in the owner's save.
Same method as 0186: every `SetVar(old, 1)` byte pattern in the script banks and every trigger row whose variable field is `old` is rewritten; nothing else is touched. Unlike 0186 it does not pin the input ROM: instead it asserts, from the ROM itself,
 (1) the counts of those uses equal the ones measured for 0186 (2/1/2/3/4/1 SetVars, 1/1/2/3/3/1 trigger rows), so no other kind of use exists, (2) no other occurrence of an old id's two bytes is left afterwards, (3) the target variables have NO occurrence at all (scripts, triggers or engine-code constants) before the patch.
Only the script and event NARCs change. Usage (from yellow-heartgold, PYTHONPATH=tools): state_var_port.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode

MAPPING = {0x4171: 0x401B, 0x4172: 0x401C, 0x4173: 0x401D, 0x4174: 0x401E, 0x4176: 0x401F, 0x4177: 0x4022}
EXPECTED_SETVAR = {0x4171: 2, 0x4172: 1, 0x4173: 2, 0x4174: 3, 0x4176: 4, 0x4177: 1}
EXPECTED_TRIGGER = {0x4171: 1, 0x4172: 1, 0x4173: 2, 0x4174: 3, 0x4176: 3, 0x4177: 1}


def trigger_rows(events, var):
    n = 0
    for raw in events.files:
        if not raw:
            continue
        try:
            groups = events_decode(bytes(raw))
        except Exception:
            continue
        n += sum(1 for grp in groups for row in grp if len(row) >= 16 and struct.unpack_from('<H', row, 14)[0] == var)
    return n


def patch(rom):
    code = bytes(rom.loadArm9().sections[0].data) + b''.join(bytes(o.data) for o in rom.loadArm9Overlays().values())
    for new in MAPPING.values():
        assert code.count(struct.pack('<I', new)) == 0, f'{new:#06x} appears as a constant in the engine code'
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    events = ndspy.narc.NARC(rom.getFileByName('a/0/3/2'))
    for new in MAPPING.values():                                   # the target block must be completely unused
        assert sum(bytes(b).count(struct.pack('<H', new)) for b in scripts.files) == 0, f'{new:#06x} already appears in a script'
        assert trigger_rows(events, new) == 0, f'{new:#06x} is already a trigger variable'
    report = {}
    for old, new in MAPPING.items():
        o, n = struct.pack('<3H', 41, old, 1), struct.pack('<3H', 41, new, 1)
        total = 0
        for i, bank in enumerate(scripts.files):
            body = bytes(bank)
            hit = body.count(o)
            if hit:
                scripts.files[i] = body.replace(o, n)
                total += hit
        assert total == EXPECTED_SETVAR[old], f'SetVar {old:#06x}: {total}'
        rows = 0
        for i, raw in enumerate(events.files):
            if not raw:
                continue
            try:
                groups = events_decode(bytes(raw))
            except Exception:
                continue
            changed = False
            for grp in groups:
                for k, row in enumerate(grp):
                    if len(row) >= 16 and struct.unpack_from('<H', row, 14)[0] == old:
                        r = bytearray(row)
                        struct.pack_into('<H', r, 14, new)
                        grp[k] = bytes(r)
                        rows += 1
                        changed = True
            if changed:
                assert events_encode(events_decode(bytes(raw))) == bytes(raw), ('event file does not round-trip', i)
                events.files[i] = events_encode(groups)
        assert rows == EXPECTED_TRIGGER[old], f'trigger {old:#06x}: {rows}'
        report[hex(old)] = dict(to=hex(new), setvar=total, triggers=rows)
    for old in MAPPING:
        assert sum(bytes(b).count(struct.pack('<H', old)) for b in scripts.files) == 0, f'{old:#06x} still appears in scripts'
        assert trigger_rows(events, old) == 0, f'{old:#06x} still in a trigger'
    rom.setFileByName('a/0/1/2', scripts.save())
    rom.setFileByName('a/0/3/2', events.save())
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    for k, v in patch(rom).items():
        print(k, v)
    rom.saveToFile(sys.argv[2])
