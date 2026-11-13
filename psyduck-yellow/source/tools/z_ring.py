"""Prototype 0261 (owner order 2026-11-12): the Z-RING. Z-Moves need it; MOM gives it in the postgame opening after the credits.
OWNER TEXT (verbatim apart from the spelling of 'received'): MOM: "OH! Before you go, this package came for you while you slept." / "It's from a Pokemon Professor in Alola. He's invited you to challenge the new Pokemon League they're forming there." /
"That's too far away for us to move right now, but maybe this could be useful here anyway?" then the system lines "You received the mysterious package", "You open it as quickly as possible", "You received...", the item fanfare, "...a Z-RING?!".
THE ITEM: item 797 had an all-zero record (Items pocket, '?' icon, tossable, no description). It becomes a key item (the record of the native Card Key 475), gets a drawn icon and a description (text bank 842, row 797-776).
THE SCENE (Pallet Town, the post-credits chain of johto_step1.py): MOM's frame-row script (map 503, var 0x4128 == 2) ends with 'SetVar 0x4128, 3'; that command becomes a jump to a block: Mom's three lines, the gift (the Key Items pocket can be full: then a line from Mom and no gift), the package lines, the fanfare, the last line, then the SetVar and on to the old ending.
RETRY AND CATCH-UP: Mom's talk script in Pallet (map 503, actor 0 = script 1, the heal) and in New Bark Town (map 63, actor 0, the Squirt Bottle wrapper of johto_mom_gift.py) get a wrapper in front: Hall of Fame done and no Z-Ring in the bag -> the same scene (a full bag retries on the next talk); a Z-Ring already in the bag
(e.g. a PKHeX injection) only sets the flag; otherwise the old script runs. So a save that is already past the opening gets the ring from Mom the next time she is talked to.
THE GATE: Z-Moves need the flag ZRING (0x9EC, free by the instruction-level scan of ROM 0260, set whenever Mom gives or finds the ring). The extra/Z button's visibility check (ov130 0x023CFC24 -> ov129 cave of z_button.py) now returns 1 for a Z-Crystal holder only if that flag is set.
The old cave routine (28 bytes at 0x023DEA50) is replaced by a longer one in the spare bytes after z_power's routine (0x023DF588).
Usage (from yellow-heartgold, PYTHONPATH=tools): z_ring.py <in.nds> <out.nds> [icon-preview.png]"""
import struct
import sys
import ndspy.narc
import ndspy.rom
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from johto_step3d import install, write_scripts
from johto_step3d import starts as bank_starts
from johto_step3e import A
from key_item_icons import canvas, encode, outline, preview
from map_edit import MapEdit
from opening import encode_text
from parcel_quest import PH
from prototype import decode_messages, encode_messages, thumb_bl

RING, NATIVE_KEY = 797, 475
ZRING_FLAG, GAME_CLEAR = 0x9EC, 0x964
PALLET_HOUSE, NEW_BARK_HOUSE = 503, 63
STEP_VAR = 0x4128                                         # the post-credits chain variable (johto_step1.py)
DESC_BANK, DESC_BASE = 842, 776
FANFARE = 0x4A1
HAS, FACE = 128, 104
BUTTON_SITE, LOOKUP, CHECK_FLAG = 0x023CFC24, 0x023CFA88, 0x023DBE10
OLD_CAVE, NEW_CAVE, NEW_CAVE_SIZE = 0x023DEA50, 0x023DF588, 48
FIRST, LAST = 776, 836

TEXT = [
    "OH!\rBefore you go, this package came for you while you slept.",
    "It's from a Pokémon Professor in Alola.\rHe's invited you to challenge the new Pokémon League they're forming there.",
    "That's too far away for us to move right now, but maybe this could be useful here anyway?",
    "You received the mysterious package",
    "You open it as quickly as possible",
    "You received...",
    "...a Z-RING?!",
]
FULL_LINE = "Oh dear, your BAG has no room for it. Make some space and talk to me again, and I will hand it over."       # PLACEHOLDER (no owner text)
DESCRIPTION = "A bracelet that lets a Pokémon\nuse its Z-Crystal for a Z-Move.\nKeep it in the BAG."

PALETTE = [None, (40, 34, 52), (200, 206, 220), (248, 250, 255), (120, 128, 150), (255, 170, 40), (255, 226, 120), (200, 90, 20), None, None, None, None, None, None, None, None]


def ring_icon():
    """A silver ring seen from the front-above with a dark socket on top that holds an orange crystal."""
    im, d = canvas()
    d.ellipse((3, 11, 28, 30), fill=2)
    d.ellipse((8, 15, 23, 26), fill=0)
    d.arc((3, 11, 28, 30), 200, 340, fill=3)
    d.arc((3, 11, 28, 30), 20, 160, fill=4)
    d.arc((8, 15, 23, 26), 20, 160, fill=3)
    d.rounded_rectangle((10, 6, 21, 14), radius=2, fill=4)
    d.polygon([(15, 1), (20, 5), (20, 10), (15, 13), (11, 10), (11, 5)], fill=5)
    d.polygon([(15, 1), (20, 5), (15, 6)], fill=6)
    d.line([(12, 6), (15, 3)], fill=6)
    d.line([(15, 7), (15, 12)], fill=7)
    d.line([(15, 7), (19, 9)], fill=7)
    outline(im)
    return im


def patch_item(rom):
    items = ndspy.narc.NARC(rom.getFileByName('a/0/1/7'))
    assert bytes(items.files[RING]) == bytes(36), 'the Z-Ring already has a record'
    items.files[RING] = bytes(items.files[NATIVE_KEY])
    rom.setFileByName('a/0/1/7', items.save())
    gfx = ndspy.narc.NARC(rom.getFileByName('a/0/1/8'))
    gfx.files[RING * 2 + 2], gfx.files[RING * 2 + 3] = encode(ring_icon(), PALETTE, bytes(gfx.files[NATIVE_KEY * 2 + 2]), bytes(gfx.files[NATIVE_KEY * 2 + 3]))
    rom.setFileByName('a/0/1/8', gfx.save())
    texts = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
    key, rows = decode_messages(texts.files[DESC_BANK])
    assert rows[RING - DESC_BASE] == [65535], 'the Z-Ring has a description already'
    rows[RING - DESC_BASE] = decode_messages(encode_text([DESCRIPTION], PH))[1][0]
    texts.files[DESC_BANK] = encode_messages(key, rows)
    rom.setFileByName('a/0/2/7', texts.save())


def scene(a, m, full, give_label):
    """The package scene (messages m[0..6], full line m_full). Ends at label 'out'. The caller has locked the player."""
    a.msg(m[0]).msg(m[1]).msg(m[2])
    a.op(125, RING, 1, 0x800C).compare(0x800C, 0).jump('full', 1)
    a.setf(ZRING_FLAG)
    a.msg(m[3]).msg(m[4]).msg(m[5])
    a.op(78, FANFARE).op(79)
    a.msg(m[6])
    a.jump('out')
    a.label('full').msg(full)
    a.label('out')
    return a


def patch_scene_house(rom, map_id, chain):
    """chain=True: the Pallet house (frame-row script 6 + Mom's talk script 1); False: the New Bark house (Mom's actor script)."""
    e = MapEdit(rom, map_id)
    m = [e.message(t) for t in TEXT]
    full = e.message(FULL_LINE)

    def block(base, after):                                  # the post-credits step (Pallet only)
        a = A()
        a.op(HAS, RING, 1, 0x800C).compare(0x800C, 1).jump('have', 1)
        scene(a, m, full, 'out')
        a.jump('done')
        a.label('have').setf(ZRING_FLAG)
        a.label('done').set_var(STEP_VAR, 3).jump(('abs', after))
        return a.build(base)

    def wrapper(base, talk):                                 # Mom's talk script
        a = A()
        a.check_flag(GAME_CLEAR).jump(('abs', talk), 0)
        a.op(HAS, RING, 1, 0x800C).compare(0x800C, 1).jump('has', 1)
        a.raw(struct.pack('<H', 96)).raw(struct.pack('<H', FACE))
        scene(a, m, full, 'out')
        a.label('out').raw(struct.pack('<H', 97)).end()
        a.label('has').setf(ZRING_FLAG).jump(('abs', talk))
        return a.build(base)

    sizes = [len(wrapper(0, 0))] + ([len(block(0, 0))] if chain else [])
    ids, addrs, _ = install(e, sizes)
    bank = bytearray(e.bank)
    st = bank_starts(bytes(bank))
    actor = bytearray(e.groups[1][0])
    talk_id = struct.unpack_from('<H', actor, 10)[0]
    talk = st[talk_id - 1]
    write_scripts(e, [addrs[0]], [wrapper(addrs[0], talk)])
    if chain:
        seq = struct.pack('<3H', 41, STEP_VAR, 3)
        assert bytes(e.bank).count(seq) == 1, 'the step-3 command was not found exactly once'
        at = bytes(e.bank).find(seq)
        write_scripts(e, [addrs[1]], [block(addrs[1], at + 6)])
        bank = bytearray(e.bank)
        bank[at:at + 6] = struct.pack('<Hi', 22, addrs[1] - (at + 6))
        e.bank = bytes(bank)
    struct.pack_into('<H', actor, 10, ids[0])
    e.groups[1][0] = bytes(actor)
    e.save()
    return dict(map=map_id, wrapper=ids[0], talk=talk_id, block=ids[1] if chain else None)


def gate_routine():
    src = f'''
        push {{r4, lr}}
        movs r4, r1
        bl #{LOOKUP:#x}
        cmp r0, #0
        bne end
        ldr r3, lit_first
        subs r4, r4, r3
        cmp r4, #{LAST - FIRST}
        bhi zero
        ldr r0, lit_flag
        bl #{CHECK_FLAG:#x}
        b end
    zero:
        movs r0, #0
    end:
        pop {{r4, pc}}
        .align 2
    lit_first: .word {FIRST}
    lit_flag: .word {ZRING_FLAG}
    '''
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, NEW_CAVE)
    return bytes(code)


def patch_gate(rom):
    """Replace the button check's Z-crystal routine (z_button.py) by one that also needs the Z-Ring flag."""
    ovs = rom.loadArm9Overlays()
    perm, battle = ovs[129], ovs[130]
    for ov in (perm, battle):
        ov.data = bytearray(ov.data)
    site = BUTTON_SITE - battle.ramAddress
    assert bytes(battle.data[site:site + 4]) == thumb_bl(BUTTON_SITE, OLD_CAVE), 'the button hook is not the one of z_button.py'
    code = gate_routine()
    assert len(code) <= NEW_CAVE_SIZE, len(code)
    at = NEW_CAVE - perm.ramAddress
    assert not any(perm.data[at:at + NEW_CAVE_SIZE]), 'the spare bytes are not zero'
    perm.data[at:at + len(code)] = code
    old = OLD_CAVE - perm.ramAddress
    assert bytes(perm.data[old:old + 2]) == struct.pack('<H', 0xB510) and any(perm.data[old + 28:old + 36]), 'unexpected old routine'
    perm.data[old:old + 28] = bytes(28)                                  # the old 28-byte routine (the power subroutine of z_power.py starts right after it, at 0x023DEA6C)
    battle.data[site:site + 4] = thumb_bl(BUTTON_SITE, NEW_CAVE)
    for ov in (perm, battle):
        rom.files[ov.fileID] = ov.save(compress=False)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovs)
    return dict(cave=hex(NEW_CAVE), size=len(code))


def patch(rom):
    report = {'gate': patch_gate(rom)}
    patch_item(rom)
    report['pallet'] = patch_scene_house(rom, PALLET_HOUSE, True)
    report['new_bark'] = patch_scene_house(rom, NEW_BARK_HOUSE, False)
    return report


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    if len(sys.argv) > 3:
        preview([(ring_icon(), PALETTE)], sys.argv[3])
    rom.saveToFile(sys.argv[2])
