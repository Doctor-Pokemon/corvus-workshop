"""ROM 0273: the TAXI PAGER's Fly animation shows CORVIKNIGHT (owner 2026-11-12: "Corviknight IS in this ROM"; the species list spells it "Corviknite", internal species 873, with pokegra sprites).
HeartGold's Fly animation draws the picture of the Pokemon it is given: Task_UseFlyInField (ARM9 0x0203D780 region) fetches it with Party_GetMonByIndex(party, slot) (BL at 0x0203D7B6) and passes it to sub_02067BF8 (the fly task).
 - That BL now goes to a hook in overlay 129 (0x023DE784). A "taxi" word (0x023DE804) set by the Taxi Pager's routine makes the hook return a prepared Corviknight instead (and clears the word); otherwise it is Party_GetMonByIndex.
 - The prepared Pokemon is made by the game itself on the heap: AllocMonZeroed(HEAP_ID_FIELD2 = 0xB, ARM9 0x0206DD2C) then CreateMon (ARM9 0x0206DE38, hg-engine trampoline) with species 873, level 50, random personality. It is never freed (about 236 bytes per taxi flight).
 - The Taxi Pager routine (taxi_pager.py / vs_recorder.py, 0x023DE700) sets the word before it calls the real FieldMove_UseFly. The Fly entry of sFieldMoveFuncTable (ARM9 0x020FE7C4) points to a 16-byte wrapper that clears the word and then runs the real UseFly,
   so a Fly started from a Pokemon's menu (the HM) never shows the taxi, even after a cancelled taxi map.
Usage (from yellow-heartgold, PYTHONPATH=tools): taxi_sprite.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import field_kit3
import vs_recorder
from prototype import thumb_bl

CORVIKNIGHT = 873
GET_MON_BL, PARTY_GET_MON = 0x0203D7B6, 0x02074644
ALLOC_MON, CREATE_MON, HEAP_FIELD2 = 0x0206DD2C, 0x0206DE38, 0x0B        # AllocMonZeroed(heap), CreateMon (hg-engine trampoline; 8 arguments, 4 of them on the stack)
REGION, REGION_END = 0x023DE784, 0x023DE808
WRAPPER_AT = 0x023DEAA0                                  # start of a 56-byte zero run in overlay 129
FLAG = 0x023DE804
FLY_ENTRY = field_kit3.FIELD_MOVE_TABLE + 8 * 1          # {use, check} of Fly: the use pointer
ROUTINE_SLACK = 0x023DE700 + field_kit3.CAVE_SIZE


def hook():
    src = f'''
        push {{r4, r5, r6, lr}}
        ldr r2, lit_flag
        ldr r3, [r2]
        cmp r3, #0
        beq real
        movs r3, #0
        str r3, [r2]
        movs r0, #{HEAP_FIELD2}
        ldr r3, lit_allocmon
        blx r3
        movs r4, r0
        sub sp, #16
        movs r0, #0
        str r0, [sp]
        str r0, [sp, #4]
        str r0, [sp, #8]
        str r0, [sp, #12]
        movs r0, r4
        ldr r1, lit_species
        movs r2, #50
        movs r3, #0
        ldr r5, lit_create
        blx r5
        add sp, #16
        movs r0, r4
        pop {{r4, r5, r6, pc}}
    real:
        ldr r3, lit_real
        blx r3
        pop {{r4, r5, r6, pc}}
        .align 2
    lit_flag: .word {FLAG}
    lit_allocmon: .word {ALLOC_MON | 1}
    lit_species: .word {CORVIKNIGHT}
    lit_create: .word {CREATE_MON | 1}
    lit_real: .word {PARTY_GET_MON | 1}
    '''
    return bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, REGION)[0])


def wrapper(base, real_use):
    src = f'''
        ldr r2, lit_flag
        movs r3, #0
        str r3, [r2]
        ldr r2, lit_use
        bx r2
        .align 2
    lit_flag: .word {FLAG}
    lit_use: .word {real_use}
    '''
    return bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, base)[0])


def patch(rom):
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d, ram = main.sections[0].data, main.sections[0].ramAddress
    h = hook()
    assert len(h) <= FLAG - REGION, len(h)
    w_at = WRAPPER_AT
    real_use, check_fly = struct.unpack_from('<2I', d, FLY_ENTRY - ram - 0 if False else field_kit3.FIELD_MOVE_TABLE - ram + 8)
    w = wrapper(w_at, real_use)
    at = REGION - perm.ramAddress
    assert not any(perm.data[at:REGION_END - perm.ramAddress]), 'the region is not zero'
    assert not any(perm.data[w_at - perm.ramAddress:w_at - perm.ramAddress + 32]), 'the wrapper spot is not zero'
    perm.data[at:at + len(h)] = h
    perm.data[w_at - perm.ramAddress:w_at - perm.ramAddress + len(w)] = w
    # the pager routine: rebuilt with the taxi word set before the real UseFly
    code = pager_code(check_fly, real_use)
    cave = field_kit3.CAVE - perm.ramAddress
    assert perm.data[cave:cave + 2] == struct.pack('<H', 0xB5F0), 'the vs_recorder.py routine is not there'
    assert len(code) <= field_kit3.CAVE_SIZE, len(code)
    perm.data[cave:cave + field_kit3.CAVE_SIZE] = code + bytes(field_kit3.CAVE_SIZE - len(code))
    # the Task_UseFlyInField call and the table entry
    assert bytes(d[GET_MON_BL - ram:GET_MON_BL - ram + 4]) == thumb_bl(GET_MON_BL, PARTY_GET_MON), 'unexpected call site'
    d[GET_MON_BL - ram:GET_MON_BL - ram + 4] = thumb_bl(GET_MON_BL, REGION)
    struct.pack_into('<I', d, field_kit3.FIELD_MOVE_TABLE - ram + 8, w_at | 1)
    rom.arm9 = main.save(compress=True)
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(hook=len(h), wrapper=hex(w_at), pager=len(code))


def pager_code(check_fly, use_fly):
    """tools/vs_recorder.py's routine (Card Album branch, Fly, can't-message) with the taxi word set just before the real UseFly."""
    src = f'''
        push {{r4, r5, r6, r7, lr}}
        sub sp, #0x1c
        movs r4, r0
        movs r5, r1
        ldrh r0, [r4, #4]
        ldr r1, lit_album
        cmp r0, r1
        bne fly
        ldr r2, lit_ascript
        b call
    fly:
        ldr r6, [r4]
        movs r0, r6
        ldr r3, lit_getfs
        blx r3
        add r1, sp, #0
        ldr r3, lit_init
        blx r3
        str r6, [sp, #0x10]
        movs r0, #0
        str r0, [sp, #0x14]
        add r0, sp, #0
        ldr r3, lit_cfly
        blx r3
        cmp r0, #0
        bne fail
        ldr r2, lit_flag
        movs r3, #1
        str r3, [r2]
        add r0, sp, #0x10
        add r1, sp, #0
        ldr r3, lit_ufly
        blx r3
        b done
    fail:
        ldr r2, lit_script
    call:
        movs r0, r4
        movs r1, r5
        ldr r3, lit_alph
        blx r3
    done:
        add sp, #0x1c
        pop {{r4, r5, r6, r7, pc}}
        .align 2
    lit_album: .word {vs_recorder.ALBUM}
    lit_ascript: .word {vs_recorder.ALBUM_SCRIPT}
    lit_getfs: .word {field_kit3.GET_FS}
    lit_init: .word {field_kit3.INIT_CHECK}
    lit_cfly: .word {check_fly}
    lit_ufly: .word {use_fly}
    lit_script: .word 10030
    lit_alph: .word {field_kit3.ALPH}
    lit_flag: .word {FLAG}
    '''
    return bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, field_kit3.CAVE)[0])


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
