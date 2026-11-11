"""Prototype 0250 (part): let a script choose the music of the NEXT wild battle (owner 2026-11-12: "Can we just let the Embedded Tower's ancient-Pokemon theme continue into the battle?").
The wild battle's music is returned by BattleSetup_GetWildBattleMusic (ARM9 0x020517FC, a SEQ id such as SEQ_GS_VS_KODAI 1174). Its last two instructions (0x0205185C `adds r0, r4, #0` + 0x0205185E `pop {r4, r5, r6, pc}`) become `bl hook`.
 - hook (ARM9 0x02048BF4, the spare tail of the unused command-482 handler that tools/set_person_sprite.py already uses): if the override word is not 0, r4 = override and the word is cleared (one battle only); then r0 = r4 and the original `pop` runs from the hook (the stack frame is the function's own).
 - script command 335 SetBattleMusic <seq id> (the unused ScrCmd_335 handler, ARM9 0x020446AC, 64 bytes): stores the value (a word or a variable) in the override halfword at 0x020446E8 (the end of that same handler's space). 0 clears it.
Note: the battle starts the track from its BEGINNING (the same sequence id is played again); a seamless continuation would mean intercepting the battle start, which is more invasive.
Usage (from yellow-heartgold, PYTHONPATH=tools): battle_music_hook.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

CMD_TABLE, OPCODE = 0xFAD00, 335
CMD, CMD_END = 0x020446AC, 0x020446EC                  # the unused handler's space (64 bytes)
OVERRIDE = 0x020446E8                                 # the halfword the command writes and the hook reads (inside that space)
LITERAL = 0x020446E4                                  # the command's pool word: the override's address
SITE = 0x0205185C
HOOK, HOOK_END = 0x02048BF4, 0x02048C10               # the spare tail of the 482 handler

CMD_SRC = '''
push {r4, lr}
adds r4, r0, #0
bl 0x0203FE2C
adds r1, r0, #0
adds r0, r4, #0
adds r0, #0x80
ldr r0, [r0]
bl 0x020403AC
ldr r1, [pc, #32]                                  
strh r0, [r1]
movs r0, #0
pop {r4, pc}
'''

HOOK_SRC = '''
ldr r0, [pc, #16]
ldrh r1, [r0]
cmp r1, #0
beq skip
adds r4, r1, #0
movs r2, #0
strh r2, [r0]
skip:
adds r0, r4, #0
pop {r4, r5, r6, pc}
'''


def asm(src, addr):
    raw, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, addr=addr)
    code = bytes(raw)
    assert not any(i.mnemonic.endswith('.w') for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code, addr)), 'Thumb-2 instruction'
    return code


def patch(rom):
    main = rom.loadArm9()
    data = main.sections[0].data = bytearray(main.sections[0].data)
    base = main.sections[0].ramAddress
    assert struct.unpack_from('<I', data, CMD_TABLE + 4 * OPCODE)[0] == CMD | 1
    assert bytes(data[SITE - base:SITE - base + 4]) == bytes.fromhex('201c70bd'), bytes(data[SITE - base:SITE - base + 4]).hex()      # adds r0, r4, #0; pop {r4, r5, r6, pc}
    cmd = asm(CMD_SRC, CMD)
    assert len(cmd) <= LITERAL - CMD and (CMD + len(cmd) + 4 - 0) <= LITERAL + 4, len(cmd)
    pad = LITERAL - CMD - len(cmd)
    assert pad >= 0 and CMD + len(cmd) + pad == LITERAL
    cmd_blob = cmd + bytes(pad) + struct.pack('<I', OVERRIDE) + struct.pack('<H', 0) + bytes(CMD_END - LITERAL - 6)
    hook = asm(HOOK_SRC, HOOK)
    hook_pad = (-(HOOK + len(hook))) % 4
    hook_blob = hook + bytes(hook_pad) + struct.pack('<I', OVERRIDE)
    assert HOOK + len(hook_blob) <= HOOK_END, len(hook_blob)
    data[CMD - base:CMD_END - base] = cmd_blob
    data[HOOK - base:HOOK + len(hook_blob) - base] = hook_blob
    data[SITE - base:SITE - base + 4] = asm(f'bl {HOOK:#x}', SITE)
    rom.arm9 = main.save(compress=True)
    return dict(command=OPCODE, cmd_bytes=len(cmd), hook_bytes=len(hook_blob))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
