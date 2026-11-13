"""ROM 0269: FLY becomes its own Key Item, the TAXI PAGER (owner 2026-11-12: "add FLY as a separate Key Item: Taxi Pager. And Flash is not necessary. Field Kit is done for now").
 1. The item: id 1129 (an all-zero record, an item the owner dropped, given by no script) becomes the key item "Taxi Pager": the record of the Lift Key with field-use id 28 and the REGISTER bit cleared, the Town Map's icon, name in bank 222,
    description in bank 846 row 55 (PLACEHOLDER wording). USE from the bag runs the routine of field_kit3.py (overlay 129 0x023DE700), now rewritten to Fly only: the real FieldMove_CheckFly / UseFly with the lead Pokemon (slot 0);
    when Fly is not allowed there the script 10030 says "The TAXI PAGER can't be used here." (text bank 211 row 186 rewritten; placeholder).
 2. The Field Kit goes back to being passive: its record is again an exact copy of the Lift Key's (no USE button). Flash from the Kit is dropped (owner).
 3. Delivery (my choice, the owner gave none): Lt. Surge hands it over right after HM02 Fly, once, when the Thunder Badge is owned (Fly is his HM): the helper of hm_gym_gifts.py is put behind a new helper that gives the pager first and then jumps into the old helper
    after its WaitButton/CloseMsg. "Already given" = the item in the bag (key items cannot be tossed). The lines are PLACEHOLDERS.
Usage (from yellow-heartgold, PYTHONPATH=tools): taxi_pager.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
import field_kit
import field_kit3
from johto_step3d import install
from johto_step3d import starts as bank_starts
from johto_step3e import A
from map_edit import MapEdit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages

PAGER, KIT, LIFT_KEY, TOWN_MAP = 1129, field_kit.KIT, 878, 442
NAME, DESC_BANK, DESC_BASE = 'Taxi Pager', 846, 1074
DESCRIPTION = "A pager that calls a flying taxi.\nWith the right BADGE, it flies you\nto a town you have visited."
CANT = "The TAXI PAGER can't be used here."
CANT_ROW = 186                                                      # row of bank 211 written by field_kit3.py
SURGE_MAP, SURGE_ACTOR, THUNDER = 365, 9, 10
LINE = 'Take this TAXI PAGER, too! With the\nTHUNDER BADGE, it calls a flying taxi\nto any town you have visited.'
GOT = '{PLAYER} received the TAXI PAGER!'
FULL = 'You have no room for this.'
TAIL_GOTO = struct.pack('<H', 22)


def routine(check_fly, use_fly, script_id):
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
    lit_getfs: .word {field_kit3.GET_FS}
    lit_init: .word {field_kit3.INIT_CHECK}
    lit_cfly: .word {check_fly}
    lit_ufly: .word {use_fly}
    lit_script: .word {script_id}
    lit_alph: .word {field_kit3.ALPH}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, field_kit3.CAVE)
    return bytes(code)


def patch_items_and_text(rom):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    assert not any(items.files[PAGER]), 'item 1129 is not empty'
    lift = bytearray(items.files[LIFT_KEY])
    pager = bytearray(lift)
    flags = struct.unpack_from('<H', pager, 8)[0]
    struct.pack_into('<H', pager, 8, flags & ~0x40)
    pager[10] = field_kit3.USE_ID
    items.files[PAGER] = bytes(pager)
    kit = bytes(items.files[KIT])
    assert kit[10] == field_kit3.USE_ID, 'the Field Kit has no use id (field_kit3.py not applied)'
    items.files[KIT] = bytes(lift)                                       # passive again (the Lift Key's record exactly)
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    gfx.files[PAGER * 2 + 2], gfx.files[PAGER * 2 + 3] = bytes(gfx.files[TOWN_MAP * 2 + 2]), bytes(gfx.files[TOWN_MAP * 2 + 3])
    rom.setFileByName('a/0/1/8', gfx.save())
    texts = ndspy.narc.NARC(rom.files[rom.filenames.idOf('a/0/2/7')])
    row = lambda text: decode_messages(encode_text([text], PH))[1][0]
    key, rows = decode_messages(texts.files[222])
    rows[PAGER] = row(NAME)
    texts.files[222] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[DESC_BANK])
    assert rows[PAGER - DESC_BASE] == [65535], rows[PAGER - DESC_BASE]
    rows[PAGER - DESC_BASE] = row(DESCRIPTION)
    texts.files[DESC_BANK] = encode_messages(key, rows)
    key, rows = decode_messages(texts.files[field_kit3.STD_TEXT])
    rows[CANT_ROW] = row(CANT)
    texts.files[field_kit3.STD_TEXT] = encode_messages(key, rows)
    rom.files[rom.filenames.idOf('a/0/2/7')] = texts.save()


def patch_engine(rom):
    main = rom.loadArm9()
    d, base = main.sections[0].data, main.sections[0].ramAddress
    ft = field_kit3.FIELD_MOVE_TABLE - base
    use_fly, check_fly = struct.unpack_from('<2I', d, ft + 8)
    code = routine(check_fly, use_fly, 10030)
    ovs = rom.loadArm9Overlays()
    perm = ovs[129]
    perm.data = bytearray(perm.data)
    at = field_kit3.CAVE - perm.ramAddress
    old = bytes(perm.data[at:at + field_kit3.CAVE_SIZE])
    assert old[:2] == struct.pack('<H', 0xB5F0), 'the field_kit3.py routine is not there'          # push {r4-r7, lr}
    assert len(code) <= field_kit3.CAVE_SIZE
    perm.data[at:at + field_kit3.CAVE_SIZE] = code + bytes(field_kit3.CAVE_SIZE - len(code))
    rom.files[perm.fileID] = perm.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(size=len(code))


def surge_helper(base, helper_a, m_line, m_got, m_full):
    """WaitButton, CloseMsg; Thunder Badge owned and no pager: line, GiveItem, fanfare, received; then into the HM helper (after its own WaitButton/CloseMsg)."""
    a = A()
    a.raw(struct.pack('<2H', 50, 53))
    a.op(294, THUNDER, 0x800C).compare(0x800C, 0).jump('old', 1)
    a.op(128, PAGER, 1, 0x800C).compare(0x800C, 1).jump('old', 1)
    a.msg(m_line)
    a.op(125, PAGER, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    a.op(78, 0x4A1).msg(m_got).op(79)
    a.label('old').jump(('abs', helper_a + 4))
    a.label('full').msg(m_full).jump(('abs', helper_a + 4))
    return a.build(base)


def patch_surge(rom):
    e = MapEdit(rom, SURGE_MAP)
    sid = struct.unpack_from('<H', e.groups[1][SURGE_ACTOR], 10)[0]
    m_line, m_got, m_full = e.message(LINE), e.message(GOT), e.message(FULL)
    size = len(surge_helper(0, 0, m_line, m_got, m_full))
    ids, addrs, _ = install(e, [size])                                      # the header may grow: find everything AFTER installing
    bank = bytearray(e.bank)
    st = bank_starts(bytes(bank))
    begin = st[sid - 1]
    end = min([s for s in st if s > begin] + [len(bank)])
    sites, targets = [], set()
    for p in range(begin, end - 8):
        if bank[p:p + 2] == TAIL_GOTO and bank[p + 6:p + 8] == b'\0\0':
            t = p + 6 + struct.unpack_from('<i', bank, p + 2)[0]
            if 0 <= t < len(bank) - 6 and bank[t:t + 4] == struct.pack('<2H', 50, 53) and bank[t + 4:t + 6] == struct.pack('<H', 294):
                sites.append(p)
                targets.add(t)
    assert sites and len(targets) == 1, (sites, targets)
    helper_a = targets.pop()
    code = surge_helper(addrs[0], helper_a, m_line, m_got, m_full)
    assert len(code) == size
    bank[addrs[0]:addrs[0] + size] = code
    for p in sites:
        bank[p + 2:p + 6] = struct.pack('<i', addrs[0] - (p + 6))
    e.bank = bytes(bank)
    e.save()
    return dict(map=SURGE_MAP, script=sid, helper=ids[0], old_helper=helper_a, tails=sites)


def patch(rom):
    patch_items_and_text(rom)
    return dict(engine=patch_engine(rom), surge=patch_surge(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
