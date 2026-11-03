"""Prototype 0166: the custom reusable TMs (Bide, Water Gun, Mega Punch, Whirlwind, Bubble Beam, Thunder Wave, Seismic Toss) are labelled "HM 00" in the bag (owner photo 2026-11-03); they show "TM 034" etc. now.
Cause: the project's custom TMs are items 115-123 (outside the native TM range 328-419). cerulean_tm.py made the bag show their Yellow TM numbers by hooking the vanilla bag routines (overlay 15, sites 0x021FE920 / 0x021FF5B2), but the expanded engine (hg-engine) replaced the label routine at 0x021FE914 by a trampoline into its own copy in overlay 129 (0x023D8674): the first site is now the tail of a BL there, and only the second site's hook (the list's TM-range test at 0x1FFFAC8) is live. The engine's routine sorts the item id into TM (328-419) / HM (420-427) ranges and sends everything else to the "HM" tag with number 0.
Fix: one hook at the start of the engine's routine, right after it has loaded the item id into r2: a custom item's id is replaced by its TM-range stand-in (327 + the Yellow TM number), so the unchanged engine code draws "TM" and the number. Nothing else changes (item ids, bag contents and compatibility stay; the list's own hook at 0x1FFFAC8 stays).
The hook replaces the two instructions at 0x023D8682 (`ldr r1, [pc, #0xb0]` = the constant 0x2E1 ; `sub sp, #0x14`) with a BL and re-does both itself. r1, r6 and r7 are free at that point (r6/r7 are saved by the routine's first push; r1's last use, the offset for `ldr r0, [r0, r1]`, is the instruction before), lr was pushed too.
Space: the zero bytes of overlay 129 after the Town Map helpers (0x023DE66A-0x023DE808); the whole length of the hook is asserted zero and inside that run (0157 lesson: a helper overran its gap into a real battle function).
Usage (from yellow-heartgold, PYTHONPATH=tools): tm_label_fix.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from prototype import thumb_bl

SITE = 0x023D8682                       # ldr r1, [pc, #0xb0] ; sub sp, #0x14  (inside the engine's label routine 0x023D8674, after `ldrh r2, [r2]`)
SITE_BYTES = bytes.fromhex('2c4985b0')
LITERAL_AT = 0x023D8734                 # the word that `ldr r1, [pc, #0xb0]` loads
FREE_RUN = (0x023DE66A, 0x023DE808)     # zero bytes after the Town Map helpers (the last one ends at 0x023DE668)
HOOK_AT = 0x023DE670
LIST_HOOK = 0x01FFFAC8                  # the list's hook in ITCM (cerulean_tm.py): its compare list and value words are the source of truth
TABLE = {115: 361, 116: 339, 117: 328, 118: 331, 119: 338, 122: 372, 123: 346}   # item -> TM-range stand-in (327 + Yellow TM number 34, 12, 1, 4, 11, 45, 19)


def list_hook_table(main):
    itcm = main.sections[1]
    at = LIST_HOOK - itcm.ramAddress
    cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB); cs.skipdata = True
    items, end = [], None
    for i in cs.disasm(bytes(itcm.data[at:at + 0xA0]), LIST_HOOK):
        if i.mnemonic == 'cmp' and i.op_str.startswith('r1, #'):
            items.append(int(i.op_str.split('#')[1], 0))
        if i.mnemonic == 'bx':
            end = i.address + 2
            break
    words = (end + 3) & ~3
    values = [struct.unpack_from('<I', itcm.data, words - itcm.ramAddress + 4 * k)[0] for k in range(len(items))]
    return dict(zip(items, values))


def hook_code(literal):
    pairs = ', '.join('%d, %d' % kv for kv in sorted(TABLE.items()))
    source = '''
ldr r1, table_ptr
loop:
ldrh r6, [r1]
cmp r6, #0
beq done
cmp r6, r2
beq found
adds r1, #4
b loop
found:
ldrh r2, [r1, #2]
done:
ldr r1, literal
sub sp, #0x14
bx lr
.balign 4
table_ptr: .word table
literal: .word %d
table: .hword %s, 0, 0
''' % (literal, pairs)
    return source


def patch(rom):
    main = rom.loadArm9()
    assert list_hook_table(main) == TABLE, 'the list hook in ITCM does not carry the expected custom TM table'
    ovs = rom.loadArm9Overlays()
    o129 = ovs[129]
    base = o129.ramAddress
    assert bytes(o129.data[SITE - base:SITE - base + 4]) == SITE_BYTES, 'the engine routine is not what was disassembled'
    literal = struct.unpack_from('<I', o129.data, LITERAL_AT - base)[0]
    code = bytes(Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(hook_code(literal), addr=HOOK_AT)[0])
    off = HOOK_AT - base
    assert FREE_RUN[0] <= HOOK_AT and HOOK_AT + len(code) <= FREE_RUN[1], (hex(HOOK_AT), len(code))
    assert not any(o129.data[off:off + len(code)]), 'the hook space is not free'
    o129.data[off:off + len(code)] = code
    o129.data[SITE - base:SITE - base + 4] = thumb_bl(SITE, HOOK_AT)
    rom.files[o129.fileID] = o129.save(compress=o129.compressed)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(site=hex(SITE), hook=hex(HOOK_AT), hook_bytes=len(code), items=sorted(TABLE), literal=hex(literal))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
