"""Prototype 0211: Mom in New Bark Town gives the player the SQUIRT BOTTLE (owner order 2026-11-09: she used to hand over things the player already has; instead she should hand over what Johto still needs so it can be played in any order, starting with the item that starts the Sudowoodo battle).
Facts (read with tools/hg_dis.py, tested in the emulator): the odd tree (Sudowoodo) on Route 36 (map 40, script 1) only needs the SQUIRT BOTTLE (item 477) in the bag: with it the tree asks "Use the SquirtBottle?" and the battle follows, as in HeartGold. The bottle normally comes from the Goldenrod flower shop after the Plain Badge (map 184 script 1).
Mom's house (map 63, bank 845):
 - Her first-visit scene (script 1, frame row 0x4106 == 0) hands out four menu "gifts" (flags 0x11b-0x11e with the lines "This is your Trainer Card", "Here you can save a record", "These are also rather helpful...", "Just try touching the buttons"). The four steps become one: the flags are still set silently, then her own line "These are also rather helpful..." and the Squirt Bottle (the native item-gift routine, CallStd 0x7f1). The old steps' 52 bytes become a jump to an appended block and no-ops.
 - Her talk script (script 2) is wrapped by a new script: if the bag has no Squirt Bottle she gives it (same line + gift), otherwise the old script runs unchanged. Her actor points at the wrapper (the house's objects are rebuilt from the event file whenever the house is entered, so an existing save gets it on the next visit). The bottle is a key item (cannot be sold or tossed), so no flag is needed.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_mom_gift.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from map_edit import MapEdit
from johto_step3d import install, write_scripts
from johto_step3e import A

MOM_HOUSE, SQUIRT_BOTTLE = 63, 477
MENU_FLAGS = (0x11B, 0x11C, 0x11D, 0x11E)
OLD_MESSAGES = (2, 3, 4, 5)
HELPFUL_LINE = 4                                          # "These are also rather helpful..."
HAS, FACE = 128, 104                                      # HasItem, FacePlayer (pret script.inc)


def old_steps():
    out = b''
    for flag, msg in zip(MENU_FLAGS, OLD_MESSAGES):
        out += struct.pack('<2H', 30, flag) + struct.pack('<2H', 78, 0x58A) + struct.pack('<H', 79) + struct.pack('<HB', 45, msg)
    return out


def gift(a):
    a.set_var(0x8004, SQUIRT_BOTTLE).set_var(0x8005, 1).op(20, 0x7F1)
    return a


def patch(rom):
    e = MapEdit(rom, MOM_HOUSE)
    steps = old_steps()
    assert len(steps) == 52 and e.bank.count(steps) == 1, 'the four old gift steps were not found exactly once'
    # sizes
    def block_code(base, after):
        a = A()
        for f in MENU_FLAGS:
            a.setf(f)
        a.msg(HELPFUL_LINE)
        gift(a)
        a.jump(('abs', after))
        return a.build(base)
    def wrapper(base, talk):
        a = A()
        a.op(HAS, SQUIRT_BOTTLE, 1, 0x800C).compare(0x800C, 1).jump(('abs', talk), 1)
        a.raw(struct.pack('<H', 96)).raw(struct.pack('<H', FACE))
        a.msg(HELPFUL_LINE)
        gift(a)
        a.raw(struct.pack('<H', 53)).raw(struct.pack('<H', 97)).end()
        return a.build(base)
    ids, addrs, starts = install(e, [len(block_code(0, 0)), len(wrapper(0, 0))])
    at = e.bank.find(steps)
    talk = starts[2 - 1]
    block_at, wrap_at = addrs
    write_scripts(e, [block_at, wrap_at], [block_code(block_at, at + 52), wrapper(wrap_at, talk)])
    bank = bytearray(e.bank)
    bank[at:at + 52] = struct.pack('<Hi', 22, block_at - (at + 6)) + bytes(46)
    e.bank = bytes(bank)
    # Mom's actor (object 0) runs the wrapper
    row = bytearray(e.groups[1][0])
    assert struct.unpack_from('<H', row, 10)[0] == 2, struct.unpack_from('<7H', row, 0)
    struct.pack_into('<H', row, 10, ids[1])
    e.groups[1][0] = bytes(row)
    e.save()
    return dict(first_visit_block=ids[0], talk_wrapper=ids[1])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
