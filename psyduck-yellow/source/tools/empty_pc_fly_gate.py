"""Prototype 0254 (owner 2026-11-12): (1) the player's PC Item Storage starts EMPTY on a New Game; (2) Fly stays unusable until the Thunder Badge (Kanto badge 10).
(1) The PC scripts (bedroom, Pokemon Centers) all share INIT 0x4166 / EVOLUTION_INIT 0x4167 / flags 0xB3B (shiny charm) and 0xA8C (friendship charm): their first-use block writes the starting stacks,
    the evolution items and the two charms only while those are unset. A new frame-table row on the bedroom (map 506) runs once at New Game while INIT is 0: it sets INIT=1, EVOLUTION_INIT=7 and both
    flags, so every first-use block is skipped and no PC script is touched. (The row sits first in the frame table; INIT is 1 afterwards, so the native rows below it run as before.)
(2) The party-menu Fly check (field-move table entry 1, ARM9 0x0206800C) had its TestBadge call replaced by 'movs r0,#1; nop' by the testing_travel patch of prototype 0020 (still in the chain).
    The call is restored with the Thunder Badge (10) as its argument.
Usage (from yellow-heartgold, PYTHONPATH=tools): empty_pc_fly_gate.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from opening import Script
from parcel_quest import append_bank
from pokemon_tower import _frame_entry
from prototype import thumb_bl
from viridian_tutorial import TABLE

BEDROOM = 506
INIT, EVOLUTION_INIT, EVOLUTION_DONE = 0x4166, 0x4167, 7
CHARM_FLAGS = (0xB3B, 0xA8C)
TEST_BADGE = 0x02028F98
FLY_IMMEDIATE, FLY_CALL = 0x02068024, 0x02068026
THUNDER_BADGE = 10


def fly_gate(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    o = 0x02000000
    assert bytes(d[FLY_IMMEDIATE - o:FLY_IMMEDIATE - o + 6]) == bytes.fromhex('04210120c046'), 'Fly check is not in the expected bypassed state'
    d[FLY_IMMEDIATE - o] = THUNDER_BADGE
    d[FLY_CALL - o:FLY_CALL - o + 4] = thumb_bl(FLY_CALL, TEST_BADGE)
    rom.arm9 = main.save(compress=True)
    return dict(site=hex(FLY_CALL), badge=THUNDER_BADGE)


def empty_pc(rom):
    main = rom.loadArm9()
    d = bytes(main.sections[0].data)
    scripts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/1/2')])
    bank_id, header_id = struct.unpack_from('<2H', d, TABLE + BEDROOM * 24 + 6)
    s = Script().emit(41, INIT, 1).emit(41, EVOLUTION_INIT, EVOLUTION_DONE)
    for flag in CHARM_FLAGS:
        s.emit(30, flag)
    s.emit(2)
    bank, count = append_bank(scripts.files[bank_id], [s.finish()])
    scripts.files[bank_id] = bytes(bank)
    scripts.files[header_id] = _frame_entry(scripts.files[header_id], INIT, 0, count + 1)
    rom.files[rom.filenames.idOf('a/0/1/2')] = scripts.save()
    return dict(script=count + 1)


def patch(rom):
    return dict(fly=fly_gate(rom), pc=empty_pc(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
