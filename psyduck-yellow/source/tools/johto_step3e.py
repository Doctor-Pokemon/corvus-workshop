"""Prototype 0209: after Mr. Pokemon, HeartGold's own Silver / police sequence runs (owner report 2026-11-09: after Oak, the National Pokedex and the first Mega Stone, going back to New Bark Town changed nothing; in HeartGold Elm calls, Silver is met and named, and Elm's lab has a police officer because one of the starters was stolen).
Cause (read with tools/hg_dis.py from pret's opcode table): HeartGold's first-visit scene in Mr. Pokemon's house (script 2, frame row 0x4107 == 0) ends by setting the native story state: SetSpawn 2, flags 0x195/0x316/0x190 set, 0x315/0x19c/0x19d cleared, 0x4073 = 3 (Cherrygrove: Silver's trigger, script 4, trainers 495/496/497 by starter), 0x4108 = 3 (Elm's lab: the police scene with the rival naming screen, then 0x4108 = 4), 0x408c = 2. Our step-3 flow sets 0x4107 = 1 (so the native scene never runs) and replaces it with our Oak and Mega Stone scenes, so none of that state was ever set. Also never set: the "starter chosen" record the native device writes (SetStarterChoice, flag 0x6a), which the Silver battle script reads (GetStarterChoice) to pick his team, and the Mystery Egg (item 0x1e4) that the lab scene takes back.
Fix: one subroutine S appended to Mr. Pokemon's script bank: HeartGold's own lines 2-5 of the house's text (the Mystery Egg speech and rest), the Mystery Egg gift (CallStd 0x7f1 like the native scene), a party heal, then the native end state above plus SetStarterChoice from our choice variable (0x413c: 1/2/3 = Chikorita/Cyndaquil/Totodile = 152/155/158) and flag 0x6a.
 - Mr. Pokemon's talk script (6 and 7 in the bank): where it sets 0x4128 = 9 after the Mega Stone, it now calls S first (a 6-byte jump to a small block: 0x4128 = 9, call S, release, end).
 - Catch-up for a save that already has the stone (0x4128 >= 9) but not the native state (0x4108 == 2): the script's "already done" branch first calls S, then says its usual line. Talking to Mr. Pokemon once more starts the sequence.
Nothing in the save layout changes; no frame rows are added.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step3e.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from johto_step3d import Asm, install, write_scripts

MR_POKEMON = 143
POSTGAME, CHOICE, LAB_STORY = 0x4128, 0x413C, 0x4108
EGG_ITEM = 0x1E4
STARTERS = (152, 155, 158)


class A(Asm):
    def call(self, target):
        self.raw(struct.pack('<H', 26))
        self.fix.append((len(self.code), target))
        return self.raw(b'\0\0\0\0')

    def ret(self):
        return self.raw(struct.pack('<H', 27))

    def op(self, code, *args):
        return self.raw(struct.pack('<H', code) + b''.join(struct.pack('<H', a) for a in args))

    def msg(self, index):
        return self.raw(struct.pack('<HB', 45, index) + struct.pack('<H', 50) + struct.pack('<H', 53))

    def setf(self, flag):
        return self.op(30, flag)


def subroutine():
    a = A()
    a.msg(2)
    a.set_var(0x8004, EGG_ITEM).set_var(0x8005, 1).op(20, 0x7F1)            # CallStd 0x7f1: "received the Mystery Egg"
    a.msg(3).msg(4)
    a.op(174, 6, 1, 0, 0).op(175).op(81, 0).op(78, 0x49F).op(79).op(282).op(174, 6, 1, 1, 0).op(175).op(82)   # fade, fanfare, HealParty, fade back
    a.msg(5)
    # the native end state of the first-visit scene
    a.set_var(0x4107, 1).op(280, 2)
    a.setf(0x195).setf(0x316).clear_flag(0x315).setf(0x190)
    a.set_var(0x4073, 3).clear_flag(0x19C).set_var(LAB_STORY, 3).clear_flag(0x19D).set_var(0x408C, 2)
    # what the native device records when the starter is taken
    for k, species in enumerate(STARTERS):
        a.compare(CHOICE, k + 1).jump('n%d' % k, 5)
        a.op(131, species).jump('done')
        a.label('n%d' % k)
    a.label('done').setf(0x6A)
    return a.ret()


def patch(rom):
    e = MapEdit(rom, MR_POKEMON)
    probe = subroutine()
    s_len = len(probe.build(0))
    r_len = len(A().set_var(POSTGAME, 9).call(('abs', 0)).raw(struct.pack('<H', 97)).end().build(0))
    c_len = len(A().compare(LAB_STORY, 2).jump(('abs', 0), 5).call(('abs', 0)).jump(('abs', 0)).build(0))
    seq = struct.pack('<3H', 41, POSTGAME, 9) + struct.pack('<2H', 97, 2)
    hits = [i for i in range(len(e.bank)) if e.bank[i:i + len(seq)] == seq]
    gt = struct.pack('<HBi', 28, 2, 17)                                       # GoToIf GT +17: "already done" branch of the talk scripts
    gts = [i for i in range(len(e.bank)) if e.bank[i:i + 7] == gt]
    assert len(hits) == 2 and len(gts) == 2, (hits, gts)
    ids, addrs, new_starts = install(e, [s_len, r_len, c_len, c_len])
    # addresses moved by the header growth: look the sites up again in the grown bank
    hits = [i for i in range(len(e.bank)) if e.bank[i:i + len(seq)] == seq]
    gts = [i for i in range(len(e.bank)) if e.bank[i:i + 7] == gt]
    assert len(hits) == 2 and len(gts) == 2, (hits, gts)
    s_at, r_at, c6_at, c7_at = addrs
    s = subroutine().build(s_at)
    r = A().set_var(POSTGAME, 9).call(('abs', s_at)).raw(struct.pack('<H', 97)).end().build(r_at)
    cs = []
    for c_at, g in zip((c6_at, c7_at), gts):
        orig = g + 7 + 17
        cs.append(A().compare(LAB_STORY, 2).jump(('abs', orig), 5).call(('abs', s_at)).jump(('abs', orig)).build(c_at))
    assert (len(s), len(r), len(cs[0]), len(cs[1])) == (s_len, r_len, c_len, c_len)
    write_scripts(e, [s_at, r_at, c6_at, c7_at], [s, r, cs[0], cs[1]])
    bank = bytearray(e.bank)
    for h in hits:                                                         # SetVar 0x4128,9 (6 bytes) -> jump to R (which also releases and ends)
        bank[h:h + 6] = struct.pack('<Hi', 22, r_at - (h + 6))
    for c_at, g in zip((c6_at, c7_at), gts):                              # the GoToIf GT branch now goes to the catch-up block first
        struct.pack_into('<i', bank, g + 3, c_at - (g + 7))
    e.bank = bytes(bank)
    e.save()
    return dict(subroutine=ids[0], stone_tail=ids[1], catch_up=ids[2:], sizes=(s_len, r_len, c_len))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
