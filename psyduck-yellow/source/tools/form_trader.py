"""Prototype 0230: the FORM TRADER, an NPC in the Johto Safari Zone Gate (map 173) who swaps a Pokemon for its Alolan / Galarian form (owner 2026-11-10, plan items 32/36).
Rules (owner): any Alolan or Galarian form (34 forms of 33 species; the legendary Galarian birds, the totem forms and Darmanitan's Zen mode are left out); the Pokemon's stats and ability follow the new form (tools/form_recalc.py, the SetMonForm handler);
its MOVES are reset to what the new form would know at its level (owner chose "B"): the four moves are written by script from the form's own level-up learnset (data/form-trader.json: hg-engine data/learnsets/learnsets.json, duplicates dropped, move ids from hg-engine's moves.h).
One-way swap, normal form -> regional form (a Pokemon that already has a form is refused): that keeps the script bank at about 14 KB (the largest bank in the ROM is 16 KB); a way back would double it.
Script (local script, NPC at (13,10) facing west): LockAll, FacePlayer, greeting, PartySelectUI (349; it waits for the menu itself), GetPartySelection (351), RestoreOverworld (150) and a fade in (174, 175; without them the screen stays black after the menu), species (354) and form (676) of the chosen slot, branch on the base species, YesNo (63; 0 = yes) with the Pokemon's nickname in {RIVAL} (BufferPartyMonNick, 199, buffer 1),
SetMonForm (659), MonGetLevel (535), then the four moves with TutorMoveTeachInSlot (654: party slot, move slot, move): clear the four slots, then every learnset move whose level is at most the Pokemon's level goes into slot (index mod 4), so the last four stay; fanfare and a closing line.
Usage (from yellow-heartgold, PYTHONPATH=tools): form_trader.py <in.nds> <out.nds>"""
import json
import struct
import sys
from pathlib import Path
import ndspy.rom
from johto_step3d import install, write_scripts
from johto_step3e import A
from map_edit import MapEdit

MAP, X, Z, FACING, SPRITE = 173, 13, 10, 2, 341
SLOT, SPECIES, FORM, LEVEL, YN = 0x8004, 0x8005, 0x8006, 0x8007, 0x800C
DATA = Path(__file__).resolve().parents[1] / 'data' / 'form-trader.json'
TEXT = dict(
    intro="Hi! I'm the FORM TRADER.\rI swap a POKéMON for its ALOLAN or GALARIAN form!\rWhich one will you show me?",
    cancel="Come back any time!",
    decline="Maybe next time!",
    noform="Sorry, that one has no ALOLAN or GALARIAN form.",
    already="That one is already a regional form.\rI can't swap it again!",
)


def article(region):
    return 'an' if region.startswith('A') else 'a'


def name(f):
    return f"{f['region']} {f['base_name']}"


def build(e, forms):
    msg = {k: e.message(v) for k, v in TEXT.items()}
    offer = {i: e.message(f"Swap {{RIVAL}} for {article(f['region'])} {name(f)}?\rIts moves will be reset to its new form's!") for i, f in enumerate(forms)}
    done = {i: e.message(f"Done! It's now {article(f['region'])} {name(f)}!\rIts moves match its new form.") for i, f in enumerate(forms)}
    a = A()
    a.op(96).op(104).msg(msg['intro'])
    a.op(349).op(351, SLOT).op(150).op(174, 6, 1, 1, 0).op(175)       # party menu, slot (255 = cancelled), RestoreOverworld, fade in
    a.compare(SLOT, 255).jump('cancel', 1)
    a.op(354, SLOT, SPECIES).op(676, SLOT, FORM).compare(FORM, 0).jump('already', 5)
    bases = []
    for f in forms:
        if f['base'] not in bases:
            bases.append(f['base'])
    for b in bases:
        a.compare(SPECIES, b).jump('base%d' % b, 1)
    a.jump('noform')
    for b in bases:
        a.label('base%d' % b)
        for i, f in enumerate(forms):
            if f['base'] != b:
                continue
            a.label('offer%d' % i)
            a.raw(struct.pack('<HBH', 199, 1, SLOT))                      # BufferPartyMonNick 1, slot
            a.raw(struct.pack('<HB', 45, offer[i])).op(63, YN).raw(struct.pack('<H', 53))
            a.compare(YN, 0).jump('apply%d' % i, 1)
            nxt = [j for j, g in enumerate(forms) if g['base'] == b and j > i]
            a.jump('offer%d' % nxt[0] if nxt else 'decline')
    for i, f in enumerate(forms):
        a.label('apply%d' % i)
        a.op(659, SLOT, f['form']).op(535, SLOT, LEVEL)
        for s in range(4):
            a.op(654, SLOT, s, 0)
        last = None
        for j, (lv, mv) in enumerate(f['moves']):
            if lv > 1 and lv != last:
                a.compare(LEVEL, lv).jump('moves%d' % i, 0)
            last = lv
            a.op(654, SLOT, j % 4, mv)
        a.label('moves%d' % i)
        a.op(78, 0x4A1).msg(done[i]).op(79).jump('end')
    a.label('cancel').msg(msg['cancel']).jump('end')
    a.label('decline').msg(msg['decline']).jump('end')
    a.label('noform').msg(msg['noform']).jump('end')
    a.label('already').msg(msg['already']).jump('end')
    a.label('end').op(97).end()
    return a


def patch(rom):
    forms = json.loads(DATA.read_text())
    e = MapEdit(rom, MAP)
    a = build(e, forms)
    size = len(a.build(0))
    ids, addrs, _ = install(e, [size])
    code = a.build(addrs[0])
    assert len(code) == size
    write_scripts(e, addrs, [code])
    actors = e.groups[1]
    npc = bytearray(bytes(actors[5]))
    words = list(struct.unpack('<16H', bytes(npc)))
    words[0], words[1], words[2], words[5], words[6], words[12], words[13] = len(actors), SPRITE, 0, ids[0], FACING, X, Z
    actors.append(struct.pack('<16H', *words))
    e.save()
    return dict(map=MAP, script=ids[0], script_bytes=size, forms=len(forms), messages=len(e.rows), npc=(X, Z), bank_bytes=len(e.bank))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
