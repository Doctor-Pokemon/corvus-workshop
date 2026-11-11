"""Prototype 0210: Silver has his own name, SILVER, and never shares the Kanto rival's name (owner order 2026-11-09: "I don't want BLUE and SILVER sharing the RIVAL name"; option chosen: fixed SILVER, no naming screen).
Facts (read with tools/hg_dis.py): the save has ONE rival-name field. The Oak intro (Kanto) puts the name the player chose for BLUE into it; HeartGold's lab scene (script 3 of Elm's lab) would overwrite it with a typed name (NameRival), and 19 native scripts print it through BufferRivalsName (script command 191). Silver's trainer names in battles are literal "Silver" rows in the trainer name text (records 1-3, 263-272, 285-289, 489-491, 735-737), so battles never read the field; the first battle's "Passerby Boy" label is HeartGold's own (the name is hidden until the lab scene), not a bug.
Fix:
 1. Script command 191 (BufferRivalsName, handler 0x02048449 in the command table at ARM9 0xFAD00) is replaced by a small ITCM handler: on a native Johto map (map id < 540 and bit 0 of byte 20 of its 24-byte header at 0x020F6BE0 clear, the rule the wild-level hook of step 5c uses) it buffers the literal "SILVER" into the requested slot; everywhere else (Kanto maps, the project's extension maps) it jumps to the original handler, so Kanto text still prints the name the player chose. The save's field is never written by Johto content.
 2. The battle's opponent name: the project's ITCM hook at 0x01FF8850 (trainer setup, trainer class in r0) copies the save's rival name for class 23 (Silver) and for the project's Blue (class 110, id >= 741). It now jumps into a copy of itself in the same dead ARM9 body, where class 23 gets the literal SILVER (the caller reads the name pointer back from [sp, #0xc]) and Blue still gets the field.
 3. Elm's lab scene (script 3, map 61): the naming screen is removed (the two fades and NameRival become no-ops) and its two 'result == 1 -> ask again' tests are disarmed; the confirmation line 27 loses its trailing YES/NO control so it simply says "I see? So SILVER was his name.".
The Oak intro's rival naming screen (Kanto) is not touched.
Usage (from yellow-heartgold, PYTHONPATH=tools): johto_step3f.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.narc
import ndspy.rom
from map_edit import MapEdit
from prototype import decode_messages, encode_messages
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from starter_properties import CMD_TABLE

HOME = 0x02073610                                          # inside the DEAD body of the old trainer party builder (ARM9 0x0207360C-0x02073A96; the stub at 0x02073604 jumps to overlay 131 and never comes back)
HOME_END = 0x02073A98

OP = 191
ORIGINAL = 0x02048449
HEADER_TABLE = 0x020F6BE0
SILVER = (317, 307, 310, 320, 303, 316, 0xFFFF)          # S I L V E R in HeartGold's character set + terminator
LAB = 61


def assemble(source, addr, pool_bytes):
    """Assemble Thumb source at `addr` with the literal pool (pool_bytes long, last in the source) marked by a '#POOL' line.
    Keystone mis-counts the padding of `.align`, which shifts every later `bl` by 2 bytes, and picks 32-bit `ldr.w` loads when it does not know a label is word aligned (ARMv5 cannot run those).
    So both candidate paddings (none / one `mov r8, r8` before the pool, each followed by `.align 2`) are assembled, and only one that passes three checks is accepted:
    no 32-bit instruction, the pool starts on a word boundary, and every `bl <number>` of the source decodes to exactly that target."""
    import re
    wanted = [int(m.group(1), 0) for m in re.finditer(r'^\s*bl (0x[0-9A-Fa-f]+)\s*$', source, re.M)]
    for pad in ('', '.short 0x46c0\n'):
        src = source.replace('#POOL', pad + '.align 2')
        raw, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm('\n'.join(l.split('@')[0] for l in src.splitlines()), addr=addr)
        code = bytes(raw)
        if (addr + len(code) - pool_bytes) % 4:
            continue
        code_part = code[:len(code) - pool_bytes]
        ins = list(Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code_part, addr))
        if any(i.mnemonic.endswith('.w') for i in ins):
            continue
        targets = [int(i.op_str.lstrip('#'), 0) for i in ins if i.mnemonic == 'bl' and i.op_str.startswith('#0x')]
        numeric = [t for t in targets if t in wanted]
        if numeric == wanted:
            return code
    raise ValueError('no padding variant assembled cleanly')


def install_hook(rom):
    main = rom.loadArm9()
    data = main.sections[0].data = bytearray(main.sections[0].data)
    assert struct.unpack_from('<I', data, CMD_TABLE + 4 * OP)[0] == ORIGINAL, 'BufferRivalsName handler is not the original one'
    source = f'''
push {{r3, r4, r5, lr}}
adds r5, r0, #0
adds r0, #0x80
ldr r4, [r0]
ldr r0, [r4, #0x20]
cmp r0, #0
beq native
ldr r0, [r0]
movs r1, #135
lsls r1, r1, #2
cmp r0, r1
bcs native
movs r1, #24
muls r0, r1, r0
ldr r1, header
adds r0, r0, r1
ldrb r0, [r0, #20]
movs r1, #1
ands r0, r1
bne native
movs r1, #0x10
adds r0, r4, #0
bl 0x020402F0
ldr r2, [r5, #8]
adds r1, r2, #1
str r1, [r5, #8]
ldrb r1, [r2]
ldr r0, [r0]
bl silver
movs r0, #0
pop {{r3, r4, r5, pc}}
native:
adds r0, r5, #0
ldr r3, original
blx r3
pop {{r3, r4, r5, pc}}
silver:
push {{r3, r4, r5, lr}}
adds r5, r0, #0
adds r4, r1, #0
ldr r1, text
ldr r0, [r5, #0xc]
bl 0x020269A0
ldr r2, [r5, #0xc]
adds r0, r5, #0
adds r1, r4, #0
movs r3, #0
bl 0x0200BDF8
pop {{r3, r4, r5, pc}}
#POOL
header: .word {HEADER_TABLE}
original: .word {ORIGINAL}
text: .word text_chars
text_chars: .short {', '.join(str(c) for c in SILVER)}
'''
    asm_text = source.replace('text: .word text_chars\ntext_chars:', 'text: .word 0\ntext_chars:')
    code = assemble(asm_text, HOME, 26)
    for ins in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(code[:code.index(struct.pack('<I', 0xFFFFFFFF)) if False else len(code) - 22], HOME):
        assert not (ins.mnemonic.endswith('.w') and ins.mnemonic.startswith('b')), ins.mnemonic
    assert HOME + len(code) <= HOME_END, len(code)
    ram = main.sections[0].ramAddress
    old = bytes(data[HOME - ram:HOME - ram + len(code)])
    assert old != bytes(len(old)) and data[0x02073604 - ram:0x02073604 - ram + 4] == bytes.fromhex('004b1847'), 'not the dead builder body'
    address = HOME
    string_off = code.index(struct.pack('<7H', *SILVER))
    string_addr = HOME + string_off
    code = bytearray(code)
    assert struct.unpack_from('<I', code, string_off - 4)[0] == 0
    struct.pack_into('<I', code, string_off - 4, string_addr)
    data[HOME - ram:HOME - ram + len(code)] = code
    # 2. the battle name of Silver: the project's ITCM hook at 0x01FF8850 (called by the trainer setup at 0x020733C0 with the trainer class in r0) lets class 23 (Silver) and class 110 with id >= 741 (the project's Blue)
    #    copy the save's rival name into the battle; class 23 now gets the literal SILVER instead (the caller reads the name pointer back from [sp, #0xc]); Blue keeps the field.
    HOME2 = (HOME + len(code) + 3) & ~3
    source2 = f'''
cmp r0, #0x17
beq silver
cmp r0, #0x6e
bne skip
ldr r1, [r4, #0x18]
ldr r0, threshold
cmp r1, r0
blo skip
bx lr
silver:
ldr r1, text2
str r1, [sp, #0xc]
bx lr
skip:
mov r0, lr
adds r0, #0xa
bx r0
#POOL
threshold: .word 741
text2: .word {string_addr}
'''
    code2 = assemble(source2, HOME2, 8)
    assert HOME2 + len(code2) <= HOME_END, (HOME2, len(code2))
    assert bytes(data[HOME2 - ram:HOME2 - ram + len(code2)]) != bytes(len(code2)), 'dead body expected to hold old code here'
    data[HOME2 - ram:HOME2 - ram + len(code2)] = code2
    itcm = main.sections[1]
    at = 0x01FF8850 - itcm.ramAddress
    assert bytes(itcm.data[at:at + 8]) == bytes.fromhex('17 28 05 d0 6e 28 04 d1'), bytes(itcm.data[at:at + 8]).hex()
    assert struct.unpack_from('<I', itcm.data, 0x01FF8868 - itcm.ramAddress)[0] == 741
    itcm.data[at:at + 8] = bytes.fromhex('00 4b 18 47') + struct.pack('<I', HOME2 | 1)
    # 3. the VS banner: overlay 115's rival-name helper (0x0225F1BC, called only from the VS screen when its class test passes) formats the SAVE's rival name.
    #    It becomes a jump to a thunk in the same dead ARM9 body: it asks the project's id routine (ov129 0x023DF679, the one the VS screen's other branch uses) for the trainer id of the battle
    #    (the caller's r6/r5 are still live); an id below 738 is one of HeartGold's own (Silver: 1-3, 263-272, 285-289, 489-491, 495-497, 735-737) and is named from the trainer name text
    #    (0x0225F158, rows changed to SILVER below); the project's Blue ids (738 and up) go to a copy of the original helper, so the VS banner keeps the name the player chose for BLUE.
    HOME3 = (HOME2 + len(code2) + 3) & ~3
    replica = '''
push {r3, r4, r5, r6, r7, lr}
adds r5, r1, #0
str r0, [sp]
movs r0, #1
movs r1, #0x1b
movs r2, #0xbd
adds r3, r5, #0
bl 0x0200BAF8
adds r6, r0, #0
adds r0, r5, #0
bl 0x0200BD08
adds r4, r0, #0
movs r0, #0x80
adds r1, r5, #0
bl 0x02026354
adds r7, r0, #0
movs r0, #0x80
adds r1, r5, #0
bl 0x02026354
adds r5, r0, #0
adds r0, r6, #0
movs r1, #0
adds r2, r5, #0
bl 0x0200BB6C
ldr r2, [sp]
adds r0, r4, #0
movs r1, #0
bl 0x0200BE6C
adds r0, r4, #0
adds r1, r7, #0
adds r2, r5, #0
bl 0x0200CBBC
adds r0, r6, #0
bl 0x0200BB44
adds r0, r4, #0
bl 0x0200BDA0
adds r0, r5, #0
bl 0x02026380
adds r0, r7, #0
pop {r3, r4, r5, r6, r7, pc}
'''
    source3 = '''
push {r0, r1, lr}
ldr r0, [r6, #4]
adds r1, r5, #0
ldr r3, idhook
blx r3
ldr r2, limit
cmp r0, r2
bhs blue
adds r1, r7, #0
ldr r3, byid
blx r3
add sp, #8
pop {pc}
blue:
pop {r0, r1, r2}
mov lr, r2
''' + replica + '''#POOL
idhook: .word 0x023DF679
byid: .word 0x0225F159
limit: .word 738
'''
    code3 = assemble(source3, HOME3, 12)
    assert HOME3 + len(code3) <= HOME_END, (HOME3, len(code3))
    assert bytes(data[HOME3 - ram:HOME3 - ram + len(code3)]) != bytes(len(code3)), 'dead body expected to hold old code here'
    data[HOME3 - ram:HOME3 - ram + len(code3)] = code3
    struct.pack_into('<I', data, CMD_TABLE + 4 * OP, address | 1)
    rom.arm9 = main.save(compress=True)
    ovs = rom.loadArm9Overlays()
    o = ovs[115]
    o.data = bytearray(o.data)
    at = 0x0225F1BC - o.ramAddress
    assert bytes(o.data[at:at + 4]) == bytes.fromhex('f8b5 0d1c'.replace(' ', '')), bytes(o.data[at:at + 4]).hex()
    o.data[at:at + 8] = bytes.fromhex('004b1847') + struct.pack('<I', HOME3 | 1)
    rom.files[o.fileID] = o.save(compress=o.compressed)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(handler=hex(address), string=hex(string_addr), bytes=len(code), class_hook=hex(HOME2), vs_thunk=hex(HOME3), vs_bytes=len(code3))


def patch_lab(rom):
    e = MapEdit(rom, LAB)
    fade_out = struct.pack('<5H', 174, 6, 1, 0, 0)
    fade_in = struct.pack('<5H', 174, 6, 1, 1, 0)
    wait = struct.pack('<H', 175)
    name = struct.pack('<2H', 143, 0x800C)
    block = fade_out + wait + name + fade_in + wait
    assert e.bank.count(block) == 1, 'naming block not found exactly once'
    at = e.bank.find(block)
    bank = bytearray(e.bank)
    bank[at:at + len(block)] = bytes(len(block))                       # all no-ops (command 0)
    # the two "== 1 -> ask again" tests of that script (the first follows the block, the second follows the confirmation menu)
    cmp1 = struct.pack('<3H', 17, 0x800C, 1)
    sites = [i for i in range(at, at + 400) if bytes(bank[i:i + 6]) == cmp1]
    assert len(sites) == 2, sites
    for i in sites:
        struct.pack_into('<H', bank, i + 4, 0xFFFF)
    e.bank = bytes(bank)
    # confirmation line 27: drop the trailing YES/NO control (0xFFFE 0x200 1 0)
    row = e.rows[27]
    assert row[-5:] == [0xFFFE, 0x200, 1, 0, 0xFFFF], row[-6:]
    e.rows[27] = row[:-5] + [0xFFFF]
    e.save()
    return dict(removed_block=at, disarmed=sites)


def patch_names(rom):
    """The VS banner's name text for HeartGold's own Silver records: 'Silver' becomes 'SILVER' (plain rows), like the dialogue."""
    tr = ndspy.narc.NARC(rom.getFileByName('a/0/5/5'))
    texts = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
    key, rows = decode_messages(bytes(texts.files[729]))
    changed = []
    for i in range(738):
        f = bytes(tr.files[i])
        if f and f[1] == 23:
            rows[i] = list(SILVER)
            changed.append(i)
    assert len(changed) == 24, changed
    texts.files[729] = encode_messages(key, rows)
    rom.setFileByName('a/0/2/7', texts.save())
    return dict(rows=len(changed))


def patch(rom):
    return dict(hook=install_hook(rom), names=patch_names(rom), lab=patch_lab(rom))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
