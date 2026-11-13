"""Prototype 0257, Z-Moves phase 1 (proof of concept, JOHTO-POSTGAME-PLAN.md items 53-54): a held Z-Crystal makes the extra button appear on the move menu.
The move-menu code (overlay 130, update function 0x023C6C54) asks 0x023CFB80 whether the shared extra button is available (it also needs the unlock flag 0x9D6). Inside it, the call at 0x023CFC24 looks the
(species, held item, form) up in the item table (0x023CFA88). That call is redirected to a routine in a zero-filled gap of overlay 129 (0x023DEA50): it calls the original lookup first and, when that finds nothing,
returns 1 if the held item is a Z-Crystal (items 776..836, both runs). The turn-start code that RUNS a form change (overlay 146, calling 0x023CFAC0) is untouched: it still finds no table entry for a crystal holder,
so pressing the button only toggles it (no form change happens). Phase 2 adds the move swap at that site. NOT yet required: the Z-Ring key item (item 797); the plan item 54 notes it for phase 1b.
Usage (from yellow-heartgold, PYTHONPATH=tools): z_button.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.code
import ndspy.rom
from prototype import thumb_bl

CAVE, CALL_SITE, LOOKUP = 0x023DEA50, 0x023CFC24, 0x023CFA88
FIRST, LAST = 776, 836


def routine():
    code = bytearray()
    code += struct.pack('<H', 0xB510)                      # push {r4, lr}
    code += struct.pack('<H', 0x000C)                      # movs r4, r1        (held item)
    code += thumb_bl(CAVE + 4, LOOKUP)                     # bl original lookup (r0 = species, r1 = item, r2 = form still in place)
    code += struct.pack('<H', 0x2800)                      # cmp r0, #0
    code += struct.pack('<H', 0xD104)                      # bne end
    code += struct.pack('<H', 0x4B02)                      # ldr r3, [pc, #8]   (= FIRST)
    code += struct.pack('<H', 0x1AE4)                      # subs r4, r4, r3
    code += struct.pack('<H', 0x2C00 | (LAST - FIRST))     # cmp r4, #(LAST-FIRST)
    code += struct.pack('<H', 0xD800)                      # bhi end
    code += struct.pack('<H', 0x2001)                      # movs r0, #1
    code += struct.pack('<H', 0xBD10)                      # end: pop {r4, pc}
    code += struct.pack('<I', FIRST)
    assert len(code) == 0x1C
    return bytes(code)


def patch(rom):
    ovs = rom.loadArm9Overlays()
    perm, battle = ovs[129], ovs[130]
    for ov in (perm, battle):
        ov.data = bytearray(ov.data)
    at = CAVE - perm.ramAddress
    code = routine()
    assert not any(perm.data[at:at + len(code)]), 'the gap is not zero'
    perm.data[at:at + len(code)] = code
    site = CALL_SITE - battle.ramAddress
    assert bytes(battle.data[site:site + 4]) == thumb_bl(CALL_SITE, LOOKUP), 'unexpected call at the extra button check'
    battle.data[site:site + 4] = thumb_bl(CALL_SITE, CAVE)
    for ov in (perm, battle):
        rom.files[ov.fileID] = ov.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(CAVE), size=len(code), site=hex(CALL_SITE))


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
