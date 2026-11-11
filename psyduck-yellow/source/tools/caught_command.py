"""Prototype 0243: a script command that asks the Pokedex "has this species been CAUGHT?" (owner 2026-11-12, for the legendary system: "Have it check the Pokedex. If the legendary is already registered as caught, it won't appear.").
HeartGold's script engine only has CheckMonSeen (opcode 707: Pokedex_CheckMonSeenFlag) - a species you merely met counts as seen, which is the wrong rule for "once each".
 - New command: opcode 336 (pret name BufferBerryName, a Platinum leftover that no script in this ROM uses; scan of every script bank, 2026-11-12) becomes
   CheckMonCaught <species> <result var>: result 1 if the Pokedex has the species as caught (caught bit AND seen bit, the engine's own rule), else 0. Same argument order as CheckMonSeen.
 - Handler: a copy of the CheckMonSeen handler (overlay 1 at 0x022019B0) with its one call changed from Pokedex_CheckMonSeenFlag (0x0202A044) to Pokedex_CheckMonCaughtFlag (0x02029FF8). The ITCM extension is full
   (32 KiB), so it is written OVER the original BufferBerryName handler (ARM9 0x02048A7C, 0x78 bytes up to the next handler at 0x02048AF4; the command table entry 336 already points at it, so the table is not touched).
   CheckMonSeen itself is untouched (the std-bank legendary list uses it).
 - Both Pokedex functions range-check through the hg-engine extension of the species limit, so Gen 5+ species (ids above 493) use the same arrays.
Usage (from yellow-heartgold, PYTHONPATH=tools): caught_command.py <in 0242.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from starter_properties import CMD_TABLE

OPCODE = 336
CAUGHT_FLAG_FN = 0x02029FF8
SEEN_FLAG_FN = 0x0202A044

SOURCE = f'''
push {{r4, r5, r6, lr}}
adds r5, r0, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r5, #0
adds r0, #0x80
ldr r0, [r0]
bl 0x020403AC
adds r6, r0, #0
adds r0, r5, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r5, #0
adds r0, #0x80
ldr r0, [r0]
bl 0x02040374
adds r5, #0x80
adds r4, r0, #0
ldr r0, [r5]
ldr r0, [r0, #0xC]
bl 0x0202A634
adds r1, r6, #0
bl {CAUGHT_FLAG_FN:#010x}
strh r0, [r4]
movs r0, #0
pop {{r4, r5, r6, pc}}
'''


HANDLER, NEXT_HANDLER = 0x02048A7C, 0x02048AF4


def patch(rom):
    main = rom.loadArm9()
    data = main.sections[0].data = bytearray(main.sections[0].data)
    entry = struct.unpack_from('<I', data, CMD_TABLE + 4 * OPCODE)[0]
    assert entry == HANDLER | 1 and struct.unpack_from('<I', data, CMD_TABLE + 4 * (OPCODE + 1))[0] == NEXT_HANDLER | 1, hex(entry)
    raw, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(SOURCE, addr=HANDLER)
    code = bytes(raw)
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    assert not any(i.mnemonic.endswith('.w') for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code, HANDLER))
    assert len(code) <= NEXT_HANDLER - HANDLER, len(code)
    at = HANDLER - main.sections[0].ramAddress
    code += bytes((NEXT_HANDLER - HANDLER) - len(code))
    data[at:at + len(code)] = code
    rom.arm9 = main.save(compress=True)
    return dict(opcode=OPCODE, handler=hex(HANDLER), size=len(code))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
