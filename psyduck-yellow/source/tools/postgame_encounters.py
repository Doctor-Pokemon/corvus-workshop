"""Prototype 0223: a SECOND set of wild tables that Kanto and Johto use after the first Hall of Fame (owner 2026-11-10, plan item 30). The tables are identical copies for now: this build changes no encounter, it only adds the switch.
How the game loads wild Pokemon: once per map load, WildEncounters_ReadFromNarc (ARM9 0x0203B88C) reads member [map header byte 0] of the encounter archive a/0/3/7 (NARC id 0x25) into the map's event struct; header byte 0xFF = "no wild Pokemon here".
This tool (1) rewrites that function in place with exactly the same 44 bytes of room: it reads the bank, tests flag 0x964 (Hall of Fame; CheckScriptFlagPassSave 0x020665AC on SavArray_Flags_get(SaveBlock2_get())) and reads member bank + 256 * flag;
the old HasWild test and the memset are dropped because (2) the archive now has 512 members of 196 bytes: 0-181 the originals, 182-255 empty (255 = "no wild Pokemon", all rates 0, so a map with header byte 0xFF reads a harmless empty table),
256-437 the postgame copies (edit these later), 438-511 empty. Nothing else reads the archive by member count. ROM-only; no ITCM or overlay space is used.
Usage (from yellow-heartgold, PYTHONPATH=tools): postgame_encounters.py <in.nds> <out.nds>"""
import struct
import sys
import ndspy.narc
import ndspy.rom

LOADER, SIZE = 0x0203B88C, 44
GET_BANK, SAVEBLOCK2, FLAGS_GET, CHECK, READ = 0x0203B344, 0x020272B0, 0x020503D0, 0x020665AC, 0x02007508
FLAG, NARC_ID = 0x964, 0x25
ORIGINAL = 182
POSTGAME = 256
RECORD = 196


def bl(src, dst):
    off = dst - (src + 4)
    assert -(1 << 22) <= off < (1 << 22) and off % 2 == 0
    return struct.pack('<2H', 0xF000 | ((off >> 12) & 0x7FF), 0xF800 | ((off >> 1) & 0x7FF))


def loader_code():
    out = b''

    def h(*words):
        nonlocal out
        out += struct.pack('<%dH' % len(words), *words)

    def call(dst):
        nonlocal out
        out += bl(LOADER + len(out), dst)
    h(0xB538)                                   # push {r3, r4, r5, lr}
    h(0x1C05)                                   # adds r5, r0, #0          r5 = encounter data buffer
    h(0x1C08)                                   # adds r0, r1, #0          r0 = map id
    call(GET_BANK)                              # r0 = map header byte 0
    h(0x1C04)                                   # adds r4, r0, #0          r4 = bank
    call(SAVEBLOCK2)
    call(FLAGS_GET)
    h(0x2196, 0x0109, 0x3104)                   # movs r1, #0x96; lsls r1, r1, #4; adds r1, #4   (0x964)
    call(CHECK)                                 # r0 = 0 or 1
    h(0x0200)                                   # lsls r0, r0, #8          r0 = 256 * flag
    h(0x1822)                                   # adds r2, r4, r0          r2 = bank + 256 * flag
    h(0x1C28)                                   # adds r0, r5, #0
    h(0x2100 | NARC_ID)                         # movs r1, #0x25
    call(READ)
    h(0xBD38)                                   # pop {r3, r4, r5, pc}
    assert len(out) == SIZE, len(out)
    return out


def patch(rom):
    main = rom.loadArm9()
    d = main.sections[0].data = bytearray(main.sections[0].data)
    at = LOADER - 0x02000000
    assert d[at:at + 2] == struct.pack('<H', 0xB538) and d[at + 40:at + 42] == struct.pack('<H', 0xBD38) and d[at + 42:at + 44] == b'\0\0', 'unexpected loader bytes'
    d[at:at + SIZE] = loader_code()
    rom.arm9 = main.save(compress=True)
    narc = ndspy.narc.NARC(rom.getFileByName('a/0/3/7'))
    files = [bytes(f) for f in narc.files]
    assert len(files) == ORIGINAL and all(len(f) == RECORD for f in files)
    empty = bytes(RECORD)
    narc.files = files + [empty] * (POSTGAME - ORIGINAL) + list(files) + [empty] * (512 - POSTGAME - ORIGINAL)
    assert len(narc.files) == 512
    rom.setFileByName('a/0/3/7', narc.save())
    return dict(loader=hex(LOADER), members=len(narc.files), postgame_first=POSTGAME)


if __name__ == '__main__':
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    print(patch(rom))
    rom.saveToFile(sys.argv[2])
