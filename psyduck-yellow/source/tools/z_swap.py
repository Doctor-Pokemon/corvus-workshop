"""Prototype 0258, Z-Moves phase 2 (proof of concept, JOHTO-POSTGAME-PLAN.md items 53-55): when the shared button was pressed and the attacker holds a Z-Crystal, the move it uses this turn becomes a Z record.
Hook: the player's Fight input function in overlay 12 (decomp BattleControllerPlayer_FightInput, 0x0224A9B0) ends with 'ctx->moveNoCur = ctx->moveNoTemp; ctx->command = ...; target = ov12_022506D4(...)'.
Its first instruction of that tail (0x0224AAA8: movs r3,#0xc1 ; lsls r3,r3,#6 = r3 = 0x3040, the moveNoTemp offset) becomes a BL to a routine in the overlay-129 gap that follows z_button.py's (0x023DEA6C).
The routine (r0-r3 are free there; r5 = ctx; ctx+0x64 = the attacker): if bit <attacker> of the shared button's pressed mask (byte 0x023D50A8+8) is set, bit 31 of the attacker's BattleMon word at ctx + 0xC0*attacker + 0x2D68 (decomp unk28_B, a spare 21-bit flag field; hg-engine uses bit 11 there for 'form change done') is clear and its held item
(ctx + 0xC0*attacker + 0x2DB8) is a Z-Crystal (776..836), it sets that bit (once per Pokemon per battle) and stores the Z move id into ctx+0x3040 (moveNoTemp); then it redoes the replaced instruction and returns. The caller copies it to moveNoCur and picks the target.
PHASE 2 TEST VALUE: the Z id is fixed at 625 (Breakneck Blitz, physical). Phase 3 chooses the record from the base move's type/category and computes the power.
Usage (from yellow-heartgold, PYTHONPATH=tools): z_swap.py <in.nds> <out.nds>   (the input must contain z_button.py)"""
import struct
import sys
import ndspy.code
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from prototype import thumb_bl

CAVE, SITE = 0x023DEA6C, 0x0224AAA8
MASK_BASE, ITEM_OFFSET, FLAGS_OFFSET, FIRST, LAST, Z_ID = 0x023D50A8, 0x2DB8, 0x2D68, 776, 836, 625


def routine():
    src = f'''
        push {{lr}}
        ldr r0, [r5, #0x64]
        ldr r1, lit_base
        ldrb r2, [r1, #8]
        lsrs r2, r0
        lsls r2, r2, #31
        bpl done
        movs r3, #0xc0
        muls r3, r0, r3
        adds r3, r5, r3
        ldr r1, lit_item
        ldrh r2, [r3, r1]
        ldr r0, lit_first
        subs r2, r2, r0
        cmp r2, #{LAST - FIRST}
        bhi done
        ldr r1, lit_flags
        ldr r2, [r3, r1]
        cmp r2, #0
        blt done
        movs r0, #1
        lsls r0, r0, #31
        orrs r2, r0
        str r2, [r3, r1]
        ldr r2, lit_z
        movs r3, #0xc1
        lsls r3, r3, #6
        str r2, [r5, r3]
    done:
        movs r3, #0xc1
        lsls r3, r3, #6
        pop {{pc}}
        .align 2
    lit_base: .word {MASK_BASE}
    lit_item: .word {ITEM_OFFSET}
    lit_first: .word {FIRST}
    lit_flags: .word {FLAGS_OFFSET}
    lit_z: .word {Z_ID}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, CAVE)
    return bytes(code)


def patch(rom):
    ovs = rom.loadArm9Overlays()
    perm, battle = ovs[129], ovs[12]
    for ov in (perm, battle):
        ov.data = bytearray(ov.data)
    code = routine()
    assert len(code) <= 0x23DEAD8 - CAVE, len(code)
    at = CAVE - perm.ramAddress
    assert not any(perm.data[at:at + len(code)]), 'the gap is not zero'
    perm.data[at:at + len(code)] = code
    site = SITE - battle.ramAddress
    assert bytes(battle.data[site:site + 4]) == bytes.fromhex('c123 9b01'.replace(' ', '')), 'unexpected instructions at the hook site'
    battle.data[site:site + 4] = thumb_bl(SITE, CAVE)
    for ov in (perm, battle):
        rom.files[ov.fileID] = ov.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(CAVE), size=len(code), site=hex(SITE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
