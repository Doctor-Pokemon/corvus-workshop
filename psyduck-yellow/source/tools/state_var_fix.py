"""Prototype 0203: the six story-state variables move AGAIN, out of 0x401B-0x401F/0x4022 (owner report 2026-11-08: leaving Silph Co. after Giovanni, BLUE's 7F fight happened a second time).
Cause (measured, emulator, ROM 0202, map 570 = Silph 7F): the ambush trigger tests variable 0x401F (Silph state) == 0 and the script sets it to 1 after the fight, but 0x401F is back at 0 after the next map load. With the trigger pointed at a variable from 0x4093 up instead, the same walk is not interrupted; with
 the variable unset the ambush fires on the first square. Probe tests: one-tile triggers on each of the six targets set to 1 -> walked through all untouched after a map load; with them unset the first one fires. So the engine resets part of the low work-variable range (0x401B-0x401F, 0x4022 included) on map loads; state_var_port.py (0188) never walked its targets in game (its own notes say so).
Same six variables, same SetVar/trigger-row method as state_var_port.py: Tower scene states 1-3, Rocket Hideout state, Silph Co. state, Route 22 rival state:
 0x401B->0x404A, 0x401C->0x4093, 0x401D->0x40C6, 0x401E->0x40E4, 0x401F->0x40F2, 0x4022->0x413F (the only six variables in 0x4040-0x416F with no script use, no trigger row, no engine constant; 0x4109/0x4111/0x4112 look free in scripts but are native trigger variables).
Asserts: SetVar/trigger counts equal the 0188 ones (2/1/2/3/4/1 and 1/1/2/3/3/1), no other occurrence of an old id's two bytes in any script bank, the targets have no occurrence in any script bank, trigger row or 32-bit constant in the ARM9/overlays. Only a/0/1/2 and a/0/3/2 change.
Known side effect for a save that already did one of these scenes: its new variable reads 0 (it never kept the old value anyway), so a trigger that tests only the variable can play its scene once more, then sets it.
Usage (from yellow-heartgold, PYTHONPATH=tools): state_var_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import events_decode, events_encode

MAPPING = {0x401B: 0x404A, 0x401C: 0x4093, 0x401D: 0x40C6, 0x401E: 0x40E4, 0x401F: 0x40F2, 0x4022: 0x413F}
EXPECTED_SETVAR = {0x401B: 2, 0x401C: 1, 0x401D: 2, 0x401E: 3, 0x401F: 4, 0x4022: 1}
EXPECTED_TRIGGER = {0x401B: 1, 0x401C: 1, 0x401D: 2, 0x401E: 3, 0x401F: 3, 0x4022: 1}


def trigger_rows(events, var):
    """Trigger rows (event group 3, variable at byte 14) that test `var`."""
    n = 0
    for raw in events.files:
        if not raw:
            continue
        try:
            groups = events_decode(bytes(raw))
        except Exception:
            continue
        n += sum(1 for row in groups[3] if len(row) >= 16 and struct.unpack_from('<H', row, 14)[0] == var)
    return n


def patch(rom):
    code = bytes(rom.loadArm9().sections[0].data) + b''.join(bytes(o.data) for o in rom.loadArm9Overlays().values())
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    events = ndspy.narc.NARC(rom.getFileByName('a/0/3/2'))
    for new in MAPPING.values():
        assert code.count(struct.pack('<I', new)) == 0, f'{new:#06x} appears as a constant in the engine code'
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
            for k, row in enumerate(groups[3]):
                if len(row) >= 16 and struct.unpack_from('<H', row, 14)[0] == old:
                    r = bytearray(row)
                    struct.pack_into('<H', r, 14, new)
                    groups[3][k] = bytes(r)
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
