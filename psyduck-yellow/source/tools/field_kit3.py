"""ROM 0267: the Silph Co. FIELD KIT, phase 2b/2c: FLASH and FLY from the bag (owner: "First: Field Kit Phase 2", 2026-11-12).
Using the Field Kit from the Key Items pocket (USE) now behaves like picking the field move from a party Pokemon's menu, with the LEAD Pokemon (party slot 0) standing in:
 - in a dark cave (the map's weather is Flash, which is exactly when the party menu offers Flash): Flash lights it up (the std_menu_flash script runs: "<lead> used Flash!");
 - anywhere else Fly is tried: the normal Fly checks (badge, Fly allowed on this map, no escort follower, not in the Safari Zone ...), then the Pokegear town map opens to pick a destination and the lead Pokemon flies there;
 - when neither works a small script says "The FIELD KIT can't be used here." (PLACEHOLDER line, not from the owner's lists).
HOW: the use function table at ARM9 0x020FE264 holds three pointers per field-use id (menu / field / check). The Field Kit's record (a copy of the Lift Key's) gets field-use id 28 (Gracidea: the item is given by no script and nothing
else uses id 28 except item 765, also given by none) and its REGISTER bit is cleared (the Select shortcut would call the Gracidea field function). The id-28 MENU function is replaced by a routine in an overlay 129 padding run
(0x023DE700, 128 zero bytes before stone_check.py's word at 0x023DE780): it builds the field-move check data (FieldMove_InitCheckData 0x02067E11), asks the real FieldMove_CheckFlash / CheckFly through sFieldMoveFuncTable (ARM9 0x020FE7BC,
{use, check} pairs, Flash = pair 7, Fly = pair 1) and calls the real FieldMove_UseFlash / UseFly with a FieldMoveUseData of (task manager, slot 0). The bag has already freed its environment when the menu function runs, as in the party-menu path.
Usage (from yellow-heartgold, PYTHONPATH=tools): field_kit3.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import field_kit
from opening import Script, encode_text
from parcel_quest import PH, append_bank
from prototype import decode_messages, encode_messages

KIT = field_kit.KIT
USE_ID = 28
USE_TABLE, FIELD_MOVE_TABLE = 0x020FE264, 0x020FE7BC
OLD_MENU_FUNC = 0x020655B9                          # ItemMenuUseFunc_Gracidea | 1 (checked)
INIT_CHECK, GET_FS, ALPH = 0x02067E11, 0x0205064D, 0x02064A8D
CAVE, CAVE_SIZE = 0x023DE700, 124
STD_BANK, STD_TEXT, STD_BASE = 1165, 211, 10000
CANT = "The FIELD KIT can't be used here."


def routine(check_flash, use_flash, check_fly, use_fly, script_id):
    src = f'''
        push {{r4, r5, r6, r7, lr}}
        sub sp, #0x1c
        movs r4, r0
        movs r5, r1
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
        ldr r3, lit_cflash
        blx r3
        cmp r0, #0
        bne tryfly
        add r0, sp, #0x10
        add r1, sp, #0
        ldr r3, lit_uflash
        blx r3
        b done
    tryfly:
        add r0, sp, #0
        ldr r3, lit_cfly
        blx r3
        cmp r0, #0
        bne fail
        add r0, sp, #0x10
        add r1, sp, #0
        ldr r3, lit_ufly
        blx r3
        b done
    fail:
        movs r0, r4
        movs r1, r5
        ldr r2, lit_script
        ldr r3, lit_alph
        blx r3
    done:
        add sp, #0x1c
        pop {{r4, r5, r6, r7, pc}}
        .align 2
    lit_getfs: .word {GET_FS}
    lit_init: .word {INIT_CHECK}
    lit_cflash: .word {check_flash}
    lit_uflash: .word {use_flash}
    lit_cfly: .word {check_fly}
    lit_ufly: .word {use_fly}
    lit_script: .word {script_id}
    lit_alph: .word {ALPH}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, CAVE)
    return bytes(code)


def patch_item_and_text(rom):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    rec = bytearray(items.files[KIT])
    flags = struct.unpack_from('<H', rec, 8)[0]
    assert (flags >> 7) & 15 == 7 and rec[10] == 0, (hex(flags), rec[10])               # Key Items pocket, no field use yet (the Lift Key's record)
    struct.pack_into('<H', rec, 8, flags & ~0x40)                                        # not registrable
    rec[10] = USE_ID
    items.files[KIT] = bytes(rec)
    rom.setFileByName('a/0/1/7', items.save())
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    key, rows = decode_messages(texts.files[STD_TEXT])
    msg = len(rows)
    assert msg < 250
    rows.extend(decode_messages(encode_text([CANT], PH))[1])
    texts.files[STD_TEXT] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    s = Script().emit(96).emit(746).msg(msg).emit(747).emit(97).emit(2)                  # LockAll, TouchscreenMenuHide, message, TouchscreenMenuShow, ReleaseAll, End
    bank, count = append_bank(bytes(scripts.files[STD_BANK]), [s.finish()])
    scripts.files[STD_BANK] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return STD_BASE + count, msg


def patch_engine(rom, script_id):
    main = rom.loadArm9()
    main.sections[0].data = bytearray(main.sections[0].data)
    d, base = main.sections[0].data, main.sections[0].ramAddress
    menu_at = USE_TABLE - base + 12 * USE_ID
    assert struct.unpack_from('<I', d, menu_at)[0] == OLD_MENU_FUNC, hex(struct.unpack_from('<I', d, menu_at)[0])
    ft = FIELD_MOVE_TABLE - base
    use_fly, check_fly = struct.unpack_from('<2I', d, ft + 8 * 1)
    use_flash, check_flash = struct.unpack_from('<2I', d, ft + 8 * 7)
    assert (use_fly, check_fly) == (0x0206809D, 0x0206800D), (hex(use_fly), hex(check_fly))
    code = routine(check_flash, use_flash, check_fly, use_fly, script_id)
    assert len(code) <= CAVE_SIZE, len(code)
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    at = CAVE - perm.ramAddress
    assert not any(perm.data[at:at + CAVE_SIZE]), 'the cave is not zero'
    perm.data[at:at + len(code)] = code
    struct.pack_into('<I', d, menu_at, CAVE | 1)
    rom.arm9 = main.save(compress=True)
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(CAVE), size=len(code), flash=(hex(check_flash), hex(use_flash)))


def patch(rom):
    script_id, msg = patch_item_and_text(rom)
    return dict(script_id=script_id, message=msg, engine=patch_engine(rom, script_id))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
