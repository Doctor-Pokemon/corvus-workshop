"""ROM 0271: the VS. RECORDER (item 465) is restored and the CARD ALBUM moves to its own Key Item (owner 2026-11-12: "move the Card Album to a different Key Item and restore the original VS. Recorder").
Why: HeartGold's Battle Frontier / Trainer House talk ("check your Battle Points using your Vs. Recorder") and a native script (bank 231, map 97) use item 465; tools/card_album.py had repurposed it.
 1. Item 465: record, name (bank 222 row 465), description (bank 830 row 465 = vanilla HeartGold's own text bank 221 row 465) and its use function (ARM9 0x02065614, ItemMenuUseFunc_VSRecorder, 0x34 bytes, from ROM 0040) are back to the original. Its icon was never changed.
 2. The Card Album is item 1076 (an all-zero record, given by no script): the Lift Key's record with field-use id 28 and the register bit cleared, Pal Pad's icon, name in bank 222, description in bank 846 row 2.
    Field-use id 28 is shared with the Taxi Pager (taxi_pager.py): the overlay 129 routine (0x023DE700) now reads the item id from the use data (u16 at +4): the Card Album runs its menu script (standard script 10025, bank 1165) through the Alph item-reaction routine, anything else tries Fly.
 3. The Oak's Lab aide (map 505, script bank 1414) gives / tests item 1076 instead of 465 (one GiveItem and one HaveItem operand).
New Game only (a save that holds the old Card Album in slot 465 would hold a Vs. Recorder now).
Usage (from yellow-heartgold, PYTHONPATH=tools): vs_recorder.py <in.nds> <out.nds> <ROM 0040.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import field_kit3
import taxi_pager
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages

VSR, ALBUM, LIFT_KEY, PAL_PAD = 465, 1076, 878, 437
OLD_FUNC, FUNC_SIZE = 0x02065614, 0x34
ALBUM_SCRIPT = 10025
LAB_BANK = 1414
ALBUM_DESC = "A collection of the notable\nTRAINERS you have beaten."


def routine(check_fly, use_fly):
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
    lit_album: .word {ALBUM}
    lit_ascript: .word {ALBUM_SCRIPT}
    lit_getfs: .word {field_kit3.GET_FS}
    lit_init: .word {field_kit3.INIT_CHECK}
    lit_cfly: .word {check_fly}
    lit_ufly: .word {use_fly}
    lit_script: .word 10030
    lit_alph: .word {field_kit3.ALPH}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, field_kit3.CAVE)
    return bytes(code)


def patch(rom, base, vanilla):
    # --- items
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    bitems = ndspy.narc.NARC(base.getFileByName('a/0/1/7'))
    assert not any(items.files[ALBUM]), 'item 1076 is not empty'
    items.files[VSR] = bytes(bitems.files[VSR])
    rec = bytearray(items.files[LIFT_KEY])
    flags = struct.unpack_from('<H', rec, 8)[0]
    struct.pack_into('<H', rec, 8, flags & ~0x40)
    rec[10] = field_kit3.USE_ID
    items.files[ALBUM] = bytes(rec)
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    gfx.files[ALBUM * 2 + 2], gfx.files[ALBUM * 2 + 3] = bytes(gfx.files[PAL_PAD * 2 + 2]), bytes(gfx.files[PAL_PAD * 2 + 3])
    rom.setFileByName('a/0/1/8', gfx.save())
    # --- texts
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    btexts = ndspy.narc.NARC(base.files[base.filenames.idOf('a/0/2/7')])
    vtexts = ndspy.narc.NARC(vanilla.files[vanilla.filenames.idOf('a/0/2/7')])
    row = lambda text: decode_messages(encode_text([text], PH))[1][0]
    key, rows = decode_messages(texts.files[222])
    rows[VSR] = decode_messages(btexts.files[222])[1][VSR]
    rows[ALBUM] = row('Card Album')
    texts.files[222] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[830])
    rows[VSR] = decode_messages(vtexts.files[221])[1][VSR]
    texts.files[830] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[846])
    assert rows[ALBUM - 1074] == [65535]
    rows[ALBUM - 1074] = row(ALBUM_DESC)
    texts.files[846] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()
    # --- ARM9 use function
    main = rom.loadArm9()
    d, ram = main.sections[0].data, main.sections[0].ramAddress
    bmain = base.loadArm9()
    orig = bytes(bmain.sections[0].data[OLD_FUNC - ram:OLD_FUNC - ram + FUNC_SIZE])
    assert orig[:6] == bytes.fromhex('38b5041c2068') and bytes(d[OLD_FUNC - ram:OLD_FUNC - ram + 2]) == struct.pack('<H', 0x4A02), 'unexpected function bytes'
    d = bytearray(d)
    d[OLD_FUNC - ram:OLD_FUNC - ram + FUNC_SIZE] = orig
    main.sections[0].data = d
    use_fly, check_fly = struct.unpack_from('<2I', d, field_kit3.FIELD_MOVE_TABLE - ram + 8)
    # --- overlay 129 routine
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    at = field_kit3.CAVE - perm.ramAddress
    assert perm.data[at:at + 2] == struct.pack('<H', 0xB5F0), 'the taxi_pager.py routine is not there'
    code = routine(check_fly, use_fly)
    assert len(code) <= field_kit3.CAVE_SIZE, len(code)
    perm.data[at:at + field_kit3.CAVE_SIZE] = code + bytes(field_kit3.CAVE_SIZE - len(code))
    rom.arm9 = main.save(compress=True)
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    # --- the Oak's Lab aide
    scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
    bank = bytearray(scripts.files[LAB_BANK])
    done = []
    for op in (125, 128):
        pat = struct.pack('<HH', op, VSR)
        assert bytes(bank).count(pat) == 1, (op, bytes(bank).count(pat))
        at = bytes(bank).find(pat)
        struct.pack_into('<H', bank, at + 2, ALBUM)
        done.append(at)
    scripts.files[LAB_BANK] = bytes(bank)
    rom.setFileByName('a/0/1/2', scripts.save())
    return dict(routine=len(code), lab=done)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom, ndspy.rom.NintendoDSRom.fromFile(sys.argv[3]), ndspy.rom.NintendoDSRom.fromFile('../Pokemon - HeartGold Version (USA).nds')))
    rom.saveToFile(sys.argv[2])
