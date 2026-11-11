"""Prototype 0249 (part): script command 337 SetPersonSprite <actor id> <sprite id> - changes the overworld sprite of an actor's event record in memory, BEFORE ShowPerson creates it
(owner 2026-11-12: the daily legendary appears as ITS OWN follower sprite; scripts could not change an actor's sprite, and the event file is capped at 0x800 bytes, so 108 hidden actors do not fit).
HeartGold's ShowPerson handler (ARM9 0x02041FB8) creates the object from the map's event records in RAM (Field_GetNumObjectEvents 0x0203B74C, Field_GetObjectEvents 0x0203B754: 32-byte records, u16 id at +0, u16 sprite at +2).
 - Command 337 (pret BufferNatureName, a Platinum leftover that no script in this ROM uses) is rewritten: its old handler (0x02048AF4, 56 bytes up to the next handler) holds the argument parsing (two words, each ReadWord 0x0203FE2C + VarGet 0x020403AC, so a variable can be passed) and
   calls a small loop kept in the handler of command 482 (0x02048BCC, also unused, 68 bytes): for each record, if its id matches, store the sprite. Returns FALSE (the script goes on). The command table is not touched (337 already points at the entry).
Usage (from yellow-heartgold, PYTHONPATH=tools): set_person_sprite.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

CMD_TABLE = 0xFAD00
OPCODE, ENTRY, ENTRY_END = 337, 0x02048AF4, 0x02048B2C
LOOP, LOOP_END, OPCODE_LOOP = 0x02048BCC, 0x02048C10, 482

ENTRY_SRC = f'''
push {{r4, r5, r6, lr}}
adds r4, r0, #0
adds r0, #0x80
ldr r5, [r0]
adds r0, r4, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r5, #0
bl 0x020403AC
adds r6, r0, #0
adds r0, r4, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r5, #0
bl 0x020403AC
adds r2, r0, #0
adds r0, r5, #0
adds r1, r6, #0
bl {LOOP:#010x}
movs r0, #0
pop {{r4, r5, r6, pc}}
'''

LOOP_SRC = '''
push {r3, r4, r5, r6, r7, lr}
adds r5, r0, #0
adds r6, r1, #0
adds r7, r2, #0
bl 0x0203B74C
adds r4, r0, #0
adds r0, r5, #0
bl 0x0203B754
again:
cmp r4, #0
beq done
ldrh r1, [r0, #0]
cmp r1, r6
bne next
strh r7, [r0, #2]
next:
adds r0, #0x20
subs r4, #1
b again
done:
pop {r3, r4, r5, r6, r7, pc}
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
