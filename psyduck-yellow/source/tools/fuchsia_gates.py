"""Prototype 0182: the Route 15 and Route 18 gatehouses are closed until the Marsh Badge (owner order 2026-11-04: "Same script as the Saffron Guards, but with different text").
Why: Strength now comes from Sabrina (Saffron Gym), and the owner wants Strength (= Sabrina beaten) before Fuchsia, so the player can reach Janine's Surf and the Warden's NUGGET routine in the intended order.
Fuchsia's land entrances are the Route 15 gatehouse (map 392, east of the city) and the Route 18 gatehouse (map 423, on the Cycling Road side); the Route 19 gatehouse (424) is already closed by its Volcano Badge guard (native).
Built exactly like saffron_gates.py: a trigger line across each gatehouse's corridor runs a script that checks the badge; without it the guard's line plays and the player is walked back two steps to the route side; with it nothing happens.
The guard NPC (script 1) is now OFFICER JENNY (owner's order: she delivers the line; sprite 34 as in Vermilion), standing in the corridor in front of the trigger line (gate 392: tile (7,7) facing east; gate 423: (3,7) facing west). She says the same line when talked to without the badge, and his original line once the badge is owned. Badge test: CheckBadge 13 (the Marsh Badge, Sabrina's), not the HM04 item, so a full bag at Sabrina's cannot lock anyone out.
Gate 392: the city door is its west end (x=1), Route 15 the east end: trigger column x=6 (z 6-8), walk back east (movement code 15). Gate 423: the Route 18 (Cycling Road side) door is its west end, Fuchsia's side the east end: trigger column x=4
(the bicycle triggers at x=5 and 6 stay untouched, behind it), walk back west (14). No flag, no variable. Owner's text (second wording, 2026-11-04).
Usage (from yellow-heartgold, PYTHONPATH=tools): fuchsia_gates.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from opening import Script, end

MARSH = 13
TEXT = ("Sorry. The recent activity of Cinnabar's volcano has caused rockslides blocking the exit here. "
        "You'd need a Pok\u00e9mon to use its great STRENGTH to push the boulders out of the way before you could get through there.")
GATES = {392: dict(x=6, back=15, jenny=(7, 7, 3)), 423: dict(x=4, back=14, jenny=(3, 7, 2))}      # map: trigger column x (z 6-8), movement code that walks the player back to the route side, Jenny's tile and facing (3 east, 2 west)
JENNY_SPRITE = 34                                                   # the Officer Jenny overworld sprite (vermilion_jenny.py's Squirtle-gift NPC)
GUARD_BEFORE = (73, 1500)


def trigger_script(blocked, back):
    s = Script().emit(96).emit(294, MARSH, 0x800C).compare(0x800C, 1).jump('open', 1)
    s.msg(blocked).movement(255, 'back').emit(95)
    end(s)
    s.label('open')
    end(s)
    s.moves('back', [(back, 2)])
    return s.finish()


def guard_script(blocked):
    s = Script().emit(73, 1500).emit(96).emit(104).emit(294, MARSH, 0x800C).compare(0x800C, 1).jump('open', 1)
    s.msg(blocked)
    end(s)
    s.label('open').msg(0)
    end(s)
    return s.finish()


def patch(rom, source=None):
    report = {}
    for mapid, g in GATES.items():
        edit = MapEdit(rom, mapid)
        assert len(edit.groups[1]) == 1 and struct.unpack_from('<H', edit.groups[1][0], 10)[0] == 1
        blocked = edit.message(TEXT)
        trig = edit.script(lambda add: trigger_script(blocked, g['back']))
        guard = edit.script(lambda add: guard_script(blocked))
        row = bytearray(edit.groups[1][0])
        struct.pack_into('<H', row, 10, guard)
        struct.pack_into('<H', row, 2, JENNY_SPRITE)                 # the gate guard becomes Officer Jenny, standing in the corridor just before the trigger line
        struct.pack_into('<H', row, 12, g['jenny'][2])
        struct.pack_into('<2H', row, 24, g['jenny'][0], g['jenny'][1])
        edit.groups[1][0] = bytes(row)
        edit.groups[3].append(struct.pack('<Hhh5H', trig, g['x'], 6, 1, 3, 0, 0, 0))
        edit.save()
        report[mapid] = dict(trigger_script=trig, guard_script=guard, message=blocked, trigger_x=g['x'])
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
