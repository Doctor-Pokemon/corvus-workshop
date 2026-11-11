"""Prototype 0232: the FORM TRADER also swaps a Pokemon for its HISUIAN form (owner 2026-11-11: "We forgot about Hisuian forms with the Form Change NPC").
Applies on top of any ROM that has the Form Trader (ROM 0230 and later; the public BETA 0.2.1.0 is the published ROM 0230 plus this tool and nothing else). The 16 Hisuian forms (Growlithe, Arcanine, Voltorb, Electrode, Typhlosion, Qwilfish, Sneasel, Samurott, Lilligant, Zorua, Zoroark, Braviary, Sliggoo, Goodra,
Avalugg, Decidueye) are all "form 1" of their species in the ROM's form table (a/0/2/8 file 11, rows 0x52E-0x53D; Arcanine, Electrode, Lilligant and Avalugg also have a duplicate
"form 2" row that is NOT offered) and have battle sprites like the Alolan control. Moves: data/form-trader-hisui.json = hg-engine data/learnsets/learnsets.json (SPECIES_*_HISUIAN, LevelMoves, identical
pairs dropped, move ids from include/constants/moves.h), the same rule as the first 34 forms. Typhlosion's Hisuian form is form 1; its form 2 slot is untouched.
The existing trader script is not changed except for one GoTo: where it used to say "no form" (the species is not one of the Alolan / Galarian bases) it now jumps into a SECOND script appended
to the same bank, which has the same offer / apply / moves-reset logic for the Hisuian bases and ends in the same "no form" line. The greeting and the "no form" line (existing message rows) are
rewritten in place to name HISUIAN as well. One-way swap, a Pokemon that already has a form is refused earlier by the first script (unchanged).
BUG FIX (found while testing this, in 0230 too): the first trader's MonGetLevel (535) had its two arguments swapped (the command takes the RESULT variable first, then the slot; handler 0x0204D564), so it
overwrote the party-slot variable with the level and read the slot from the level variable: the form changed but TutorMoveTeachInSlot then ran on "slot 30" and no move was ever reset. All 34 old calls (6 bytes each) are
swapped in place here; the 16 new ones are written the right way round.
Usage (from yellow-heartgold, PYTHONPATH=tools): form_trader_hisui.py <in.nds> <out.nds>"""
import json
import struct
import sys
import ndspy.rom
import form_trader as ft
from johto_step3d import install, write_scripts
from johto_step3e import A
from map_edit import MapEdit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages

DATA = ft.DATA.with_name('form-trader-hisui.json')
INTRO = "Hi! I'm the FORM TRADER.\rI swap a POKéMON for its ALOLAN, GALARIAN or HISUIAN form!\rWhich one will you show me?"
NOFORM = "Sorry, that one has no ALOLAN, GALARIAN or HISUIAN form."
SLOT, SPECIES, FORM, LEVEL, YN = ft.SLOT, ft.SPECIES, ft.FORM, ft.LEVEL, ft.YN


def row_of(e, line):
    words = decode_messages(encode_text([line], PH))[1][0]
    hits = [i for i, r in enumerate(e.rows) if list(r) == list(words)]
    assert len(hits) == 1, (line, hits)
    return hits[0]


def build(forms, offer, done, decline, noform):
    a = A()
    bases = [f['base'] for f in forms]
    assert len(set(bases)) == len(bases)
    for b in bases:
        a.compare(SPECIES, b).jump('offer%d' % b, 1)
    a.jump('noform')
    for i, f in enumerate(forms):
        a.label('offer%d' % f['base'])
        a.raw(struct.pack('<HBH', 199, 1, SLOT))                                                   # BufferPartyMonNick 1, slot
        a.raw(struct.pack('<HB', 45, offer[i])).op(63, YN).raw(struct.pack('<H', 53))
        a.compare(YN, 0).jump('apply%d' % i, 1)
        a.jump('decline')
    for i, f in enumerate(forms):
        a.label('apply%d' % i)
        a.op(659, SLOT, f['form']).op(535, LEVEL, SLOT)                                          # SetMonForm slot form; MonGetLevel result-var, slot
        for s in range(4):
            a.op(654, SLOT, s, 0)                                                                 # clear the four move slots
        last = None
        for j, (lv, mv) in enumerate(f['moves']):
            if lv > 1 and lv != last:
                a.compare(LEVEL, lv).jump('moves%d' % i, 0)
            last = lv
            a.op(654, SLOT, j % 4, mv)
        a.label('moves%d' % i)
        a.op(78, 0x4A1).msg(done[i]).op(79).jump('end')
    a.label('decline').msg(decline).jump('end')
    a.label('noform').msg(noform).jump('end')
    a.label('end').op(97).end()
    return a


def patch(rom):
    forms = json.loads(DATA.read_text())
    assert len(forms) == 16 and all(f['form'] == 1 and f['region'] == 'HISUIAN' for f in forms)
    e = MapEdit(rom, ft.MAP)
    old_intro, old_noform, decline = row_of(e, ft.TEXT['intro']), row_of(e, ft.TEXT['noform']), row_of(e, ft.TEXT['decline'])
    new = {k: decode_messages(encode_text([v], PH))[1][0] for k, v in (('intro', INTRO), ('noform', NOFORM))}
    e.rows[old_intro], e.rows[old_noform] = new['intro'], new['noform']
    offer = [e.message(f"Swap {{RIVAL}} for {ft.article(f['region'])} {ft.name(f)}?\rIts moves will be reset to its new form's!") for f in forms]
    done = [e.message(f"Done! It's now {ft.article(f['region'])} {ft.name(f)}!\rIts moves match its new form.") for f in forms]
    size = len(build(forms, offer, done, decline, old_noform).build(0))
    old_code = struct.pack('<HB', 45, old_noform) + struct.pack('<HH', 50, 53)                    # the old script's "no form" label: NPCMsg, WaitButton, CloseMsg
    ids, addrs, _ = install(e, [size])                                                           # the bank header grows: look the sites up afterwards
    label = e.bank.find(old_code)
    assert label >= 0 and e.bank.find(old_code, label + 1) < 0, 'old no-form code not unique'
    sites = [a for a in range(len(e.bank) - 6) if e.bank[a:a + 2] == b'\x16\x00' and a + 6 + struct.unpack_from('<i', e.bank, a + 2)[0] == label]
    assert len(sites) == 1, sites
    bad = struct.pack('<3H', 535, SLOT, LEVEL)                                                    # MonGetLevel with the arguments swapped (the old script, 34 forms)
    fixed = struct.pack('<3H', 535, LEVEL, SLOT)
    assert e.bank.count(bad) == 34 and e.bank.count(fixed) == 0, (e.bank.count(bad), e.bank.count(fixed))
    bank = bytearray(e.bank.replace(bad, fixed))
    e.bank = bytes(bank)
    code = build(forms, offer, done, decline, old_noform).build(addrs[0])
    assert len(code) == size
    write_scripts(e, addrs, [code])
    bank = bytearray(e.bank)
    struct.pack_into('<Hi', bank, sites[0], 22, addrs[0] - (sites[0] + 6))
    e.bank = bytes(bank)
    e.save()
    return dict(map=ft.MAP, new_script=ids[0], script_bytes=size, forms=len(forms), messages=len(e.rows), site=sites[0], bank_bytes=len(e.bank))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
