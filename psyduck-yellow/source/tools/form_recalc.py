"""Prototype 0229: the script command SetMonForm (659) also re-derives the ability and recalculates the stats of the Pokemon (owner 2026-11-10, regional-form NPC, plan item 32).
Cause: pret ScrCmd_SetMonForm = SetMonData(mon, MON_DATA_FORM, &form) only, so a Pokemon changed to Alolan/Galarian keeps the old form's stored stats until its next level-up (tested: Galarian Meowth kept the normal Attack at Lv20).
The handler lives in overlay 1 at 0x02201424 (76 bytes, the next function starts at 0x02201470). It is rewritten IN PLACE (same size, same entry address): after SetMonData the mon is passed to RecalcPartyPokemonStats (0x0206E250).
After SetMonData the handler calls ResetPartyPokemonAbility (0x020722D4: the game's own routine that picks ability 1 or 2 from the species/form personal data by the personality bit, as after an evolution) and RecalcPartyPokemonStats (0x0206E250).
Room: +14 bytes for "save the mon in r6", the ability call and the recalc call; recovered by reusing r4 (= field system, [ctx + 0x80]) instead of reloading it three times, "movs r4,#0x80; ldr r4,[r5,r4]" (4 bytes instead of 6), and by using the stack slot the push already reserves (no sub/add sp; "str r0,[sp]" for the form; r7 added to the push so the stack stays 8-byte aligned). ROM-only; no new code space.
Usage (from yellow-heartgold, PYTHONPATH=tools): form_recalc.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom

OV, START, SIZE = 1, 0x02201424, 76
VAR_PTR, GET_VAR, PARTY_OF_SAVE, PARTY_MON, SET_MON_DATA, RECALC, RESET_ABILITY = 0x0203FE2C, 0x020403AC, 0x02074904, 0x02074644, 0x0206EC40, 0x0206E250, 0x020722D4
ORIGINAL_HEAD, ORIGINAL_TAIL = bytes.fromhex('78b581b0'), bytes.fromhex('0020' '01b0' '78bd')   # push; sub sp / movs r0,#0; add sp; pop
MON_DATA_FORM = 0x70


def bl(src, dst):
    off = dst - (src + 4)
    assert -(1 << 22) <= off < (1 << 22) and off % 2 == 0
    return struct.pack('<2H', 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))


def handler():
    out = bytearray()

    def h(*w):
        out.extend(struct.pack('<%dH' % len(w), *w))

    def call(dst):
        out.extend(bl(START + len(out), dst))
    h(0xB5F8)                   # push {r3, r4, r5, r6, r7, lr}   (24 bytes: 8-aligned; the r3 slot at [sp] holds the form)
    h(0x1C05)                   # adds r5, r0, #0            r5 = script context
    h(0x2480)                   # movs r4, #0x80
    h(0x592C)                   # ldr r4, [r5, r4]           r4 = field system
    call(VAR_PTR)               # r0 = ctx still
    h(0x1C01)                   # adds r1, r0, #0
    h(0x1C20)                   # adds r0, r4, #0
    call(GET_VAR)
    h(0x1C06)                   # adds r6, r0, #0            r6 = party index
    h(0x1C28)                   # adds r0, r5, #0
    call(VAR_PTR)
    h(0x1C01)                   # adds r1, r0, #0
    h(0x1C20)                   # adds r0, r4, #0
    call(GET_VAR)
    h(0x9000)                   # str r0, [sp]               the form (low halfword)
    h(0x68E0)                   # ldr r0, [r4, #0xc]         save data
    call(PARTY_OF_SAVE)
    h(0x1C31)                   # adds r1, r6, #0
    call(PARTY_MON)
    h(0x1C06)                   # adds r6, r0, #0            NEW: keep the mon
    h(0x2100 | MON_DATA_FORM)   # movs r1, #0x70
    h(0xAA00)                   # add r2, sp, #0
    call(SET_MON_DATA)
    h(0x1C30)                   # adds r0, r6, #0            NEW
    call(RESET_ABILITY)         # NEW: ability from the new form's personal data
    h(0x1C30)                   # adds r0, r6, #0            NEW
    call(RECALC)                # NEW: recalculate the stats
    h(0x2000)                   # movs r0, #0
    h(0xBDF8)                   # pop {r3, r4, r5, r6, r7, pc}
    assert len(out) <= SIZE, len(out)
    out.extend(struct.pack('<H', 0x46C0) * ((SIZE - len(out)) // 2))     # nops (unreachable)
    return bytes(out)


def patch(rom):
    ovs = rom.loadArm9Overlays({OV})
    o = ovs[OV]
    data = bytearray(o.data)
    at = START - o.ramAddress
    assert data[at:at + 4] == ORIGINAL_HEAD and data[at + SIZE - 6:at + SIZE] == ORIGINAL_TAIL, 'unexpected SetMonForm handler bytes'
    code = handler()
    data[at:at + SIZE] = code
    o.data = bytes(data)
    rom.files[o.fileID] = o.save(compress=o.compressed)
    ovs_all = rom.loadArm9Overlays()
    ovs_all[OV] = o
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs_all)
    return dict(handler=hex(START), size=SIZE, used=len([1 for i in range(0, SIZE, 2) if code[i:i + 2] != b'\xc0\x46']) * 2)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
