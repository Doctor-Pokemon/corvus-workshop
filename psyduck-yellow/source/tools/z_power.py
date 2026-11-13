"""Prototype 0259, Z-Moves phase 3 (proof of concept, JOHTO-POSTGAME-PLAN.md items 53-57): the Z-Move is chosen from the base move and its power is computed from the base move's power.
hg-engine keeps a copy of every move's data in the battle structure (BattleStruct.moveTbl at ctx + 0x317E, 16 bytes per move: effect u16, split u8, power u8, type u8, accuracy u8, pp u8 ...) and its damage code reads
the power, split and type of the move that is used from there. So the routine that z_swap.py hooked (ov12 0x224AAA8, called with r5 = ctx, ctx+0x64 = attacker) now works on that table:
  base = ctx->moveNoTemp (ctx + 0x3040); a status base move (split 2) is left alone (no Z-Move, the Z-use flag is NOT spent);
  the generic physical Z record with the base move's TYPE is found by walking ids 625, 627, ... 659 (each type has a physical/special pair; the types of the records are in the table: 625 Normal, 627 Fighting ... 643 Fire ... 659 Fairy);
  that record gets the base move's split and a power from the base move's power (Serebii's Z-Move power table: <=55 100, <=65 120, <=75 140, <=85 160, <=100 175, <=110 180, <=120 190, <=130 195, more 200) and accuracy 0 (never misses);
  moveNoTemp = that Z id; the once-per-battle flag (one byte per battler at ctx + 0x3173 + battler: the explicit padding of hg-engine's BattleStruct in front of moveTbl, zero at battle start) is set.
NOTE: z_swap.py's flag (bit 31 of the BattleMon word at ctx + 0xC0*b + 0x2D68) was WRONG: that bit is used by the engine (the word read 0x90010000 on a Pokemon at low HP), so Z-Moves silently never fired then and writing it could have changed other behaviour.
Conditions: shared button pressed for the attacker (byte 0x023D50A8+8), held Z-Crystal 776..836, own flag byte clear.
NOT done: the move-specific Z-Move powers (Drain, Weather Ball, Hex ...) and moves with power 0 (they get 100), status Z-Moves, Z-Move side effects and animations of their own.
The new routine lives in the overlay-129 gap at 0x023DF4EC; the power table is a small subroutine (r1 = base power -> r3) in the place of z_swap.py's old routine at 0x023DEA6C (the 84 bytes there are replaced) and the BL in overlay 12 is repointed.
Usage (from yellow-heartgold, PYTHONPATH=tools): z_power.py <in.nds> <out.nds>   (the input must contain z_button.py and z_swap.py)"""
import struct
import sys
import ndspy.code
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from prototype import thumb_bl

OLD_CAVE, OLD_SIZE, CAVE, CAVE_SIZE, SITE = 0x023DEA6C, 84, 0x023DF4EC, 204, 0x0224AAA8
SUB = OLD_CAVE                                          # the power table routine takes over the old gap (r1 = base power -> r3 = Z power)
MASK_BASE, ITEM_OFFSET, PAD_OFFSET, FIRST, LAST = 0x023D50A8, 0x2DB8, 0x3173, 776, 836
TABLE_OFFSET, FIRST_Z, LAST_Z = 0x317E, 625, 659
POWERS = ((55, 100), (65, 120), (75, 140), (85, 160), (100, 175), (110, 180), (120, 190), (130, 195))
LAST_POWER = 200


def routine():
    src = f'''
        push {{r6, r7, lr}}
        ldr r0, [r5, #0x64]
        ldr r1, lit_base
        ldrb r2, [r1, #8]
        lsrs r2, r0
        lsls r2, r2, #31
        bpl done
        ldr r3, lit_pad
        adds r3, r5, r3
        ldrb r2, [r3, r0]
        cmp r2, #0
        bne done
        movs r3, #0xc0
        muls r3, r0, r3
        adds r3, r5, r3
        ldr r1, lit_item
        ldrh r2, [r3, r1]
        ldr r1, lit_first
        subs r2, r2, r1
        cmp r2, #{LAST - FIRST}
        bhi done
        ldr r7, lit_table
        adds r7, r5, r7
        movs r0, #0xc1
        lsls r0, r0, #6
        ldr r0, [r5, r0]
        lsls r0, r0, #4
        adds r6, r7, r0
        ldrb r2, [r6, #2]
        cmp r2, #2
        bhs done
        ldrb r1, [r6, #3]
        ldrb r0, [r6, #4]
        ldr r3, lit_zoff
        adds r6, r7, r3
        ldr r7, lit_zfirst
    loop:
        ldrb r3, [r6, #4]
        cmp r3, r0
        beq found
        adds r6, #32
        adds r7, #2
        ldr r3, lit_zlast
        cmp r7, r3
        ble loop
        b done
    found:
        strb r2, [r6, #2]
        movs r3, #0
        strb r3, [r6, #5]
        bl #{SUB:#x}
        strb r3, [r6, #3]
        movs r3, #0xc1
        lsls r3, r3, #6
        str r7, [r5, r3]
        ldr r0, [r5, #0x64]
        ldr r3, lit_pad
        adds r3, r5, r3
        movs r1, #1
        strb r1, [r3, r0]
    done:
        movs r3, #0xc1
        lsls r3, r3, #6
        pop {{r6, r7, pc}}
        .align 2
    lit_base: .word {MASK_BASE}
    lit_item: .word {ITEM_OFFSET}
    lit_first: .word {FIRST}
    lit_pad: .word {PAD_OFFSET}
    lit_table: .word {TABLE_OFFSET}
    lit_zoff: .word {TABLE_OFFSET - TABLE_OFFSET + 16 * FIRST_Z}
    lit_zfirst: .word {FIRST_Z}
    lit_zlast: .word {LAST_Z}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, CAVE)
    return bytes(code)


def power_routine():
    steps = []
    for limit, power in POWERS:
        steps.append(f'movs r3, #{power}\ncmp r1, #{limit}\nbls sub_done')
    steps.append(f'movs r3, #{LAST_POWER}')
    src = '\n'.join(steps[:-1]) + '\n' + steps[-1] + '\nsub_done:\nbx lr\n'
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, SUB)
    return bytes(code)


def patch(rom):
    ovs = rom.loadArm9Overlays()
    perm, battle = ovs[129], ovs[12]
    for ov in (perm, battle):
        ov.data = bytearray(ov.data)
    site = SITE - battle.ramAddress
    assert bytes(battle.data[site:site + 4]) == thumb_bl(SITE, OLD_CAVE), 'the hook is not the one of z_swap.py'
    old = OLD_CAVE - perm.ramAddress
    assert any(perm.data[old:old + OLD_SIZE]) and not any(perm.data[old + OLD_SIZE:old + OLD_SIZE + 8]), 'unexpected old routine area'
    code = routine()
    assert len(code) <= CAVE_SIZE, len(code)
    at = CAVE - perm.ramAddress
    assert not any(perm.data[at:at + CAVE_SIZE]), 'the new gap is not zero'
    perm.data[at:at + len(code)] = code
    sub = power_routine()
    assert len(sub) <= OLD_SIZE
    perm.data[old:old + OLD_SIZE] = bytes(OLD_SIZE)
    perm.data[old:old + len(sub)] = sub
    battle.data[site:site + 4] = thumb_bl(SITE, CAVE)
    for ov in (perm, battle):
        rom.files[ov.fileID] = ov.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(CAVE), size=len(code), sub=hex(SUB), sub_size=len(sub), site=hex(SITE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
