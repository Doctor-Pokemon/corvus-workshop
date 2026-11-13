"""ROM 0265: the Silph Co. FIELD KIT, phase 2a: Surf, Waterfall, Whirlpool and Rock Climb without a party Pokemon (owner: "First: Field Kit Phase 2", 2026-11-12).
Phase 1 (field_kit.py, ROM 0222) covered Cut, Rock Smash and Strength. Research (pret/pokeheartgold + our ROM, 2026-11-12):
 - The shared obstacle bank 1165 already has the same "GetPartySlotWithMove var,move" site for the four moves: Rock Climb (431) at 1882 and 2001, Surf (57) at 2127, Waterfall (127) at 2411 and 2498, Whirlpool (250) at 2568 and 2655 (offsets of the 0263 bank). Phase 1's helper (party slot, or slot 0 with the Kit in the bag, or 6) is reused for each.
 - Two checks live in ENGINE code (overlay 1, the field overlay), BEFORE any script runs: field_control.c asks GetIdxOfFirstPartyMonWithMove(party, MOVE_SURF) to offer the Surf script at the shore (BL at 0x021E7544), and
   MOVE_WATERFALL to set the "used Waterfall" player event (BL at 0x021E6BBE). Both BLs to GetIdxOfFirstPartyMonWithMove (ARM9 0x020542E8) are the only callers in the whole ROM. They now call a small routine in an overlay 129
   padding run (0x023DF9B8): it calls the original and, when no party Pokemon knows the move (0xFF) and the bag holds the Field Kit (item 1128), answers slot 0 instead. The badge rules stay as they are.
 - Not here (phase 2b/2c): Flash (std_menu_flash script, party slot argument) and Fly (opens the Pokegear map from a party Pokemon; needs a bag "use" hook), both left for the next steps.
Usage (from yellow-heartgold, PYTHONPATH=tools): field_kit2.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import field_kit
from prototype import thumb_bl

NEW_SITES = ((431, 'Rock Climb'), (57, 'Surf'), (127, 'Waterfall'), (250, 'Whirlpool'))
GETIDX = 0x020542E8
SURF_BL, WATERFALL_BL = 0x021E7544, 0x021E6BBE
CAVE, CAVE_SIZE = 0x023DF9B8, 100
SAVE_GET, BAG_GET, HAS_ITEM = 0x020272B1, 0x0207879D, 0x020784B1       # SaveArray_Get() (no args), Sav2_Bag_get(save), Bag_HasItem(bag, item, qty, heap); all Thumb
GETIDX_T = GETIDX | 1
HEAP_FIELD2 = 4


def routine():
    src = f'''
        push {{r4, lr}}
        ldr r3, lit_getidx
        blx r3
        cmp r0, #0xff
        bne end
        ldr r3, lit_save
        blx r3
        ldr r3, lit_bag
        blx r3
        ldr r1, lit_kit
        movs r2, #1
        movs r3, #{HEAP_FIELD2}
        ldr r4, lit_has
        blx r4
        cmp r0, #0
        beq none
        movs r0, #0
        b end
    none:
        movs r0, #0xff
    end:
        pop {{r4, pc}}
        .align 2
    lit_getidx: .word {GETIDX_T}
    lit_save: .word {SAVE_GET}
    lit_bag: .word {BAG_GET}
    lit_kit: .word {field_kit.KIT}
    lit_has: .word {HAS_ITEM}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, CAVE)
    return bytes(code)


def patch_engine(rom):
    ovs = rom.loadArm9Overlays()
    perm, field = ovs[129], ovs[1]
    for ov in (perm, field):
        ov.data = bytearray(ov.data)
    code = routine()
    assert len(code) <= CAVE_SIZE, len(code)
    at = CAVE - perm.ramAddress
    assert not any(perm.data[at:at + CAVE_SIZE]), 'the cave is not zero'
    perm.data[at:at + len(code)] = code
    for site in (SURF_BL, WATERFALL_BL):
        o = site - field.ramAddress
        assert bytes(field.data[o:o + 4]) == thumb_bl(site, GETIDX), hex(site)
        field.data[o:o + 4] = thumb_bl(site, CAVE)
    for ov in (perm, field):
        rom.files[ov.fileID] = ov.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(CAVE), size=len(code))


def patch(rom):
    field_kit.SITES = NEW_SITES
    report = dict(obstacles=field_kit.patch_obstacles(rom))
    report['engine'] = patch_engine(rom)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
