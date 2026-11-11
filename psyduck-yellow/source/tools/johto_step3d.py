"""Prototype 0207: Elm's lab no longer traps the player after our starter menu, the native "take one from the device" intro no longer runs, and the 0206 bedroom FREEZE is removed.
Reports (owner, real 3DS, 2026-11-09): (a) the native lab intro sent the player to a "device" that only says two valuable Pokemon are left; (b) after Elm's menu gave the starter and the Mega Ring, Elm still refused to let the player leave ("the Poke Balls are in that device").
Cause (emulator): the lab (map 61) keeps HeartGold's trigger rows on the native lab story variable 0x4108: value 0 at z10 = script 12 (the intro and the "where are you going" blocker), value 1 at z11 = script 4 (the assistant who hands out Potions when you leave). Taking a starter from the native device sets 0x4108 = 1 (and 0x4072 = 1, clears flag 0x160); our menu (Elm's talk script 17, johto_step3.py) never did, so the player stayed at 0 for ever.
Fix (all one-shot, nothing the engine re-runs every frame):
 LAB: (1) Elm's menu, on the give path, now does what the device does: 0x4108 = 1, 0x4072 = 1, clear 0x160, then the old 0x4128 = 7 and 0x4107 = 1 (the 6-byte SetVar 0x4128,7 inside script 17 is replaced by a jump to an appended block; nothing else in script 17 moves).
      (2) the z10 trigger (script 12) now runs a small new script first: postgame variable 0x4128 == 6 -> run OUR Elm script (starter menu) instead of the native intro; 0x4128 > 6 -> set the same state a native pick would have set (0x4108 = 1, 0x4072 = 1, clear 0x160) and end (this releases a save that already has its starter and is stuck at 0x4108 = 0); 0x4128 < 6 -> the native script 12 as before.
 BEDROOM (map 506): 0206's starter was a level-script FRAME row on variable 0x4128 == 0 whose script did nothing when the Hall of Fame flag was not set: the engine re-runs a frame row every frame while its variable matches, and the player cannot move while that happens (measured: a player on 0206 cannot walk in the bedroom, so a new game could not leave its first room). That row is removed. The chain start moves into the map's own one-shot level scripts: the map-entry row (type 2, script 3) and the on-load row (type 3, script 4) now point at two new scripts that do "if flag 0x964 and 0x4128 == 0 then 0x4128 = 1" and then jump into the original script, which is unchanged.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step3d.py <in.nds> <out.nds>   (in = the 0206 ROM)"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit

BEDROOM, ELM_LAB = 506, 61
POSTGAME, LAB_STORY, LAB_DEVICE, DEVICE_FLAG, NATIVE_FIRST_VISIT, GAME_CLEAR = 0x4128, 0x4108, 0x4072, 0x160, 0x4107, 0x964
INTRO_SCRIPT, ELM_SCRIPT = 12, 17


def starts(bank):
    count = next(i for i in range(400) if struct.unpack_from('<H', bank, 4 * i)[0] == 0xFD13)
    return [struct.unpack_from('<I', bank, 4 * i)[0] + 4 * i + 4 for i in range(count)]


class Asm:
    """Tiny assembler for the few script commands used here; jumps are relative to the end of the instruction."""
    def __init__(self):
        self.code, self.fix, self.labels = bytearray(), [], {}

    def raw(self, b):
        self.code += b
        return self

    def set_var(self, var, val):
        return self.raw(struct.pack('<4H', 41, var, val, 0)[:6])

    def clear_flag(self, flag):
        return self.raw(struct.pack('<2H', 31, flag))

    def check_flag(self, flag):
        return self.raw(struct.pack('<2H', 32, flag))

    def compare(self, var, val):
        return self.raw(struct.pack('<3H', 17, var, val))

    def end(self):
        return self.raw(struct.pack('<H', 2))

    def jump(self, target, cond=None):
        """cond None = always (op 22); else op 28 with cond (0 <, 1 =, 2 >, 5 !=). target = label name or ('abs', address)."""
        self.raw(struct.pack('<H', 22) if cond is None else struct.pack('<HB', 28, cond))
        self.fix.append((len(self.code), target))
        return self.raw(b'\0\0\0\0')

    def label(self, name):
        self.labels[name] = len(self.code)
        return self

    def build(self, base):
        out = bytearray(self.code)
        for at, target in self.fix:
            dest = target[1] if isinstance(target, tuple) else base + self.labels[target]
            struct.pack_into('<i', out, at, dest - (base + at + 4))
        return bytes(out)


def install(e, specs):
    """specs: list of (placeholder size). Appends that many scripts; returns (ids, addresses in the NEW bank)."""
    ids = [e.script(lambda add, n=n: bytes(n)) for n in specs]
    bank_starts = starts(e.bank)
    return ids, [bank_starts[i - 1] for i in ids], bank_starts


def write_scripts(e, addrs, scripts):
    bank = bytearray(e.bank)
    for at, code in zip(addrs, scripts):
        assert bytes(bank[at:at + len(code)]) == bytes(len(code)), 'placeholder was not empty'
        bank[at:at + len(code)] = code
    e.bank = bytes(bank)


def header_rows(h):
    i = 0
    while h[i] != 0:
        i += 5
    return i


def patch_bedroom(rom):
    e = MapEdit(rom, BEDROOM)
    hid = struct.unpack_from('<H', e.d, e.at + 8)[0]
    h = bytearray(e.scripts.files[hid])
    i = header_rows(h)
    rows = {h[j]: (j, struct.unpack_from('<I', h, j + 1)[0]) for j in range(0, i, 5)}
    assert set(rows) == {1, 2, 3} and rows[2][1] == 3 and rows[3][1] == 4, rows
    # the 0206 frame row (0x4128 == 0 -> script 8) goes
    frame = i + 1
    assert struct.unpack_from('<3H', h, frame) == (POSTGAME, 0, 8), h.hex(' ')
    del h[frame:frame + 6]
    size = 42
    ids, addrs, new_starts = install(e, [size, size])
    report = {}
    for (typ, orig), new_id, addr in zip(((2, 3), (3, 4)), ids, addrs):
        a = Asm()
        a.check_flag(GAME_CLEAR).jump('go', 1)
        a.jump(('abs', new_starts[orig - 1]))
        a.label('go').compare(POSTGAME, 0).jump(('abs', new_starts[orig - 1]), 5)
        a.set_var(POSTGAME, 1).jump(('abs', new_starts[orig - 1]))
        code = a.build(addr)
        assert len(code) == size, len(code)
        write_scripts(e, [addr], [code])
        struct.pack_into('<I', h, rows[typ][0] + 1, new_id)
        report[f'type{typ}'] = new_id
    e.scripts.files[hid] = bytes(h)
    e.save()
    return report


def patch_lab(rom):
    e = MapEdit(rom, ELM_LAB)
    seq = struct.pack('<6H', 41, POSTGAME, 7, 41, NATIVE_FIRST_VISIT, 1)
    assert e.bank.count(seq) == 1, 'Elm give path not found exactly once'
    ids, (p_at, q_at), new_starts = install(e, [50, 32])
    p_id, q_id = ids
    elm_start, intro_start = new_starts[ELM_SCRIPT - 1], new_starts[INTRO_SCRIPT - 1]
    q = Asm().set_var(LAB_STORY, 1).set_var(LAB_DEVICE, 1).clear_flag(DEVICE_FLAG).set_var(POSTGAME, 7).set_var(NATIVE_FIRST_VISIT, 1).raw(struct.pack('<H', 97)).end()   # ReleaseAll + End, as the original tail
    q = q.build(q_at)
    assert len(q) == 32, len(q)
    p = Asm()
    p.compare(POSTGAME, 6).jump('native', 0).jump('given', 2).jump(('abs', elm_start))
    p.label('given').set_var(LAB_STORY, 1).set_var(LAB_DEVICE, 1).clear_flag(DEVICE_FLAG).end()
    p.label('native').jump(('abs', intro_start))
    p = p.build(p_at)
    assert len(p) == 50, len(p)
    write_scripts(e, [p_at, q_at], [p, q])
    # Elm's give path: SetVar 0x4128,7 (6 bytes) -> jump to Q (which does the whole tail)
    bank = bytearray(e.bank)
    at = bytes(bank).find(seq)
    bank[at:at + 6] = struct.pack('<Hi', 22, q_at - (at + 6))
    e.bank = bytes(bank)
    # the z10 trigger (native intro / blocker) runs P first
    hit = [k for k, t in enumerate(e.groups[3]) if len(t) >= 16 and struct.unpack_from('<H', t, 0)[0] == INTRO_SCRIPT and struct.unpack_from('<H', t, 14)[0] == LAB_STORY and struct.unpack_from('<H', t, 12)[0] == 0]
    assert len(hit) == 1, hit
    row = bytearray(e.groups[3][hit[0]])
    struct.pack_into('<H', row, 0, p_id)
    e.groups[3][hit[0]] = bytes(row)
    e.save()
    return dict(entry_script=p_id, give_tail_script=q_id)


def patch(rom):
    return dict(bedroom=patch_bedroom(rom), lab=patch_lab(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
