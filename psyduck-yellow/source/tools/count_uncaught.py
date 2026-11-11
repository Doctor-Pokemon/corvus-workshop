"""Prototype 0251 (part): script command 343 CountUncaught <result var> = how many National Dex species are NOT registered as caught
(owner 2026-11-12: Mew appears in the Embedded Tower only once everything except Mew and Arceus is registered, Arceus only once everything except Arceus is).
The National Dex of this game = dex numbers 1-1025 = species ids 1-493 and 544-1075 (tools/postgame_spread.py dexnum: the ids 494-543 are the project's own slots, not dex entries). A species counts as registered when Pokedex_CheckMonCaughtFlag (ARM9 0x02029FF8, the same test as command 336 CheckMonCaught) says so.
 - Command 343 (pret MoveBGEvent, a leftover no script in this ROM uses): the old handler (ARM9 0x0204488C, 80 bytes) is rewritten like the CheckMonSeen handler (read the result variable, fetch the Pokedex from fieldSystem->saveData, 0x0202A634), calls the counting loop and stores the count;
   the loop lives in the handler of command 370 (ScrCmd_370, ARM9 0x02043164, 80 bytes, also unused). The command table is not touched.
Usage (from yellow-heartgold, PYTHONPATH=tools): count_uncaught.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

CMD_TABLE = 0xFAD00
OPCODE, ENTRY, ENTRY_END = 343, 0x0204488C, 0x020448DC
OPCODE_LOOP, LOOP, LOOP_END = 370, 0x02043164, 0x020431B4
CAUGHT = 0x02029FF8

ENTRY_SRC = f'''
push {{r4, r5, r6, lr}}
adds r4, r0, #0
adds r0, #0x80
ldr r5, [r0]
adds r0, r4, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r5, #0
bl 0x02040374
adds r6, r0, #0
ldr r0, [r5, #0xC]
bl 0x0202A634
bl {LOOP:#010x}
strh r0, [r6]
movs r0, #0
pop {{r4, r5, r6, pc}}
'''


def scan(tag, first, limit_asm):
    return f'''
{first}
{limit_asm}
{tag}:
adds r0, r5, #0
adds r1, r6, #0
bl {CAUGHT:#010x}
cmp r0, #0
bne {tag}n
adds r4, #1
{tag}n:
adds r6, #1
cmp r6, r7
blo {tag}
'''


LOOP_SRC = '''
push {r4, r5, r6, r7, lr}
adds r5, r0, #0
movs r4, #0
''' + scan('a', 'movs r6, #1', 'movs r7, #247\nlsls r7, r7, #1') + scan('b', 'movs r6, #17\nlsls r6, r6, #5', 'movs r7, #0x43\nlsls r7, r7, #4\nadds r7, #4') + '''
adds r0, r4, #0
pop {r4, r5, r6, r7, pc}
'''


def assemble(source, address, limit):
    raw, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(source, addr=address)
    code = bytes(raw)
    assert not any(i.mnemonic.endswith('.w') for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code, address)), 'Thumb-2 instruction'
    assert len(code) <= limit, (len(code), limit)
    return code


def patch(rom):
    main = rom.loadArm9()
    data = main.sections[0].data = bytearray(main.sections[0].data)
    base = main.sections[0].ramAddress
    assert struct.unpack_from('<I', data, CMD_TABLE + 4 * OPCODE)[0] == ENTRY | 1
    entry = assemble(ENTRY_SRC, ENTRY, ENTRY_END - ENTRY)
    loop = assemble(LOOP_SRC, LOOP, LOOP_END - LOOP)
    data[ENTRY - base:ENTRY_END - base] = entry + bytes(ENTRY_END - ENTRY - len(entry))
    data[LOOP - base:LOOP_END - base] = loop + bytes(LOOP_END - LOOP - len(loop))
    rom.arm9 = main.save(compress=True)
    return dict(opcode=OPCODE, entry_bytes=len(entry), loop_bytes=len(loop))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
